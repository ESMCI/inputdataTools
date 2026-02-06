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
