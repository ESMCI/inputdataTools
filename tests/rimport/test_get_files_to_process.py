"""
Tests for get_files_to_process function in rimport script.
"""

import os
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

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

    def test_single_file_relpath(self, tmp_path, monkeypatch):
        """Test giving it a single file by its relative path"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filename = "test.nc"
        test_file = inputdata_root / filename
        test_file.write_text("abc123")

        # cwd outside the inputdata tree: relative name stays unanchored
        monkeypatch.chdir(tmp_path)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
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
            file=test_file,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [test_file]

    def test_filelist_relpath_with_relpaths(self, tmp_path):
        """Test giving it a file list (outside tree) by its relative path, containing relative
        paths: fatal error, since the list file is outside the inputdata tree"""
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
        filelist_relpath = os.path.relpath(filelist)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist_relpath,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 2
        assert files_to_process is None

    def test_filelist_abspath_with_relpaths(self, tmp_path):
        """Test giving it a file list (outside tree) by its absolute path, containing relative
        paths: fatal error, since the list file is outside the inputdata tree"""
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
            file=None,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 2
        assert files_to_process is None

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
        filelist_relpath = os.path.relpath(filelist)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist_relpath,
            items_to_process=None,
            inputdata_root=inputdata_root,
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
            file=None,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_list_inside_tree_relative_entries_anchored_to_list_dir(self, tmp_path):
        """Test that relative entries in a list file inside the tree anchor to the list file's
        own directory, not the inputdata root"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        list_dir = inputdata_root / "lnd"
        list_dir.mkdir(parents=True)

        filenames = ["clm2/file1.nc", "file2.nc"]
        filelist = list_dir / "filelist.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        list_dir_resolved = list_dir.resolve()
        assert files_to_process == [str(list_dir_resolved / f) for f in filenames]

    def test_list_at_root_relative_entries_anchored_to_root(self, tmp_path):
        """Test that a list file located at the inputdata root itself (root counts as inside the
        tree) anchors relative entries to the root"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        filenames = ["test0.txt", "test1.txt"]
        filelist = inputdata_root / "filelist.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        root_resolved = inputdata_root.resolve()
        assert files_to_process == [str(root_resolved / f) for f in filenames]

    def test_list_outside_tree_relative_entry_errors(self, tmp_path, caplog):
        """Test that a relative entry in a list file outside the tree is a fatal error"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        filelist = tmp_path / "filelist.txt"
        filelist.write_text("relative_file.nc\n", encoding="utf8")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 2
        assert files_to_process is None
        assert "relative_file.nc" in caplog.text
        assert str(filelist.resolve()) in caplog.text

    def test_list_outside_tree_absolute_entries_ok(self, tmp_path):
        """Test that a list file outside the tree still works when all entries are absolute"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        filenames = []
        for i in range(2):
            filename = inputdata_root / f"test{i}.txt"
            filenames.append(str(filename))
            filename.write_text("def567")

        filelist = tmp_path / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_filelist_not_found(self, tmp_path):
        """Test giving it a file list that doesn't exist"""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        filelist = "bsfearirn"
        assert not os.path.exists(filelist)
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )
        assert result == 2
        assert files_to_process is None

    def test_filelist_empty(self, tmp_path):
        """Test giving it an empty file list"""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        filelist = tmp_path / "bsfearirn"
        filelist.write_text("")
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=[],
            inputdata_root=inputdata_root,
        )
        assert result == 2
        assert files_to_process is None

    def test_items_to_process_abspaths(self, tmp_path):
        """Test giving it a list of absolute paths in items_to_process"""
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

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=filenames,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_items_to_process_relpaths(self, tmp_path, monkeypatch):
        """Test giving it a list of relative paths in items_to_process"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        filenames = []
        for i in range(2):
            filename = inputdata_root / f"test{i}.txt"
            filenames.append(os.path.basename(filename))
            filename.write_text("def567")

        # cwd outside the inputdata tree: relative names stay unanchored
        monkeypatch.chdir(tmp_path)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=filenames,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_items_to_process_mixpaths(self, tmp_path, monkeypatch):
        """Test giving it a list of absolute and relative paths in items_to_process"""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        filenames = []
        for i in range(2):
            filename = inputdata_root / f"test{i}.txt"
            filenames.append(os.path.basename(filename))
            filename.write_text("def567")
        for i in range(2):
            filename = inputdata_root / f"test{2*i}.txt"
            filenames.append(str(filename))
            filename.write_text("def567")
        assert len(filenames) == 4

        # cwd outside the inputdata tree: relative names stay unanchored
        monkeypatch.chdir(tmp_path)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=filenames,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_single_file_and_list(self, tmp_path, monkeypatch):
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

        filelist = inputdata_root / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # cwd outside the inputdata tree: relative `file` name stays unanchored
        monkeypatch.chdir(tmp_path)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=filelist,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [filename] + [
            str(inputdata_root.resolve() / f) for f in filenames
        ]

    def test_single_or_filelist_or_list_required(self, tmp_path):
        """Test that at least one of file, filelist, items_to_process is required"""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 2
        assert files_to_process is None

    def test_cli_file_relative_cwd_inside_tree(self, tmp_path, monkeypatch):
        """Test that a relative --file name anchors to cwd when cwd is inside the tree"""
        inputdata_root = tmp_path / "inputdata"
        subdir = inputdata_root / "sub"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)
        cwd = Path.cwd().resolve()

        filename = "test.nc"

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(cwd / filename)]

    def test_cli_items_relative_cwd_inside_tree(self, tmp_path, monkeypatch):
        """Test that relative items_to_process names anchor to cwd when cwd is inside the tree"""
        inputdata_root = tmp_path / "inputdata"
        subdir = inputdata_root / "sub"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)
        cwd = Path.cwd().resolve()

        filenames = ["test0.txt", "test1.txt"]

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=filenames,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(cwd / f) for f in filenames]

    def test_cli_relative_cwd_outside_tree_unchanged(self, tmp_path, monkeypatch):
        """Test that a relative --file name is left unchanged when cwd is outside the tree"""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        monkeypatch.chdir(outside)

        filename = "test.nc"

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [filename]

    def test_cli_cwd_equals_root_anchors_to_root(self, tmp_path, monkeypatch):
        """Test that cwd == inputdata root counts as inside the tree"""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        monkeypatch.chdir(inputdata_root)
        cwd = Path.cwd().resolve()

        filename = "test.nc"

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(cwd / filename)]

    def test_cli_absolute_unchanged_cwd_inside_tree(self, tmp_path, monkeypatch):
        """Test that an absolute --file name is left unchanged even when cwd is inside the tree"""
        inputdata_root = tmp_path / "inputdata"
        subdir = inputdata_root / "sub"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        abs_file = str(inputdata_root / "other" / "test.nc")

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=abs_file,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [abs_file]

    def test_cli_cwd_inside_tree_via_symlink(self, tmp_path, monkeypatch):
        """Test that a relative name anchors to the real (resolved) cwd when cwd was reached
        through a symlink into the tree."""
        inputdata_root = tmp_path / "inputdata"
        real_sub = inputdata_root / "sub"
        real_sub.mkdir(parents=True)
        link = tmp_path / "link"
        link.symlink_to(real_sub)
        monkeypatch.chdir(link)

        filename = "test.nc"

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=None,
            items_to_process=None,
            inputdata_root=inputdata_root,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(real_sub.resolve() / filename)]
