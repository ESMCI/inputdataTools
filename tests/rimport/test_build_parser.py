"""
Tests for build_parser() function in rimport script.
"""

import os
import argparse
import importlib.util
from importlib.machinery import SourceFileLoader

import pytest

import shared

# Import rimport module from file without .py extension
rimport_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "rimport",
)
loader = SourceFileLoader("rimport", rimport_path)
spec = importlib.util.spec_from_loader("rimport", loader)
if spec is None:
    raise ImportError(f"Could not create spec for rimport from {rimport_path}")
rimport = importlib.util.module_from_spec(spec)
# Don't add to sys.modules to avoid conflict with other test files
loader.exec_module(rimport)


@pytest.fixture(scope="function", autouse=True)
def fixture_temp_inputdata(temp_dirs):
    """
    Override rimport's DEFAULT_INPUTDATA_ROOT to ensure portability.

    We can't do it in tests/conftest.py's temp_dirs fixture because of how rimport is imported here;
    we'd get "no module rimport" errors. However, we can use the tempdir that got set up in that
    fixture.
    """
    rimport.DEFAULT_INPUTDATA_ROOT = shared.DEFAULT_INPUTDATA_ROOT


class TestBuildParser:
    """Test suite for build_parser() function."""

    def test_parser_creation(self):
        """Test that build_parser creates an ArgumentParser."""
        parser = rimport.build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    @pytest.mark.parametrize("file_flag", ["-file", "-f", "--file"])
    def test_file_arguments_accepted(self, file_flag):
        """Test that all file argument flags are accepted."""
        parser = rimport.build_parser()
        args = parser.parse_args([file_flag, "test.txt"])
        assert args.file == "test.txt"
        assert args.filelist is None

    @pytest.mark.parametrize("list_flag", ["-list", "-l", "--list"])
    def test_list_arguments_accepted(self, list_flag):
        """Test that all list argument flags are accepted."""
        parser = rimport.build_parser()
        args = parser.parse_args([list_flag, "files.txt"])
        assert args.filelist == "files.txt"
        assert args.file is None

    @pytest.mark.parametrize(
        "inputdata_flag",
        ["-inputdata", "-i", "--inputdata", "--inputdata-root", "-inputdata-root"],
    )
    def test_inputdata_arguments_accepted(self, temp_dirs, inputdata_flag):
        """Test that all inputdata argument flags are accepted."""
        inputdata_root, _ = temp_dirs
        parser = rimport.build_parser()
        args = parser.parse_args(
            [inputdata_flag, inputdata_root, "-f", "dummy_file.nc"]
        )
        assert args.inputdata_root == inputdata_root

    def test_file_and_list_not_mutually_exclusive(self, capsys):
        """Test that -file and -list can be used together."""
        parser = rimport.build_parser()
        file = "test.txt"
        filelist = "files.txt"
        args = parser.parse_args(["-file", file, "-list", filelist])
        assert args.file == file
        assert args.filelist == filelist
        assert args.items_to_process == []

    def test_positional_items_to_process(self):
        """Test that positional items_to_process are accepted"""
        parser = rimport.build_parser()
        items_to_process = ["abc123", "def456"]
        args = parser.parse_args(items_to_process)
        assert args.file is None
        assert args.filelist is None
        assert args.items_to_process == items_to_process

    def test_file_and_list_ok_with_items_to_process(self):
        """Test that -file and -list can be used together with items_to_process"""
        parser = rimport.build_parser()
        file = "test.txt"
        filelist = "files.txt"
        items_to_process = ["abc123", "def456"]
        args = parser.parse_args(["-file", file, "-list", filelist, *items_to_process])
        assert args.file == file
        assert args.filelist == filelist
        assert args.items_to_process == items_to_process

    def test_inputdata_default(self):
        """Test that -inputdata has correct default value."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.txt"])
        assert args.inputdata_root == str(rimport.DEFAULT_INPUTDATA_ROOT)

    def test_check_default(self):
        """Test that --check has the correct default value."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.txt"])
        assert args.check is False

    @pytest.mark.parametrize("check_flag", ["-check", "-c", "--check"])
    def test_check_arguments_accepted(self, check_flag):
        """Test that all check argument flags are accepted."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.txt", check_flag])
        assert args.check is True

    def test_inputdata_custom(self, temp_dirs):
        """Test that -inputdata can be customized."""
        parser = rimport.build_parser()
        inputdata_root, _ = temp_dirs
        custom_path = os.path.join(inputdata_root, "custom", "path")
        os.makedirs(custom_path)
        args = parser.parse_args(["-file", "test.txt", "-inputdata", custom_path])
        assert args.inputdata_root == custom_path

    @pytest.mark.parametrize("help_flag", ["-help", "-h", "--help"])
    def test_help_flags_show_help(self, help_flag):
        """Test that all help flag options trigger help."""
        parser = rimport.build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([help_flag])
        # Help should exit with code 0
        assert exc_info.value.code == 0

    def test_file_with_inputdata(self, temp_dirs):
        """Test combining -file with -inputdata."""
        parser = rimport.build_parser()
        inputdata_root, _ = temp_dirs
        custom_path = os.path.join(inputdata_root, "custom", "path2")
        os.makedirs(custom_path)
        args = parser.parse_args(["-file", "data.nc", "-inputdata", custom_path])
        assert args.file == "data.nc"
        assert args.inputdata_root == custom_path

    def test_list_with_inputdata(self, temp_dirs):
        """Test combining -list with -inputdata."""
        parser = rimport.build_parser()
        inputdata_root, _ = temp_dirs
        custom_path = os.path.join(inputdata_root, "custom", "path3")
        os.makedirs(custom_path)
        args = parser.parse_args(["-list", "files.txt", "-inputdata", custom_path])
        assert args.filelist == "files.txt"
        assert args.inputdata_root == custom_path

    def test_quiet_default(self):
        """Test that quiet defaults to False."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.nc"])
        assert args.quiet is False

    def test_verbose_default(self):
        """Test that verbose defaults to False."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.nc"])
        assert args.verbose is False

    @pytest.mark.parametrize("quiet_flag", ["-q", "--quiet"])
    def test_quiet_arguments_accepted(self, quiet_flag):
        """Test that all quiet argument flags are accepted."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.nc", quiet_flag])
        assert args.quiet is True
        assert args.verbose is False

    @pytest.mark.parametrize("verbose_flag", ["-v", "--verbose"])
    def test_verbose_arguments_accepted(self, verbose_flag):
        """Test that all verbose argument flags are accepted."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.nc", verbose_flag])
        assert args.verbose is True
        assert args.quiet is False

    def test_quiet_and_verbose_mutually_exclusive(self, capsys):
        """Test that -q and -v cannot be used together."""
        parser = rimport.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["-file", "test.nc", "-q", "-v"])

        # Check that the error message explains the problem
        captured = capsys.readouterr()
        stderr_lines = captured.err.strip().split("\n")
        assert "not allowed with argument" in stderr_lines[-1]
