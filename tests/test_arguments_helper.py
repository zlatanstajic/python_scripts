"""Tests for src/helpers/arguments_helper.py."""

import pytest

from src.helpers.arguments_helper import ArgumentsHelper, missing_required_arguments


class TestMissingRequiredArguments:
    """Tests for the module-level missing_required_arguments function."""

    def test_raises_value_error(self):
        """Verify the function raises ValueError."""
        with pytest.raises(ValueError):
            missing_required_arguments()

    def test_error_message_content(self):
        """Verify the error message mentions --help."""
        with pytest.raises(ValueError, match="--help"):
            missing_required_arguments()


class TestArgumentsHelperMissingRequiredArgumentsMessage:
    """Tests for ArgumentsHelper.missing_required_arguments_message."""

    def test_raises_value_error(self):
        """Verify the static method raises ValueError."""
        with pytest.raises(ValueError):
            ArgumentsHelper.missing_required_arguments_message()

    def test_error_message_content(self):
        """Verify the error message mentions --help."""
        with pytest.raises(ValueError, match="--help"):
            ArgumentsHelper.missing_required_arguments_message()
