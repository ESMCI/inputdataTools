"""
Tests for main() function in rimport script.

These tests focus on the logic and control flow in main(), mocking out
the helper functions to isolate main()'s behavior.
"""

import os
import importlib.util
from importlib.machinery import SourceFileLoader
from unittest.mock import patch, call
import pytest

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


class TestMain:
    """Test suite for main() function."""

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_single_file_success(
        self,
        _mock_ensure_running_as,
        mock_normalize_paths,
        mock_get_staging_root,
        mock_stage_data,
        mock_validate_source_path,
        tmp_path,
        caplog,
    ):
        """Test main() logic flow when a single file stages successfully."""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        mock_get_staging_root.return_value = staging_root
        test_file = inputdata_root / "test.nc"
        mock_normalize_paths.return_value = [test_file]
        # test_file doesn't exist on disk; bypass pre-flight so this test still exercises only
        # main()'s control flow, not validate_source_path's real checks.
        mock_validate_source_path.return_value = None

        # Run
        # Absolute -file removes cwd coupling entirely: get_files_to_process runs for real here
        # (unmocked), and a relative name would anchor to the pytest invocation dir, not tmp_path.
        result = rimport.main(
            ["-file", str(test_file), "-inputdata", str(inputdata_root)]
        )

        # Verify
        assert result == 0
        mock_normalize_paths.assert_called_once_with(inputdata_root, [str(test_file)])
        check = False
        mock_stage_data.assert_called_once_with(
            test_file, inputdata_root, staging_root, check
        )
        assert "No need to run relink.py" in caplog.text

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "read_filelist")
    @patch.object(rimport, "ensure_running_as")
    def test_file_list_success(
        self,
        _mock_ensure_running_as,
        mock_read_filelist,
        mock_normalize_paths,
        mock_get_staging_root,
        mock_stage_data,
        mock_validate_source_path,
        tmp_path,
    ):
        """Test main() logic flow when a file list stages successfully."""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()
        filelist = inputdata_root / "files.txt"
        filelist.write_text("file1.nc\nfile2.nc\n")

        mock_get_staging_root.return_value = staging_root
        mock_read_filelist.return_value = ["file1.nc", "file2.nc"]
        file1 = inputdata_root / "file1.nc"
        file2 = inputdata_root / "file2.nc"
        mock_normalize_paths.return_value = [file1, file2]
        # Neither file exists on disk; bypass pre-flight so this test still exercises only
        # main()'s control flow, not validate_source_path's real checks.
        mock_validate_source_path.return_value = None

        # Run
        result = rimport.main(
            ["-list", str(filelist), "-inputdata", str(inputdata_root)]
        )

        # Verify
        assert result == 0
        mock_read_filelist.assert_called_once_with(filelist)
        mock_normalize_paths.assert_called_once_with(
            inputdata_root,
            [
                str(inputdata_root.resolve() / "file1.nc"),
                str(inputdata_root.resolve() / "file2.nc"),
            ],
        )
        assert mock_stage_data.call_count == 2
        check = False
        mock_stage_data.assert_has_calls(
            [
                call(file1, inputdata_root, staging_root, check),
                call(file2, inputdata_root, staging_root, check),
            ]
        )

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_stage_data_exception_handling(
        self,
        _mock_ensure_running_as,
        mock_normalize_paths,
        _mock_get_staging_root,
        mock_stage_data,
        mock_validate_source_path,
        tmp_path,
        capsys,
    ):
        """Test that main() handles exceptions from stage_data and continues processing."""
        # Setup
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        file1 = inputdata_root / "file1.nc"
        file2 = inputdata_root / "file2.nc"
        file3 = inputdata_root / "file3.nc"
        mock_normalize_paths.return_value = [file1, file2, file3]
        # None of the files exist on disk; bypass pre-flight so this test still exercises only
        # main()'s per-file error handling, not validate_source_path's real checks.
        mock_validate_source_path.return_value = None

        # Make stage_data fail for file2 but succeed for others
        def stage_data_side_effect(src, *_args, **_kwargs):
            if src == file2:
                raise RuntimeError("Test error for file2")

        mock_stage_data.side_effect = stage_data_side_effect

        # Run
        result = rimport.main(["-file", "test.nc", "-inputdata", str(inputdata_root)])

        # Verify
        assert result == 1  # Should return 1 because of error
        assert mock_stage_data.call_count == 3  # All files should be attempted

        # Check that error was printed to stderr
        captured = capsys.readouterr()
        assert "error processing" in captured.err
        assert "Test error for file2" in captured.err

        # Check that message about not needing to run relink was NOT printed
        assert "No need to run relink.py" not in captured.err
        assert "No need to run relink.py" not in captured.out

    @patch.object(rimport, "ensure_running_as")
    def test_nonexistent_inputdata_directory(
        self, _mock_ensure_running_as, tmp_path, capsys
    ):
        """Test that argument parser rejects nonexistent inputdata directory."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(SystemExit) as exc_info:
            rimport.main(["-file", "test.nc", "-inputdata", str(nonexistent)])

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "does not exist" in captured.err

    @patch.object(rimport, "ensure_running_as")
    def test_nonexistent_filelist(self, _mock_ensure_running_as, tmp_path, capsys):
        """Test that main() returns error code 2 for nonexistent file list."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        nonexistent_list = tmp_path / "nonexistent.txt"

        result = rimport.main(
            ["-list", str(nonexistent_list), "-inputdata", str(inputdata_root)]
        )

        assert result == 2
        captured = capsys.readouterr()
        assert "list file not found" in captured.err

    @patch.object(rimport, "read_filelist")
    @patch.object(rimport, "ensure_running_as")
    def test_empty_filelist(
        self, _mock_ensure_running_as, mock_read_filelist, tmp_path, capsys
    ):
        """Test that main() returns error code 2 for empty file list."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        filelist = tmp_path / "empty.txt"
        filelist.write_text("")

        mock_read_filelist.return_value = []

        result = rimport.main(
            ["-list", str(filelist), "-inputdata", str(inputdata_root)]
        )

        assert result == 2
        captured = capsys.readouterr()
        assert "no filenames found in list" in captured.err

    @patch.object(rimport, "ensure_running_as")
    def test_requires_file_or_filelist(self, _mock_ensure_running_as, tmp_path, capsys):
        """Test that main() returns error code 2 if neither file nor filelist provided."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        result = rimport.main(["-inputdata", str(inputdata_root)])

        assert result == 2
        captured = capsys.readouterr()
        assert "At least one of --file or --filelist is required" in captured.err

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_check_mode_calls(
        self,
        mock_ensure_running_as,
        mock_normalize_paths,
        mock_get_staging_root,
        mock_stage_data,
        mock_validate_source_path,
        tmp_path,
        caplog,
    ):
        """Test that --check mode skips the user check but does call stage_data."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        mock_get_staging_root.return_value = staging_root
        test_file = inputdata_root / "test.nc"
        mock_normalize_paths.return_value = [test_file]
        # test_file doesn't exist on disk; bypass pre-flight (which runs in --check mode too)
        # so this test still exercises only main()'s control flow.
        mock_validate_source_path.return_value = None

        result = rimport.main(
            ["-file", "test.nc", "-inputdata", str(inputdata_root), "--check"]
        )

        assert result == 0
        # ensure_running_as should NOT be called in check mode
        mock_ensure_running_as.assert_not_called()
        # stage_data should be called with check=True
        check = True
        mock_stage_data.assert_called_once_with(
            test_file, inputdata_root, staging_root, check
        )
        # Message about relink.py should not have been printed
        assert "No need to run relink.py" not in caplog.text

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_skip_user_check_env_var(
        self,
        mock_ensure_running_as,
        mock_normalize_paths,
        _mock_get_staging_root,
        _mock_stage,
        mock_validate_source_path,
        tmp_path,
        monkeypatch,
    ):
        """Test that RIMPORT_SKIP_USER_CHECK=1 skips the user check."""
        monkeypatch.setenv("RIMPORT_SKIP_USER_CHECK", "1")

        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        test_file = inputdata_root / "test.nc"
        mock_normalize_paths.return_value = [test_file]
        # test_file doesn't exist on disk; bypass pre-flight so this test still exercises only
        # the user-check skip logic.
        mock_validate_source_path.return_value = None

        result = rimport.main(["-file", "test.nc", "-inputdata", str(inputdata_root)])

        assert result == 0
        # ensure_running_as should NOT be called when env var is set
        mock_ensure_running_as.assert_not_called()

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_prints_file_path_before_processing(
        self,
        _mock_ensure_running_as,
        mock_normalize_paths,
        _mock_get_staging_root,
        _mock_stage,
        mock_validate_source_path,
        tmp_path,
        capsys,
    ):
        """Test that main() prints each file path before processing."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        file1 = inputdata_root / "file1.nc"
        file2 = inputdata_root / "file2.nc"
        mock_normalize_paths.return_value = [file1, file2]
        # Neither file exists on disk; bypass pre-flight so this test still exercises only the
        # per-file print, not validate_source_path's real checks.
        mock_validate_source_path.return_value = None

        result = rimport.main(["-file", "test.nc", "-inputdata", str(inputdata_root)])

        assert result == 0
        captured = capsys.readouterr()
        # Check that file paths are printed with quotes
        assert f"'{file1}':" in captured.out
        assert f"'{file2}':" in captured.out

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_multiple_errors_returns_1(
        self,
        _mock_ensure_running_as,
        mock_normalize_paths,
        _mock_get_staging_root,
        mock_stage_data,
        mock_validate_source_path,
        tmp_path,
    ):
        """Test that main() returns 1 when multiple files fail."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        file1 = inputdata_root / "file1.nc"
        file2 = inputdata_root / "file2.nc"
        file3 = inputdata_root / "file3.nc"
        mock_normalize_paths.return_value = [file1, file2, file3]
        # None of the files exist on disk; bypass pre-flight so this test still exercises the
        # per-file loop's runtime-error handling, not validate_source_path's real checks.
        mock_validate_source_path.return_value = None

        # Make all files fail
        mock_stage_data.side_effect = RuntimeError("Test error")

        result = rimport.main(["-file", "test.nc", "-inputdata", str(inputdata_root)])

        assert result == 1
        assert mock_stage_data.call_count == 3

    @patch.object(rimport, "validate_source_path")
    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_error_counter_increments_correctly(
        self,
        _mock_ensure_running_as,
        mock_normalize_paths,
        _mock_get_staging_root,
        mock_stage_data,
        mock_validate_source_path,
        tmp_path,
        capsys,
    ):
        """Test that the error counter increments for each failed file."""
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()

        files = [inputdata_root / f"file{i}.nc" for i in range(5)]
        mock_normalize_paths.return_value = files
        # None of the files exist on disk; bypass pre-flight so this test still exercises only
        # the per-file error counter, not validate_source_path's real checks.
        mock_validate_source_path.return_value = None

        # Make files 1 and 3 fail
        def stage_data_side_effect(src, *_args, **_kwargs):
            if src in [files[1], files[3]]:
                raise RuntimeError(f"Test error for {src.name}")

        mock_stage_data.side_effect = stage_data_side_effect

        result = rimport.main(["-file", "test.nc", "-inputdata", str(inputdata_root)])

        assert result == 1
        captured = capsys.readouterr()
        # Should have 2 error messages
        assert captured.err.count("error processing") == 2

    @patch.object(rimport, "replace_one_file_with_symlink")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_error_if_file_already_published_but_relink_fails(
        self,
        _mock_ensure_running_as,
        mock_normalize_paths,
        mock_get_staging_root,
        _mock_replace_one_file_with_symlink,
        tmp_path,
        capsys,
    ):
        """
        Test that main() returns error code 1 if attempting to relink an already-published file
        fails.
        """
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filename = "test.nc"
        src = inputdata_root / filename
        src.write_text("some data")
        assert src.exists()
        dst = staging_root / filename
        dst.write_text("some data")

        mock_get_staging_root.return_value = staging_root
        test_file = inputdata_root / filename
        mock_normalize_paths.return_value = [test_file]

        result = rimport.main(["-inputdata", str(inputdata_root), str(src)])

        assert result == 1
        captured = capsys.readouterr()
        assert "rimport: error processing" in captured.err
        assert "Error relinking during rimport" in captured.err

    @patch.object(rimport, "replace_one_file_with_symlink")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "normalize_paths")
    @patch.object(rimport, "ensure_running_as")
    def test_error_if_file_newly_published_but_relink_fails(
        self,
        _mock_ensure_running_as,
        mock_normalize_paths,
        mock_get_staging_root,
        _mock_replace_one_file_with_symlink,
        tmp_path,
        capsys,
    ):
        """
        Test that main() returns error code 1 if attempting to relink a newly-published file
        fails.
        """
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()

        filename = "test.nc"
        src = inputdata_root / filename
        src.write_text("some data")
        assert src.exists()

        mock_get_staging_root.return_value = staging_root
        test_file = inputdata_root / filename
        mock_normalize_paths.return_value = [test_file]

        result = rimport.main(["-inputdata", str(inputdata_root), str(src)])

        assert result == 1
        captured = capsys.readouterr()
        assert "rimport: error processing" in captured.err
        assert "Error relinking during rimport" in captured.err

    @patch.object(rimport, "stage_data")
    @patch.object(rimport, "get_staging_root")
    @patch.object(rimport, "ensure_running_as")
    def test_preflight_gate_rejects_whole_batch_and_never_calls_stage_data(
        self,
        _mock_ensure_running_as,
        mock_get_staging_root,
        mock_stage_data,
        tmp_path,
        capsys,
    ):
        """Test main()'s pre-flight gate: a batch with a mix of valid and invalid paths returns
        2, logs every failure, and never calls stage_data — not even for the valid path.

        Unlike the other main() tests in this file, this one does NOT mock
        validate_source_path (or normalize_paths): it lets the real pre-flight gate run
        against real files, so it is actually exercising the gate rather than assuming it
        works.
        """
        inputdata_root = tmp_path / "inputdata"
        inputdata_root.mkdir()
        staging_root = tmp_path / "staging"
        staging_root.mkdir()
        mock_get_staging_root.return_value = staging_root

        valid = inputdata_root / "good.nc"
        valid.write_text("data")
        missing = inputdata_root / "missing.nc"
        bad_dir = inputdata_root / "adir"
        bad_dir.mkdir()

        result = rimport.main(
            [
                "-inputdata",
                str(inputdata_root),
                str(valid),
                str(missing),
                str(bad_dir),
            ]
        )

        assert result == 2
        mock_stage_data.assert_not_called()

        captured = capsys.readouterr()
        assert "2 of 3 file(s) failed pre-flight validation" in captured.err
        assert f"source not found: {missing}" in captured.err
        assert f"source is a directory, not a file: {bad_dir}" in captured.err

        # The valid file was never staged or turned into a symlink.
        assert not (staging_root / "good.nc").exists()
        assert not valid.is_symlink()
