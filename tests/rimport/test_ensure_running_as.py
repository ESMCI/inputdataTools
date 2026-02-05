"""
Tests for ensure_running_as() function in rimport script.
"""

import os
import sys
import importlib.util
from importlib.machinery import SourceFileLoader
from unittest.mock import patch, MagicMock

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
sys.modules["rimport"] = rimport
loader.exec_module(rimport)


class TestEnsureRunningAs:
    """Test suite for ensure_running_as() function."""

    def test_does_nothing_when_already_running_as_target_user(self):
        """Test that function returns normally when already running as target user."""
        # Get current user
        current_uid = os.geteuid()

        # Mock pwd.getpwnam to return current UID
        with patch("pwd.getpwnam") as mock_getpwnam:
            mock_pw = MagicMock()
            mock_pw.pw_uid = current_uid
            mock_getpwnam.return_value = mock_pw

            # Mock stdin.isatty and os.execvp to ensure they're not called
            with patch("sys.stdin.isatty") as mock_isatty:
                with patch("os.execvp") as mock_execvp:
                    # Should not raise or exec
                    rimport.ensure_running_as(
                        "testuser", ["rimport", "-file", "test.nc"]
                    )

                    # Verify stdin.isatty and os.execvp were NOT called
                    mock_isatty.assert_not_called()
                    mock_execvp.assert_not_called()

    def test_execs_sudo_when_different_user_and_interactive(self):
        """Test that function execs sudo when running as different user with TTY."""
        current_uid = os.geteuid()
        different_uid = current_uid + 1000

        # Mock pwd.getpwnam to return different UID
        with patch("pwd.getpwnam") as mock_getpwnam:
            mock_pw = MagicMock()
            mock_pw.pw_uid = different_uid
            mock_getpwnam.return_value = mock_pw

            # Mock stdin.isatty to return True
            with patch("sys.stdin.isatty", return_value=True):
                # Mock os.execvp to prevent actual exec
                with patch("os.execvp") as mock_execvp:
                    rimport.ensure_running_as(
                        "otheruser", ["rimport", "-file", "test.nc"]
                    )

                    # Verify execvp was called with correct arguments
                    mock_execvp.assert_called_once()
                    call_args = mock_execvp.call_args[0]
                    assert call_args[0] == "sudo"
                    assert call_args[1][0] == "sudo"
                    assert call_args[1][1] == "-u"
                    assert call_args[1][2] == "otheruser"
                    assert call_args[1][3] == "--"
                    assert call_args[1][4:] == ["rimport", "-file", "test.nc"]

    def test_error_message_for_nonexistent_user(self, caplog):
        """Test that appropriate error message is shown for nonexistent user."""
        # Mock pwd.getpwnam to raise KeyError
        with patch("pwd.getpwnam", side_effect=KeyError("user not found")):
            with pytest.raises(SystemExit) as exc_info:
                rimport.ensure_running_as("baduser", ["rimport", "-file", "test.nc"])

            assert exc_info.value.code == 2
            assert "baduser" in caplog.text
            assert "not found" in caplog.text

    def test_error_message_for_non_interactive(self, caplog):
        """Test that appropriate error message is shown when not interactive."""
        current_uid = os.geteuid()
        different_uid = current_uid + 1000

        # Mock pwd.getpwnam to return different UID
        with patch("pwd.getpwnam") as mock_getpwnam:
            mock_pw = MagicMock()
            mock_pw.pw_uid = different_uid
            mock_getpwnam.return_value = mock_pw

            # Mock stdin.isatty to return False
            with patch("sys.stdin.isatty", return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    rimport.ensure_running_as(
                        "otheruser", ["rimport", "-file", "test.nc"]
                    )

                assert exc_info.value.code == 2
                assert "interactive TTY" in caplog.text
                assert "2FA" in caplog.text
