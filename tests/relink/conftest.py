"""
Shared fixtures for relink tests.
"""

import os
import tempfile
import shutil

import pytest
from unittest.mock import patch


@pytest.fixture(scope="function", name="temp_dirs")
def fixture_temp_dirs():
    """Create temporary source and target directories for testing."""
    source_dir = tempfile.mkdtemp(prefix="test_source_")
    target_dir = tempfile.mkdtemp(prefix="test_target_")

    with patch("relink.DEFAULT_SOURCE_ROOT", source_dir):
        with patch("relink.DEFAULT_TARGET_ROOT", target_dir):
            yield source_dir, target_dir

    # Cleanup
    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.rmtree(target_dir, ignore_errors=True)


@pytest.fixture(name="current_user")
def fixture_current_user():
    """Get the current user's username."""
    username = os.environ["USER"]
    return username
