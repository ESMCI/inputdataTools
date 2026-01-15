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

DEFAULT_SOURCE_ROOT = "/glade/campaign/cesm/cesmdata/cseg/inputdata/"
DEFAULT_TARGET_ROOT = (
    "/glade/campaign/collections/gdex/data/d651077/cesmdata/inputdata/"
)

# Set up logger
logger = logging.getLogger(__name__)


def find_and_replace_owned_files(source_dir, target_dir, username, dry_run=False):
    """
    Finds files owned by a specific user in a source directory tree,
    deletes them, and replaces them with symbolic links to the same
    relative path in a target directory tree.

    Args:
        source_dir (str): The root of the directory tree to search for files.
        target_dir (str): The root of the directory tree containing the new files.
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

    for dirpath, _, filenames in os.walk(source_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            # Use os.stat().st_uid to get the file's owner UID
            try:
                if os.path.islink(file_path):
                    logger.info("Skipping symlink: %s", file_path)
                    continue

                file_uid = os.stat(file_path).st_uid
            except FileNotFoundError:
                continue  # Skip if file was deleted during traversal

            if file_uid == user_uid:
                logger.info("Found owned file: %s", file_path)

                # Determine the relative path and the new link's destination
                relative_path = os.path.relpath(file_path, source_dir)
                link_target = os.path.join(target_dir, relative_path)

                # Check if the target file actually exists
                if not os.path.exists(link_target):
                    logger.warning(
                        "Warning: Corresponding file not found in '%s' "
                        "for '%s'. Skipping.",
                        target_dir,
                        file_path,
                    )
                    continue

                # Get the link name
                link_name = file_path

                if dry_run:
                    logger.info(
                        "[DRY RUN] Would create symbolic link: %s -> %s",
                        link_name,
                        link_target,
                    )
                    continue

                # Remove the original file
                try:
                    os.rename(link_name, link_name + ".tmp")
                    logger.info("Deleted original file: %s", link_name)
                except OSError as e:
                    logger.error("Error deleting file %s: %s. Skipping.", link_name, e)
                    continue

                # Create the symbolic link, handling necessary parent directories
                try:
                    # Create parent directories for the link if they don't exist
                    os.makedirs(os.path.dirname(link_name), exist_ok=True)
                    os.symlink(link_target, link_name)
                    os.remove(link_name + ".tmp")
                    logger.info(
                        "Created symbolic link: %s -> %s", link_name, link_target
                    )
                except OSError as e:
                    os.rename(link_name + ".tmp", link_name)
                    logger.error(
                        "Error creating symlink for %s: %s. Skipping.", link_name, e
                    )


def validate_directory(path):
    """
    Validate that the path exists and is a directory.

    Args:
        path (str): The path to validate.

    Returns:
        str: The absolute path if valid.

    Raises:
        argparse.ArgumentTypeError: If path doesn't exist or is not a directory.
    """
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
        "--source-root",
        type=validate_directory,
        default=DEFAULT_SOURCE_ROOT,
        help=(
            f"The root of the directory tree to search for files (default: {DEFAULT_SOURCE_ROOT})"
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

    return parser.parse_args()

def main():

    args = parse_arguments()

    # Configure logging based on verbosity flags
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format="%(message)s", stream=sys.stdout)

    my_username = os.environ["USER"]

    start_time = time.time()

    # --- Execution ---
    find_and_replace_owned_files(
        args.source_root, args.target_root, my_username, dry_run=args.dry_run
    )

    if args.timing:
        elapsed_time = time.time() - start_time
        logger.info("Execution time: %.2f seconds", elapsed_time)

if __name__ == "__main__":
    main()
