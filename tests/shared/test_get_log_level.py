"""
Tests for shared.py get_log_level() function.
"""

import logging
import shared


class TestGetLogLevel:
    """Test suite for get_log_level() function."""

    def test_default_returns_info(self):
        """Test that default (no flags) returns INFO level."""
        result = shared.get_log_level()
        assert result == logging.INFO

    def test_quiet_returns_warning(self):
        """Test that quiet=True returns WARNING level."""
        result = shared.get_log_level(quiet=True)
        assert result == logging.WARNING

    def test_verbose_returns_debug(self):
        """Test that verbose=True returns DEBUG level."""
        result = shared.get_log_level(verbose=True)
        assert result == logging.DEBUG

    def test_quiet_takes_precedence_over_verbose(self):
        """Test that quiet takes precedence when both are True."""
        result = shared.get_log_level(quiet=True, verbose=True)
        assert result == logging.WARNING

    def test_quiet_false_verbose_false(self):
        """Test explicit False values return INFO."""
        result = shared.get_log_level(quiet=False, verbose=False)
        assert result == logging.INFO
