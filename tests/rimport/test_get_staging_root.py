"""
Tests for get_staging_root() function in rimport script.
"""

import os
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

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
# Don't add to sys.modules to avoid conflict with other test files
loader.exec_module(rimport)


@pytest.fixture(autouse=True)
def verify_returns_path():
    """Fixture that verifies get_staging_root always returns a Path object."""
    # Store the original function
    original_func = rimport.get_staging_root

    def wrapper(*args, **kwargs):
        result = original_func(*args, **kwargs)
        assert isinstance(
            result, Path
        ), f"get_staging_root should return Path, got {type(result)}"
        return result

    # Temporarily replace the function
    rimport.get_staging_root = wrapper
    yield
    # Restore original function
    rimport.get_staging_root = original_func


class TestGetStagingRoot:
    """Test suite for get_staging_root() function."""

    def test_returns_default_when_env_not_set(self, monkeypatch):
        """Test that default staging root is returned when RIMPORT_STAGING is not set."""
        # Ensure RIMPORT_STAGING is not set
        monkeypatch.delenv("RIMPORT_STAGING", raising=False)

        result = rimport.get_staging_root()

        assert result == rimport.DEFAULT_STAGING_ROOT

    def test_returns_env_value_when_set(self, tmp_path, monkeypatch):
        """Test that RIMPORT_STAGING environment variable is used when set."""
        custom_staging = tmp_path / "custom_staging"
        custom_staging.mkdir()

        monkeypatch.setenv("RIMPORT_STAGING", str(custom_staging))
        result = rimport.get_staging_root()

        assert result == custom_staging.resolve()

    def test_expands_tilde_in_env_value(self, monkeypatch):
        """Test that ~ is expanded in RIMPORT_STAGING value."""
        # Use a path with ~ that will be expanded
        monkeypatch.setenv("RIMPORT_STAGING", "~/my_staging")
        result = rimport.get_staging_root()

        # Should be expanded and resolved
        assert "~" not in str(result)
        assert result.is_absolute()

    def test_resolves_relative_path_in_env_value(self, monkeypatch):
        """Test that relative paths in RIMPORT_STAGING are resolved."""
        # Set a relative path
        monkeypatch.setenv("RIMPORT_STAGING", "./staging")
        result = rimport.get_staging_root()

        # Should be resolved to absolute path
        assert result.is_absolute()

    def test_env_value_with_spaces(self, tmp_path, monkeypatch):
        """Test handling of RIMPORT_STAGING with spaces in path."""
        custom_staging = tmp_path / "staging with spaces"
        custom_staging.mkdir()

        monkeypatch.setenv("RIMPORT_STAGING", str(custom_staging))
        result = rimport.get_staging_root()

        assert result == custom_staging.resolve()

    def test_env_value_overrides_default(self, tmp_path, monkeypatch):
        """Test that RIMPORT_STAGING overrides the default value."""
        custom_staging = tmp_path / "override"
        custom_staging.mkdir()

        monkeypatch.setenv("RIMPORT_STAGING", str(custom_staging))
        result = rimport.get_staging_root()

        # Should NOT be the default
        assert result != rimport.DEFAULT_STAGING_ROOT
        assert result == custom_staging.resolve()
