"""
Tests of replace_files_with_symlinks() in relink.py. Note that this module is focused on testing
just the logic of this function. The actual replacement and other stuff that happens in
replace_one_file_with_symlink() is tested in test_replace_one_file_with_symlink.
"""

import os
import sys
import tempfile
import pwd
import logging
from unittest.mock import patch, call
import pytest

import shared

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402


@pytest.fixture(autouse=True)
def configure_logging_for_tests():
    """Configure logging for all tests in this module."""
    shared.configure_logging(logging.INFO)
    yield
    # Cleanup
    relink.logger.handlers.clear()


@pytest.fixture(name="mock_replace_one")
def fixture_mock_replace_one():
    """Fixture that mocks relink.replace_one_file_with_symlink"""
    with patch("relink.replace_one_file_with_symlink") as mock:
        yield mock


def test_basic_file_replacement_given_dir(
    temp_dirs, current_user, mock_replace_one, caplog
):
    """Test basic functionality: given directory, replace owned file with symlink."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create a file in source directory
    source_file = os.path.join(inputdata_root, "test_file.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source content")

    # Create corresponding file in target directory
    target_file = os.path.join(target_dir, "test_file.txt")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_files_with_symlinks(
        inputdata_root, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=False,
    )

    # Verify message with filename was printed
    assert f"'{source_file}':" in caplog.text


def test_basic_file_replacement_given_file(
    temp_dirs, current_user, mock_replace_one, caplog
):
    """Test basic functionality: given owned file, replace with symlink."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create a file in source directory
    source_file = os.path.join(inputdata_root, "test_file.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source content")

    # Create corresponding file in target directory
    target_file = os.path.join(target_dir, "test_file.txt")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_files_with_symlinks(
        source_file, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=False,
    )

    # Verify message with filename was printed
    assert f"'{source_file}':" in caplog.text


def test_dry_run(temp_dirs, current_user, mock_replace_one, caplog):
    """Test that dry_run=True is passed correctly."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create a file in source directory
    source_file = os.path.join(inputdata_root, "test_file.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("source content")

    # Create corresponding file in target directory
    target_file = os.path.join(target_dir, "test_file.txt")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_files_with_symlinks(
        inputdata_root,
        target_dir,
        username,
        inputdata_root=inputdata_root,
        dry_run=True,
    )

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=True,
    )

    # Verify message with filename was printed
    assert f"'{source_file}':" in caplog.text


def test_nested_directory_structure(temp_dirs, current_user, mock_replace_one):
    """Test with nested directory structures."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create nested directories
    nested_path = os.path.join("subdir1", "subdir2")
    os.makedirs(os.path.join(inputdata_root, nested_path))
    os.makedirs(os.path.join(target_dir, nested_path))

    # Create files in nested directories
    source_file = os.path.join(inputdata_root, nested_path, "nested_file.txt")
    target_file = os.path.join(target_dir, nested_path, "nested_file.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("nested source")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("nested target")

    # Run the function
    relink.replace_files_with_symlinks(
        inputdata_root, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=False,
    )


def test_skip_existing_symlinks(temp_dirs, current_user, caplog, mock_replace_one):
    """Test that existing symlinks are skipped."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create a target file
    target_file = os.path.join(target_dir, "target.txt")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target")

    # Create a symlink in source (pointing somewhere else)
    source_link = os.path.join(inputdata_root, "existing_link.txt")
    dummy_target = os.path.join(tempfile.gettempdir(), "somewhere")
    os.symlink(dummy_target, source_link)

    # Run the function
    with caplog.at_level(logging.DEBUG):
        relink.replace_files_with_symlinks(
            inputdata_root, target_dir, username, inputdata_root=inputdata_root
        )

    # Verify replace_one_file_with_symlink() wasn't called
    mock_replace_one.assert_not_called()

    # Verify message with filename was NOT printed
    assert f"'{source_link}':" not in caplog.text


def test_missing_target_file(temp_dirs, current_user, caplog, mock_replace_one):
    """Test behavior when target file doesn't exist."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create only source file (no corresponding target)
    source_file = os.path.join(inputdata_root, "orphan.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("orphan content")

    # Run the function
    with caplog.at_level(logging.INFO):
        relink.replace_files_with_symlinks(
            inputdata_root, target_dir, username, inputdata_root=inputdata_root
        )

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=False,
    )


def test_invalid_username(temp_dirs, caplog, mock_replace_one):
    """Test behavior with invalid username."""
    inputdata_root, target_dir = temp_dirs

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
        relink.replace_files_with_symlinks(
            inputdata_root, target_dir, invalid_username, inputdata_root=inputdata_root
        )

    # Verify replace_one_file_with_symlink() wasn't called
    mock_replace_one.assert_not_called()


def test_multiple_files(temp_dirs, current_user, mock_replace_one, caplog):
    """Test with multiple files in the directory."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create multiple files
    for i in range(5):
        source_file = os.path.join(inputdata_root, f"file_{i}.txt")
        target_file = os.path.join(target_dir, f"file_{i}.txt")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write(f"source {i}")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(f"target {i}")

    # Run the function
    relink.replace_files_with_symlinks(
        inputdata_root, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() was called correctly
    calls = []
    for i in range(5):
        source_file = os.path.join(inputdata_root, f"file_{i}.txt")
        calls.append(call(inputdata_root, target_dir, source_file, dry_run=False))
    mock_replace_one.assert_has_calls(calls, any_order=True)

    # Verify message with filename was printed
    for i in range(5):
        source_file = os.path.join(inputdata_root, f"file_{i}.txt")
        assert f"'{source_file}':" in caplog.text


def test_multiple_files_nested(temp_dirs, current_user, mock_replace_one):
    """Test with multiple files scattered throughout a nested directory tree."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create nested directory structure with files at different levels
    test_files = [
        "root_file1.txt",
        "root_file2.txt",
        os.path.join("level1", "file_a.txt"),
        os.path.join("level1", "file_b.txt"),
        os.path.join("level1", "subdir", "file_c.txt"),
        os.path.join("level2", "deep", "nested", "file_d.txt"),
        os.path.join("level2", "file_e.txt"),
    ]

    # Create all files and their parent directories
    source_files = []
    for rel_path in test_files:
        source_file = os.path.join(inputdata_root, rel_path)
        source_files.append(source_file)
        target_file = os.path.join(target_dir, rel_path)

        # Create parent directories
        os.makedirs(os.path.dirname(source_file), exist_ok=True)
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        # Create files
        with open(source_file, "w", encoding="utf-8") as f:
            f.write(f"source content for {rel_path}")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(f"target content for {rel_path}")

    # Run the function
    relink.replace_files_with_symlinks(
        inputdata_root, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() was called correctly
    calls = []
    for source_file in source_files:
        calls.append(call(inputdata_root, target_dir, source_file, dry_run=False))
    mock_replace_one.assert_has_calls(calls, any_order=True)


def test_absolute_paths(temp_dirs, current_user, mock_replace_one):
    """Test that function handles relative paths by converting to absolute."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Create test files
    source_file = os.path.join(inputdata_root, "test.txt")
    target_file = os.path.join(target_dir, "test.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("test")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("test target")

    # Use relative paths (if possible)
    cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(inputdata_root))
        rel_source = os.path.basename(inputdata_root)
        rel_target = os.path.basename(target_dir)

        # Run with relative paths
        relink.replace_files_with_symlinks(
            rel_source, rel_target, username, inputdata_root=inputdata_root
        )
    finally:
        os.chdir(cwd)

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=False,
    )


def test_print_searching_message(temp_dirs, current_user, caplog):
    """Test that searching message is printed."""
    inputdata_root, target_dir = temp_dirs
    username = current_user

    # Run the function
    with caplog.at_level(logging.INFO):
        relink.replace_files_with_symlinks(
            inputdata_root, target_dir, username, inputdata_root=inputdata_root
        )

    # Check that searching message was logged
    assert f"Searching for files owned by '{username}'" in caplog.text
    assert f"in '{os.path.abspath(inputdata_root)}'" in caplog.text


def test_empty_directories(temp_dirs, mock_replace_one):
    """Test with empty directories."""
    inputdata_root, target_dir = temp_dirs
    username = os.environ["USER"]

    # Run with empty directories (should not crash)
    relink.replace_files_with_symlinks(
        inputdata_root, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() wasn't called
    mock_replace_one.assert_not_called()


def test_file_with_spaces_in_name(temp_dirs, mock_replace_one):
    """Test files with spaces in their names."""
    inputdata_root, target_dir = temp_dirs
    username = os.environ["USER"]

    # Create files with spaces
    source_file = os.path.join(inputdata_root, "file with spaces.txt")
    target_file = os.path.join(target_dir, "file with spaces.txt")

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("content")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_files_with_symlinks(
        inputdata_root, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=False,
    )


def test_file_with_special_characters(temp_dirs, mock_replace_one):
    """Test files with special characters in names."""
    inputdata_root, target_dir = temp_dirs
    username = os.environ["USER"]

    # Create files with special chars (that are valid in filenames)
    filename = "file-with_special.chars@123.txt"
    source_file = os.path.join(inputdata_root, filename)
    target_file = os.path.join(target_dir, filename)

    with open(source_file, "w", encoding="utf-8") as f:
        f.write("content")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("target content")

    # Run the function
    relink.replace_files_with_symlinks(
        inputdata_root, target_dir, username, inputdata_root=inputdata_root
    )

    # Verify replace_one_file_with_symlink() was called correctly
    mock_replace_one.assert_called_once_with(
        inputdata_root,
        target_dir,
        source_file,
        dry_run=False,
    )
