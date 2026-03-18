import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch  # noqa: E402

import pyperclip  # noqa: E402
import pytest  # noqa: E402

from scripts.generate_password import (  # noqa: E402
    generate_password,
    main,
    parse_arguments,
)


class TestGeneratePassword:
    def test_generate_password_valid_length(self):
        password = generate_password(8, 4, 20)
        assert len(password) == 20
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" for c in password)

    def test_generate_password_minimum_length(self):
        password = generate_password(8, 4, 8)
        assert len(password) == 8

    def test_generate_password_too_short(self):
        with pytest.raises(
            Exception, match="Please enter length greater than or equal to 8"
        ):
            generate_password(8, 4, 4)

    def test_generate_password_not_divisible(self):
        with pytest.raises(Exception, match="Please enter length divisible by 4"):
            generate_password(8, 4, 10)


class TestParseArguments:
    @patch("sys.argv", ["script"])
    def test_parse_arguments_default(self):
        args = parse_arguments(8, 4)
        assert args.length == 20

    @patch("sys.argv", ["script", "-l", "16"])
    def test_parse_arguments_custom_length(self):
        args = parse_arguments(8, 4)
        assert args.length == 16


class TestMain:
    @patch("scripts.generate_password.pyperclip.copy")
    @patch("scripts.generate_password.logger")
    @patch("scripts.generate_password.parse_arguments")
    @patch("scripts.generate_password.generate_password")
    def test_main_success(self, mock_gen_pass, mock_parse_args, mock_logger, mock_copy):
        mock_parse_args.return_value.length = 20
        mock_gen_pass.return_value = "testpassword"

        main()

        mock_gen_pass.assert_called_once_with(8, 4, 20)
        mock_copy.assert_called_once_with("testpassword")
        mock_logger.info.assert_called_once_with("testpassword")

    @patch(
        "scripts.generate_password.pyperclip.copy",
        side_effect=pyperclip.PyperclipException("Clipboard error"),
    )
    @patch("scripts.generate_password.logger")
    @patch("scripts.generate_password.parse_arguments")
    @patch("scripts.generate_password.generate_password")
    def test_main_clipboard_error(
        self, mock_gen_pass, mock_parse_args, mock_logger, mock_copy
    ):
        mock_parse_args.return_value.length = 20
        mock_gen_pass.return_value = "testpassword"

        main()

        mock_logger.info.assert_called_with("testpassword")
        mock_logger.warning.assert_called_with(
            "Could not copy to clipboard. Please install xclip/xsel on Linux."
        )
