"""
Tests for relink.py script as called from command line
"""

import os
import sys
import subprocess
from pathlib import Path

import pytest

from shared import INDENT


@pytest.fixture(name="mock_dirs")
def fixture_mock_dirs(tmp_path):
    """Create temporary directories and files for command-line testing."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # Create a test file
    source_file = source_dir / "test_file.txt"
    target_file = target_dir / "test_file.txt"
    source_file.write_text("source content")
    target_file.write_text("target content")

    return source_dir, target_dir, source_file, target_file


@pytest.fixture(name="nested_mock_dirs")
def fixture_nested_mock_dirs(tmp_path):
    """Create a nested source/target layout for testing relative-path resolution
    from inside an inputdata subdirectory."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_sub_dir = source_dir / "sub"
    target_sub_dir = target_dir / "sub"
    source_sub_dir.mkdir(parents=True)
    target_sub_dir.mkdir(parents=True)

    # Create a test file
    source_file = source_sub_dir / "test_file.txt"
    target_file = target_sub_dir / "test_file.txt"
    source_file.write_text("source content")
    target_file.write_text("target content")

    return source_dir, target_dir, source_sub_dir, source_file, target_file


def test_command_line_execution_dry_run(mock_dirs):
    """Test executing relink.py from command line with --dry-run flag."""
    source_dir, target_dir, source_file, _ = mock_dirs

    # Get the path to relink.py
    relink_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "relink.py",
    )

    # Build the command
    command = [
        sys.executable,
        relink_script,
        str(source_dir),
        "--target-root",
        str(target_dir),
        "--dry-run",
        "--inputdata-root",
        str(source_dir),
    ]

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    # Verify the command executed successfully
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Verify dry-run messages in output
    assert "DRY RUN MODE" in result.stdout
    assert f"{INDENT}[DRY RUN] Would create symbolic link:" in result.stdout

    # Verify no actual changes were made
    assert source_file.is_file()
    assert not source_file.is_symlink()


def test_command_line_execution_given_dir(mock_dirs):
    """Test executing relink.py from command line given a directory."""
    source_dir, target_dir, source_file, target_file = mock_dirs

    # Get the path to relink.py
    relink_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "relink.py",
    )

    # Build the command
    command = [
        sys.executable,
        relink_script,
        str(source_dir),
        "--target-root",
        str(target_dir),
        "-inputdata",
        str(source_dir),
    ]

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    # Verify the command executed successfully
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Verify the file was converted to a symlink
    assert source_file.is_symlink()
    assert os.readlink(str(source_file)) == str(target_file)

    # Verify success messages in output
    assert f"{INDENT}Created symbolic link:" in result.stdout


def test_command_line_execution_given_file(mock_dirs):
    """Test executing relink.py from command line given a file."""
    source_dir, target_dir, source_file, target_file = mock_dirs

    # Get the path to relink.py
    relink_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "relink.py",
    )

    # Build the command
    command = [
        sys.executable,
        relink_script,
        str(source_file),
        "--target-root",
        str(target_dir),
        "-inputdata",
        str(source_dir),
    ]

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    # Verify the command executed successfully
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Verify the file was converted to a symlink
    assert source_file.is_symlink()
    assert os.readlink(str(source_file)) == str(target_file)

    # Verify success messages in output
    assert f"{INDENT}Created symbolic link:" in result.stdout


def test_command_line_relative_file_from_inputdata_subdir(nested_mock_dirs):
    """Test that a bare relative filename is resolved against the cwd (an
    inputdata subdirectory), not against the inputdata root.

    A same-named decoy file sits directly under the inputdata root, outside
    "sub", with different content than the intended file, plus a matching
    target copy (also with different content) so it *would* be relinked if a
    root-relative regression resolved "test_file.txt" against inputdata_root
    instead of cwd. Because this is a single-file argument rather than a
    directory to recurse into, such a regression would process the decoy
    INSTEAD OF the subdir file, not in addition to it. The return code and
    decoy_file.is_file() pass either way (the latter because is_file()
    follows a symlink to a real file); what actually discriminates is that
    the decoy stays a plain file with its original content (not relinked),
    and that the intended subdir file is the one converted to a symlink --
    pointing at the subdir's target copy, not the root decoy's.
    """
    source_dir, target_dir, source_sub_dir, source_file, target_file = (
        nested_mock_dirs
    )

    # Decoy file directly under the inputdata root (outside "sub"), same
    # name as the intended file but different content, with a matching
    # target copy (also different content). Correct cwd-relative resolution
    # of "test_file.txt" never reaches this file; a root-relative regression
    # would relink it instead of the subdir file.
    decoy_file = source_dir / "test_file.txt"
    decoy_target = target_dir / "test_file.txt"
    decoy_file.write_text("decoy content")
    decoy_target.write_text("decoy target content")

    # Get the path to relink.py
    relink_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "relink.py",
    )

    # Build the command
    command = [
        sys.executable,
        relink_script,
        "test_file.txt",
        "--target-root",
        str(target_dir),
        "--inputdata-root",
        str(source_dir),
    ]

    # Execute the command with cwd set to the inputdata subdirectory
    result = subprocess.run(
        command, cwd=str(source_sub_dir), capture_output=True, text=True, check=False
    )

    # Verify the command executed successfully
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Verify the intended subdir file was converted to a symlink pointing at
    # the subdir's target copy (not the root decoy's)
    assert source_file.is_symlink()
    assert os.readlink(str(source_file)) == str(target_file)

    # Verify the decoy at the inputdata root was NOT reached/relinked
    assert decoy_file.is_file()
    assert not decoy_file.is_symlink()
    assert decoy_file.read_text() == "decoy content"


def test_command_line_relative_dir_dot_from_inputdata_subdir(nested_mock_dirs):
    """Test that '.' is resolved against the cwd (an inputdata subdirectory),
    not against the inputdata root.

    A decoy file sits directly under the inputdata root, outside "sub", with
    a matching target copy so it *would* be relinkable if reached. Because
    relink's search is recursive, resolving '.' against cwd (source_dir/sub)
    never reaches the decoy, while a root-relative regression -- resolving
    '.' against inputdata_root (source_dir) instead -- would recurse into
    the decoy too. Only the decoy assertion below actually discriminates
    between those two resolutions; the symlink-target subdirectory
    (test_file.txt) is reached by recursion either way.
    """
    source_dir, target_dir, source_sub_dir, source_file, target_file = (
        nested_mock_dirs
    )

    # Decoy file directly under the inputdata root (outside "sub"), with a
    # matching target copy. Correct cwd-relative resolution of "." never
    # reaches this file; a root-relative regression would.
    decoy_file = source_dir / "decoy.txt"
    decoy_target = target_dir / "decoy.txt"
    decoy_file.write_text("decoy content")
    decoy_target.write_text("decoy target content")

    # Get the path to relink.py
    relink_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "relink.py",
    )

    # Build the command
    command = [
        sys.executable,
        relink_script,
        ".",
        "--target-root",
        str(target_dir),
        "--inputdata-root",
        str(source_dir),
    ]

    # Execute the command with cwd set to the inputdata subdirectory
    result = subprocess.run(
        command, cwd=str(source_sub_dir), capture_output=True, text=True, check=False
    )

    # Verify the command executed successfully
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Verify the file was converted to a symlink pointing at the target copy
    assert source_file.is_symlink()
    assert os.readlink(str(source_file)) == str(target_file)

    # Verify the decoy outside "sub" was NOT reached/relinked
    assert decoy_file.is_file()
    assert not decoy_file.is_symlink()
    assert decoy_file.read_text() == "decoy content"


def test_command_line_multiple_source_dirs(temp_dirs):
    """Test executing relink.py with multiple source directories."""
    inputdata_dir, target_dir = temp_dirs
    # Create multiple source directories
    source1 = Path(os.path.join(inputdata_dir, "source1"))
    source2 = Path(os.path.join(inputdata_dir, "source2"))
    target1 = Path(os.path.join(target_dir, "source1"))
    target2 = Path(os.path.join(target_dir, "source2"))
    source1.mkdir()
    source2.mkdir()
    target1.mkdir()
    target2.mkdir()

    # Create files in each source directory
    source1_file = source1 / "file1.txt"
    source2_file = source2 / "file2.txt"
    target1_file = target1 / "file1.txt"
    target2_file = target2 / "file2.txt"

    source1_file.write_text("source1 content")
    source2_file.write_text("source2 content")
    target1_file.write_text("target1 content")
    target2_file.write_text("target2 content")

    # Get the path to relink.py
    relink_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "relink.py",
    )

    # Build the command with multiple source directories
    command = [
        sys.executable,
        relink_script,
        str(source1),
        str(source2),
        "--target-root",
        target_dir,
        "--inputdata-root",
        str(inputdata_dir),
    ]

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    # Verify the command executed successfully
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Verify both files were converted to symlinks
    assert source1_file.is_symlink()
    assert source2_file.is_symlink()
    assert os.readlink(str(source1_file)) == str(target1_file)
    assert os.readlink(str(source2_file)) == str(target2_file)


def test_command_line_source_dir_and_file(temp_dirs):
    """Test executing relink.py with a source directory and source file."""
    inputdata_dir, target_dir = temp_dirs
    # Create multiple source directories
    source1 = Path(os.path.join(inputdata_dir, "source1"))
    source2 = Path(os.path.join(inputdata_dir, "source2"))
    target1 = Path(os.path.join(target_dir, "source1"))
    target2 = Path(os.path.join(target_dir, "source2"))
    source1.mkdir()
    source2.mkdir()
    target1.mkdir()
    target2.mkdir()

    # Create files in each source directory
    source1_file = source1 / "file1.txt"
    source2_file = source2 / "file2.txt"
    target1_file = target1 / "file1.txt"
    target2_file = target2 / "file2.txt"

    source1_file.write_text("source1 content")
    source2_file.write_text("source2 content")
    target1_file.write_text("target1 content")
    target2_file.write_text("target2 content")

    # Get the path to relink.py
    relink_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "relink.py",
    )

    # Build the command
    command = [
        sys.executable,
        relink_script,
        str(source1),
        source2_file,
        "--target-root",
        target_dir,
        "--inputdata-root",
        str(inputdata_dir),
    ]

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    # Verify the command executed successfully
    assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"

    # Verify both files were converted to symlinks
    assert source1_file.is_symlink()
    assert source2_file.is_symlink()
    assert os.readlink(str(source1_file)) == str(target1_file)
    assert os.readlink(str(source2_file)) == str(target2_file)
