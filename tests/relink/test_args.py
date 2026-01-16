"""
Tests related to argument parsing and processing in relink.py script.
"""

import os
import sys
import tempfile
import shutil
import logging
import argparse
from unittest.mock import patch

import pytest

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402


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
        with patch("sys.argv", ["relink.py", str(custom_source)]):
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
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "--timing"]):
            args = relink.parse_arguments()
            assert args.timing is True

    def test_timing_default(self, mock_default_dirs):
        """Test that timing defaults to False."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.timing is False


class TestValidateDirectory:
    """Test suite for validate_directory function."""

    def test_valid_directory(self, tmp_path):
        """Test that valid directory is accepted and returns absolute path."""
        test_dir = tmp_path / "valid_dir"
        test_dir.mkdir()

        result = relink.validate_directory(str(test_dir))
        assert result == str(test_dir.resolve())

    def test_nonexistent_directory(self):
        """Test that nonexistent directory raises ArgumentTypeError."""
        nonexistent = os.path.join(os.sep, "nonexistent", "directory", "12345")

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            relink.validate_directory(nonexistent)

        assert "does not exist" in str(exc_info.value)
        assert nonexistent in str(exc_info.value)

    def test_file_instead_of_directory(self, tmp_path):
        """Test that a file path raises ArgumentTypeError."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            relink.validate_directory(str(test_file))

        assert "not a directory" in str(exc_info.value)

    def test_relative_path_converted_to_absolute(self, tmp_path):
        """Test that relative paths are converted to absolute."""
        test_dir = tmp_path / "relative_test"
        test_dir.mkdir()

        # Change to parent directory and use relative path
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            result = relink.validate_directory("relative_test")
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

        result = relink.validate_directory(str(link_dir))
        # validate_directory returns absolute path of the symlink itself
        assert result == str(link_dir.absolute())
        # Verify it's still a symlink
        assert os.path.islink(result)


class TestProcessArgs:
    """Test suite for process_args function."""

    # pylint: disable=no-member

    def test_process_args_quiet_sets_warning_level(self):
        """Test that quiet flag sets log level to WARNING."""
        args = argparse.Namespace(quiet=True, verbose=False)
        relink.process_args(args)
        assert args.log_level == logging.WARNING

    def test_process_args_verbose_sets_debug_level(self):
        """Test that verbose flag sets log level to DEBUG."""
        args = argparse.Namespace(quiet=False, verbose=True)
        relink.process_args(args)
        assert args.log_level == logging.DEBUG

    def test_process_args_default_sets_info_level(self):
        """Test that default (no flags) sets log level to INFO."""
        args = argparse.Namespace(quiet=False, verbose=False)
        relink.process_args(args)
        assert args.log_level == logging.INFO

    def test_process_args_modifies_args_in_place(self):
        """Test that process_args modifies the args object in place."""
        args = argparse.Namespace(quiet=False, verbose=False)
        original_args = args
        relink.process_args(args)
        # Should be the same object, modified in place
        assert args is original_args
        assert hasattr(args, "log_level")
