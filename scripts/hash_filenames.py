#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import json
import os
import random
import string
import sys

from dotenv import load_dotenv  # Add this import at the top

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import finish_script, run_script  # type: ignore

logger = setup_logging(__name__)

MAPPING_FILENAME = "hash_filenames_mapping.txt"


def get_file_extensions():
    """Get target file extensions from environment variable."""
    load_dotenv()  # Load environment variables from .env
    exts = os.getenv("HASH_FILENAMES_FILE_EXTENSIONS")
    if exts:
        # Split by comma, strip whitespace, ensure dot prefix
        return {
            e if e.startswith(".") else "." + e
            for e in [x.strip().lower() for x in exts.split(",") if x.strip()]
        }
    else:
        finish_script(
            True,
            "Environment variable HASH_FILENAMES_FILE_EXTENSIONS not set.",
        )


def load_mapping(mapping_file):
    """Load existing mappings from file."""
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_mapping(mapping_file, mappings):
    """Save mappings to file only if there are mappings to save."""
    if not mappings:
        return

    try:
        with open(mapping_file, "w") as f:
            json.dump(mappings, f, indent=2)
    except IOError as e:
        logger.warning(f"Could not save mapping file: {e}")


def get_mapping_file_path(directory):
    """Get the path to the mapping file for a directory."""
    return os.path.join(directory, MAPPING_FILENAME)


def is_file_in_mapping(mapping, filename):
    """Check if a file is already in the mapping (by original filename)."""
    return filename in mapping


def generate_random_hash(length=10):
    """Generate a random alphanumeric hash string."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def is_hashed(filename, length=10):
    """Check if a filename appears to already be hashed."""
    name, _ = os.path.splitext(filename)
    return len(name) == length and all(
        c in string.ascii_letters + string.digits for c in name
    )


def hash_files(directory, verbose=False):
    """Rename files in a directory with random hash names."""
    file_extensions = get_file_extensions()
    mapping_file = get_mapping_file_path(directory)
    mappings = load_mapping(mapping_file)

    for root, _, files in os.walk(directory):
        for filename in files:
            # Skip mapping file itself
            if filename == MAPPING_FILENAME:
                continue

            file_ext = os.path.splitext(filename)[1].lower()

            # Skip if not in target extensions
            if file_ext not in file_extensions:
                continue

            # Skip if already in mapping (already hashed)
            if is_file_in_mapping(mappings, filename):
                if verbose:
                    logger.info(f"Skipped (already hashed): {filename}")
                continue

            # Skip if filename already looks hashed
            if is_hashed(filename):
                if verbose:
                    logger.info(f"Skipped (already hashed): {filename}")
                continue

            new_name = generate_random_hash() + file_ext
            old_path = os.path.join(root, filename)
            new_path = os.path.join(root, new_name)

            # Avoid overwriting existing files
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                # Add to mapping
                mappings[filename] = new_name
                if verbose:
                    logger.info(f"Renamed: {old_path} -> {new_path}")
            else:
                if verbose:
                    logger.info(f"Skipped (target exists): {old_path} -> {new_path}")

        # Save mapping file after processing each directory
        save_mapping(mapping_file, mappings)


def move_hashed_files(directory, verbose=False):
    """Move hashed files into numbered batch folders."""
    file_extensions = get_file_extensions()
    hashed_files = []

    for root, _, files in os.walk(directory):
        for filename in files:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in file_extensions and is_hashed(filename):
                hashed_files.append(os.path.join(root, filename))

    batch_size = 100
    for i in range(0, len(hashed_files), batch_size):
        batch = hashed_files[i : i + batch_size]
        folder_num = (i // batch_size) + 1
        folder_name = f"hashed_{folder_num:03d}"
        target_folder = os.path.join(directory, folder_name)
        os.makedirs(target_folder, exist_ok=True)
        for file_path in batch:
            dest_path = os.path.join(target_folder, os.path.basename(file_path))
            os.rename(file_path, dest_path)
            if verbose:
                logger.info(f"Moved: {file_path} -> {dest_path}")

    # After all batches, check and remove any empty hashed_ folders in the script's running directory
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if (
            os.path.isdir(item_path)
            and item.startswith("hashed_")
            and not os.listdir(item_path)
        ):
            os.rmdir(item_path)
            if verbose:
                logger.info(f"Deleted empty folder: {item_path}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Renames files in the given directory with hash name that are not already hashed.",
    )
    parser.add_argument(
        "-d",
        "--directory",
        required=False,
        default=os.getcwd(),
        help="Path to the directory containing files to rename. Defaults to current directory.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )
    parser.add_argument(
        "-m",
        "--move",
        action="store_true",
        help="Move hashed files to hashed_00X folder.",
    )
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    args = parse_arguments()
    hash_files(args.directory, args.verbose)
    if args.move:
        move_hashed_files(args.directory, args.verbose)


if __name__ == "__main__":
    run_script(main)
