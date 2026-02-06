"""
Tests for relink.py --dry-run option.
"""

import os
import sys
import logging
from unittest.mock import patch

import pytest

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402

from shared import INDENT


@pytest.fixture(name="dry_run_setup")
def fixture_dry_run_setup(temp_dirs):
    """Set up directories and files for dry-run tests."""
    source_dir, target_dir = temp_dirs
    username = os.environ["USER"]

    # Create files
    source_file = os.path.join(source_dir, "test_file.txt")
    target_file = os.path.join(target_dir, "test_file.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source content")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    return source_dir, target_dir, source_file, target_file, username


def test_dry_run_no_changes(dry_run_setup, caplog):
    """Test that dry-run mode makes no actual changes."""
    source_dir, target_dir, source_file, _, username = dry_run_setup

    # Get original file info
    with open(source_file, "r", encoding="utf-8") as f:
        original_content = f.read()
    original_is_link = os.path.islink(source_file)

    # Run in dry-run mode
    with caplog.at_level(logging.INFO):
        relink.replace_files_with_symlinks(
            source_dir, target_dir, username, inputdata_root=source_dir, dry_run=True
        )

    # Verify no changes were made
    assert os.path.isfile(source_file), "Original file should still exist"
    assert not os.path.islink(source_file), "File should not be a symlink"
    with open(source_file, "r", encoding="utf-8") as f:
        assert f.read() == original_content
    assert os.path.islink(source_file) == original_is_link


def test_dry_run_shows_message(dry_run_setup, caplog):
    """Test that dry-run mode shows what would be done."""
    source_dir, target_dir, source_file, target_file, username = dry_run_setup

    # Run in dry-run mode
    with caplog.at_level(logging.INFO):
        relink.replace_files_with_symlinks(
            source_dir, target_dir, username, inputdata_root=source_dir, dry_run=True
        )

    # Check that dry-run messages were logged
    assert "DRY RUN MODE" in caplog.text
    assert f"{INDENT}[DRY RUN] Would create symbolic link:" in caplog.text
    assert f"{source_file} -> {target_file}" in caplog.text


def test_dry_run_no_delete_or_create_messages(dry_run_setup, caplog):
    """Test that dry-run doesn't show delete/create messages."""
    source_dir, target_dir, _, _, username = dry_run_setup

    # Run in dry-run mode
    with caplog.at_level(logging.INFO):
        relink.replace_files_with_symlinks(
            source_dir, target_dir, username, inputdata_root=source_dir, dry_run=True
        )

    # Verify actual operation messages are NOT logged
    assert f"{INDENT}Deleted original file:" not in caplog.text
    assert f"{INDENT}Created symbolic link:" not in caplog.text
    # But the dry-run message should be there
    assert f"{INDENT}[DRY RUN] Would create symbolic link: " in caplog.text
