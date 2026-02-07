"""
Tests of replace_one_file_with_symlink() in relink.py
"""

import os
import sys
import logging
from unittest.mock import patch

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402

from shared import INDENT


def test_basic_file_replacement(temp_dirs):
    """Test basic functionality: replace owned file with symlink."""
    source_dir, target_dir = temp_dirs

    # Create a file in source directory
    source_file = os.path.join(source_dir, "test_file.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source content")

    # Create corresponding file in target directory
    target_file = os.path.join(target_dir, "test_file.txt")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

    # Verify the source file is now a symlink
    assert os.path.islink(source_file), "Source file should be a symlink"
    assert (
        os.readlink(source_file) == target_file
    ), "Symlink should point to target file"


def test_nested_directory_structure(temp_dirs):
    """Test with nested directory structures."""
    source_dir, target_dir = temp_dirs

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
    relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

    # Verify
    assert os.path.islink(source_file), "Nested file should be a symlink"
    assert os.readlink(source_file) == target_file


def test_missing_target_file(temp_dirs, caplog):
    """Test behavior when target file doesn't exist."""
    source_dir, target_dir = temp_dirs

    # Create only source file (no corresponding target)
    source_file = os.path.join(source_dir, "orphan.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("orphan content")

    # Run the function
    with caplog.at_level(logging.INFO):
        relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

    # Verify the file is NOT converted to symlink
    assert not os.path.islink(source_file), "File should not be a symlink"
    assert os.path.isfile(source_file), "Original file should still exist"

    # Check warning message
    assert f"{INDENT}Warning: Corresponding file " in caplog.text
    assert " not found" in caplog.text


def test_absolute_paths(temp_dirs):
    """Test that function handles relative paths by converting to absolute."""
    source_dir, target_dir = temp_dirs

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
        relink.replace_one_file_with_symlink(rel_source, rel_target, source_file)

        # Verify it still works
        assert os.path.islink(source_file)
    finally:
        os.chdir(cwd)


def test_no_print_found_owned_file(temp_dirs, caplog):
    """Test that message with filename is printed."""
    source_dir, target_dir = temp_dirs

    # Create a file owned by current user
    source_file = os.path.join(source_dir, "owned_file.txt")
    target_file = os.path.join(target_dir, "owned_file.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("content")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    with caplog.at_level(logging.INFO):
        relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

    # Check that message was NOT logged (should happen in replace_files_with_symlinks instead)
    assert f"'{source_file}':" not in caplog.text


def test_print_deleted_and_created_messages(temp_dirs, caplog):
    """Test that deleted and created symlink messages are printed."""
    source_dir, target_dir = temp_dirs

    # Create files
    source_file = os.path.join(source_dir, "test_file.txt")
    target_file = os.path.join(target_dir, "test_file.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target")

    # Run the function
    with caplog.at_level(logging.INFO):
        relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

    # Check messages
    assert f"{INDENT}Deleted original file:" in caplog.text
    assert f"{INDENT}Created symbolic link:" in caplog.text
    assert f"{source_file} -> {target_file}" in caplog.text


def test_error_creating_symlink(temp_dirs, caplog):
    """Test error message when symlink creation fails."""
    source_dir, target_dir = temp_dirs

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
            relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

        # Check error message
        assert f"{INDENT}Error creating symlink" in caplog.text
        assert source_file in caplog.text


def test_file_with_spaces_in_name(temp_dirs):
    """Test files with spaces in their names."""
    source_dir, target_dir = temp_dirs

    # Create files with spaces
    source_file = os.path.join(source_dir, "file with spaces.txt")
    target_file = os.path.join(target_dir, "file with spaces.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("content")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

    # Verify
    assert os.path.islink(source_file)
    assert os.readlink(source_file) == target_file


def test_file_with_special_characters(temp_dirs):
    """Test files with special characters in names."""
    source_dir, target_dir = temp_dirs

    # Create files with special chars (that are valid in filenames)
    filename = "file-with_special.chars@123.txt"
    source_file = os.path.join(source_dir, filename)
    target_file = os.path.join(target_dir, filename)

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("content")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

    # Verify
    assert os.path.islink(source_file)
    assert os.readlink(source_file) == target_file


def test_error_deleting_file(temp_dirs, caplog):
    """Test error message when file deletion fails."""
    source_dir, target_dir = temp_dirs

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
            relink.replace_one_file_with_symlink(source_dir, target_dir, source_file)

        # Check error message
        assert f"{INDENT}Error deleting file" in caplog.text
        assert source_file in caplog.text
