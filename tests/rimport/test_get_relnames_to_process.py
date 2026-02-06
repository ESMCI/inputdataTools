"""
Tests for main() function in rimport script.

These tests focus on the logic and control flow in main(), mocking out
the helper functions to isolate main()'s behavior.
"""

import os
import importlib.util
from importlib.machinery import SourceFileLoader

# pylint: disable=too-many-arguments,too-many-positional-arguments

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
# Don't add to sys.modules to avoid conflict with other test files (patches here not being applied)
loader.exec_module(rimport)


class TestGetRelnamesToProcess:
    """Test suite for get_relnames_to_process() function."""

    def test_single_file_relpath(self, tmp_path):
        """Test giving it a single file by its relative path"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filename = "test.nc"
        test_file = inputdata_root / filename
        test_file.write_text("abc123")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename, filelist=None
        )

        # Verify
        assert result == 0
        assert files_to_process == [filename]

    def test_single_file_abspath(self, tmp_path):
        """Test giving it a single file by its absolute path"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filename = "test.nc"
        test_file = inputdata_root / filename
        test_file.write_text("abc123")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=test_file, filelist=None
        )

        # Verify
        assert result == 0
        assert files_to_process == [test_file]

    def test_filelist_relpath_with_relpaths(self, tmp_path):
        """Test giving it a file list by its relative path, containing relative paths"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filenames = []
        for i in range(2):
            filename = f"test{i}.txt"
            filenames.append(filename)
            (inputdata_root / filename).write_text("def567")

        filelist = tmp_path / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")
        filelist_relpath = filelist.relative_to(os.getcwd(), walk_up=True)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None, filelist=filelist_relpath
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_filelist_abspath_with_relpaths(self, tmp_path):
        """Test giving it a file list by its absolute path, containing relative paths"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filenames = []
        for i in range(2):
            filename = f"test{i}.txt"
            filenames.append(filename)
            (inputdata_root / filename).write_text("def567")

        filelist = tmp_path / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None, filelist=filelist
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_filelist_relpath_with_abspaths(self, tmp_path):
        """Test giving it a file list by its relative path, containing absolute paths"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filenames = []
        for i in range(2):
            filename = inputdata_root / f"test{i}.txt"
            filenames.append(str(filename))
            filename.write_text("def567")

        filelist = tmp_path / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")
        filelist_relpath = filelist.relative_to(os.getcwd(), walk_up=True)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None, filelist=filelist_relpath
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_filelist_abspath_with_abspaths(self, tmp_path):
        """Test giving it a file list by its absolute path, containing absolute paths"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filenames = []
        for i in range(2):
            filename = inputdata_root / f"test{i}.txt"
            filenames.append(str(filename))
            filename.write_text("def567")

        filelist = tmp_path / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None, filelist=filelist
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_filelist_not_found(self):
        """Test giving it a file list that doesn't exist"""
        filelist = "bsfearirn"
        assert not os.path.exists(filelist)
        files_to_process, result = rimport.get_files_to_process(
            file=None, filelist=filelist
        )
        assert result == 2
        assert files_to_process is None

    def test_filelist_empty(self, tmp_path):
        """Test giving it an empty file list"""
        filelist = tmp_path / "bsfearirn"
        filelist.write_text("")
        files_to_process, result = rimport.get_files_to_process(
            file=None, filelist=filelist
        )
        assert result == 2
        assert files_to_process is None

    def test_single_file_and_list(self, tmp_path):
        """Test giving it a single file by its relative path"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filename = "test.nc"
        test_file = inputdata_root / filename
        test_file.write_text("abc123")

        filenames = []
        for i in range(2):
            f = f"test{i}.txt"
            filenames.append(f)
            (inputdata_root / f).write_text("def567")

        filelist = tmp_path / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename, filelist=filelist
        )

        # Verify
        assert result == 0
        assert files_to_process == [filename] + filenames

    def test_single_or_list_required(self):
        """Test that either file or filelist is required"""
        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None, filelist=None
        )

        # Verify
        assert result == 2
        assert files_to_process is None
