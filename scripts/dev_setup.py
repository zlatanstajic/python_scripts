#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import os
import re
import subprocess
import sys

import pyperclip  # type: ignore
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.arguments_helper import missing_required_arguments  # type: ignore
from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import finish_script, run_script  # type: ignore

logger = setup_logging(__name__)


def issue_name_for_branch(issue_name: str) -> str:
    """Convert issue name to branch-friendly format.

    Args:
        issue_name: The issue name.

    Returns:
        Formatted branch name.
    """
    if re.search(r"\d", issue_name):
        finish_script(True, "Issue name cannot contain numbers.")

    name = (
        issue_name.replace(" ", "_")
        .replace("&", "_and_")
        .replace("|", "_-_")
        .replace(".", "_dot_")
        .replace("/", "_forward-slash_")
    )
    return name.lower()


def is_git_repository() -> None:
    """Check if current directory is a git repository."""
    if not os.path.isdir(".git"):
        raise Exception("This script must be run in a git repository directory.")


def get_current_directory() -> None:
    """Print the current directory name."""
    current_directory = os.path.basename(os.getcwd())
    logger.info(f"Located in directory: {current_directory}\n")


def user_input(message: str) -> str:
    """Get user input with message.

    Args:
        message: The prompt message.

    Returns:
        User input.
    """
    return input(f"{message}: ")


def do_you_wish_to_proceed() -> bool:
    """Ask user if they wish to proceed.

    Returns:
        True if yes, False if no.
    """
    while True:
        yn = input("Do you wish to proceed? [y/n]: ").strip().lower()
        if yn in ("y", "yes"):
            return True
        elif yn in ("n", "no"):
            return False


def get_git_branches() -> list[str]:
    """Get list of git branches.

    Returns:
        List of branch names.
    """
    result = subprocess.run(["git", "branch", "--list"], capture_output=True, text=True)
    if result.returncode != 0:
        finish_script(True, "Unable to list git branches.")
    # Remove the '*' from the current branch and strip whitespace
    branches = [
        line.replace("*", "").strip() for line in result.stdout.strip().split("\n")
    ]
    return [b for b in branches if b]


def select_branch(branches: list[str]) -> str:
    """Select a branch interactively.

    Args:
        branches: List of available branches.

    Returns:
        Selected branch name.
    """
    logger.info("Available branches:")
    for idx, branch in enumerate(branches, 1):
        logger.info(f"{idx}. {branch}")
    while True:
        try:
            choice = int(
                user_input("\nSelect the branch number to create new branch from")
            )
            if 1 <= choice <= len(branches):
                return branches[choice - 1]
            else:
                logger.warning("Invalid selection. Please enter a valid number.")
        except ValueError:
            logger.warning("Invalid input. Please enter a number.")


def get_target_branch(branch_prefix: str, number: int, name: str) -> str:
    """Get the target branch name.

    Args:
        branch_prefix: Prefix for branch.
        number: Issue number.
        name: Issue name.

    Returns:
        Target branch name.
    """
    return f"{branch_prefix}/{number}_{issue_name_for_branch(name)}"


def read_environment_variables() -> tuple[str, str, str]:
    """Read environment variables.

    Returns:
        Tuple of branch_prefix, request_prefix, issue_base_path.
    """
    branch_prefix = os.getenv("BRANCH_PREFIX", "issues")
    request_prefix = os.getenv("REQUEST_PREFIX", "refs:")
    issue_base_path = os.getenv("ISSUE_BASE_PATH", "")
    return branch_prefix, request_prefix, issue_base_path


def checkout_source_branch(source_branch: str) -> None:
    """Checkout to source branch.

    Args:
        source_branch: Branch to checkout.
    """
    result = subprocess.run(["git", "checkout", source_branch])
    if result.returncode != 0:
        finish_script(True, f"Not able to checkout to the {source_branch}")


def push_to_target_branch(target_branch: str) -> None:
    """Push target branch to remote.

    Args:
        target_branch: Branch to push.
    """
    subprocess.run(["git", "push", "-u", "origin", target_branch])


def create_and_checkout_new_branch(target_branch: str) -> None:
    """Create and checkout new branch.

    Args:
        target_branch: Branch to create.
    """
    subprocess.run(["git", "pull"])
    subprocess.run(["git", "branch", target_branch])
    subprocess.run(["git", "checkout", target_branch])


def delete_new_branch_and_checkout_to_source_branch(
    source_branch: str, target_branch: str
) -> None:
    """Delete new branch and checkout to source.

    Args:
        source_branch: Source branch.
        target_branch: Target branch to delete.
    """
    subprocess.run(["git", "checkout", source_branch])
    subprocess.run(["git", "branch", "-D", target_branch])


def create_message_name(request_prefix: str, number: int, name: str) -> str:
    """Create commit message name.

    Args:
        request_prefix: Prefix for request.
        number: Issue number.
        name: Issue name.

    Returns:
        Message name.
    """
    return f"{request_prefix} #{number} {name}\n"


def create_message_description(
    issue_base_path: str, branch_prefix: str, number: int
) -> str:
    """Create commit message description.

    Args:
        issue_base_path: Base path for issues.
        branch_prefix: Branch prefix.
        number: Issue number.

    Returns:
        Message description.
    """
    if issue_base_path:
        issue_base_path_value = issue_base_path
        if issue_base_path.startswith("https://github.com/"):
            # Split and check if there's a username part
            parts = issue_base_path.rstrip("/").split("/")
            if len(parts) == 4:  # ['https:', '', 'github.com', 'username']
                repo_url = f"{issue_base_path.rstrip('/')}/{os.path.basename(os.getcwd())}/issues"
                issue_base_path_value = repo_url
            else:
                logger.warning(
                    f"Couldn't determine GitHub issue path from: {issue_base_path}"
                )
        # Construct message description
        return f"Based on {branch_prefix} [#{number}]({issue_base_path_value}/{number})"
    return ""


def handle_copy_to_clipboard(message_name: str, message_description: str) -> None:
    """Handle copying messages to clipboard.

    Args:
        message_name: The name message.
        message_description: The description message.
    """
    try:
        # Copy to clipboard is best if you have installed
        # https://github.com/diodon-dev/diodon on your system.
        if message_description:
            pyperclip.copy(message_description)
            logger.info(
                f"\nCopied message description to the clipboard:\n\n{message_description}"
            )
        pyperclip.copy(message_name)
        logger.info(f"\nCopied message name info to the clipboard:\n\n{message_name}")
    except pyperclip.PyperclipException:
        logger.warning(
            "Warning: Could not copy to clipboard. Please install xclip/xsel on Linux."
        )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Development setup for git. Creates a new branch for an issue and pushes it to remote.",
    )
    parser.add_argument("-nu", "--number", type=int, help="Issue number (required)")
    parser.add_argument("-na", "--name", type=str, help="Issue name (required)")
    args = parser.parse_args()
    if not args.number or not args.name:
        missing_required_arguments()
    return args


def main() -> None:
    """Main entry point for the script."""
    args = parse_arguments()
    load_dotenv()
    get_current_directory()
    is_git_repository()

    branch_prefix, request_prefix, issue_base_path = read_environment_variables()
    source_branch = select_branch(get_git_branches())
    target_branch = get_target_branch(branch_prefix, args.number, args.name)

    logger.info(f"Will create branch {target_branch} from {source_branch}\n")

    if not do_you_wish_to_proceed():
        finish_script()

    checkout_source_branch(source_branch)
    create_and_checkout_new_branch(target_branch)

    logger.info("\nWill push local branch to remote")

    if do_you_wish_to_proceed():
        push_to_target_branch(target_branch)
        handle_copy_to_clipboard(
            create_message_name(request_prefix, args.number, args.name),
            create_message_description(issue_base_path, branch_prefix, args.number),
        )
    else:
        delete_new_branch_and_checkout_to_source_branch(source_branch, target_branch)

    finish_script()


if __name__ == "__main__":
    run_script(main)
