Media Library Organizer
=======================

``media-organizer`` recursively inspects one media directory and
creates a separate, organized copy. Its ``scan``, ``plan``, ``apply``,
``report``, and ``duplicates`` subcommands never move, rename, delete, modify,
re-encode, or write metadata into source media. ``review-duplicates`` is the
only subcommand that deletes source media, one confirmed copy at a time; see
`Duplicate detection and review`_. Input and output trees must not overlap.

Workflow
--------

First inspect the library without writing a plan or copying media files:

.. code-block:: bash

   media-organizer scan --input "/home/user/Media" --verbose

Then create a normalized SQLite manifest and a reviewable Markdown report. By
default they are saved as ``organization-plan.sqlite3`` and
``organization-plan.md`` inside the organized output directory:

.. code-block:: bash

   media-organizer plan \
     --input "/home/user/Media" \
     --output "/home/user/Organized" \
     --verbose

Review the report, then apply the exact approved SQLite plan:

.. code-block:: bash

   media-organizer apply \
     --plan "/home/user/Organized/organization-plan.sqlite3" \
     --verbose

``--plan-file`` selects the SQLite database path and ``--report-file``
selects the Markdown path. The normalized ``organization_plan``,
``plan_entries``, ``plan_entry_warnings``, and ``plan_skipped`` tables
record absolute source and destination paths, original and generated filenames,
recording time and timezone, metadata provenance, GPS coordinates, resolved
country and locality, detailed place, media type, technical metadata, warnings,
source identity, SHA-256 digest, and operation status. Existing JSON plans can
still be applied for backward compatibility.

After every entry applies successfully, the SQLite plan and Markdown report are
removed. If any entry fails, both remain in place, and the database and Markdown
report retain the recorded operation statuses so the problem can be inspected
and the plan retried.

Privacy of generated files
--------------------------

Plans, reports, and the metadata cache can contain personal file paths,
filenames, timestamps, and location data. Plans and the cache can also retain
GPS coordinates and detailed place information. Disabling network geocoding
does not remove location metadata from these local files.

Keep these outputs private. Before sharing an example or bug report, replace
personal paths and metadata with synthetic values. The repository ignores
SQLite databases and their sidecar files, default Markdown plans, and legacy
JSON plans and reports. Custom output filenames still need their own ignore
rules or storage outside the checkout. Ignore rules do not remove data that
has already been committed from Git history.

Library report
--------------

After organizing, run ``report`` inside the library to save a SQLite inventory
of what it holds:

.. code-block:: bash

   cd "/home/user/Organized"
   media-organizer report

The inventory is written to ``media-report.sqlite3`` in the current directory
and replaces an older report there. ``--input`` selects a different directory;
the report is still saved in the current directory. ``report`` accepts the
same ``--overrides``, ``--index``, geocoding, and ``--verbose`` options as
``scan``, never copies media, and exits with status 1 when a file is skipped.
The normalized database contains:

* ``media_report``: report metadata plus total, photo, video, classified,
  unclassified, country, locality, and skipped counts.
* ``report_formats``: file extensions such as ``JPG`` or ``MP4``, counted
  separately for images and videos.
* ``report_orientations``: ``landscape``, ``portrait``, ``square``, and
  ``unknown`` files, counted separately for images and videos.
* ``report_locations``: files per locality within each country.
* ``report_entries``: each file's path, media type, format, size in bytes,
  displayed resolution, orientation, duration, country, locality, and location
  provenance.
* ``report_skipped``: files that could not be read, with the reason.

Orientation compares the displayed width and height. Video rotation comes from
the FFprobe display matrix. Photo rotation comes from the EXIF orientation that
ExifTool reads, so without ExifTool a rotated photo keeps its stored
orientation. FFprobe 7 and later list each tile of a tiled HEIF photo as a
separate stream; such a photo takes its size from ExifTool and is ``unknown``
without it.

A file whose path follows the organizer's ``Year/Country/Locality`` layout, and
whose generated name repeats that year and locality, reports that folder's
country and locality with ``organized:path`` provenance. Other files are
classified the same way ``scan`` classifies them. When OpenStreetMap
Nominatim resolved a location, the report includes its attribution.

Duplicate detection and review
------------------------------

``duplicates`` finds exact visual duplicates, such as the same photo or video
copied from several devices, and saves them for review in the browser:

.. code-block:: bash

   media-organizer duplicates --input "/home/user/Media" --verbose
   media-organizer review-duplicates --report duplicate-report.sqlite3

``duplicates`` requires ``ffmpeg`` and ``ffprobe`` on ``PATH`` and otherwise
fails before writing anything. It only reads media and writes
``duplicate-report.sqlite3`` to the current directory, replacing an older
report there; ``--report-file`` selects another path, which must not use a
media file extension. Every candidate that discovery finds is considered.
Candidates that resolve outside the input directory are skipped, and hard
links and symlinks to one file count once. Only files of equal size are
decoded and compared.

FFmpeg decodes every visual stream of a photo, or the first visual stream of a
video, to ``rgba64le`` frames without automatic rotation, and its
``framehash`` muxer hashes each frame with SHA-256. The visual digest covers
the displayed size, the rotation, each stream's dimensions and sample aspect
ratio, and every frame's stream index, size, and hash in order, but not
timestamps or encoder details. Files are grouped only when these digests are
identical, so resized, cropped, recompressed, or merely similar media are not
duplicates. Decoding complete videos is CPU-intensive. Whether HEIC, HEIF, and
AVIF photos decode depends on the FFmpeg build, and without ExifTool, photos
that differ only in their EXIF orientation tag can match. A candidate that
cannot be read, validated, or decoded is recorded as skipped without stopping
other files, and the command then exits with status 1. The normalized
database contains:

* ``duplicate_report``: the schema version, creation time, and source
  directory.
* ``duplicate_groups``: each group's file size, visual digest, and
  ``unresolved`` or ``resolved`` status.
* ``duplicate_entries``: each copy's path, media type, device, inode,
  nanosecond modification time, byte SHA-256 digest, displayed resolution,
  duration, ``present`` or ``deleted`` status, and last deletion error.
* ``duplicate_skipped``: files that could not be compared, with the reason.

``review-duplicates`` binds only to ``127.0.0.1``, on port ``8765`` unless
``--port`` selects another, and opens a tokenized page in the system browser.
The page is available only while the command runs in the foreground; Ctrl+C
stops the server and closes the report, and a busy port makes the command exit
with status 1. Each unresolved group shows its present copies side by side
with a preview, path, media type, size, resolution, and duration, and every
copy has its own delete button, so a group of three or more copies is reviewed
as one group.

.. warning::

   Deleting a copy permanently removes that file from disk and cannot be
   undone. The report's status records are an audit trail, not a backup.

A deletion needs an explicit browser confirmation and a POST request carrying
the page's per-process token; GET requests never delete anything. The server
then takes the report's write lock, reloads the entry, and requires that it is
still present in an unresolved group, that its path still resolves inside the
recorded source directory, that it is a regular file rather than a symlink,
that its device, inode, size, and nanosecond modification time are unchanged,
that another copy in the group still matches the report, and that its byte
SHA-256 digest still matches. Before touching the file, it writes the outcome
to the report: the copy is marked ``deleted``, and its group becomes
``resolved`` once fewer than two present copies remain. It then repeats the
identity check, removes exactly that path, and commits the report only after
the removal succeeds. A failed check deletes nothing and records a short
reason on the copy instead, which the page then shows, and repeating a
submission for a deleted copy or a resolved group changes nothing.

Nothing is deleted when the report cannot be updated, for example because it
is read-only or locked by another process; the request then fails with a fixed
error that contains no file details. Removing a file and committing the report
cannot be one atomic step, so if only the final commit fails, the removed copy
stays listed as present and then fails revalidation as missing.

Previews are generated on request, and only for report entries that still match
their recorded identity. A photo preview is one frame scaled to fit 640x640
pixels, and a video preview is a 3x3 contact sheet of key frames spread over
its duration, each tile fitting 320x320 pixels. FFmpeg gets 30 seconds per
preview; a failed, slow, or changed file shows a "Preview unavailable" image
instead. Every response carries a restrictive Content Security Policy and
anti-framing, no-sniff, no-referrer, and no-store headers, error responses
contain no filesystem details, and every rendered path is HTML-escaped.

Progress reporting
------------------

``--verbose`` is available on ``scan``, ``plan``, ``apply``, ``report``, and
``duplicates``. It flushes messages immediately so progress remains visible
during long operations. Scan and report show recursive discovery, cache hits,
metadata extraction, classification, and skipped files. Plan reports
destination selection and hashing percentages. Duplicates shows discovery,
equal-size comparison, metadata extraction, frame decoding, byte hashing
percentages, and skipped files.
Apply reports source validation, copying and verification percentages, each
saved operation status, failures, and final plan cleanup. Without the option,
the concise command output is unchanged.

Discovery and metadata
----------------------

Recognized image extensions are JPEG, JPG, PNG, HEIC, HEIF, WebP, TIFF, TIF,
and AVIF. Recognized video extensions are MP4, MOV, MKV, AVI, WebM, M4V, WMV,
MPEG, MPG, MTS, M2TS, and 3GP. Matching is case-insensitive. An extension only
makes a file a candidate: FFprobe normally must confirm that it contains a
decodable visual stream. When FFprobe cannot parse a HEIC or HEIF image,
ExifTool may validate its file type and positive dimensions instead. Format
availability can depend on the installed FFmpeg and ExifTool builds. Unreadable
and invalid candidates are reported and do not stop unrelated files.

FFprobe is required on ``PATH``. ExifTool is optional and enriches recording
timestamps, EXIF GPS, title, dimensions, and camera/device metadata for photos
and videos when installed. The organizer deliberately uses each source file's
filesystem modification time as the effective recording time for year grouping
and generated filenames. Its
local UTC offset is retained and the manifest marks its provenance as
``filesystem:mtime``. The nanosecond modification time is also used for cache
invalidation and approved-plan validation. Missing locations remain unknown.

Location classification
-----------------------

Classification is conservative and considers, in order, embedded GPS,
explicit geographic metadata, recognizable aliases in the title, filename or
source path, and per-file overrides. A result must contain both a country and
a parent city, town, or village. Detailed landmarks remain in the manifest but
do not become directories.

GPS coordinates are never transmitted by default. To approve sending them to
the OpenStreetMap Nominatim service for reverse geocoding, opt in explicitly:

.. code-block:: bash

   media-organizer plan \
     --input "/home/user/Media" \
     --output "/home/user/Organized" \
     --allow-network-geocoding

Only coordinates are used in the lookup; media contents are never uploaded.
Exact lookup results are cached, requests are single-threaded and limited to
one per second, and output includes OpenStreetMap attribution. The public
server discourages large or recurring bulk jobs; read the `Nominatim usage
policy <https://operations.osmfoundation.org/policies/nominatim/>`_ before
opting in. ``--geocoder-url`` can select a compatible self-hosted or alternate
service; it must be an ``http`` or ``https`` URL. Service availability and returned administrative boundaries remain
external limitations, so review the plan before applying it.

Overrides
---------

An optional UTF-8 JSON file can define recognizable place aliases and exact
per-file classifications. Relative file keys use paths below ``--input``:

.. code-block:: json

   {
     "places": {
       "Beograd": {"country": "Serbia", "locality": "Belgrade"},
       "Lloret": {"country": "Spain", "locality": "Lloret de Mar"}
     },
     "files": {
       "2026/unknown/IMG_1031.mov": {
         "country": "Serbia",
         "locality": "Novi Sad"
       }
     }
   }

Pass it to either inspection command with ``--overrides overrides.json``.
Conflicting recognizable aliases cause an unclassified result instead of a
guess. The organizer never merges nearby coordinates with a radius rule.

Output names and unknown metadata
---------------------------------

Classified media files are grouped as ``Year/Country/Locality`` and named
``YYYY-MM-DD_HH-MM-SS_Locality.ext``. Multiple visits to the same locality in
one year therefore share a directory. Country and locality components are
transliterated to ASCII Latin letters and digits with hyphen separators;
Cyrillic and Greek names have explicit transliteration support, and Latin
diacritics are folded to their ASCII forms. Known localized names are
canonicalized to English first, such as ``España`` to ``Spain``, ``Србија`` to
``Serbia``, and ``Београд`` to ``Belgrade``. Online reverse-geocoding requests
also explicitly request English results. A name in an unsupported script
uses ``Unknown-Country`` or ``Unknown-Locality`` rather than placing non-ASCII
text in a path. Deterministic ``_002``, ``_003``, and later suffixes resolve
collisions.

If none of the media files has a classified location, the organizer
omits location directories. Dated files then go directly under ``Year`` and
use their sanitized containing-folder description as the filename title. For
example, ``2022-08 - Traganou Beach on Rhodes`` produces
``Year/YYYY-MM-DD_HH-MM-SS_Traganou_Beach_on_Rhodes.ext``. The leading
``YYYY-MM - `` portion is omitted, and description words are joined with
underscores. If at least one file is classified, a known year with an unknown
location still goes to
``Year/Unclassified`` and is named
``YYYY-MM-DD_HH-MM-SS_Unclassified.ext``. Normal source files always have a
filesystem modification time; ``Unclassified/Unknown-Year`` and
``Undated_<content-hash>.ext`` remain defensive fallbacks for manually created
metadata without one. Organized filenames never reuse the original filename,
although the original name remains recorded in both manifests. The tool never
fabricates a location.

Cache and copy safety
---------------------

The default SQLite index is
``$XDG_CACHE_HOME/media-organizer/metadata.sqlite3`` or, when that variable is
unset, ``~/.cache/media-organizer/metadata.sqlite3``. ``--index`` selects a
different path, but the index must remain outside the source tree. Cached
metadata is reused only while absolute path, size, nanosecond modification
time, device, and inode still match. Records cached before display rotation
was recorded are read again once.

Planning hashes every source file. Applying a plan checks its recorded size,
timestamp, and SHA-256 before copying. It checks available space, writes a
temporary file beside the destination, verifies its size and digest, and
finalizes without replacing an existing path. An identical destination is
reported as already organized; a different existing file is left untouched.
The SQLite manifest status is transactionally updated after each entry, interrupted
temporary files are removed, failures do not stop unrelated entries, and
reapplying a completed plan is safe.
