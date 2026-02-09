"""
System tests for rimport script executed from command line.
"""

import os
import sys
import subprocess

import pytest


@pytest.fixture(name="rimport_script")
def fixture_rimport_script():
    """Return the path to the rimport script."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "rimport",
    )


@pytest.fixture(name="test_env")
def fixture_test_env(tmp_path):
    """Create test environment with inputdata and staging directories."""
    inputdata_root = tmp_path / "inputdata"
    staging_root = tmp_path / "staging"
    inputdata_root.mkdir()
    staging_root.mkdir()

    return {
        "inputdata_root": inputdata_root,
        "staging_root": staging_root,
        "tmp_path": tmp_path,
    }


@pytest.fixture(name="rimport_env")
def fixture_rimport_env(test_env):
    """Create environment dict for running rimport with test settings."""
    env = os.environ.copy()
    env["RIMPORT_STAGING"] = str(test_env["staging_root"])
    env["RIMPORT_SKIP_USER_CHECK"] = "1"
    return env


class TestRimportCommandLine:
    """System tests for rimport command-line execution."""

    def test_file_option_stages_single_file(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that -file option stages a single file."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create a file in inputdata
        test_file = inputdata_root / "test.nc"
        test_file.write_text("test data")

        # Run rimport with -file option
        command = [
            sys.executable,
            rimport_script,
            "-file",
            "test.nc",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify file was staged
        staged_file = staging_root / "test.nc"
        assert staged_file.exists()
        assert staged_file.read_text() == "test data"

        # Verify file was relinked
        assert test_file.is_symlink()
        assert test_file.resolve() == staged_file

    def test_list_option_stages_multiple_files(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that -list option stages multiple files."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]
        tmp_path = test_env["tmp_path"]

        # Create files in inputdata
        file1 = inputdata_root / "file1.nc"
        file2 = inputdata_root / "file2.nc"
        file1.write_text("data1")
        file2.write_text("data2")

        # Create filelist
        filelist = tmp_path / "filelist.txt"
        filelist.write_text("file1.nc\nfile2.nc\n")

        # Run rimport with -list option
        command = [
            sys.executable,
            rimport_script,
            "-list",
            str(filelist),
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify both files were staged
        assert (staging_root / "file1.nc").exists()
        assert (staging_root / "file2.nc").exists()
        assert (staging_root / "file1.nc").read_text() == "data1"
        assert (staging_root / "file2.nc").read_text() == "data2"

        # Verify both files were relinked
        assert file1.is_symlink()
        assert file1.resolve() == (staging_root / "file1.nc")
        assert file2.is_symlink()
        assert file2.resolve() == (staging_root / "file2.nc")

    def test_preserves_directory_structure(self, rimport_script, test_env, rimport_env):
        """Test that directory structure is preserved in staging."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create nested file
        nested_file = inputdata_root / "dir1" / "dir2" / "file.nc"
        nested_file.parent.mkdir(parents=True)
        nested_file.write_text("nested data")

        # Run rimport
        command = [
            sys.executable,
            rimport_script,
            "-file",
            "dir1/dir2/file.nc",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify directory structure is preserved
        staged_file = staging_root / "dir1" / "dir2" / "file.nc"
        assert staged_file.exists()
        assert staged_file.read_text() == "nested data"

        # Verify file was relinked
        assert nested_file.is_symlink()
        assert nested_file.resolve() == staged_file

    def test_error_for_nonexistent_file(self, rimport_script, test_env, rimport_env):
        """Test that error is reported for nonexistent file."""
        inputdata_root = test_env["inputdata_root"]

        # Run rimport with nonexistent file
        command = [
            sys.executable,
            rimport_script,
            "-file",
            "nonexistent.nc",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify error
        assert result.returncode != 0
        assert "error" in result.stderr.lower()

    def test_error_for_nonexistent_list_file(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that error is reported when list file doesn't exist."""
        inputdata_root = test_env["inputdata_root"]
        tmp_path = test_env["tmp_path"]

        # Run rimport with nonexistent list file
        command = [
            sys.executable,
            rimport_script,
            "-list",
            str(tmp_path / "nonexistent.txt"),
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify error
        assert result.returncode == 2
        assert "list file not found" in result.stderr

    def test_error_for_empty_list_file(self, rimport_script, test_env, rimport_env):
        """Test that error is reported when list file is empty."""
        inputdata_root = test_env["inputdata_root"]
        tmp_path = test_env["tmp_path"]

        # Create empty list file
        filelist = tmp_path / "empty.txt"
        filelist.write_text("")

        # Run rimport
        command = [
            sys.executable,
            rimport_script,
            "-list",
            str(filelist),
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify error
        assert result.returncode == 2
        assert "no filenames found" in result.stderr

    @pytest.mark.parametrize("help_flag", ["-help", "-h", "--help"])
    def test_help_flag_shows_help(self, rimport_script, help_flag):
        """Test that help flags show help message."""
        command = [sys.executable, rimport_script, help_flag]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        # Help should exit with code 0
        assert result.returncode == 0
        assert "usage:" in result.stdout
        # Python 3.10+ uses "options:", earlier versions use "optional arguments:"
        assert "options:" in result.stdout or "optional arguments:" in result.stdout

    def test_list_with_comments_and_blanks(self, rimport_script, test_env, rimport_env):
        """Test that list file with comments and blank lines works correctly."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]
        tmp_path = test_env["tmp_path"]

        # Create files
        file1 = inputdata_root / "file1.nc"
        file2 = inputdata_root / "file2.nc"
        file1.write_text("data1")
        file2.write_text("data2")

        # Create filelist with comments and blanks
        filelist = tmp_path / "filelist.txt"
        filelist.write_text("# Comment\nfile1.nc\n\n# Another comment\nfile2.nc\n")

        # Run rimport
        command = [
            sys.executable,
            rimport_script,
            "-list",
            str(filelist),
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify both files were staged
        assert (staging_root / "file1.nc").exists()
        assert (staging_root / "file2.nc").exists()

        # Verify both files were relinked
        assert file1.is_symlink()
        assert file1.resolve() == (staging_root / "file1.nc")
        assert file2.is_symlink()
        assert file2.resolve() == (staging_root / "file2.nc")

    def test_prints_and_exits_for_already_published_linked_file(
        self, rimport_script, test_env, rimport_env
    ):
        """
        Test that stage_data returns early with msg if file already published/linked. Note that the
        only thing this test does that the stage_data tests don't is to check that main() correctly
        passes the unresolved symlink to normalize_paths.
        """
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create a real file in staging and a symlink to it in inputdata
        real_file = staging_root / "real_file.nc"
        real_file.write_text("data")
        src = inputdata_root / "link.nc"
        src.symlink_to(real_file)

        # Run rimport with -file option
        command = [
            sys.executable,
            rimport_script,
            "-file",
            "link.nc",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify the right message was printed
        msg = "File is already published and linked"
        assert msg in result.stdout

        # Verify the WRONG message was NOT printed
        msg = "is already under staging directory"
        assert msg not in result.stdout

    def test_error_broken_symlink(self, rimport_script, test_env, rimport_env):
        """
        Test that stage_data errors with msg if file is a link w/ nonexistent target. Note that the
        only thing this test does that the stage_data tests don't is to check that main() correctly
        passes the unresolved symlink to stage_data.
        """
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create a symlink in inputdata pointing to a nonexistent file
        real_file = staging_root / "real_file.nc"
        src = inputdata_root / "link.nc"
        src.symlink_to(real_file)

        # Run rimport
        command = [
            sys.executable,
            rimport_script,
            "-file",
            "link.nc",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify failure
        assert result.returncode != 0, f"Command unexpectedly passed: {result.stdout}"

        # Verify the right message was printed
        msg = "Source is a broken symlink"
        assert msg in result.stderr

    def test_error_symlink_pointing_outside_staging(
        self, rimport_script, test_env, rimport_env
    ):
        """
        Test that stage_data errors w/ msg if file is link w/ target outside staging. Note that the
        only thing this test does that the stage_data tests don't is to check that main() correctly
        passes the unresolved symlink to stage_data.
        """
        inputdata_root = test_env["inputdata_root"]
        tmp_path = test_env["tmp_path"]

        # Create a real file outside staging and a symlink to it in inputdata
        real_file = tmp_path / "real_file.nc"
        real_file.write_text("data")
        src = inputdata_root / "link.nc"
        src.symlink_to(real_file)

        # Run rimport
        command = [
            sys.executable,
            rimport_script,
            "-file",
            "link.nc",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify failure
        assert result.returncode != 0, f"Command unexpectedly passed: {result.stdout}"

        # Verify the right message was printed
        msg = "is outside staging directory"
        assert msg in result.stderr

    def test_check_doesnt_copy(self, rimport_script, test_env, rimport_env):
        """Test that a file is NOT copied to the staging directory if check is True."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create a file in inputdata
        test_file = inputdata_root / "test.nc"
        test_file.write_text("test data")

        # Make sure --check skips ensure_running_as()
        del rimport_env["RIMPORT_SKIP_USER_CHECK"]

        # Run rimport with --check option
        command = [
            sys.executable,
            rimport_script,
            "-file",
            "test.nc",
            "-inputdata",
            str(inputdata_root),
            "--check",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify file was not staged
        staged_file = staging_root / "test.nc"
        assert not staged_file.exists()

        # Verify file was not replaced with a symlink
        assert not test_file.is_symlink()

        # Verify message was printed
        assert "not already published" in result.stdout
