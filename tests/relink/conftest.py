"""
Shared fixtures for relink tests.
"""

import os

import pytest


@pytest.fixture(name="current_user")
def fixture_current_user():
    """Get the current user's username."""
    username = os.environ["USER"]
    return username
