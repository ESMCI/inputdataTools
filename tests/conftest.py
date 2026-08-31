"""
Pytest configuration and shared fixtures for all tests.
"""

import os
import tempfile
import shutil

import pytest
from unittest.mock import patch


@pytest.fixture(scope="session")
def workspace_root():
    """Return the root directory of the workspace."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="function", name="temp_dirs")
def fixture_temp_dirs():
    """Create temporary source and target directories for testing."""
    source_dir = tempfile.mkdtemp(prefix="test_source_")
    target_dir = tempfile.mkdtemp(prefix="test_target_")

    with patch("relink.DEFAULT_INPUTDATA_ROOT", source_dir):
        with patch("relink.DEFAULT_STAGING_ROOT", target_dir):
            with patch("shared.DEFAULT_INPUTDATA_ROOT", source_dir):
                with patch("shared.DEFAULT_STAGING_ROOT", target_dir):
                    yield source_dir, target_dir

    # Cleanup
    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.rmtree(target_dir, ignore_errors=True)


@pytest.fixture(scope="function", name="nested_mock_dirs")
def fixture_nested_mock_dirs(tmp_path):
    """Create a nested source/target directory layout for testing relative-path
    resolution."""
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

    yield source_dir, target_dir, source_sub_dir, source_file, target_file

    # No explicit cleanup: everything above was created under tmp_path, which
    # pytest already removes automatically. Unlike fixture_temp_dirs (which
    # uses tempfile.mkdtemp, a directory pytest does not manage), an explicit
    # shutil.rmtree here would be redundant.
