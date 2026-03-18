#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import os
import re
import subprocess
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import finish_script, run_script  # type: ignore

logger = setup_logging(__name__)


def get_installed_php_versions() -> list[str]:
    """Get list of installed PHP version paths."""
    result = subprocess.run(
        ["update-alternatives", "--list", "php"], capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error("Could not list PHP versions.")
        return []
    php_paths = result.stdout.strip().split("\n")
    if not php_paths:
        raise Exception("No PHP versions found.")
    return php_paths


def extract_version_from_path(php_path: str) -> str | None:
    """Extract version from path.

    Args:
        php_path: The path to the PHP binary.

    Returns:
        The version string or None if not found.
    """
    # Try to extract version like 8.3, 8.2, 7.4, etc.
    match = re.search(r"php(?:/|)(\d+\.\d+)", php_path)
    if match:
        return match.group(1)
    # Fallback: try to extract from filename
    match = re.search(r"php(\d+\.\d+)", php_path)
    if match:
        return match.group(1)
    return None


def build_version_map(php_paths: list[str]) -> dict[str, str]:
    """Build map of version to path.

    Args:
        php_paths: List of PHP paths.

    Returns:
        Dictionary mapping version to path.
    """
    version_map = {}
    for path in php_paths:
        version = extract_version_from_path(path)
        if version:
            version_map[version] = path
    return version_map


def switch_php_version(php_path: str) -> None:
    """Switch to the given PHP version.

    Args:
        php_path: The path to the PHP version to switch to.
    """
    # Get the currently set PHP alternative
    current_result = subprocess.run(
        ["update-alternatives", "--query", "php"], capture_output=True, text=True
    )
    current_path = None
    if current_result.returncode == 0:
        for line in current_result.stdout.splitlines():
            if line.startswith("Value:"):
                current_path = line.split(":", 1)[1].strip()
                break

    if current_path:
        logger.info(f"Currently set PHP version: {current_path}")
        if current_path == php_path:
            logger.info("The selected PHP version is already set. No changes made.")
            return

    result = subprocess.run(
        ["sudo", "update-alternatives", "--set", "php", php_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"Could not switch to PHP version at {php_path}.")
        logger.error(result.stderr)
    else:
        logger.info(f"✅ Successfully switched to PHP version at {php_path}.")
        # Display the current PHP version
        version_result = subprocess.run(
            ["php", "--version"], capture_output=True, text=True
        )
        if version_result.returncode == 0:
            logger.info("Current PHP version:")
            logger.info(version_result.stdout)
        else:
            logger.error("Could not display PHP version.")


def handle_nonexistent_version_argument(
    version_map: dict[str, str], version: str
) -> None:
    """Handle error for nonexistent version.

    Args:
        version_map: Map of versions to paths.
        version: The requested version.
    """
    logger.error(f"PHP version {version} is not among the installed alternatives.")
    logger.info("Installed PHP versions:")
    for v in sorted(version_map):
        logger.info(f"- {v} ({version_map[v]})")
    finish_script(True, "Please pick one of the installed PHP versions.")


def interactive_version_pick(version_map: dict[str, str]) -> None:
    """Interactive pick of version.

    Args:
        version_map: Map of versions to paths.
    """
    logger.info("Installed PHP versions:")
    for i, (v, path) in enumerate(sorted(version_map.items()), 1):
        logger.info(f"{i}. PHP {v} ({path})")

    try:
        choice = int(input("Select the PHP version to switch to (by number): "))
        versions = list(sorted(version_map.items()))
        if 1 <= choice <= len(versions):
            switch_php_version(versions[choice - 1][1])
        else:
            finish_script(True, "Invalid choice.")
    except ValueError:
        finish_script(True, "Invalid input. Please enter a number.")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Switch between installed PHP versions using update-alternatives. "
        "The script will only allow switching to a version that is already installed on your system."
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        help="PHP version to switch to (e.g., 8.3, 8.2, 7.4). Must be one of the installed alternatives. (optional)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the script."""
    args = parse_arguments()
    php_paths = get_installed_php_versions()
    version_map = build_version_map(php_paths)

    if args.version:
        if args.version not in version_map:
            handle_nonexistent_version_argument(version_map, args.version)
        else:
            switch_php_version(version_map[args.version])
    else:
        interactive_version_pick(version_map)


if __name__ == "__main__":
    run_script(main)
