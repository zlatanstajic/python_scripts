#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import zipfile

from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import run_script  # type: ignore

logger = setup_logging(__name__)


def is_git_repository():
    """Verify the current directory is a git repository."""
    if not os.path.isdir(".git"):
        raise Exception("This script must be run in a git repository directory.")


def display_directory_name():
    """Display the current working directory name."""
    cwd = os.getcwd()
    dir_name = os.path.basename(cwd)
    logger.info(f"Current directory: {dir_name}")


def get_string_env(var_name):
    """Get a required string environment variable."""
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(
            f"Error: Required environment variable '{var_name}' is not set."
        )
    return value


def get_last_two_git_hashes():
    """Get the penultimate and last git commit hashes."""
    result = subprocess.run(
        ["git", "rev-list", "--max-count=2", "HEAD"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    hashes = result.stdout.strip().split("\n")
    if len(hashes) < 2:
        raise Exception("Repository must have at least two commits.")
    return hashes[1], hashes[0]  # penultimate, last


def print_commit_hash_usage(
    start_commit_hash,
    end_commit_hash,
    default_start_commit_hash,
    default_end_commit_hash,
):
    """Log whether default or provided commit hashes are being used."""
    used_default_start = start_commit_hash == default_start_commit_hash
    used_default_end = end_commit_hash == default_end_commit_hash

    if used_default_start:
        logger.info(
            f"Using default start_commit_hash (penultimate): {default_start_commit_hash}"
        )
    else:
        logger.info(f"Using provided start_commit_hash: {start_commit_hash}")

    if used_default_end:
        logger.info(f"Using default end_commit_hash (last): {default_end_commit_hash}")
    else:
        logger.info(f"Using provided end_commit_hash: {end_commit_hash}")


def get_default_target_directory_path():
    """Get the default target directory path from environment."""
    return get_string_env("TARGET_DIRECTORY_PATH") + f"/{os.path.basename(os.getcwd())}"


def do_copy_files_and_folders(
    start_commit_hash, end_commit_hash, target_directory_path
):
    """Copy changed files between two commits to the target directory."""
    # Get the list of changed files between two commits
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            start_commit_hash,
            end_commit_hash,
        ],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    files = result.stdout.strip().split("\n")

    if not any(file_path for file_path in files if file_path):
        raise Exception("No changed files to copy.")

    for file_path in files:
        if not file_path:
            continue
        target_path = os.path.join(target_directory_path, file_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        try:
            shutil.copy2(file_path, target_path)
        except Exception as e:
            logger.warning(f"Could not copy {file_path}: {e}")

    # Always copy the .vscode folder if it exists
    if os.path.isdir(".vscode"):
        vscode_target = os.path.join(target_directory_path, ".vscode")
        if os.path.exists(vscode_target):
            shutil.rmtree(vscode_target)
        shutil.copytree(".vscode", vscode_target)
        logger.info(f".vscode folder copied to {vscode_target}")

    logger.info(f"Files copied to {target_directory_path} directory")


def zip_copied_files(target_directory_path):
    """Zip the copied files directory and remove the original."""
    # Add datetime to zip filename
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = f"{target_directory_path}_{now_str}.zip"
    logger.info(f"Zipping folder {target_directory_path} to {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_directory_path):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(
                    abs_path, os.path.dirname(target_directory_path)
                )
                zipf.write(abs_path, rel_path)
    logger.info(f"Zipped folder created at {zip_path}")
    # Delete the copied folder after zipping
    shutil.rmtree(target_directory_path)
    logger.info(f"Deleted copied folder: {target_directory_path}")


def parse_arguments(
    default_start_commit_hash, default_end_commit_hash, default_target_directory_path
):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Copy all differences between two git commits.",
    )
    parser.add_argument(
        "-s",
        "--start_commit_hash",
        type=str,
        default=default_start_commit_hash,
        help=f"Start commit hash (default: penultimate commit {default_start_commit_hash}) (optional)",
    )
    parser.add_argument(
        "-e",
        "--end_commit_hash",
        type=str,
        default=default_end_commit_hash,
        help=f"End commit hash (default: last commit {default_end_commit_hash}) (optional)",
    )
    parser.add_argument(
        "-t",
        "--target_directory_path",
        type=str,
        default=default_target_directory_path,
        help=f"Target directory to copy files to (default: {default_target_directory_path}) (optional)",
    )

    return parser.parse_args()


def main():
    """Main entry point for the script."""
    load_dotenv()

    default_start_commit_hash, default_end_commit_hash = get_last_two_git_hashes()

    args = parse_arguments(
        default_start_commit_hash,
        default_end_commit_hash,
        get_default_target_directory_path(),
    )

    # Inform user if defaults are being used
    print_commit_hash_usage(
        args.start_commit_hash,
        args.end_commit_hash,
        default_start_commit_hash,
        default_end_commit_hash,
    )

    display_directory_name()
    is_git_repository()
    do_copy_files_and_folders(
        args.start_commit_hash, args.end_commit_hash, args.target_directory_path
    )
    zip_copied_files(args.target_directory_path)


if __name__ == "__main__":
    run_script(main)
