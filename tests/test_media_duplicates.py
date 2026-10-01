"""Tests for exact visual duplicate detection and duplicate review."""

import hashlib
import html
import http.client
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
from contextlib import closing, contextmanager
from pathlib import Path

import pytest

from scripts import media_organizer


def framehash_lines(
    frame_hashes,
    *,
    software="Lavf58.76.100",
    timebase="1/25",
    sar="1/1",
    frame_size=48,
    first_timestamp=0,
):
    """Return FFmpeg framehash output describing the given frame hashes."""
    lines = [
        "#format: frame checksums",
        "#version: 2",
        "#hash: SHA256",
        f"#software: {software}",
        f"#tb 0: {timebase}",
        "#media_type 0: video",
        "#codec_id 0: rawvideo",
        "#dimensions 0: 4x3",
        f"#sar 0: {sar}",
        "#stream#, dts,        pts, duration,     size, hash",
    ]
    for offset, frame_hash in enumerate(frame_hashes):
        timestamp = first_timestamp + offset
        lines.append(
            f"0, {timestamp:10d}, {timestamp:10d}, {1:8d}, {frame_size:8d}, "
            f"{frame_hash}"
        )
    return lines


class FakeMediaTools:
    """Answer FFprobe, ExifTool, and FFmpeg framehash calls by file name."""

    def __init__(self):
        self.frames = {}
        self.invalid = set()
        self.probed = []
        self.decoded = []

    def run_json(self, command):
        """Return one 4x3 visual stream, as FFprobe would, without ExifTool."""
        if command[0] == "exiftool":
            raise FileNotFoundError("exiftool")
        name = Path(command[-1]).name
        self.probed.append(name)
        if name in self.invalid:
            return {"streams": [], "format": {}}
        stream = {"codec_type": "video", "width": 4, "height": 3}
        return {"streams": [stream], "format": {"duration": "2.5"}}

    def framehash_lines(self, command):
        """Yield the configured frames, or fail like an undecodable file."""
        name = Path(command[command.index("-i") + 1]).name
        self.decoded.append(name)
        if name not in self.frames:
            raise RuntimeError("Invalid data found when processing input")
        yield from framehash_lines(self.frames[name])


@pytest.fixture
def media_tools(monkeypatch):
    """Replace FFprobe, ExifTool, and FFmpeg with deterministic fakes."""
    tools = FakeMediaTools()
    monkeypatch.setattr(media_organizer, "_run_json", tools.run_json)
    monkeypatch.setattr(media_organizer, "_framehash_lines", tools.framehash_lines)
    return tools


def write_file(path, content):
    """Create a file with the given bytes, including its parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def group_names(report):
    """Return the file names in each duplicate group, in report order."""
    return [
        [Path(entry["path"]).name for entry in group["entries"]]
        for group in report["groups"]
    ]


def snapshot(root):
    """Record each path's content or link target, mode, mtime, device, and inode."""
    state = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        if path.is_symlink():
            content = os.readlink(path)
        elif path.is_file():
            content = path.read_bytes()
        else:
            content = None
        state[path] = (
            content,
            info.st_mode,
            info.st_mtime_ns,
            info.st_dev,
            info.st_ino,
        )
    return state


def media_metadata(path, media_type="image", width=4, height=3, rotation=0):
    """Build the metadata visual_digest reads for a synthetic media path."""
    return media_organizer.MediaMetadata(
        path=str(path),
        original_filename=path.name,
        extension=path.suffix,
        original_directory=str(path.parent),
        file_size=5,
        mtime_ns=1,
        media_type=media_type,
        width=width,
        height=height,
        rotation=rotation,
    )


def report_entry(path, digest, inode):
    """Return one present duplicate entry as find_duplicates records it."""
    return {
        "path": str(path),
        "media_type": "video" if path.suffix == ".mp4" else "image",
        "device": 7,
        "inode": inode,
        "mtime_ns": 1_700_000_000_123_456_789,
        "sha256": digest,
        "resolution": "4x3",
        "duration": 2.5 if path.suffix == ".mp4" else None,
        "status": "present",
        "error": None,
    }


def sample_report(tmp_path):
    """Return a detection result with a 2-copy group, a 3-copy group, and a skip."""
    source = tmp_path / "source"
    return {
        "schema_version": media_organizer.DUPLICATE_REPORT_SCHEMA_VERSION,
        "created_at": "2026-10-01T12:00:00+02:00",
        "source_directory": str(source),
        "groups": [
            {
                "file_size": 5,
                "visual_digest": "a" * 64,
                "status": "unresolved",
                "entries": [
                    report_entry(source / "a.jpg", "1" * 64, 11),
                    report_entry(source / "b.jpg", "2" * 64, 12),
                ],
            },
            {
                "file_size": 9,
                "visual_digest": "b" * 64,
                "status": "unresolved",
                "entries": [
                    report_entry(source / "clip.mp4", "3" * 64, 13),
                    report_entry(source / "copy.mp4", "3" * 64, 14),
                    report_entry(source / "third.mp4", "3" * 64, 15),
                ],
            },
        ],
        "skipped": [{"path": str(source / "broken.mp4"), "reason": "Invalid data"}],
    }


def query(path, sql):
    """Return every row of one SQL query against a report database."""
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql).fetchall()


def test_only_equal_size_candidates_are_inspected(tmp_path, media_tools):
    source = tmp_path / "source"
    write_file(source / "a.jpg", b"12345")
    write_file(source / "b.jpg", b"54321")
    write_file(source / "unique.jpg", b"1234567")
    write_file(source / "clip.mp4", b"123456789")
    for name in ("a.jpg", "b.jpg", "unique.jpg", "clip.mp4"):
        media_tools.frames[name] = ["same"]

    report = media_organizer.find_duplicates(source)

    assert group_names(report) == [["a.jpg", "b.jpg"]]
    assert report["groups"][0]["file_size"] == 5
    assert sorted(media_tools.probed) == ["a.jpg", "b.jpg"]
    assert sorted(media_tools.decoded) == ["a.jpg", "b.jpg"]
    assert report["skipped"] == []


def test_groups_require_identical_decoded_frames(tmp_path, media_tools):
    source = tmp_path / "source"
    for name, frames in (
        ("first.png", ["p1"]),
        ("second.png", ["p1"]),
        ("different.png", ["p2"]),
        ("clip.mp4", ["v1", "v2"]),
        ("copy.mp4", ["v1", "v2"]),
        ("long.mp4", ["v1", "v2", "v3"]),
    ):
        write_file(source / name, name[:4].encode())
        media_tools.frames[name] = frames

    report = media_organizer.find_duplicates(source)

    assert group_names(report) == [
        ["clip.mp4", "copy.mp4"],
        ["first.png", "second.png"],
    ]
    videos, photos = report["groups"]
    assert videos["visual_digest"] != photos["visual_digest"]
    assert len({entry["sha256"] for entry in photos["entries"]}) == 2
    assert [entry["duration"] for entry in videos["entries"]] == [2.5, 2.5]
    assert {entry["media_type"] for entry in videos["entries"]} == {"video"}


def test_three_identical_copies_form_one_group_ordered_by_path(tmp_path, media_tools):
    source = tmp_path / "source"
    for relative in ("one.jpg", "three.jpg", "nested/two.jpg"):
        write_file(source / relative, b"photo")
        media_tools.frames[Path(relative).name] = ["same"]

    report = media_organizer.find_duplicates(source)

    [group] = report["groups"]
    assert [
        Path(entry["path"]).relative_to(source.resolve()).as_posix()
        for entry in group["entries"]
    ] == ["nested/two.jpg", "one.jpg", "three.jpg"]
    assert group["status"] == "unresolved"
    for entry in group["entries"]:
        info = os.stat(entry["path"])
        assert (entry["device"], entry["inode"], entry["mtime_ns"]) == (
            info.st_dev,
            info.st_ino,
            info.st_mtime_ns,
        )
        assert entry["sha256"] == hashlib.sha256(b"photo").hexdigest()
        assert entry["media_type"] == "image"
        assert entry["resolution"] == "4x3"
        assert entry["duration"] is None
        assert (entry["status"], entry["error"]) == ("present", None)


def test_links_to_one_file_are_counted_once(tmp_path, media_tools):
    source = tmp_path / "source"
    original = write_file(source / "original.jpg", b"photo")
    os.link(original, source / "hardlink.jpg")
    (source / "symlink.jpg").symlink_to(original)
    for name in ("copy.jpg", "hardlink.jpg", "original.jpg"):
        media_tools.frames[name] = ["same"]

    alone = media_organizer.find_duplicates(source)

    assert alone["groups"] == []
    assert alone["skipped"] == []
    assert media_tools.decoded == []

    write_file(source / "copy.jpg", b"photo")
    report = media_organizer.find_duplicates(source)

    assert group_names(report) == [["copy.jpg", "hardlink.jpg"]]
    assert report["skipped"] == []


def test_candidates_resolving_outside_the_input_are_skipped(tmp_path, media_tools):
    source = tmp_path / "source"
    outside = write_file(tmp_path / "outside" / "photo.jpg", b"photo")
    write_file(source / "a.jpg", b"photo")
    write_file(source / "b.jpg", b"photo")
    (source / "link.jpg").symlink_to(outside)
    for name in ("a.jpg", "b.jpg", "photo.jpg"):
        media_tools.frames[name] = ["same"]

    report = media_organizer.find_duplicates(source)

    assert group_names(report) == [["a.jpg", "b.jpg"]]
    assert report["skipped"] == [
        {
            "path": str(outside.resolve()),
            "reason": "Resolves outside the input directory",
        }
    ]
    assert "photo.jpg" not in media_tools.decoded


def test_decode_failures_are_skipped_without_stopping_other_buckets(
    tmp_path, media_tools
):
    source = tmp_path / "source"
    for name in ("broken.mp4", "clip.mp4", "copy.mp4"):
        write_file(source / name, b"video")
    for name in ("a.jpg", "b.jpg"):
        write_file(source / name, b"image-bytes")
    for name in ("clip.mp4", "copy.mp4"):
        media_tools.frames[name] = ["video-frame"]
    for name in ("a.jpg", "b.jpg"):
        media_tools.frames[name] = ["image-frame"]

    report = media_organizer.find_duplicates(source)

    assert group_names(report) == [["a.jpg", "b.jpg"], ["clip.mp4", "copy.mp4"]]
    assert report["skipped"] == [
        {
            "path": str((source / "broken.mp4").resolve()),
            "reason": "Invalid data found when processing input",
        }
    ]


def test_files_changed_during_detection_are_skipped(tmp_path, media_tools, monkeypatch):
    source = tmp_path / "source"
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        write_file(source / name, b"photo")
        media_tools.frames[name] = ["same"]
    real_sha256_file = media_organizer.sha256_file

    def touch_while_hashing(path, progress=None):
        if path.name == "c.jpg":
            os.utime(path, ns=(1, 1))
        return real_sha256_file(path, progress)

    monkeypatch.setattr(media_organizer, "sha256_file", touch_while_hashing)

    report = media_organizer.find_duplicates(source)

    assert group_names(report) == [["a.jpg", "b.jpg"]]
    assert report["skipped"] == [
        {
            "path": str((source / "c.jpg").resolve()),
            "reason": "Changed during duplicate detection",
        }
    ]


def test_detection_only_reads_source_files(tmp_path, media_tools):
    source = tmp_path / "source"
    original = write_file(source / "photo.jpg", b"photo")
    write_file(source / "copy.jpg", b"photo")
    write_file(source / "broken.jpg", b"photo")
    os.link(original, source / "hardlink.jpg")
    (source / "symlink.jpg").symlink_to(original)
    os.chmod(original, 0o640)
    for name in ("copy.jpg", "hardlink.jpg"):
        media_tools.frames[name] = ["same"]
    before = snapshot(source)

    report = media_organizer.find_duplicates(source)

    assert group_names(report) == [["copy.jpg", "hardlink.jpg"]]
    assert [Path(item["path"]).name for item in report["skipped"]] == ["broken.jpg"]
    assert snapshot(source) == before


def test_visual_digest_hashes_content_but_not_timing_or_encoder(tmp_path, monkeypatch):
    output = {}
    monkeypatch.setattr(
        media_organizer, "_framehash_lines", lambda _command: output["lines"]
    )

    def digest(lines, **metadata):
        output["lines"] = lines
        photo = media_metadata(tmp_path / "photo.jpg", **metadata)
        return media_organizer.visual_digest(photo)

    base = digest(framehash_lines(["h1", "h2"]))

    assert (
        digest(
            framehash_lines(
                ["h1", "h2"],
                software="Lavf61.7.100",
                timebase="1/30",
                first_timestamp=40,
            )
        )
        == base
    )
    assert digest(framehash_lines(["h1", "h3"])) != base
    assert digest(framehash_lines(["h2", "h1"])) != base
    assert digest(framehash_lines(["h1", "h2"], sar="4/3")) != base
    assert digest(framehash_lines(["h1", "h2"], frame_size=96)) != base
    assert digest(framehash_lines(["h1", "h2"]), rotation=180) != base
    assert digest(framehash_lines(["h1", "h2"]), width=8) != base


def test_visual_digest_decodes_every_photo_stream_and_first_video_stream(
    tmp_path, monkeypatch
):
    commands = []

    def record(command):
        commands.append(list(command))
        return framehash_lines(["h1"])

    monkeypatch.setattr(media_organizer, "_framehash_lines", record)

    media_organizer.visual_digest(media_metadata(tmp_path / "photo.heic"))
    media_organizer.visual_digest(
        media_metadata(tmp_path / "clip.mov", media_type="video")
    )

    photo, video = commands
    assert photo[photo.index("-map") + 1] == "0:v"
    assert video[video.index("-map") + 1] == "0:v:0"
    for command in commands:
        assert command[0] == "ffmpeg"
        assert command.index("-noautorotate") < command.index("-i")
        assert command[command.index("-pix_fmt") + 1] == "rgba64le"
        assert command[command.index("-f") + 1] == "framehash"
        assert command[command.index("-hash") + 1] == "sha256"


@pytest.mark.parametrize(
    "lines",
    [[], framehash_lines([]), framehash_lines(["h1"]) + ["0, 0, 0"]],
)
def test_visual_digest_rejects_output_without_usable_frames(
    tmp_path, monkeypatch, lines
):
    monkeypatch.setattr(media_organizer, "_framehash_lines", lambda _command: lines)

    with pytest.raises(RuntimeError, match="no usable frame hashes"):
        media_organizer.visual_digest(media_metadata(tmp_path / "photo.jpg"))


def test_visual_digest_refuses_image_paths_ffmpeg_reads_as_patterns(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        media_organizer,
        "_framehash_lines",
        lambda _command: pytest.fail("FFmpeg must not run"),
    )

    with pytest.raises(ValueError, match="sequence pattern"):
        media_organizer.visual_digest(media_metadata(tmp_path / "IMG_%03d.jpg"))


def test_framehash_lines_streams_output_and_reports_the_last_error(tmp_path):
    script = "print('#dimensions 0: 1x1'); print('0, 0, 0, 1, 4, abc')"
    failing = "import sys; sys.stderr.write('warning\\nInvalid data\\n'); sys.exit(1)"

    assert list(media_organizer._framehash_lines([sys.executable, "-c", script])) == [
        "#dimensions 0: 1x1",
        "0, 0, 0, 1, 4, abc",
    ]
    with pytest.raises(RuntimeError, match="^Invalid data$"):
        list(media_organizer._framehash_lines([sys.executable, "-c", failing]))
    with pytest.raises(RuntimeError, match="could not start"):
        list(media_organizer._framehash_lines([str(tmp_path / "missing-ffmpeg")]))


def test_framehash_lines_stops_ffmpeg_when_reading_ends_early():
    script = "import time; print('0, 0, 0, 1, 4, abc', flush=True); time.sleep(60)"
    started = time.monotonic()
    lines = media_organizer._framehash_lines([sys.executable, "-c", script])

    assert next(lines) == "0, 0, 0, 1, 4, abc"
    lines.close()

    assert time.monotonic() - started < 30


def test_duplicate_report_round_trips_through_normalized_tables(tmp_path):
    report = sample_report(tmp_path)
    path = tmp_path / "duplicate-report.sqlite3"

    media_organizer.write_duplicate_report(report, path)
    loaded = media_organizer.load_duplicate_report(path)

    entry_ids = iter(range(1, 6))
    expected_groups = [
        {
            "id": group_id,
            **group,
            "entries": [{"id": next(entry_ids), **entry} for entry in group["entries"]],
        }
        for group_id, group in enumerate(report["groups"], start=1)
    ]
    assert loaded == {**report, "groups": expected_groups}
    assert {
        name
        for (name,) in query(path, "SELECT name FROM sqlite_master WHERE type='table'")
    } == {
        "duplicate_report",
        "duplicate_groups",
        "duplicate_entries",
        "duplicate_skipped",
    }
    assert query(path, "SELECT id, group_id, status FROM duplicate_entries") == [
        (1, 1, "present"),
        (2, 1, "present"),
        (3, 2, "present"),
        (4, 2, "present"),
        (5, 2, "present"),
    ]


def test_writing_a_report_replaces_the_previous_one_atomically(tmp_path):
    path = tmp_path / "duplicate-report.sqlite3"
    first = sample_report(tmp_path)
    second = {**first, "groups": first["groups"][:1], "skipped": []}

    media_organizer.write_duplicate_report(first, path)
    media_organizer.write_duplicate_report(second, path)

    assert len(media_organizer.load_duplicate_report(path)["groups"]) == 1
    with pytest.raises(KeyError):
        media_organizer.write_duplicate_report(
            {**first, "groups": [{"file_size": 5}]}, path
        )
    assert media_organizer.load_duplicate_report(path)["skipped"] == []
    assert [item.name for item in tmp_path.iterdir()] == [path.name]


@pytest.mark.parametrize(
    "tamper, message",
    [
        ("DROP TABLE duplicate_skipped", "missing tables: duplicate_skipped"),
        ("UPDATE duplicate_report SET schema_version = 2", "Unsupported"),
        ("DELETE FROM duplicate_report", "Unsupported"),
        ("UPDATE duplicate_entries SET group_id = 9 WHERE id = 5", "relations"),
        ("DELETE FROM duplicate_entries WHERE id = 2", "relations"),
        ("ALTER TABLE duplicate_entries DROP COLUMN error", "Malformed"),
    ],
)
def test_malformed_duplicate_reports_are_rejected(tmp_path, tamper, message):
    path = tmp_path / "duplicate-report.sqlite3"
    media_organizer.write_duplicate_report(sample_report(tmp_path), path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(tamper)
        connection.commit()

    with pytest.raises(ValueError, match=message):
        media_organizer.load_duplicate_report(path)


def test_files_that_are_not_sqlite_are_rejected(tmp_path):
    path = tmp_path / "duplicate-report.sqlite3"
    path.write_text("not a database", encoding="utf-8")

    with pytest.raises(ValueError, match="Not a SQLite duplicate report"):
        media_organizer.load_duplicate_report(path)


def test_non_regular_candidates_are_skipped(tmp_path, media_tools):
    source = tmp_path / "source"
    source.mkdir()
    os.mkfifo(source / "pipe.mp4")

    report = media_organizer.find_duplicates(source)

    assert report["groups"] == []
    assert report["skipped"] == [
        {"path": str((source / "pipe.mp4").resolve()), "reason": "Not a regular file"}
    ]
    assert media_tools.probed == []


@pytest.fixture
def media_library(tmp_path, media_tools, monkeypatch):
    """Create a library with one duplicate pair and put fake tools on PATH."""
    monkeypatch.setattr(
        media_organizer.shutil, "which", lambda name: f"/usr/bin/{name}"
    )
    source = tmp_path / "source"
    for name in ("a.jpg", "b.jpg"):
        write_file(source / name, b"photo")
        media_tools.frames[name] = ["same"]
    write_file(source / "clip.mp4", b"unique video")
    return source


def test_duplicates_arguments_take_no_scan_options():
    arguments = media_organizer.parse_arguments(["duplicates", "--input", "/media"])

    assert arguments.input == Path("/media")
    assert arguments.report_file is None
    assert arguments.verbose is False
    with pytest.raises(SystemExit):
        media_organizer.parse_arguments(["duplicates"])
    with pytest.raises(SystemExit):
        media_organizer.parse_arguments(
            ["duplicates", "--input", "/media", "--index", "/cache.sqlite3"]
        )


def test_duplicates_writes_the_report_to_the_current_directory(
    tmp_path, media_library, monkeypatch, capsys
):
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    result = media_organizer.main(["duplicates", "--input", str(media_library)])

    report_path = workdir / media_organizer.DUPLICATE_REPORT_FILENAME
    report = media_organizer.load_duplicate_report(report_path)
    assert result == 0
    assert report["source_directory"] == str(media_library.resolve())
    assert group_names(report) == [["a.jpg", "b.jpg"]]
    output = capsys.readouterr().out
    assert f"Wrote {report_path.resolve()}." in output
    summary = "Found: 1 duplicate group(s), 2 copies, 0 skipped; no files changed."
    assert summary in output
    assert "Scanning recursively" not in output


def test_duplicates_honors_report_file_and_verbose(
    tmp_path, media_library, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "reports" / "library.sqlite3"

    result = media_organizer.main(
        [
            "duplicates",
            "--input",
            str(media_library),
            "--report-file",
            str(report_path),
            "--verbose",
        ]
    )

    assert result == 0
    report = media_organizer.load_duplicate_report(report_path)
    assert group_names(report) == [["a.jpg", "b.jpg"]]
    assert not (tmp_path / media_organizer.DUPLICATE_REPORT_FILENAME).exists()
    output = capsys.readouterr().out
    for message in (
        f"Scanning recursively: {media_library.resolve()}",
        "Discovered 3 media candidate(s).",
        "Comparing 2 candidate(s) in 1 equal-size bucket(s).",
        "[1/2] Extracting metadata:",
        "[2/2] Hashing decoded frames:",
        "Hashing bytes:",
        "Byte hash: 100%",
        f"Wrote {report_path.resolve()}.",
    ):
        assert message in output


@pytest.mark.parametrize("missing", ["ffmpeg", "ffprobe"])
def test_duplicates_requires_ffmpeg_and_ffprobe(
    tmp_path, media_library, media_tools, monkeypatch, capsys, missing
):
    monkeypatch.setattr(
        media_organizer.shutil,
        "which",
        lambda name: None if name == missing else f"/usr/bin/{name}",
    )
    monkeypatch.chdir(tmp_path)

    result = media_organizer.main(["duplicates", "--input", str(media_library)])

    assert result == 1
    assert f"Error: {missing} must be installed and on PATH" in capsys.readouterr().err
    assert not (tmp_path / media_organizer.DUPLICATE_REPORT_FILENAME).exists()
    assert media_tools.probed == []


def test_duplicates_refuses_a_report_file_with_a_media_extension(
    tmp_path, media_library, media_tools, capsys
):
    report_path = tmp_path / "report.JPG"

    result = media_organizer.main(
        ["duplicates", "--input", str(media_library), "--report-file", str(report_path)]
    )

    assert result == 1
    assert "must not use a media file extension" in capsys.readouterr().err
    assert not report_path.exists()
    assert media_tools.probed == []


def test_duplicates_records_invalid_media_and_exits_1(
    tmp_path, media_library, media_tools, monkeypatch, capsys
):
    write_file(media_library / "broken.jpg", b"photo")
    media_tools.invalid.add("broken.jpg")
    monkeypatch.chdir(tmp_path)

    result = media_organizer.main(["duplicates", "--input", str(media_library)])

    report = media_organizer.load_duplicate_report(
        tmp_path / media_organizer.DUPLICATE_REPORT_FILENAME
    )
    assert result == 1
    assert group_names(report) == [["a.jpg", "b.jpg"]]
    assert report["skipped"] == [
        {
            "path": str((media_library / "broken.jpg").resolve()),
            "reason": "FFprobe found no decodable image",
        }
    ]
    assert "2 copies, 1 skipped" in capsys.readouterr().out


def test_repeated_runs_replace_the_duplicate_report(
    tmp_path, media_library, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    arguments = ["duplicates", "--input", str(media_library)]
    report_path = tmp_path / media_organizer.DUPLICATE_REPORT_FILENAME

    assert media_organizer.main(arguments) == 0
    assert len(media_organizer.load_duplicate_report(report_path)["groups"]) == 1
    (media_library / "b.jpg").unlink()
    assert media_organizer.main(arguments) == 0

    assert media_organizer.load_duplicate_report(report_path)["groups"] == []
    assert sorted(item.name for item in tmp_path.iterdir()) == [
        media_organizer.DUPLICATE_REPORT_FILENAME,
        "source",
    ]


def test_duplicate_runs_never_modify_source_files(
    tmp_path, media_library, media_tools, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    os.chmod(media_library / "a.jpg", 0o600)
    (media_library / "link.jpg").symlink_to(media_library / "a.jpg")
    blocker = write_file(tmp_path / "blocker", b"")
    arguments = ["duplicates", "--input", str(media_library)]
    unwritable_report = ["--report-file", str(blocker / "report.sqlite3")]
    before = snapshot(media_library)

    assert media_organizer.main(arguments) == 0
    assert snapshot(media_library) == before
    assert media_organizer.main([*arguments, *unwritable_report]) == 1
    assert snapshot(media_library) == before
    media_tools.invalid.add("b.jpg")
    assert media_organizer.main(arguments) == 1
    assert snapshot(media_library) == before
    media_tools.invalid.clear()
    del media_tools.frames["a.jpg"]
    assert media_organizer.main(arguments) == 1
    assert snapshot(media_library) == before


@pytest.fixture(autouse=True)
def browser(monkeypatch):
    """Record browser launches so that no test opens a real browser."""
    opened = []
    monkeypatch.setattr(media_organizer.webbrowser, "open", opened.append)
    return opened


def build_review_report(tmp_path, groups):
    """Create real files for each group and write a report that matches them."""
    source = tmp_path / "source"
    report_groups = []
    for index, names in enumerate(groups):
        content = f"content-{index}".encode()
        entries = []
        for name in names:
            path = write_file(source / name, content)
            info = path.stat()
            video = path.suffix == ".mp4"
            entries.append(
                {
                    "path": str(path.resolve()),
                    "media_type": "video" if video else "image",
                    "device": info.st_dev,
                    "inode": info.st_ino,
                    "mtime_ns": info.st_mtime_ns,
                    "sha256": media_organizer.sha256_file(path),
                    "resolution": "4x3",
                    "duration": 2.5 if video else None,
                    "status": "present",
                    "error": None,
                }
            )
        report_groups.append(
            {
                "file_size": len(content),
                "visual_digest": f"{index:064d}",
                "status": "unresolved",
                "entries": entries,
            }
        )
    report_path = tmp_path / media_organizer.DUPLICATE_REPORT_FILENAME
    media_organizer.write_duplicate_report(
        {
            "schema_version": media_organizer.DUPLICATE_REPORT_SCHEMA_VERSION,
            "created_at": "2026-10-01T12:00:00+02:00",
            "source_directory": str(source.resolve()),
            "groups": report_groups,
            "skipped": [],
        },
        report_path,
    )
    return report_path, source


@pytest.fixture
def review_library(tmp_path):
    """Report a photo pair and a 3-copy video group backed by real files."""
    return build_review_report(
        tmp_path, [["a.jpg", "b.jpg"], ["clip.mp4", "copy.mp4", "third.mp4"]]
    )


@contextmanager
def running_server(report_path):
    """Serve a report on an OS-assigned loopback port, then shut it down."""
    server = media_organizer.DuplicateReviewServer(report_path, port=0)
    thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()


@pytest.fixture
def review_server(review_library):
    """Serve the review library while a test sends it requests."""
    with running_server(review_library[0]) as server:
        yield server


def request(server, method, target, body=None, headers=None):
    """Send one request to a review server and return status, headers, and body."""
    connection = http.client.HTTPConnection(
        media_organizer.REVIEW_HOST, server.server_port, timeout=10
    )
    try:
        headers = dict(headers or {})
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        connection.request(method, target, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, response.headers, response.read()
    finally:
        connection.close()


def review_page(server):
    """Return the HTML of a server's review page."""
    status, headers, body = request(server, "GET", f"/?token={server.token}")
    assert (status, headers["Content-Type"]) == (200, "text/html; charset=utf-8")
    return body.decode("utf-8")


class FakePreviewRun:
    """Record FFmpeg preview commands and answer them with fixed output."""

    def __init__(self, returncode=0, stdout=b"\xff\xd8preview\xff\xd9"):
        self.returncode = returncode
        self.stdout = stdout
        self.calls = []

    def __call__(self, command, **options):
        """Return the configured result of one FFmpeg run."""
        self.calls.append((list(command), options))
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, b"")


def time_out(command, **options):
    """Fail like an FFmpeg preview that exceeds its time limit."""
    raise subprocess.TimeoutExpired(command, options["timeout"])


def interrupt_serving(served):
    """Return a serve_forever replacement that records the server and stops."""

    def serve_forever(server, poll_interval=0.5):
        served.append(server)
        raise KeyboardInterrupt

    return serve_forever


def test_review_server_binds_only_to_loopback(review_server):
    assert review_server.server_address[0] == "127.0.0.1"
    assert review_server.server_port != 0
    assert review_server.url == (
        f"http://127.0.0.1:{review_server.server_port}/?token={review_server.token}"
    )


def test_review_page_shows_every_unresolved_group_side_by_side(
    review_server, review_library
):
    _report_path, source = review_library

    page = review_page(review_server)

    assert f'<style nonce="{review_server.nonce}">' in page
    assert "grid-template-columns:repeat(auto-fit" in page
    assert page.count('<section class="group">') == 2
    assert page.count('<article class="card">') == 5
    assert "Group 1: 2 identical copies" in page
    assert "Group 2: 3 identical copies" in page
    names = ("a.jpg", "b.jpg", "clip.mp4", "copy.mp4", "third.mp4")
    for entry_id, name in enumerate(names, start=1):
        assert f"<dd>{(source / name).resolve()}</dd>" in page
        assert f'src="/preview/{entry_id}?token={review_server.token}"' in page
    assert "<dd>9 bytes</dd>" in page
    assert "<dd>4x3</dd>" in page
    assert "<dd>2.5 s</dd>" in page
    assert "<dd>not applicable</dd>" in page


def test_resolved_groups_and_deleted_copies_leave_the_page(
    review_server, review_library
):
    report_path, _source = review_library
    with closing(sqlite3.connect(report_path)) as connection:
        connection.execute(
            "UPDATE duplicate_groups SET status = 'resolved' WHERE id = 1"
        )
        connection.execute(
            "UPDATE duplicate_entries SET status = 'deleted' WHERE id = 3"
        )
        connection.commit()

    page = review_page(review_server)

    assert "Group 1:" not in page
    assert "Group 2: 2 identical copies" in page
    assert "/preview/3?" not in page

    with closing(sqlite3.connect(report_path)) as connection:
        connection.execute("UPDATE duplicate_groups SET status = 'resolved'")
        connection.commit()

    assert "No unresolved duplicate groups remain." in review_page(review_server)


def test_review_page_escapes_every_rendered_path(tmp_path):
    names = ["<b>\"bold\"&'x'.jpg", "<img src=x onerror=alert(1)>.jpg"]
    report_path, _source = build_review_report(tmp_path, [names])

    with running_server(report_path) as server:
        page = review_page(server)

    assert "<b>" not in page
    assert "<img src=x" not in page
    assert "&lt;b&gt;&quot;bold&quot;&amp;&#x27;x&#x27;.jpg" in page
    assert "&lt;img src=x onerror=alert(1)&gt;.jpg" in page


@pytest.mark.parametrize(
    "target",
    [
        "/",
        "/?token=wrong",
        "/?token={token}&token={token}",
        "/?token=%C3%A9",
        "/preview/1",
        "/preview/1?token=wrong",
    ],
)
def test_review_routes_require_the_process_token(review_server, target):
    status, _headers, body = request(
        review_server, "GET", target.format(token=review_server.token)
    )

    assert (status, body) == (403, b"Forbidden\n")


@pytest.mark.parametrize(
    "method, target, status",
    [
        ("GET", "/missing?token={token}", 404),
        ("GET", "/etc/passwd?token={token}", 404),
        ("GET", "/preview/abc?token={token}", 404),
        ("GET", "/preview/0?token={token}", 404),
        ("GET", "/preview/../../etc/passwd?token={token}", 404),
        ("GET", "/preview/%2e%2e%2fetc%2fpasswd?token={token}", 404),
        ("GET", "/preview/99?token={token}", 404),
        ("POST", "/?token={token}", 405),
        ("PUT", "/preview/1?token={token}", 405),
        ("DELETE", "/preview/1?token={token}", 405),
        ("PATCH", "/", 405),
        ("HEAD", "/", 405),
        ("OPTIONS", "/", 405),
        ("POST", "/missing", 404),
    ],
)
def test_other_paths_and_methods_are_refused_without_detail(
    review_server, review_library, method, target, status
):
    code, headers, body = request(
        review_server, method, target.format(token=review_server.token)
    )

    assert code == status
    if method != "HEAD":
        assert body == (b"Not found\n" if status == 404 else b"Method not allowed\n")
    if status == 405:
        assert headers["Allow"] == "GET"


def test_security_headers_are_sent_with_every_response(review_server, monkeypatch):
    monkeypatch.setattr(media_organizer.subprocess, "run", FakePreviewRun())
    token = review_server.token

    for method, target in (
        ("GET", f"/?token={token}"),
        ("GET", f"/preview/1?token={token}"),
        ("GET", "/"),
        ("GET", "/missing"),
        ("POST", f"/?token={token}"),
        ("BREW", "/"),
    ):
        _status, headers, _body = request(review_server, method, target)
        policy = headers["Content-Security-Policy"]
        assert "default-src 'none'" in policy
        assert f"script-src 'nonce-{review_server.nonce}'" in policy
        assert f"style-src 'nonce-{review_server.nonce}'" in policy
        assert "frame-ancestors 'none'" in policy
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert headers["Cache-Control"] == "no-store"


def test_photo_preview_is_one_bounded_jpeg_frame(review_server, monkeypatch):
    fake_run = FakePreviewRun()
    monkeypatch.setattr(media_organizer.subprocess, "run", fake_run)

    status, headers, body = request(
        review_server, "GET", f"/preview/1?token={review_server.token}"
    )

    assert (status, headers["Content-Type"], body) == (
        200,
        "image/jpeg",
        fake_run.stdout,
    )
    [(command, options)] = fake_run.calls
    assert command[0] == "ffmpeg"
    assert command[command.index("-i") + 1].endswith("a.jpg")
    assert command[command.index("-map") + 1] == "0:v:0"
    assert command[command.index("-frames:v") + 1] == "1"
    assert "'min(640,iw)':'min(640,ih)'" in command[command.index("-vf") + 1]
    assert "-skip_frame" not in command
    assert 0 < options["timeout"] <= 60


def test_video_preview_is_a_tiled_contact_sheet(review_server, monkeypatch):
    fake_run = FakePreviewRun()
    monkeypatch.setattr(media_organizer.subprocess, "run", fake_run)

    status, headers, _body = request(
        review_server, "GET", f"/preview/3?token={review_server.token}"
    )

    assert (status, headers["Content-Type"]) == (200, "image/jpeg")
    [(command, options)] = fake_run.calls
    video_filter = command[command.index("-vf") + 1]
    assert "gte(t-prev_selected_t,0.278)" in video_filter
    assert "scale=320:320:force_original_aspect_ratio=decrease" in video_filter
    assert video_filter.endswith("tile=3x3")
    assert command[command.index("-skip_frame") + 1] == "nokey"
    assert command.index("-skip_frame") < command.index("-i")
    assert command[command.index("-frames:v") + 1] == "1"
    assert 0 < options["timeout"] <= 60


def test_failed_or_slow_previews_show_the_unavailable_state(review_server, monkeypatch):
    target = f"/preview/1?token={review_server.token}"

    for fake_run in (
        FakePreviewRun(returncode=1, stdout=b""),
        FakePreviewRun(stdout=b"not a jpeg"),
        time_out,
    ):
        monkeypatch.setattr(media_organizer.subprocess, "run", fake_run)
        status, headers, body = request(review_server, "GET", target)
        assert (status, headers["Content-Type"]) == (200, "image/svg+xml")
        assert b"Preview unavailable" in body


def test_previews_are_limited_to_unchanged_report_files(
    tmp_path, review_server, review_library, monkeypatch
):
    report_path, source = review_library
    fake_run = FakePreviewRun()
    monkeypatch.setattr(media_organizer.subprocess, "run", fake_run)
    private = write_file(tmp_path / "private.jpg", b"secret")
    with (source / "b.jpg").open("ab") as handle:
        handle.write(b"changed")
    (source / "clip.mp4").unlink()
    (source / "clip.mp4").symlink_to(source / "copy.mp4")
    with closing(sqlite3.connect(report_path)) as connection:
        connection.execute(
            "UPDATE duplicate_entries SET path = ? WHERE id = 4", (str(private),)
        )
        connection.commit()

    for entry_id in (2, 3, 4):
        status, headers, body = request(
            review_server, "GET", f"/preview/{entry_id}?token={review_server.token}"
        )
        assert (status, headers["Content-Type"]) == (200, "image/svg+xml")
        assert b"secret" not in body
    assert fake_run.calls == []


def test_read_only_routes_change_no_files(review_server, review_library, monkeypatch):
    report_path, source = review_library
    monkeypatch.setattr(media_organizer.subprocess, "run", FakePreviewRun())
    token = review_server.token
    before = snapshot(source)
    entries = query(report_path, "SELECT * FROM duplicate_entries")
    groups = query(report_path, "SELECT * FROM duplicate_groups")

    for method, target in (
        ("GET", f"/?token={token}"),
        *(("GET", f"/preview/{entry_id}?token={token}") for entry_id in range(1, 7)),
        ("GET", "/"),
        ("POST", f"/?token={token}"),
        ("DELETE", f"/preview/1?token={token}"),
    ):
        request(review_server, method, target)

    assert snapshot(source) == before
    assert query(report_path, "SELECT * FROM duplicate_entries") == entries
    assert query(report_path, "SELECT * FROM duplicate_groups") == groups


@pytest.mark.parametrize("interrupted", [True, False])
def test_serving_opens_the_browser_after_binding_and_closes_everything(
    review_library, monkeypatch, capsys, interrupted
):
    opened = []
    served = []

    def open_browser(url):
        port = urllib.parse.urlsplit(url).port
        with socket.create_connection((media_organizer.REVIEW_HOST, port), timeout=5):
            opened.append(url)

    def stop_normally(server, poll_interval=0.5):
        served.append(server)

    monkeypatch.setattr(media_organizer.webbrowser, "open", open_browser)
    monkeypatch.setattr(
        media_organizer.DuplicateReviewServer,
        "serve_forever",
        interrupt_serving(served) if interrupted else stop_normally,
    )

    media_organizer.serve_duplicate_review(review_library[0], port=0)

    [server] = served
    assert opened == [server.url]
    assert server.socket.fileno() == -1
    with pytest.raises(sqlite3.ProgrammingError):
        server.connection.execute("SELECT 1")
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(
            (media_organizer.REVIEW_HOST, server.server_port), timeout=5
        )
    output = capsys.readouterr().out
    assert server.url in output
    assert ("Stopped the review server." in output) is interrupted


def test_review_duplicates_arguments_default_to_port_8765():
    arguments = media_organizer.parse_arguments(
        ["review-duplicates", "--report", "report.sqlite3"]
    )
    custom = media_organizer.parse_arguments(
        ["review-duplicates", "--report", "report.sqlite3", "--port", "9000"]
    )

    assert (arguments.report, arguments.port) == (Path("report.sqlite3"), 8765)
    assert media_organizer.DEFAULT_REVIEW_PORT == 8765
    assert custom.port == 9000
    with pytest.raises(SystemExit):
        media_organizer.parse_arguments(["review-duplicates"])


def test_main_review_duplicates_serves_until_interrupted(
    review_library, browser, monkeypatch
):
    served = []
    monkeypatch.setattr(
        media_organizer.DuplicateReviewServer,
        "serve_forever",
        interrupt_serving(served),
    )

    result = media_organizer.main(
        ["review-duplicates", "--report", str(review_library[0]), "--port", "0"]
    )

    [server] = served
    assert result == 0
    assert browser == [server.url]
    assert server.url.startswith("http://127.0.0.1:")
    assert server.socket.fileno() == -1


def test_main_review_duplicates_reports_a_busy_port(review_library, browser, capsys):
    with socket.socket() as blocker:
        blocker.bind((media_organizer.REVIEW_HOST, 0))
        blocker.listen()
        port = blocker.getsockname()[1]
        result = media_organizer.main(
            [
                "review-duplicates",
                "--report",
                str(review_library[0]),
                "--port",
                str(port),
            ]
        )

    assert result == 1
    assert f"Error: Cannot serve on 127.0.0.1:{port}" in capsys.readouterr().err
    assert browser == []


def test_main_review_duplicates_rejects_bad_reports_and_ports(
    tmp_path, review_library, browser, capsys
):
    not_a_report = write_file(tmp_path / "notes.sqlite3", b"notes")

    for arguments, message in (
        (["--report", str(not_a_report)], "Not a SQLite duplicate report"),
        (["--report", str(tmp_path / "missing.sqlite3")], "No such file"),
        (
            ["--report", str(review_library[0]), "--port", "70000"],
            "Port must be between 0 and 65535",
        ),
    ):
        assert media_organizer.main(["review-duplicates", *arguments]) == 1
        assert message in capsys.readouterr().err
    assert browser == []


def post_delete(server, entry_id, **overrides):
    """Submit one entry's delete form as the confirmed page would."""
    fields = {"token": server.token, "entry": str(entry_id), "confirmed": "yes"}
    fields.update(overrides)
    return request(server, "POST", "/delete", body=urllib.parse.urlencode(fields))


def review_state(report_path):
    """Return every entry's status and error and every group's status."""
    return (
        query(
            report_path, "SELECT id, status, error FROM duplicate_entries ORDER BY id"
        ),
        query(report_path, "SELECT id, status FROM duplicate_groups ORDER BY id"),
    )


def files_state(tmp_path):
    """Snapshot the source tree and any private files outside it."""
    return {**snapshot(tmp_path / "source"), **snapshot(tmp_path / "private")}


def edit_entry(report_path, entry_id, **columns):
    """Overwrite columns of one report entry, as a tampering user could."""
    assignments = ", ".join(f"{column} = ?" for column in columns)
    with closing(sqlite3.connect(report_path)) as connection:
        connection.execute(
            f"UPDATE duplicate_entries SET {assignments} WHERE id = ?",
            (*columns.values(), entry_id),
        )
        connection.commit()


def recorded_identity(path):
    """Return the report columns that make an entry match an existing file."""
    info = path.lstat()
    return {
        "path": str(path),
        "device": info.st_dev,
        "inode": info.st_ino,
        "mtime_ns": info.st_mtime_ns,
        "sha256": media_organizer.sha256_file(path),
    }


def private_file(tmp_path):
    """Create a file outside the source with the size of the photo group."""
    return write_file(tmp_path / "private" / "photo.jpg", b"content-0")


def point_outside_the_source(report_path, source, tmp_path, monkeypatch):
    """Edit entry 1 to name an outside file whose recorded identity matches."""
    edit_entry(report_path, 1, **recorded_identity(private_file(tmp_path)))


def traverse_out_of_the_source(report_path, source, tmp_path, monkeypatch):
    """Edit entry 1 to reach an outside file through a parent reference."""
    identity = recorded_identity(private_file(tmp_path))
    identity["path"] = str(source / ".." / "private" / "photo.jpg")
    edit_entry(report_path, 1, **identity)


def leave_through_a_symlinked_directory(report_path, source, tmp_path, monkeypatch):
    """Edit entry 1 to reach an outside file through a symlinked directory."""
    private = private_file(tmp_path)
    (source / "linked").symlink_to(private.parent, target_is_directory=True)
    identity = recorded_identity(private)
    identity["path"] = str(source / "linked" / private.name)
    edit_entry(report_path, 1, **identity)


def swap_in_a_symlink(report_path, source, tmp_path, monkeypatch):
    """Replace the selected copy with a symlink to its duplicate."""
    (source / "a.jpg").unlink()
    (source / "a.jpg").symlink_to(source / "b.jpg")


def replace_the_file(report_path, source, tmp_path, monkeypatch):
    """Replace the selected copy with a new inode holding the same bytes."""
    path = source / "a.jpg"
    recorded = path.stat().st_mtime_ns
    replacement = write_file(source / "replacement.tmp", path.read_bytes())
    os.utime(replacement, ns=(recorded, recorded))
    os.replace(replacement, path)


def modify_content_in_place(report_path, source, tmp_path, monkeypatch):
    """Change one byte while keeping the inode, size, and mtime."""
    path = source / "a.jpg"
    recorded = path.stat().st_mtime_ns
    with path.open("r+b") as handle:
        handle.write(b"X")
    os.utime(path, ns=(recorded, recorded))


def change_the_mtime(report_path, source, tmp_path, monkeypatch):
    """Give the selected copy a different modification time."""
    os.utime(source / "a.jpg", ns=(1, 1))


def change_the_size(report_path, source, tmp_path, monkeypatch):
    """Append bytes to the selected copy."""
    with (source / "a.jpg").open("ab") as handle:
        handle.write(b"more")


def remove_the_copy(report_path, source, tmp_path, monkeypatch):
    """Delete the selected copy outside the review page."""
    (source / "a.jpg").unlink()


def remove_its_duplicate(report_path, source, tmp_path, monkeypatch):
    """Delete the only other copy outside the review page."""
    (source / "b.jpg").unlink()


def fail_the_digest(report_path, source, tmp_path, monkeypatch):
    """Make reading the selected copy for its byte digest fail."""

    def unreadable(path, progress=None):
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr(media_organizer, "sha256_file", unreadable)


def fail_the_unlink(report_path, source, tmp_path, monkeypatch):
    """Make the operating system refuse the deletion."""

    def refuse(path, *args, **kwargs):
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr(media_organizer.os, "unlink", refuse)


def test_each_copy_has_a_confirmed_token_protected_delete_form(
    review_server, review_library
):
    _report_path, source = review_library

    page = review_page(review_server)

    token_field = f'<input type="hidden" name="token" value="{review_server.token}">'
    assert page.count('<form method="post" action="/delete" class="delete"') == 5
    assert page.count(token_field) == 5
    assert page.count('<input type="hidden" name="confirmed" value="">') == 5
    assert page.count('<button type="submit">Delete this copy</button>') == 5
    assert '<input type="hidden" name="entry" value="3">' in page
    photo = (source / "a.jpg").resolve()
    assert f'data-confirm="Permanently delete {photo}? This cannot be undone."' in page
    assert f'<script nonce="{review_server.nonce}">' in page
    assert "if (!window.confirm(form.dataset.confirm))" in page
    assert 'form.elements.confirmed.value = "yes";' in page
    assert "cannot be undone" in page


def test_one_confirmed_post_deletes_only_the_selected_copy(
    review_server, review_library
):
    report_path, source = review_library
    before = snapshot(source)

    status, headers, body = post_delete(review_server, 1)

    assert (status, headers["Location"], body) == (
        303,
        f"/?token={review_server.token}",
        b"",
    )
    deleted = source / "a.jpg"
    assert not deleted.exists()
    assert snapshot(source) == {
        path: state for path, state in before.items() if path != deleted
    }
    entries, groups = review_state(report_path)
    assert entries == [
        (1, "deleted", None),
        (2, "present", None),
        (3, "present", None),
        (4, "present", None),
        (5, "present", None),
    ]
    assert groups == [(1, "resolved"), (2, "unresolved")]
    assert "Group 1:" not in review_page(review_server)


def test_three_copy_groups_stay_in_review_until_one_copy_remains(
    review_server, review_library
):
    report_path, source = review_library

    assert post_delete(review_server, 3)[0] == 303
    assert review_state(report_path)[1] == [(1, "unresolved"), (2, "unresolved")]
    assert "Group 2: 2 identical copies" in review_page(review_server)
    assert post_delete(review_server, 4)[0] == 303
    status, _headers, _body = post_delete(review_server, 5)

    assert status == 409
    assert review_state(report_path)[1] == [(1, "unresolved"), (2, "resolved")]
    assert sorted(path.name for path in source.iterdir()) == [
        "a.jpg",
        "b.jpg",
        "third.mp4",
    ]


def test_repeated_submissions_return_the_already_resolved_response(
    review_server, review_library
):
    report_path, source = review_library
    assert post_delete(review_server, 1)[0] == 303
    before = snapshot(source)
    state = review_state(report_path)

    for entry_id in (1, 2):
        status, _headers, body = post_delete(review_server, entry_id)
        assert (status, body) == (409, b"This copy or its group is already resolved\n")

    assert snapshot(source) == before
    assert review_state(report_path) == state
    assert (source / "b.jpg").exists()


@pytest.mark.parametrize(
    "overrides, status",
    [
        ({"token": ""}, 403),
        ({"token": "wrong"}, 403),
        ({"token": "é"}, 403),
        ({"confirmed": ""}, 400),
        ({"confirmed": "no"}, 400),
        ({"entry": ""}, 404),
        ({"entry": "99"}, 404),
        ({"entry": "0"}, 404),
        ({"entry": "1 OR 1=1"}, 404),
        ({"entry": "../a.jpg"}, 404),
        ({"entry": "{path}"}, 404),
    ],
)
def test_rejected_delete_requests_preserve_every_file(
    review_server, review_library, overrides, status
):
    report_path, source = review_library
    before = snapshot(source)
    state = review_state(report_path)
    fields = {
        name: value.format(path=source / "a.jpg") for name, value in overrides.items()
    }

    code, _headers, body = post_delete(review_server, 1, **fields)

    assert code == status
    assert str(source) not in body.decode()
    assert snapshot(source) == before
    assert review_state(report_path) == state


def test_get_and_malformed_requests_cannot_delete(review_server, review_library):
    report_path, source = review_library
    token = review_server.token
    before = snapshot(source)
    state = review_state(report_path)
    confirmed = urllib.parse.urlencode(
        {"token": token, "entry": "1", "confirmed": "yes"}
    )
    two_tokens = urllib.parse.urlencode(
        [("token", token), ("token", token), ("entry", "1"), ("confirmed", "yes")]
    )

    status, headers, _body = request(review_server, "GET", f"/delete?{confirmed}")
    assert (status, headers["Allow"]) == (405, "POST")
    assert request(review_server, "PUT", f"/delete?{confirmed}")[0] == 405
    assert request(review_server, "POST", f"/?{confirmed}")[0] == 405
    assert request(review_server, "POST", "/delete", body=two_tokens)[0] == 403
    unconfirmed = f"token={token}&entry=1"
    assert request(review_server, "POST", "/delete", body=unconfirmed)[0] == 400
    for length in ("abc", "5000"):
        headers = {"Content-Length": length}
        assert request(review_server, "POST", "/delete", headers=headers)[0] == 400

    assert snapshot(source) == before
    assert review_state(report_path) == state


@pytest.mark.parametrize(
    "tamper, reason",
    [
        (point_outside_the_source, "The file is outside the report's source directory"),
        (
            traverse_out_of_the_source,
            "The file is outside the report's source directory",
        ),
        (
            leave_through_a_symlinked_directory,
            "The file is outside the report's source directory",
        ),
        (swap_in_a_symlink, "The path is no longer a regular file"),
        (replace_the_file, "The file changed after duplicate detection"),
        (modify_content_in_place, "The file content changed after duplicate detection"),
        (change_the_mtime, "The file changed after duplicate detection"),
        (change_the_size, "The file changed after duplicate detection"),
        (remove_the_copy, "The file is no longer available"),
        (remove_its_duplicate, "No other copy in this group still matches the report"),
        (fail_the_digest, "Deletion failed: Permission denied"),
        (fail_the_unlink, "Deletion failed: Permission denied"),
    ],
)
def test_failed_revalidation_deletes_nothing_and_records_why(
    tmp_path, review_server, review_library, monkeypatch, tamper, reason
):
    report_path, source = review_library
    tamper(report_path, source, tmp_path, monkeypatch)
    before = files_state(tmp_path)

    status, headers, _body = post_delete(review_server, 1)

    assert (status, headers["Location"]) == (303, f"/?token={review_server.token}")
    assert files_state(tmp_path) == before
    entries, groups = review_state(report_path)
    assert entries[0] == (1, "present", reason)
    assert groups == [(1, "unresolved"), (2, "unresolved")]
    assert f'<p class="error">{html.escape(reason)}</p>' in review_page(review_server)


def assert_report_failure_deleted_nothing(response, report_path, source, before):
    """Assert a report failure answered 500 and left every file and entry as is."""
    status, headers, body = response
    assert (status, body) == (500, b"The duplicate report could not be updated\n")
    assert headers["Cache-Control"] == "no-store"
    assert snapshot(source) == before
    entries, groups = review_state(report_path)
    assert entries[0] == (1, "present", None)
    assert groups == [(1, "unresolved"), (2, "unresolved")]


def test_deletion_writes_its_status_under_the_write_lock_before_unlinking(
    review_server, review_library, monkeypatch
):
    report_path, source = review_library
    observed = []
    real_unlink = os.unlink

    def checked_unlink(path, *args, **kwargs):
        staged = review_server.connection.execute(
            "SELECT status FROM duplicate_entries WHERE id = 1"
        ).fetchone()[0]
        with closing(sqlite3.connect(report_path, timeout=0)) as other:
            committed = other.execute(
                "SELECT status FROM duplicate_entries WHERE id = 1"
            ).fetchone()[0]
            try:
                other.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as error:
                lock = str(error)
            else:
                lock = "not held"
        observed.append((staged, committed, lock))
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(media_organizer.os, "unlink", checked_unlink)

    status, _headers, _body = post_delete(review_server, 1)

    assert status == 303
    assert observed == [("deleted", "present", "database is locked")]
    assert not (source / "a.jpg").exists()
    entries, groups = review_state(report_path)
    assert entries[0] == (1, "deleted", None)
    assert groups == [(1, "resolved"), (2, "unresolved")]


def test_a_change_after_hashing_discards_the_staged_status(
    review_server, review_library, monkeypatch
):
    report_path, source = review_library
    real_sha256_file = media_organizer.sha256_file

    def touch_after_hashing(path, progress=None):
        digest = real_sha256_file(path, progress)
        os.utime(path, ns=(1, 1))
        return digest

    monkeypatch.setattr(media_organizer, "sha256_file", touch_after_hashing)

    status, _headers, _body = post_delete(review_server, 1)

    assert status == 303
    assert (source / "a.jpg").exists()
    entries, groups = review_state(report_path)
    assert entries[0] == (1, "present", "The file changed after duplicate detection")
    assert groups == [(1, "unresolved"), (2, "unresolved")]


def test_a_read_only_report_deletes_nothing(review_library):
    report_path, source = review_library
    os.chmod(report_path, 0o444)
    if os.access(report_path, os.W_OK):
        pytest.skip("the current user can write read-only files")
    before = snapshot(source)

    with running_server(report_path) as server:
        response = post_delete(server, 1)

    assert_report_failure_deleted_nothing(response, report_path, source, before)


def test_a_report_locked_by_another_connection_deletes_nothing(
    review_server, review_library
):
    report_path, source = review_library
    # Fail fast instead of waiting for the default five-second busy timeout.
    review_server.connection.execute("PRAGMA busy_timeout = 50")
    before = snapshot(source)

    with closing(sqlite3.connect(report_path)) as holder:
        holder.execute("BEGIN IMMEDIATE")
        response = post_delete(review_server, 1)
        holder.rollback()

    assert_report_failure_deleted_nothing(response, report_path, source, before)


def test_a_failing_status_write_deletes_nothing(review_server, review_library):
    report_path, source = review_library
    with closing(sqlite3.connect(report_path)) as connection:
        connection.execute(
            """
            CREATE TRIGGER refuse_status BEFORE UPDATE OF status ON duplicate_entries
            BEGIN SELECT RAISE(ABORT, 'status write refused'); END
            """
        )
        connection.commit()
    before = snapshot(source)

    response = post_delete(review_server, 1)

    assert_report_failure_deleted_nothing(response, report_path, source, before)
