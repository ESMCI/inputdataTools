"""
Tests for get_files_to_process function in rimport script.
"""

import logging
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

        # A relative name always anchors to cwd
        monkeypatch.chdir(inputdata_root)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=None,
            items_to_process=None,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(inputdata_root.resolve() / filename)]

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
        )

        # Verify
        assert result == 0
        assert files_to_process == [test_file]

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
        )

        # Verify
        assert result == 0
        list_dir_resolved = list_dir.resolve()
        assert files_to_process == [str(list_dir_resolved / f) for f in filenames]

    def test_list_relative_entries_anchor_to_list_dir_not_cwd(self, tmp_path, monkeypatch):
        """Test that relative list entries anchor to the list file's own directory even when
        the cwd is inside the tree at a DIFFERENT location. This is the discriminating setup:
        every other list test runs with cwd outside the tree, where cwd-anchoring and
        list-dir-anchoring agree and so can't tell the two schemes apart."""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        atm_dir = inputdata_root / "atm"
        list_dir = inputdata_root / "lnd"
        atm_dir.mkdir(parents=True)
        list_dir.mkdir(parents=True)

        # Real file, alongside the list file's own subtree
        real_file = list_dir / "clm2" / "file1.nc"
        real_file.parent.mkdir(parents=True)
        real_file.write_text("real data")

        # Decoy at the cwd-anchored location: a cwd-anchoring regression would resolve here
        # instead, giving a wrong-file failure rather than a merely-missing-file one.
        decoy_file = atm_dir / "clm2" / "file1.nc"
        decoy_file.parent.mkdir(parents=True)
        decoy_file.write_text("decoy data")

        filelist = list_dir / "filelist.txt"
        filelist.write_text("clm2/file1.nc\n", encoding="utf8")

        # cwd inside the tree, but at a different location than the list file
        monkeypatch.chdir(atm_dir)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(real_file.resolve())]

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
        )

        # Verify
        assert result == 0
        root_resolved = inputdata_root.resolve()
        assert files_to_process == [str(root_resolved / f) for f in filenames]

    def test_list_outside_tree_relative_entry_anchors_to_list_dir(self, tmp_path, monkeypatch):
        """Test that a relative entry in a list file OUTSIDE the tree now anchors to the list
        file's own directory instead of erroring (the deleted root-fallback used to make this a
        fatal error). Discriminating setup: cwd is neither the list dir nor the inputdata root,
        so the assertion can distinguish list-dir-anchoring from cwd-anchoring and from the
        (now-impossible) root-anchoring."""
        # Setup
        list_dir = tmp_path / "outside" / "listdir"
        list_dir.mkdir(parents=True)
        filelist = list_dir / "filelist.txt"
        filelist.write_text("relative_file.nc\n", encoding="utf8")

        elsewhere = tmp_path / "outside" / "elsewhere"
        elsewhere.mkdir(parents=True)
        monkeypatch.chdir(elsewhere)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str((list_dir / "relative_file.nc").resolve())]

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
        )

        # Verify
        assert result == 0
        assert files_to_process == filenames

    def test_filelist_not_found(self, tmp_path):
        """Test giving it a file list that doesn't exist"""
        filelist = "bsfearirn"
        assert not os.path.exists(filelist)
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=None,
        )
        assert result == 2
        assert files_to_process is None

    def test_filelist_empty(self, tmp_path):
        """Test giving it an empty file list"""
        filelist = tmp_path / "bsfearirn"
        filelist.write_text("")
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=filelist,
            items_to_process=[],
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

        # A relative name always anchors to cwd
        monkeypatch.chdir(inputdata_root)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=filenames,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(inputdata_root.resolve() / f) for f in filenames]

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

        # A relative name always anchors to cwd; absolute names are unaffected
        monkeypatch.chdir(inputdata_root)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=filenames,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(inputdata_root.resolve() / f) for f in filenames[:2]] + (
            filenames[2:]
        )

    def test_single_file_and_list(self, tmp_path, monkeypatch):
        """Test giving it a single file by its relative path together with a list file.
        Discriminating setup: cwd is a SUBDIRECTORY of inputdata_root, distinct from the list
        file's own directory (inputdata_root itself), so the test pins cwd-anchoring for the
        relative `file` and list-dir-anchoring for the list entries at once, and can tell the
        two apart."""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()
        subdir = inputdata_root / "sub"
        subdir.mkdir()

        filename = "test.nc"
        test_file = subdir / filename
        test_file.write_text("abc123")

        filenames = []
        for i in range(2):
            f = f"test{i}.txt"
            filenames.append(f)
            (inputdata_root / f).write_text("def567")

        filelist = inputdata_root / "file_list.txt"
        filelist.write_text("\n".join(filenames), encoding="utf8")

        # cwd is inside the tree, but at the subdir, not the list file's own directory
        monkeypatch.chdir(subdir)

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=filelist,
            items_to_process=None,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(subdir.resolve() / filename)] + [
            str(inputdata_root.resolve() / f) for f in filenames
        ]

    def test_single_or_filelist_or_list_required(self, tmp_path):
        """Test that at least one of file, filelist, items_to_process is required"""
        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=None,
            filelist=None,
            items_to_process=None,
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
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(cwd / f) for f in filenames]

    def test_cli_relative_cwd_outside_tree_still_anchors_to_cwd(self, tmp_path, monkeypatch):
        """Test that a relative --file name anchors to cwd even when cwd is outside the
        inputdata tree: there is no inside/outside distinction any more, one rule applies
        everywhere, with no root-relative fallback."""
        outside = tmp_path / "outside"
        outside.mkdir()
        monkeypatch.chdir(outside)

        filename = "test.nc"

        # Run
        files_to_process, result = rimport.get_files_to_process(
            file=filename,
            filelist=None,
            items_to_process=None,
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(outside.resolve() / filename)]

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
        )

        # Verify
        assert result == 0
        assert files_to_process == [str(real_sub.resolve() / filename)]

    def test_deleted_cwd_with_absolute_names_still_works(self, tmp_path, monkeypatch, caplog):
        """Test that a deleted cwd does not raise: absolute names are returned unchanged since
        cwd is irrelevant to resolving them. Simulates a deleted cwd for real (not mocked): chdir
        into a directory, then remove it out from under the process (confirmed to actually raise
        FileNotFoundError from Path.cwd() on this platform before writing this test)."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        abs_file = str(inputdata_root / "test.nc")

        deleted_dir = tmp_path / "deleted"
        deleted_dir.mkdir()
        monkeypatch.chdir(deleted_dir)
        deleted_dir.rmdir()

        # Run
        with caplog.at_level(logging.WARNING):
            files_to_process, result = rimport.get_files_to_process(
                file=abs_file,
                filelist=None,
                items_to_process=None,
            )

        # Verify
        assert result == 0
        assert files_to_process == [abs_file]
        # No warning: the cwd being undeterminable doesn't matter for absolute names
        assert "working directory" not in caplog.text.lower()

    def test_deleted_cwd_with_relative_name_errors(self, tmp_path, monkeypatch, caplog):
        """Test that a deleted cwd is now a FATAL error for relative names, rather than falling
        back to root-relative resolution: with no fallback, there is nothing left to anchor a
        relative name against. Confirms rc 2, files_to_process is None, and that the error
        message names the offending relative name."""
        filename = "test.nc"

        deleted_dir = tmp_path / "deleted"
        deleted_dir.mkdir()
        monkeypatch.chdir(deleted_dir)
        deleted_dir.rmdir()

        # Run
        with caplog.at_level(logging.ERROR):
            files_to_process, result = rimport.get_files_to_process(
                file=filename,
                filelist=None,
                items_to_process=None,
            )

        # Verify
        assert result == 2
        assert files_to_process is None
        assert filename in caplog.text
        assert "working directory" in caplog.text.lower()

    def test_deleted_cwd_with_multiple_relative_names_reports_all(
        self, tmp_path, monkeypatch, caplog
    ):
        """Test that when a deleted cwd leaves several relative names unresolvable, the error
        message names ALL of them, not just the first -- Sam's stated preference is to fail
        before doing anything and name every offending input, not just one."""
        filename = "test.nc"
        item_names = ["a.txt", "b.txt"]

        deleted_dir = tmp_path / "deleted"
        deleted_dir.mkdir()
        monkeypatch.chdir(deleted_dir)
        deleted_dir.rmdir()

        # Run
        with caplog.at_level(logging.ERROR):
            files_to_process, result = rimport.get_files_to_process(
                file=filename,
                filelist=None,
                items_to_process=item_names,
            )

        # Verify
        assert result == 2
        assert files_to_process is None
        assert filename in caplog.text
        for item_name in item_names:
            assert item_name in caplog.text
