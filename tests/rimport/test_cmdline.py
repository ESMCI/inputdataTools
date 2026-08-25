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
            str(test_file),
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

        # Create filelist (outside the tree: entries must be absolute)
        filelist = tmp_path / "filelist.txt"
        filelist.write_text(f"{file1}\n{file2}\n")

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

    def test_list_inside_tree_relative_entries(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a list file inside the inputdata tree anchors relative entries to the
        list file's own directory, not the inputdata root."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create nested file and a list file alongside it inside the tree
        nested_file = inputdata_root / "lnd" / "clm2" / "file1.nc"
        nested_file.parent.mkdir(parents=True)
        nested_file.write_text("nested data")

        filelist = inputdata_root / "lnd" / "filelist.txt"
        filelist.write_text("clm2/file1.nc\n")

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

        # Verify the file was staged, anchored to the list dir's own subtree
        staged_file = staging_root / "lnd" / "clm2" / "file1.nc"
        assert staged_file.exists()
        assert staged_file.read_text() == "nested data"

        # Verify file was relinked
        assert nested_file.is_symlink()
        assert nested_file.resolve() == staged_file

    def test_list_inside_tree_relative_entries_anchor_to_list_dir_not_cwd(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a list file's relative entries anchor to the list file's own directory,
        not the cwd, even when rimport is run with its cwd inside the tree at a DIFFERENT
        location. The existing e2e list test passes no cwd= to subprocess.run, so pytest's own
        (outside-the-tree) cwd applies and cwd-anchoring and list-dir-anchoring agree; this test
        sets cwd= explicitly so the two schemes can be told apart."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Real file, alongside the list file inside "lnd"
        nested_file = inputdata_root / "lnd" / "clm2" / "file1.nc"
        nested_file.parent.mkdir(parents=True)
        nested_file.write_text("real data")

        filelist = inputdata_root / "lnd" / "filelist.txt"
        filelist.write_text("clm2/file1.nc\n")

        # Decoy at the cwd-anchored location: a cwd-anchoring regression would resolve here
        # instead, giving a wrong-file failure rather than a merely-missing-file one.
        decoy_file = inputdata_root / "atm" / "clm2" / "file1.nc"
        decoy_file.parent.mkdir(parents=True)
        decoy_file.write_text("decoy data")

        # Run rimport with -list option, cwd inside the tree but at a DIFFERENT location
        # than the list file
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
            cwd=inputdata_root / "atm",
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify the real file (not the decoy) was staged, anchored to the list dir's subtree
        staged_file = staging_root / "lnd" / "clm2" / "file1.nc"
        assert staged_file.exists()
        assert staged_file.read_text() == "real data"

        # Verify file was relinked
        assert nested_file.is_symlink()
        assert nested_file.resolve() == staged_file

        # Verify the decoy was left untouched, and nothing staged at the cwd-anchored path
        assert not decoy_file.is_symlink()
        assert decoy_file.read_text() == "decoy data"
        assert not (staging_root / "atm" / "clm2" / "file1.nc").exists()

    def test_list_outside_tree_relative_entry_error(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a relative entry in a list file outside the tree is a fatal error."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]
        tmp_path = test_env["tmp_path"]

        # Create the file that would be staged if this succeeded
        test_file = inputdata_root / "file1.nc"
        test_file.write_text("data1")

        # Create filelist OUTSIDE the tree with a relative entry
        filelist = tmp_path / "filelist.txt"
        filelist.write_text("file1.nc\n")

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

        # Verify fatal error, naming both the offending entry and the list file
        assert result.returncode == 2
        assert "file1.nc" in result.stderr
        assert str(filelist.resolve()) in result.stderr

        # Verify nothing was staged or symlinked
        assert not (staging_root / "file1.nc").exists()
        assert not test_file.is_symlink()

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
            str(nested_file),
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
            str(inputdata_root / "nonexistent.nc"),
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

        # Create filelist with comments and blanks (outside the tree: entries must be absolute)
        filelist = tmp_path / "filelist.txt"
        filelist.write_text(f"# Comment\n{file1}\n\n# Another comment\n{file2}\n")

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
            str(src),
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
            str(src),
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
            str(src),
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

    def test_check_doesnt_copy_unpublished(self, rimport_script, test_env, rimport_env):
        """Test that an unpublished file is not copied to the staging directory if check is True."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create a file in inputdata
        file_basename = "test.nc"
        test_file = inputdata_root / file_basename
        test_file.write_text("test data")

        # Make sure --check skips ensure_running_as()
        del rimport_env["RIMPORT_SKIP_USER_CHECK"]

        # Run rimport with --check option
        command = [
            sys.executable,
            rimport_script,
            "-file",
            str(test_file),
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
        staged_file = staging_root / file_basename
        assert not staged_file.exists()

        # Verify file was not replaced with a symlink
        assert not test_file.is_symlink()

        # Verify message was printed
        assert "not already published" in result.stdout

        # Verify messages weren't printed
        assert "already published but NOT linked".lower() not in result.stdout.lower()
        assert "Deleted original file".lower() not in result.stdout.lower()
        assert "Created symbolic link".lower() not in result.stdout.lower()
        assert "Error creating symlink".lower() not in result.stdout.lower()

    def test_relative_file_from_inputdata_subdir_stages_that_file(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a relative positional filename anchors to cwd when rimport is run from
        inside an inputdata subdirectory, staging the file that is actually there rather than
        a same-named decoy file at the inputdata root."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        subdir = inputdata_root / "lnd" / "clm2"
        subdir.mkdir(parents=True)

        subdir_file = subdir / "test.nc"
        subdir_file.write_text("subdir data")

        decoy_file = inputdata_root / "test.nc"
        decoy_file.write_text("decoy data")

        # Run rimport with a relative positional filename, from inside the subdir
        command = [
            sys.executable,
            rimport_script,
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
            cwd=subdir,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify the subdir file (not the decoy) was staged
        staged_file = staging_root / "lnd" / "clm2" / "test.nc"
        assert staged_file.exists()
        assert staged_file.read_text() == "subdir data"

        # Verify the subdir file was relinked
        assert subdir_file.is_symlink()
        assert subdir_file.resolve() == staged_file

        # Verify the decoy at the inputdata root was left untouched
        assert not decoy_file.is_symlink()
        assert decoy_file.read_text() == "decoy data"

        # Verify nothing was staged at the root-anchored path
        assert not (staging_root / "test.nc").exists()

    def test_relative_file_from_subdir_missing_errors_no_root_fallback(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a relative positional filename run from an inputdata subdirectory errors
        when the file isn't there, rather than falling back to a same-named file at the root."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        subdir = inputdata_root / "lnd" / "clm2"
        subdir.mkdir(parents=True)

        root_file = inputdata_root / "test.nc"
        root_file.write_text("root data")

        # Run rimport with a relative positional filename, from inside the subdir
        command = [
            sys.executable,
            rimport_script,
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
            cwd=subdir,
        )

        # Verify failure
        assert result.returncode != 0, f"Command unexpectedly passed: {result.stdout}"
        assert "source not found" in result.stderr

        # Verify the root file was left untouched
        assert not root_file.is_symlink()
        assert root_file.read_text() == "root data"

        # Verify nothing was staged
        assert not any(staging_root.iterdir())

    def test_relative_file_from_outside_tree_resolves_against_root(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a relative positional filename still resolves against the inputdata root,
        as before, when rimport is run from outside the inputdata tree."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]
        tmp_path = test_env["tmp_path"]

        test_file = inputdata_root / "test.nc"
        test_file.write_text("root data")

        # Run rimport with a relative positional filename, from outside the tree
        command = [
            sys.executable,
            rimport_script,
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
            cwd=tmp_path,
        )

        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify the file was staged, resolved against the inputdata root
        staged_file = staging_root / "test.nc"
        assert staged_file.exists()
        assert staged_file.read_text() == "root data"

        # Verify file was relinked
        assert test_file.is_symlink()
        assert test_file.resolve() == staged_file

    def test_dotdot_escape_from_subdir_errors(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a '..'-escaping relative filename, anchored lexically to cwd, is rejected
        by stage_data's existing outside-the-root guardrail."""
        inputdata_root = test_env["inputdata_root"]
        tmp_path = test_env["tmp_path"]

        subdir = inputdata_root / "lnd"
        subdir.mkdir(parents=True)

        # File must exist, or the "source not found" check fires before the guardrail and the
        # "not under inputdata root" message never appears.
        outside_file = tmp_path / "outside.nc"
        outside_file.write_text("outside data")

        # Run rimport with an escaping relative positional filename, from inside the subdir
        command = [
            sys.executable,
            rimport_script,
            "../../outside.nc",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
            cwd=subdir,
        )

        # Verify failure
        assert result.returncode != 0, f"Command unexpectedly passed: {result.stdout}"
        assert "not under inputdata root" in result.stderr

        # Verify the outside file was left untouched
        assert not outside_file.is_symlink()
        assert outside_file.read_text() == "outside data"

    def test_dotdot_escape_from_list_inside_tree_errors(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that a '..'-escaping relative entry in a list file INSIDE the tree is rejected
        by stage_data's existing outside-the-root guardrail. This is the list-side twin of
        test_dotdot_escape_from_subdir_errors above."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]
        tmp_path = test_env["tmp_path"]

        list_dir = inputdata_root / "lnd"
        list_dir.mkdir(parents=True)

        # File must exist, or the "source not found" check fires before the guardrail and the
        # "not under inputdata root" message never appears.
        outside_file = tmp_path / "outside.nc"
        outside_file.write_text("outside data")

        # List file INSIDE the tree, with an entry that escapes the tree
        filelist = list_dir / "filelist.txt"
        filelist.write_text("../../outside.nc\n")

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

        # Verify failure
        assert result.returncode == 1, f"Command unexpectedly passed: {result.stdout}"
        assert "not under inputdata root" in result.stderr

        # Verify nothing was staged
        assert not any(staging_root.rglob("*"))

        # Verify the outside file was left untouched
        assert not outside_file.is_symlink()
        assert outside_file.read_text() == "outside data"

    def test_check_doesnt_relink_published(self, rimport_script, test_env, rimport_env):
        """Test that published file is not relinked if check is True."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        # Create a file in inputdata and staging
        file_basename = "test.nc"
        test_file = inputdata_root / file_basename
        test_file.write_text("test data")
        staged_file = staging_root / file_basename
        staged_file.write_text("test data")

        # Make sure --check skips ensure_running_as()
        del rimport_env["RIMPORT_SKIP_USER_CHECK"]

        # Run rimport with --check option
        command = [
            sys.executable,
            rimport_script,
            "-file",
            str(test_file),
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

        # Verify file was not replaced with a symlink
        assert not test_file.is_symlink()

        # Verify message was printed
        assert "already published but NOT linked".lower() in result.stdout.lower()

        # Verify messages weren't printed
        assert "linking now".lower() not in result.stdout.lower()
        assert "Deleted original file".lower() not in result.stdout.lower()
        assert "Created symbolic link".lower() not in result.stdout.lower()
        assert "Error creating symlink".lower() not in result.stdout.lower()

    def test_directory_argument_from_subdir_errors_and_leaves_tree_intact(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that pointing rimport at a directory (e.g. via the cwd-anchored positional from
        inside an inputdata subdir) errors cleanly instead of falling into the destructive
        replace-with-symlink path, which would rename the directory to '<name>.tmp', symlink it
        away, and then fail to roll back."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        subdir = inputdata_root / "lnd" / "clm2"
        subdir.mkdir(parents=True)
        inner_file = subdir / "data.nc"
        inner_file.write_text("clm2 data")

        # The matching staging mirror must ALSO exist as a directory, or dst.exists() is False
        # and stage_data takes the harmless "not already published" branch instead of the
        # destructive one — this is the fixture detail that makes the bug actually bite.
        staging_mirror = staging_root / "lnd" / "clm2"
        staging_mirror.mkdir(parents=True)

        # Run rimport with a relative positional directory name, from inside the parent dir
        command = [
            sys.executable,
            rimport_script,
            "clm2",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
            cwd=subdir.parent,
        )

        # Verify failure
        assert result.returncode != 0, f"Command unexpectedly passed: {result.stdout}"
        assert "directory" in result.stderr
        assert "not a file" in result.stderr

        # Verify the tree is intact: clm2 is still a real directory, not a symlink; no
        # '<name>.tmp' path was left anywhere under inputdata_root; and its contents are
        # untouched.
        assert subdir.is_dir() and not subdir.is_symlink(), (
            f"clm2 should still be a plain, non-symlink directory after the error; "
            f"is_dir={subdir.is_dir()} is_symlink={subdir.is_symlink()}"
        )
        tmp_paths = list(inputdata_root.rglob("*.tmp"))
        assert not tmp_paths, f"Found unexpected '.tmp' path(s) left behind: {tmp_paths}"
        assert inner_file.read_text() == "clm2 data"

    def test_empty_string_argument_errors_and_leaves_tree_intact(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that an empty-string positional (as from an unset shell variable, e.g.
        `rimport "$maybe_unset"`) errors cleanly instead of anchoring to the inputdata root
        itself and running that root through the destructive replace-with-symlink path."""
        inputdata_root = test_env["inputdata_root"]
        # staging_root itself need not be assigned here — the fixture already created it, and
        # its mere existence is what makes dst.exists() true for rel="." (see the brief: this is
        # what turns an unset shell variable into a whole-tree rename).

        marker_file = inputdata_root / "marker.nc"
        marker_file.write_text("root marker")

        # Run rimport with an empty-string positional, from inside the inputdata root itself,
        # so it anchors (via _anchor_cli) to the root — the same as an unset shell variable
        # expanding to "".
        command = [
            sys.executable,
            rimport_script,
            "",
            "-inputdata",
            str(inputdata_root),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=rimport_env,
            cwd=inputdata_root,
        )

        # Verify failure
        assert result.returncode != 0, f"Command unexpectedly passed: {result.stdout}"
        assert "directory" in result.stderr
        assert "not a file" in result.stderr

        # Verify the inputdata root itself is untouched: still a real directory, not renamed,
        # not replaced with a symlink, no '.tmp' sibling.
        assert inputdata_root.is_dir() and not inputdata_root.is_symlink(), (
            f"inputdata root should still be a plain, non-symlink directory after the error; "
            f"is_dir={inputdata_root.is_dir()} is_symlink={inputdata_root.is_symlink()}"
        )
        tmp_siblings = list(inputdata_root.parent.glob(f"{inputdata_root.name}.tmp"))
        assert not tmp_siblings, f"Found unexpected '.tmp' sibling(s): {tmp_siblings}"
        assert marker_file.read_text() == "root marker"

    def test_check_directory_argument_reports_error_not_publishable(
        self, rimport_script, test_env, rimport_env
    ):
        """Test that --check on a directory argument reports it as an error, rather than
        claiming (as it did before the guard) that the directory is already published but not
        linked and available for download."""
        inputdata_root = test_env["inputdata_root"]
        staging_root = test_env["staging_root"]

        subdir = inputdata_root / "lnd" / "clm2"
        subdir.mkdir(parents=True)
        inner_file = subdir / "data.nc"
        inner_file.write_text("clm2 data")

        # Matching staging mirror, as in the destructive-path test above.
        staging_mirror = staging_root / "lnd" / "clm2"
        staging_mirror.mkdir(parents=True)

        command = [
            sys.executable,
            rimport_script,
            "clm2",
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
            cwd=subdir.parent,
        )

        # Verify failure
        assert result.returncode != 0, f"Command unexpectedly passed: {result.stdout}"
        assert "directory" in result.stderr
        assert "not a file" in result.stderr

        # Verify --check does NOT claim the directory is already published / downloadable
        assert "already published" not in result.stdout.lower()
        assert "available for download" not in result.stdout.lower()

        # Verify the tree is intact
        assert subdir.is_dir() and not subdir.is_symlink()
        assert not list(inputdata_root.rglob("*.tmp"))
        assert inner_file.read_text() == "clm2 data"
