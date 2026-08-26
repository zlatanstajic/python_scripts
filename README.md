# Python Scripts

[![CI](https://github.com/zlatanstajic/python_scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/zlatanstajic/python_scripts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://zlatanstajic.github.io/python_scripts/)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776ab.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-0a9edc.svg?logo=pytest&logoColor=white)](https://pytest.org/)

> Two focused Python command-line utilities for rendering a single-page PDF CV
> from Markdown and capturing 1600x900 website screenshots with Playwright.

📖 **Browse the docs:**
[zlatanstajic.github.io/python_scripts](https://zlatanstajic.github.io/python_scripts/)
(source in [`docs/`](docs/), published via GitHub Pages).

The repository's former general automation utilities now live in the sibling
[`shell-scripts`](https://github.com/zlatanstajic/shell-scripts) project.

<img src="assets/img/og-image.png" alt="Python Scripts social preview" width="100%">

## Table of Contents

- [Requirements](#requirements)
- [CV generator](#cv-generator)
- [Website screenshots](#website-screenshots)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

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

[⬆ back to top](#table-of-contents)

---

## CV generator

Set `MARKDOWN_FILE_URL` and `PDF_OUTPUT_LOCATION` in `.env`, then run:

```bash
python scripts/cv_generator.py
```

`MARKDOWN_FILE_URL` may be a local path or `file://` URL. Relative input and
output paths are resolved from the current working directory.

[⬆ back to top](#table-of-contents)

---

## Website screenshots

Set `SCREENSHOT_SITES` to a comma-separated URL list and optionally set
`SCREENSHOT_OUTPUT_DIR` (the default is `~/Pictures`), then run:

```bash
python scripts/screenshot.py
```

The tool runs Chromium headlessly and saves the visible 1600x900 viewport as a
JPEG named from each site's hostname. The CLI accepts no options other than
`-h`/`--help`; sites and output location are configured only through `.env`.

[⬆ back to top](#table-of-contents)

---

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

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md)
for details.

[⬆ back to top](#table-of-contents)
