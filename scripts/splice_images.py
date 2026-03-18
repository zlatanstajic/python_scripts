#!/usr/bin/env python3
# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import os
import random
import string
import subprocess
import sys

from dotenv import load_dotenv  # Add this import at the top
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import finish_script, run_script  # type: ignore

logger = setup_logging(__name__)


def generate_random_hash(length=10):
    """Generate a random alphanumeric hash string."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def get_image_height(image_path):
    """Get the height of an image in pixels."""
    try:
        with Image.open(image_path) as img:
            return img.height
    except Exception:
        return None


def get_valid_extensions():
    """Get valid image extensions from environment variable."""
    load_dotenv()  # Load environment variables from .env
    exts = os.getenv("SPLICE_IMAGES_FILE_EXTENSIONS")
    if not exts:
        finish_script(
            True,
            "Environment variable SPLICE_IMAGES_FILE_EXTENSIONS is not set. "
            "Please set it to a comma-separated list of valid image extensions.",
        )
    assert exts is not None
    return tuple(ext.strip() for ext in exts.split(",") if ext.strip())


def get_random_images_from_directory(directory, count=3):
    """Get a random sample of images from a directory."""
    all_images = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(get_valid_extensions())
        and os.path.isfile(os.path.join(directory, f))
    ]
    if len(all_images) < count:
        finish_script(
            True,
            f"Not enough images in {directory} (found {len(all_images)}, need {count}).",
        )
    return random.sample(all_images, count)


def get_filtered_images(number, images=None):
    """Get filtered images from provided list or random selection."""
    if images:
        filtered_images = [
            img for img in images if img.lower().endswith(get_valid_extensions())
        ][:number]
    else:
        filtered_images = get_random_images_from_directory(os.getcwd(), count=number)

    if len(filtered_images) < 2:
        finish_script(True, "Please provide at least two images to splice.")
    return filtered_images


def get_height(filtered_images, height):
    """Get the target height, defaulting to the first image's height."""
    if height is None or height <= 0:
        height = get_image_height(filtered_images[0])
        if height is None:
            finish_script(
                True, "Could not determine image height. Please provide --height."
            )
    return height


def get_filter_complex(filtered_images, height):
    """Build the FFmpeg filter_complex string for horizontal stacking."""
    num_inputs = len(filtered_images)
    filter_parts = []
    v_labels = []
    for idx in range(num_inputs):
        v_label = f"v{idx}"
        v_labels.append(v_label)
        filter_parts.append(
            f"[{idx}:v]scale=-1:{get_height(filtered_images, height)}[{v_label}]"
        )
    hstack = "".join([f"[{v}]" for v in v_labels]) + f"hstack=inputs={num_inputs}[v]"
    return "; ".join(filter_parts + [hstack])


def input_arguments(filtered_images):
    """Build FFmpeg input arguments for the given images."""
    input_args = []
    for img in filtered_images:
        input_args.extend(["-i", img])
    return input_args


def output_path(filtered_images, output):
    """Generate the output file path for the spliced image."""
    if output and "." in output:
        file_ext = os.path.splitext(output)[1]
    else:
        file_ext = os.path.splitext(filtered_images[0])[1]
    output_file_name = generate_random_hash() + file_ext

    output_folder = "spliced_images"
    os.makedirs(output_folder, exist_ok=True)
    return os.path.join(output_folder, output_file_name)


def splice_images(filtered_images, filter_complex, output):
    """Splice images horizontally using FFmpeg."""
    ffmpeg_cmd = [
        "ffmpeg",
        *input_arguments(filtered_images),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        output_path(filtered_images, output),
    ]
    subprocess.run(
        ffmpeg_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def move_images(filtered_images):
    """Move processed images to the standalone folder."""
    standalone_folder = "standalone_images"
    os.makedirs(standalone_folder, exist_ok=True)
    for img in filtered_images:
        try:
            dest_path = os.path.join(standalone_folder, os.path.basename(img))
            os.rename(img, dest_path)
            logger.info(f"Moved {img} to {dest_path}")
        except Exception as e:
            logger.error(f"Could not move {img} to {standalone_folder}: {e}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Splices images horizontally using ffmpeg.",
    )
    parser.add_argument(
        "-i",
        "--images",
        nargs="+",
        help="List of input image files (e.g. -i img1.jpg img2.jpg img3.jpg)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output image filename.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Width to scale images to (default: 800)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Height to scale images to (default: ignored to inherit original photos height)",
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=2,
        help="Number of images to splice (default: 2)",
    )
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    args = parse_arguments()
    filtered_images = get_filtered_images(args.number, args.images)
    splice_images(
        filtered_images, get_filter_complex(filtered_images, args.height), args.output
    )
    move_images(filtered_images)


if __name__ == "__main__":
    run_script(main)
