# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Two independent Python CLI utilities, packaged as the `scripts` package:

- `scripts/cv_generator.py` — Markdown CV → single-page A4 PDF (Markdown → HTML → WeasyPrint).
- `scripts/screenshot.py` — 1600x900 Chromium/Playwright JPEG screenshots per configured site.

The scripts share no code beyond duplicated `load_environment` / `required_setting`
helpers. General automation utilities that used to live here moved to the sibling
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
python setup/install-pre-commit.py                  # install the git pre-commit hook
```

CI (`.github/workflows/ci.yml`) runs the lint set and pytest on Python 3.10/3.11/3.12;
`deploy-docs.yml` publishes `docs/` to GitHub Pages on `master`.

## Configuration model

Both scripts read configuration **only** from a `.env` file in the *current working
directory* (`Path.cwd() / ".env"`), loaded with `override=False` so real environment
variables win. A missing `.env` is a hard error. There are no CLI options beyond
`-h`/`--help` on the screenshot script. Any new setting must be documented in
`.env.example`. Never read or write the real `.env`.

## Conventions that matter here

- Python 3.10+, `from __future__ import annotations`, type hints, Google-style
  docstrings (`pydocstyle` enforces this on `scripts/`, not on tests), 88-char lines.
- `main()` returns an `int` exit code; `if __name__ == "__main__": raise SystemExit(main())`.
  Errors are caught in `main()`, printed as `Error: ...` to stderr, and turned into a
  non-zero return — do not let tracebacks escape.
- Two lint configs coexist: `pyproject.toml` `[tool.flake8]` (unread by flake8 7) and
  `.flake8` (the effective one). `mypy.ini` overrides `[tool.mypy]` — it targets 3.11
  and is laxer. Change both files when tightening rules.
- Runtime deps go in `pyproject.toml` *and* `requirements.txt`; dev deps in
  `pyproject.toml` *and* `requirements-dev.txt`. Dev tool versions are pinned exactly.
- Behavior changes must update `README.md` and the relevant page in `docs/`.
- Branch naming is enforced by convention: `issues/<number>_<short_description>` off
  `master`. See `CONTRIBUTING.md`.

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
- Per-site failures are reported and counted, not fatal; the process exits 1 if any
  site failed. Output is `<hostname>.jpg`, overwritten each run.
- Tests fake Playwright rather than launching a browser — keep the seams
  (`capture_website`, `load_config`, `hostname_to_filename`) injectable.
