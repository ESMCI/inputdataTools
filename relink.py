"""
Finds files owned by a specific user in a source directory tree,
deletes them, and replaces them with symbolic links to the same
relative path in a target directory tree.
"""

import os
import pwd
import argparse
import logging
import time
from pathlib import Path

from shared import (
    DEFAULT_INPUTDATA_ROOT,
    DEFAULT_STAGING_ROOT,
    get_log_level,
    add_parser_verbosity_group,
    add_inputdata_root,
    validate_paths,
    validate_directory,
    configure_logging,
    logger,
    INDENT,
)

# Define a custom log level that always prints
ALWAYS = logging.CRITICAL * 2
logging.addLevelName(ALWAYS, "ALWAYS")


def always(self, message, *args, **kwargs):
    """Log message that always appears regardless of log level."""
    if self.isEnabledFor(ALWAYS):
        # pylint: disable=protected-access
        self._log(ALWAYS, message, args, **kwargs)


logging.Logger.always = always


def _handle_non_dir_entry(entry: os.DirEntry, user_uid: int):
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


def _handle_non_dir_str(path: str, user_uid: int):
    """
    Check if a non-directory string is owned by the user and should be processed. This should only
    ever be needed if the user specified a file to process on the command line. Because we don't
    expect users to process large numbers of files at once in this way, it's okay if this function
    isn't performance-optimized.

    Args:
        path (str): A filesystem path.
        user_uid (int): The UID of the user whose files to find.

    Returns:
        str or None: The absolute path to the file if it's owned by the user
                     and is a regular file (not a symlink), otherwise None.
    """
    # Is this even owned by the user?
    if os.stat(path, follow_symlinks=False).st_uid == user_uid:

        is_file = os.path.isfile(path)
        is_symlink = os.path.islink(path)

        # Log about skipping symlinks
        if is_symlink:
            logger.debug("Skipping symlink: %s", path)

        # Return if it's a file (and not a symlink)
        elif is_file:
            return path

    return None


def handle_non_dir(var, user_uid):
    """
    Check if a non-directory is owned by the user and should be processed. Passes var to a
    helper function depending on its type.

    Args:
        var (os.DirEntry or str): A directory entry from os.scandir(), or a string path.
        user_uid (int): The UID of the user whose files to find.

    Returns:
        str or None: The absolute path to the file if it's owned by the user
                     and is a regular file (not a symlink), otherwise None.

    Raises:
        TypeError: If var is not a DirEntry-like object.
    """

    # Handle a variable of type str.
    if isinstance(var, str):
        file_path = _handle_non_dir_str(var, user_uid)

    # Handle a variable of type like os.DirEntry.
    # Fall back to duck typing: If var has the required DirEntry methods and members, treat it as a
    # DirEntry. This is necessary for this conditional to work with the MockDirEntry type used in
    # testing. ("If it looks, walks, and quacks like a duck...")
    elif isinstance(var, os.DirEntry) or all(
        hasattr(var, m) for m in ["stat", "is_file", "is_symlink", "path"]
    ):
        file_path = _handle_non_dir_entry(var, user_uid)

    else:
        raise TypeError(
            f"Unsure how to handle non-directory variable of type {type(var)}"
        )

    return file_path


def find_owned_files_scandir(item, user_uid, inputdata_root=DEFAULT_INPUTDATA_ROOT):
    """
    Efficiently find all files owned by a specific user using os.scandir().

    This is more efficient than os.walk() because os.scandir() caches stat
    information during directory traversal, reducing system calls.

    Args:
        item (str): The root directory to search, or the file to check.
        user_uid (int): The UID of the user whose files to find.
        inputdata_root (str): The root of the directory tree containing CESM input data.

    Yields:
        str: Absolute paths to files owned by the user.

    Raises:
        ValueError: If any file found is not under inputdata_root.
    """
    try:
        with os.scandir(item) as entries:
            for entry in entries:
                try:
                    # Recursively process directories (not following symlinks)
                    if entry.is_dir(follow_symlinks=False):
                        yield from find_owned_files_scandir(
                            entry.path, user_uid, inputdata_root
                        )

                    # Things other than directories are handled separately
                    elif (entry_path := handle_non_dir(entry, user_uid)) is not None:
                        yield entry_path

                except (OSError, PermissionError) as e:
                    logger.error("Error accessing %s: %s. Skipping.", entry.path, e)
                    continue

    except NotADirectoryError:
        if (file_path := handle_non_dir(item, user_uid)) is not None:
            yield file_path

    except (OSError, PermissionError) as e:
        logger.error("Error accessing %s: %s. Skipping.", item, e)


def replace_files_with_symlinks(
    item_to_process,
    target_dir,
    username,
    inputdata_root=DEFAULT_INPUTDATA_ROOT,
    dry_run=False,
):
    """
    Finds files owned by a specific user in a source directory tree,
    deletes them, and replaces them with symbolic links to the same
    relative path in a target directory tree.

    Args:
        item_to_process (str): The root directory to search, or the file to process.
        target_dir (str): The root of the directory tree containing the new files.
        inputdata_root (str): The root of the directory tree containing CESM input data.
        username (str): The name of the user whose files will be processed.
        dry_run (bool): If True, only show what would be done without making changes.
    """
    item_to_process = os.path.abspath(item_to_process)
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
        item_to_process,
    )

    # Use efficient scandir-based search
    for file_path in find_owned_files_scandir(
        item_to_process, user_uid, inputdata_root
    ):
        replace_one_file_with_symlink(
            inputdata_root, target_dir, file_path, dry_run=dry_run
        )


def replace_one_file_with_symlink(inputdata_root, target_dir, file_path, dry_run=False):
    """
    Given a file, replaces it with a symbolic link to the same relative path in a target directory
    tree.

    Args:
        inputdata_root (str): The root of the directory tree containing CESM input data.
        target_dir (str): The root of the directory tree containing the new files.
        file_path (str): The path of the file to be replaced.
        dry_run (bool): If True, only show what would be done without making changes.
    """
    logger.info("'%s':", file_path)

    # Determine the relative path and the new link's destination
    relative_path = os.path.relpath(file_path, inputdata_root)
    link_target = os.path.join(target_dir, relative_path)

    # Check if the target file actually exists
    if not os.path.exists(link_target):
        logger.warning(
            "%sWarning: Corresponding file '%s' not found. Skipping.",
            INDENT,
            link_target,
        )
        return

    # Get the link name
    link_name = file_path

    if dry_run:
        logger.info(
            "%s[DRY RUN] Would create symbolic link: %s -> %s",
            INDENT,
            link_name,
            link_target,
        )
        return

    # Remove the original file
    try:
        os.rename(link_name, link_name + ".tmp")
        logger.info("%sDeleted original file: %s", INDENT, link_name)
    except OSError as e:
        logger.error("%sError deleting file %s: %s. Skipping.", INDENT, link_name, e)
        return

    # Create the symbolic link, handling necessary parent directories
    try:
        # Create parent directories for the link if they don't exist
        os.makedirs(os.path.dirname(link_name), exist_ok=True)
        os.symlink(link_target, link_name)
        os.remove(link_name + ".tmp")
        logger.info("%sCreated symbolic link: %s -> %s", INDENT, link_name, link_target)
    except OSError as e:
        os.rename(link_name + ".tmp", link_name)
        logger.error(
            "%sError creating symlink for %s: %s. Skipping.", INDENT, link_name, e
        )


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments containing items_to_process,
                            target_root, and verbosity settings.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Find files owned by a user and replace them with symbolic links to a target directory."
        )
    )
    parser.add_argument(
        "items_to_process",
        nargs="*",
        default=DEFAULT_INPUTDATA_ROOT,
        type=validate_paths,
        help=(
            f"One or more (directories to search for) files (default: {DEFAULT_INPUTDATA_ROOT})"
        ),
    )
    parser.add_argument(
        "--target-root",
        type=validate_directory,
        default=DEFAULT_STAGING_ROOT,
        help=(
            f"The root of the directory tree where files should be moved to "
            f"(default: {DEFAULT_STAGING_ROOT})"
        ),
    )

    # Add inputdata_root option flags
    add_inputdata_root(parser)

    # Add verbosity options
    add_parser_verbosity_group(parser)

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
    args.log_level = get_log_level(quiet=args.quiet, verbose=args.verbose)

    # Ensure that items_to_process is a list
    if hasattr(args, "items_to_process") and not isinstance(
        args.items_to_process, list
    ):
        args.items_to_process = [args.items_to_process]

    # Check that everything is an absolute path (should have been converted, if needed, during
    # validate_paths).
    if hasattr(args, "items_to_process"):
        for item in args.items_to_process:
            assert os.path.isabs(item)
    if hasattr(args, "target_root"):
        assert os.path.isabs(args.target_root)

    # Check that every item in items_to_process is a child of inputdata_root
    if hasattr(args, "items_to_process"):  # Sometimes doesn't if we're testing
        for item in args.items_to_process:
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
    # pylint: disable=missing-function-docstring

    args = parse_arguments()

    configure_logging(args.log_level)

    my_username = os.environ["USER"]

    start_time = time.time()

    # --- Execution ---
    for item in args.items_to_process:
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
