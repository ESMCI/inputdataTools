"""
Tests of find_owned_files_scandir() in relink.py
"""

import os
import sys
import tempfile
import logging

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402


def test_find_owned_files_basic(temp_dirs):
    """Test basic functionality: find files owned by user."""
    source_dir, _ = temp_dirs
    user_uid = os.stat(source_dir).st_uid

    # Create files
    file1 = os.path.join(source_dir, "file1.txt")
    file2 = os.path.join(source_dir, "file2.txt")

    with open(file1, "w", encoding="utf-8") as f:
        f.write("content1")
    with open(file2, "w", encoding="utf-8") as f:
        f.write("content2")

    # Find owned files
    found_files = list(relink.find_owned_files_scandir(source_dir, user_uid))

    # Verify both files were found
    assert len(found_files) == 2
    assert file1 in found_files
    assert file2 in found_files


def test_find_owned_files_nested(temp_dirs):
    """Test finding files in nested directory structures."""
    source_dir, _ = temp_dirs
    user_uid = os.stat(source_dir).st_uid

    # Create nested directories
    nested_path = os.path.join("subdir1", "subdir2")
    os.makedirs(os.path.join(source_dir, nested_path))

    # Create files at different levels
    file1 = os.path.join(source_dir, "root_file.txt")
    file2 = os.path.join(source_dir, "subdir1", "level1_file.txt")
    file3 = os.path.join(source_dir, nested_path, "level2_file.txt")

    for f in [file1, file2, file3]:
        with open(f, "w", encoding="utf-8") as fp:
            fp.write("content")

    # Find owned files
    found_files = list(relink.find_owned_files_scandir(source_dir, user_uid))

    # Verify all files were found
    assert len(found_files) == 3
    assert file1 in found_files
    assert file2 in found_files
    assert file3 in found_files


def test_skip_symlinks(temp_dirs, caplog):
    """Test that symlinks are skipped and logged."""
    source_dir, _ = temp_dirs
    user_uid = os.stat(source_dir).st_uid

    # Create a regular file
    regular_file = os.path.join(source_dir, "regular.txt")
    with open(regular_file, "w", encoding="utf-8") as f:
        f.write("content")

    # Create a symlink
    symlink_path = os.path.join(source_dir, "link.txt")
    dummy_target = os.path.join(tempfile.gettempdir(), "somewhere")
    os.symlink(dummy_target, symlink_path)

    # Find owned files with logging
    with caplog.at_level(logging.INFO):
        found_files = list(relink.find_owned_files_scandir(source_dir, user_uid))

    # Verify only regular file was found
    assert len(found_files) == 1
    assert regular_file in found_files
    assert symlink_path not in found_files

    # Check that "Skipping symlink" message was logged
    assert "Skipping symlink:" in caplog.text
    assert symlink_path in caplog.text


def test_empty_directory(temp_dirs):
    """Test with empty directory."""
    source_dir, _ = temp_dirs
    user_uid = os.stat(source_dir).st_uid

    # Find owned files in empty directory
    found_files = list(relink.find_owned_files_scandir(source_dir, user_uid))

    # Should return empty list
    assert len(found_files) == 0


def test_permission_error_handling(temp_dirs, caplog):
    """Test that permission errors are handled gracefully."""
    source_dir, _ = temp_dirs
    user_uid = os.stat(source_dir).st_uid

    # Create a file
    file1 = os.path.join(source_dir, "accessible.txt")
    with open(file1, "w", encoding="utf-8") as f:
        f.write("content")

    # Create a subdirectory
    subdir = os.path.join(source_dir, "subdir")
    os.makedirs(subdir)
    file2 = os.path.join(subdir, "file_in_subdir.txt")
    with open(file2, "w", encoding="utf-8") as f:
        f.write("content")

    # Remove read permission from subdirectory
    os.chmod(subdir, 0o000)

    try:
        # Find owned files with debug logging
        with caplog.at_level(logging.DEBUG):
            found_files = list(relink.find_owned_files_scandir(source_dir, user_uid))

        # Should find the accessible file but skip the inaccessible directory
        assert file1 in found_files
        assert file2 not in found_files

        # Check that error was logged at DEBUG level
        assert "Error accessing" in caplog.text
    finally:
        # Restore permissions for cleanup
        os.chmod(subdir, 0o755)


def test_only_files_not_directories(temp_dirs):
    """Test that only files are returned, not directories."""
    source_dir, _ = temp_dirs
    user_uid = os.stat(source_dir).st_uid

    # Create files and directories
    file1 = os.path.join(source_dir, "file.txt")
    with open(file1, "w", encoding="utf-8") as f:
        f.write("content")

    subdir = os.path.join(source_dir, "subdir")
    os.makedirs(subdir)

    # Find owned files
    found_files = list(relink.find_owned_files_scandir(source_dir, user_uid))

    # Should only find the file, not the directory
    assert len(found_files) == 1
    assert file1 in found_files
    assert subdir not in found_files


def test_does_not_follow_symlink_directories(temp_dirs):
    """Test that symlinked directories are not followed."""
    source_dir, _ = temp_dirs
    user_uid = os.stat(source_dir).st_uid

    # Create a real directory with a file
    real_dir = os.path.join(source_dir, "real_dir")
    os.makedirs(real_dir)
    file_in_real = os.path.join(real_dir, "file.txt")
    with open(file_in_real, "w", encoding="utf-8") as f:
        f.write("content")

    # Create a symlink to a directory outside source_dir
    external_dir = tempfile.mkdtemp()
    try:
        external_file = os.path.join(external_dir, "external.txt")
        with open(external_file, "w", encoding="utf-8") as f:
            f.write("external content")

        symlink_dir = os.path.join(source_dir, "link_to_external")
        os.symlink(external_dir, symlink_dir)

        # Find owned files
        found_files = list(relink.find_owned_files_scandir(source_dir, user_uid))

        # Should find file in real directory but not in symlinked directory
        assert file_in_real in found_files
        assert external_file not in found_files
    finally:
        # Cleanup
        os.remove(external_file)
        os.rmdir(external_dir)
