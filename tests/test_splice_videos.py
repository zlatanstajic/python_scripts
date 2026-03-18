import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.splice_videos import (
    calculate_number_of_random_clips,
    concatenate_clips,
    create_available_block_indices,
    create_input_video_path,
    create_output_video_path,
    create_random_clips,
    create_random_clips_path,
    create_txt_file_for_concatenation,
    get_extension_os_path,
    get_video_duration,
    main,
    parse_arguments,
)


class TestGetExtensionOsPath:
    def test_get_extension_os_path(self):
        assert get_extension_os_path("video.mp4") == ".mp4"


class TestGetVideoDuration:
    @patch("subprocess.check_output")
    def test_get_video_duration(self, mock_check_output):
        mock_check_output.return_value = b"120.0\n"
        duration = get_video_duration("video.mp4")
        assert duration == 120.0


class TestCreateInputVideoPath:
    def test_create_input_video_path(self):
        path = create_input_video_path("video.mp4")
        assert path == "assets/inputs/video.mp4"


class TestCreateOutputVideoPath:
    def test_create_output_video_path(self):
        path = create_output_video_path("video.mp4")
        assert path == "assets/spliced/output_from_video.mp4"


class TestCreateRandomClipsPath:
    @patch("shutil.rmtree")
    @patch("os.makedirs")
    @patch("builtins.print")
    def test_create_random_clips_path(self, mock_print, mock_makedirs, mock_rmtree):
        path = create_random_clips_path()
        assert path == "assets/random_clips"


class TestCalculateNumberOfRandomClips:
    def test_calculate_number_of_random_clips(self):
        num = calculate_number_of_random_clips(120, 10, 3)
        assert num == 3


class TestCreateAvailableBlockIndices:
    def test_create_available_block_indices(self):
        indices = create_available_block_indices(120, 3, 10)
        assert isinstance(indices, list)


class TestCreateRandomClips:
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_create_random_clips(self, mock_print, mock_run):
        clips = []
        create_random_clips(2, 3, [1, 2], "path", clips, "input.mp4")
        assert len(clips) == 2


class TestCreateTxtFileForConcatenation:
    @patch("builtins.open", new_callable=MagicMock)
    def test_create_txt_file_for_concatenation(self, mock_open):
        create_txt_file_for_concatenation("list.txt", ["clip1.mp4", "clip2.mp4"])


class TestConcatenateClips:
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_concatenate_clips(self, mock_print, mock_run):
        concatenate_clips(["clip1.mp4"], "list.txt", "output.mp4", 3)


class TestParseArguments:
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments(self, mock_parse):
        mock_args = MagicMock()
        mock_args.input_video = "video.mp4"
        mock_args.duration = 10
        mock_parse.return_value = mock_args
        args = parse_arguments()
        assert args.input_video == "video.mp4"


# Main is complex, skip for brevity
