import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.git_copy import (
    display_directory_name,
    do_copy_files_and_folders,
    get_default_target_directory_path,
    get_last_two_git_hashes,
    get_string_env,
    is_git_repository,
    main,
    parse_arguments,
    print_commit_hash_usage,
    zip_copied_files,
)


class TestIsGitRepository:
    @patch("os.path.isdir", return_value=True)
    def test_is_git_repository_exists(self, mock_isdir):
        is_git_repository()

    @patch("os.path.isdir", return_value=False)
    def test_is_git_repository_not_exists(self, mock_isdir):
        with pytest.raises(Exception):
            is_git_repository()


class TestDisplayDirectoryName:
    @patch("os.getcwd", return_value="/path/to/dir")
    @patch("os.path.basename", return_value="dir")
    @patch("builtins.print")
    def test_display_directory_name(self, mock_print, mock_basename, mock_getcwd):
        display_directory_name()


class TestGetStringEnv:
    @patch.dict(os.environ, {"VAR": "value"})
    def test_get_string_env(self):
        assert get_string_env("VAR") == "value"

    def test_get_string_env_missing(self):
        with pytest.raises(ValueError):
            get_string_env("MISSING")


class TestGetLastTwoGitHashes:
    @patch("subprocess.run")
    def test_get_last_two_git_hashes(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "hash1\nhash2\n"
        mock_run.return_value = mock_result
        start, end = get_last_two_git_hashes()
        assert start == "hash2"
        assert end == "hash1"


class TestPrintCommitHashUsage:
    @patch("builtins.print")
    def test_print_commit_hash_usage(self, mock_print):
        print_commit_hash_usage("start", "end", "start", "end")


class TestGetDefaultTargetDirectoryPath:
    @patch("scripts.git_copy.get_string_env", return_value="/target")
    @patch("os.path.basename", return_value="repo")
    def test_get_default_target_directory_path(self, mock_basename, mock_get_env):
        path = get_default_target_directory_path()
        assert path == "/target/repo"


class TestDoCopyFilesAndFolders:
    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("shutil.copy2")
    @patch("os.path.isdir", return_value=True)
    @patch("shutil.copytree")
    @patch("builtins.print")
    def test_do_copy_files_and_folders(
        self, mock_print, mock_copytree, mock_isdir, mock_copy2, mock_makedirs, mock_run
    ):
        mock_result = MagicMock()
        mock_result.stdout = "file1.txt\nfile2.txt\n"
        mock_run.return_value = mock_result
        do_copy_files_and_folders("start", "end", "/target")


class TestZipCopiedFiles:
    @patch("datetime.datetime")
    @patch("zipfile.ZipFile")
    @patch("os.walk")
    @patch("shutil.rmtree")
    @patch("builtins.print")
    def test_zip_copied_files(
        self, mock_print, mock_rmtree, mock_walk, mock_zipfile, mock_datetime
    ):
        mock_datetime.now.return_value.strftime.return_value = "20231010_120000"
        zip_copied_files("/target")


class TestParseArguments:
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments(self, mock_parse):
        mock_args = MagicMock()
        mock_parse.return_value = mock_args
        args = parse_arguments("start", "end", "/target")
        assert args == mock_args


# Main test would require heavy mocking
