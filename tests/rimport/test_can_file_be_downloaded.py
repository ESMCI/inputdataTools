"""
Tests for can_file_be_downloaded() function in rimport script.
"""

import os
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from shared import DEFAULT_STAGING_ROOT

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

RELPATH_THAT_DOES_EXIST = os.path.join(
    "share", "meshes", "ne3pg3_ESMFmesh_c221214_cdf5.asc"
)


class TestCanFileBeDownloaded:
    """Test suite for can_file_be_downloaded() function."""

    @pytest.mark.skipif(
        not os.path.exists("/glade"), reason="This test can only run on Glade"
    )
    def test_existing_file_exists(self):
        """Test that the file that should exist does. If not, other tests will definitely fail."""
        file_abspath = Path(os.path.join(DEFAULT_STAGING_ROOT, RELPATH_THAT_DOES_EXIST))
        assert file_abspath.exists()

    def test_true_abspath(self):
        """Test that can_file_be_downloaded() is true for an existing file given absolute path"""
        file_abspath = Path(os.path.join(DEFAULT_STAGING_ROOT, RELPATH_THAT_DOES_EXIST))
        assert rimport.can_file_be_downloaded(
            file_abspath,
            DEFAULT_STAGING_ROOT,
        )

    def test_true_relpath(self):
        """Test that can_file_be_downloaded() is true for an existing file given relative path"""
        file_relpath = Path(RELPATH_THAT_DOES_EXIST)
        assert rimport.can_file_be_downloaded(
            file_relpath,
            DEFAULT_STAGING_ROOT,
        )

    def test_false_nonexistent(self):
        """Test that can_file_be_downloaded() is false for a nonexistent file"""
        file_relpath = Path("weurueridniduafnea/smfnigsroerij/msdif8ernnr.nc")
        assert not rimport.can_file_be_downloaded(
            file_relpath,
            DEFAULT_STAGING_ROOT,
        )
