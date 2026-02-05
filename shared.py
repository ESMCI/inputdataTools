"""
Things shared between rimport and relink
"""

import logging

DEFAULT_INPUTDATA_ROOT = "/glade/campaign/cesm/cesmdata/cseg/inputdata/"
DEFAULT_STAGING_ROOT = (
    "/glade/campaign/collections/gdex/data/d651077/cesmdata/inputdata/"
)


def get_log_level(quiet: bool = False, verbose: bool = False) -> int:
    """Determine logging level based on quiet and verbose flags.

    Args:
        quiet: If True, show only warnings and errors (WARNING level).
        verbose: If True, show debug messages (DEBUG level).

    Returns:
        int: Logging level (DEBUG, INFO, or WARNING).

    Note:
        If both quiet and verbose are True, quiet takes precedence.
    """
    if quiet:
        return logging.WARNING
    if verbose:
        return logging.DEBUG
    return logging.INFO
