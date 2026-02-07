"""
Tests for check_relink_worked() function in rimport script.
"""

import os
import importlib.util
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
# Don't add to sys.modules to avoid conflict with other test files
loader.exec_module(rimport)


def test_ok(tmp_path):
    """Check that it doesn't error if src is a symlink pointing to dst"""
    # Set up
    dst = tmp_path / "dst.nc"
    src = tmp_path / "src.nc"
    src.symlink_to(dst)

    # Shouldn't error
    rimport.check_relink_worked(src, dst)


def test_error_not_symlink(tmp_path):
    """Check that it does error if src isn't a symlink"""
    # Set up
    dst = tmp_path / "dst.nc"
    src = tmp_path / "src.nc"

    # Should error
    with pytest.raises(RuntimeError) as exc_info:
        rimport.check_relink_worked(src, dst)

    # Verify error message was printed
    assert "Error relinking during rimport" in str(exc_info.value)


def test_error_symlink_but_not_to_dst(tmp_path):
    """Check that it does error if src is a symlink but not pointing to dst"""
    # Set up
    dst = tmp_path / "dst.nc"
    other = tmp_path / "other.nc"
    src = tmp_path / "src.nc"
    src.symlink_to(other)

    # Should error
    with pytest.raises(RuntimeError) as exc_info:
        rimport.check_relink_worked(src, dst)

    # Verify error message was printed
    assert "Error relinking during rimport" in str(exc_info.value)
