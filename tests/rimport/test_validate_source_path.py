"""
Tests for validate_source_path() function in rimport script.
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


def test_ok_regular_file_under_root(tmp_path):
    """A valid regular file under the inputdata root returns None."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    src = inputdata_root / "file.nc"
    src.write_text("data")

    assert rimport.validate_source_path(src, inputdata_root, staging_root) is None


def test_ok_already_published_symlink_is_not_a_failure(tmp_path):
    """DANGEROUS CASE: a live symlink whose target resolves under staging_root is the normal
    state of a file that has already been published and linked by a previous run. This must
    return None, not an exception — otherwise re-running rimport over an already-published
    tree would report every published file as a pre-flight failure."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    real_file = staging_root / "real_file.nc"
    real_file.write_text("data")
    src = inputdata_root / "link.nc"
    src.symlink_to(real_file)

    assert rimport.validate_source_path(src, inputdata_root, staging_root) is None


def test_error_broken_symlink(tmp_path):
    """A symlink whose target does not exist returns a RuntimeError, unraised."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    src = inputdata_root / "broken_link.nc"
    src.symlink_to(tmp_path / "nonexistent.nc")

    result = rimport.validate_source_path(src, inputdata_root, staging_root)
    assert isinstance(result, RuntimeError)
    assert "Source is a broken symlink" in str(result)


def test_error_live_symlink_target_outside_staging(tmp_path):
    """A live symlink whose target resolves outside staging_root returns a RuntimeError,
    unraised."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    real_file = tmp_path / "real_file.nc"
    real_file.write_text("data")
    src = inputdata_root / "link.nc"
    src.symlink_to(real_file)

    result = rimport.validate_source_path(src, inputdata_root, staging_root)
    assert isinstance(result, RuntimeError)
    assert "outside staging directory" in str(result)


def test_error_missing_file(tmp_path):
    """A path that does not exist returns a FileNotFoundError, unraised."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    src = inputdata_root / "nonexistent.nc"

    result = rimport.validate_source_path(src, inputdata_root, staging_root)
    assert isinstance(result, FileNotFoundError)
    assert "source not found" in str(result)


def test_error_directory(tmp_path):
    """A directory (not a symlink) returns a RuntimeError, unraised."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    src = inputdata_root / "adir"
    src.mkdir()

    result = rimport.validate_source_path(src, inputdata_root, staging_root)
    assert isinstance(result, RuntimeError)
    assert "source is a directory, not a file" in str(result)


def test_error_file_outside_inputdata_root(tmp_path):
    """A regular file outside the inputdata root returns a RuntimeError, unraised."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    src = tmp_path / "outside" / "file.nc"
    src.parent.mkdir()
    src.write_text("data")

    result = rimport.validate_source_path(src, inputdata_root, staging_root)
    assert isinstance(result, RuntimeError)
    assert "not under inputdata root" in str(result)


def test_error_file_already_under_staging_directory(tmp_path):
    """A regular (non-symlink) file already living under staging_root returns a RuntimeError,
    unraised."""
    inputdata_root = tmp_path / "inputdata"
    inputdata_root.mkdir()
    staging_root = tmp_path / "staging"
    staging_root.mkdir()

    src = staging_root / "file.nc"
    src.write_text("data")

    result = rimport.validate_source_path(src, inputdata_root, staging_root)
    assert isinstance(result, RuntimeError)
    assert "already under staging directory" in str(result)
