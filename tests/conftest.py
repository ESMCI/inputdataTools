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
