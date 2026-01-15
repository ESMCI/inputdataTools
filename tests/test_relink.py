"""
Tests for relink.py script.
"""

import os
import sys
import tempfile
import shutil
import pwd
import logging
from unittest.mock import patch

import pytest

# Add parent directory to path to import relink module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# pylint: disable=wrong-import-position
import relink  # noqa: E402


@pytest.fixture(scope="function", autouse=True)
def configure_logging():
    """Configure logging to output to stdout for all tests."""
    # Configure logging before each test
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
        force=True,  # Force reconfiguration
    )
    yield
    # Clean up logging handlers after each test
    logging.getLogger().handlers.clear()


@pytest.fixture(scope="function", name="mock_default_dirs")
def fixture_mock_default_dirs():
    """Mock the default directories to use temporary directories."""
    source_dir = tempfile.mkdtemp(prefix="test_default_source_")
    target_dir = tempfile.mkdtemp(prefix="test_default_target_")

    with patch.object(relink, "DEFAULT_SOURCE_ROOT", source_dir):
        with patch.object(relink, "DEFAULT_TARGET_ROOT", target_dir):
            yield source_dir, target_dir

    # Cleanup
    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.rmtree(target_dir, ignore_errors=True)


@pytest.fixture(scope="function", name="temp_dirs")
def fixture_temp_dirs():
    """Create temporary source and target directories for testing."""
    source_dir = tempfile.mkdtemp(prefix="test_source_")
    target_dir = tempfile.mkdtemp(prefix="test_target_")

    yield source_dir, target_dir

    # Cleanup
    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.rmtree(target_dir, ignore_errors=True)


class TestFindAndReplaceOwnedFiles:
    """Test suite for find_and_replace_owned_files function."""

    @pytest.fixture
    def current_user(self):
        """Get the current user's username."""
        username = os.environ["USER"]
        return username

    def test_basic_file_replacement(self, temp_dirs, current_user):
        """Test basic functionality: replace owned file with symlink."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create a file in source directory
        source_file = os.path.join(source_dir, "test_file.txt")
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("source content")

        # Create corresponding file in target directory
        target_file = os.path.join(target_dir, "test_file.txt")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target content")

        # Run the function
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify the source file is now a symlink
        assert os.path.islink(source_file), "Source file should be a symlink"
        assert (
            os.readlink(source_file) == target_file
        ), "Symlink should point to target file"

    def test_nested_directory_structure(self, temp_dirs, current_user):
        """Test with nested directory structures."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create nested directories
        nested_path = os.path.join("subdir1", "subdir2")
        os.makedirs(os.path.join(source_dir, nested_path))
        os.makedirs(os.path.join(target_dir, nested_path))

        # Create files in nested directories
        source_file = os.path.join(source_dir, nested_path, "nested_file.txt")
        target_file = os.path.join(target_dir, nested_path, "nested_file.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("nested source")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("nested target")

        # Run the function
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify
        assert os.path.islink(source_file), "Nested file should be a symlink"
        assert os.readlink(source_file) == target_file

    def test_skip_existing_symlinks(self, temp_dirs, current_user, caplog):
        """Test that existing symlinks are skipped."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create a target file
        target_file = os.path.join(target_dir, "target.txt")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target")

        # Create a symlink in source (pointing somewhere else)
        source_link = os.path.join(source_dir, "existing_link.txt")
        dummy_target = os.path.join(tempfile.gettempdir(), "somewhere")
        os.symlink(dummy_target, source_link)

        # Get the inode and mtime before running the function
        stat_before = os.lstat(source_link)

        # Run the function
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify the symlink is unchanged (same inode means it wasn't deleted/recreated)
        stat_after = os.lstat(source_link)
        assert (
            stat_before.st_ino == stat_after.st_ino
        ), "Symlink should not have been recreated"
        assert (
            stat_before.st_mtime == stat_after.st_mtime
        ), "Symlink mtime should be unchanged"
        assert (
            os.readlink(source_link) == dummy_target
        ), "Symlink target should be unchanged"

        # Check that "Skipping symlink" message was logged
        assert "Skipping symlink:" in caplog.text
        assert source_link in caplog.text

    def test_missing_target_file(self, temp_dirs, current_user, caplog):
        """Test behavior when target file doesn't exist."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create only source file (no corresponding target)
        source_file = os.path.join(source_dir, "orphan.txt")
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("orphan content")

        # Run the function
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify the file is NOT converted to symlink
        assert not os.path.islink(source_file), "File should not be a symlink"
        assert os.path.isfile(source_file), "Original file should still exist"

        # Check warning message
        assert "Warning: Corresponding file not found" in caplog.text

    def test_invalid_username(self, temp_dirs, caplog):
        """Test behavior with invalid username."""
        source_dir, target_dir = temp_dirs

        # Use a username that doesn't exist
        invalid_username = "nonexistent_user_12345"
        try:
            pwd.getpwnam(invalid_username).pw_uid
        except KeyError:
            pass
        else:
            raise RuntimeError(f"{invalid_username=} DOES actually exist")

        # Run the function
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(
                source_dir, target_dir, invalid_username
            )

        # Check error message
        assert "Error: User" in caplog.text
        assert "not found" in caplog.text

    def test_multiple_files(self, temp_dirs, current_user):
        """Test with multiple files in the directory."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create multiple files
        for i in range(5):
            source_file = os.path.join(source_dir, f"file_{i}.txt")
            target_file = os.path.join(target_dir, f"file_{i}.txt")

            with open(source_file, "w", encoding="utf-8") as f:
                f.write(f"source {i}")
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(f"target {i}")

        # Run the function
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify all files are symlinks
        for i in range(5):
            source_file = os.path.join(source_dir, f"file_{i}.txt")
            target_file = os.path.join(target_dir, f"file_{i}.txt")
            assert os.path.islink(source_file)
            assert os.readlink(source_file) == target_file

    def test_absolute_paths(self, temp_dirs, current_user):
        """Test that function handles relative paths by converting to absolute."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create test files
        source_file = os.path.join(source_dir, "test.txt")
        target_file = os.path.join(target_dir, "test.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("test")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("test target")

        # Use relative paths (if possible)
        cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(source_dir))
            rel_source = os.path.basename(source_dir)
            rel_target = os.path.basename(target_dir)

            # Run with relative paths
            relink.find_and_replace_owned_files(rel_source, rel_target, username)

            # Verify it still works
            assert os.path.islink(source_file)
        finally:
            os.chdir(cwd)

    def test_print_searching_message(self, temp_dirs, current_user, caplog):
        """Test that searching message is printed."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Run the function
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Check that searching message was logged
        assert f"Searching for files owned by '{username}'" in caplog.text
        assert f"in '{os.path.abspath(source_dir)}'" in caplog.text

    def test_print_found_owned_file(self, temp_dirs, current_user, caplog):
        """Test that 'Found owned file' message is printed."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create a file owned by current user
        source_file = os.path.join(source_dir, "owned_file.txt")
        target_file = os.path.join(target_dir, "owned_file.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("content")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target content")

        # Run the function
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Check that "Found owned file" message was logged
        assert "Found owned file:" in caplog.text
        assert source_file in caplog.text

    def test_print_deleted_and_created_messages(self, temp_dirs, current_user, caplog):
        """Test that deleted and created symlink messages are printed."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create files
        source_file = os.path.join(source_dir, "test_file.txt")
        target_file = os.path.join(target_dir, "test_file.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("source")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target")

        # Run the function
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Check messages
        assert "Deleted original file:" in caplog.text
        assert "Created symbolic link:" in caplog.text
        assert f"{source_file} -> {target_file}" in caplog.text

    def test_handles_file_deleted_during_traversal(
        self, temp_dirs, current_user, caplog
    ):
        """Test that FileNotFoundError during stat is handled gracefully."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create files
        source_file = os.path.join(source_dir, "disappearing.txt")
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("content")

        # Mock os.stat to raise FileNotFoundError for this specific file
        original_stat = os.stat

        def mock_stat(path, *args, **kwargs):
            if path == source_file:
                raise FileNotFoundError(f"Simulated: {path} deleted during traversal")
            return original_stat(path, *args, **kwargs)

        with patch("os.stat", side_effect=mock_stat):
            with caplog.at_level(logging.INFO):
                # Should not crash, should continue processing
                relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Should complete without errors (file was skipped)
        # No error message should be logged (it's silently skipped via continue)
        assert "Error" not in caplog.text
        assert "disappearing.txt" not in caplog.text


class TestParseArguments:
    """Test suite for parse_arguments function."""

    def test_default_arguments(self, mock_default_dirs):
        """Test that default arguments are used when none provided."""
        source_dir, target_dir = mock_default_dirs
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.source_root == source_dir
            assert args.target_root == target_dir

    def test_custom_source_root(self, mock_default_dirs, tmp_path):
        """Test custom source root argument."""
        _, target_dir = mock_default_dirs
        custom_source = tmp_path / "custom_source"
        custom_source.mkdir()
        with patch("sys.argv", ["relink.py", "--source-root", str(custom_source)]):
            args = relink.parse_arguments()
            assert args.source_root == str(custom_source.resolve())
            assert args.target_root == target_dir

    def test_custom_target_root(self, mock_default_dirs, tmp_path):
        """Test custom target root argument."""
        source_dir, _ = mock_default_dirs
        custom_target = tmp_path / "custom_target"
        custom_target.mkdir()
        with patch("sys.argv", ["relink.py", "--target-root", str(custom_target)]):
            args = relink.parse_arguments()
            assert args.source_root == source_dir
            assert args.target_root == str(custom_target.resolve())

    def test_both_custom_paths(self, tmp_path):
        """Test both custom source and target roots."""
        source_path = tmp_path / "custom_source"
        target_path = tmp_path / "custom_target"
        source_path.mkdir()
        target_path.mkdir()
        with patch(
            "sys.argv",
            [
                "relink.py",
                "--source-root",
                str(source_path),
                "--target-root",
                str(target_path),
            ],
        ):
            args = relink.parse_arguments()
            assert args.source_root == str(source_path.resolve())
            assert args.target_root == str(target_path.resolve())

    def test_verbose_flag(self, mock_default_dirs):  # pylint: disable=unused-argument
        """Test that --verbose flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "--verbose"]):
            args = relink.parse_arguments()
            assert args.verbose is True
            assert args.quiet is False

    def test_quiet_flag(self, mock_default_dirs):  # pylint: disable=unused-argument
        """Test that --quiet flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "--quiet"]):
            args = relink.parse_arguments()
            assert args.quiet is True
            assert args.verbose is False

    def test_verbose_short_flag(
        self, mock_default_dirs
    ):  # pylint: disable=unused-argument
        """Test that -v flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "-v"]):
            args = relink.parse_arguments()
            assert args.verbose is True

    def test_quiet_short_flag(
        self, mock_default_dirs
    ):  # pylint: disable=unused-argument
        """Test that -q flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "-q"]):
            args = relink.parse_arguments()
            assert args.quiet is True

    def test_default_verbosity(
        self, mock_default_dirs
    ):  # pylint: disable=unused-argument
        """Test that default verbosity has both flags as False."""
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.verbose is False
            assert args.quiet is False

    def test_verbose_and_quiet_mutually_exclusive(self, mock_default_dirs):
        """Test that --verbose and --quiet cannot be used together."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "--verbose", "--quiet"]):
            with pytest.raises(SystemExit) as exc_info:
                relink.parse_arguments()
            # Mutually exclusive arguments cause SystemExit with code 2
            assert exc_info.value.code == 2

    def test_verbose_and_quiet_short_flags_mutually_exclusive(self, mock_default_dirs):
        """Test that -v and -q cannot be used together."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "-v", "-q"]):
            with pytest.raises(SystemExit) as exc_info:
                relink.parse_arguments()
            # Mutually exclusive arguments cause SystemExit with code 2
            assert exc_info.value.code == 2

    def test_dry_run_flag(self, mock_default_dirs):
        """Test that --dry-run flag is parsed correctly."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "--dry-run"]):
            args = relink.parse_arguments()
            assert args.dry_run is True

    def test_dry_run_default(self, mock_default_dirs):
        """Test that dry_run defaults to False."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.dry_run is False

    def test_timing_flag(self, mock_default_dirs):
        """Test that --timing flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "--timing"]):
            args = relink.parse_arguments()
            assert args.timing is True

    def test_timing_default(self, mock_default_dirs):
        """Test that timing defaults to False."""
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.timing is False


class TestTiming:
    """Test suite for timing functionality."""

    def test_timing_message_logged(self, tmp_path, caplog):
        """Test that timing message is logged when timing is enabled."""
        # Create real directories
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create a file
        source_file = source_dir / "test_file.txt"
        target_file = target_dir / "test_file.txt"
        source_file.write_text("source")
        target_file.write_text("target")

        # Mock sys.argv to simulate running with --timing
        test_argv = [
            "relink.py",
            "--source-root", str(source_dir),
            "--target-root", str(target_dir),
            "--timing"
        ]

        with patch("sys.argv", test_argv):
            with caplog.at_level(logging.INFO):
                # Call main() which includes the timing logic
                relink.main()

        # Verify timing message was logged
        assert "Execution time:" in caplog.text
        assert "seconds" in caplog.text

    def test_timing_not_logged_by_default(self, tmp_path, caplog):
        """Test that timing message is not logged when timing is disabled."""
        # Create real directories
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create a file
        source_file = source_dir / "test_file.txt"
        target_file = target_dir / "test_file.txt"
        source_file.write_text("source")
        target_file.write_text("target")

        # Mock sys.argv WITHOUT --timing flag
        test_argv = [
            "relink.py",
            "--source-root", str(source_dir),
            "--target-root", str(target_dir)
        ]

        with patch("sys.argv", test_argv):
            with caplog.at_level(logging.INFO):
                # Call main() without timing flag
                relink.main()

        # Verify timing message was NOT logged
        assert "Execution time:" not in caplog.text


class TestDryRun:
    """Test suite for dry-run functionality."""

    def test_dry_run_no_changes(self, temp_dirs, caplog):
        """Test that dry-run mode makes no actual changes."""
        source_dir, target_dir = temp_dirs
        username = os.environ["USER"]

        # Create files
        source_file = os.path.join(source_dir, "test_file.txt")
        target_file = os.path.join(target_dir, "test_file.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("source content")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target content")

        # Get original file info
        with open(source_file, "r", encoding="utf-8") as f:
            original_content = f.read()
        original_is_link = os.path.islink(source_file)

        # Run in dry-run mode
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(
                source_dir, target_dir, username, dry_run=True
            )

        # Verify no changes were made
        assert os.path.isfile(source_file), "Original file should still exist"
        assert not os.path.islink(source_file), "File should not be a symlink"
        with open(source_file, "r", encoding="utf-8") as f:
            assert f.read() == original_content
        assert os.path.islink(source_file) == original_is_link

    def test_dry_run_shows_message(self, temp_dirs, caplog):
        """Test that dry-run mode shows what would be done."""
        source_dir, target_dir = temp_dirs
        username = os.environ["USER"]

        # Create files
        source_file = os.path.join(source_dir, "test_file.txt")
        target_file = os.path.join(target_dir, "test_file.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("source")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target")

        # Run in dry-run mode
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(
                source_dir, target_dir, username, dry_run=True
            )

        # Check that dry-run messages were logged
        assert "DRY RUN MODE" in caplog.text
        assert "[DRY RUN] Would create symbolic link:" in caplog.text
        assert f"{source_file} -> {target_file}" in caplog.text

    def test_dry_run_no_delete_or_create_messages(self, temp_dirs, caplog):
        """Test that dry-run doesn't show delete/create messages."""
        source_dir, target_dir = temp_dirs
        username = os.environ["USER"]

        # Create files
        source_file = os.path.join(source_dir, "test_file.txt")
        target_file = os.path.join(target_dir, "test_file.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("source")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target")

        # Run in dry-run mode
        with caplog.at_level(logging.INFO):
            relink.find_and_replace_owned_files(
                source_dir, target_dir, username, dry_run=True
            )

        # Verify actual operation messages are NOT logged
        assert "Deleted original file:" not in caplog.text
        assert "Created symbolic link:" not in caplog.text
        # But the dry-run message should be there
        assert "[DRY RUN] Would create symbolic link: " in caplog.text
