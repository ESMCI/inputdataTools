"""
Things shared between rimport and relink
"""

import logging
import argparse
import os

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


def add_inputdata_root(parser: argparse.ArgumentParser):
    """Add inputdata_root option to an argument parser.

    The root of the directory tree containing CESM input data. Only intended for use in testing, so
    help is suppressed.

    Args:
        parser: ArgumentParser instance to add the inputdata_root arg to.
    """
    parser.add_argument(
        "--inputdata-root",
        "-inputdata-root",
        "--inputdata",
        "-inputdata",
        "-i",
        type=validate_directory,
        default=DEFAULT_INPUTDATA_ROOT,
        help=argparse.SUPPRESS,
    )


def add_help(parser: argparse.ArgumentParser):
    """Add help option to an argument parser.

    Provides -help to mirror legacy rimport behavior (in addition to -h and --help).

    Args:
        parser: ArgumentParser instance to add the help arg to.
    """
    parser.add_argument(
        "-h",
        "--help",
        "-help",
        action="help",
        help="Show this help message and exit",
    )


def add_parser_verbosity_group(parser: argparse.ArgumentParser):
    """Add mutually exclusive verbosity options to an argument parser.

    Adds -v/--verbose and -q/--quiet flags as a mutually exclusive group.

    Args:
        parser: ArgumentParser instance to add the verbosity group to.

    Returns:
        The mutually exclusive argument group that was created.
    """
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output (DEBUG level)"
    )
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode (show only warnings and errors)",
    )
    return verbosity_group


def validate_paths(path, check_is_dir=False):
    """
    Validate that one or more paths exist.

    Args:
        path (str or list): The path to validate, or a list of such paths.

    Returns:
        str or list: The absolute path(s) if valid.

    Raises:
        argparse.ArgumentTypeError: If a path doesn't exist.
    """
    if isinstance(path, list):
        result = []
        for item in path:
            result.append(validate_paths(item, check_is_dir=check_is_dir))
        return result

    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"'{path}' does not exist")
    if check_is_dir and not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"'{path}' is not a directory")
    return os.path.abspath(path)


def validate_directory(path):
    """
    Validate that one or more directories exist.

    Args:
        path (str or list): The directory to validate, or a list of such directories.

    Returns:
        str or list: The absolute path(s) if valid.

    Raises:
        argparse.ArgumentTypeError: If a path doesn't exist.
    """
    return validate_paths(path, check_is_dir=True)
