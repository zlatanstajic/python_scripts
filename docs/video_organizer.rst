Video Library Organizer
=======================

``video-organizer`` recursively inspects one video directory and creates a
separate, organized copy. It never moves, renames, deletes, modifies,
re-encodes, or writes metadata into source videos. Input and output directory
trees must not overlap.

Workflow
--------

First inspect the library without writing a plan or copying videos:

.. code-block:: bash

   video-organizer scan --input "/home/user/Videos" --verbose

Then create reviewable JSON and Markdown manifests. By default they are saved
as ``organization-plan.json`` and ``organization-plan.md`` inside the organized
output directory:

.. code-block:: bash

   video-organizer plan \
     --input "/home/user/Videos" \
     --output "/home/user/Organized" \
     --verbose

Review the reports, then apply the exact approved JSON plan:

.. code-block:: bash

   video-organizer apply \
     --plan "/home/user/Organized/organization-plan.json" \
     --verbose

``--plan-file`` and ``--report-file`` select different report paths. Every
manifest entry records its absolute source and destination, original and
generated filenames, recording time and timezone, metadata provenance, GPS
coordinates, resolved country and locality, detailed place, technical video
metadata, warnings, source identity, SHA-256 digest, and operation status.
After every entry applies successfully, the JSON plan and Markdown report are
removed. If any entry fails, both remain in place with the recorded operation
statuses so the problem can be inspected and the plan retried.

Progress reporting
------------------

``--verbose`` is available on ``scan``, ``plan``, and ``apply``. It flushes
messages immediately so progress remains visible during long operations. Scan
reports recursive discovery, cache hits, metadata extraction, classification,
and skipped files. Plan reports destination selection and hashing percentages.
Apply reports source validation, copying and verification percentages, each
saved operation status, failures, and final plan cleanup. Without the option,
the concise command output is unchanged.

Discovery and metadata
----------------------

The recognized extensions are MP4, MOV, MKV, AVI, WebM, M4V, WMV, MPEG, MPG,
MTS, M2TS, and 3GP, case-insensitively. An extension only makes a file a
candidate: FFprobe must confirm that it contains a video stream. Unreadable
and invalid candidates are reported and do not stop unrelated files.

FFprobe is required on ``PATH``. ExifTool is optional and enriches recording
timestamps, GPS, title, and camera/device metadata when installed. The
organizer deliberately uses each source file's filesystem modification time as
the effective recording time for year grouping and generated filenames. Its
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

   video-organizer plan \
     --input "/home/user/Videos" \
     --output "/home/user/Organized" \
     --allow-network-geocoding

Only coordinates are used in the lookup; video contents are never uploaded.
Exact lookup results are cached, requests are single-threaded and limited to
one per second, and output includes OpenStreetMap attribution. The public
server discourages large or recurring bulk jobs; read the `Nominatim usage
policy <https://operations.osmfoundation.org/policies/nominatim/>`_ before
opting in. ``--geocoder-url`` can select a compatible self-hosted or alternate
service. Service availability and returned administrative boundaries remain
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

Classified videos are grouped as ``Year/Country/Locality`` and named
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

A known year with an unknown location goes to ``Year/Unclassified`` and is
named ``YYYY-MM-DD_HH-MM-SS_Unclassified.ext``. Normal source files always
have a filesystem modification time; ``Unclassified/Unknown-Year`` and
``Undated_<content-hash>.ext`` remain defensive fallbacks for manually created
metadata without one. Organized filenames never reuse the original filename,
although the original name remains recorded in both manifests. The tool never
fabricates a location.

Cache and copy safety
---------------------

The default SQLite index is
``$XDG_CACHE_HOME/video-organizer/metadata.sqlite3`` or, when that variable is
unset, ``~/.cache/video-organizer/metadata.sqlite3``. ``--index`` selects a
different path, but the index must remain outside the source tree. Cached
metadata is reused only while absolute path, size, nanosecond modification
time, device, and inode still match.

Planning hashes every source file. Applying a plan checks its recorded size,
timestamp, and SHA-256 before copying. It checks available space, writes a
temporary file beside the destination, verifies its size and digest, and
finalizes without replacing an existing path. An identical destination is
reported as already organized; a different existing file is left untouched.
The manifest status is atomically updated after each entry, interrupted
temporary files are removed, failures do not stop unrelated entries, and
reapplying a completed plan is safe.
