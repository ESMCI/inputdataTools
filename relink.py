"""
Finds files owned by a specific user in a source directory tree,
deletes them, and replaces them with symbolic links to the same
relative path in a target directory tree.
"""

import os
import sys
import pwd
import argparse
import logging
import time
from pathlib import Path

DEFAULT_SOURCE_ROOT = "/glade/campaign/cesm/cesmdata/cseg/inputdata/"
DEFAULT_TARGET_ROOT = (
    "/glade/campaign/collections/gdex/data/d651077/cesmdata/inputdata/"
)

# Set up logger
logger = logging.getLogger(__name__)

# Define a custom log level that always prints
ALWAYS = logging.CRITICAL * 2
logging.addLevelName(ALWAYS, "ALWAYS")


def always(self, message, *args, **kwargs):
    """Log message that always appears regardless of log level."""
    if self.isEnabledFor(ALWAYS):
        # pylint: disable=protected-access
        self._log(ALWAYS, message, args, **kwargs)


logging.Logger.always = always


def _handle_non_dir_entry(entry, user_uid):
    """
    Check if a non-directory entry is owned by the user and should be processed.

    Args:
        entry (os.DirEntry): A directory entry from os.scandir().
        user_uid (int): The UID of the user whose files to find.

    Returns:
        str or None: The absolute path to the file if it's owned by the user
                     and is a regular file (not a symlink), otherwise None.
    """
    # Is this even owned by the user?
    if entry.stat(follow_symlinks=False).st_uid == user_uid:

        # Return if it's a file (not following symlinks)
        if entry.is_file(follow_symlinks=False):
            return entry.path

        # Log about skipping symlinks
        if entry.is_symlink():
            logger.debug("Skipping symlink: %s", entry.path)

    return None


def handle_non_dir(var, user_uid, inputdata_root):
    """
    Check if a non-directory is owned by the user and should be processed. Passes var to a
    helper function depending on its type.

    Args:
        var (os.DirEntry or str): A directory entry from os.scandir(), or a string path.
        user_uid (int): The UID of the user whose files to find.
        inputdata_root (str): The root of the directory tree containing CESM input data.

    Returns:
        str or None: The absolute path to the file if it's owned by the user
                     and is a regular file (not a symlink), otherwise None.

    Raises:
        TypeError: If var is not a DirEntry-like object.
        ValueError: If the file path is not under inputdata_root.
    """

    # Fall back to duck typing: If var has the required DirEntry methods and members, treat it as a
    # DirEntry. This is necessary for this conditional to work with the MockDirEntry type used in
    # testing. ("If it looks, walks, and quacks like a duck...")
    if isinstance(var, os.DirEntry) or all(
        hasattr(var, m) for m in ["stat", "is_file", "is_symlink", "path"]
    ):
        file_path = _handle_non_dir_entry(var, user_uid)
    else:
        raise TypeError(
            f"Unsure how to handle non-directory variable of type {type(var)}"
        )

    # Check that resulting path is a child of inputdata_root
    if file_path is not None and not Path(file_path).is_relative_to(inputdata_root):
        raise ValueError(
            f"'{file_path}' must be equivalent to or under '{inputdata_root}"
        )

    return file_path


def find_owned_files_scandir(directory, user_uid, inputdata_root=DEFAULT_SOURCE_ROOT):
    """
    Efficiently find all files owned by a specific user using os.scandir().

    This is more efficient than os.walk() because os.scandir() caches stat
    information during directory traversal, reducing system calls.

    Args:
        directory (str): The root directory to search.
        user_uid (int): The UID of the user whose files to find.
        inputdata_root (str): The root of the directory tree containing CESM input data.

    Yields:
        str: Absolute paths to files owned by the user.

    Raises:
        ValueError: If any file found is not under inputdata_root.
    """
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                try:
                    # Recursively process directories (not following symlinks)
                    if entry.is_dir(follow_symlinks=False):
                        yield from find_owned_files_scandir(
                            entry.path, user_uid, inputdata_root
                        )

                    # Things other than directories are handled separately
                    elif (
                        entry_path := handle_non_dir(entry, user_uid, inputdata_root)
                    ) is not None:
                        yield entry_path

                except (OSError, PermissionError) as e:
                    logger.debug("Error accessing %s: %s. Skipping.", entry.path, e)
                    continue

    except (OSError, PermissionError) as e:
        logger.debug("Error accessing %s: %s. Skipping.", directory, e)


def replace_files_with_symlinks(
    source_dir, target_dir, username, inputdata_root=DEFAULT_SOURCE_ROOT, dry_run=False
):
    """
    Finds files owned by a specific user in a source directory tree,
    deletes them, and replaces them with symbolic links to the same
    relative path in a target directory tree.

    Args:
        source_dir (str): The root of the directory tree to search for files.
        target_dir (str): The root of the directory tree containing the new files.
        inputdata_root (str): The root of the directory tree containing CESM input data.
        username (str): The name of the user whose files will be processed.
        dry_run (bool): If True, only show what would be done without making changes.
    """
    source_dir = os.path.abspath(source_dir)
    target_dir = os.path.abspath(target_dir)

    # Get the user ID (UID) for the specified username
    try:
        user_uid = pwd.getpwnam(username).pw_uid
    except KeyError:
        logger.error("Error: User '%s' not found. Exiting.", username)
        return

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    logger.info(
        "Searching for files owned by '%s' (UID: %s) in '%s'...",
        username,
        user_uid,
        source_dir,
    )

    # Use efficient scandir-based search
    for file_path in find_owned_files_scandir(source_dir, user_uid, inputdata_root):
        replace_one_file_with_symlink(
            source_dir, target_dir, file_path, dry_run=dry_run
        )


def replace_one_file_with_symlink(source_dir, target_dir, file_path, dry_run=False):
    """
    Given a file, replaces it with a symbolic link to the same relative path in a target directory
    tree.

    Args:
        source_dir (str): The root of the directory tree to search for files.
        target_dir (str): The root of the directory tree containing the new files.
        file_path (str): The path of the file to be replaced.
        dry_run (bool): If True, only show what would be done without making changes.
    """
    logger.info("Found owned file: %s", file_path)

    # Determine the relative path and the new link's destination
    relative_path = os.path.relpath(file_path, source_dir)
    link_target = os.path.join(target_dir, relative_path)

    # Check if the target file actually exists
    if not os.path.exists(link_target):
        logger.warning(
            "Warning: Corresponding file not found in '%s' for '%s'. Skipping.",
            target_dir,
            file_path,
        )
        return

    # Get the link name
    link_name = file_path

    if dry_run:
        logger.info(
            "[DRY RUN] Would create symbolic link: %s -> %s",
            link_name,
            link_target,
        )
        return

    # Remove the original file
    try:
        os.rename(link_name, link_name + ".tmp")
        logger.info("Deleted original file: %s", link_name)
    except OSError as e:
        logger.error("Error deleting file %s: %s. Skipping.", link_name, e)
        return

    # Create the symbolic link, handling necessary parent directories
    try:
        # Create parent directories for the link if they don't exist
        os.makedirs(os.path.dirname(link_name), exist_ok=True)
        os.symlink(link_target, link_name)
        os.remove(link_name + ".tmp")
        logger.info("Created symbolic link: %s -> %s", link_name, link_target)
    except OSError as e:
        os.rename(link_name + ".tmp", link_name)
        logger.error("Error creating symlink for %s: %s. Skipping.", link_name, e)


def validate_directory(path):
    """
    Validate that one or more paths exist and are directories.

    Args:
        path (str or list): The path to validate, or a list of such paths.

    Returns:
        str or list: The absolute path(s) if valid.

    Raises:
        argparse.ArgumentTypeError: If a path doesn't exist or is not a directory.
    """
    if isinstance(path, list):
        result = []
        for item in path:
            result.append(validate_directory(item))
        return result

    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Directory '{path}' does not exist")
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"'{path}' is not a directory")
    return os.path.abspath(path)


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments containing source_root,
                            target_root, and verbosity settings.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Find files owned by a user and replace them with symbolic links to a target directory."
        )
    )
    parser.add_argument(
        "source_root",
        nargs="*",
        default=DEFAULT_SOURCE_ROOT,
        help=(
            f"One or more directories to search for files (default: {DEFAULT_SOURCE_ROOT})"
        ),
    )
    parser.add_argument(
        "--target-root",
        type=validate_directory,
        default=DEFAULT_TARGET_ROOT,
        help=(
            f"The root of the directory tree where files should be moved to "
            f"(default: {DEFAULT_TARGET_ROOT})"
        ),
    )

    # The root of the directory tree containing CESM input data.
    # ONLY INTENDED FOR USE IN TESTING
    parser.add_argument(
        "--inputdata-root",
        "-inputdata",  # to match rimport
        type=validate_directory,
        default=DEFAULT_SOURCE_ROOT,
        help=argparse.SUPPRESS,
    )

    # Verbosity options (mutually exclusive)
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode (show only warnings and errors)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Measure and display the execution time",
    )

    args = parser.parse_args()

    process_args(args)

    return args


def process_args(args):
    """
    Process parsed arguments and set derived attributes.

    Sets the log_level attribute on args based on verbosity flags.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    # Configure logging based on verbosity flags
    if args.quiet:
        args.log_level = logging.WARNING
    elif args.verbose:
        args.log_level = logging.DEBUG
    else:
        args.log_level = logging.INFO

    # Ensure that source_root is a list
    if hasattr(args, "source_root") and not isinstance(args.source_root, list):
        args.source_root = [args.source_root]

    # Check that every item in source_root is a child of inputdata_root
    if hasattr(args, "source_root"):  # Sometimes doesn't if we're testing
        for item in args.source_root:
            if not Path(item).is_relative_to(args.inputdata_root):
                raise argparse.ArgumentTypeError(
                    f"Item '{item}' not under inputdata root '{args.inputdata_root}'"
                )

    # Check that target_root is NOT a child of inputdata_root
    if hasattr(args, "target_root"):  # Sometimes doesn't if we're testing
        if Path(args.target_root).is_relative_to(args.inputdata_root):
            raise argparse.ArgumentTypeError(
                f"Target root ('{args.target_root}') must not be under inputdata root "
                f"'{args.inputdata_root}'"
            )


def main():

    args = parse_arguments()

    logging.basicConfig(level=args.log_level, format="%(message)s", stream=sys.stdout)

    my_username = os.environ["USER"]

    start_time = time.time()

    # --- Execution ---
    for item in args.source_root:
        replace_files_with_symlinks(
            item,
            args.target_root,
            my_username,
            inputdata_root=args.inputdata_root,
            dry_run=args.dry_run,
        )

    if args.timing:
        elapsed_time = time.time() - start_time
        logger.always("Execution time: %.2f seconds", elapsed_time)


if __name__ == "__main__":
    main()
