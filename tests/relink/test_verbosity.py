"""
Tests of verbosity levels in relink.py script.
"""

import os
import sys
import tempfile
import logging
from unittest.mock import patch

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402

from shared import INDENT


def test_quiet_mode_suppresses_info_messages(temp_dirs, caplog):
    """Test that quiet mode suppresses INFO level messages."""
    source_dir, target_dir = temp_dirs
    username = os.environ["USER"]

    # Create files
    source_file = os.path.join(source_dir, "test_file.txt")
    target_file = os.path.join(target_dir, "test_file.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target")

    # Create a symlink to test "Skipping symlink" message
    source_link = os.path.join(source_dir, "existing_link.txt")
    dummy_target = os.path.join(tempfile.gettempdir(), "somewhere")
    os.symlink(dummy_target, source_link)

    # Run the function with WARNING level (quiet mode)
    with caplog.at_level(logging.WARNING):
        relink.replace_files_with_symlinks(
            source_dir, target_dir, username, inputdata_root=source_dir
        )

    # Verify INFO messages are NOT in the log
    assert "Searching for files owned by" not in caplog.text
    assert "Skipping symlink:" not in caplog.text
    assert "Found owned file:" not in caplog.text
    assert f"{INDENT}Deleted original file:" not in caplog.text
    assert f"{INDENT}Created symbolic link:" not in caplog.text


def test_quiet_mode_shows_warnings(temp_dirs, caplog):
    """Test that quiet mode still shows WARNING level messages."""
    source_dir, target_dir = temp_dirs
    username = os.environ["USER"]

    # Create only source file (no corresponding target) to trigger warning
    source_file = os.path.join(source_dir, "orphan.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("orphan content")

    # Run the function with WARNING level (quiet mode)
    with caplog.at_level(logging.WARNING):
        relink.replace_files_with_symlinks(
            source_dir, target_dir, username, inputdata_root=source_dir
        )

    # Verify WARNING message IS in the log
    assert f"{INDENT}Warning: Corresponding file" in caplog.text
    assert "not found" in caplog.text


def test_quiet_mode_shows_errors(temp_dirs, caplog):
    """Test that quiet mode still shows ERROR level messages."""
    source_dir, target_dir = temp_dirs
    username = os.environ["USER"]

    # Test 1: Invalid username error
    invalid_username = "nonexistent_user_12345"
    with caplog.at_level(logging.WARNING):
        relink.replace_files_with_symlinks(
            source_dir, target_dir, invalid_username, inputdata_root=source_dir
        )
    assert "Error: User" in caplog.text
    assert "not found" in caplog.text

    # Clear the log for next test
    caplog.clear()

    # Test 2: Error deleting file
    source_file = os.path.join(source_dir, "test.txt")
    target_file = os.path.join(target_dir, "test.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target")

    def mock_rename(src, dst):
        raise OSError("Simulated rename error")

    with patch("os.rename", side_effect=mock_rename):
        with caplog.at_level(logging.WARNING):
            relink.replace_files_with_symlinks(
                source_dir, target_dir, username, inputdata_root=source_dir
            )
        assert f"{INDENT}Error deleting file" in caplog.text

    # Clear the log for next test
    caplog.clear()

    # Test 3: Error creating symlink
    source_file2 = os.path.join(source_dir, "test2.txt")
    target_file2 = os.path.join(target_dir, "test2.txt")

    with open(source_file2, "w", encoding="utf-8") as f:
        f.write("source2")
    with open(target_file2, "w", encoding="utf-8") as f:
        f.write("target2")

    def mock_symlink(src, dst):
        raise OSError("Simulated symlink error")

    with patch("os.symlink", side_effect=mock_symlink):
        with caplog.at_level(logging.WARNING):
            relink.replace_files_with_symlinks(
                source_dir, target_dir, username, inputdata_root=source_dir
            )
        assert f"{INDENT}Error creating symlink" in caplog.text
