#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import os
import shutil
import sys

from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import finish_script, run_script  # type: ignore

logger = setup_logging(__name__)


def read_environment_variables() -> tuple[str, str]:
    """Read required environment variables.

    Returns:
        Tuple of backup_location and projects_dest_folder.

    Raises:
        SystemExit: If variables are missing.
    """
    backup_location = os.getenv("BACKUP_LOCATION")
    projects_dest_folder = os.getenv("PROJECTS_DESTINATION_FOLDER_NAME")
    if not backup_location or not projects_dest_folder:
        finish_script(
            True, "Missing BACKUP_LOCATION or PROJECTS_DESTINATION_FOLDER_NAME in .env"
        )
    assert backup_location is not None
    assert projects_dest_folder is not None
    return backup_location, projects_dest_folder


def check_if_vscode_folder_already_exits(vscode_folder: str, current_dir: str) -> None:
    """Check if .vscode folder exists and exit if so.

    Args:
        vscode_folder: Path to .vscode folder.
        current_dir: Current directory.
    """
    if os.path.isdir(vscode_folder):
        finish_script(
            False, f".vscode folder already exists in {current_dir}. Nothing to do."
        )


def do_restore_operation(
    vscode_folder: str,
    current_dir: str,
    vscode_folder_name: str,
    backup_location: str,
    projects_dest_folder: str,
) -> None:
    """Perform the restore operation.

    Args:
        vscode_folder: Target .vscode path.
        current_dir: Current directory.
        vscode_folder_name: Name of folder.
        backup_location: Backup base path.
        projects_dest_folder: Projects folder in backup.
    """
    backup_vscode_path = os.path.join(
        backup_location,
        projects_dest_folder,
        os.path.basename(current_dir),
        vscode_folder_name,
    )

    try:
        shutil.copytree(backup_vscode_path, vscode_folder)
        logger.info(f".vscode folder restored from backup: {backup_vscode_path}")
    except Exception as e:
        finish_script(True, f"Failed to copy .vscode folder: {e}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Restore the .vscode folder from the backup location to the current directory. "
        "The script checks if the .vscode folder exists in the current directory. "
        "If not, it attempts to copy it from the backup location as specified in the .env file."
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the script."""
    parse_arguments()
    load_dotenv()

    vscode_folder_name = ".vscode"
    current_dir = os.getcwd()
    vscode_folder = os.path.join(current_dir, vscode_folder_name)

    check_if_vscode_folder_already_exits(vscode_folder, current_dir)
    backup_location, projects_dest_folder = read_environment_variables()
    do_restore_operation(
        vscode_folder,
        current_dir,
        vscode_folder_name,
        backup_location,
        projects_dest_folder,
    )


if __name__ == "__main__":
    run_script(main)
