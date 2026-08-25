# Python Scripts

Two focused Python command-line utilities:

- `scripts/cv_generator.py` renders a single-page PDF CV from Markdown.
- `scripts/screenshot.py` captures 1600x900 website viewport screenshots with Playwright.

The repository's former general automation utilities now live in the sibling
[`shell-scripts`](https://github.com/zlatanstajic/shell-scripts) project.

## Requirements

- Python 3.10 or newer
- WeasyPrint system libraries for PDF generation
- A Playwright Chromium browser for screenshots

Install the project and browser runtime:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

## CV generator

Set `MARKDOWN_FILE_URL` and `PDF_OUTPUT_LOCATION` in `.env`, then run:

```bash
python scripts/cv_generator.py
```

`MARKDOWN_FILE_URL` may be a local path or `file://` URL. Relative input and
output paths are resolved from the current working directory.

## Website screenshots

Set `SCREENSHOT_SITES` to a comma-separated URL list and optionally set
`SCREENSHOT_OUTPUT_DIR` (the default is `~/Pictures`), then run:

```bash
python scripts/screenshot.py
```

The tool runs Chromium headlessly and saves the visible 1600x900 viewport as a
JPEG named from each site's hostname. The CLI accepts no options other than
`-h`/`--help`; sites and output location are configured only through `.env`.

## Development

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

See [the documentation](docs/index.rst), [contribution guidelines](CONTRIBUTING.md),
and [license](LICENSE.md) for more information.
