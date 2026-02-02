"""
Tests for resolve_paths() function in rimport script.
"""

import os
import sys
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

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
sys.modules["rimport"] = rimport
loader.exec_module(rimport)


@pytest.fixture(name="root")
def fixture_root(tmp_path):
    """Create and return a root directory for testing."""
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    return root_dir


class TestResolvePaths:
    """Test suite for resolve_paths() function."""

    def test_single_relative_path(self, root):
        """Test resolving a single relative path."""
        result = rimport.resolve_paths(root, ["file1.nc"])

        assert len(result) == 1
        assert result[0] == (root / "file1.nc").resolve()

    def test_multiple_relative_paths(self, root):
        """Test resolving multiple relative paths."""
        relnames = ["file1.nc", "file2.nc", "file3.nc"]
        result = rimport.resolve_paths(root, relnames)

        assert len(result) == 3
        assert result[0] == (root / "file1.nc").resolve()
        assert result[1] == (root / "file2.nc").resolve()
        assert result[2] == (root / "file3.nc").resolve()

    def test_nested_relative_paths(self, root):
        """Test resolving nested relative paths."""
        relnames = ["dir1/file1.nc", "dir2/subdir/file2.nc"]
        result = rimport.resolve_paths(root, relnames)

        assert len(result) == 2
        assert result[0] == (root / "dir1" / "file1.nc").resolve()
        assert result[1] == (root / "dir2" / "subdir" / "file2.nc").resolve()

    def test_absolute_path(self, tmp_path, root):
        """Test that absolute paths are preserved."""
        abs_path = tmp_path / "other" / "file.nc"
        relnames = [str(abs_path)]

        result = rimport.resolve_paths(root, relnames)

        assert len(result) == 1
        assert result[0] == abs_path.resolve()

    def test_mixed_relative_and_absolute(self, tmp_path, root):
        """Test mixing relative and absolute paths."""
        abs_path = tmp_path / "other" / "file.nc"
        relnames = ["file1.nc", str(abs_path), "dir/file2.nc"]

        result = rimport.resolve_paths(root, relnames)

        assert len(result) == 3
        assert result[0] == (root / "file1.nc").resolve()
        assert result[1] == abs_path.resolve()
        assert result[2] == (root / "dir" / "file2.nc").resolve()

    def test_empty_list(self, root):
        """Test with empty list of names."""
        result = rimport.resolve_paths(root, [])

        assert len(result) == 0
        assert result == []

    def test_paths_with_spaces(self, root):
        """Test paths with spaces in names."""
        relnames = ["file with spaces.nc", "dir with spaces/file.nc"]
        result = rimport.resolve_paths(root, relnames)

        assert len(result) == 2
        assert result[0] == (root / "file with spaces.nc").resolve()
        assert result[1] == (root / "dir with spaces" / "file.nc").resolve()

    def test_paths_with_special_characters(self, root):
        """Test paths with special characters."""
        relnames = ["file-name_123.nc", "dir@test/file.nc"]
        result = rimport.resolve_paths(root, relnames)

        assert len(result) == 2
        assert result[0] == (root / "file-name_123.nc").resolve()
        assert result[1] == (root / "dir@test" / "file.nc").resolve()

    def test_returns_path_objects(self, root):
        """Test that result contains Path objects."""
        result = rimport.resolve_paths(root, ["file.nc"])

        assert len(result) == 1
        assert isinstance(result[0], Path)

    def test_resolves_dot_and_dotdot(self, root):
        """Test that . and .. are resolved."""
        relnames = ["./file1.nc", "dir/../file2.nc", "dir/./file3.nc"]
        result = rimport.resolve_paths(root, relnames)

        assert len(result) == 3
        assert result[0] == (root / "file1.nc").resolve()
        assert result[1] == (root / "file2.nc").resolve()
        assert result[2] == (root / "dir" / "file3.nc").resolve()
