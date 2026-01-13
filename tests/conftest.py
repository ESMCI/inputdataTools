"""
Pytest configuration and shared fixtures for relink tests.
"""

import os

import pytest


@pytest.fixture(scope="session")
def workspace_root():
    """Return the root directory of the workspace."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
