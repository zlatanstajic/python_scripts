# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

"""Logging configuration and utilities for the python_scripts package."""

import logging
import sys


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up and return a logger instance.

    Args:
        name: The name of the logger (typically __name__).
        level: The logging level (default: logging.INFO).

    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Only add handler if logger doesn't already have one
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
