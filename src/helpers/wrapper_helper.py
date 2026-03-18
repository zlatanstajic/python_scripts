#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import logging
import sys
from typing import Callable

logger = logging.getLogger(__name__)


def run_script(function: Callable[[], None]) -> None:
    """Run a script function with error handling.

    Args:
        function: The main function to run.
    """
    try:
        function()
    except EOFError:
        finish_script(False, "Script canceled. Exiting.")
    except KeyboardInterrupt:
        finish_script(False, "Script interrupted by user (Ctrl+C). Exiting.")
    except Exception as e:
        finish_script(True, f"Error: {e}")


def finish_script(is_with_error: bool = False, details: str = "") -> None:
    """Finish the script with status.

    Args:
        is_with_error: Whether there was an error.
        details: Additional details.
    """
    status = "ERROR" if is_with_error else "OK"
    suffix = f" - {details}" if details else ""
    logger.info(f"\n\nScript finishing {status}{suffix}")
    sys.exit(int(is_with_error))


class WrapperHelper:
    """Helper class for script lifecycle management."""

    @staticmethod
    def end(is_with_error: bool = False, details: str = "") -> None:
        """End the script.

        Args:
            is_with_error: Whether there was an error.
            details: Additional details.
        """
        finish_script(is_with_error, details)

    @staticmethod
    def main(function: Callable[[], None]) -> None:
        """Run the main function.

        Args:
            function: The function to run.
        """
        run_script(function)
