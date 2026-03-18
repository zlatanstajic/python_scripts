#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import os
import random
import string
import sys

import pyperclip  # type: ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import run_script  # type: ignore

logger = setup_logging(__name__)


def generate_password(
    minimum_password_length: int, number_of_chunks: int, length: int = 20
) -> str:
    """Generate a random password of specified length.

    Args:
        minimum_password_length: The minimum allowed length.
        number_of_chunks: Number of character types to use.
        length: The desired password length.

    Returns:
        A randomly generated password string.

    Raises:
        ValueError: If length is too short or not divisible by number_of_chunks.
    """
    if length < minimum_password_length:
        raise ValueError(
            f"Please enter length greater than or equal to {minimum_password_length}."
        )
    if length % number_of_chunks != 0:
        raise ValueError(
            f"Please enter length divisible by {number_of_chunks} like: 8, 12, 16, 20, 24, 28, 32..."
        )

    chunks = [
        string.ascii_lowercase,
        string.ascii_uppercase,
        string.digits,
        string.punctuation,
    ]
    random.shuffle(chunks)

    password = ""
    for chunk in chunks:
        password += "".join(random.sample(chunk, (length // 4)))

    return password


def parse_arguments(
    minimum_password_length: int, number_of_chunks: int
) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        minimum_password_length: Minimum password length for description.
        number_of_chunks: Number of chunks for description.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=f"Generate strong and secure password. Minimum length is {minimum_password_length} and must be divisible by {number_of_chunks}."
    )
    parser.add_argument(
        "-l", "--length", type=int, default=20, help="Length of the password (Optional)"
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the script."""
    minimum_password_length = 8
    number_of_chunks = 4

    args = parse_arguments(minimum_password_length, number_of_chunks)
    password = generate_password(minimum_password_length, number_of_chunks, args.length)

    try:
        pyperclip.copy(password)
    except pyperclip.PyperclipException:
        logger.warning(
            "Could not copy to clipboard. Please install xclip/xsel on Linux."
        )

    logger.info(password)


if __name__ == "__main__":
    run_script(main)
