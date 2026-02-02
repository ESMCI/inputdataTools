"""
Tests for read_filelist() function in rimport script.
"""

import os
import sys
import importlib.util
from importlib.machinery import SourceFileLoader

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


class TestReadFilelist:
    """Test suite for read_filelist() function."""

    def test_reads_single_line(self, tmp_path):
        """Test reading a file with a single line."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text("file1.nc\n")

        result = rimport.read_filelist(list_file)

        assert len(result) == 1
        assert result[0] == "file1.nc"

    def test_reads_multiple_lines(self, tmp_path):
        """Test reading a file with multiple lines."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text("file1.nc\nfile2.nc\nfile3.nc\n")

        result = rimport.read_filelist(list_file)

        assert len(result) == 3
        assert result[0] == "file1.nc"
        assert result[1] == "file2.nc"
        assert result[2] == "file3.nc"

    def test_ignores_blank_lines(self, tmp_path):
        """Test that blank lines are ignored."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text("file1.nc\n\nfile2.nc\n\n\nfile3.nc\n")

        result = rimport.read_filelist(list_file)

        assert len(result) == 3
        assert result == ["file1.nc", "file2.nc", "file3.nc"]

    def test_ignores_comment_lines(self, tmp_path):
        """Test that lines starting with # are ignored."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text(
            "# This is a comment\nfile1.nc\n# Another comment\nfile2.nc\n"
        )

        result = rimport.read_filelist(list_file)

        assert len(result) == 2
        assert result == ["file1.nc", "file2.nc"]

    def test_strips_whitespace(self, tmp_path):
        """Test that leading and trailing whitespace is stripped."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text("  file1.nc  \n\tfile2.nc\t\n   file3.nc\n")

        result = rimport.read_filelist(list_file)

        assert len(result) == 3
        assert result == ["file1.nc", "file2.nc", "file3.nc"]

    def test_ignores_whitespace_only_lines(self, tmp_path):
        """Test that lines with only whitespace are ignored."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text("file1.nc\n   \n\t\t\nfile2.nc\n")

        result = rimport.read_filelist(list_file)

        assert len(result) == 2
        assert result == ["file1.nc", "file2.nc"]

    def test_empty_file(self, tmp_path):
        """Test reading an empty file."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text("")

        result = rimport.read_filelist(list_file)

        assert len(result) == 0
        assert result == []

    def test_file_with_only_comments_and_blanks(self, tmp_path):
        """Test file with only comments and blank lines."""
        list_file = tmp_path / "filelist123.txt"
        list_file.write_text("# Comment 1\n\n# Comment 2\n\n")

        result = rimport.read_filelist(list_file)

        assert len(result) == 0
        assert result == []

    def test_mixed_content(self, tmp_path):
        """Test file with mixed comments, blanks, and valid lines."""
        list_file = tmp_path / "filelist.txt"
        content = """# Header comment
file1.nc

# Section 1
file2.nc
  file3.nc  

# Section 2
file4.nc
"""
        list_file.write_text(content)

        result = rimport.read_filelist(list_file)

        assert len(result) == 4
        assert result == ["file1.nc", "file2.nc", "file3.nc", "file4.nc"]

    def test_handles_files_with_spaces(self, tmp_path):
        """Test that filenames with spaces are preserved."""
        list_file = tmp_path / "filelist.txt"
        list_file.write_text("file with spaces.nc\nanother file.nc\n")

        result = rimport.read_filelist(list_file)

        assert len(result) == 2
        assert result[0] == "file with spaces.nc"
        assert result[1] == "another file.nc"
