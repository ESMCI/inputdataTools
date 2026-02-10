"""
Tests for stage_data() function in rimport script.
"""

import os
import logging
import importlib.util
from importlib.machinery import SourceFileLoader
from unittest.mock import patch

import pytest

import shared

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


@pytest.fixture(autouse=True)
def configure_logging_for_tests():
    """Configure logging for all tests in this module."""
    shared.configure_logging(logging.INFO)
    yield
    # Cleanup
    rimport.logger.handlers.clear()


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

    def test_copies_and_relinks_unpublished(self, inputdata_root, staging_root):
        """Test that an unpublished file is copied to the staging directory and relinked."""
        # Create file in inputdata root
        src = inputdata_root / "file.nc"
        src.write_text("data content")

        # Stage the file
        rimport.stage_data(src, inputdata_root, staging_root)

        # Verify file was copied to staging
        dst = staging_root / "file.nc"
        assert dst.exists()
        assert dst.read_text() == "data content"

        # Verify original was replaced with symlink
        assert src.is_symlink()
        assert src.resolve() == dst

    def test_check_doesnt_copy_unpublished(self, inputdata_root, staging_root, caplog):
        """Test that an unpublished file is NOT copied to the staging directory if check is True"""
        # Create file in inputdata root
        file_basename = "file.nc"
        src = inputdata_root / file_basename
        src.write_text("data content")

        # Check the file
        rimport.stage_data(src, inputdata_root, staging_root, check=True)

        # Verify file was NOT copied to staging or relinked
        dst = staging_root / file_basename
        assert not dst.exists()
        assert not src.is_symlink()

    def test_check_doesnt_relink_published(self, inputdata_root, staging_root, caplog):
        """Test that a published file is NOT relinked if check is True"""
        # Create file in inputdata root and staging
        file_basename = "file.nc"
        src = inputdata_root / file_basename
        src.write_text("data content")
        dst = staging_root / file_basename
        dst.write_text("data content")

        # Check the file
        rimport.stage_data(src, inputdata_root, staging_root, check=True)

        # Verify file was NOT relinked
        assert not src.is_symlink()

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

        # Verify original was replaced with symlink
        assert src.is_symlink()
        assert src.resolve() == dst

    def test_prints_live_symlink_already_published_not_downloadable(
        self, inputdata_root, staging_root, caplog
    ):
        """
        Test that staging a live, already-published symlink prints a message and returns
        immediately without copying anything. Should say it's not available for download.
        """
        # Create a real file in staging and a symlink to it in inputdata
        real_file = staging_root / "real_file.nc"
        real_file.write_text("data")
        src = inputdata_root / "link.nc"
        src.symlink_to(real_file)

        # Mock shutil.copy2 to verify it's never called
        with patch("shutil.copy2") as mock_copy:
            # Should print message for live symlink and return early
            rimport.stage_data(src, inputdata_root, staging_root)

            # Verify the right messages were logged
            msg = "File is already published and linked"
            assert msg in caplog.text
            msg = "File is not (yet) available for download"
            assert msg in caplog.text

            # Verify the WRONG message was NOT logged
            msg = "is already under staging directory"
            assert msg not in caplog.text

            # Verify that shutil.copy2 was never called (function returned early)
            mock_copy.assert_not_called()

    @patch.object(rimport, "can_file_be_downloaded")
    def test_prints_live_symlink_already_published_is_downloadable(
        self, mock_can_file_be_downloaded, inputdata_root, staging_root, caplog
    ):
        """
        Like test_prints_live_symlink_already_published_not_downloadable, but mocks
        can_file_be_downloaded() to test "is available for download" message.
        """
        # Create a real file in staging and a symlink to it in inputdata
        real_file = staging_root / "real_file.nc"
        real_file.write_text("data")
        src = inputdata_root / "link.nc"
        src.symlink_to(real_file)

        # Mock can_file_be_downloaded to return True
        mock_can_file_be_downloaded.return_value = True

        # Mock shutil.copy2 to verify it's never called
        with patch("shutil.copy2") as mock_copy:
            # Should print message for live symlink and return early
            rimport.stage_data(src, inputdata_root, staging_root)

            # Verify that shutil.copy2 was never called (function returned early)
            mock_copy.assert_not_called()

        # Verify the right messages were logged
        msg = "File is already published and linked"
        assert msg in caplog.text
        msg = "File is available for download"
        assert msg in caplog.text

        # Verify the WRONG message was NOT logged
        msg = "is already under staging directory"
        assert msg not in caplog.text

    @patch.object(rimport, "can_file_be_downloaded")
    def test_prints_published_but_not_linked(
        self, mock_can_file_be_downloaded, inputdata_root, staging_root, caplog
    ):
        """
        Tests printed message for when a file has been published (copied to staging root) but not
        yet linked (inputdata version replaced with symlink to staging version).
        """
        # Create a real file in staging AND in inputdata
        filename = "real_file.nc"
        staged = staging_root / filename
        staged.write_text("data")
        inputdata = inputdata_root / filename
        inputdata.write_text("data")

        # Mock can_file_be_downloaded to return True
        mock_can_file_be_downloaded.return_value = True

        # Mock shutil.copy2 to verify it's never called
        with patch("shutil.copy2") as mock_copy:

            # Should print message for live symlink and return early
            rimport.stage_data(inputdata, inputdata_root, staging_root)

            # Verify that shutil.copy2 was never called (function returned early)
            mock_copy.assert_not_called()

        # Verify the right messages were logged or not
        msg = "File is already published and linked"
        assert msg not in caplog.text
        msg = "File is already published but NOT linked; linking"
        assert msg in caplog.text
        msg = "File is available for download"
        assert msg in caplog.text

        # Verify the file got linked
        assert inputdata.is_symlink()
        assert inputdata.resolve() == staged

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
        self, inputdata_root, staging_root
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

        # Verify the file got linked
        assert src.is_symlink()
        assert src.resolve() == dst

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

        # Verify the file got linked
        assert src.is_symlink()
        assert src.resolve() == dst

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

        # Verify the file got linked
        assert src.is_symlink()
        assert src.resolve() == dst

    @patch.object(rimport, "replace_one_file_with_symlink")
    def test_not_already_published_errors_if_relink_fails(
        self, _mock_replace_one_file_with_symlink, inputdata_root, staging_root
    ):
        """
        Test that it errors if, after publishing, replace_one_file_with_symlink() doesn't make the
        symlink.
        """
        # Create file in inputdata root
        src = inputdata_root / "file.nc"
        src.write_text("data content")

        assert not inputdata_root.is_symlink()
        assert not src.is_symlink()
        dst = staging_root / "file.nc"
        assert not dst.exists()

        # Stage the file but expect failure during relink check
        with pytest.raises(RuntimeError) as exc_info:
            rimport.stage_data(src, inputdata_root, staging_root)

        # Verify file was copied to staging
        assert dst.exists()
        assert dst.read_text() == "data content"

        # Verify error message was printed
        assert "Error relinking during rimport" in str(exc_info.value)

    @patch.object(rimport, "can_file_be_downloaded")
    @patch.object(rimport, "replace_one_file_with_symlink")
    def test_already_published_errors_if_relink_fails(
        self,
        _mock_replace_one_file_with_symlink,
        mock_can_file_be_downloaded,
        inputdata_root,
        staging_root,
    ):
        """
        Test that it errors if, for an already-published file, replace_one_file_with_symlink()
        doesn't make the symlink.
        """
        # Create a real file in staging AND in inputdata
        filename = "real_file.nc"
        staged = staging_root / filename
        staged.write_text("data")
        inputdata = inputdata_root / filename
        inputdata.write_text("data")

        # Mock can_file_be_downloaded to return True
        mock_can_file_be_downloaded.return_value = True

        # Expect failure during relink check
        with pytest.raises(RuntimeError) as exc_info:
            rimport.stage_data(inputdata, inputdata_root, staging_root)

        # Verify error message was printed
        assert "Error relinking during rimport" in str(exc_info.value)
