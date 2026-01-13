"""
Tests for relink.py script.
"""

import os
import sys
import tempfile
import shutil
import pwd
from unittest.mock import patch
import pytest

# Add parent directory to path to import relink module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import relink


class TestFindAndReplaceOwnedFiles:
    """Test suite for find_and_replace_owned_files function."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary source and target directories for testing."""
        source_dir = tempfile.mkdtemp(prefix="test_source_")
        target_dir = tempfile.mkdtemp(prefix="test_target_")

        yield source_dir, target_dir

        # Cleanup
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(target_dir, ignore_errors=True)

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

    def test_skip_existing_symlinks(self, temp_dirs, current_user):
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
        inode_before = stat_before.st_ino
        mtime_before = stat_before.st_mtime

        # Run the function
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify the symlink is unchanged (same inode means it wasn't deleted/recreated)
        stat_after = os.lstat(source_link)
        assert (
            inode_before == stat_after.st_ino
        ), "Symlink should not have been recreated"
        assert mtime_before == stat_after.st_mtime, "Symlink mtime should be unchanged"
        assert (
            os.readlink(source_link) == dummy_target
        ), "Symlink target should be unchanged"

    def test_missing_target_file(self, temp_dirs, current_user, capsys):
        """Test behavior when target file doesn't exist."""
        source_dir, target_dir = temp_dirs
        username = current_user

        # Create only source file (no corresponding target)
        source_file = os.path.join(source_dir, "orphan.txt")
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("orphan content")

        # Run the function
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify the file is NOT converted to symlink
        assert not os.path.islink(source_file), "File should not be a symlink"
        assert os.path.isfile(source_file), "Original file should still exist"

        # Check warning message
        captured = capsys.readouterr()
        assert "Warning: Corresponding file not found" in captured.out

    def test_invalid_username(self, temp_dirs, capsys):
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
        relink.find_and_replace_owned_files(source_dir, target_dir, invalid_username)

        # Check error message
        captured = capsys.readouterr()
        assert "Error: User" in captured.out
        assert "not found" in captured.out

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


class TestParseArguments:
    """Test suite for parse_arguments function."""

    def test_default_arguments(self):
        """Test that default arguments are used when none provided."""
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.source_root == relink.DEFAULT_SOURCE_ROOT
            assert args.target_root == relink.DEFAULT_TARGET_ROOT

    def test_custom_source_root(self):
        """Test custom source root argument."""
        test_path = os.path.join(os.sep, "custom", "source", "path")
        with patch("sys.argv", ["relink.py", "--source-root", test_path]):
            args = relink.parse_arguments()
            assert args.source_root == test_path
            assert args.target_root == relink.DEFAULT_TARGET_ROOT

    def test_custom_target_root(self):
        """Test custom target root argument."""
        test_path = os.path.join(os.sep, "custom", "target", "path")
        with patch("sys.argv", ["relink.py", "--target-root", test_path]):
            args = relink.parse_arguments()
            assert args.source_root == relink.DEFAULT_SOURCE_ROOT
            assert args.target_root == test_path

    def test_both_custom_paths(self):
        """Test both custom source and target roots."""
        source_path = os.path.join(os.sep, "custom", "source")
        target_path = os.path.join(os.sep, "custom", "target")
        with patch(
            "sys.argv",
            ["relink.py", "--source-root", source_path, "--target-root", target_path],
        ):
            args = relink.parse_arguments()
            assert args.source_root == source_path
            assert args.target_root == target_path


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary source and target directories for testing."""
        source_dir = tempfile.mkdtemp(prefix="test_source_")
        target_dir = tempfile.mkdtemp(prefix="test_target_")

        yield source_dir, target_dir

        # Cleanup
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(target_dir, ignore_errors=True)

    def test_empty_directories(self, temp_dirs):
        """Test with empty directories."""
        source_dir, target_dir = temp_dirs
        username = os.environ["USER"]

        # Run with empty directories (should not crash)
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Should complete without errors
        assert True

    def test_file_with_spaces_in_name(self, temp_dirs):
        """Test files with spaces in their names."""
        source_dir, target_dir = temp_dirs
        username = os.environ["USER"]

        # Create files with spaces
        source_file = os.path.join(source_dir, "file with spaces.txt")
        target_file = os.path.join(target_dir, "file with spaces.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("content")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target content")

        # Run the function
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify
        assert os.path.islink(source_file)
        assert os.readlink(source_file) == target_file

    def test_file_with_special_characters(self, temp_dirs):
        """Test files with special characters in names."""
        source_dir, target_dir = temp_dirs
        username = os.environ["USER"]

        # Create files with special chars (that are valid in filenames)
        filename = "file-with_special.chars@123.txt"
        source_file = os.path.join(source_dir, filename)
        target_file = os.path.join(target_dir, filename)

        with open(source_file, "w", encoding="utf-8") as f:
            f.write("content")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("target content")

        # Run the function
        relink.find_and_replace_owned_files(source_dir, target_dir, username)

        # Verify
        assert os.path.islink(source_file)
        assert os.readlink(source_file) == target_file
