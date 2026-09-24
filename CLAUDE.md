# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Three independent Python CLI utilities, packaged as the `scripts` package:

- `scripts/cv_generator.py` — Markdown CV → single-page A4 PDF (Markdown → HTML → WeasyPrint).
- `scripts/screenshot.py` — 1600x900 Chromium/Playwright JPEG screenshots per configured site.
- `scripts/media_organizer.py` — copy-only, manifest-driven media organization.

The scripts share no code; the CV and screenshot scripts each carry duplicated
`load_environment` / `required_setting` helpers. General automation utilities that
used to live here moved to the sibling
`shell-scripts` repository — do not re-add them.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m playwright install chromium   # screenshot script only
cp .env.example .env
```

WeasyPrint needs its system libraries (pango/cairo) present for PDF generation.

## Commands

```bash
python scripts/cv_generator.py        # reads MARKDOWN_FILE_URL, PDF_OUTPUT_LOCATION
python scripts/screenshot.py          # reads SCREENSHOT_SITES, SCREENSHOT_OUTPUT_DIR
python scripts/media_organizer.py -h  # scan, plan, apply, and report subcommands

python -m pytest tests/                                   # full suite + coverage
python -m pytest tests/test_screenshot.py::test_load_config_parses_sites_and_creates_output_directory
python -m pytest tests/ -k hostname                       # by name

python -m flake8 scripts/
python -m mypy scripts/
python -m pydocstyle scripts/
python -m bandit -r scripts/ -ll
python -m isort . --profile black --check-only --diff
python -m black . --check --diff
python -m compileall -q scripts tests

python -m sphinx -W -b html docs docs/_build/html   # docs; warnings are errors
python tools/gen-og-image.py                        # regenerate social preview (Pillow)
python setup/install-pre-commit.py                  # install the gate as the pre-commit hook
```

The hook installer backs up a different existing hook to `pre-commit.bak`
(then `.bak.1`, ...) instead of overwriting it.

CI (`.github/workflows/ci.yml`) runs the documented checks except Sphinx on Python
3.10–3.13; `deploy-docs.yml` builds Sphinx with warnings as errors and
publishes `docs/` to GitHub Pages on relevant pushes to `master`.

## Configuration model

`cv_generator` and `screenshot` read configuration **only** from a `.env` file in
the *current working directory* (`Path.cwd() / ".env"`), loaded with
`override=False` so real environment variables win. A missing `.env` is a hard
error. Neither CLI has options beyond `-h`/`--help`, and any new setting must be
documented in `.env.example`. `media_organizer` reads no `.env`: it is configured
only through its `scan`/`plan`/`apply`/`report` flags. Never read or write the
real `.env`.

## Conventions that matter here

- Python 3.10+, `from __future__ import annotations`, type hints, Google-style
  docstrings (`pydocstyle` enforces this on `scripts/`, not on tests), 88-char lines.
- `main()` returns an `int` exit code; `if __name__ == "__main__": raise SystemExit(main())`.
  Errors are caught in `main()`, printed as `Error: ...` to stderr, and turned into a
  non-zero return — do not let tracebacks escape.
- Each tool has exactly one config: `.flake8` for flake8 (it cannot read
  `pyproject.toml`), `mypy.ini` for mypy (targets 3.10), and `pyproject.toml` for
  Black, isort, pydocstyle, pytest, and coverage. Black infers its target versions
  from `requires-python`. Bandit is configured only by its command-line flags.
- Runtime deps go in `pyproject.toml` *and* `requirements.txt`; dev deps in
  `pyproject.toml` *and* `requirements-dev.txt`. Dev tool versions are pinned exactly.
- Behavior changes must update `README.md` and the relevant page in `docs/`.
- Branch naming is enforced by convention: `issues/<number>-<short-description>` off
  `master`, with the description in kebab-case (lowercase, hyphen-separated, never
  `snake_case`). See `CONTRIBUTING.md`.

## cv_generator specifics

- `RENDER_PROFILES` is an ordered tuple of four progressively tighter typography
  profiles. `generate_pdf` renders each in order and keeps the first that produces
  exactly one page; if none fits, it raises and leaves any existing PDF untouched.
  Don't add a profile below 8.5pt / 1.25 line-height without updating the error text.
- `ExperienceHeaderTreeprocessor` splits each `<h3>` at its **last** `|` into
  `.experience-title` / `.experience-dates` spans, preserving inline markup via the
  `_clone_range` element-cloning helpers. Editing those helpers risks silently
  dropping links or emphasis — the tests in `tests/test_cv_generator.py` cover it.
- The PDF is written to a temp file in the destination directory and `os.replace`d, so
  a failed render never truncates the previous output. Preserve that atomicity.
- CSS lives in `BASE_CSS` plus generated `:root` custom properties; the whole
  stylesheet is inlined into a self-contained HTML document.

## screenshot specifics

- One fresh browser context per site, reduced motion, animations disabled via injected
  CSS, `COOKIE_BANNER_SELECTORS` removed best-effort (failures ignored per selector).
- Per-site failures are reported and counted; the process exits 1 if any site
  failed. Output is `<hostname>.jpg`, except GitHub Pages project sites use
  `<project>.jpg` with underscores replaced by hyphens
  (`https://username.github.io/my_project/` → `my-project.jpg`). Files are
  overwritten on later runs.
- Tests fake Playwright rather than launching a browser — keep the seams
  (`capture_website`, `load_config`, `hostname_to_filename`) injectable.

## media organizer specifics

- `ffprobe` validates visual streams; `exiftool` enriches metadata when available.
- The source and output trees must never overlap. Source media files are read-only.
- `plan` binds entries to source size, nanosecond mtime, and SHA-256; `apply`
  copies via a temporary sibling, verifies the digest, then finalizes without
  overwriting.
- Plan artifacts default to the output directory. A successful `apply` removes
  them; a partially failed apply retains them for inspection and retry.
- `--verbose` uses injected progress callbacks; keep library calls quiet by
  default and flush CLI progress during scan, hashing, copying, and verification.
- Output location components are ASCII-transliterated and hyphen-separated.
  Known localized country/locality aliases are canonicalized to English first.
  Never use an original source filename as an organized destination fallback;
  undated names use a content-hash prefix.
- The effective recording timestamp is always the source filesystem mtime,
  labeled `filesystem:mtime`; embedded timestamps do not drive output paths.
- `report` reuses the scan pipeline and writes `media-report.json` to the
  current working directory, which may be inside the scanned tree. Paths that
  match `ORGANIZED_PATH` (`Year/Country/Locality/` plus a filename repeating
  that year and locality) take their location from the path as
  `organized:path`, because an organized copy carries neither its
  classification nor its source mtime.
- Orientation uses the displayed size: FFprobe display-matrix rotation, else
  EXIF `Orientation` for photos. A photo with several FFprobe streams is a
  tiled HEIF, so its size comes only from ExifTool. `MetadataIndex.get`
  treats records without a `rotation` key as stale.
- Network reverse geocoding is disabled unless `--allow-network-geocoding` is
  supplied. `NominatimGeocoder` accepts only http(s) endpoints with a host, which
  is what justifies its `# nosec B310`. Tests must use fake geocoders and metadata
  tool output.
