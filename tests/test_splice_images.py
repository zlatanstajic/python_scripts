import os
import shutil
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.splice_images import (
    generate_random_hash,
    get_filter_complex,
    get_filtered_images,
    get_height,
    get_image_height,
    get_random_images_from_directory,
    get_valid_extensions,
    input_arguments,
    main,
    move_images,
    output_path,
    parse_arguments,
    splice_images,
)


@pytest.fixture(scope="session", autouse=True)
def cleanup_spliced_images():
    yield
    if os.path.exists("spliced_images"):
        shutil.rmtree("spliced_images")


class TestGenerateRandomHash:
    def test_generate_random_hash(self):
        hash_val = generate_random_hash(5)
        assert len(hash_val) == 5


class TestGetImageHeight:
    @patch("PIL.Image.open")
    def test_get_image_height(self, mock_open):
        mock_img = MagicMock()
        mock_img.height = 100
        mock_open.return_value.__enter__.return_value = mock_img
        height = get_image_height("img.jpg")
        assert height == 100


class TestGetValidExtensions:
    @patch.dict(os.environ, {"SPLICE_IMAGES_FILE_EXTENSIONS": ".jpg,.png"})
    def test_get_valid_extensions(self):
        exts = get_valid_extensions()
        assert exts == (".jpg", ".png")


class TestGetRandomImagesFromDirectory:
    @patch("os.listdir", return_value=["img1.jpg", "img2.jpg", "noting.txt"])
    @patch("os.path.isfile", return_value=True)
    @patch("scripts.splice_images.get_valid_extensions", return_value=(".jpg",))
    @patch("random.sample", return_value=["/dir/img1.jpg", "/dir/img2.jpg"])
    def test_get_random_images_from_directory(
        self, mock_sample, mock_get_ext, mock_isfile, mock_listdir
    ):
        images = get_random_images_from_directory("/dir", 2)
        assert len(images) == 2


class TestGetFilteredImages:
    @patch("scripts.splice_images.get_random_images_from_directory")
    @patch("scripts.splice_images.get_valid_extensions", return_value=(".jpg",))
    def test_get_filtered_images_random(self, mock_get_ext, mock_get_random):
        mock_get_random.return_value = ["img1.jpg", "img2.jpg"]
        images = get_filtered_images(2)
        assert images == ["img1.jpg", "img2.jpg"]

    @patch("scripts.splice_images.get_valid_extensions", return_value=(".jpg", ".png"))
    def test_get_filtered_images_provided(self, mock_get_ext):
        images = get_filtered_images(2, ["img1.jpg", "img2.jpg", "img3.png"])
        assert len(images) == 2
        assert images[0] in ["img1.jpg", "img2.jpg", "img3.png"]


class TestGetHeight:
    @patch("scripts.splice_images.get_image_height", return_value=100)
    def test_get_height_provided(self, mock_get_height):
        height = get_height(["img.jpg"], 200)
        assert height == 200

    @patch("scripts.splice_images.get_image_height", return_value=100)
    def test_get_height_auto(self, mock_get_height):
        height = get_height(["img.jpg"], None)
        assert height == 100


class TestGetFilterComplex:
    def test_get_filter_complex(self):
        filter_str = get_filter_complex(["img1.jpg", "img2.jpg"], 100)
        assert "hstack" in filter_str


class TestInputArguments:
    def test_input_arguments(self):
        args = input_arguments(["img1.jpg", "img2.jpg"])
        assert args == ["-i", "img1.jpg", "-i", "img2.jpg"]


class TestOutputPath:
    @patch("os.makedirs")
    def test_output_path(self, mock_makedirs):
        path = output_path(["img1.jpg"], None)
        assert "spliced_images" in path


class TestSpliceImages:
    @patch("subprocess.run")
    def test_splice_images(self, mock_run):
        splice_images(["img1.jpg"], "filter", None)


class TestMoveImages:
    @patch("os.makedirs")
    @patch("os.rename")
    @patch("builtins.print")
    def test_move_images(self, mock_print, mock_rename, mock_makedirs):
        move_images(["img1.jpg"])


class TestParseArguments:
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments(self, mock_parse):
        mock_args = MagicMock()
        mock_parse.return_value = mock_args
        args = parse_arguments()
        assert args == mock_args


# Main test
@patch("scripts.splice_images.parse_arguments")
@patch(
    "scripts.splice_images.get_filtered_images", return_value=["img1.jpg", "img2.jpg"]
)
@patch("scripts.splice_images.get_filter_complex", return_value="filter")
@patch("scripts.splice_images.splice_images")
@patch("scripts.splice_images.move_images")
def test_main(mock_move, mock_splice, mock_get_filter, mock_get_filtered, mock_parse):
    main()
