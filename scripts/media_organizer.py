#!/usr/bin/env python3
"""Build a verified, copy-only photo and video library from an approved plan.

The command has three phases: ``scan`` reads metadata without changing source
files, ``plan`` writes SQLite and Markdown manifests, and ``apply`` copies and
verifies the files described by an approved SQLite manifest. ``report`` writes
a SQLite inventory of the media in a directory, such as a finished library.
``duplicates`` saves groups of files with identical decoded visual content to
a SQLite report without changing them. ``review-duplicates`` serves a
temporary page on the loopback interface for comparing those copies and is
the only command that deletes source media: one confirmed copy at a time,
after revalidating it against the report.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import http.server
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
import webbrowser
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from stat import S_ISREG
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
DUPLICATE_REPORT_FILENAME = "duplicate-report.sqlite3"
DUPLICATE_REPORT_SCHEMA_VERSION = 1
REVIEW_HOST = "127.0.0.1"
DEFAULT_REVIEW_PORT = 8765
_PREVIEW_PATH = re.compile(r"/preview/([1-9][0-9]{0,17})")
_UNAVAILABLE_PREVIEW = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180">'
    b'<rect width="100%" height="100%" fill="#e5e7eb"/>'
    b'<text x="50%" y="50%" text-anchor="middle" font-family="sans-serif" '
    b'fill="#374151">Preview unavailable</text></svg>'
)
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


def find_duplicates(
    source: Path, progress: ProgressCallback | None = None
) -> dict[str, Any]:
    """Group the media below source whose decoded visual content is identical.

    Only files of equal size are decoded and compared. Each ``(device, inode)``
    pair counts once, so a hard link or symlink never forms a group with the
    file it names, and a candidate resolving outside source is skipped. Source
    files are only read.
    """
    source = source.expanduser().resolve()
    skipped: list[dict[str, str]] = []
    identities: set[tuple[int, int]] = set()
    buckets: dict[int, list[tuple[Path, os.stat_result]]] = {}
    _emit_progress(progress, f"Scanning recursively: {source}")
    candidates = discover_media(source)
    _emit_progress(progress, f"Discovered {len(candidates)} media candidate(s).")
    for path in candidates:
        try:
            if not _is_relative_to(path, source):
                raise ValueError("Resolves outside the input directory")
            file_stat = path.stat()
            if not S_ISREG(file_stat.st_mode):
                raise ValueError("Not a regular file")
        except (OSError, ValueError) as error:
            skipped.append({"path": str(path), "reason": str(error)})
            _emit_progress(progress, f"Skipped {path}: {error}")
            continue
        identity = (file_stat.st_dev, file_stat.st_ino)
        if identity not in identities:
            identities.add(identity)
            buckets.setdefault(file_stat.st_size, []).append((path, file_stat))
    comparable = [
        (size, buckets[size]) for size in sorted(buckets) if len(buckets[size]) > 1
    ]
    total = sum(len(bucket) for _size, bucket in comparable)
    _emit_progress(
        progress,
        f"Comparing {total} candidate(s) in {len(comparable)} equal-size bucket(s).",
    )
    groups: list[dict[str, Any]] = []
    position = 0
    for size, bucket in comparable:
        matches: dict[str, list[tuple[MediaMetadata, os.stat_result]]] = {}
        for path, file_stat in bucket:
            position += 1
            prefix = f"[{position}/{total}]"
            try:
                _emit_progress(progress, f"{prefix} Extracting metadata: {path}")
                metadata = extract_metadata(path)
                _emit_progress(progress, f"{prefix} Hashing decoded frames: {path}")
                digest = visual_digest(metadata)
            except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
                skipped.append({"path": str(path), "reason": str(error)})
                _emit_progress(progress, f"{prefix} Skipped: {error}")
                continue
            matches.setdefault(digest, []).append((metadata, file_stat))
        for digest, members in matches.items():
            if len(members) < 2:
                continue
            entries: list[dict[str, Any]] = []
            for metadata, file_stat in members:
                try:
                    entries.append(_duplicate_entry(metadata, file_stat, progress))
                except (OSError, ValueError) as error:
                    skipped.append({"path": metadata.path, "reason": str(error)})
                    _emit_progress(progress, f"Skipped {metadata.path}: {error}")
            if len(entries) > 1:
                entries.sort(key=lambda entry: str(entry["path"]))
                groups.append(
                    {
                        "file_size": size,
                        "visual_digest": digest,
                        "status": "unresolved",
                        "entries": entries,
                    }
                )
    groups.sort(key=lambda group: str(group["entries"][0]["path"]))
    skipped.sort(key=lambda item: item["path"])
    return {
        "schema_version": DUPLICATE_REPORT_SCHEMA_VERSION,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_directory": str(source),
        "groups": groups,
        "skipped": skipped,
    }


def _duplicate_entry(
    metadata: MediaMetadata,
    file_stat: os.stat_result,
    progress: ProgressCallback | None,
) -> dict[str, Any]:
    """Hash a matched file and record the identity a later deletion must match."""
    path = Path(metadata.path)
    _emit_progress(progress, f"Hashing bytes: {path}")
    byte_digest = sha256_file(
        path,
        _percentage_progress(progress, "Byte hash") if progress is not None else None,
    )
    if _file_identity(path.stat()) != _file_identity(file_stat):
        raise ValueError("Changed during duplicate detection")
    size = display_size(metadata)
    return {
        "path": str(path),
        "media_type": metadata.media_type,
        "device": file_stat.st_dev,
        "inode": file_stat.st_ino,
        "mtime_ns": file_stat.st_mtime_ns,
        "sha256": byte_digest,
        "resolution": f"{size[0]}x{size[1]}" if size else None,
        "duration": metadata.duration,
        "status": "present",
        "error": None,
    }


def _file_identity(file_stat: os.stat_result) -> tuple[int, int, int, int]:
    """Return the device, inode, size, and nanosecond mtime of a file."""
    return file_stat.st_dev, file_stat.st_ino, file_stat.st_size, file_stat.st_mtime_ns


def visual_digest(metadata: MediaMetadata) -> str:
    """Return a SHA-256 digest of the decoded visual content of a media file.

    FFmpeg decodes every visual stream of a photo, or the first visual stream of
    a video, to ``rgba64le`` frames without applying rotation. The digest covers
    the displayed size, the rotation, each stream's ``#dimensions`` and ``#sar``
    lines, and each frame's stream index, byte size, and hash in order, but not
    timestamps or the ``#software`` and ``#tb`` lines.
    """
    if metadata.media_type == "image" and "%" in metadata.path:
        raise ValueError("FFmpeg reads '%' in an image path as a sequence pattern")
    command = (
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-noautorotate",
        "-i",
        metadata.path,
        "-map",
        "0:v" if metadata.media_type == "image" else "0:v:0",
        "-pix_fmt",
        "rgba64le",
        "-f",
        "framehash",
        "-hash",
        "sha256",
        "-",
    )
    digest = hashlib.sha256()
    digest.update(f"display {display_size(metadata)}\n".encode())
    digest.update(f"rotation {metadata.rotation}\n".encode())
    frames = 0
    unexpected = False
    for line in _framehash_lines(command):
        if line.startswith(("#dimensions", "#sar")):
            digest.update(f"{line.strip()}\n".encode())
        elif line.strip() and not line.startswith("#"):
            fields = [field.strip() for field in line.split(",")]
            if len(fields) < 6:
                unexpected = True
                continue
            digest.update(f"{fields[0]},{fields[4]},{fields[5]}\n".encode())
            frames += 1
    if unexpected or not frames:
        raise RuntimeError("FFmpeg produced no usable frame hashes")
    return digest.hexdigest()


def _framehash_lines(command: Sequence[str]) -> Iterable[str]:
    """Yield FFmpeg ``framehash`` output lines as they are produced.

    Unlike ``_run_json``, this neither buffers the output nor stops after a
    fixed time, because decoding a complete video can take much longer.
    """
    with tempfile.TemporaryFile() as errors:
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=errors,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as error:
            raise RuntimeError(f"FFmpeg could not start: {error}") from error
        with process:
            finished = False
            try:
                for line in cast(Iterable[str], process.stdout):
                    yield line.rstrip("\n")
                finished = True
            finally:
                if not finished:
                    process.kill()
        if process.returncode:
            errors.seek(0)
            details = errors.read().decode("utf-8", "replace").strip().splitlines()
            raise RuntimeError(details[-1] if details else "FFmpeg could not decode")


def write_duplicate_report(report: Mapping[str, Any], path: Path) -> None:
    """Atomically store duplicate groups in a normalized SQLite database."""
    _atomic_sqlite_write(
        path, lambda connection: _store_duplicate_report(connection, report)
    )


def _store_duplicate_report(
    connection: sqlite3.Connection, report: Mapping[str, Any]
) -> None:
    """Create the duplicate report schema and insert one detection run."""
    connection.executescript(
        """
        CREATE TABLE duplicate_report (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            schema_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            source_directory TEXT NOT NULL
        );
        CREATE TABLE duplicate_groups (
            id INTEGER PRIMARY KEY,
            file_size INTEGER NOT NULL,
            visual_digest TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('unresolved', 'resolved'))
        );
        CREATE TABLE duplicate_entries (
            id INTEGER PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES duplicate_groups (id),
            path TEXT NOT NULL UNIQUE,
            media_type TEXT NOT NULL,
            device INTEGER NOT NULL,
            inode INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            resolution TEXT,
            duration REAL,
            status TEXT NOT NULL CHECK (status IN ('present', 'deleted')),
            error TEXT,
            UNIQUE (device, inode)
        );
        CREATE TABLE duplicate_skipped (
            position INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            reason TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO duplicate_report VALUES (1, ?, ?, ?)",
        (report["schema_version"], report["created_at"], report["source_directory"]),
    )
    entry_id = 0
    for group_id, group in enumerate(report["groups"], start=1):
        connection.execute(
            "INSERT INTO duplicate_groups VALUES (?, ?, ?, ?)",
            (group_id, group["file_size"], group["visual_digest"], group["status"]),
        )
        for entry in group["entries"]:
            entry_id += 1
            connection.execute(
                """
                INSERT INTO duplicate_entries VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    group_id,
                    entry["path"],
                    entry["media_type"],
                    entry["device"],
                    entry["inode"],
                    entry["mtime_ns"],
                    entry["sha256"],
                    entry["resolution"],
                    entry["duration"],
                    entry["status"],
                    entry["error"],
                ),
            )
    connection.executemany(
        "INSERT INTO duplicate_skipped VALUES (?, ?, ?)",
        [
            (position, item["path"], item["reason"])
            for position, item in enumerate(report["skipped"], start=1)
        ],
    )


def load_duplicate_report(path: Path) -> dict[str, Any]:
    """Load a duplicate report after validating its schema and relations."""
    path = path.expanduser().resolve()
    if not _is_sqlite_database(path):
        raise ValueError(f"Not a SQLite duplicate report: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        _validate_duplicate_report(connection)
        row = connection.execute(
            """
            SELECT schema_version, created_at, source_directory
            FROM duplicate_report WHERE id = 1
            """
        ).fetchone()
        groups = {
            group["id"]: {**dict(group), "entries": []}
            for group in connection.execute(
                """
                SELECT id, file_size, visual_digest, status
                FROM duplicate_groups ORDER BY id
                """
            )
        }
        for entry in connection.execute(
            """
            SELECT id, group_id, path, media_type, device, inode, mtime_ns, sha256,
                resolution, duration, status, error
            FROM duplicate_entries ORDER BY id
            """
        ):
            values = dict(entry)
            groups[values.pop("group_id")]["entries"].append(values)
        return {
            **dict(row),
            "groups": list(groups.values()),
            "skipped": [
                dict(item)
                for item in connection.execute(
                    "SELECT path, reason FROM duplicate_skipped ORDER BY position"
                )
            ],
        }
    except sqlite3.DatabaseError as error:
        raise ValueError(f"Malformed duplicate report: {error}") from error
    finally:
        connection.close()


def _validate_duplicate_report(connection: sqlite3.Connection) -> None:
    """Reject missing tables, unsupported versions, and broken group relations."""
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    required = {
        "duplicate_report",
        "duplicate_groups",
        "duplicate_entries",
        "duplicate_skipped",
    }
    if not required <= tables:
        missing = ", ".join(sorted(required - tables))
        raise ValueError(f"Duplicate report is missing tables: {missing}")
    row = connection.execute(
        "SELECT schema_version FROM duplicate_report WHERE id = 1"
    ).fetchone()
    if row is None or row[0] != DUPLICATE_REPORT_SCHEMA_VERSION:
        raise ValueError("Unsupported duplicate report schema version")
    broken = connection.execute(
        """
        SELECT 1 FROM duplicate_entries
        WHERE group_id NOT IN (SELECT id FROM duplicate_groups)
        UNION ALL
        SELECT 1 FROM duplicate_groups
        WHERE (
            SELECT COUNT(*) FROM duplicate_entries
            WHERE duplicate_entries.group_id = duplicate_groups.id
        ) < 2
        LIMIT 1
        """
    ).fetchone()
    if broken is not None:
        raise ValueError("Duplicate report has invalid group-entry relations")


def serve_duplicate_review(report_path: Path, port: int = DEFAULT_REVIEW_PORT) -> None:
    """Serve the review page for a duplicate report until interrupted.

    The system browser opens the tokenized page once the loopback port is
    bound. Requests are handled one at a time, and the server and the report
    database are closed when serving ends, including after Ctrl+C.
    """
    server = DuplicateReviewServer(report_path, port)
    try:
        print(f"Reviewing {server.report_path} at {server.url}", flush=True)
        print("Press Ctrl+C to stop the review server.", flush=True)
        webbrowser.open(server.url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped the review server.", flush=True)
    finally:
        server.server_close()


class DuplicateReviewServer(http.server.HTTPServer):
    """Serve one duplicate report on the loopback interface, one request at a time."""

    def __init__(self, report_path: Path, port: int = DEFAULT_REVIEW_PORT) -> None:
        """Validate and open the report, then bind to ``REVIEW_HOST``."""
        if not 0 <= port <= 65535:
            raise ValueError(f"Port must be between 0 and 65535: {port}")
        self.report_path = report_path.expanduser().resolve()
        report = load_duplicate_report(self.report_path)
        self.source_directory = Path(report["source_directory"])
        self.token = secrets.token_urlsafe(32)
        self.nonce = secrets.token_urlsafe(16)
        # Requests are handled one at a time, so the connection is never shared
        # concurrently, even when a test serves from another thread.
        self.connection = sqlite3.connect(self.report_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        try:
            super().__init__((REVIEW_HOST, port), DuplicateReviewHandler)
        except OSError as error:
            raise OSError(
                f"Cannot serve on {REVIEW_HOST}:{port}: {error.strerror or error}; "
                "stop the other server or choose another --port"
            ) from error

    @property
    def url(self) -> str:
        """Return the tokenized address of the review page."""
        return f"http://{REVIEW_HOST}:{self.server_port}/?token={self.token}"

    def server_close(self) -> None:
        """Close the listening socket and the report database."""
        super().server_close()
        self.connection.close()


class DuplicateReviewHandler(http.server.BaseHTTPRequestHandler):
    """Answer token-protected requests for the review page and its previews."""

    server: DuplicateReviewServer

    def log_message(self, format: str, *args: Any) -> None:
        """Keep request lines, which carry the access token, off the console."""

    def end_headers(self) -> None:
        """Add the security headers to every response before ending them."""
        nonce = self.server.nonce
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; img-src 'self'; "
            f"style-src 'nonce-{nonce}'; script-src 'nonce-{nonce}'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        """Serve the review page or one entry's preview to a token holder."""
        url = urllib.parse.urlsplit(self.path)
        if self._allowed_method(url.path) != "GET":
            self._reject_method()
        elif not self._authorized(urllib.parse.parse_qs(url.query).get("token", [])):
            self._respond(HTTPStatus.FORBIDDEN, b"Forbidden\n")
        elif url.path == "/":
            page = _render_review_page(self.server).encode("utf-8")
            self._respond(HTTPStatus.OK, page, "text/html; charset=utf-8")
        else:
            self._send_preview(int(url.path.rsplit("/", 1)[1]))

    def _reject_method(self) -> None:
        """Answer 405 on a known route and 404 on any other path."""
        allowed = self._allowed_method(urllib.parse.urlsplit(self.path).path)
        if allowed is None:
            self._respond(HTTPStatus.NOT_FOUND, b"Not found\n")
        else:
            self._respond(
                HTTPStatus.METHOD_NOT_ALLOWED,
                b"Method not allowed\n",
                extra_headers=(("Allow", allowed),),
            )

    def do_POST(self) -> None:
        """Delete one confirmed copy, then redirect back to the review page.

        A report that cannot be read or updated gets a fixed 500 response.
        """
        if urllib.parse.urlsplit(self.path).path != "/delete":
            self._reject_method()
            return
        form = self._read_form()
        if form is None:
            self._respond(HTTPStatus.BAD_REQUEST, b"Bad request\n")
            return
        try:
            outcome = delete_duplicate_entry(
                self.server.connection,
                self.server.source_directory,
                form,
                self.server.token,
            )
        except sqlite3.Error:
            self._respond(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                b"The duplicate report could not be updated\n",
            )
            return
        rejected = {
            "forbidden": (HTTPStatus.FORBIDDEN, b"Forbidden\n"),
            "unconfirmed": (HTTPStatus.BAD_REQUEST, b"Deletion was not confirmed\n"),
            "unknown": (HTTPStatus.NOT_FOUND, b"Not found\n"),
            "resolved": (
                HTTPStatus.CONFLICT,
                b"This copy or its group is already resolved\n",
            ),
        }
        if outcome in rejected:
            self._respond(*rejected[outcome])
        else:
            location = f"/?token={self.server.token}"
            self._respond(
                HTTPStatus.SEE_OTHER, b"", extra_headers=(("Location", location),)
            )

    do_PUT = do_PATCH = do_DELETE = _reject_method
    do_HEAD = do_OPTIONS = do_TRACE = do_CONNECT = _reject_method

    @staticmethod
    def _allowed_method(path: str) -> str | None:
        """Return the method a route accepts, or None for an unknown path."""
        if path == "/" or _PREVIEW_PATH.fullmatch(path):
            return "GET"
        if path == "/delete":
            return "POST"
        return None

    def _read_form(self) -> dict[str, list[str]] | None:
        """Return a small URL-encoded request body, or None when it is invalid."""
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None
        if not 0 <= length <= 4096:
            return None
        body = self.rfile.read(length).decode("utf-8", "replace")
        return urllib.parse.parse_qs(body, keep_blank_values=True)

    def _authorized(self, tokens: Sequence[str]) -> bool:
        """Return whether a request carried exactly this process's token."""
        return len(tokens) == 1 and secrets.compare_digest(
            tokens[0].encode("utf-8"), self.server.token.encode("utf-8")
        )

    def _send_preview(self, entry_id: int) -> None:
        """Send a report entry's preview, or the unavailable-preview image."""
        entry = _review_entry(self.server.connection, entry_id)
        if entry is None:
            self._respond(HTTPStatus.NOT_FOUND, b"Not found\n")
            return
        preview = _entry_preview(entry, self.server.source_directory)
        if preview is None:
            self._respond(HTTPStatus.OK, _UNAVAILABLE_PREVIEW, "image/svg+xml")
        else:
            self._respond(HTTPStatus.OK, preview, "image/jpeg")

    def _respond(
        self,
        status: HTTPStatus,
        body: bytes,
        content_type: str = "text/plain; charset=utf-8",
        extra_headers: Sequence[tuple[str, str]] = (),
    ) -> None:
        """Send one complete response."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


def _review_entry(connection: sqlite3.Connection, entry_id: int) -> sqlite3.Row | None:
    """Return one report entry with its group's file size and status."""
    return cast(
        "sqlite3.Row | None",
        connection.execute(
            """
            SELECT duplicate_entries.*, duplicate_groups.file_size,
                duplicate_groups.status AS group_status
            FROM duplicate_entries
            JOIN duplicate_groups ON duplicate_groups.id = duplicate_entries.group_id
            WHERE duplicate_entries.id = ?
            """,
            (entry_id,),
        ).fetchone(),
    )


def _recorded_file_problem(entry: sqlite3.Row, source_directory: Path) -> str | None:
    """Return why a report entry no longer names its recorded file, or None."""
    path = Path(entry["path"])
    try:
        inside = _is_relative_to(path.resolve(), source_directory)
        file_stat = os.lstat(path)
    except (OSError, RuntimeError):
        return "The file is no longer available"
    if not inside:
        return "The file is outside the report's source directory"
    if not S_ISREG(file_stat.st_mode):
        return "The path is no longer a regular file"
    recorded = (entry["device"], entry["inode"], entry["file_size"], entry["mtime_ns"])
    if _file_identity(file_stat) != recorded:
        return "The file changed after duplicate detection"
    return None


def _entry_preview(entry: sqlite3.Row, source_directory: Path) -> bytes | None:
    """Return a bounded JPEG preview of an unchanged report entry, if possible.

    A photo becomes one frame scaled to fit 640x640 pixels. A video becomes a
    3x3 contact sheet of key frames spread over its duration, each scaled to
    fit 320x320 pixels. FFmpeg gets 30 seconds per preview.
    """
    if _recorded_file_problem(entry, source_directory) is not None:
        return None
    if entry["media_type"] == "image":
        options: tuple[str, ...] = ()
        video_filter = (
            "scale='min(640,iw)':'min(640,ih)':force_original_aspect_ratio=decrease"
        )
    else:
        interval = max((_as_float(entry["duration"]) or 0.0) / 9, 0.1)
        options = ("-skip_frame", "nokey")
        video_filter = (
            f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{interval:.3f})',"
            "scale=320:320:force_original_aspect_ratio=decrease,tile=3x3"
        )
    command = (
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        *options,
        "-i",
        str(entry["path"]),
        "-map",
        "0:v:0",
        "-vf",
        video_filter,
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-c:v",
        "mjpeg",
        "-",
    )
    try:
        result = subprocess.run(command, capture_output=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode or not result.stdout.startswith(b"\xff\xd8"):
        return None
    return result.stdout


def delete_duplicate_entry(
    connection: sqlite3.Connection,
    source_directory: Path,
    form: Mapping[str, Sequence[str]],
    token: str,
) -> str:
    """Delete one confirmed duplicate copy after revalidating it against the report.

    Returns ``"forbidden"`` or ``"unconfirmed"`` before the report is opened for
    writing, and ``"unknown"`` or ``"resolved"`` without touching any file.
    Otherwise the report's write lock is taken with ``BEGIN IMMEDIATE`` before
    the entry is reloaded, and the file is checked again. A deletion is written
    to the report before the file is removed and committed only after removal
    succeeds, returning ``"deleted"``. A copy that fails a check is kept with a
    sanitized error on its entry, returning ``"failed"``. A ``sqlite3.Error``
    from a read-only, locked, or unwritable report rolls the transaction back and
    propagates; when it is raised before removal, the file is untouched.
    """
    fields = {name: values[0] for name, values in form.items() if len(values) == 1}
    submitted = fields.get("token", "").encode("utf-8")
    if not secrets.compare_digest(submitted, token.encode("utf-8")):
        return "forbidden"
    if fields.get("confirmed") != "yes":
        return "unconfirmed"
    connection.execute("BEGIN IMMEDIATE")
    try:
        outcome = _delete_under_lock(
            connection, fields.get("entry", ""), source_directory
        )
        connection.commit()
    finally:
        if connection.in_transaction:
            connection.rollback()
    return outcome


def _delete_under_lock(
    connection: sqlite3.Connection, entry_id: str, source_directory: Path
) -> str:
    """Revalidate and delete one entry inside the open report write transaction."""
    entry = None
    if re.fullmatch(r"[1-9][0-9]{0,17}", entry_id):
        entry = _review_entry(connection, int(entry_id))
    if entry is None:
        return "unknown"
    if entry["status"] != "present" or entry["group_status"] != "unresolved":
        return "resolved"
    problem = _deletion_problem(connection, entry, source_directory)
    if problem is None:
        connection.execute("SAVEPOINT deletion")
        connection.execute(
            """
            UPDATE duplicate_entries SET status = 'deleted', error = NULL
            WHERE id = ?
            """,
            (entry["id"],),
        )
        connection.execute(
            """
            UPDATE duplicate_groups SET status = 'resolved'
            WHERE id = ? AND (
                SELECT COUNT(*) FROM duplicate_entries
                WHERE group_id = ? AND status = 'present'
            ) < 2
            """,
            (entry["group_id"], entry["group_id"]),
        )
        problem = _recorded_file_problem(entry, source_directory)
        if problem is None:
            try:
                os.unlink(entry["path"])
            except OSError as error:
                reason = error.strerror or "operating system error"
                problem = f"Deletion failed: {reason}"
            else:
                return "deleted"
        connection.execute("ROLLBACK TO deletion")
    connection.execute(
        "UPDATE duplicate_entries SET error = ? WHERE id = ?",
        (problem, entry["id"]),
    )
    return "failed"


def _deletion_problem(
    connection: sqlite3.Connection, entry: sqlite3.Row, source_directory: Path
) -> str | None:
    """Return why an entry's file must be kept, or None once it is revalidated."""
    problem = _recorded_file_problem(entry, source_directory)
    if problem is not None:
        return problem
    siblings = connection.execute(
        """
        SELECT duplicate_entries.*, duplicate_groups.file_size
        FROM duplicate_entries
        JOIN duplicate_groups ON duplicate_groups.id = duplicate_entries.group_id
        WHERE duplicate_entries.group_id = ? AND duplicate_entries.id != ?
            AND duplicate_entries.status = 'present'
        """,
        (entry["group_id"], entry["id"]),
    ).fetchall()
    if all(_recorded_file_problem(sibling, source_directory) for sibling in siblings):
        return "No other copy in this group still matches the report"
    try:
        if sha256_file(Path(entry["path"])) != entry["sha256"]:
            return "The file content changed after duplicate detection"
    except OSError as error:
        return f"Deletion failed: {error.strerror or 'operating system error'}"
    return None


def _render_review_page(server: DuplicateReviewServer) -> str:
    """Return the review page with side-by-side cards for unresolved groups."""
    groups: dict[int, list[sqlite3.Row]] = {}
    for row in server.connection.execute(
        """
        SELECT duplicate_entries.*, duplicate_groups.file_size
        FROM duplicate_entries
        JOIN duplicate_groups ON duplicate_groups.id = duplicate_entries.group_id
        WHERE duplicate_groups.status = 'unresolved'
            AND duplicate_entries.status = 'present'
        ORDER BY duplicate_groups.id, duplicate_entries.id
        """
    ):
        groups.setdefault(row["group_id"], []).append(row)
    token = _html(server.token)
    sections = "".join(
        _render_review_group(group_id, rows, token) for group_id, rows in groups.items()
    )
    style = (
        "body{font-family:system-ui,sans-serif;margin:1.5rem;color:#1f2937;"
        "background:#f9fafb}.cards{display:grid;gap:1rem;"
        "grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))}"
        ".card{background:#fff;border:1px solid #d1d5db;border-radius:.5rem;"
        "padding:1rem}.card img{display:block;width:100%;height:18rem;"
        "object-fit:contain;background:#e5e7eb}dt{font-weight:600}"
        "dd{margin:0 0 .5rem;overflow-wrap:anywhere}"
        ".error,.warning{color:#991b1b}.warning{font-weight:600}"
        "button{background:#b91c1c;color:#fff;border:0;border-radius:.375rem;"
        "padding:.5rem 1rem;cursor:pointer}"
    )
    script = (
        'for (const form of document.querySelectorAll("form.delete")) {'
        'form.addEventListener("submit", (event) => {'
        "if (!window.confirm(form.dataset.confirm)) {"
        "event.preventDefault();"
        "return;"
        "}"
        'form.elements.confirmed.value = "yes";'
        "});"
        "}"
    )
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Duplicate review</title>"
        f'<style nonce="{_html(server.nonce)}">{style}</style></head><body>'
        "<h1>Duplicate review</h1>"
        f"<p>Source directory: <code>{_html(server.source_directory)}</code></p>"
        '<p class="warning">Deleting a copy permanently removes that file from '
        "disk and cannot be undone. Every deletion asks for confirmation.</p>"
        f"{sections or '<p>No unresolved duplicate groups remain.</p>'}"
        f'<script nonce="{_html(server.nonce)}">{script}</script>'
        "</body></html>"
    )


def _render_review_group(group_id: int, rows: Sequence[sqlite3.Row], token: str) -> str:
    """Return one group's section with a card for each present copy."""
    cards = []
    for row in rows:
        entry_id = _html(row["id"])
        duration = (
            "not applicable" if row["duration"] is None else f"{row['duration']} s"
        )
        error = f'<p class="error">{_html(row["error"])}</p>' if row["error"] else ""
        confirm = f"Permanently delete {row['path']}? This cannot be undone."
        cards.append(
            '<article class="card">'
            f'<img src="/preview/{entry_id}?token={token}" '
            f'alt="Preview of copy {entry_id}" loading="lazy">'
            f"<dl><dt>Path</dt><dd>{_html(row['path'])}</dd>"
            f"<dt>Media type</dt><dd>{_html(row['media_type'])}</dd>"
            f"<dt>Size</dt><dd>{_html(row['file_size'])} bytes</dd>"
            f"<dt>Resolution</dt><dd>{_html(row['resolution'] or 'unknown')}</dd>"
            f"<dt>Duration</dt><dd>{_html(duration)}</dd></dl>"
            f"{error}"
            '<form method="post" action="/delete" class="delete" '
            f'data-confirm="{_html(confirm)}">'
            f'<input type="hidden" name="token" value="{token}">'
            f'<input type="hidden" name="entry" value="{entry_id}">'
            '<input type="hidden" name="confirmed" value="">'
            '<button type="submit">Delete this copy</button></form>'
            "</article>"
        )
    return (
        '<section class="group">'
        f"<h2>Group {_html(group_id)}: {len(rows)} identical copies</h2>"
        f'<div class="cards">{"".join(cards)}</div></section>'
    )


def _html(value: Any) -> str:
    """Return a value as HTML-escaped text."""
    return html.escape(str(value))


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
    """Parse the scan, plan, apply, report, and duplicate command-line interface."""
    parser = argparse.ArgumentParser(
        description="Organize photos and videos by year and parent locality without "
        "changing the source library. Only review-duplicates deletes source media, "
        "one confirmed copy at a time."
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
    duplicates_parser = commands.add_parser(
        "duplicates",
        help=f"write exact visual duplicate groups to {DUPLICATE_REPORT_FILENAME}",
    )
    duplicates_parser.add_argument(
        "--input", required=True, type=Path, help="media directory to search"
    )
    duplicates_parser.add_argument(
        "--report-file",
        type=Path,
        help=f"SQLite report path (default: ./{DUPLICATE_REPORT_FILENAME})",
    )
    duplicates_parser.add_argument(
        "--verbose",
        action="store_true",
        help="show discovery, decoding, and hashing progress",
    )
    review_parser = commands.add_parser(
        "review-duplicates",
        help=f"compare duplicates on a temporary page at {REVIEW_HOST} and delete "
        "confirmed copies",
    )
    review_parser.add_argument(
        "--report", required=True, type=Path, help="report written by duplicates"
    )
    review_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_REVIEW_PORT,
        help="loopback port to serve on (default: %(default)s)",
    )
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

        if args.command == "duplicates":
            missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
            if missing:
                raise RuntimeError(
                    f"{' and '.join(missing)} must be installed and on PATH"
                )
            report_file = args.report_file or Path.cwd() / DUPLICATE_REPORT_FILENAME
            report_file = report_file.expanduser().resolve()
            if report_file.suffix.lower() in SUPPORTED_EXTENSIONS:
                raise ValueError(
                    "The duplicate report must not use a media file extension"
                )
            duplicates = find_duplicates(
                args.input, _console_progress if args.verbose else None
            )
            write_duplicate_report(duplicates, report_file)
            copies = sum(len(group["entries"]) for group in duplicates["groups"])
            print(f"Wrote {report_file}.")
            print(
                f"Found: {len(duplicates['groups'])} duplicate group(s), {copies} "
                f"copies, {len(duplicates['skipped'])} skipped; no files changed."
            )
            return 1 if duplicates["skipped"] else 0

        if args.command == "review-duplicates":
            serve_duplicate_review(args.report, args.port)
            return 0

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
