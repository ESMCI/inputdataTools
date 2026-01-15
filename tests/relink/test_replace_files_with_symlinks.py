"""
Tests of replace_files_with_symlinks() in relink.py
"""

import os
import sys
import tempfile
import pwd
import logging
from unittest.mock import patch

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402


def test_basic_file_replacement(temp_dirs, current_user):
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
    relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Verify the source file is now a symlink
    assert os.path.islink(source_file), "Source file should be a symlink"
    assert (
        os.readlink(source_file) == target_file
    ), "Symlink should point to target file"


def test_nested_directory_structure(temp_dirs, current_user):
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
    relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Verify
    assert os.path.islink(source_file), "Nested file should be a symlink"
    assert os.readlink(source_file) == target_file


def test_skip_existing_symlinks(temp_dirs, current_user, caplog):
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
        relink.replace_files_with_symlinks(source_dir, target_dir, username)

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


def test_missing_target_file(temp_dirs, current_user, caplog):
    """Test behavior when target file doesn't exist."""
    source_dir, target_dir = temp_dirs
    username = current_user

    # Create only source file (no corresponding target)
    source_file = os.path.join(source_dir, "orphan.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("orphan content")

    # Run the function
    with caplog.at_level(logging.INFO):
        relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Verify the file is NOT converted to symlink
    assert not os.path.islink(source_file), "File should not be a symlink"
    assert os.path.isfile(source_file), "Original file should still exist"

    # Check warning message
    assert "Warning: Corresponding file not found" in caplog.text


def test_invalid_username(temp_dirs, caplog):
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
        relink.replace_files_with_symlinks(source_dir, target_dir, invalid_username)

    # Check error message
    assert "Error: User" in caplog.text
    assert "not found" in caplog.text


def test_multiple_files(temp_dirs, current_user):
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
    relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Verify all files are symlinks
    for i in range(5):
        source_file = os.path.join(source_dir, f"file_{i}.txt")
        target_file = os.path.join(target_dir, f"file_{i}.txt")
        assert os.path.islink(source_file)
        assert os.readlink(source_file) == target_file


def test_absolute_paths(temp_dirs, current_user):
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
        relink.replace_files_with_symlinks(rel_source, rel_target, username)

        # Verify it still works
        assert os.path.islink(source_file)
    finally:
        os.chdir(cwd)


def test_print_searching_message(temp_dirs, current_user, caplog):
    """Test that searching message is printed."""
    source_dir, target_dir = temp_dirs
    username = current_user

    # Run the function
    with caplog.at_level(logging.INFO):
        relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Check that searching message was logged
    assert f"Searching for files owned by '{username}'" in caplog.text
    assert f"in '{os.path.abspath(source_dir)}'" in caplog.text


def test_print_found_owned_file(temp_dirs, current_user, caplog):
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
        relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Check that "Found owned file" message was logged
    assert "Found owned file:" in caplog.text
    assert source_file in caplog.text


def test_print_deleted_and_created_messages(temp_dirs, current_user, caplog):
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
        relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Check messages
    assert "Deleted original file:" in caplog.text
    assert "Created symbolic link:" in caplog.text
    assert f"{source_file} -> {target_file}" in caplog.text


def test_error_creating_symlink(temp_dirs, caplog):
    """Test error message when symlink creation fails."""
    source_dir, target_dir = temp_dirs
    username = os.environ["USER"]

    # Create source file
    source_file = os.path.join(source_dir, "test.txt")
    target_file = os.path.join(target_dir, "test.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target")

    # Mock os.symlink to raise an error
    def mock_symlink(src, dst):
        raise OSError("Simulated symlink error")

    with patch("os.symlink", side_effect=mock_symlink):
        # Run the function
        with caplog.at_level(logging.INFO):
            relink.replace_files_with_symlinks(source_dir, target_dir, username)

        # Check error message
        assert "Error creating symlink" in caplog.text
        assert source_file in caplog.text


def test_empty_directories(temp_dirs):
    """Test with empty directories."""
    source_dir, target_dir = temp_dirs
    username = os.environ["USER"]

    # Run with empty directories (should not crash)
    relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Should complete without errors
    assert True


def test_file_with_spaces_in_name(temp_dirs):
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
    relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Verify
    assert os.path.islink(source_file)
    assert os.readlink(source_file) == target_file


def test_file_with_special_characters(temp_dirs):
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
    relink.replace_files_with_symlinks(source_dir, target_dir, username)

    # Verify
    assert os.path.islink(source_file)
    assert os.readlink(source_file) == target_file


def test_error_deleting_file(temp_dirs, caplog):
    """Test error message when file deletion fails."""
    source_dir, target_dir = temp_dirs
    username = os.environ["USER"]

    # Create files
    source_file = os.path.join(source_dir, "test.txt")
    target_file = os.path.join(target_dir, "test.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target")

    # Mock os.rename to raise an error
    def mock_rename(src, dst):
        raise OSError("Simulated rename error")

    with patch("os.rename", side_effect=mock_rename):
        # Run the function
        with caplog.at_level(logging.INFO):
            relink.replace_files_with_symlinks(source_dir, target_dir, username)

        # Check error message
        assert "Error deleting file" in caplog.text
        assert source_file in caplog.text
