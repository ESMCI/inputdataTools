"""
Tests of handle_non_dir() and _handle_non_dir_entry() in relink.py
"""

# pylint: disable=protected-access

import os
import sys
import tempfile
import logging
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402


@pytest.fixture(name="mock_direntry")
def fixture_mock_direntry():
    """
    Factory fixture to create mock DirEntry objects.

    Returns:
        callable: A function that creates a mock DirEntry with specified properties.
    """

    def _create_mock(name, path, uid, is_file=True, is_symlink=False):
        """
        Create a mock DirEntry object.

        Args:
            name (str): The name of the file/directory.
            path (str): The full path to the file/directory.
            uid (int): The UID of the owner.
            is_file (bool): Whether this is a file.
            is_symlink (bool): Whether this is a symlink.

        Returns:
            Mock: A mock DirEntry object.
        """
        mock_entry = Mock(spec=os.DirEntry)
        mock_entry.name = name
        mock_entry.path = path

        mock_stat = Mock()
        mock_stat.st_uid = uid
        mock_entry.stat.return_value = mock_stat

        mock_entry.is_file.return_value = is_file
        mock_entry.is_symlink.return_value = is_symlink

        return mock_entry

    return _create_mock


class TestHandleNonDirEntry:
    """
    Tests for _handle_non_dir_entry() function.

    Logging tests are in test_verbosity.py.
    """

    def test_returns_path_for_owned_regular_file(self, temp_dirs):
        """Test that owned regular files return their path."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid

        # Create a regular file
        test_file = os.path.join(source_dir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("content")

        # Get DirEntry for the file
        with os.scandir(source_dir) as entries:
            entry = next(e for e in entries if e.name == "test.txt")
            result = relink._handle_non_dir_entry(entry, user_uid)

        assert result == test_file

    def test_returns_none_for_file_owned_by_different_user(
        self, temp_dirs, mock_direntry
    ):
        """Test that files owned by different users return None."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid
        different_uid = user_uid + 1000

        # Create a file
        test_file = os.path.join(source_dir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("content")

        # Create mock entry with different UID
        mock_entry = mock_direntry(
            "test.txt", test_file, different_uid, is_file=True, is_symlink=False
        )

        result = relink._handle_non_dir_entry(mock_entry, user_uid)

        assert result is None

    def test_returns_none_and_logs_for_owned_symlink(self, temp_dirs, caplog):
        """Test that owned symlinks return None and are logged."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid

        # Create a symlink
        symlink_path = os.path.join(source_dir, "link.txt")
        dummy_target = os.path.join(tempfile.gettempdir(), "somewhere")
        os.symlink(dummy_target, symlink_path)

        # Get DirEntry for the symlink
        with os.scandir(source_dir) as entries:
            entry = next(e for e in entries if e.name == "link.txt")

            with caplog.at_level(logging.DEBUG):
                result = relink._handle_non_dir_entry(entry, user_uid)

        assert result is None
        assert "Skipping symlink:" in caplog.text
        assert symlink_path in caplog.text

    def test_returns_none_for_symlink_owned_by_different_user(
        self, temp_dirs, caplog, mock_direntry
    ):
        """Test that symlinks owned by different users return None without logging."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid
        different_uid = user_uid + 1000

        # Create a symlink
        symlink_path = os.path.join(source_dir, "link.txt")
        dummy_target = os.path.join(tempfile.gettempdir(), "somewhere")
        os.symlink(dummy_target, symlink_path)

        # Create mock entry with different UID
        mock_entry = mock_direntry(
            "link.txt", symlink_path, different_uid, is_file=False, is_symlink=True
        )

        with caplog.at_level(logging.DEBUG):
            result = relink._handle_non_dir_entry(mock_entry, user_uid)

        assert result is None
        # Should NOT log because it's not owned by the user
        assert "Skipping symlink:" not in caplog.text

    def test_handles_file_with_spaces(self, temp_dirs):
        """Test that files with spaces in names are handled correctly."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid

        # Create a file with spaces
        test_file = os.path.join(source_dir, "file with spaces.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("content")

        # Get DirEntry for the file
        with os.scandir(source_dir) as entries:
            entry = next(e for e in entries if e.name == "file with spaces.txt")
            result = relink._handle_non_dir_entry(entry, user_uid)

        assert result == test_file

    def test_handles_file_with_special_characters(self, temp_dirs):
        """Test that files with special characters are handled correctly."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid

        # Create a file with special characters
        filename = "file-with_special.chars@123.txt"
        test_file = os.path.join(source_dir, filename)
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("content")

        # Get DirEntry for the file
        with os.scandir(source_dir) as entries:
            entry = next(e for e in entries if e.name == filename)
            result = relink._handle_non_dir_entry(entry, user_uid)

        assert result == test_file


class TestHandleNonDir:
    """Tests for handle_non_dir() function."""

    def test_works_with_direntry(self, temp_dirs):
        """Test that handle_non_dir works with os.DirEntry objects."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid

        # Create a regular file
        test_file = os.path.join(source_dir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("content")

        # Get DirEntry for the file
        with os.scandir(source_dir) as entries:
            entry = next(e for e in entries if e.name == "test.txt")
            result = relink.handle_non_dir(entry, user_uid, source_dir)

        assert result == test_file

    def test_raises_typeerror_for_int(self, temp_dirs):
        """Test that handle_non_dir raises TypeError for an integer."""
        source_dir, _ = temp_dirs
        user_uid = os.stat(source_dir).st_uid

        invalid_input = 12345
        expected_type = type(invalid_input)

        with pytest.raises(
            TypeError,
            match=f"Unsure how to handle non-directory variable of type.*{expected_type}",
        ):
            relink.handle_non_dir(invalid_input, user_uid, source_dir)
