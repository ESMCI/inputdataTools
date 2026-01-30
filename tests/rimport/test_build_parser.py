"""
Tests for build_parser() function in rimport script.
"""

import os
import sys
import argparse
import importlib.util
from importlib.machinery import SourceFileLoader

import pytest

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
sys.modules["rimport"] = rimport
loader.exec_module(rimport)


class TestBuildParser:
    """Test suite for build_parser() function."""

    def test_parser_creation(self):
        """Test that build_parser creates an ArgumentParser."""
        parser = rimport.build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_file_argument_accepted(self):
        """Test that -file argument is accepted."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.txt"])
        assert args.file == "test.txt"
        assert args.filelist is None

    def test_list_argument_accepted(self):
        """Test that -list argument is accepted."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-list", "files.txt"])
        assert args.filelist == "files.txt"
        assert args.file is None

    def test_file_and_list_mutually_exclusive(self, capsys):
        """Test that -file and -list cannot be used together."""
        parser = rimport.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["-file", "test.txt", "-list", "files.txt"])

        # Check that the error message explains the problem
        captured = capsys.readouterr()
        stderr_lines = captured.err.strip().split("\n")
        assert "not allowed with argument" in stderr_lines[-1]

    def test_file_or_list_required(self, capsys):
        """Test that either -file or -list is required."""
        parser = rimport.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

        # Check that the error message explains the problem
        captured = capsys.readouterr()
        stderr_lines = captured.err.strip().split("\n")
        assert "error: one of the arguments" in stderr_lines[-1]

    def test_inputdata_default(self):
        """Test that -inputdata has correct default value."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "test.txt"])
        assert args.inputdata == rimport.DEFAULT_SOURCE_ROOT

    def test_inputdata_custom(self):
        """Test that -inputdata can be customized."""
        parser = rimport.build_parser()
        custom_path = "/custom/path"
        args = parser.parse_args(["-file", "test.txt", "-inputdata", custom_path])
        assert args.inputdata == custom_path

    @pytest.mark.parametrize("help_flag", ["-help", "-h", "--help"])
    def test_help_flags_show_help(self, help_flag):
        """Test that all help flag options trigger help."""
        parser = rimport.build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([help_flag])
        # Help should exit with code 0
        assert exc_info.value.code == 0

    def test_file_with_inputdata(self):
        """Test combining -file with -inputdata."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-file", "data.nc", "-inputdata", "/my/data"])
        assert args.file == "data.nc"
        assert args.inputdata == "/my/data"

    def test_list_with_inputdata(self):
        """Test combining -list with -inputdata."""
        parser = rimport.build_parser()
        args = parser.parse_args(["-list", "files.txt", "-inputdata", "/my/data"])
        assert args.filelist == "files.txt"
        assert args.inputdata == "/my/data"
