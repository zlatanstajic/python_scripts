# Python Scripts

[![CI](https://github.com/zlatanstajic/python_scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/zlatanstajic/python_scripts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://zlatanstajic.github.io/python_scripts/)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776ab.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-0a9edc.svg?logo=pytest&logoColor=white)](https://pytest.org/)

> **Practical Python tools for documents, the web, and media libraries.**
> Three focused command-line utilities: render a single-page PDF CV, capture
> website screenshots, and build a verified organized copy of a media library.

📖 **Browse the docs:**
[zlatanstajic.github.io/python_scripts](https://zlatanstajic.github.io/python_scripts/)
(source in [`docs/`](docs/), published via GitHub Pages).

The repository's former general automation utilities now live in the sibling
[`shell-scripts`](https://github.com/zlatanstajic/shell-scripts) project.

<img src="assets/img/og-image.png" alt="Python Scripts social preview" width="100%">

## Table of Contents

- [Requirements](#requirements)
- [Development](#development)
- [Usage](#usage)
- [Configuration](#configuration)
- [Quality checks](#quality-checks)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

---

## Requirements

- Python 3.10 or newer
- WeasyPrint system libraries for PDF generation
- A Playwright Chromium browser for screenshots
- FFprobe (from FFmpeg) for media validation and metadata inspection
- Optional: ExifTool for richer photo, phone, and camcorder metadata

[⬆ back to top](#table-of-contents)

---

## Development

Install the project in editable mode together with the browser runtime:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

The install puts `cv-generator`, `website-screenshot`, and `media-organizer` on
the `PATH` of the activated environment. Because the install is editable,
edits under `scripts/` take effect immediately for those commands — no
reinstall is required.

The one exception is `[project.scripts]` in `pyproject.toml`: command names are
packaging metadata rather than source, so a new or renamed command only appears
after re-running `python -m pip install -e ".[dev]"`.

### Optional: user-level install with pipx

`pipx install .` places the same three commands in an isolated environment that
never needs activating. It is a good fit for `cv-generator`, which needs only
the WeasyPrint system libraries listed under [Requirements](#requirements).

No `pip` or `pipx` install ever provides the Chromium binary that
`website-screenshot` requires; only `python -m playwright install chromium`,
run with the interpreter of the environment that holds the command, does. That
step is not verified for a pipx-managed environment here, so use the virtual
environment above when you need `website-screenshot`.

[⬆ back to top](#table-of-contents)

---

## Usage

### CV generator

Set `MARKDOWN_FILE_URL` and `PDF_OUTPUT_LOCATION` in `.env`, then run:

```bash
cv-generator
```

`MARKDOWN_FILE_URL` may be a local path or `file://` URL. Relative input and
output paths are resolved from the current working directory.

### Website screenshots

Set `SCREENSHOT_SITES` to a comma-separated URL list and optionally set
`SCREENSHOT_OUTPUT_DIR` (the default is `~/Pictures`), then run:

```bash
website-screenshot
```

The tool runs Chromium headlessly and saves the visible 1600x900 viewport as a
JPEG named from each site's hostname — or, for GitHub Pages project sites, from
the repository name with underscores replaced by hyphens
(`https://username.github.io/my_project/` becomes `my-project.jpg`).
These first two commands accept no options other than `-h`/`--help`; their
inputs and output locations are configured only through `.env`.

Running the modules by file path is still supported and behaves identically:

```bash
python scripts/cv_generator.py
python scripts/screenshot.py
python scripts/media_organizer.py --help
```

### Media library organizer

The `media-organizer` command handles both photos and videos. It
uses a reviewable three-step workflow and never moves, renames, deletes, edits,
re-encodes, or writes metadata into source media:

Supported image formats are JPEG, PNG, HEIC, HEIF, WebP, TIFF, and AVIF;
existing video-format support is unchanged.

```bash
media-organizer scan --input "/home/user/Media" --verbose
media-organizer plan \
  --input "/home/user/Media" \
  --output "/home/user/Organized" \
  --verbose
media-organizer apply \
  --plan "/home/user/Organized/organization-plan.json" \
  --verbose
```

`plan` writes `organization-plan.json` and `organization-plan.md` in the
organized output directory by default. A fully successful `apply` removes both
plan artifacts; if an entry fails, it retains them with operation statuses for
inspection and retry. Copies are grouped under
`Year/Country/Locality`, written to temporary files, checked against the
plan's size and SHA-256 digest, and finalized without overwriting existing
files. Source and destination trees may not overlap.

After organizing, run `report` inside the library to save a JSON inventory of
what it holds:

```bash
cd "/home/user/Organized"
media-organizer report
```

`report` writes `media-report.json` to the current directory and replaces an
older report there. It counts photos, videos, formats such as `JPG` and `MP4`,
orientations such as landscape and portrait, and files per country and
locality. It also lists every file. Files in the organizer's
`Year/Country/Locality` folders report that folder's location; other files are
classified the same way `scan` classifies them. `--input` reports on another
directory, and the report is still saved in the current directory.

Location path components are transliterated to ASCII and use only Latin
letters, digits, and hyphen separators. Known localized location names are
canonicalized to English first (for example, `España` becomes `Spain` and
`Београд` becomes `Belgrade`). If no media file has a classified location,
location directories are omitted and each file's containing-folder
description is used in generated filenames. A leading `YYYY-MM - ` folder
prefix is omitted, and words are joined with underscores. In a mixed library,
unknown locations use `Unclassified`. Generated destination filenames never
reuse source filenames, and undated files use a deterministic content-hash
name. Original names remain available in the plan reports for traceability.

Year grouping and generated timestamps use the source file's filesystem
modification time. Reports identify this explicitly with the
`filesystem:mtime` provenance and retain its local UTC offset.

`--verbose` is optional on all four subcommands. It displays recursive
discovery, cache and metadata activity, classification, per-file planning,
hashing and copying percentages, verification, status persistence, and cleanup.

FFprobe is required to validate supported photo and video formats. ExifTool is
used when installed for richer EXIF, GPS, title, and camera metadata and
otherwise produces a warning. Without ExifTool, the report can show a rotated
photo in its stored orientation. Embedded GPS coordinates stay local by default.
Passing
`--allow-network-geocoding` explicitly permits coordinates to be sent to the
OpenStreetMap Nominatim reverse-geocoding service; responses are cached in the
SQLite metadata index. Public-server requests are serialized and limited to
one per second; use `--geocoder-url` with an `http` or `https` URL for another
compatible service. Review the
[Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/)
before opting in. See the [media organizer guide](docs/media_organizer.rst) for
metadata rules, overrides, cache behavior, and limitations.

[⬆ back to top](#table-of-contents)

---

## Configuration

The CV and screenshot commands read `.env` from the **current working
directory**, not from the
repository root and not from the installation directory. The file is loaded
with `override=False`, so real environment variables win over the values in the
file. A missing `.env` is a hard error.

```bash
cd ~/some/project && website-screenshot   # uses ~/some/project/.env
```

Every supported setting is documented in [`.env.example`](.env.example).

[⬆ back to top](#table-of-contents)

---

## Quality checks

```bash
python -m pytest tests/
python -m compileall -q scripts tests
python -m flake8 scripts/
python -m mypy scripts/
python -m pydocstyle scripts/
python -m bandit -r scripts/ -ll
python -m isort . --profile black --check-only --diff
python -m black . --check --diff
```

The pytest configuration measures coverage for `scripts/`. Build documentation
with warnings treated as errors using:

```bash
python -m sphinx -W -b html docs docs/_build/html
```

CI runs the Python checks on Python 3.10–3.13 for pushes to `master` and pull
requests targeting it. A separate documentation workflow builds Sphinx with
warnings as errors; see the [CI/CD guide](docs/cicd.rst) for details.

The social-preview image is generated deterministically by a committed Pillow
script and can be regenerated with:

```bash
python tools/gen-og-image.py  # requires Pillow
```

[⬆ back to top](#table-of-contents)

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to
propose a change.

[⬆ back to top](#table-of-contents)

---

## Security

Please follow the [security policy](SECURITY.md) to report a vulnerability
without publishing its details.

[⬆ back to top](#table-of-contents)

---

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md)
for details.

[⬆ back to top](#table-of-contents)
