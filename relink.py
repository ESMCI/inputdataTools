import os
import shutil
import pwd
import argparse

DEFAULT_SOURCE_ROOT = '/glade/campaign/cesm/cesmdata/cseg/inputdata/'
DEFAULT_TARGET_ROOT = '/glade/campaign/collections/gdex/data/d651077/cesmdata/inputdata/'

def find_and_replace_owned_files(source_dir, target_dir, username):
    """
    Finds files owned by a specific user in a source directory tree,
    deletes them, and replaces them with symbolic links to the same
    relative path in a target directory tree.

    Args:
        source_dir (str): The root of the directory tree to search for files.
        target_dir (str): The root of the directory tree containing the new files.
        username (str): The name of the user whose files will be processed.
    """
    source_dir = os.path.abspath(source_dir)
    target_dir = os.path.abspath(target_dir)

    # Get the user ID (UID) for the specified username
    try:
        user_uid = pwd.getpwnam(username).pw_uid
    except KeyError:
        print(f"Error: User '{username}' not found. Exiting.")
        return

    print(f"Searching for files owned by '{username}' (UID: {user_uid}) in '{source_dir}'...")

    for dirpath, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            
            # Use os.stat().st_uid to get the file's owner UID
            try:
                if os.path.islink(file_path):
                    print(f"Skipping symlink: {file_path}")
                    continue

                file_uid = os.stat(file_path).st_uid
            except FileNotFoundError:
                continue # Skip if file was deleted during traversal
            
            if file_uid == user_uid:
                print(f"Found owned file: {file_path}")

                # Determine the relative path and the new link's destination
                relative_path = os.path.relpath(file_path, source_dir)
                link_target = os.path.join(target_dir, relative_path)
                
                # Check if the target file actually exists
                if not os.path.exists(link_target):
                    print(f"Warning: Corresponding file not found in '{target_dir}' for '{file_path}'. Skipping.")
                    continue

                # Get the link name
                link_name = file_path

                # Remove the original file
                try:
                    os.rename(link_name, link_name+".tmp")
                    print(f"Deleted original file: {link_name}")
                except OSError as e:
                    print(f"Error deleting file {link_name}: {e}. Skipping.")
                    continue

                # Create the symbolic link, handling necessary parent directories
                try:
                    # Create parent directories for the link if they don't exist
                    os.makedirs(os.path.dirname(link_name), exist_ok=True)
                    os.symlink(link_target, link_name)
                    os.remove(link_name+".tmp")
                    print(f"Created symbolic link: {link_name} -> {link_target}")
                except OSError as e:
                    os.rename(link_name+".tmp", link_name)
                    print(f"Error creating symlink for {link_name}: {e}. Skipping.")

def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments containing source_root 
                            and target_root.
    """
    parser = argparse.ArgumentParser(
        description=(
            'Find files owned by a user and replace them with symbolic links to a target directory.'
        )
    )
    parser.add_argument(
        '--source-root',
        default=DEFAULT_SOURCE_ROOT,
        help=(
            f'The root of the directory tree to search for files (default: {DEFAULT_SOURCE_ROOT})'
        )
    )
    parser.add_argument(
        '--target-root',
        default=DEFAULT_TARGET_ROOT,
        help=(
            f'The root of the directory tree where files should be moved to '
            f'(default: {DEFAULT_TARGET_ROOT})'
        )
    )

    return parser.parse_args()

if __name__ == '__main__':
    # --- Configuration ---
    args = parse_arguments()
    my_username = os.environ['USER']

    # --- Execution ---
    find_and_replace_owned_files(args.source_root, args.target_root, my_username)
    

