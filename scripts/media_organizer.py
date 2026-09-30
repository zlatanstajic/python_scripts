#!/usr/bin/env python3
"""Build a verified, copy-only photo and video library from an approved plan.

The command has three phases: ``scan`` reads metadata without changing source
files, ``plan`` writes SQLite and Markdown manifests, and ``apply`` copies and
verifies the files described by an approved SQLite manifest. ``report`` writes
a SQLite inventory of the media in a directory, such as a finished library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable, Mapping, Protocol, Sequence, cast

VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".webm",
    ".wmv",
}
HEIF_EXTENSIONS = {".heic", ".heif"}
IMAGE_EXTENSIONS = {
    ".avif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
} | HEIF_EXTENSIONS
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, SCHEMA_VERSION}
REPORT_SCHEMA_VERSION = 1
PLAN_FILENAME = "organization-plan.sqlite3"
REPORT_FILENAME = "media-report.sqlite3"
SQLITE_HEADER = b"SQLite format 3\x00"
COPY_CHUNK_SIZE = 1024 * 1024
DEFAULT_GEOCODER_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_REQUEST_INTERVAL = 1.0
NOMINATIM_ATTRIBUTION = "Data © OpenStreetMap contributors (ODbL)"
NON_ALPHANUMERIC = re.compile(r"[^A-Za-z0-9]+")
TIMESTAMP_KEYS = (
    "DateTimeOriginal",
    "MediaCreateDate",
    "TrackCreateDate",
    "CreateDate",
    "creation_time",
)
GPS_LATITUDE_KEYS = ("GPSLatitude", "com.apple.quicktime.location.ISO6709")
GPS_LONGITUDE_KEYS = ("GPSLongitude",)
COUNTRY_KEYS = ("Country", "CountryCode", "LocationCountry")
LOCALITY_KEYS = ("City", "Town", "Village", "LocationCity")
EXIF_ORIENTATION_ROTATIONS = {3: 180, 4: 180, 5: 270, 6: 90, 7: 90, 8: 270}
# Classified copies are written to Year/Country/Locality/ and repeat the year
# and locality in their generated filename, optionally with a _NNN suffix.
ORGANIZED_PATH = re.compile(
    r"(?P<year>\d{4})/(?P<country>[A-Za-z0-9-]+)/(?P<locality>[A-Za-z0-9-]+)/"
    r"(?P=year)-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_(?P=locality)(?:_\d{3,})?\.\w+"
)

_TRANSLITERATION_BASE = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Ђ": "Dj",
    "Е": "E",
    "Ё": "Yo",
    "Є": "Ye",
    "Ж": "Zh",
    "З": "Z",
    "И": "I",
    "І": "I",
    "Ї": "Yi",
    "Й": "Y",
    "Ј": "J",
    "К": "K",
    "Л": "L",
    "Љ": "Lj",
    "М": "M",
    "Н": "N",
    "Њ": "Nj",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "Ћ": "C",
    "У": "U",
    "Ф": "F",
    "Х": "Kh",
    "Ц": "Ts",
    "Ч": "Ch",
    "Џ": "Dzh",
    "Ш": "Sh",
    "Щ": "Shch",
    "Ъ": "",
    "Ы": "Y",
    "Ь": "",
    "Э": "E",
    "Ю": "Yu",
    "Я": "Ya",
    "Ґ": "G",
    "Ѓ": "Gj",
    "Ѕ": "Dz",
    "Ќ": "Kj",
    "Α": "A",
    "Β": "V",
    "Γ": "G",
    "Δ": "D",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "I",
    "Θ": "Th",
    "Ι": "I",
    "Κ": "K",
    "Λ": "L",
    "Μ": "M",
    "Ν": "N",
    "Ξ": "X",
    "Ο": "O",
    "Π": "P",
    "Ρ": "R",
    "Σ": "S",
    "Τ": "T",
    "Υ": "Y",
    "Φ": "F",
    "Χ": "Ch",
    "Ψ": "Ps",
    "Ω": "O",
}
TRANSLITERATION = str.maketrans(
    _TRANSLITERATION_BASE
    | {key.lower(): value.lower() for key, value in _TRANSLITERATION_BASE.items()}
    | {"ς": "s"}
)
COUNTRY_ENGLISH_ALIASES = {
    "albania": "Albania",
    "shqiperia": "Albania",
    "austria": "Austria",
    "osterreich": "Austria",
    "belgie": "Belgium",
    "belgique": "Belgium",
    "bosna-i-hercegovina": "Bosnia and Herzegovina",
    "bosna-i-herzegovina": "Bosnia and Herzegovina",
    "bulgaria": "Bulgaria",
    "balgariya": "Bulgaria",
    "cesko": "Czechia",
    "croatia": "Croatia",
    "hrvatska": "Croatia",
    "danmark": "Denmark",
    "deutschland": "Germany",
    "eire": "Ireland",
    "ellada": "Greece",
    "espana": "Spain",
    "finland": "Finland",
    "france": "France",
    "germany": "Germany",
    "grcka": "Greece",
    "grchka": "Greece",
    "greece": "Greece",
    "hungary": "Hungary",
    "island": "Iceland",
    "italia": "Italy",
    "italy": "Italy",
    "magyarorszag": "Hungary",
    "montenegro": "Montenegro",
    "crna-gora": "Montenegro",
    "nederland": "Netherlands",
    "north-macedonia": "North Macedonia",
    "makedonija": "North Macedonia",
    "norge": "Norway",
    "polska": "Poland",
    "romania": "Romania",
    "serbia": "Serbia",
    "srbija": "Serbia",
    "slovenia": "Slovenia",
    "slovenija": "Slovenia",
    "slovensko": "Slovakia",
    "spain": "Spain",
    "spanija": "Spain",
    "shpanija": "Spain",
    "suisse": "Switzerland",
    "suomi": "Finland",
    "sverige": "Sweden",
    "schweiz": "Switzerland",
    "svizzera": "Switzerland",
    "turkiye": "Turkey",
}
LOCALITY_ENGLISH_ALIASES = {
    "athina": "Athens",
    "beograd": "Belgrade",
    "firenze": "Florence",
    "koln": "Cologne",
    "moskva": "Moscow",
    "munchen": "Munich",
    "praha": "Prague",
    "roma": "Rome",
    "venezia": "Venice",
    "wien": "Vienna",
}

ProgressCallback = Callable[[str], None]
PercentageCallback = Callable[[int], None]


@dataclass
class MediaMetadata:
    """Metadata and provenance collected for one candidate media file."""

    path: str
    original_filename: str
    extension: str
    original_directory: str
    file_size: int
    mtime_ns: int
    media_type: str = "video"
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    rotation: int = 0
    recording_timestamp: str | None = None
    recording_timezone: str | None = None
    timestamp_provenance: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    detailed_place: str | None = None
    title: str | None = None
    camera: str | None = None
    country: str | None = None
    locality: str | None = None
    location_provenance: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Location:
    """A country and parent locality returned by a geographic resolver."""

    country: str
    locality: str
    detailed_place: str | None = None


class Geocoder(Protocol):
    """Interface used to resolve coordinates without coupling to a provider."""

    def resolve(self, latitude: float, longitude: float) -> Location | None:
        """Return a reliable parent locality for coordinates, if available."""


class NullGeocoder:
    """Default resolver that never transmits coordinates."""

    def resolve(self, latitude: float, longitude: float) -> Location | None:
        """Leave GPS coordinates unclassified."""
        return None


class NominatimGeocoder:
    """Opt-in OpenStreetMap Nominatim resolver with SQLite-backed caching."""

    def __init__(self, index: "MetadataIndex", url: str = DEFAULT_GEOCODER_URL):
        """Initialize the resolver with a cache and an http(s) provider endpoint."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"Geocoder URL must be an http or https URL: {url}")
        self.index = index
        self.url = url
        self.provenance = "gps:nominatim"
        self.last_request_at: float | None = None

    def resolve(self, latitude: float, longitude: float) -> Location | None:
        """Resolve coordinates, preferring city, town, or village fields."""
        cached = self.index.get_geocode(latitude, longitude)
        if cached is not None:
            return cached

        query = urllib.parse.urlencode(
            {
                "format": "jsonv2",
                "lat": f"{latitude:.8f}",
                "lon": f"{longitude:.8f}",
                "addressdetails": "1",
                "accept-language": "en",
                "zoom": "13",
            }
        )
        request = urllib.request.Request(
            f"{self.url}?{query}",
            headers={
                "User-Agent": "python-scripts-media-organizer/1.0 "
                "(https://github.com/zlatanstajic/python_scripts)",
                "Accept-Language": "en",
            },
        )
        if self.last_request_at is not None:
            elapsed = time.monotonic() - self.last_request_at
            time.sleep(max(0.0, NOMINATIM_REQUEST_INTERVAL - elapsed))
        self.last_request_at = time.monotonic()
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310
            payload = json.load(response)

        address = payload.get("address", {})
        country = _first_text(address, ("country",))
        locality = _first_text(
            address,
            ("city", "town", "village", "municipality", "hamlet"),
        )
        if not country or not locality:
            return None
        location = Location(country, locality, payload.get("display_name"))
        self.index.put_geocode(latitude, longitude, location)
        return location


class MetadataIndex:
    """Persistent metadata and reverse-geocoding cache."""

    def __init__(self, path: Path):
        """Open a cache database, creating its schema when necessary."""
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS media (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                device INTEGER NOT NULL,
                inode INTEGER NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS geocodes (
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                country TEXT NOT NULL,
                locality TEXT NOT NULL,
                detailed_place TEXT,
                language TEXT NOT NULL DEFAULT 'en',
                PRIMARY KEY (latitude, longitude)
            )
            """
        )
        geocode_columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(geocodes)")
        }
        if "language" not in geocode_columns:
            self.connection.execute(
                "ALTER TABLE geocodes ADD COLUMN language TEXT NOT NULL DEFAULT ''"
            )
        self.connection.commit()

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()

    def get(self, path: Path) -> MediaMetadata | None:
        """Return cached metadata when the file identity matches a current record."""
        stat = path.stat()
        row = self.connection.execute(
            "SELECT size, mtime_ns, device, inode, metadata FROM media WHERE path = ?",
            (str(path),),
        ).fetchone()
        if row is None or row[:4] != (
            stat.st_size,
            stat.st_mtime_ns,
            stat.st_dev,
            stat.st_ino,
        ):
            return None
        record = json.loads(row[4])
        if "rotation" not in record:
            return None  # cached before display rotation was recorded
        return MediaMetadata(**record)

    def put(self, metadata: MediaMetadata) -> None:
        """Insert or replace cached metadata for a source file."""
        source = Path(metadata.path)
        stat = source.stat()
        self.connection.execute(
            """
            INSERT OR REPLACE INTO media
                (path, size, mtime_ns, device, inode, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                metadata.path,
                stat.st_size,
                stat.st_mtime_ns,
                stat.st_dev,
                stat.st_ino,
                json.dumps(asdict(metadata), ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def get_geocode(self, latitude: float, longitude: float) -> Location | None:
        """Return an exactly cached coordinate lookup."""
        row = self.connection.execute(
            """
            SELECT country, locality, detailed_place FROM geocodes
            WHERE latitude = ? AND longitude = ? AND language = 'en'
            """,
            (latitude, longitude),
        ).fetchone()
        return Location(*row) if row else None

    def put_geocode(
        self, latitude: float, longitude: float, location: Location
    ) -> None:
        """Cache an exact coordinate lookup without radius-based merging."""
        self.connection.execute(
            """
            INSERT OR REPLACE INTO geocodes
                (latitude, longitude, country, locality, detailed_place, language)
            VALUES (?, ?, ?, ?, ?, 'en')
            """,
            (
                latitude,
                longitude,
                location.country,
                location.locality,
                location.detailed_place,
            ),
        )
        self.connection.commit()

    def __enter__(self) -> "MetadataIndex":
        """Return the open index for use as a context manager."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Close the index when its context exits."""
        self.close()


def default_index_path() -> Path:
    """Return a cache path outside a typical source media directory."""
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_root / "media-organizer" / "metadata.sqlite3"


def _first_text(values: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    """Return the first non-empty textual value for a sequence of keys."""
    for key in keys:
        value = values.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _run_json(command: Sequence[str]) -> Any:
    """Run a metadata command and decode its JSON output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.SubprocessError as error:
        raise RuntimeError(f"Metadata command failed: {error}") from error
    if result.returncode:
        detail = result.stderr.strip() or "command failed"
        raise RuntimeError(detail)
    return json.loads(result.stdout)


def discover_media(source: Path, excluded: Sequence[Path] = ()) -> list[Path]:
    """Return supported media candidates below source in deterministic order."""
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Input directory does not exist: {source}")
    excluded_paths = [path.expanduser().resolve() for path in excluded]
    discovered: list[Path] = []
    for root, directories, filenames in os.walk(source):
        root_path = Path(root)
        directories[:] = sorted(
            directory
            for directory in directories
            if not directory.startswith(".media-organizer-")
            and not any(
                _is_relative_to((root_path / directory).resolve(), excluded_path)
                for excluded_path in excluded_paths
            )
        )
        for filename in sorted(filenames):
            candidate = (root_path / filename).resolve()
            if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                discovered.append(candidate)
    return discovered


def _parse_timestamp(value: str) -> tuple[str, str | None] | None:
    """Normalize common ISO and ExifTool timestamps without inventing zones."""
    text = value.strip().replace("Z", "+00:00")
    if re.match(r"^\d{4}:\d{2}:\d{2}", text):
        text = text[:4] + "-" + text[5:7] + "-" + text[8:]
    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(?:\.\d+)?"
        r"(?P<zone>Z|[+-]\d{2}:?\d{2})?$",
        text,
    )
    if not match:
        return None
    normalized = f"{match.group(1)}T{match.group(2)}"
    zone = match.group("zone")
    if zone:
        if zone == "Z":
            zone = "+00:00"
        elif len(zone) == 5:
            zone = zone[:3] + ":" + zone[3:]
        normalized += zone
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return normalized, zone


def _parse_iso6709(value: str) -> tuple[float, float] | None:
    """Parse latitude and longitude from an ISO 6709-style QuickTime value."""
    match = re.match(r"^([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)", value)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _as_float(value: Any) -> float | None:
    """Return a finite numeric metadata value when possible."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def extract_metadata(path: Path) -> MediaMetadata:
    """Validate media with FFprobe and combine FFprobe/ExifTool metadata."""
    path = path.resolve()
    extension = path.suffix.lower()
    media_type = "image" if extension in IMAGE_EXTENSIONS else "video"
    stat = path.stat()
    metadata = MediaMetadata(
        path=str(path),
        original_filename=path.name,
        extension=path.suffix,
        original_directory=str(path.parent),
        file_size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        media_type=media_type,
    )
    probe_error: RuntimeError | None = None
    try:
        probe = _run_json(
            (
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            )
        )
    except RuntimeError as error:
        if extension not in HEIF_EXTENSIONS:
            raise
        probe = {}
        probe_error = error
    visual_streams = [
        stream
        for stream in probe.get("streams", [])
        if stream.get("codec_type") == "video"
    ]
    if not visual_streams and extension not in HEIF_EXTENSIONS:
        expected = "decodable image" if media_type == "image" else "video stream"
        raise ValueError(f"FFprobe found no {expected}")

    stream = visual_streams[0] if visual_streams else {}
    format_data = probe.get("format", {})
    if media_type == "video" or len(visual_streams) == 1:
        # FFprobe 7+ lists each tile of a tiled HEIF photo as a separate stream,
        # so a photo with several streams takes its full size from ExifTool.
        metadata.width = _integer_or_none(stream.get("width"))
        metadata.height = _integer_or_none(stream.get("height"))
    if media_type == "video":
        metadata.duration = _as_float(
            format_data.get("duration") or stream.get("duration")
        )
    probe_values: dict[str, Any] = {}
    probe_values.update(format_data.get("tags", {}))
    probe_values.update(stream.get("tags", {}))
    exif_values: dict[str, Any] = {}

    try:
        exif_payload = _run_json(("exiftool", "-j", "-n", str(path)))
        if exif_payload and isinstance(exif_payload[0], dict):
            exif_values.update(exif_payload[0])
    except FileNotFoundError:
        metadata.warnings.append("ExifTool is not installed; metadata may be limited")
    except (RuntimeError, json.JSONDecodeError, IndexError, TypeError) as error:
        metadata.warnings.append(f"ExifTool metadata unavailable: {error}")

    if not visual_streams:
        file_type = str(exif_values.get("FileType", "")).upper()
        exif_width = _integer_or_none(
            _first_text(exif_values, ("ImageWidth", "ExifImageWidth"))
        )
        exif_height = _integer_or_none(
            _first_text(exif_values, ("ImageHeight", "ExifImageHeight"))
        )
        validated_by_exiftool = (
            file_type in {"HEIC", "HEIF"}
            and exif_width is not None
            and exif_width > 0
            and exif_height is not None
            and exif_height > 0
        )
        if not validated_by_exiftool:
            detail = f": {probe_error}" if probe_error is not None else ""
            raise ValueError(
                "FFprobe could not validate HEIC/HEIF and ExifTool did not "
                f"confirm its file type and dimensions{detail}"
            ) from probe_error
        metadata.warnings.append(
            "FFprobe could not parse HEIC/HEIF; validated with ExifTool"
        )

    if exif_values:
        metadata.width = metadata.width or _integer_or_none(
            _first_text(exif_values, ("ImageWidth", "ExifImageWidth"))
        )
        metadata.height = metadata.height or _integer_or_none(
            _first_text(exif_values, ("ImageHeight", "ExifImageHeight"))
        )
    metadata.rotation = _display_rotation(
        stream, exif_values.get("Orientation") if media_type == "image" else None
    )

    combined = {**probe_values, **exif_values}
    _populate_metadata(metadata, combined)
    probe_location = _embedded_location_pair(probe_values)
    exif_location = _embedded_location_pair(exif_values)
    if probe_location and exif_location and probe_location != exif_location:
        metadata.country = None
        metadata.locality = None
        metadata.location_provenance = None
        metadata.warnings.append("Conflicting embedded geographic metadata")
    _apply_filesystem_modified_time(metadata, path)
    return metadata


def _integer_or_none(value: Any) -> int | None:
    """Convert a metadata value to an integer when possible."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _display_rotation(stream: Mapping[str, Any], exif_orientation: Any) -> int:
    """Return the clockwise rotation, in degrees, that media needs for display."""
    for side_data in stream.get("side_data_list", []):
        rotation = _as_float(side_data.get("rotation"))
        if rotation is not None:
            # FFprobe reports the display-matrix rotation counterclockwise.
            return round(-rotation / 90) % 4 * 90
    orientation = _integer_or_none(exif_orientation)
    return EXIF_ORIENTATION_ROTATIONS.get(orientation or 0, 0)


def _embedded_location_pair(values: Mapping[str, Any]) -> tuple[str, str] | None:
    """Return a complete normalized embedded country/locality pair."""
    country = _first_text(values, COUNTRY_KEYS)
    locality = _first_text(values, LOCALITY_KEYS)
    if country and locality:
        return country.casefold(), locality.casefold()
    return None


def _populate_metadata(metadata: MediaMetadata, values: Mapping[str, Any]) -> None:
    """Populate normalized fields from combined tool metadata."""
    for key in TIMESTAMP_KEYS:
        raw_timestamp = values.get(key)
        if raw_timestamp:
            parsed = _parse_timestamp(str(raw_timestamp))
            if parsed:
                metadata.recording_timestamp, metadata.recording_timezone = parsed
                if metadata.recording_timezone is None:
                    separate_zone = _normalize_timezone(
                        _first_text(
                            values,
                            ("OffsetTimeOriginal", "TimeZone", "TimeZoneOffset"),
                        )
                    )
                    if separate_zone:
                        metadata.recording_timestamp += separate_zone
                        metadata.recording_timezone = separate_zone
                metadata.timestamp_provenance = f"embedded:{key}"
                break
    if metadata.recording_timestamp is None:
        metadata.warnings.append("No reliable recording timestamp found")

    latitude = _as_float(_first_text(values, GPS_LATITUDE_KEYS[:1]))
    longitude = _as_float(_first_text(values, GPS_LONGITUDE_KEYS))
    iso_location = _first_text(values, GPS_LATITUDE_KEYS[1:])
    if (latitude is None or longitude is None) and iso_location:
        parsed_coordinates = _parse_iso6709(iso_location)
        if parsed_coordinates:
            latitude, longitude = parsed_coordinates
    if latitude is not None and longitude is not None:
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            metadata.latitude = latitude
            metadata.longitude = longitude
        else:
            metadata.warnings.append("Embedded GPS coordinates are invalid")

    metadata.country = _first_text(values, COUNTRY_KEYS)
    metadata.locality = _first_text(values, LOCALITY_KEYS)
    if metadata.country and metadata.locality:
        metadata.location_provenance = "embedded:geographic-metadata"
    elif metadata.country or metadata.locality:
        metadata.warnings.append("Incomplete embedded geographic metadata")
        metadata.country = None
        metadata.locality = None
    metadata.detailed_place = _first_text(values, ("Location", "SubLocation"))
    metadata.title = _first_text(values, ("Title", "DisplayName", "title"))
    make = _first_text(values, ("Make", "AndroidManufacturer"))
    model = _first_text(
        values, ("Model", "DeviceModelName", "com.apple.quicktime.model")
    )
    metadata.camera = " ".join(value for value in (make, model) if value) or None


def _normalize_timezone(value: str | None) -> str | None:
    """Normalize a standalone UTC offset to ``+HH:MM`` or ``-HH:MM``."""
    if not value:
        return None
    match = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", value.strip())
    if not match:
        return None
    hours, minutes = int(match.group(2)), int(match.group(3))
    if hours > 23 or minutes > 59:
        return None
    return f"{match.group(1)}{hours:02d}:{minutes:02d}"


def _apply_filesystem_modified_time(metadata: MediaMetadata, path: Path) -> None:
    """Use the source file modification time as its effective recording time."""
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime).astimezone()
    timestamp = modified.isoformat(timespec="seconds")
    metadata.mtime_ns = stat.st_mtime_ns
    metadata.recording_timestamp = timestamp
    metadata.recording_timezone = _normalize_timezone(modified.strftime("%z"))
    metadata.timestamp_provenance = "filesystem:mtime"
    metadata.warnings = [
        warning
        for warning in metadata.warnings
        if warning != "No reliable recording timestamp found"
    ]


def load_overrides(path: Path | None) -> dict[str, Any]:
    """Load optional classifications and recognizable place aliases from JSON."""
    if path is None:
        return {"files": {}, "places": {}}
    with path.expanduser().open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Overrides must be a JSON object")
    files = data.get("files", {})
    places = data.get("places", {})
    if not isinstance(files, dict) or not isinstance(places, dict):
        raise ValueError("Overrides 'files' and 'places' values must be objects")
    return {"files": files, "places": places}


def classify_location(
    metadata: MediaMetadata,
    source: Path,
    geocoder: Geocoder,
    overrides: Mapping[str, Any],
) -> None:
    """Classify a media file using the documented conservative priority order."""
    if metadata.latitude is not None and metadata.longitude is not None:
        try:
            resolved = geocoder.resolve(metadata.latitude, metadata.longitude)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            metadata.warnings.append(f"GPS lookup failed: {error}")
        else:
            if resolved:
                metadata.country = resolved.country
                metadata.locality = resolved.locality
                metadata.detailed_place = resolved.detailed_place
                metadata.location_provenance = getattr(
                    geocoder, "provenance", "gps:reverse-geocoded"
                )
                return
            metadata.warnings.append("GPS coordinates were not resolved to a locality")

    if metadata.country and metadata.locality:
        return

    places = overrides.get("places", {})
    searchable = [metadata.title or "", metadata.original_filename]
    try:
        searchable.append(str(Path(metadata.path).relative_to(source)))
    except ValueError:
        searchable.append(metadata.original_directory)
    matches: list[tuple[str, Mapping[str, Any], str]] = []
    for alias, location in places.items():
        if not isinstance(location, dict):
            continue
        for field_number, value in enumerate(searchable):
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", value, re.IGNORECASE):
                provenance = "title" if field_number == 0 else "filename-or-directory"
                matches.append((alias, location, provenance))
                break
    unique = {
        (str(match[1].get("country", "")), str(match[1].get("locality", "")))
        for match in matches
    }
    if len(unique) == 1 and matches:
        country, locality = next(iter(unique))
        if country and locality:
            metadata.country = country
            metadata.locality = locality
            metadata.location_provenance = matches[0][2]
            return
    elif len(unique) > 1:
        metadata.warnings.append("Conflicting recognizable location names")

    files = overrides.get("files", {})
    relative = str(Path(metadata.path).relative_to(source))
    file_override = files.get(relative) or files.get(metadata.path)
    if isinstance(file_override, dict):
        country = str(file_override.get("country", "")).strip()
        locality = str(file_override.get("locality", "")).strip()
        if country and locality:
            metadata.country = country
            metadata.locality = locality
            metadata.location_provenance = "user-override"
            return
    metadata.warnings.append("Location is unclassified")


def scan_library(
    source: Path,
    index: MetadataIndex,
    geocoder: Geocoder,
    overrides: Mapping[str, Any],
    excluded: Sequence[Path] = (),
    progress: ProgressCallback | None = None,
) -> tuple[list[MediaMetadata], list[dict[str, str]]]:
    """Discover media, reuse valid cache records, and classify each file."""
    source = source.expanduser().resolve()
    media_files: list[MediaMetadata] = []
    skipped: list[dict[str, str]] = []
    _emit_progress(progress, f"Scanning recursively: {source}")
    candidates = discover_media(source, excluded)
    total = len(candidates)
    _emit_progress(progress, f"Discovered {total} media candidate(s).")
    for position, path in enumerate(candidates, start=1):
        prefix = f"[{position}/{total}]"
        try:
            _emit_progress(progress, f"{prefix} Checking metadata cache: {path}")
            metadata = index.get(path)
            if metadata is None:
                _emit_progress(progress, f"{prefix} Extracting metadata: {path}")
                metadata = extract_metadata(path)
                index.put(metadata)
            else:
                _emit_progress(progress, f"{prefix} Using cached metadata: {path}")
                if metadata.timestamp_provenance != "filesystem:mtime":
                    _apply_filesystem_modified_time(metadata, path)
                    index.put(metadata)
            _emit_progress(progress, f"{prefix} Classifying date and location")
            classify_location(metadata, source, geocoder, overrides)
            _normalize_metadata_location(metadata)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
            skipped.append({"path": str(path), "reason": str(error)})
            _emit_progress(progress, f"{prefix} Skipped: {error}")
            continue
        media_files.append(metadata)
        _emit_progress(progress, f"{prefix} Metadata ready")
    return media_files, skipped


def _emit_progress(progress: ProgressCallback | None, message: str) -> None:
    """Send a progress message when verbose reporting is enabled."""
    if progress is not None:
        progress(message)


def _prefixed_progress(progress: ProgressCallback, prefix: str) -> ProgressCallback:
    """Return a callback that prefixes every progress message."""

    def report(message: str) -> None:
        progress(f"{prefix} {message}")

    return report


def _percentage_progress(progress: ProgressCallback, label: str) -> PercentageCallback:
    """Return a percentage callback writing through a text progress callback."""

    def report(percentage: int) -> None:
        progress(f"{label}: {percentage}%")

    return report


def sanitize_component(value: str, fallback: str = "Unclassified") -> str:
    """Return an ASCII alphanumeric component with hyphen separators."""
    transliterated = value.translate(TRANSLITERATION)
    transliterated = unicodedata.normalize("NFKD", transliterated)
    transliterated = transliterated.translate(TRANSLITERATION)
    ascii_value = transliterated.encode("ascii", "ignore").decode("ascii")
    component = NON_ALPHANUMERIC.sub("-", ascii_value).strip("-")
    return component[:180].rstrip("-") or fallback


def source_folder_title(source: Path) -> str:
    """Return a filename-safe title derived from the source folder name."""
    match = re.match(r"^\d{4}-\d{2}\s*-\s*(.+)$", source.name)
    description = match.group(1) if match else source.name
    return sanitize_component(description, "Source").replace("-", "_")


def _english_alias_key(value: str) -> str:
    """Return the normalized lookup key used by English location aliases."""
    return sanitize_component(value, "").casefold()


def english_country_name(value: str) -> str:
    """Return a known English country name, preserving unknown source text."""
    return COUNTRY_ENGLISH_ALIASES.get(_english_alias_key(value), value)


def english_locality_name(value: str) -> str:
    """Return a known English locality name, preserving unknown source text."""
    return LOCALITY_ENGLISH_ALIASES.get(_english_alias_key(value), value)


def _normalize_metadata_location(metadata: MediaMetadata) -> None:
    """Canonicalize classified country and locality values to known English names."""
    if metadata.country:
        metadata.country = english_country_name(metadata.country)
    if metadata.locality:
        metadata.locality = english_locality_name(metadata.locality)


def _timestamp_filename(metadata: MediaMetadata) -> str | None:
    """Return the sortable timestamp part of a filename when verified."""
    if not metadata.recording_timestamp:
        return None
    return datetime.fromisoformat(metadata.recording_timestamp).strftime(
        "%Y-%m-%d_%H-%M-%S"
    )


def sha256_file(path: Path, progress: PercentageCallback | None = None) -> str:
    """Return a streaming SHA-256 digest for a file."""
    digest = hashlib.sha256()
    total = path.stat().st_size if progress is not None else 0
    transferred = 0
    last_reported = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(COPY_CHUNK_SIZE), b""):
            digest.update(chunk)
            transferred += len(chunk)
            last_reported = _report_percentage(
                progress, transferred, total, last_reported
            )
    if progress is not None and total == 0:
        progress(100)
    return digest.hexdigest()


def _report_percentage(
    progress: PercentageCallback | None,
    transferred: int,
    total: int,
    last_reported: int,
) -> int:
    """Report transfer progress in ten-percent increments."""
    if progress is None or total <= 0:
        return last_reported
    percentage = min(100, int(transferred * 100 / total))
    if percentage == 100 or percentage >= last_reported + 10:
        progress(percentage)
        return percentage
    return last_reported


def validate_separate_trees(source: Path, output: Path) -> tuple[Path, Path]:
    """Reject identical, nested, or enclosing source/output directory trees."""
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if (
        source == output
        or _is_relative_to(source, output)
        or _is_relative_to(output, source)
    ):
        raise ValueError("Input and output directory trees must not overlap")
    return source, output


def _is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is inside parent (Python 3.8-compatible helper)."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def build_plan(
    source: Path,
    output: Path,
    media_files: Sequence[MediaMetadata],
    skipped: Sequence[Mapping[str, str]],
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Build a deterministic, hash-bound organization manifest."""
    source, output = validate_separate_trees(source, output)
    used: set[Path] = set()
    entries: list[dict[str, Any]] = []
    sorted_media = sorted(media_files, key=lambda item: item.path)
    has_classified_locations = any(
        item.country and item.locality for item in sorted_media
    )
    total = len(sorted_media)
    _emit_progress(progress, f"Building plan for {total} media file(s).")
    for position, metadata in enumerate(sorted_media, start=1):
        prefix = f"[{position}/{total}]"
        country = english_country_name(metadata.country) if metadata.country else None
        locality = (
            english_locality_name(metadata.locality) if metadata.locality else None
        )
        hash_progress: PercentageCallback | None = None
        if progress is not None:
            hash_progress = _percentage_progress(progress, f"{prefix} Hashing source")
        source_hash = sha256_file(Path(metadata.path), hash_progress)
        _emit_progress(progress, f"{prefix} Selecting destination: {metadata.path}")
        timestamp = _timestamp_filename(metadata)
        if timestamp:
            year = timestamp[:4]
            if country and locality:
                directory = (
                    output
                    / year
                    / sanitize_component(country, "Unknown-Country")
                    / sanitize_component(locality, "Unknown-Locality")
                )
                fragment = sanitize_component(locality, "Unknown-Locality")
            elif not has_classified_locations:
                directory = output / year
                fragment = source_folder_title(Path(metadata.path).parent)
            else:
                directory = output / year / "Unclassified"
                fragment = "Unclassified"
            base_name = f"{timestamp}_{fragment}{metadata.extension}"
        else:
            directory = output / "Unclassified" / "Unknown-Year"
            base_name = f"Undated_{source_hash[:12]}{metadata.extension}"

        destination = _unique_destination(
            directory,
            base_name,
            Path(metadata.path),
            used,
        )
        used.add(destination)
        entries.append(
            {
                "source": metadata.path,
                "media_type": metadata.media_type,
                "destination": str(destination),
                "original_filename": metadata.original_filename,
                "generated_filename": destination.name,
                "file_size": metadata.file_size,
                "source_mtime_ns": metadata.mtime_ns,
                "sha256": source_hash,
                "recording_timestamp": metadata.recording_timestamp,
                "recording_timezone": metadata.recording_timezone,
                "timestamp_provenance": metadata.timestamp_provenance,
                "country": country,
                "locality": locality,
                "location_provenance": metadata.location_provenance,
                "gps": (
                    {"latitude": metadata.latitude, "longitude": metadata.longitude}
                    if metadata.latitude is not None and metadata.longitude is not None
                    else None
                ),
                "detailed_place": metadata.detailed_place,
                "title": metadata.title,
                "camera": metadata.camera,
                "duration": metadata.duration,
                "resolution": (
                    f"{metadata.width}x{metadata.height}"
                    if metadata.width and metadata.height
                    else None
                ),
                "warnings": metadata.warnings,
                "status": "planned",
            }
        )
        _emit_progress(progress, f"{prefix} Planned: {destination}")
    classified = sum(bool(entry["country"] and entry["locality"]) for entry in entries)
    images = sum(entry["media_type"] == "image" for entry in entries)
    videos = len(entries) - images
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_directory": str(source),
        "output_directory": str(output),
        "summary": {
            "total_files": len(entries),
            "videos": videos,
            "images": images,
            "classified": classified,
            "unclassified": len(entries) - classified,
            "skipped": len(skipped),
        },
        "entries": entries,
        "skipped": list(skipped),
    }


def _unique_destination(
    directory: Path, filename: str, source: Path, used: set[Path]
) -> Path:
    """Choose a deterministic non-conflicting destination path."""
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = (directory / filename).resolve()
    counter = 2
    while candidate in used or (
        candidate.exists() and not _files_identical(source, candidate)
    ):
        candidate = (directory / f"{stem}_{counter:03d}{suffix}").resolve()
        counter += 1
    return candidate


def _files_identical(first: Path, second: Path) -> bool:
    """Return whether two files have equal sizes and SHA-256 digests."""
    try:
        return first.stat().st_size == second.stat().st_size and sha256_file(
            first
        ) == sha256_file(second)
    except OSError:
        return False


def write_plan(plan: dict[str, Any], database_path: Path, markdown_path: Path) -> None:
    """Atomically write a SQLite plan and its human-readable Markdown report."""
    source = Path(plan["source_directory"]).resolve()
    database_path = database_path.expanduser().resolve()
    markdown_path = markdown_path.expanduser().resolve()
    if database_path == markdown_path:
        raise ValueError("SQLite plan and Markdown report paths must be different")
    if _is_relative_to(database_path, source) or _is_relative_to(markdown_path, source):
        raise ValueError("Organization reports must be outside the input directory")
    plan["plan_file"] = str(database_path)
    plan["report_file"] = str(markdown_path)
    _atomic_sqlite_write(
        database_path, lambda connection: _store_plan(connection, plan)
    )
    _write_plan_markdown(plan, markdown_path)


def _store_plan(connection: sqlite3.Connection, plan: Mapping[str, Any]) -> None:
    """Create the normalized plan schema and insert one organization plan."""
    connection.executescript(
        """
        CREATE TABLE organization_plan (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            schema_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            source_directory TEXT NOT NULL,
            output_directory TEXT NOT NULL,
            report_file TEXT,
            total_files INTEGER NOT NULL,
            videos INTEGER NOT NULL,
            images INTEGER NOT NULL,
            classified INTEGER NOT NULL,
            unclassified INTEGER NOT NULL,
            skipped INTEGER NOT NULL
        );
        CREATE TABLE plan_entries (
            position INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            media_type TEXT NOT NULL,
            destination TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            generated_filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            source_mtime_ns INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            recording_timestamp TEXT,
            recording_timezone TEXT,
            timestamp_provenance TEXT,
            country TEXT,
            locality TEXT,
            location_provenance TEXT,
            latitude REAL,
            longitude REAL,
            detailed_place TEXT,
            title TEXT,
            camera TEXT,
            duration REAL,
            resolution TEXT,
            status TEXT NOT NULL,
            error TEXT
        );
        CREATE TABLE plan_entry_warnings (
            entry_position INTEGER NOT NULL,
            position INTEGER NOT NULL,
            warning TEXT NOT NULL,
            PRIMARY KEY (entry_position, position),
            FOREIGN KEY (entry_position) REFERENCES plan_entries(position)
                ON DELETE CASCADE
        );
        CREATE TABLE plan_skipped (
            position INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            reason TEXT NOT NULL
        );
        """
    )
    summary = plan["summary"]
    total_files = summary.get("total_files", summary.get("total_videos", 0))
    connection.execute(
        """
        INSERT INTO organization_plan VALUES
            (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plan["schema_version"],
            plan["created_at"],
            plan["source_directory"],
            plan["output_directory"],
            plan.get("report_file"),
            total_files,
            summary.get("videos", total_files),
            summary.get("images", 0),
            summary["classified"],
            summary["unclassified"],
            summary["skipped"],
        ),
    )
    for position, entry in enumerate(plan["entries"], start=1):
        gps = entry.get("gps") or {}
        connection.execute(
            """
            INSERT INTO plan_entries VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                position,
                entry["source"],
                entry["media_type"],
                entry["destination"],
                entry["original_filename"],
                entry["generated_filename"],
                entry["file_size"],
                entry["source_mtime_ns"],
                entry["sha256"],
                entry.get("recording_timestamp"),
                entry.get("recording_timezone"),
                entry.get("timestamp_provenance"),
                entry.get("country"),
                entry.get("locality"),
                entry.get("location_provenance"),
                gps.get("latitude"),
                gps.get("longitude"),
                entry.get("detailed_place"),
                entry.get("title"),
                entry.get("camera"),
                entry.get("duration"),
                entry.get("resolution"),
                entry.get("status", "planned"),
                entry.get("error"),
            ),
        )
        connection.executemany(
            "INSERT INTO plan_entry_warnings VALUES (?, ?, ?)",
            [
                (position, warning_position, warning)
                for warning_position, warning in enumerate(
                    entry.get("warnings", []), start=1
                )
            ],
        )
    connection.executemany(
        "INSERT INTO plan_skipped VALUES (?, ?, ?)",
        [
            (position, item["path"], item["reason"])
            for position, item in enumerate(plan["skipped"], start=1)
        ],
    )


def _write_plan_markdown(plan: Mapping[str, Any], path: Path) -> None:
    """Write the human-readable view of an organization plan."""
    summary = plan["summary"]
    total_files = summary.get("total_files", summary.get("total_videos", 0))
    video_files = summary.get("videos", total_files)
    image_files = summary.get("images", 0)
    lines = [
        "# Media organization plan",
        "",
        f"- Source: `{plan['source_directory']}`",
        f"- Destination: `{plan['output_directory']}`",
        f"- Total files: {total_files}",
        f"- Videos: {video_files}",
        f"- Images: {image_files}",
        f"- Classified: {summary['classified']}",
        f"- Unclassified: {summary['unclassified']}",
        f"- Skipped: {summary['skipped']}",
        "",
    ]
    if any(
        entry.get("location_provenance") == "gps:nominatim" for entry in plan["entries"]
    ):
        lines.extend([f"- Geocoding attribution: {NOMINATIM_ATTRIBUTION}", ""])
    lines.extend(["## Proposed copies", ""])
    for entry in plan["entries"]:
        location = (
            ", ".join(value for value in (entry["locality"], entry["country"]) if value)
            or "Unclassified"
        )
        lines.extend(
            [
                f"### {entry['original_filename']}",
                "",
                f"- Original: `{entry['source']}`",
                f"- Destination: `{entry['destination']}`",
                f"- Recording time: {entry['recording_timestamp'] or 'Unknown'}",
                f"- Timestamp provenance: {entry['timestamp_provenance'] or 'None'}",
                f"- Location: {location}",
                f"- Location provenance: {entry['location_provenance'] or 'None'}",
                f"- Warnings: {', '.join(entry['warnings']) or 'None'}",
                f"- Status: {entry.get('status', 'planned')}",
                *([f"- Error: {entry['error']}"] if entry.get("error") else []),
                "",
            ]
        )
    if plan["skipped"]:
        lines.extend(["## Skipped files", ""])
        for item in plan["skipped"]:
            lines.append(f"- `{item['path']}` — {item['reason']}")
        lines.append("")
    _atomic_text_write(path, "\n".join(lines))


def _atomic_sqlite_write(
    path: Path, populate: Callable[[sqlite3.Connection], None]
) -> None:
    """Build a SQLite database beside its destination and atomically replace it."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            populate(connection)
            connection.commit()
        finally:
            connection.close()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    """Write JSON through a temporary sibling and atomically replace the target."""
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    _atomic_text_write(path, text)


def _atomic_text_write(path: Path, content: str) -> None:
    """Write text through a temporary sibling and atomically replace the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_plan(path: Path) -> dict[str, Any]:
    """Load and minimally validate a versioned organization plan."""
    path = path.expanduser().resolve()
    with path.open("rb") as handle:
        is_sqlite = handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER
    if is_sqlite:
        plan = _load_sqlite_plan(path)
    else:
        with path.open(encoding="utf-8") as handle:
            plan = cast(dict[str, Any], json.load(handle))
    if plan.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError("Unsupported organization plan schema version")
    if not isinstance(plan.get("entries"), list):
        raise ValueError("Organization plan has no valid entries list")
    validate_separate_trees(
        Path(plan["source_directory"]), Path(plan["output_directory"])
    )
    return plan


def _load_sqlite_plan(path: Path) -> dict[str, Any]:
    """Load an organization plan from its normalized SQLite tables."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        plan_row = connection.execute(
            "SELECT * FROM organization_plan WHERE id = 1"
        ).fetchone()
        if plan_row is None:
            raise ValueError("SQLite organization plan has no plan record")
        entries: list[dict[str, Any]] = []
        for row in connection.execute("SELECT * FROM plan_entries ORDER BY position"):
            warnings = [
                warning_row[0]
                for warning_row in connection.execute(
                    """
                    SELECT warning FROM plan_entry_warnings
                    WHERE entry_position = ? ORDER BY position
                    """,
                    (row["position"],),
                )
            ]
            latitude, longitude = row["latitude"], row["longitude"]
            entries.append(
                {
                    "source": row["source"],
                    "media_type": row["media_type"],
                    "destination": row["destination"],
                    "original_filename": row["original_filename"],
                    "generated_filename": row["generated_filename"],
                    "file_size": row["file_size"],
                    "source_mtime_ns": row["source_mtime_ns"],
                    "sha256": row["sha256"],
                    "recording_timestamp": row["recording_timestamp"],
                    "recording_timezone": row["recording_timezone"],
                    "timestamp_provenance": row["timestamp_provenance"],
                    "country": row["country"],
                    "locality": row["locality"],
                    "location_provenance": row["location_provenance"],
                    "gps": (
                        {"latitude": latitude, "longitude": longitude}
                        if latitude is not None and longitude is not None
                        else None
                    ),
                    "detailed_place": row["detailed_place"],
                    "title": row["title"],
                    "camera": row["camera"],
                    "duration": row["duration"],
                    "resolution": row["resolution"],
                    "warnings": warnings,
                    "status": row["status"],
                    **({"error": row["error"]} if row["error"] else {}),
                }
            )
        skipped = [
            {"path": row["path"], "reason": row["reason"]}
            for row in connection.execute(
                "SELECT path, reason FROM plan_skipped ORDER BY position"
            )
        ]
        return {
            "schema_version": plan_row["schema_version"],
            "created_at": plan_row["created_at"],
            "source_directory": plan_row["source_directory"],
            "output_directory": plan_row["output_directory"],
            "plan_file": str(path),
            "report_file": plan_row["report_file"],
            "summary": {
                "total_files": plan_row["total_files"],
                "videos": plan_row["videos"],
                "images": plan_row["images"],
                "classified": plan_row["classified"],
                "unclassified": plan_row["unclassified"],
                "skipped": plan_row["skipped"],
            },
            "entries": entries,
            "skipped": skipped,
        }
    finally:
        connection.close()


def _is_sqlite_database(path: Path) -> bool:
    """Return whether path starts with the SQLite file signature."""
    with path.open("rb") as handle:
        return handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER


def _save_plan_status(plan_path: Path, plan: Mapping[str, Any], position: int) -> None:
    """Persist one entry status to SQLite or a legacy JSON plan."""
    if not _is_sqlite_database(plan_path):
        _atomic_json_write(plan_path, plan)
        return
    entry = plan["entries"][position - 1]
    connection = sqlite3.connect(plan_path)
    try:
        connection.execute(
            """
            UPDATE plan_entries SET status = ?, error = ?
            WHERE position = ?
            """,
            (entry["status"], entry.get("error"), position),
        )
        connection.commit()
    finally:
        connection.close()


def apply_plan(
    plan_path: Path, progress: ProgressCallback | None = None
) -> tuple[int, int, int]:
    """Copy, hash-verify, and finalize every safe entry in an approved plan."""
    plan_path = plan_path.expanduser().resolve()
    _emit_progress(progress, f"Loading approved plan: {plan_path}")
    plan = load_plan(plan_path)
    source_root = Path(plan["source_directory"]).resolve()
    output_root = Path(plan["output_directory"]).resolve()
    if _is_relative_to(plan_path, source_root):
        raise ValueError("The mutable plan file must be outside the source directory")
    output_root.mkdir(parents=True, exist_ok=True)
    _emit_progress(progress, "Checking existing outputs and required disk space")
    pending_size = sum(
        int(entry["file_size"])
        for entry in plan["entries"]
        if _entry_needs_space(entry, output_root)
    )
    if shutil.disk_usage(output_root).free < pending_size:
        raise OSError("Insufficient free space for all pending plan entries")

    copied = already = failed = 0
    total = len(plan["entries"])
    for position, entry in enumerate(plan["entries"], start=1):
        prefix = f"[{position}/{total}]"
        source = entry.get("source", "unknown source")
        _emit_progress(progress, f"{prefix} Processing: {source}")
        entry_progress: ProgressCallback | None = None
        if progress is not None:
            entry_progress = _prefixed_progress(progress, prefix)
        try:
            outcome = _apply_entry(
                entry, source_root, output_root, progress=entry_progress
            )
        except (OSError, ValueError) as error:
            entry["status"] = "failed"
            entry["error"] = str(error)
            failed += 1
            _emit_progress(progress, f"{prefix} Failed: {error}")
        else:
            entry["status"] = outcome
            entry.pop("error", None)
            if outcome == "copied":
                copied += 1
            else:
                already += 1
            _emit_progress(progress, f"{prefix} Completed: {outcome}")
        _save_plan_status(plan_path, plan, position)
        _emit_progress(progress, f"{prefix} Saved operation status")
    if failed == 0:
        _emit_progress(progress, "All entries succeeded; removing plan artifacts")
        _remove_completed_plan_files(plan_path, plan, source_root)
    elif plan.get("report_file"):
        _write_plan_markdown(plan, Path(str(plan["report_file"])))
    return copied, already, failed


def _remove_completed_plan_files(
    plan_path: Path, plan: Mapping[str, Any], source_root: Path
) -> None:
    """Remove completed plan artifacts while protecting the source tree."""
    report_value = plan.get("report_file")
    if report_value:
        report_path = Path(str(report_value)).expanduser().resolve()
        if _is_relative_to(report_path, source_root):
            raise ValueError("Plan report file points inside the source directory")
        if report_path != plan_path:
            report_path.unlink(missing_ok=True)
    plan_path.unlink(missing_ok=True)


def _entry_needs_space(entry: Mapping[str, Any], output_root: Path) -> bool:
    """Return whether an entry does not already have a matching safe output."""
    try:
        destination = Path(str(entry["destination"])).resolve()
        return not (
            _is_relative_to(destination, output_root)
            and destination.is_file()
            and _matches_entry(destination, entry)
        )
    except (KeyError, OSError, TypeError, ValueError):
        return True


def _apply_entry(
    entry: dict[str, Any],
    source_root: Path,
    output_root: Path,
    progress: ProgressCallback | None = None,
) -> str:
    """Safely apply one manifest entry and return its completed status."""
    source = Path(entry["source"]).resolve()
    destination = Path(entry["destination"]).resolve()
    if not _is_relative_to(source, source_root):
        raise ValueError("Plan source escapes the declared source directory")
    if not _is_relative_to(destination, output_root):
        raise ValueError("Plan destination escapes the declared output directory")
    stat_before = source.stat()
    if stat_before.st_size != int(entry["file_size"]):
        raise ValueError("Source size changed after planning")
    if stat_before.st_mtime_ns != int(entry["source_mtime_ns"]):
        raise ValueError("Source timestamp changed after planning")
    _emit_progress(progress, "Validating source hash")
    source_hash = sha256_file(
        source,
        _percentage_progress(progress, "Source hash") if progress is not None else None,
    )
    if source_hash != entry["sha256"]:
        raise ValueError("Source content changed after planning")

    if destination.exists():
        _emit_progress(progress, "Verifying existing destination")
        if destination.is_file() and _matches_entry(
            destination,
            entry,
            (
                _percentage_progress(progress, "Existing file hash")
                if progress is not None
                else None
            ),
        ):
            return "already-organized"
        raise FileExistsError(f"Destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".media-organizer-", suffix=".part", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with (
            source.open("rb") as input_handle,
            os.fdopen(descriptor, "wb") as output_handle,
        ):
            _emit_progress(progress, f"Copying to temporary file: {temporary}")
            _copy_with_progress(
                input_handle,
                output_handle,
                int(entry["file_size"]),
                (
                    _percentage_progress(progress, "Copy")
                    if progress is not None
                    else None
                ),
            )
            output_handle.flush()
            os.fsync(output_handle.fileno())
        _emit_progress(progress, "Verifying temporary copy")
        if not _matches_entry(
            temporary,
            entry,
            (
                _percentage_progress(progress, "Temporary file hash")
                if progress is not None
                else None
            ),
        ):
            raise OSError("Copied file failed size or SHA-256 verification")
        _emit_progress(progress, f"Finalizing destination: {destination}")
        try:
            os.link(temporary, destination)
        except (AttributeError, NotImplementedError):  # pragma: no cover
            _exclusive_finalize(temporary, destination)
        temporary.unlink()
        _emit_progress(progress, "Verifying finalized destination")
        if not _matches_entry(
            destination,
            entry,
            (
                _percentage_progress(progress, "Final file hash")
                if progress is not None
                else None
            ),
        ):
            raise OSError("Finalized file failed size or SHA-256 verification")
        if source.stat().st_mtime_ns != stat_before.st_mtime_ns:
            raise OSError("Source changed while it was being copied")
        return "copied"
    finally:
        temporary.unlink(missing_ok=True)


def _copy_with_progress(
    input_handle: BinaryIO,
    output_handle: BinaryIO,
    total: int,
    progress: PercentageCallback | None = None,
) -> None:
    """Copy bytes while optionally reporting ten-percent increments."""
    transferred = 0
    last_reported = 0
    while True:
        chunk = input_handle.read(COPY_CHUNK_SIZE)
        if not chunk:
            break
        output_handle.write(chunk)
        transferred += len(chunk)
        last_reported = _report_percentage(progress, transferred, total, last_reported)
    if progress is not None and total == 0:
        progress(100)


def _exclusive_finalize(temporary: Path, destination: Path) -> None:
    """Finalize without overwriting on platforms where hard links are unavailable."""
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        os.replace(temporary, destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _matches_entry(
    path: Path,
    entry: Mapping[str, Any],
    progress: PercentageCallback | None = None,
) -> bool:
    """Return whether a file matches the plan's size and digest."""
    return (
        path.stat().st_size == int(entry["file_size"])
        and sha256_file(path, progress) == entry["sha256"]
    )


def display_size(metadata: MediaMetadata) -> tuple[int, int] | None:
    """Return the width and height as displayed, after any quarter-turn rotation."""
    if not metadata.width or not metadata.height:
        return None
    if metadata.rotation in (90, 270):
        return metadata.height, metadata.width
    return metadata.width, metadata.height


def orientation_label(size: tuple[int, int] | None) -> str:
    """Name the orientation of a displayed width and height."""
    if size is None:
        return "unknown"
    width, height = size
    if width == height:
        return "square"
    return "landscape" if width > height else "portrait"


def organized_location(path: Path) -> Location | None:
    """Return the country and locality recorded by an organized copy's path."""
    match = ORGANIZED_PATH.fullmatch("/".join(path.parts[-4:]))
    if match is None or "Unclassified" in match.group("country", "locality"):
        return None
    return Location(match.group("country"), match.group("locality"))


def build_report(
    directory: Path,
    media_files: Sequence[MediaMetadata],
    skipped: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Count the media types, formats, orientations, and locations in a directory."""
    entries: list[dict[str, Any]] = []
    formats: dict[str, Counter[str]] = {"image": Counter(), "video": Counter()}
    orientations: dict[str, Counter[str]] = {"image": Counter(), "video": Counter()}
    locations: dict[str, Counter[str]] = {}
    for metadata in sorted(media_files, key=lambda item: item.path):
        country, locality = metadata.country, metadata.locality
        provenance = metadata.location_provenance
        organized = organized_location(Path(metadata.path))
        if organized is not None:
            country, locality = organized.country, organized.locality
            provenance = "organized:path"
        size = display_size(metadata)
        media_format = metadata.extension.lstrip(".").upper()
        media_orientation = orientation_label(size)
        formats[metadata.media_type][media_format] += 1
        orientations[metadata.media_type][media_orientation] += 1
        if country and locality:
            locations.setdefault(country, Counter())[locality] += 1
        entries.append(
            {
                "path": metadata.path,
                "media_type": metadata.media_type,
                "format": media_format,
                "file_size": metadata.file_size,
                "resolution": f"{size[0]}x{size[1]}" if size else None,
                "orientation": media_orientation,
                "duration": metadata.duration,
                "country": country,
                "locality": locality,
                "location_provenance": provenance,
            }
        )
    classified = sum(bool(entry["country"] and entry["locality"]) for entry in entries)
    images = sum(entry["media_type"] == "image" for entry in entries)
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "directory": str(directory.expanduser().resolve()),
        "summary": {
            "total_files": len(entries),
            "images": images,
            "videos": len(entries) - images,
            "classified": classified,
            "unclassified": len(entries) - classified,
            "countries": len(locations),
            "localities": sum(len(counts) for counts in locations.values()),
            "skipped": len(skipped),
        },
        "formats": {
            kind: dict(sorted(counts.items())) for kind, counts in formats.items()
        },
        "orientations": {
            kind: dict(sorted(counts.items())) for kind, counts in orientations.items()
        },
        "locations": {
            country: dict(sorted(locations[country].items()))
            for country in sorted(locations)
        },
        "entries": entries,
        "skipped": list(skipped),
    }
    if any(entry["location_provenance"] == "gps:nominatim" for entry in entries):
        report["geocoding_attribution"] = NOMINATIM_ATTRIBUTION
    return report


def write_report(report: Mapping[str, Any], path: Path) -> None:
    """Atomically store a media inventory in a normalized SQLite database."""
    _atomic_sqlite_write(path, lambda connection: _store_report(connection, report))


def _store_report(connection: sqlite3.Connection, report: Mapping[str, Any]) -> None:
    """Create the report schema and insert one media inventory."""
    connection.executescript(
        """
        CREATE TABLE media_report (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            schema_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            directory TEXT NOT NULL,
            total_files INTEGER NOT NULL,
            images INTEGER NOT NULL,
            videos INTEGER NOT NULL,
            classified INTEGER NOT NULL,
            unclassified INTEGER NOT NULL,
            countries INTEGER NOT NULL,
            localities INTEGER NOT NULL,
            skipped INTEGER NOT NULL,
            geocoding_attribution TEXT
        );
        CREATE TABLE report_entries (
            position INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            media_type TEXT NOT NULL,
            format TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            resolution TEXT,
            orientation TEXT NOT NULL,
            duration REAL,
            country TEXT,
            locality TEXT,
            location_provenance TEXT
        );
        CREATE TABLE report_formats (
            media_type TEXT NOT NULL,
            format TEXT NOT NULL,
            file_count INTEGER NOT NULL,
            PRIMARY KEY (media_type, format)
        );
        CREATE TABLE report_orientations (
            media_type TEXT NOT NULL,
            orientation TEXT NOT NULL,
            file_count INTEGER NOT NULL,
            PRIMARY KEY (media_type, orientation)
        );
        CREATE TABLE report_locations (
            country TEXT NOT NULL,
            locality TEXT NOT NULL,
            file_count INTEGER NOT NULL,
            PRIMARY KEY (country, locality)
        );
        CREATE TABLE report_skipped (
            position INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            reason TEXT NOT NULL
        );
        """
    )
    summary = report["summary"]
    connection.execute(
        """
        INSERT INTO media_report VALUES
            (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report["schema_version"],
            report["created_at"],
            report["directory"],
            summary["total_files"],
            summary["images"],
            summary["videos"],
            summary["classified"],
            summary["unclassified"],
            summary["countries"],
            summary["localities"],
            summary["skipped"],
            report.get("geocoding_attribution"),
        ),
    )
    connection.executemany(
        """
        INSERT INTO report_entries VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                position,
                entry["path"],
                entry["media_type"],
                entry["format"],
                entry["file_size"],
                entry["resolution"],
                entry["orientation"],
                entry["duration"],
                entry["country"],
                entry["locality"],
                entry["location_provenance"],
            )
            for position, entry in enumerate(report["entries"], start=1)
        ],
    )
    connection.executemany(
        "INSERT INTO report_formats VALUES (?, ?, ?)",
        [
            (media_type, media_format, count)
            for media_type, formats in report["formats"].items()
            for media_format, count in formats.items()
        ],
    )
    connection.executemany(
        "INSERT INTO report_orientations VALUES (?, ?, ?)",
        [
            (media_type, orientation, count)
            for media_type, orientations in report["orientations"].items()
            for orientation, count in orientations.items()
        ],
    )
    connection.executemany(
        "INSERT INTO report_locations VALUES (?, ?, ?)",
        [
            (country, locality, count)
            for country, localities in report["locations"].items()
            for locality, count in localities.items()
        ],
    )
    connection.executemany(
        "INSERT INTO report_skipped VALUES (?, ?, ?)",
        [
            (position, item["path"], item["reason"])
            for position, item in enumerate(report["skipped"], start=1)
        ],
    )


def load_report(path: Path) -> dict[str, Any]:
    """Load a media inventory from its normalized SQLite database."""
    path = path.expanduser().resolve()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute("SELECT * FROM media_report WHERE id = 1").fetchone()
        if row is None:
            raise ValueError("SQLite media report has no report record")
        report: dict[str, Any] = {
            "schema_version": row["schema_version"],
            "created_at": row["created_at"],
            "directory": row["directory"],
            "summary": {
                key: row[key]
                for key in (
                    "total_files",
                    "images",
                    "videos",
                    "classified",
                    "unclassified",
                    "countries",
                    "localities",
                    "skipped",
                )
            },
            "formats": {"image": {}, "video": {}},
            "orientations": {"image": {}, "video": {}},
            "locations": {},
            "entries": [
                {
                    key: entry[key]
                    for key in (
                        "path",
                        "media_type",
                        "format",
                        "file_size",
                        "resolution",
                        "orientation",
                        "duration",
                        "country",
                        "locality",
                        "location_provenance",
                    )
                }
                for entry in connection.execute(
                    "SELECT * FROM report_entries ORDER BY position"
                )
            ],
            "skipped": [
                {"path": skipped["path"], "reason": skipped["reason"]}
                for skipped in connection.execute(
                    "SELECT * FROM report_skipped ORDER BY position"
                )
            ],
        }
        for item in connection.execute(
            "SELECT * FROM report_formats ORDER BY media_type, format"
        ):
            report["formats"][item["media_type"]][item["format"]] = item["file_count"]
        for item in connection.execute(
            """
            SELECT * FROM report_orientations
            ORDER BY media_type, orientation
            """
        ):
            report["orientations"][item["media_type"]][item["orientation"]] = item[
                "file_count"
            ]
        for item in connection.execute(
            "SELECT * FROM report_locations ORDER BY country, locality"
        ):
            report["locations"].setdefault(item["country"], {})[item["locality"]] = (
                item["file_count"]
            )
        if row["geocoding_attribution"]:
            report["geocoding_attribution"] = row["geocoding_attribution"]
        return report
    finally:
        connection.close()


def _add_scan_options(parser: argparse.ArgumentParser) -> None:
    """Add the metadata and classification options shared by media scans."""
    parser.add_argument("--overrides", type=Path, help="optional classification JSON")
    parser.add_argument(
        "--index",
        type=Path,
        default=default_index_path(),
        help="SQLite metadata cache (default: %(default)s)",
    )
    parser.add_argument(
        "--allow-network-geocoding",
        action="store_true",
        help="send GPS coordinates to OpenStreetMap Nominatim",
    )
    parser.add_argument(
        "--geocoder-url",
        default=DEFAULT_GEOCODER_URL,
        help="http(s) reverse-geocoding endpoint (default: %(default)s)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="show detailed progress",
    )


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the scan, plan, apply, and report command-line interface."""
    parser = argparse.ArgumentParser(
        description="Organize photos and videos by year and parent locality without "
        "changing the source library."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    scan_parser = commands.add_parser("scan", help="inspect media without copying")
    scan_parser.add_argument(
        "--input", required=True, type=Path, help="source directory"
    )
    _add_scan_options(scan_parser)
    plan_parser = commands.add_parser("plan", help="write organization manifests")
    plan_parser.add_argument(
        "--input", required=True, type=Path, help="source directory"
    )
    _add_scan_options(plan_parser)
    plan_parser.add_argument("--output", required=True, type=Path)
    plan_parser.add_argument("--plan-file", type=Path, help="SQLite plan database path")
    plan_parser.add_argument(
        "--report-file", type=Path, help="Markdown plan report path"
    )
    apply_parser = commands.add_parser("apply", help="apply an approved SQLite plan")
    apply_parser.add_argument("--plan", required=True, type=Path)
    apply_parser.add_argument(
        "--verbose",
        action="store_true",
        help="show hashing, copying, verification, and cleanup progress",
    )
    report_parser = commands.add_parser(
        "report", help=f"write {REPORT_FILENAME} to the current directory"
    )
    report_parser.add_argument(
        "--input",
        type=Path,
        default=Path("."),
        help="media directory to report on (default: current directory)",
    )
    _add_scan_options(report_parser)
    return parser.parse_args(arguments)


def _scan_from_arguments(
    arguments: argparse.Namespace, output: Path | None = None
) -> tuple[list[MediaMetadata], list[dict[str, str]]]:
    """Run a configured scan while managing its cache and geocoder."""
    source = arguments.input.expanduser().resolve()
    index_path = arguments.index.expanduser().resolve()
    if _is_relative_to(index_path, source):
        raise ValueError("The metadata index must be outside the input directory")
    excluded = [output] if output is not None else []
    with MetadataIndex(index_path) as index:
        geocoder: Geocoder
        if arguments.allow_network_geocoding:
            geocoder = NominatimGeocoder(index, arguments.geocoder_url)
        else:
            geocoder = NullGeocoder()
        return scan_library(
            source,
            index,
            geocoder,
            load_overrides(arguments.overrides),
            excluded,
            _console_progress if arguments.verbose else None,
        )


def _console_progress(message: str) -> None:
    """Print one immediately visible CLI progress message."""
    print(message, flush=True)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the selected workflow and convert expected errors to exit codes."""
    args = parse_arguments(arguments)
    try:
        if args.command == "scan":
            media_files, skipped = _scan_from_arguments(args)
            for media in media_files:
                location = (
                    "/".join(
                        value for value in (media.country, media.locality) if value
                    )
                    or "Unclassified"
                )
                print(f"[{media.media_type.upper()}] {media.path} -> {location}")
            for item in skipped:
                print(f"[SKIPPED] {item['path']}: {item['reason']}")
            if args.allow_network_geocoding:
                print(NOMINATIM_ATTRIBUTION)
            print(f"Finished: {len(media_files)} files, {len(skipped)} skipped.")
            return 1 if skipped else 0

        if args.command == "plan":
            source, output = validate_separate_trees(args.input, args.output)
            plan_file = args.plan_file or output / PLAN_FILENAME
            report_file = args.report_file or output / "organization-plan.md"
            for report_path in (plan_file, report_file):
                if _is_relative_to(report_path.expanduser().resolve(), source):
                    raise ValueError(
                        "Organization reports must be outside the input directory"
                    )
            media_files, skipped = _scan_from_arguments(args, output)
            plan = build_plan(
                source,
                output,
                media_files,
                skipped,
                _console_progress if args.verbose else None,
            )
            write_plan(plan, plan_file, report_file)
            print(f"Wrote {plan_file} and {report_file}.")
            print(
                f"Planned: {len(media_files)} files, {len(skipped)} skipped; "
                "no files copied."
            )
            if args.allow_network_geocoding:
                print(NOMINATIM_ATTRIBUTION)
            return 1 if skipped else 0

        if args.command == "report":
            media_files, skipped = _scan_from_arguments(args)
            report_file = Path.cwd() / REPORT_FILENAME
            write_report(build_report(args.input, media_files, skipped), report_file)
            print(f"Wrote {report_file}.")
            print(f"Reported: {len(media_files)} files, {len(skipped)} skipped.")
            if args.allow_network_geocoding:
                print(NOMINATIM_ATTRIBUTION)
            return 1 if skipped else 0

        copied, already, failed = apply_plan(
            args.plan, _console_progress if args.verbose else None
        )
        print(
            f"Finished: {copied} copied, {already} already organized, {failed} failed."
        )
        if failed == 0:
            print("Removed completed plan and report files.")
        return 1 if failed else 0
    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        sqlite3.Error,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
