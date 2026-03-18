#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT


def missing_required_arguments() -> None:
    """Raise an error for missing required arguments."""
    raise ValueError(
        "Missing required arguments! Use -h or --help to see which ones..."
    )


class ArgumentsHelper:
    """Helper class for argument validation."""

    @staticmethod
    def missing_required_arguments_message() -> None:
        """Raise missing arguments error."""
        missing_required_arguments()
