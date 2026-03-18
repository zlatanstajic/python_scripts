import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.php_switch import (
    build_version_map,
    extract_version_from_path,
    get_installed_php_versions,
    handle_nonexistent_version_argument,
    interactive_version_pick,
    main,
    parse_arguments,
    switch_php_version,
)


class TestExtractVersionFromPath:
    def test_extract_version_from_path_standard(self):
        assert extract_version_from_path("/usr/bin/php8.3") == "8.3"

    def test_extract_version_from_path_with_php(self):
        assert extract_version_from_path("/usr/bin/php8.2") == "8.2"

    def test_extract_version_from_path_no_match(self):
        assert extract_version_from_path("/usr/bin/php") is None


class TestBuildVersionMap:
    def test_build_version_map(self):
        paths = ["/usr/bin/php8.3", "/usr/bin/php8.2"]
        version_map = build_version_map(paths)
        assert version_map == {"8.3": "/usr/bin/php8.3", "8.2": "/usr/bin/php8.2"}


class TestGetInstalledPhpVersions:
    @patch("subprocess.run")
    def test_get_installed_php_versions_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/bin/php8.3\n/usr/bin/php8.2\n"
        mock_run.return_value = mock_result
        versions = get_installed_php_versions()
        assert versions == ["/usr/bin/php8.3", "/usr/bin/php8.2"]

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_get_installed_php_versions_error(self, mock_print, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        versions = get_installed_php_versions()
        assert versions == []


class TestSwitchPhpVersion:
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_switch_php_version_success(self, mock_print, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        switch_php_version("/usr/bin/php8.3")
        # Assert calls

    # Add more tests as needed


class TestHandleNonexistentVersionArgument:
    @patch("builtins.print")
    @patch("scripts.php_switch.finish_script")
    def test_handle_nonexistent_version_argument(self, mock_finish, mock_print):
        version_map = {"8.3": "/usr/bin/php8.3"}
        handle_nonexistent_version_argument(version_map, "8.2")
        mock_finish.assert_called_once()


class TestInteractiveVersionPick:
    @patch("builtins.input", return_value="1")
    @patch("scripts.php_switch.switch_php_version")
    @patch("builtins.print")
    def test_interactive_version_pick(self, mock_print, mock_switch, mock_input):
        version_map = {"8.3": "/usr/bin/php8.3"}
        interactive_version_pick(version_map)
        mock_switch.assert_called_once_with("/usr/bin/php8.3")


class TestParseArguments:
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments(self, mock_parse):
        mock_args = MagicMock()
        mock_args.version = "8.3"
        mock_parse.return_value = mock_args
        args = parse_arguments()
        assert args.version == "8.3"


# Main test would require heavy mocking
