"""
Tests related to argument parsing and processing in relink.py script.
"""

import os
import sys
from pathlib import Path
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


class TestParseArguments:
    """Test suite for parse_arguments function."""

    def test_default_arguments(self, temp_dirs):
        """Test that default arguments are used when none provided."""
        source_dir, target_dir = temp_dirs
        with patch("sys.argv", ["relink.py", source_dir]):
            args = relink.parse_arguments()
            assert args.source_root == [source_dir]
            assert args.target_root == target_dir

    def test_custom_source_root(self, temp_dirs):
        """Test custom source root argument."""
        source_dir, target_dir = temp_dirs
        custom_source = Path(os.path.join(source_dir, "custom_source"))
        custom_source.mkdir()
        with patch("sys.argv", ["relink.py", str(custom_source)]):
            args = relink.parse_arguments()
            assert args.source_root == [str(custom_source.resolve())]
            assert args.target_root == target_dir

    def test_custom_target_root(self, temp_dirs):
        """Test custom target root argument."""
        source_dir, target_dir = temp_dirs
        custom_target = Path(os.path.join(target_dir, "custom_target"))
        custom_target.mkdir()
        with patch("sys.argv", ["relink.py", "--target-root", str(custom_target)]):
            args = relink.parse_arguments()
            assert args.source_root == [source_dir]
            assert args.target_root == str(custom_target.resolve())

    def test_both_custom_paths(self, temp_dirs):
        """Test both custom source and target roots."""
        source_root, target_root = temp_dirs
        source_dir = Path(os.path.join(source_root, "custom_source"))
        target_dir = Path(os.path.join(target_root, "custom_target"))
        source_dir.mkdir()
        target_dir.mkdir()
        with patch(
            "sys.argv",
            [
                "relink.py",
                str(source_dir),
                "--target-root",
                str(target_dir),
            ],
        ):
            args = relink.parse_arguments()
            assert args.source_root == [str(source_dir.resolve())]
            assert args.target_root == str(target_dir.resolve())

    def test_verbose_flag(self, temp_dirs):  # pylint: disable=unused-argument
        """Test that --verbose flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "--verbose"]):
            args = relink.parse_arguments()
            assert args.verbose is True
            assert args.quiet is False

    def test_quiet_flag(self, temp_dirs):  # pylint: disable=unused-argument
        """Test that --quiet flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "--quiet"]):
            args = relink.parse_arguments()
            assert args.quiet is True
            assert args.verbose is False

    def test_verbose_short_flag(self, temp_dirs):  # pylint: disable=unused-argument
        """Test that -v flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "-v"]):
            args = relink.parse_arguments()
            assert args.verbose is True

    def test_quiet_short_flag(self, temp_dirs):  # pylint: disable=unused-argument
        """Test that -q flag is parsed correctly."""
        with patch("sys.argv", ["relink.py", "-q"]):
            args = relink.parse_arguments()
            assert args.quiet is True

    def test_default_verbosity(self, temp_dirs):  # pylint: disable=unused-argument
        """Test that default verbosity has both flags as False."""
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.verbose is False
            assert args.quiet is False

    def test_verbose_and_quiet_mutually_exclusive(self, temp_dirs):
        """Test that --verbose and --quiet cannot be used together."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "--verbose", "--quiet"]):
            with pytest.raises(SystemExit) as exc_info:
                relink.parse_arguments()
            # Mutually exclusive arguments cause SystemExit with code 2
            assert exc_info.value.code == 2

    def test_verbose_and_quiet_short_flags_mutually_exclusive(self, temp_dirs):
        """Test that -v and -q cannot be used together."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "-v", "-q"]):
            with pytest.raises(SystemExit) as exc_info:
                relink.parse_arguments()
            # Mutually exclusive arguments cause SystemExit with code 2
            assert exc_info.value.code == 2

    def test_dry_run_flag(self, temp_dirs):
        """Test that --dry-run flag is parsed correctly."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "--dry-run"]):
            args = relink.parse_arguments()
            assert args.dry_run is True

    def test_dry_run_default(self, temp_dirs):
        """Test that dry_run defaults to False."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.dry_run is False

    def test_timing_flag(self, temp_dirs):
        """Test that --timing flag is parsed correctly."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py", "--timing"]):
            args = relink.parse_arguments()
            assert args.timing is True

    def test_timing_default(self, temp_dirs):
        """Test that timing defaults to False."""
        # pylint: disable=unused-argument
        with patch("sys.argv", ["relink.py"]):
            args = relink.parse_arguments()
            assert args.timing is False

    def test_multiple_source_roots(self, temp_dirs):
        """Test that multiple source root arguments are parsed correctly."""
        inputdata_root, target_dir = temp_dirs
        source1 = Path(os.path.join(inputdata_root, "source1"))
        source2 = Path(os.path.join(inputdata_root, "source2"))
        source3 = Path(os.path.join(inputdata_root, "source3"))
        source1.mkdir()
        source2.mkdir()
        source3.mkdir()

        with patch("sys.argv", ["relink.py", str(source1), str(source2), str(source3)]):
            args = relink.parse_arguments()
            assert len(args.source_root) == 3
            assert str(source1.resolve()) in args.source_root
            assert str(source2.resolve()) in args.source_root
            assert str(source3.resolve()) in args.source_root
            assert args.target_root == target_dir

    def test_multiple_source_roots_with_target(self, temp_dirs):
        """Test multiple source roots with custom target root."""
        inputdata_root, target_dir = temp_dirs
        source1 = Path(os.path.join(inputdata_root, "source1"))
        source2 = Path(os.path.join(inputdata_root, "source2"))
        target = Path(os.path.join(target_dir, "target"))
        source1.mkdir()
        source2.mkdir()
        target.mkdir()

        with patch(
            "sys.argv",
            [
                "relink.py",
                str(source1),
                str(source2),
                "--target-root",
                str(target),
            ],
        ):
            args = relink.parse_arguments()
            assert len(args.source_root) == 2
            assert str(source1.resolve()) in args.source_root
            assert str(source2.resolve()) in args.source_root
            assert args.target_root == str(target.resolve())


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

    def test_list_with_invalid_directory(self, tmp_path):
        """Test that a list with one invalid directory raises error."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            relink.validate_directory([str(dir1), str(nonexistent)])

        assert "does not exist" in str(exc_info.value)

    def test_list_with_file_instead_of_directory(self, tmp_path):
        """Test that a list containing a file raises error."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        file1 = tmp_path / "file.txt"
        file1.write_text("content")

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            relink.validate_directory([str(dir1), str(file1)])

        assert "not a directory" in str(exc_info.value)


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

    def test_error_if_source_not_in_inputdata(self):
        """Test that process_args errors if source isn't in inputdata_root."""
        args = argparse.Namespace(
            quiet=False, verbose=False, source_root="abc123", inputdata_root="def456"
        )
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            relink.process_args(args)
        assert "not under inputdata root" in str(exc_info.value)

    def test_error_if_target_in_inputdata(self):
        """Test that process_args errors if target is in inputdata_root."""
        inputdata_root = "inputdata"
        target_root = os.path.join(inputdata_root, "abc123")
        args = argparse.Namespace(
            quiet=False,
            verbose=False,
            target_root=target_root,
            inputdata_root=inputdata_root,
        )
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            relink.process_args(args)
        assert "must not be under inputdata root" in str(exc_info.value)
