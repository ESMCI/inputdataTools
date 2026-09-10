"""
Tests for expand_directories() function in rimport script.
"""

import os
import logging
import importlib.util
from importlib.machinery import SourceFileLoader


# Import rimport module from file without .py extension
rimport_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "rimport",
)
loader = SourceFileLoader("rimport", rimport_path)
spec = importlib.util.spec_from_loader("rimport", loader)
if spec is None:
    raise ImportError(f"Could not create spec for rimport from {rimport_path}")
rimport = importlib.util.module_from_spec(spec)
# Don't add to sys.modules to avoid conflict with other test files
loader.exec_module(rimport)


def test_directory_expands_to_discovered_files(tmp_path):
    """Files found by walking a named directory are tagged discovered, not named."""
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.nc").write_text("a")
    (d / "b.nc").write_text("b")

    entries, skips = rimport.expand_directories([d], tmp_path)

    assert skips == []
    assert entries == [
        rimport.Entry(d / "a.nc", False),
        rimport.Entry(d / "b.nc", False),
    ]


def test_plain_file_passes_through_as_named(tmp_path):
    """A file the user typed stays named, so its failures stay fatal."""
    f = tmp_path / "f.nc"
    f.write_text("data")

    entries, _skips = rimport.expand_directories([f], tmp_path)

    assert entries == [rimport.Entry(f, True)]


def test_nonexistent_path_passes_through_as_named(tmp_path):
    """Expansion does not validate. A missing path stays named so pre-flight can reject it."""
    missing = tmp_path / "missing.nc"

    entries, _skips = rimport.expand_directories([missing], tmp_path)

    assert entries == [rimport.Entry(missing, True)]


def test_symlink_to_directory_is_not_expanded(tmp_path):
    """A named symlink-to-directory stays ONE named entry under the per-file rules.

    It is not walked, matching walk_files' refusal to descend through a directory symlink.
    """
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "inside.nc").write_text("data")
    link = tmp_path / "dirlink"
    link.symlink_to(real_dir)

    entries, _skips = rimport.expand_directories([link], tmp_path)

    assert entries == [rimport.Entry(link, True)]


def test_duplicates_collapse_and_named_wins(tmp_path):
    """Naming a file that also lives inside a named directory keeps it named.

    Otherwise the user's own explicitly typed path would be demoted to a discovered
    entry, and its validation failure would warn-and-skip instead of aborting.
    """
    d = tmp_path / "d"
    d.mkdir()
    inner = d / "inner.nc"
    inner.write_text("data")

    entries, _skips = rimport.expand_directories([d, inner], tmp_path)

    assert entries == [rimport.Entry(inner, True)]


def test_named_wins_when_the_file_is_named_before_its_directory(tmp_path):
    """Naming the file before the directory that contains it reaches the same verdict as
    naming it after (the test above). The two orders take different routes: this one sets
    `named` first and the walk must not clear it."""
    d = tmp_path / "d"
    d.mkdir()
    inner = d / "inner.nc"
    inner.write_text("data")

    entries, _skips = rimport.expand_directories([inner, d], tmp_path)

    assert entries == [rimport.Entry(inner, True)]


def test_duplicate_order_is_first_seen(tmp_path):
    """De-duplication preserves the order a path was first encountered, across arguments."""
    d1 = tmp_path / "d1"
    d1.mkdir()
    (d1 / "b.nc").write_text("b")
    d2 = tmp_path / "d2"
    d2.mkdir()
    (d2 / "a.nc").write_text("a")

    # d1 first, so its file leads, even though "a.nc" sorts before "b.nc" within a walk.
    entries, _skips = rimport.expand_directories([d1, d2, d1], tmp_path)

    assert [e.path.name for e in entries] == ["b.nc", "a.nc"]


def test_walk_skips_are_passed_through(tmp_path):
    """An unreadable directory found during expansion surfaces as a Skip."""
    d = tmp_path / "d"
    d.mkdir()
    locked = d / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        _entries, skips = rimport.expand_directories([d], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert len(skips) == 1
    assert skips[0].path == locked


def test_empty_directory_warns_but_is_not_a_skip(tmp_path, caplog):
    """A named directory containing nothing is worth saying out loud, but is not an error
    and must not affect the exit code."""
    d = tmp_path / "empty"
    d.mkdir()

    with caplog.at_level(logging.WARNING, logger="rimport_relink"):
        entries, skips = rimport.expand_directories([d], tmp_path)

    assert entries == []
    assert skips == []
    assert f"no files found under {d}" in caplog.text


def test_logs_expansion_counts(tmp_path, caplog):
    """The blast radius is printed by `expand_directories()` -- i.e., before anything is staged."""
    d1 = tmp_path / "d1"
    d1.mkdir()
    (d1 / "a.nc").write_text("a")
    d2 = tmp_path / "d2"
    d2.mkdir()
    (d2 / "b.nc").write_text("b")
    (d2 / "c.nc").write_text("c")

    with caplog.at_level(logging.INFO, logger="rimport_relink"):
        rimport.expand_directories([d1, d2], tmp_path)

    assert "expanded 2 director(ies) to 3 file(s)" in caplog.text


def test_no_expansion_logs_no_count_line(tmp_path, caplog):
    """A batch of plain files should not emit a confusing 'expanded 0' line."""
    f = tmp_path / "f.nc"
    f.write_text("data")

    with caplog.at_level(logging.INFO, logger="rimport_relink"):
        rimport.expand_directories([f], tmp_path)

    assert "expanded" not in caplog.text


def test_unreadable_directory_does_not_warn_that_it_is_empty(tmp_path, caplog):
    """A directory that could not be read is not an empty directory. Saying "no files found"
    for it contradicts the Permission denied reported for the same path."""
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "hidden.nc").write_text("data")
    os.chmod(locked, 0o000)

    try:
        with caplog.at_level(logging.WARNING, logger="rimport_relink"):
            entries, skips = rimport.expand_directories([locked], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert entries == []
    assert len(skips) == 1
    assert "no files found" not in caplog.text


def test_discovered_walk_skip_is_warned_where_it_happened(tmp_path, caplog):
    """Every skip is reported twice: here, as the run reaches it, and again in the end-of-run
    summary. Without this first report a skip during a fatal abort is reported zero times."""
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.nc").write_text("a")
    locked = d / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        with caplog.at_level(logging.WARNING, logger="rimport_relink"):
            rimport.expand_directories([d], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert f"skipping '{locked}'" in caplog.text
    # The line already names the path, so the reason must not repeat it. OSError's str()
    # appends the filename and prefixes the errno; strerror is the part worth reading.
    assert "Permission denied" in caplog.text
    assert "[Errno" not in caplog.text
    assert caplog.text.count(str(locked)) == 1


def test_named_unreadable_directory_is_not_warned_as_skipped(tmp_path, caplog):
    """A NAMED unreadable directory is fatal, and main reports it as such. Warning
    it as a failure; warning "skipping" here too would contradict "nothing was published"."""
    locked = tmp_path / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        with caplog.at_level(logging.WARNING, logger="rimport_relink"):
            rimport.expand_directories([locked], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert "skipping" not in caplog.text


def test_named_unreadable_directory_is_not_warned_even_when_also_discovered(tmp_path, caplog):
    """A path can be named AND discovered at once: name a tree and an unreadable directory
    inside it, and the walk of the tree finds what the user also typed. It is still named,
    so main reports it as a fatal failure and nothing here may call it "skipping" -- the two
    messages contradict each other. Provenance is whole-batch membership, not "is this the
    directory being walked"."""
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.nc").write_text("a")
    locked = d / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        with caplog.at_level(logging.WARNING, logger="rimport_relink"):
            rimport.expand_directories([d, locked], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert "skipping" not in caplog.text


def test_expansion_count_is_logged_before_any_skip_warning(tmp_path, caplog):
    """The count line is the blast radius, and it belongs at the top where it cannot be
    pushed down the screen by one warning per unreadable directory."""
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.nc").write_text("a")
    locked = d / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        with caplog.at_level(logging.INFO, logger="rimport_relink"):
            rimport.expand_directories([d], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert caplog.text.index("expanded 1 director(ies)") < caplog.text.index("skipping")


def test_directory_named_twice_is_reported_once(tmp_path, caplog):
    """Naming the same directory twice is one directory, not two, so the blast-radius line
    counts it once."""
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.nc").write_text("a")

    with caplog.at_level(logging.INFO, logger="rimport_relink"):
        rimport.expand_directories([d, d], tmp_path)

    assert "expanded 1 director(ies) to 1 file(s)" in caplog.text


def test_duplicate_arguments_do_not_duplicate_a_skip(tmp_path, caplog):
    """One unreadable directory is one skip, however many of the named arguments reach it.
    Otherwise it is warned about twice, listed twice in the end-of-run summary, and counted
    twice in the total."""
    d = tmp_path / "d"
    d.mkdir()
    locked = d / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        with caplog.at_level(logging.WARNING, logger="rimport_relink"):
            _entries, skips = rimport.expand_directories([d, d], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert len(skips) == 1
    assert caplog.text.count("skipping") == 1


def test_overlapping_named_directories_do_not_duplicate_a_skip(tmp_path):
    """Same defect by another route: a subdirectory named alongside its parent is walked
    twice, so anything unreadable beneath it is recorded twice."""
    d = tmp_path / "d"
    d.mkdir()
    sub = d / "sub"
    sub.mkdir()
    locked = sub / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        _entries, skips = rimport.expand_directories([d, sub], tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert len(skips) == 1


def test_directory_outside_the_root_is_not_expanded(tmp_path):
    """Expansion is scoped to the inputdata tree. A directory outside it passes through as a
    named entry for the pre-flight gate to reject, exactly as a nonexistent path does."""
    root = tmp_path / "inputdata"
    root.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "a.nc").write_text("a")

    entries, skips = rimport.expand_directories([outside], root)

    assert entries == [rimport.Entry(outside, True)]
    assert skips == []


def test_directory_outside_the_root_is_not_even_walked(tmp_path, monkeypatch):
    """Declining to expand must happen BEFORE the walk, not by discarding its results:
    walking recurses, and the whole point is not to stat a tree we have no business in."""
    root = tmp_path / "inputdata"
    root.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    def _fail(_path):
        raise AssertionError("walk_files must not be called for a path outside the root")

    monkeypatch.setattr(rimport, "walk_files", _fail)

    rimport.expand_directories([outside], root)


def test_directory_at_the_root_itself_is_expanded(tmp_path):
    """The boundary case: the root is not outside itself."""
    root = tmp_path / "inputdata"
    root.mkdir()
    (root / "a.nc").write_text("a")

    entries, _skips = rimport.expand_directories([root], root)

    assert entries == [rimport.Entry(root / "a.nc", False)]


def test_scope_is_decided_after_resolving_symlinks(tmp_path):
    """The scope test resolves both sides, matching validate_source_path, so a directory
    reached through a symlinked parent is judged by where it really is rather than by how it
    was spelled. A lexical test would call this one outside the root and decline to expand
    it; the two checks would then disagree about the same path."""
    root = tmp_path / "inputdata"
    (root / "lnd").mkdir(parents=True)
    (root / "lnd" / "a.nc").write_text("a")
    # A door into the tree from outside it. Spelled through here, the path is lexically
    # outside `root` but resolves inside.
    door = tmp_path / "door"
    door.symlink_to(root)

    entries, _skips = rimport.expand_directories([door / "lnd"], root)

    assert entries == [rimport.Entry(door / "lnd" / "a.nc", False)]
