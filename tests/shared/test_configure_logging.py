"""
Tests for shared configure_logging() function.
"""

import logging

import pytest

import shared

logger = logging.getLogger(__name__)


class TestConfigureLogging:
    """Test suite for configure_logging() function."""

    @pytest.fixture(autouse=True)
    def cleanup_logger(self):
        """Clean up logger handlers after each test."""
        yield
        # Clear handlers after test
        logger.handlers.clear()

    def test_sets_logger_level_to_info(self):
        """Test that configure_logging sets the logger level to INFO."""
        shared.configure_logging(logging.INFO, logger)
        assert logger.level == logging.INFO

    def test_creates_two_handlers(self):
        """Test that configure_logging creates exactly two handlers."""
        shared.configure_logging(logging.INFO, logger)
        assert len(logger.handlers) == 2

    def test_info_handler_goes_to_stdout(self, capsys):
        """Test that INFO level messages go to stdout."""
        shared.configure_logging(logging.INFO, logger)
        logger.info("Test info message")

        captured = capsys.readouterr()
        assert "Test info message" in captured.out
        assert captured.err == ""

    def test_warning_handler_goes_to_stdout(self, capsys):
        """Test that WARNING level messages go to stdout."""
        shared.configure_logging(logging.INFO, logger)
        logger.warning("Test warning message")

        captured = capsys.readouterr()
        assert "Test warning message" in captured.out
        assert captured.err == ""

    def test_error_handler_goes_to_stderr(self, capsys):
        """Test that ERROR level messages go to stderr."""
        shared.configure_logging(logging.INFO, logger)
        logger.error("Test error message")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Test error message" in captured.err

    def test_critical_handler_goes_to_stderr(self, capsys):
        """Test that CRITICAL level messages go to stderr."""
        shared.configure_logging(logging.INFO, logger)
        logger.critical("Test critical message")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Test critical message" in captured.err

    def test_clears_existing_handlers(self):
        """Test that configure_logging clears any existing handlers."""
        # Add a dummy handler
        from io import StringIO

        dummy_handler = logging.StreamHandler(StringIO())
        logger.addHandler(dummy_handler)
        assert len(logger.handlers) >= 1

        # Configure logging
        shared.configure_logging(logging.INFO, logger)

        # Verify old handlers were cleared and new ones added
        assert len(logger.handlers) == 2
        assert dummy_handler not in logger.handlers

    def test_formatter_uses_message_only(self, capsys):
        """Test that the formatter outputs only the message without level/timestamp."""
        shared.configure_logging(logging.INFO, logger)
        logger.info("Simple message")

        captured = capsys.readouterr()
        output = captured.out.strip()
        assert output == "Simple message"
        assert "INFO" not in output

    def test_multiple_calls_dont_duplicate_handlers(self):
        """Test that calling configure_logging multiple times doesn't duplicate handlers."""
        shared.configure_logging(logging.INFO, logger)
        assert len(logger.handlers) == 2

        shared.configure_logging(logging.INFO, logger)
        assert len(logger.handlers) == 2  # Still 2, not 4

        shared.configure_logging(logging.INFO, logger)
        assert len(logger.handlers) == 2  # Still 2, not 6

    def test_configure_with_debug_level(self, capsys):
        """Test that configure_logging accepts DEBUG level."""
        shared.configure_logging(logging.DEBUG, logger)

        # DEBUG messages should now be logged
        logger.debug("Debug message")

        captured = capsys.readouterr()
        assert "Debug message" in captured.out
        assert captured.err == ""

    def test_configure_with_warning_level(self, capsys):
        """Test that configure_logging accepts WARNING level."""
        shared.configure_logging(logging.WARNING, logger)

        # INFO messages should be suppressed
        logger.info("Info message")
        # WARNING messages should be logged
        logger.warning("Warning message")

        captured = capsys.readouterr()
        assert "Info message" not in captured.out
        assert "Warning message" in captured.out
        assert captured.err == ""

    def test_configure_with_info_level_suppresses_debug(self, capsys):
        """Test that INFO level suppresses DEBUG messages."""
        shared.configure_logging(logging.INFO, logger)

        logger.debug("Debug message")
        logger.info("Info message")

        captured = capsys.readouterr()
        assert "Debug message" not in captured.out
