"""
Tests for walk_files() function in rimport script.
"""

import os
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


def test_finds_files_recursively(tmp_path):
    """Files at every depth are returned, and directories themselves are not."""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "top.nc").write_text("top")
    (tmp_path / "a" / "mid.nc").write_text("mid")
    (tmp_path / "a" / "b" / "deep.nc").write_text("deep")

    files, skips = rimport.walk_files(tmp_path)

    assert skips == []
    assert files == [
        tmp_path / "a" / "b" / "deep.nc",
        tmp_path / "a" / "mid.nc",
        tmp_path / "top.nc",
    ]


def test_entries_are_sorted_at_each_level(tmp_path):
    """Order is deterministic, so output and downstream assertions are stable."""
    for name in ["zebra.nc", "apple.nc", "mango.nc"]:
        (tmp_path / name).write_text(name)

    files, _skips = rimport.walk_files(tmp_path)

    assert [f.name for f in files] == ["apple.nc", "mango.nc", "zebra.nc"]


def test_symlinks_to_files_are_yielded(tmp_path):
    """A symlink is an entry to act on, not something to pass over."""
    real = tmp_path / "real.nc"
    real.write_text("data")
    link = tmp_path / "link.nc"
    link.symlink_to(real)

    files, _skips = rimport.walk_files(tmp_path)

    assert link in files


def test_does_not_descend_through_directory_symlink(tmp_path):
    """A symlink to a directory is yielded as ONE entry; the walk must not follow it.

    Following it would let the walk leave the directory the user named, and would let a
    cyclic link loop forever.
    """
    tree = tmp_path / "tree"
    tree.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "hidden_away.nc").write_text("must not be found")
    link = tree / "dirlink"
    link.symlink_to(outside)

    files, _skips = rimport.walk_files(tree)

    assert files == [link]
    assert not any(f.name == "hidden_away.nc" for f in files)


def test_dotfiles_are_included(tmp_path):
    """No hidden-file filter: rimport publishes what is there."""
    (tmp_path / ".hidden.nc").write_text("data")

    files, _skips = rimport.walk_files(tmp_path)

    assert [f.name for f in files] == [".hidden.nc"]


def test_empty_directory_yields_nothing(tmp_path):
    """An empty tree is not an error."""
    files, skips = rimport.walk_files(tmp_path)

    assert files == []
    assert skips == []


def test_unreadable_directory_is_returned_as_a_skip(tmp_path):
    """A directory that cannot be read is reported, not raised, and does not abort the walk."""
    readable = tmp_path / "readable"
    readable.mkdir()
    (readable / "good.nc").write_text("data")
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "unreachable.nc").write_text("data")
    os.chmod(locked, 0o000)

    try:
        files, skips = rimport.walk_files(tmp_path)
    finally:
        os.chmod(locked, 0o700)

    assert files == [readable / "good.nc"]
    assert len(skips) == 1
    assert skips[0].path == locked
    assert isinstance(skips[0].reason, OSError)
