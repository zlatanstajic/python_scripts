import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.restore_vscode_folder import (
    check_if_vscode_folder_already_exits,
    do_restore_operation,
    main,
    parse_arguments,
    read_environment_variables,
)


class TestReadEnvironmentVariables:
    @patch.dict(
        os.environ,
        {"BACKUP_LOCATION": "/backup", "PROJECTS_DESTINATION_FOLDER_NAME": "projects"},
    )
    def test_read_environment_variables(self):
        backup, projects = read_environment_variables()
        assert backup == "/backup"
        assert projects == "projects"


class TestCheckIfVscodeFolderAlreadyExits:
    @patch("os.path.isdir", return_value=True)
    @patch("scripts.restore_vscode_folder.finish_script")
    def test_check_if_vscode_folder_already_exists(self, mock_finish, mock_isdir):
        check_if_vscode_folder_already_exits("/path/.vscode", "/path")
        mock_finish.assert_called_once()

    @patch("os.path.isdir", return_value=False)
    def test_check_if_vscode_folder_not_exists(self, mock_isdir):
        check_if_vscode_folder_already_exits("/path/.vscode", "/path")


class TestDoRestoreOperation:
    @patch("shutil.copytree")
    @patch("builtins.print")
    def test_do_restore_operation(self, mock_print, mock_copytree):
        do_restore_operation("/path/.vscode", "/path", ".vscode", "/backup", "projects")


class TestParseArguments:
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments(self, mock_parse):
        mock_args = MagicMock()
        mock_parse.return_value = mock_args
        args = parse_arguments()
        assert args == mock_args


# Main test
@patch("scripts.restore_vscode_folder.parse_arguments")
@patch("scripts.restore_vscode_folder.load_dotenv")
@patch("os.getcwd", return_value="/path")
@patch("scripts.restore_vscode_folder.check_if_vscode_folder_already_exits")
@patch(
    "scripts.restore_vscode_folder.read_environment_variables",
    return_value=("/backup", "projects"),
)
@patch("scripts.restore_vscode_folder.do_restore_operation")
def test_main(
    mock_do_restore, mock_read_env, mock_check, mock_getcwd, mock_load, mock_parse
):
    main()
