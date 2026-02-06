"""
Tests for shared.py validate_directory() and validate_paths() functions.
"""

import os
import argparse

import pytest

import shared


class TestValidateDirectory:
    """Test suite for validate_directory function."""

    def test_valid_directory(self, tmp_path):
        """Test that valid directory is accepted and returns absolute path."""
        test_dir = tmp_path / "valid_dir"
        test_dir.mkdir()

        result = shared.validate_directory(str(test_dir))
        assert result == str(test_dir.resolve())

    def test_nonexistent_directory(self):
        """Test that nonexistent directory raises ArgumentTypeError."""
        nonexistent = os.path.join(os.sep, "nonexistent", "directory", "12345")

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            shared.validate_directory(nonexistent)

        assert "does not exist" in str(exc_info.value)
        assert nonexistent in str(exc_info.value)

    def test_relative_path_converted_to_absolute(self, tmp_path):
        """Test that relative paths are converted to absolute."""
        test_dir = tmp_path / "relative_test"
        test_dir.mkdir()

        # Change to parent directory and use relative path
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            result = shared.validate_directory("relative_test")
            assert os.path.isabs(result)
            assert result == str(test_dir.resolve())
        finally:
            os.chdir(cwd)

    def test_symlink_to_directory(self, tmp_path):
        """Test that symlink to a directory is accepted."""
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()

        link_dir = tmp_path / "link_dir"
        link_dir.symlink_to(real_dir)

        result = shared.validate_paths(str(link_dir))
        # validate_directory returns absolute path of the symlink itself
        assert result == str(link_dir.absolute())
        # Verify it's still a symlink
        assert os.path.islink(result)

    def test_list_with_invalid_directory(self, tmp_path):
        """Test that a list with one invalid directory raises error."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            shared.validate_paths([str(dir1), str(nonexistent)])

        assert "does not exist" in str(exc_info.value)


class TestValidatePaths:
    """Test suite for validate_paths function."""

    def test_valid_directory(self, tmp_path):
        """Test that valid directory is accepted and returns absolute path."""
        test_dir = tmp_path / "valid_dir"
        test_dir.mkdir()

        result = shared.validate_paths(str(test_dir))
        assert result == str(test_dir.resolve())

    def test_nonexistent_directory(self):
        """Test that nonexistent directory raises ArgumentTypeError."""
        nonexistent = os.path.join(os.sep, "nonexistent", "directory", "12345")

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            shared.validate_paths(nonexistent)

        assert "does not exist" in str(exc_info.value)
        assert nonexistent in str(exc_info.value)

    def test_file_instead_of_directory(self, tmp_path):
        """Test that a file path doesn't raise ArgumentTypeError (or any error)."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")

        shared.validate_paths(str(test_file))

    def test_relative_path_converted_to_absolute(self, tmp_path):
        """Test that relative paths are converted to absolute."""
        test_dir = tmp_path / "relative_test"
        test_dir.mkdir()

        # Change to parent directory and use relative path
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            result = shared.validate_paths("relative_test")
            assert os.path.isabs(result)
            assert result == str(test_dir.resolve())
        finally:
            os.chdir(cwd)

    def test_symlink_to_directory(self, tmp_path):
        """Test that symlink to a directory is accepted."""
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()

        link_dir = tmp_path / "link_dir"
        link_dir.symlink_to(real_dir)

        result = shared.validate_paths(str(link_dir))
        # validate_directory returns absolute path of the symlink itself
        assert result == str(link_dir.absolute())
        # Verify it's still a symlink
        assert os.path.islink(result)

    def test_list_with_invalid_directory(self, tmp_path):
        """Test that a list with one invalid directory raises error."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            shared.validate_paths([str(dir1), str(nonexistent)])

        assert "does not exist" in str(exc_info.value)

    def test_list_with_file_instead_of_directory(self, tmp_path):
        """Test that a list containing a file doesn't raise error."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        file1 = tmp_path / "file.txt"
        file1.write_text("content")

        shared.validate_paths([str(dir1), str(file1)])
