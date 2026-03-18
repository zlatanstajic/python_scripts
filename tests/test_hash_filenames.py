import json
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.hash_filenames import (
    generate_random_hash,
    get_file_extensions,
    get_mapping_file_path,
    hash_files,
    is_file_in_mapping,
    is_hashed,
    load_mapping,
    main,
    move_hashed_files,
    parse_arguments,
    save_mapping,
)


class TestGetFileExtensions:
    @patch.dict(os.environ, {"HASH_FILENAMES_FILE_EXTENSIONS": ".jpg,.png"})
    def test_get_file_extensions(self):
        exts = get_file_extensions()
        assert exts == {".jpg", ".png"}


class TestLoadMapping:
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"old": "new"}')
    def test_load_mapping_exists(self, mock_file, mock_exists):
        mapping = load_mapping("mapping.txt")
        assert mapping == {"old": "new"}

    @patch("os.path.exists", return_value=False)
    def test_load_mapping_not_exists(self, mock_exists):
        mapping = load_mapping("mapping.txt")
        assert mapping == {}


class TestSaveMapping:
    @patch("builtins.open", new_callable=mock_open)
    def test_save_mapping(self, mock_file):
        save_mapping("mapping.txt", {"old": "new"})
        mock_file.assert_called_once()


class TestGetMappingFilePath:
    def test_get_mapping_file_path(self):
        path = get_mapping_file_path("/dir")
        assert path == "/dir/hash_filenames_mapping.txt"


class TestIsFileInMapping:
    def test_is_file_in_mapping(self):
        assert is_file_in_mapping({"file.jpg": "hash.jpg"}, "file.jpg") is True
        assert is_file_in_mapping({"file.jpg": "hash.jpg"}, "other.jpg") is False


class TestGenerateRandomHash:
    def test_generate_random_hash(self):
        hash_val = generate_random_hash(5)
        assert len(hash_val) == 5
        assert all(c.isalnum() for c in hash_val)


class TestIsHashed:
    def test_is_hashed_true(self):
        assert is_hashed("aB3kLm9QzX.jpg") is True

    def test_is_hashed_false(self):
        assert is_hashed("file.jpg") is False


class TestHashFiles:
    @patch("scripts.hash_filenames.get_file_extensions", return_value={".jpg"})
    @patch("scripts.hash_filenames.load_mapping", return_value={})
    @patch("scripts.hash_filenames.save_mapping")
    @patch("os.walk", return_value=[("/dir", [], ["file.jpg"])])
    @patch("os.rename")
    @patch("os.path.exists", return_value=False)
    def test_hash_files(
        self, mock_exists, mock_rename, mock_walk, mock_save, mock_load, mock_get_ext
    ):
        hash_files("/dir")
        # Assert rename called


class TestMoveHashedFiles:
    @patch("scripts.hash_filenames.get_file_extensions", return_value={".jpg"})
    @patch("os.walk", return_value=[("/dir", [], ["aB3kLm9QzX.jpg"])])
    @patch("os.makedirs")
    @patch("os.rename")
    @patch("os.listdir", return_value=["hashed_001"])
    @patch("os.path.isdir", return_value=True)
    @patch("os.rmdir")
    def test_move_hashed_files(
        self,
        mock_rmdir,
        mock_isdir,
        mock_listdir,
        mock_rename,
        mock_makedirs,
        mock_walk,
        mock_get_ext,
    ):
        move_hashed_files("/dir")
        # Assert moves


class TestParseArguments:
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments(self, mock_parse):
        mock_args = MagicMock()
        mock_args.directory = "/dir"
        mock_args.verbose = True
        mock_args.move = False
        mock_parse.return_value = mock_args
        args = parse_arguments()
        assert args.directory == "/dir"


# Main test
@patch("scripts.hash_filenames.parse_arguments")
@patch("scripts.hash_filenames.hash_files")
@patch("scripts.hash_filenames.move_hashed_files")
def test_main(mock_move, mock_hash, mock_parse):
    mock_args = MagicMock()
    mock_args.directory = "/dir"
    mock_args.verbose = False
    mock_args.move = True
    mock_parse.return_value = mock_args
    main()
    mock_hash.assert_called_once_with("/dir", False)
    mock_move.assert_called_once_with("/dir", False)
