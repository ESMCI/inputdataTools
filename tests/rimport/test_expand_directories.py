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

    entries, skips = rimport.expand_directories([d])

    assert skips == []
    assert entries == [
        rimport.Entry(d / "a.nc", False),
        rimport.Entry(d / "b.nc", False),
    ]


def test_plain_file_passes_through_as_named(tmp_path):
    """A file the user typed stays named, so its failures stay fatal."""
    f = tmp_path / "f.nc"
    f.write_text("data")

    entries, _skips = rimport.expand_directories([f])

    assert entries == [rimport.Entry(f, True)]


def test_nonexistent_path_passes_through_as_named(tmp_path):
    """Expansion does not validate. A missing path stays named so pre-flight can reject it."""
    missing = tmp_path / "missing.nc"

    entries, _skips = rimport.expand_directories([missing])

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

    entries, _skips = rimport.expand_directories([link])

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

    entries, _skips = rimport.expand_directories([d, inner])

    assert entries == [rimport.Entry(inner, True)]


def test_duplicate_order_is_first_seen(tmp_path):
    """De-duplication preserves the order a path was first encountered."""
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.nc").write_text("a")
    (d / "b.nc").write_text("b")

    entries, _skips = rimport.expand_directories([d, d])

    assert [e.path.name for e in entries] == ["a.nc", "b.nc"]


def test_walk_skips_are_passed_through(tmp_path):
    """An unreadable directory found during expansion surfaces as a Skip."""
    d = tmp_path / "d"
    d.mkdir()
    locked = d / "locked"
    locked.mkdir()
    os.chmod(locked, 0o000)

    try:
        _entries, skips = rimport.expand_directories([d])
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
        entries, skips = rimport.expand_directories([d])

    assert entries == []
    assert skips == []
    assert f"no files found under {d}" in caplog.text


def test_logs_expansion_counts(tmp_path, caplog):
    """The blast radius is visible before anything is staged."""
    d1 = tmp_path / "d1"
    d1.mkdir()
    (d1 / "a.nc").write_text("a")
    d2 = tmp_path / "d2"
    d2.mkdir()
    (d2 / "b.nc").write_text("b")
    (d2 / "c.nc").write_text("c")

    with caplog.at_level(logging.INFO, logger="rimport_relink"):
        rimport.expand_directories([d1, d2])

    assert "expanded 2 director(ies) to 3 file(s)" in caplog.text


def test_no_expansion_logs_no_count_line(tmp_path, caplog):
    """A batch of plain files should not emit a confusing 'expanded 0' line."""
    f = tmp_path / "f.nc"
    f.write_text("data")

    with caplog.at_level(logging.INFO, logger="rimport_relink"):
        rimport.expand_directories([f])

    assert "expanded" not in caplog.text
