"""
Tests for configure_logging() function in rimport script.
"""

import os
import sys
import importlib.util
import logging
from importlib.machinery import SourceFileLoader

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
loader.exec_module(rimport)


class TestConfigureLogging:
    """Test suite for configure_logging() function."""

    @pytest.fixture(autouse=True)
    def cleanup_logger(self):
        """Clean up logger handlers after each test."""
        yield
        # Clear handlers after test
        rimport.logger.handlers.clear()

    def test_sets_logger_level_to_info(self):
        """Test that configure_logging sets the logger level to INFO."""
        rimport.configure_logging()
        assert rimport.logger.level == logging.INFO

    def test_creates_two_handlers(self):
        """Test that configure_logging creates exactly two handlers."""
        rimport.configure_logging()
        assert len(rimport.logger.handlers) == 2

    def test_info_handler_goes_to_stdout(self, capsys):
        """Test that INFO level messages go to stdout."""
        rimport.configure_logging()
        rimport.logger.info("Test info message")

        captured = capsys.readouterr()
        assert "Test info message" in captured.out
        assert captured.err == ""

    def test_warning_handler_goes_to_stdout(self, capsys):
        """Test that WARNING level messages go to stdout."""
        rimport.configure_logging()
        rimport.logger.warning("Test warning message")

        captured = capsys.readouterr()
        assert "Test warning message" in captured.out
        assert captured.err == ""

    def test_error_handler_goes_to_stderr(self, capsys):
        """Test that ERROR level messages go to stderr."""
        rimport.configure_logging()
        rimport.logger.error("Test error message")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Test error message" in captured.err

    def test_critical_handler_goes_to_stderr(self, capsys):
        """Test that CRITICAL level messages go to stderr."""
        rimport.configure_logging()
        rimport.logger.critical("Test critical message")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Test critical message" in captured.err

    def test_debug_messages_not_logged_if_info(self, capsys):
        """Test that DEBUG level messages are not logged if logger level is INFO."""
        rimport.configure_logging()
        rimport.logger.debug("Test debug message")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_clears_existing_handlers(self):
        """Test that configure_logging clears any existing handlers."""
        # Add a dummy handler
        from io import StringIO
        dummy_handler = logging.StreamHandler(StringIO())
        rimport.logger.addHandler(dummy_handler)
        assert len(rimport.logger.handlers) >= 1

        # Configure logging
        rimport.configure_logging()

        # Verify old handlers were cleared and new ones added
        assert len(rimport.logger.handlers) == 2
        assert dummy_handler not in rimport.logger.handlers

    def test_formatter_uses_message_only(self, capsys):
        """Test that the formatter outputs only the message without level/timestamp."""
        rimport.configure_logging()
        rimport.logger.info("Simple message")

        captured = capsys.readouterr()
        output = captured.out.strip()
        assert output == "Simple message"
        assert "INFO" not in output

    def test_multiple_calls_dont_duplicate_handlers(self):
        """Test that calling configure_logging multiple times doesn't duplicate handlers."""
        rimport.configure_logging()
        assert len(rimport.logger.handlers) == 2

        rimport.configure_logging()
        assert len(rimport.logger.handlers) == 2  # Still 2, not 4

        rimport.configure_logging()
        assert len(rimport.logger.handlers) == 2  # Still 2, not 6
