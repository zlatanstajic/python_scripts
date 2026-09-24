"""Tests for the copy-only media library organizer."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from scripts import media_organizer


class MappingGeocoder:
    """Test geocoder returning exact coordinate mappings."""

    def __init__(self, locations):
        self.locations = locations

    def resolve(self, latitude, longitude):
        return self.locations.get((latitude, longitude))


def metadata_for(path: Path, timestamp="2026-09-08T18:42:15+02:00"):
    """Build metadata from a synthetic media path."""
    stat = path.stat()
    return media_organizer.MediaMetadata(
        path=str(path.resolve()),
        original_filename=path.name,
        extension=path.suffix,
        original_directory=str(path.parent.resolve()),
        file_size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        recording_timestamp=timestamp,
        media_type=(
            "image"
            if path.suffix.lower() in media_organizer.IMAGE_EXTENSIONS
            else "video"
        ),
        recording_timezone="+02:00" if timestamp else None,
        timestamp_provenance="embedded:creation_time" if timestamp else None,
    )


def test_discover_media_is_recursive_and_supports_expected_formats(tmp_path):
    source = tmp_path / "Media"
    nested = source / "2026" / "Sеptember"
    nested.mkdir(parents=True)
    expected = []
    for index, extension in enumerate(sorted(media_organizer.SUPPORTED_EXTENSIONS)):
        path = nested / f"video {index}{extension.upper()}"
        path.write_bytes(b"video")
        expected.append(path.resolve())
    (nested / "notes.txt").write_text("not media", encoding="utf-8")

    assert media_organizer.discover_media(source) == sorted(expected)


def test_discover_media_excludes_generated_directories(tmp_path):
    source = tmp_path / "source"
    hidden = source / ".media-organizer-copy"
    hidden.mkdir(parents=True)
    (hidden / "partial.mp4").write_bytes(b"partial")
    kept = source / "kept.mp4"
    kept.write_bytes(b"kept")

    assert media_organizer.discover_media(source) == [kept.resolve()]


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

    monkeypatch.setattr(media_organizer, "_run_json", fake_run)
    result = media_organizer.extract_metadata(video)

    modified = datetime.fromtimestamp(video.stat().st_mtime).astimezone()
    assert result.recording_timestamp == modified.isoformat(timespec="seconds")
    assert result.recording_timezone == media_organizer._normalize_timezone(
        modified.strftime("%z")
    )
    assert result.timestamp_provenance == "filesystem:mtime"
    assert (result.latitude, result.longitude) == (41.3851, 2.1734)
    assert (result.width, result.height, result.duration) == (1920, 1080, 4.25)
    assert result.camera == "Example Camera"
    assert result.title == "Old town"


def test_extract_image_metadata_with_ffprobe_and_exiftool(monkeypatch, tmp_path):
    image = tmp_path / "holiday.JPG"
    image.write_bytes(b"image-data")

    def fake_run(command):
        if command[0] == "ffprobe":
            return {
                "streams": [
                    {
                        "codec_type": "video",
                    }
                ],
                "format": {},
            }
        return [
            {
                "DateTimeOriginal": "2022:08:14 12:34:56+02:00",
                "GPSLatitude": 36.32,
                "GPSLongitude": 28.09,
                "Make": "Example",
                "Model": "Phone",
                "ImageWidth": 4032,
                "ImageHeight": 3024,
            }
        ]

    monkeypatch.setattr(media_organizer, "_run_json", fake_run)
    result = media_organizer.extract_metadata(image)

    assert result.media_type == "image"
    assert result.duration is None
    assert (result.width, result.height) == (4032, 3024)
    assert (result.latitude, result.longitude) == (36.32, 28.09)
    assert result.camera == "Example Phone"


@pytest.mark.parametrize(
    "stream, exif_orientation, expected",
    [
        ({"side_data_list": [{"rotation": 90}]}, None, 270),
        ({"side_data_list": [{"rotation": -90}]}, 8, 90),
        ({"side_data_list": [{"rotation": -180}]}, None, 180),
        ({}, 6, 90),
        ({}, 8, 270),
        ({}, 1, 0),
        ({}, None, 0),
    ],
)
def test_display_rotation_prefers_ffprobe_over_exif_orientation(
    stream, exif_orientation, expected
):
    assert media_organizer._display_rotation(stream, exif_orientation) == expected


@pytest.mark.parametrize(
    "exiftool_output, expected_size",
    [
        ([{"ImageWidth": 4032, "ImageHeight": 3024, "Orientation": 6}], (3024, 4032)),
        (None, None),
    ],
)
def test_tiled_photo_takes_its_size_from_exiftool(
    monkeypatch, tmp_path, exiftool_output, expected_size
):
    photo = tmp_path / "IMG_0001.HEIC"
    photo.write_bytes(b"photo")

    def fake_run(command):
        if command[0] == "ffprobe":
            tile = {"codec_type": "video", "width": 512, "height": 512}
            return {"streams": [tile, dict(tile)], "format": {}}
        if exiftool_output is None:
            raise FileNotFoundError("exiftool")
        return exiftool_output

    monkeypatch.setattr(media_organizer, "_run_json", fake_run)
    result = media_organizer.extract_metadata(photo)

    assert media_organizer.display_size(result) == expected_size


def test_extract_metadata_rejects_undecodable_image(monkeypatch, tmp_path):
    candidate = tmp_path / "invalid.jpg"
    candidate.write_bytes(b"not-image")
    monkeypatch.setattr(
        media_organizer,
        "_run_json",
        lambda _command: {"streams": [], "format": {}},
    )

    with pytest.raises(ValueError, match="no decodable image"):
        media_organizer.extract_metadata(candidate)


def test_extract_metadata_rejects_file_without_video_stream(monkeypatch, tmp_path):
    candidate = tmp_path / "invalid.mp4"
    candidate.write_bytes(b"not-video")
    monkeypatch.setattr(
        media_organizer,
        "_run_json",
        lambda _command: {"streams": [], "format": {}},
    )

    with pytest.raises(ValueError, match="no video stream"):
        media_organizer.extract_metadata(candidate)


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

    monkeypatch.setattr(media_organizer, "_run_json", fake_run)
    result = media_organizer.extract_metadata(candidate)

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

    monkeypatch.setattr(media_organizer, "_run_json", fake_run)
    result = media_organizer.extract_metadata(candidate)

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

    media_organizer._populate_metadata(
        metadata,
        {"com.apple.quicktime.location.ISO6709": "+44.8178+020.4569+120.0/"},
    )

    assert metadata.latitude == 44.8178
    assert metadata.longitude == 20.4569


def test_standalone_recording_timezone_is_preserved(tmp_path):
    candidate = tmp_path / "clip.mov"
    candidate.write_bytes(b"video")
    metadata = metadata_for(candidate, timestamp=None)

    media_organizer._populate_metadata(
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
            (44.1, 20.1): media_organizer.Location(
                "Serbia", "Village A", "Village A river"
            ),
            (44.2, 20.2): media_organizer.Location(
                "Serbia", "Village A", "Village A forest"
            ),
        }
    )

    for metadata in (first_metadata, second_metadata):
        media_organizer.classify_location(metadata, source, geocoder, {})

    assert first_metadata.locality == second_metadata.locality == "Village A"
    assert first_metadata.detailed_place != second_metadata.detailed_place


def test_neighboring_localities_remain_separate(tmp_path):
    source = tmp_path / "videos"
    source.mkdir()
    places = []
    geocoder = MappingGeocoder(
        {
            (1.0, 2.0): media_organizer.Location("Serbia", "Village A"),
            (1.1, 2.1): media_organizer.Location("Serbia", "Village B"),
        }
    )
    for index, coordinates in enumerate(((1.0, 2.0), (1.1, 2.1))):
        path = source / f"{index}.mp4"
        path.write_bytes(b"video")
        item = metadata_for(path)
        item.latitude, item.longitude = coordinates
        media_organizer.classify_location(item, source, geocoder, {})
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

    media_organizer.classify_location(
        metadata, source.parent, media_organizer.NullGeocoder(), overrides
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

    media_organizer.classify_location(
        metadata, source, media_organizer.NullGeocoder(), overrides
    )

    assert (metadata.country, metadata.locality) == ("Serbia", "Belgrade")
    assert metadata.location_provenance == "user-override"


@pytest.mark.parametrize(
    "folder_name, expected",
    [
        ("Family videos", "Family_videos"),
        ("2021-06 - Videos description", "Videos_description"),
        ("2022-08 - Traganou Beach on Rhodes", "Traganou_Beach_on_Rhodes"),
    ],
)
def test_source_folder_title(folder_name, expected):
    assert media_organizer.source_folder_title(Path(folder_name)) == expected


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

    plan = media_organizer.build_plan(
        source,
        output,
        [first_metadata, second_metadata, unknown_metadata],
        [],
    )

    destinations = [Path(entry["destination"]) for entry in plan["entries"]]
    assert destinations[0].parent == output / "2026" / "Spain" / "Lloret-de-Mar"
    assert destinations[0].name == "2026-09-08_18-42-15_Lloret-de-Mar.mov"
    assert destinations[1].name == "2026-09-08_18-42-15_Lloret-de-Mar_002.mov"
    unknown_hash = media_organizer.sha256_file(unknown)[:12]
    assert destinations[2] == (
        output / "Unclassified" / "Unknown-Year" / f"Undated_{unknown_hash}.mp4"
    )
    assert "uncertain" not in destinations[2].name


def test_all_unknown_locations_use_source_folder_description_as_title(tmp_path):
    source = tmp_path / "Camera" / "Stark" / "2019"
    source_folder = source / "2019-07 - Jul - Lefkada"
    output = tmp_path / "Sorted" / "Stark"
    source_folder.mkdir(parents=True)
    path = source_folder / "FHD0015.MOV"
    path.write_bytes(b"video")
    metadata = metadata_for(path, timestamp="2019-07-21T17:07:52+02:00")
    plan = media_organizer.build_plan(source, output, [metadata], [])

    destination = Path(plan["entries"][0]["destination"])
    assert destination == output / "2019" / "2019-07-21_17-07-52_Jul_Lefkada.MOV"
    assert "FHD0015" not in destination.name


def test_build_plan_includes_images_and_media_counts(tmp_path):
    source = tmp_path / "Photos"
    source_folder = source / "2022-08 - Traganou Beach on Rhodes"
    output = tmp_path / "Sorted"
    source_folder.mkdir(parents=True)
    image = source_folder / "IMG_1031.JPG"
    image.write_bytes(b"image")
    metadata = metadata_for(image, timestamp="2022-08-14T12:34:56+02:00")
    plan = media_organizer.build_plan(source, output, [metadata], [])

    entry = plan["entries"][0]
    destination = Path(entry["destination"])
    assert destination == output / "2022" / (
        "2022-08-14_12-34-56_Traganou_Beach_on_Rhodes.JPG"
    )
    assert entry["media_type"] == "image"
    assert plan["summary"]["total_files"] == 1
    assert plan["summary"]["images"] == 1
    assert plan["summary"]["videos"] == 0


def test_unknown_location_stays_unclassified_in_mixed_library(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    located_path = source / "located.mov"
    unknown_path = source / "unknown.mov"
    located_path.write_bytes(b"located")
    unknown_path.write_bytes(b"unknown")
    located = metadata_for(located_path)
    located.country = "Serbia"
    located.locality = "Belgrade"

    plan = media_organizer.build_plan(
        source,
        output,
        [located, metadata_for(unknown_path)],
        [],
    )

    destinations = {
        entry["original_filename"]: Path(entry["destination"])
        for entry in plan["entries"]
    }
    assert destinations["unknown.mov"] == output / "2026" / "Unclassified" / (
        "2026-09-08_18-42-15_Unclassified.mov"
    )


def test_cyrillic_locations_are_transliterated_to_ascii(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    path = source / "original-name.mp4"
    path.write_bytes(b"video")
    metadata = metadata_for(path)
    metadata.country = "Србија"
    metadata.locality = "Београд"

    plan = media_organizer.build_plan(source, output, [metadata], [])

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

    plan = media_organizer.build_plan(source, output, [metadata], [])

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
    assert media_organizer.english_country_name(source_name) == english_name


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
        media_organizer.validate_separate_trees(source, tmp_path / output_name)


def test_load_plan_accepts_legacy_video_schema(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    plan_path = tmp_path / "legacy-plan.json"
    payload = {
        "schema_version": 1,
        "source_directory": str(source),
        "output_directory": str(output),
        "entries": [],
    }
    plan_path.write_text(json.dumps(payload), encoding="utf-8")

    assert media_organizer.load_plan(plan_path)["schema_version"] == 1


def test_metadata_index_reuses_and_invalidates_records(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"first")
    metadata = metadata_for(video)
    index_path = tmp_path / "cache" / "index.sqlite3"

    with media_organizer.MetadataIndex(index_path) as index:
        index.put(metadata)
        assert index.get(video) == metadata
        video.write_bytes(b"changed content")
        assert index.get(video) is None


def test_metadata_index_rereads_records_cached_without_rotation(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    with media_organizer.MetadataIndex(tmp_path / "index.sqlite3") as index:
        index.put(metadata_for(video))
        (stored,) = index.connection.execute("SELECT metadata FROM media").fetchone()
        record = json.loads(stored)
        del record["rotation"]
        index.connection.execute("UPDATE media SET metadata = ?", (json.dumps(record),))

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

    with media_organizer.MetadataIndex(index_path) as index:
        assert index.get_geocode(40.4, -3.7) is None
        location = media_organizer.Location("Spain", "Madrid", "Madrid, Spain")
        index.put_geocode(40.4, -3.7, location)
        assert index.get_geocode(40.4, -3.7) == location


def test_write_plan_produces_json_and_markdown_reports(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    plan = media_organizer.build_plan(
        source,
        tmp_path / "output",
        [metadata_for(video)],
        [{"path": "/bad.avi", "reason": "invalid"}],
    )
    json_path = tmp_path / "organization-plan.json"
    markdown_path = tmp_path / "organization-plan.md"

    media_organizer.write_plan(plan, json_path, markdown_path)

    written_plan = json.loads(json_path.read_text(encoding="utf-8"))
    assert written_plan["summary"]["skipped"] == 1
    assert written_plan["summary"]["total_files"] == 1
    assert written_plan["summary"]["videos"] == 1
    assert written_plan["summary"]["images"] == 0
    assert written_plan["plan_file"] == str(json_path)
    assert written_plan["report_file"] == str(markdown_path)
    report = markdown_path.read_text(encoding="utf-8")
    assert report.startswith("# Media organization plan")
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
    plan = media_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = tmp_path / "plan.json"
    report_path = tmp_path / "plan.md"
    media_organizer.write_plan(plan, plan_path, report_path)

    progress = []
    assert media_organizer.apply_plan(plan_path, progress.append) == (1, 0, 0)
    destination = Path(plan["entries"][0]["destination"])
    assert destination.read_bytes() == original
    assert video.read_bytes() == original
    assert video.stat().st_mtime_ns == stat_before.st_mtime_ns
    assert not plan_path.exists()
    assert not report_path.exists()
    assert any("Copy: 100%" in message for message in progress)
    assert progress[-1] == "All entries succeeded; removing plan artifacts"

    repeated_plan = media_organizer.build_plan(
        source, output, [metadata_for(video)], []
    )
    media_organizer.write_plan(repeated_plan, plan_path, report_path)
    assert media_organizer.apply_plan(plan_path) == (0, 1, 0)
    assert not plan_path.exists()
    assert not report_path.exists()


def test_apply_refuses_changed_source_and_existing_conflict(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"original")
    plan = media_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = tmp_path / "plan.json"
    report_path = tmp_path / "plan.md"
    media_organizer.write_plan(plan, plan_path, report_path)
    destination = Path(plan["entries"][0]["destination"])
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"conflict")

    assert media_organizer.apply_plan(plan_path) == (0, 0, 1)
    assert destination.read_bytes() == b"conflict"
    assert plan_path.exists()
    assert report_path.exists()

    destination.unlink()
    video.write_bytes(b"changed")
    assert media_organizer.apply_plan(plan_path) == (0, 0, 1)
    assert not destination.exists()


def test_interrupted_copy_removes_partial_file(monkeypatch, tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"original")
    plan = media_organizer.build_plan(source, output, [metadata_for(video)], [])
    entry = plan["entries"][0]

    def interrupt(_input, output_handle, _total, _progress=None):
        output_handle.write(b"partial")
        raise OSError("interrupted")

    monkeypatch.setattr(media_organizer, "_copy_with_progress", interrupt)
    with pytest.raises(OSError, match="interrupted"):
        media_organizer._apply_entry(entry, source.resolve(), output.resolve())

    destination = Path(entry["destination"])
    assert not destination.exists()
    assert list(destination.parent.glob(".media-organizer-*.part")) == []


def test_apply_rejects_manifest_path_traversal(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    plan = media_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan["entries"][0]["destination"] = str(tmp_path / "escaped.mp4")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    assert media_organizer.apply_plan(plan_path) == (0, 0, 1)
    assert not (tmp_path / "escaped.mp4").exists()


def test_scan_uses_cached_metadata_without_reextracting(monkeypatch, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    index_path = tmp_path / "index.sqlite3"
    with media_organizer.MetadataIndex(index_path) as index:
        index.put(metadata_for(video))
        monkeypatch.setattr(
            media_organizer,
            "extract_metadata",
            lambda _path: pytest.fail("metadata should have come from cache"),
        )
        videos, skipped = media_organizer.scan_library(
            source, index, media_organizer.NullGeocoder(), {}
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
        media_organizer,
        "extract_metadata",
        lambda _path: (_ for _ in ()).throw(ValueError("invalid video")),
    )

    result = media_organizer.main(
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

    result = media_organizer.main(
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


@pytest.mark.parametrize(
    "geocoder_url",
    ["file:///etc/passwd", "ftp://example.com/reverse", "https:///reverse", "reverse"],
)
def test_non_http_geocoder_url_is_rejected(tmp_path, capsys, geocoder_url):
    source = tmp_path / "source"
    source.mkdir()

    result = media_organizer.main(
        [
            "scan",
            "--input",
            str(source),
            "--index",
            str(tmp_path / "index.sqlite3"),
            "--allow-network-geocoding",
            "--geocoder-url",
            geocoder_url,
        ]
    )

    assert result == 1
    assert "must be an http or https URL" in capsys.readouterr().err


@pytest.mark.parametrize(
    "geocoder_url",
    ["https://nominatim.example.org/reverse", "http://localhost:8080/reverse"],
)
def test_http_geocoder_url_is_accepted(tmp_path, geocoder_url):
    with media_organizer.MetadataIndex(tmp_path / "index.sqlite3") as index:
        geocoder = media_organizer.NominatimGeocoder(index, geocoder_url)

    assert geocoder.url == geocoder_url


def test_plan_reports_inside_source_are_rejected(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()

    result = media_organizer.main(
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
        media_organizer,
        "_scan_from_arguments",
        lambda _arguments, _output: ([], []),
    )

    result = media_organizer.main(
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
    assert "Building plan for 0 media file(s)." in command_output
    assert str(output / "organization-plan.json") in command_output


def test_apply_rejects_mutable_plan_inside_source(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    plan = media_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = source / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(ValueError, match="plan file must be outside"):
        media_organizer.apply_plan(plan_path)

    assert not output.exists()


def test_apply_continues_after_one_entry_fails(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    bad = source / "bad.mp4"
    good = source / "good.mp4"
    bad.write_bytes(b"bad")
    good.write_bytes(b"good")
    plan = media_organizer.build_plan(
        source, output, [metadata_for(bad), metadata_for(good)], []
    )
    bad.write_bytes(b"changed")
    plan_path = tmp_path / "plan.json"
    media_organizer.write_plan(plan, plan_path, tmp_path / "plan.md")

    assert media_organizer.apply_plan(plan_path) == (1, 0, 1)
    statuses = {
        entry["original_filename"]: entry["status"]
        for entry in json.loads(plan_path.read_text(encoding="utf-8"))["entries"]
    }
    assert statuses == {"bad.mp4": "failed", "good.mp4": "copied"}


def test_parse_arguments_requires_one_input_directory():
    args = media_organizer.parse_arguments(["scan", "--input", "/videos", "--verbose"])
    assert args.input == Path("/videos")
    assert args.verbose is True
    apply_args = media_organizer.parse_arguments(
        ["apply", "--plan", "/organized/organization-plan.json", "--verbose"]
    )
    assert apply_args.verbose is True
    with pytest.raises(SystemExit):
        media_organizer.parse_arguments(["scan"])


def test_source_permissions_and_content_are_not_modified(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    video = source / "clip.mp4"
    video.write_bytes(b"video")
    os.chmod(video, 0o640)
    before = video.stat()
    plan = media_organizer.build_plan(source, output, [metadata_for(video)], [])
    plan_path = tmp_path / "plan.json"
    media_organizer.write_plan(plan, plan_path, tmp_path / "plan.md")

    media_organizer.apply_plan(plan_path)

    after = video.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns
    assert video.read_bytes() == b"video"


@pytest.mark.parametrize(
    "relative_path, expected",
    [
        (
            "2026/Spain/Lloret-de-Mar/2026-09-08_18-42-15_Lloret-de-Mar.mov",
            ("Spain", "Lloret-de-Mar"),
        ),
        (
            "2026/Spain/Lloret-de-Mar/2026-09-08_18-42-15_Lloret-de-Mar_002.MOV",
            ("Spain", "Lloret-de-Mar"),
        ),
        ("2025/Spain/Lloret-de-Mar/2026-09-08_18-42-15_Lloret-de-Mar.mov", None),
        ("2026/Spain/Girona/2026-09-08_18-42-15_Lloret-de-Mar.mov", None),
        ("2026/2026/Unclassified/2026-09-08_18-42-15_Unclassified.mov", None),
        ("2019/Camera/Stark/FHD0015.MOV", None),
        ("2019/2019-07-21_17-07-52_Jul_Lefkada.MOV", None),
    ],
)
def test_organized_location_requires_the_generated_layout(
    tmp_path, relative_path, expected
):
    location = media_organizer.Location(*expected) if expected else None

    assert media_organizer.organized_location(tmp_path / relative_path) == location


def test_build_report_counts_types_formats_orientations_and_locations(tmp_path):
    library = tmp_path / "Organized"
    belgrade = library / "2026" / "Serbia" / "Belgrade"
    belgrade.mkdir(parents=True)
    upright_video = belgrade / "2026-09-08_18-42-15_Belgrade.MP4"
    photo = belgrade / "2026-09-08_18-42-15_Belgrade_002.jpg"
    square_photo = library / "square.png"
    unknown_video = library / "unknown.mov"
    for path in (upright_video, photo, square_photo, unknown_video):
        path.write_bytes(path.name.encode())
    upright = metadata_for(upright_video)
    upright.width, upright.height, upright.rotation = 1920, 1080, 90
    landscape = metadata_for(photo)
    landscape.width, landscape.height = 4000, 3000
    square = metadata_for(square_photo)
    square.width = square.height = 1080
    square.country, square.locality = "Greece", "Athens"
    square.location_provenance = "gps:nominatim"

    report = media_organizer.build_report(
        library,
        [upright, landscape, square, metadata_for(unknown_video)],
        [{"path": "/bad.avi", "reason": "invalid"}],
    )

    assert report["directory"] == str(library.resolve())
    assert report["summary"] == {
        "total_files": 4,
        "images": 2,
        "videos": 2,
        "classified": 3,
        "unclassified": 1,
        "countries": 2,
        "localities": 2,
        "skipped": 1,
    }
    assert report["formats"] == {
        "image": {"JPG": 1, "PNG": 1},
        "video": {"MOV": 1, "MP4": 1},
    }
    assert report["orientations"] == {
        "image": {"landscape": 1, "square": 1},
        "video": {"portrait": 1, "unknown": 1},
    }
    assert report["locations"] == {"Greece": {"Athens": 1}, "Serbia": {"Belgrade": 2}}
    entries = {Path(entry["path"]).name: entry for entry in report["entries"]}
    assert entries[upright_video.name]["resolution"] == "1080x1920"
    assert entries[upright_video.name]["location_provenance"] == "organized:path"
    assert entries[unknown_video.name]["country"] is None
    assert report["skipped"] == [{"path": "/bad.avi", "reason": "invalid"}]
    assert report["geocoding_attribution"] == media_organizer.NOMINATIM_ATTRIBUTION


def test_main_report_writes_inventory_to_current_directory(
    monkeypatch, tmp_path, capsys
):
    library = tmp_path / "Organized"
    athens = library / "2024" / "Greece" / "Athens"
    athens.mkdir(parents=True)
    (athens / "2024-05-01_10-00-00_Athens.jpg").write_bytes(b"photo")
    (library / "clip.mp4").write_bytes(b"video")

    def fake_run(command):
        if command[0] == "exiftool":
            raise FileNotFoundError("exiftool")
        width, height = (3000, 4000) if command[-1].endswith(".jpg") else (1920, 1080)
        stream = {"codec_type": "video", "width": width, "height": height}
        return {"streams": [stream], "format": {}}

    monkeypatch.setattr(media_organizer, "_run_json", fake_run)
    monkeypatch.chdir(library)
    arguments = ["report", "--index", str(tmp_path / "index.sqlite3")]

    assert media_organizer.main(arguments) == 0
    assert media_organizer.main(arguments) == 0

    report = json.loads((library / "media-report.json").read_text(encoding="utf-8"))
    assert report["directory"] == str(library.resolve())
    assert report["summary"]["total_files"] == 2
    assert report["orientations"] == {
        "image": {"portrait": 1},
        "video": {"landscape": 1},
    }
    assert report["locations"] == {"Greece": {"Athens": 1}}
    assert (
        f"Wrote {library.resolve() / 'media-report.json'}." in capsys.readouterr().out
    )
