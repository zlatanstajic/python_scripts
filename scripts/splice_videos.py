# Copyright (c) Zlatan Stajic <contact@zlatanstajic.com>
# SPDX-License-Identifier: MIT

import argparse
import math
import os
import random
import shutil
import subprocess
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.arguments_helper import ArgumentsHelper  # type: ignore
from helpers.logging_helper import setup_logging  # type: ignore
from helpers.wrapper_helper import WrapperHelper  # type: ignore

logger = setup_logging(__name__)


def get_extension_os_path(filename: str) -> str:
    """Get the lowercase file extension from a filename."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file in seconds."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        logger.info(f"Getting video duration for {video_path}")
        duration_str = subprocess.check_output(cmd).decode("utf-8").strip()
        total_video_duration = float(duration_str)
        if total_video_duration is None:
            WrapperHelper.end(True, "Could not get video duration. Exiting.")
            assert False
        logger.info(f"Total video duration is {total_video_duration} seconds.")
        return total_video_duration
    except (subprocess.CalledProcessError, ValueError) as e:
        WrapperHelper.end(True, f"Error getting video duration for {video_path}: {e}")
        assert False


def create_input_video_path(input_video: str) -> str:
    """Create the input video file path."""
    return f"assets/inputs/{input_video}"


def create_output_video_path(input_video: str) -> str:
    """Create the output video file path."""
    return f"assets/spliced/output_from_{input_video}"


def create_random_clips_path() -> str:
    """Create and return the random clips directory path."""
    # Directory in question
    random_clips_path = "assets/random_clips"
    # Remove directory with it's content
    try:
        shutil.rmtree(random_clips_path)
        logger.info(f"Successfully removed directory: {random_clips_path}")
    except OSError as e:
        WrapperHelper.end(True, f"Error removing directory '{random_clips_path}': {e}")
        assert False
    # Create directory for content
    try:
        logger.info(f"Successfully created directory: {random_clips_path}")
        os.makedirs(random_clips_path, exist_ok=True)
        return random_clips_path
    except OSError as e:
        WrapperHelper.end(True, f"Error creating directory '{random_clips_path}': {e}")
        assert False


def calculate_number_of_random_clips(
    total_video_duration: float, target_total_duration: int, segment_duration: int
) -> int:
    """Calculate the number of random clips needed, with duration in seconds."""
    num_segments_needed = target_total_duration // segment_duration
    if total_video_duration < target_total_duration:
        logger.info(
            f"Input video ({total_video_duration:.2f}s) is shorter than target ({target_total_duration}s). Adjusting target segments."
        )
        num_segments_needed = math.floor(total_video_duration / segment_duration)
        # Ensure we don't try to get more segments than possible if the video is very short
        if num_segments_needed <= 0:
            WrapperHelper.end(
                True,
                "Input video is too short to create any segments of the specified duration. Exiting.",
            )
            assert False

    # Ensure output doesn't exceed 1 GB
    max_file_size_bytes = 1024 * 1024 * 1024  # 1 GB
    estimated_bitrate_bps = (
        1_500_000  # 1.5 Mbps (conservative estimate for ultrafast CRF 18)
    )
    actual_output_duration = num_segments_needed * segment_duration
    estimated_output_size = (actual_output_duration * estimated_bitrate_bps) / 8

    if estimated_output_size > max_file_size_bytes:
        max_duration = (max_file_size_bytes * 8) / estimated_bitrate_bps
        num_segments_needed = int(max_duration // segment_duration)
        logger.info(
            f"Output would exceed 1 GB. Reducing segments from {target_total_duration // segment_duration} to {num_segments_needed}."
        )
        if num_segments_needed <= 0:
            WrapperHelper.end(
                True,
                "Even a single segment would exceed 1 GB. Segment duration is too long. Exiting.",
            )
            assert False

    return num_segments_needed


def create_available_block_indices(
    total_video_duration: float, segment_duration: int, num_segments_needed: int
) -> list[int]:
    """Create shuffled list of available block indices for clip extraction."""
    num_possible_blocks = math.floor(total_video_duration / segment_duration)

    # Ignore first 10% and last 10% of the input video
    skip_start_blocks = math.ceil(num_possible_blocks * 0.1)
    skip_end_blocks = math.ceil(num_possible_blocks * 0.1)
    first_valid_block = skip_start_blocks
    last_valid_block = num_possible_blocks - skip_end_blocks

    if last_valid_block <= first_valid_block:
        WrapperHelper.end(
            True,
            "Input video is too short to create clips after ignoring first and last 10%. Exiting.",
        )
        assert False

    available_block_indices = list(range(first_valid_block, last_valid_block))

    if len(available_block_indices) < num_segments_needed:
        logger.info(
            f"Not enough unique {segment_duration}-second blocks ({len(available_block_indices)}) to fulfill {num_segments_needed} segments."
        )
        num_segments_needed = len(available_block_indices)

    random.shuffle(available_block_indices)
    return available_block_indices


def create_random_clips(
    num_segments_needed: int,
    segment_duration: int,
    available_block_indices: list[int],
    random_clips_path: str,
    clips_to_concatenate: list[str],
    input_video_path: str,
) -> None:
    """Extract random clips from the input video."""
    logger.info(
        f"Generating {num_segments_needed} random {segment_duration}-second clips..."
    )
    for i in range(num_segments_needed):
        if not available_block_indices:
            logger.info("No more unique blocks to select from.")
            break

        block_index = available_block_indices.pop()
        start_time = block_index * segment_duration

        input_video_extension = get_extension_os_path(input_video_path)
        output_clip_path = os.path.join(
            random_clips_path, f"clip_{i:03d}{input_video_extension}"
        )
        clips_to_concatenate.append(output_clip_path)

        # FFmpeg command to extract a segment using fast input seeking and re-encoding for exact duration
        extract_cmd = [
            "ffmpeg",
            "-ss",
            str(start_time),
            "-i",
            input_video_path,
            "-t",
            str(segment_duration),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "18",
            "-an",
            "-avoid_negative_ts",
            "make_zero",
            "-y",
            output_clip_path,
        ]
        logger.info(f"Extracting: {' '.join(extract_cmd)}")
        try:
            # Capture output to prevent FFmpeg spamming console, only print on error
            subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error extracting clip {output_clip_path}: {e}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            continue  # Continue to next clip, or you could 'break' if an error should stop the process


def create_txt_file_for_concatenation(
    clips_list_file_path: str, clips_to_concatenate: list[str]
) -> None:
    """Create a text file listing clips for FFmpeg concatenation."""
    with open(clips_list_file_path, "w") as f:
        for clip in clips_to_concatenate:
            # Use forward slashes for FFmpeg consistency, and ensure path is relative to the script
            # or an absolute path if you prefer. Here we make it relative to where script is run.
            f.write(f"file '{clip.replace(os.sep, '/')}'\n")


def concatenate_clips(
    clips_to_concatenate: list[str],
    clips_list_file_path: str,
    output_video_path: str,
    segment_duration: int,
) -> None:
    """Concatenate clips into a single output video."""
    logger.info(
        f"Concatenating {len(clips_to_concatenate)} clips into {output_video_path} (re-encoding for smooth transitions)..."
    )
    concat_cmd = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        clips_list_file_path,
        "-c:v",
        "libx264",  # Re-encode video
        "-preset",
        "medium",  # Use 'medium' preset for better quality/compression balance during final re-encoding
        "-crf",
        "23",  # Constant Rate Factor for quality. Adjust as needed.
        "-c:a",
        "aac",  # Re-encode audio
        "-b:a",
        "128k",  # Audio bitrate. Adjust as needed.
        output_video_path,
    ]
    try:
        # Capture output to prevent FFmpeg spamming console, only print on error
        subprocess.run(concat_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error concatenating clips: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return

    logger.info(
        f"\nSuccessfully created {output_video_path} from random {segment_duration}-second clips."
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Splicing video clips together.",
    )
    parser.add_argument(
        "-i",
        "--input_video",
        type=str,
        help="Input video name with extension (Required)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        help="Output video duration in seconds (Required)",
    )
    parser.add_argument(
        "-s",
        "--segment",
        type=int,
        default=3,
        help="Random clip video duration in seconds (Optional)",
    )
    args = parser.parse_args()
    if not args.input_video or not args.duration:
        ArgumentsHelper.missing_required_arguments_message()
    return args


def main() -> None:
    """Main entry point for the script."""
    args = parse_arguments()
    segment_duration = args.segment
    target_total_duration = args.duration

    random_clips_path = "assets/random_clips"

    # Check if clips already exist in random_clips directory
    existing_clips = []
    if os.path.exists(random_clips_path):
        existing_clips = [
            f
            for f in os.listdir(random_clips_path)
            if os.path.isfile(os.path.join(random_clips_path, f))
            and f != "concat_list.txt"
        ]

    if existing_clips:
        logger.info(
            f"Found {len(existing_clips)} existing clips in {random_clips_path}. Skipping clip generation."
        )
        input_video_path = create_input_video_path(args.input_video)
        total_video_duration = get_video_duration(input_video_path)
    else:
        logger.info("No existing clips found. Generating new clips.")
        random_clips_path = create_random_clips_path()
        input_video_path = create_input_video_path(args.input_video)
        total_video_duration = get_video_duration(input_video_path)
        num_segments_needed = calculate_number_of_random_clips(
            total_video_duration, target_total_duration, segment_duration
        )
        available_block_indices = create_available_block_indices(
            total_video_duration, segment_duration, num_segments_needed
        )
        clips_to_concatenate: list[str] = []

        create_random_clips(
            num_segments_needed,
            segment_duration,
            available_block_indices,
            random_clips_path,
            clips_to_concatenate,
            input_video_path,
        )

    # Gather all generated clips from random_clips directory
    all_clips = sorted(
        [
            os.path.join(random_clips_path, f)
            for f in os.listdir(random_clips_path)
            if os.path.isfile(os.path.join(random_clips_path, f))
        ]
    )
    if not all_clips:
        WrapperHelper.end(
            True, "No clips found in random_clips. Nothing to concatenate."
        )
        assert False

    # Create concat list file for FFmpeg
    concat_list_path = os.path.join(random_clips_path, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for clip in all_clips:
            abs_clip = os.path.abspath(clip)
            f.write(f"file '{abs_clip}'\n")

    # Prepare output directory and path
    output_dir = "assets/spliced"
    os.makedirs(output_dir, exist_ok=True)
    output_file = create_output_video_path(args.input_video)

    # Concatenate clips into single output file
    concat_cmd = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_path,
        "-c",
        "copy",
        "-y",
        output_file,
    ]
    logger.info(f"\nConcatenating {len(all_clips)} clips into {output_file}...")
    try:
        subprocess.run(concat_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error concatenating clips: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        WrapperHelper.end(True, "Concatenation failed. Exiting.")
        assert False

    # Get output file duration for report
    output_duration = get_video_duration(output_file)

    # Print report
    logger.info("\n===== Splice Report =====")
    logger.info(f"Input video:       {args.input_video}")
    logger.info(f"Input duration:    {total_video_duration:.2f}s")
    logger.info(f"Clips generated:   {len(all_clips)}")
    logger.info(f"Clip duration:     {segment_duration}s each")
    logger.info(f"Output file:       {output_file}")
    logger.info(f"Output duration:   {output_duration:.2f}s")
    logger.info(f"Output location:   {os.path.abspath(output_file)}")
    logger.info("=========================")


if __name__ == "__main__":
    WrapperHelper.main(main)
