"""Tests for the copy-only video library organizer."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from scripts import video_organizer


class MappingGeocoder:
    """Test geocoder returning exact coordinate mappings."""

    def __init__(self, locations):
        self.locations = locations

    def resolve(self, latitude, longitude):
        return self.locations.get((latitude, longitude))


def metadata_for(path: Path, timestamp="2026-09-08T18:42:15+02:00"):
    """Build metadata from a synthetic video path."""
    stat = path.stat()
    return video_organizer.VideoMetadata(
        path=str(path.resolve()),
        original_filename=path.name,
        extension=path.suffix,
        original_directory=str(path.parent.resolve()),
        file_size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        recording_timestamp=timestamp,
        recording_timezone="+02:00" if timestamp else None,
        timestamp_provenance="embedded:creation_time" if timestamp else None,
    )


def test_discover_videos_is_recursive_and_supports_expected_formats(tmp_path):
    source = tmp_path / "Videos"
    nested = source / "2026" / "Sеptember"
    nested.mkdir(parents=True)
    expected = []
    for index, extension in enumerate(sorted(video_organizer.SUPPORTED_EXTENSIONS)):
        path = nested / f"video {index}{extension.upper()}"
        path.write_bytes(b"video")
        expected.append(path.resolve())
    (nested / "notes.txt").write_text("not a video", encoding="utf-8")

    assert video_organizer.discover_videos(source) == sorted(expected)


def test_discover_videos_excludes_generated_directories(tmp_path):
    source = tmp_path / "source"
    hidden = source / ".video-organizer-copy"
    hidden.mkdir(parents=True)
    (hidden / "partial.mp4").write_bytes(b"partial")
    kept = source / "kept.mp4"
    kept.write_bytes(b"kept")

    assert video_organizer.discover_videos(source) == [kept.resolve()]


def test_extract_metadata_combines_ffprobe_and_exiftool(monkeypatch, tmp_path):
    video = tmp_path / "résumé clip.MOV"
    video.write_bytes(b"video-data")

    def fake_run(command):
        if command[0] == "ffprobe":
            return {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 1920,
                        "height": 1080,
                        "tags": {"creation_time": "2026-09-08T16:42:15Z"},
                    }
                ],
                "format": {"duration": "4.25", "tags": {"title": "Old town"}},
            }
        return [
            {
                "DateTimeOriginal": "2026:09:08 18:42:15+02:00",
                "GPSLatitude": 41.3851,
                "GPSLongitude": 2.1734,
                "Make": "Example",
                "Model": "Camera",
            }
        ]

    monkeypatch.setattr(video_organizer, "_run_json", fake_run)
    result = video_organizer.extract_metadata(video)

    modified = datetime.fromtimestamp(video.stat().st_mtime).astimezone()
    assert result.recording_timestamp == modified.isoformat(timespec="seconds")
    assert result.recording_timezone == video_organizer._normalize_timezone(
        modified.strftime("%z")
    )
    assert result.timestamp_provenance == "filesystem:mtime"
    assert (result.latitude, result.longitude) == (41.3851, 2.1734)
    assert (result.width, result.height, result.duration) == (1920, 1080, 4.25)
    assert result.camera == "Example Camera"
    assert result.title == "Old town"


def test_extract_metadata_rejects_file_without_video_stream(monkeypatch, tmp_path):
    candidate = tmp_path / "invalid.mp4"
    candidate.write_bytes(b"not-video")
    monkeypatch.setattr(
        video_organizer,
        "_run_json",
        lambda _command: {"streams": [], "format": {}},
    )

    with pytest.raises(ValueError, match="no video stream"):
        video_organizer.extract_metadata(candidate)


def test_extract_metadata_reports_conflicting_embedded_locations(monkeypatch, tmp_path):
    candidate = tmp_path / "conflict.mp4"
    candidate.write_bytes(b"video")

    def fake_run(command):
        if command[0] == "ffprobe":
            return {
                "streams": [{"codec_type": "video"}],
                "format": {"tags": {"Country": "Italy", "City": "Rome"}},
            }
        return [{"Country": "Greece", "City": "Athens"}]

    monkeypatch.setattr(video_organizer, "_run_json", fake_run)
    result = video_organizer.extract_metadata(candidate)

    assert result.country is None
    assert result.locality is None
    assert "Conflicting embedded geographic metadata" in result.warnings


def test_missing_exiftool_and_metadata_are_reported(monkeypatch, tmp_path):
    candidate = tmp_path / "plain.mp4"
    candidate.write_bytes(b"video")

    def fake_run(command):
        if command[0] == "exiftool":
            raise FileNotFoundError("exiftool")
        return {
            "streams": [{"codec_type": "video"}],
            "format": {},
        }

    monkeypatch.setattr(video_organizer, "_run_json", fake_run)
    result = video_organizer.extract_metadata(candidate)

    assert result.recording_timestamp is not None
    assert result.timestamp_provenance == "filesystem:mtime"
    assert any("ExifTool is not installed" in warning for warning in result.warnings)
    assert not any(
        "No reliable recording timestamp" in warning for warning in result.warnings
    )


def test_quicktime_iso6709_coordinates_are_parsed(tmp_path):
    candidate = tmp_path / "clip.mov"
    candidate.write_bytes(b"video")
    metadata = metadata_for(candidate)

    video_organizer._populate_metadata(
        metadata,
        {"com.apple.quicktime.location.ISO6709": "+44.8178+020.4569+120.0/"},
    )

    assert metadata.latitude == 44.8178
    assert metadata.longitude == 20.4569


def test_standalone_recording_timezone_is_preserved(tmp_path):
    candidate = tmp_path / "clip.mov"
    candidate.write_bytes(b"video")
    metadata = metadata_for(candidate, timestamp=None)

    video_organizer._populate_metadata(
        metadata,
        {
            "DateTimeOriginal": "2026:09:08 18:42:15",
            "OffsetTimeOriginal": "+0230",
        },
    )

    assert metadata.recording_timestamp == "2026-09-08T18:42:15+02:30"
    assert metadata.recording_timezone == "+02:30"


def test_gps_resolution_groups_landmarks_by_parent_locality(tmp_path):
    source = tmp_path / "videos"
    source.mkdir()
    first = source / "river.mp4"
    second = source / "forest.mp4"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    first_metadata = metadata_for(first)
    second_metadata = metadata_for(second)
    first_metadata.latitude, first_metadata.longitude = (44.1, 20.1)
    second_metadata.latitude, second_metadata.longitude = (44.2, 20.2)
    geocoder = MappingGeocoder(
        {
            (44.1, 20.1): video_organizer.Location(
                "Serbia", "Village A", "Village A river"
            ),
            (44.2, 20.2): video_organizer.Location(
                "Serbia", "Village A", "Village A forest"
            ),
        }
    )

    for metadata in (first_metadata, second_metadata):
        video_organizer.classify_location(metadata, source, geocoder, {})

    assert first_metadata.locality == second_metadata.locality == "Village A"
    assert first_metadata.detailed_place != second_metadata.detailed_place


def test_neighboring_localities_remain_separate(tmp_path):
    source = tmp_path / "videos"
    source.mkdir()
    places = []
    geocoder = MappingGeocoder(
        {
            (1.0, 2.0): video_organizer.Location("Serbia", "Village A"),
            (1.1, 2.1): video_organizer.Location("Serbia", "Village B"),
        }
    )
    for index, coordinates in enumerate(((1.0, 2.0), (1.1, 2.1))):
        path = source / f"{index}.mp4"
        path.write_bytes(b"video")
        item = metadata_for(path)
        item.latitude, item.longitude = coordinates
        video_organizer.classify_location(item, source, geocoder, {})
        places.append(item.locality)

    assert places == ["Village A", "Village B"]


def test_conflicting_recognizable_locations_are_not_guessed(tmp_path):
    source = tmp_path / "Athens"
    source.mkdir()
    path = source / "Rome.mp4"
    path.write_bytes(b"video")
    metadata = metadata_for(path)
    overrides = {
        "places": {
            "Athens": {"country": "Greece", "locality": "Athens"},
            "Rome": {"country": "Italy", "locality": "Rome"},
        }
    }

    video_organizer.classify_location(
        metadata, source.parent, video_organizer.NullGeocoder(), overrides
    )

    assert metadata.locality is None
    assert "Conflicting recognizable location names" in metadata.warnings


def test_user_file_override_classifies_an_unknown_video(tmp_path):
    source = tmp_path / "videos"
    source.mkdir()
    path = source / "clip.mp4"
    path.write_bytes(b"video")
    metadata = metadata_for(path)
    overrides = {"files": {"clip.mp4": {"country": "Serbia", "locality": "Belgrade"}}}

    video_organizer.classify_location(
        metadata, source, video_organizer.NullGeocoder(), overrides
    )

    assert (metadata.country, metadata.locality) == ("Serbia", "Belgrade")
    assert metadata.location_provenance == "user-override"


def test_build_plan_handles_unknowns_unicode_and_collisions(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "organized"
    source.mkdir()
    first = source / "one.mov"
    second = source / "two.mov"
    unknown = source / "uncertain?.mp4"
    for path in (first, second, unknown):
        path.write_bytes(path.name.encode())
    first_metadata = metadata_for(first)
    second_metadata = metadata_for(second)
    for item in (first_metadata, second_metadata):
        item.country = "España"
        item.locality = "Lloret de Mar"
        item.location_provenance = "gps:reverse-geocoded"
    unknown_metadata = metadata_for(unknown, timestamp=None)

    plan = video_organizer.build_plan(
        source,
        output,
        [first_metadata, second_metadata, unknown_metadata],
        [],
    )

    destinations = [Path(entry["destination"]) for entry in plan["entries"]]
    assert destinations[0].parent == output / "2026" / "Spain" / "Lloret-de-Mar"
    assert destinations[0].name == "2026-09-08_18-42-15_Lloret-de-Mar.mov"
    assert destinations[1].name == "2026-09-08_18-42-15_Lloret-de-Mar_002.mov"
    unknown_hash = video_organizer.sha256_file(unknown)[:12]
    assert destinations[2] == (
        output / "Unclassified" / "Unknown-Year" / f"Undated_{unknown_hash}.mp4"
    )
    assert "uncertain" not in destinations[2].name


def test_known_date_unknown_location_does_not_use_original_stem(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    path = source / "IMG 1031.mov"
    path.write_bytes(b"video")
    plan = video_organizer.build_plan(source, output, [metadata_for(path)], [])

    destination = Path(plan["entries"][0]["destination"])
    assert destination == output / "2026" / "Unclassified" / (
        "2026-09-08_18-42-15_Unclassified.mov"
    )
    assert "IMG" not in destination.name


def test_cyrillic_locations_are_transliterated_to_ascii(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    path = source / "original-name.mp4"
    path.write_bytes(b"video")
    metadata = metadata_for(path)
    metadata.country = "Србија"
    metadata.locality = "Београд"

    plan = video_organizer.build_plan(source, output, [metadata], [])

    destination = Path(plan["entries"][0]["destination"])
    assert destination == output / "2026" / "Serbia" / "Belgrade" / (
        "2026-09-08_18-42-15_Belgrade.mp4"
    )
    assert destination.as_posix().isascii()


def test_unsupported_location_script_uses_ascii_fallback(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    path = source / "original.mp4"
    path.write_bytes(b"video")
    metadata = metadata_for(path)
    metadata.country = "日本"
    metadata.locality = "東京"

    plan = video_organizer.build_plan(source, output, [metadata], [])

    destination = Path(plan["entries"][0]["destination"])
    assert destination == output / "2026" / "Unknown-Country" / (
        "Unknown-Locality/2026-09-08_18-42-15_Unknown-Locality.mp4"
    )


@pytest.mark.parametrize(
    "source_name, english_name",
    [
        ("España", "Spain"),
        ("Шпанија", "Spain"),
        ("Србија", "Serbia"),
        ("Deutschland", "Germany"),
        ("Italia", "Italy"),
    ],
)
def test_known_country_names_are_canonicalized_to_english(source_name, english_name):
    assert video_organizer.english_country_name(source_name) == english_name


@pytest.mark.parametrize(
    "source_name, output_name",
    [
        ("library", "library"),
        ("library", "library/output"),
        ("output/library", "output"),
    ],
)
def test_source_destination_overlap_is_rejected(tmp_path, source_name, output_name):
    source = tmp_path / source_name
    source.mkdir(parents=True)

    with pytest.raises(ValueError, match="must not overlap"):
        video_organizer.validate_separate_trees(source, tmp_path / output_name)


def test_metadata_index_reuses_and_invalidates_records(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"first")
    metadata = metadata_for(video)
    index_path = tmp_path / "cache" / "index.sqlite3"

    with video_organizer.MetadataIndex(index_path) as index:
        index.put(metadata)
        assert index.get(video) == metadata
        video.write_bytes(b"changed content")
        assert index.get(video) is None


def test_metadata_index_invalidates_old_non_english_geocodes(tmp_path):
    index_path = tmp_path / "index.sqlite3"
    connection = sqlite3.connect(index_path)
    connection.execute(
        """
        CREATE TABLE geocodes (
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            country TEXT NOT NULL,
            locality TEXT NOT NULL,
            detailed_place TEXT,
            PRIMARY KEY (latitude, longitude)
        )
        """
    )
    connection.execute(
        "INSERT INTO geocodes VALUES (?, ?, ?, ?, ?)",
        (40.4, -3.7, "España", "Madrid", "Madrid, España"),
    )
    connection.commit()
    connection.close()

    with video_organizer.MetadataIndex(index_path) as index:
        assert index.get_geocode(40.4, -3.7) is None
        location = video_organizer.Location("Spain", "Madrid", "Madrid, Spain")
        index.put_geocode(40.4, -3.7, location)
        assert index.get_geocode(40.4, -3.7) == location


def test_write_plan_produces_json_and_markdown_reports(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    plan = video_organizer.build_plan(
        source,
        tmp_path / "output",
        [metadata_for(video)],
        [{"path": "/bad.avi", "reason": "invalid"}],
    )
    json_path = tmp_path / "organization-plan.json"
    markdown_path = tmp_path / "organization-plan.md"

    video_organizer.write_plan(plan, json_path, markdown_path)

    written_plan = json.loads(json_path.read_text(encoding="utf-8"))
    assert written_plan["summary"]["skipped"] == 1
    assert written_plan["plan_file"] == str(json_path)
    assert written_plan["report_file"] == str(markdown_path)
    report = markdown_path.read_text(encoding="utf-8")
    assert str(video.resolve()) in report
    assert "Unclassified" in report
    assert "/bad.avi" in report


def test_apply_copies_verifies_is_idempotent_and_preserves_source(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    original = b"original video bytes"
    video.write_bytes(original)
    stat_before = video.stat()
    plan = video_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = tmp_path / "plan.json"
    report_path = tmp_path / "plan.md"
    video_organizer.write_plan(plan, plan_path, report_path)

    progress = []
    assert video_organizer.apply_plan(plan_path, progress.append) == (1, 0, 0)
    destination = Path(plan["entries"][0]["destination"])
    assert destination.read_bytes() == original
    assert video.read_bytes() == original
    assert video.stat().st_mtime_ns == stat_before.st_mtime_ns
    assert not plan_path.exists()
    assert not report_path.exists()
    assert any("Copy: 100%" in message for message in progress)
    assert progress[-1] == "All entries succeeded; removing plan artifacts"

    repeated_plan = video_organizer.build_plan(
        source, output, [metadata_for(video)], []
    )
    video_organizer.write_plan(repeated_plan, plan_path, report_path)
    assert video_organizer.apply_plan(plan_path) == (0, 1, 0)
    assert not plan_path.exists()
    assert not report_path.exists()


def test_apply_refuses_changed_source_and_existing_conflict(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"original")
    plan = video_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = tmp_path / "plan.json"
    report_path = tmp_path / "plan.md"
    video_organizer.write_plan(plan, plan_path, report_path)
    destination = Path(plan["entries"][0]["destination"])
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"conflict")

    assert video_organizer.apply_plan(plan_path) == (0, 0, 1)
    assert destination.read_bytes() == b"conflict"
    assert plan_path.exists()
    assert report_path.exists()

    destination.unlink()
    video.write_bytes(b"changed")
    assert video_organizer.apply_plan(plan_path) == (0, 0, 1)
    assert not destination.exists()


def test_interrupted_copy_removes_partial_file(monkeypatch, tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"original")
    plan = video_organizer.build_plan(source, output, [metadata_for(video)], [])
    entry = plan["entries"][0]

    def interrupt(_input, output_handle, _total, _progress=None):
        output_handle.write(b"partial")
        raise OSError("interrupted")

    monkeypatch.setattr(video_organizer, "_copy_with_progress", interrupt)
    with pytest.raises(OSError, match="interrupted"):
        video_organizer._apply_entry(entry, source.resolve(), output.resolve())

    destination = Path(entry["destination"])
    assert not destination.exists()
    assert list(destination.parent.glob(".video-organizer-*.part")) == []


def test_apply_rejects_manifest_path_traversal(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    plan = video_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan["entries"][0]["destination"] = str(tmp_path / "escaped.mp4")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    assert video_organizer.apply_plan(plan_path) == (0, 0, 1)
    assert not (tmp_path / "escaped.mp4").exists()


def test_scan_uses_cached_metadata_without_reextracting(monkeypatch, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    index_path = tmp_path / "index.sqlite3"
    with video_organizer.MetadataIndex(index_path) as index:
        index.put(metadata_for(video))
        monkeypatch.setattr(
            video_organizer,
            "extract_metadata",
            lambda _path: pytest.fail("metadata should have come from cache"),
        )
        videos, skipped = video_organizer.scan_library(
            source, index, video_organizer.NullGeocoder(), {}
        )

    assert len(videos) == 1
    assert skipped == []
    assert videos[0].timestamp_provenance == "filesystem:mtime"
    expected = datetime.fromtimestamp(video.stat().st_mtime).astimezone()
    assert videos[0].recording_timestamp == expected.isoformat(timespec="seconds")


def test_main_scan_reports_invalid_candidate_without_traceback(
    monkeypatch, tmp_path, capsys
):
    source = tmp_path / "source"
    source.mkdir()
    (source / "bad.mp4").write_bytes(b"bad")
    index = tmp_path / "index.sqlite3"
    monkeypatch.setattr(
        video_organizer,
        "extract_metadata",
        lambda _path: (_ for _ in ()).throw(ValueError("invalid video")),
    )

    result = video_organizer.main(
        [
            "scan",
            "--input",
            str(source),
            "--index",
            str(index),
            "--verbose",
        ]
    )

    assert result == 1
    output = capsys.readouterr().out
    assert "Scanning recursively:" in output
    assert "Extracting metadata:" in output
    assert "[SKIPPED]" in output


def test_index_inside_source_is_rejected(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()

    result = video_organizer.main(
        [
            "scan",
            "--input",
            str(source),
            "--index",
            str(source / "index.sqlite3"),
        ]
    )

    assert result == 1
    assert "must be outside" in capsys.readouterr().err


def test_plan_reports_inside_source_are_rejected(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()

    result = video_organizer.main(
        [
            "plan",
            "--input",
            str(source),
            "--output",
            str(tmp_path / "output"),
            "--plan-file",
            str(source / "plan.json"),
            "--index",
            str(tmp_path / "index.sqlite3"),
        ]
    )

    assert result == 1
    assert "reports must be outside" in capsys.readouterr().err
    assert not (source / "plan.json").exists()


def test_main_plan_defaults_reports_to_output(monkeypatch, tmp_path, capsys):
    source = tmp_path / "source"
    output = tmp_path / "organized"
    source.mkdir()
    monkeypatch.setattr(
        video_organizer,
        "_scan_from_arguments",
        lambda _arguments, _output: ([], []),
    )

    result = video_organizer.main(
        [
            "plan",
            "--input",
            str(source),
            "--output",
            str(output),
            "--verbose",
        ]
    )

    assert result == 0
    assert (output / "organization-plan.json").exists()
    assert (output / "organization-plan.md").exists()
    command_output = capsys.readouterr().out
    assert "Building plan for 0 video(s)." in command_output
    assert str(output / "organization-plan.json") in command_output


def test_apply_rejects_mutable_plan_inside_source(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    plan = video_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = source / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(ValueError, match="plan file must be outside"):
        video_organizer.apply_plan(plan_path)

    assert not output.exists()


def test_apply_continues_after_one_entry_fails(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    bad = source / "bad.mp4"
    good = source / "good.mp4"
    bad.write_bytes(b"bad")
    good.write_bytes(b"good")
    plan = video_organizer.build_plan(
        source, output, [metadata_for(bad), metadata_for(good)], []
    )
    bad.write_bytes(b"changed")
    plan_path = tmp_path / "plan.json"
    video_organizer.write_plan(plan, plan_path, tmp_path / "plan.md")

    assert video_organizer.apply_plan(plan_path) == (1, 0, 1)
    statuses = {
        entry["original_filename"]: entry["status"]
        for entry in json.loads(plan_path.read_text(encoding="utf-8"))["entries"]
    }
    assert statuses == {"bad.mp4": "failed", "good.mp4": "copied"}


def test_parse_arguments_requires_one_input_directory():
    args = video_organizer.parse_arguments(["scan", "--input", "/videos", "--verbose"])
    assert args.input == Path("/videos")
    assert args.verbose is True
    apply_args = video_organizer.parse_arguments(
        ["apply", "--plan", "/organized/organization-plan.json", "--verbose"]
    )
    assert apply_args.verbose is True
    with pytest.raises(SystemExit):
        video_organizer.parse_arguments(["scan"])


def test_source_permissions_and_content_are_not_modified(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    os.chmod(video, 0o640)
    before = video.stat()
    plan = video_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = tmp_path / "plan.json"
    video_organizer.write_plan(plan, plan_path, tmp_path / "plan.md")

    video_organizer.apply_plan(plan_path)

    after = video.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns
    assert video.read_bytes() == b"video"
