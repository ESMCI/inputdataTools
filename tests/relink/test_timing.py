"""
Tests of relink.py --timing option
"""

import os
import sys
import logging
from unittest.mock import patch

import pytest

# Add parent directory to path to import relink module
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# pylint: disable=wrong-import-position
import relink  # noqa: E402


@pytest.mark.parametrize(
    "use_timing, should_log_timing", [(True, True), (False, False)]
)
def test_timing_logging(tmp_path, caplog, use_timing, should_log_timing):
    """Test that timing message is logged only when --timing flag is used."""
    # Create real directories
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # Create a file
    source_file = source_dir / "test_file.txt"
    target_file = target_dir / "test_file.txt"
    source_file.write_text("source")
    target_file.write_text("target")

    # Build argv with or without --timing flag
    test_argv = [
        "relink.py",
        str(source_dir),
        "--target-root",
        str(target_dir),
    ]
    if use_timing:
        test_argv.append("--timing")

    with patch("sys.argv", test_argv):
        with caplog.at_level(logging.INFO):
            # Call main() which includes the timing logic
            relink.main()

    # Verify timing message presence based on flag
    if should_log_timing:
        assert "Execution time:" in caplog.text
        assert "seconds" in caplog.text
    else:
        assert "Execution time:" not in caplog.text


def test_timing_shows_in_quiet_mode(tmp_path, caplog):
    """Test that timing message is shown even when --quiet flag is used."""
    # Create real directories
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # Create a file
    source_file = source_dir / "test_file.txt"
    target_file = target_dir / "test_file.txt"
    source_file.write_text("source")
    target_file.write_text("target")

    # Build argv with both --timing and --quiet flags
    test_argv = [
        "relink.py",
        str(source_dir),
        "--target-root",
        str(target_dir),
        "--timing",
        "--quiet",
    ]

    with patch("sys.argv", test_argv):
        with caplog.at_level(logging.WARNING):
            # Call main() which includes the timing logic
            relink.main()

    # Verify timing message appears even in quiet mode
    assert "Execution time:" in caplog.text
    assert "seconds" in caplog.text
    # Verify that INFO messages are suppressed
    assert "Searching for files owned by" not in caplog.text
