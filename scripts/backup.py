#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import hashlib
import hmac
import os
import shutil
import subprocess
import sys

from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import run_script  # type: ignore

logger = setup_logging(__name__)


def get_env(var_name: str, is_list: bool = False) -> str | list[str]:
    """Get environment variable value.

    Args:
        var_name: The variable name.
        is_list: Whether to return as list.

    Returns:
        The value or list of values.

    Raises:
        ValueError: If variable is not set.
    """
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(
            f"Error: Required environment variable '{var_name}' is not set."
        )
    if is_list:
        value = os.getenv(var_name, "")
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def get_parent_folder_name(path: str) -> str:
    """Get the parent folder name of a path.

    Args:
        path: The file path.

    Returns:
        Parent folder name.
    """
    head1, tail1 = os.path.split(path)
    head2, parent_folder_name = os.path.split(head1)
    return parent_folder_name


def compute_file_hash(file_path: str, key: str) -> str:
    """Compute HMAC-SHA256 hash of a file.

    Args:
        file_path: Path to the file.
        key: Secret key for HMAC.

    Returns:
        Hex digest of the HMAC-SHA256 hash.
    """
    with open(file_path, "rb") as f:
        content = f.read()
    return hmac.new(key.encode(), content, hashlib.sha256).hexdigest()


def sudo_makedirs(path: str) -> None:
    """Create directories with sudo if needed.

    Args:
        path: The path to create.
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except PermissionError:
            # Try with sudo if permission denied
            subprocess.run(["sudo", "mkdir", "-p", path], check=True)


def sudo_rmtree(path: str) -> None:
    """Remove directory tree with sudo if needed.

    Args:
        path: The path to remove.
    """
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
        except PermissionError:
            subprocess.run(["sudo", "rm", "-rf", path], check=True)


def do_simple_backup(backup_destination: str, env_prefixes: list[str]) -> None:
    """Perform simple backup for given prefixes.

    Args:
        backup_destination: Destination path.
        env_prefixes: List of prefixes.
    """
    for env_prefix in env_prefixes:
        src_paths = get_env(f"{env_prefix}_SOURCE_PATHS", True)
        if src_paths:
            dest_folder_name = os.getenv(f"{env_prefix}_DESTINATION_FOLDER_NAME")
            # Delete old destination folder (with files) and create new
            dest_path = os.path.join(str(backup_destination), str(dest_folder_name))
            sudo_rmtree(dest_path)
            sudo_makedirs(dest_path)
            # Backup destination path
            for src_path in src_paths:
                try:
                    shutil.copy(src_path, dest_path)
                except Exception as e:
                    logger.error(
                        f"Error in {dest_folder_name} backup: Unable to copy {dest_path}: {e}"
                    )


def do_projects_backup(backup_location: str) -> None:
    """Perform projects backup.

    Args:
        backup_location: Base backup location.
    """
    # Projects environment variables
    projects_destination_folder = get_env("PROJECTS_DESTINATION_FOLDER_NAME")
    projects_source_paths = get_env("PROJECTS_SOURCE_PATHS", True)
    # Check if there are defined projects for backup
    if projects_source_paths:

        def get_env_file_for_environment(project):
            if os.path.isfile(f"{project}/.env"):
                return ".env"
            elif os.path.isfile(f"{project}/.env.rb"):
                return ".env.rb"
            else:
                return ""

        def is_subfolder_of_project(project_path):
            return os.path.basename(project_path) in ["api", "frontend", "backend"]

        def get_project_name(project_path):
            folder_name = os.path.basename(project_path)
            if is_subfolder_of_project(project_path):
                parent_folder_name = get_parent_folder_name(project_path)
                return parent_folder_name + "/" + folder_name
            return folder_name

        env_hash_key = os.getenv("ENV_FILES_ZIP_PASSWORD", "pa55")
        env_filenames = {".env", ".env.rb"}

        def backup_file(project, file, error_message="Unable to backup"):
            src = os.path.join(project, file)
            is_env = file in env_filenames
            dst = os.path.join(
                projects_dir,
                get_project_name(project),
                file + ".hash" if is_env else file,
            )
            try:
                sudo_makedirs(os.path.dirname(dst))
                if is_env:
                    new_hash = compute_file_hash(src, env_hash_key)
                    if os.path.isfile(dst):
                        with open(dst, "r") as f:
                            existing_hash = f.read().strip()
                        if new_hash == existing_hash:
                            logger.info(f"Skipping {project} {file}: unchanged")
                            return
                    with open(dst, "w") as f:
                        f.write(new_hash)
                    logger.info(f"Backed up {project} {file}: hash updated")
                else:
                    shutil.copy(src, dst)
            except Exception as e:
                logger.error(f"{error_message} {project} {file}: {e}")

        # Create projects destination folder if it doesn't exist
        projects_dir = os.path.join(backup_location, str(projects_destination_folder))
        sudo_makedirs(projects_dir)
        for project in projects_source_paths:
            sudo_makedirs(os.path.join(projects_dir, get_project_name(project)))
        # Projects backup
        for project in projects_source_paths:
            # Copy env file
            env_file = get_env_file_for_environment(project)
            if env_file:
                backup_file(project, env_file)

            # Copy config.json file
            config_file = "config.json"
            if os.path.isfile(f"{project}/{config_file}"):
                backup_file(project, config_file)

            # Copy .vscode folder if it exists in the project
            project_path = (
                os.path.dirname(project)
                if is_subfolder_of_project(project)
                else project
            )
            project_name = (
                get_parent_folder_name(project)
                if is_subfolder_of_project(project)
                else os.path.basename(project)
            )
            src_vscode = os.path.join(project_path, ".vscode")
            dst_vscode = os.path.join(projects_dir, project_name, ".vscode")
            if os.path.isdir(src_vscode):
                try:
                    # Remove destination if it exists to avoid copytree error
                    if os.path.exists(dst_vscode):
                        shutil.rmtree(dst_vscode)
                    shutil.copytree(src_vscode, dst_vscode)
                except Exception as e:
                    logger.error(f"Unable to backup .vscode folder for {project}: {e}")


def do_deployments_backup(backup_location: str) -> None:
    """Perform deployments backup.

    Args:
        backup_location: Base backup location.
    """
    # Deployments environment variables
    deployments_destination_folder_name = get_env("DEPLOYMENTS_DESTINATION_FOLDER_NAME")
    deployment_source_paths = get_env("DEPLOYMENT_SOURCE_PATHS", True)
    # Check if there are defined deployments for backup
    if deployment_source_paths:

        def copy_directory_contents(source_dir, destination_dir):
            if not os.path.exists(source_dir):
                logger.error(
                    f"Error copying directory contents: Source directory '{source_dir}' does not exist."
                )
                return

            try:
                shutil.copytree(source_dir, destination_dir)
            except shutil.Error as e:
                logger.error(f"Error copying directory: {e}")
            except OSError as e:
                logger.error(f"OS Error: {e}")

        # Delete old deployments destination folder (with files) and create new
        deployments_dir = os.path.join(
            backup_location, str(deployments_destination_folder_name)
        )
        sudo_rmtree(deployments_dir)
        sudo_makedirs(deployments_dir)
        # Deployments backup
        deployments_dir = os.path.join(
            backup_location, str(deployments_destination_folder_name)
        )
        for deployment in deployment_source_paths:
            try:
                copy_directory_contents(
                    deployment,
                    deployments_dir + "/" + get_parent_folder_name(deployment),
                )
            except Exception as e:
                logger.error(f"Unable to backup deployment {deployment}: {e}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Backup documents on Linux machine.")
    return parser.parse_args()


def main() -> None:
    """Main entry point for the script."""
    # Defining argument parser
    parse_arguments()
    # Load environment variables from .env file if present
    load_dotenv()
    # Loading environment variables
    backup_location = get_env("BACKUP_LOCATION")
    # Do backups
    assert isinstance(backup_location, str)
    do_simple_backup(backup_location, ["SYSTEM", "VSCODE"])
    do_projects_backup(backup_location)
    do_deployments_backup(backup_location)
    # Display message
    logger.info("Completed all backup steps.")


if __name__ == "__main__":
    run_script(main)
