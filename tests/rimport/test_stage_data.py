"""
Tests for stage_data() function in rimport script.
"""

import os
import sys
import importlib.util
from importlib.machinery import SourceFileLoader

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


@pytest.fixture(name="inputdata_root")
def fixture_inputdata_root(tmp_path):
    """Create and return an inputdata root directory."""
    root = tmp_path / "inputdata"
    root.mkdir()
    return root


@pytest.fixture(name="staging_root")
def fixture_staging_root(tmp_path):
    """Create and return a staging root directory."""
    root = tmp_path / "staging"
    root.mkdir()
    return root


class TestStageData:
    """Test suite for stage_data() function."""

    def test_copies_file_to_staging(self, inputdata_root, staging_root):
        """Test that a file is copied to the staging directory."""
        # Create file in inputdata root
        src = inputdata_root / "file.nc"
        src.write_text("data content")

        # Stage the file
        rimport.stage_data(src, inputdata_root, staging_root)

        # Verify file was copied to staging
        dst = staging_root / "file.nc"
        assert dst.exists()
        assert dst.read_text() == "data content"

    def test_preserves_directory_structure(self, inputdata_root, staging_root):
        """Test that directory structure is preserved in staging."""
        # Create nested file in inputdata root
        src = inputdata_root / "dir1" / "dir2" / "file.nc"
        src.parent.mkdir(parents=True)
        src.write_text("nested data")

        # Stage the file
        rimport.stage_data(src, inputdata_root, staging_root)

        # Verify directory structure is preserved
        dst = staging_root / "dir1" / "dir2" / "file.nc"
        assert dst.exists()
        assert dst.read_text() == "nested data"

    def test_raises_error_for_live_symlink_already_published(
        self, inputdata_root, staging_root
    ):
        """
        Test that staging a live, already-published symlink raises RuntimeError with accurate
        message.
        """
        # Create a real file and a symlink to it
        real_file = staging_root / "real_file.nc"
        real_file.write_text("data")
        src = inputdata_root / "link.nc"
        src.symlink_to(real_file)

        # Should raise RuntimeError for live symlink
        with pytest.raises(RuntimeError, match="File is already published and linked"):
            rimport.stage_data(src, inputdata_root, staging_root)

    def test_raises_error_for_live_symlink_pointing_somewhere_other_than_staging(
        self, tmp_path, inputdata_root, staging_root
    ):
        """
        Test that staging a live symlink that points to somewhere other than staging directory
        raises RuntimeError with accurate message.
        """
        # Create a real file outside the staging directory and a symlink to it
        real_file = tmp_path / "real_file.nc"
        real_file.write_text("data")
        src = inputdata_root / "link.nc"
        src.symlink_to(real_file)

        # Should raise RuntimeError for live symlink
        with pytest.raises(RuntimeError, match="outside staging directory"):
            rimport.stage_data(src, inputdata_root, staging_root)

    def test_raises_error_for_broken_symlink(
        self, tmp_path, inputdata_root, staging_root
    ):
        """Test that staging a broken symlink raises RuntimeError."""
        # Create a broken symlink
        src = inputdata_root / "broken_link.nc"
        src.symlink_to(tmp_path / "nonexistent.nc")

        # Should raise RuntimeError for broken symlink
        with pytest.raises(RuntimeError, match="Source is a broken symlink"):
            rimport.stage_data(src, inputdata_root, staging_root)

    def test_raises_error_for_nonexistent_file(self, inputdata_root, staging_root):
        """Test that staging a nonexistent file raises FileNotFoundError."""
        # Reference a nonexistent file
        src = inputdata_root / "nonexistent.nc"

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="source not found"):
            rimport.stage_data(src, inputdata_root, staging_root)

    def test_raises_error_for_file_outside_inputdata_root(
        self, tmp_path, inputdata_root, staging_root
    ):
        """Test that staging a file outside inputdata root raises RuntimeError."""
        # Create a file outside inputdata root
        src = tmp_path / "outside" / "file.nc"
        src.parent.mkdir()
        src.write_text("data")

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="not under inputdata root"):
            rimport.stage_data(src, inputdata_root, staging_root)

    def test_raises_error_for_file_outside_inputdata_root_with_special_str(
        self, tmp_path, inputdata_root, staging_root
    ):
        """
        Test that staging a file outside inputdata root raises RuntimeError, even if a certain
        special string is included in its path.
        """
        # Create a file outside inputdata root
        src = tmp_path / "outside" / "file_d651077.nc"
        src.parent.mkdir()
        src.write_text("data")

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="not under inputdata root"):
            rimport.stage_data(src, inputdata_root, staging_root)

    def test_raises_error_for_already_published_file(
        self, tmp_path, inputdata_root, staging_root
    ):
        """Test that staging an already published file raises RuntimeError."""
        # Create a file in staging_root
        src = staging_root / "file.nc"
        src.write_text("data")

        # Should raise RuntimeError for already published file
        with pytest.raises(RuntimeError, match="already under staging directory"):
            rimport.stage_data(src, inputdata_root, staging_root)

    def test_preserves_file_metadata(self, inputdata_root, staging_root):
        """Test that file metadata (timestamps, permissions) is preserved."""
        # Create file in inputdata root
        src = inputdata_root / "file.nc"
        src.write_text("data")

        # Set specific permissions
        src.chmod(0o644)

        # Get original metadata
        src_stat = src.stat()

        # Stage the file
        rimport.stage_data(src, inputdata_root, staging_root)

        # Verify metadata is preserved
        dst = staging_root / "file.nc"
        dst_stat = dst.stat()

        assert dst_stat.st_mtime == src_stat.st_mtime
        assert dst_stat.st_mode == src_stat.st_mode

    def test_handles_files_with_spaces(self, inputdata_root, staging_root):
        """Test handling files with spaces in names."""
        # Create file with spaces in inputdata root
        src = inputdata_root / "file with spaces.nc"
        src.write_text("data")

        # Stage the file
        rimport.stage_data(src, inputdata_root, staging_root)

        # Verify file was copied
        dst = staging_root / "file with spaces.nc"
        assert dst.exists()
        assert dst.read_text() == "data"

    def test_handles_files_with_special_characters(self, inputdata_root, staging_root):
        """Test handling files with special characters."""
        # Create file with special chars in inputdata root
        src = inputdata_root / "file-name_123@test.nc"
        src.write_text("data")

        # Stage the file
        rimport.stage_data(src, inputdata_root, staging_root)

        # Verify file was copied
        dst = staging_root / "file-name_123@test.nc"
        assert dst.exists()
        assert dst.read_text() == "data"
