# Python Scripts

[![CI](https://github.com/zlatanstajic/python_scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/zlatanstajic/python_scripts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://zlatanstajic.github.io/python_scripts/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> A collection of Python command-line utilities for development setup, backups, file management, media processing, password generation, PHP switching, VS Code restoration, single-page CV generation, and website screenshots.

📖 **Browse the docs:** [zlatanstajic.github.io/python_scripts](https://zlatanstajic.github.io/python_scripts/) (source in [`docs/`](docs/), published via GitHub Pages).

## Table of Contents

- [Install](#install)
- [List of Available Scripts](#list-of-available-scripts)
- [Documentation](#documentation)
- [Testing](#testing)
- [Continuous Integration](#continuous-integration)
- [Contributing](#contributing)
- [License](#license)

---

## Install

Python 3.10 or newer and `pip` are required. Clone the repository and create an isolated environment:

```bash
git clone https://github.com/zlatanstajic/python_scripts.git
cd python_scripts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The scripts run directly from the clone; this project does not install console entry points. For example:

```bash
python scripts/generate_password.py -l 20
```

Copy the example configuration before using a script that reads environment variables, then edit only the settings that script needs:

```bash
cp .env.example .env
```

On Linux, clipboard operations through `pyperclip` may also require `xclip` or `xsel`. The media scripts require `ffmpeg` (and video splicing also uses `ffprobe`); PHP switching requires a system that manages PHP through `update-alternatives` and permission to run it with `sudo`.

The screenshot script also needs a Chromium build that `pip` does not download. Install it once per machine after the requirements are in place; it is a separate download of several hundred megabytes:

```bash
playwright install chromium
```

For tests, documentation, and quality tools, install the development extras instead:

```bash
python -m pip install -e ".[dev]"
```

[⬆ back to top](#table-of-contents)

---

## List of Available Scripts

The repository contains eleven utilities. Run commands from the repository root unless an entry says otherwise.

<details markdown="1">
<summary><strong>Backup</strong> — <a href="scripts/backup.py"><code>scripts/backup.py</code></a></summary>

Backs up configured system files, VS Code files, project metadata, and deployment directories on Linux. Existing destination folders for the system, VS Code, and deployment sections are replaced. For configured projects, `.env`/`.env.rb` contents are represented by keyed HMAC hashes for change detection; `config.json` and `.vscode` content are copied when present.

```text
Show help  : python scripts/backup.py --help
Run backup : python scripts/backup.py

No command-line options other than -h/--help.

Configuration is read from .env (see .env.example):
BACKUP_LOCATION is required. The SYSTEM, VSCODE, PROJECTS and DEPLOYMENT
source-path and destination-folder settings select what is backed up.
ENV_FILES_ZIP_PASSWORD is the project-env HMAC key (default: pa55).
```

</details>

<details markdown="1">
<summary><strong>CV Generator</strong> — <a href="scripts/cv_generator.py"><code>scripts/cv_generator.py</code></a></summary>

Converts a local Markdown CV into an ATS-friendly, single-page A4 PDF. It tries progressively tighter supported render profiles, writes the result atomically, and leaves an existing output untouched if the CV cannot fit on one page. A heading such as `### Role / Company | Dates` is rendered with its dates aligned to the right.

```text
Generate PDF : python scripts/cv_generator.py

This script has no command-line options, including no --help option.
It reads .env from the current working directory:
MARKDOWN_FILE_URL     Local Markdown path or file:// URL (required)
PDF_OUTPUT_LOCATION  Local destination path or file:// URL (required)
```

</details>

<details markdown="1">
<summary><strong>Development Setup</strong> — <a href="scripts/dev_setup.py"><code>scripts/dev_setup.py</code></a></summary>

Interactively selects a local base branch, pulls it, creates an issue branch, optionally pushes that branch to `origin`, and copies issue-aware commit text to the clipboard. If pushing is declined, the newly created branch is deleted and the selected base branch is restored. Issue names cannot contain digits.

```text
Show help   : python scripts/dev_setup.py --help
Create task : python scripts/dev_setup.py -nu 123 -na "Improve readme"

  -nu, --number  Issue number (required)
  -na, --name    Issue name (required)

Optional .env settings (defaults shown):
BRANCH_PREFIX=issues, REQUEST_PREFIX=refs:, ISSUE_BASE_PATH=""
```

</details>

<details markdown="1">
<summary><strong>Generate Password</strong> — <a href="scripts/generate_password.py"><code>scripts/generate_password.py</code></a></summary>

Generates a password containing equal-sized lowercase, uppercase, digit, and punctuation groups, prints it, and attempts to copy it to the clipboard. The requested length must be at least 8 and divisible by 4.

```text
Show help     : python scripts/generate_password.py --help
Default (20)  : python scripts/generate_password.py
Custom length : python scripts/generate_password.py -l 32

  -l, --length  Password length (default: 20)
```

</details>

<details markdown="1">
<summary><strong>Git Copy</strong> — <a href="scripts/git_copy.py"><code>scripts/git_copy.py</code></a></summary>

Copies files changed between two commits, includes `.vscode` when present, creates a timestamped ZIP beside the target directory, and removes the uncompressed copied directory. Run it inside a Git repository with at least two commits. Files deleted at the ending commit cannot be copied and are reported as warnings.

```text
Show help      : python scripts/git_copy.py --help
Use defaults   : python scripts/git_copy.py
Choose range   : python scripts/git_copy.py -s <start> -e <end> -t /tmp/export

  -s, --start_commit_hash      Start commit (default: penultimate commit)
  -e, --end_commit_hash        End commit (default: current HEAD)
  -t, --target_directory_path  Copy destination

When -t is omitted, the destination is
$TARGET_DIRECTORY_PATH/<current-directory-name>; TARGET_DIRECTORY_PATH
is required in .env even when -t is supplied because defaults are resolved
before arguments are parsed.
```

</details>

<details markdown="1">
<summary><strong>Hash Filenames</strong> — <a href="scripts/hash_filenames.py"><code>scripts/hash_filenames.py</code></a></summary>

Recursively renames files with configured extensions to random ten-character names and records original-to-new names in `hash_filenames_mapping.txt`. With `--move`, hashed files are gathered into `hashed_001`, `hashed_002`, and subsequent batches of up to 100 files.

```text
Show help    : python scripts/hash_filenames.py --help
Hash a tree  : python scripts/hash_filenames.py -d /path/to/files -v
Move batches : python scripts/hash_filenames.py -d /path/to/files -m

  -d, --directory  Directory to process (default: current directory)
  -v, --verbose    Report skipped, renamed, moved, and removed items
  -m, --move       Move hashed files into numbered batch folders

HASH_FILENAMES_FILE_EXTENSIONS in .env is required and contains a
comma-separated extension list (see .env.example).
```

</details>

<details markdown="1">
<summary><strong>PHP Switch</strong> — <a href="scripts/php_switch.py"><code>scripts/php_switch.py</code></a></summary>

Lists PHP alternatives registered with `update-alternatives` and switches the active `php` executable. With no version, it prompts for an installed alternative; with a version, it rejects values that are not installed. Switching runs `sudo update-alternatives --set php ...`.

```text
Show help   : python scripts/php_switch.py --help
Interactive : python scripts/php_switch.py
Switch      : python scripts/php_switch.py -v 8.3

  -v, --version  Installed PHP version to activate (optional)
```

</details>

<details markdown="1">
<summary><strong>Restore VS Code Folder</strong> — <a href="scripts/restore_vscode_folder.py"><code>scripts/restore_vscode_folder.py</code></a></summary>

Restores `.vscode` for the current project from `<BACKUP_LOCATION>/<PROJECTS_DESTINATION_FOLDER_NAME>/<current-directory-name>/.vscode`. It exits without changing anything if the current directory already has `.vscode`.

```text
Show help : python scripts/restore_vscode_folder.py --help
Restore   : python scripts/restore_vscode_folder.py

No command-line options other than -h/--help.
BACKUP_LOCATION and PROJECTS_DESTINATION_FOLDER_NAME are required in .env.
```

</details>

<details markdown="1">
<summary><strong>Screenshot</strong> — <a href="scripts/screenshot.py"><code>scripts/screenshot.py</code></a></summary>

Captures one desktop screenshot per configured website with Playwright. Chromium is launched once and each site is opened in a fresh context sized to a 1600x900 viewport at scale factor 1, with animations suppressed and known cookie banners removed before capture. Every site is saved as a 1600x900 JPEG named after its hostname, overwriting the file from the previous run. A failing site is reported and does not stop the others; the exit code is non-zero when any site failed.

```text
Show help     : python scripts/screenshot.py --help
Capture sites : python scripts/screenshot.py

There are no command-line options other than --help.
It reads .env from the current working directory:
SCREENSHOT_SITES       Comma-separated http(s) website URLs (required)
SCREENSHOT_OUTPUT_DIR  Destination directory for the JPEG files
                       (default: ~/Pictures)
```

</details>

<details markdown="1">
<summary><strong>Splice Images</strong> — <a href="scripts/splice_images.py"><code>scripts/splice_images.py</code></a></summary>

Uses `ffmpeg` to scale images to a common height and join them horizontally. Inputs may be supplied explicitly or selected randomly from the current directory. The generated image receives a random name under `spliced_images/`, and processed inputs are moved to `standalone_images/`. The `--output` value currently selects only the output extension; `--width` is accepted but is not currently applied by the scaling filter.

```text
Show help       : python scripts/splice_images.py --help
Choose images   : python scripts/splice_images.py -i a.jpg b.jpg
Random from cwd : python scripts/splice_images.py -n 3 --height 600

  -i, --images   One or more input image paths
  -o, --output   Output filename whose extension will be reused
      --width    Accepted width value (default: 800; currently unused)
      --height   Scale height (default: height of first selected image)
  -n, --number   Number of images to select (default: 2)

SPLICE_IMAGES_FILE_EXTENSIONS in .env is required and contains the valid
comma-separated extensions (see .env.example).
```

</details>

<details markdown="1">
<summary><strong>Splice Videos</strong> — <a href="scripts/splice_videos.py"><code>scripts/splice_videos.py</code></a></summary>

Uses `ffprobe` and `ffmpeg` to extract random, non-overlapping clips from the middle 80% of a video and concatenate them. Input names resolve below `assets/inputs/`; output is written to `assets/spliced/output_from_<input-name>`. If `assets/random_clips/` already contains clips, they are reused instead of regenerated.

```text
Show help : python scripts/splice_videos.py --help
Splice    : python scripts/splice_videos.py -i source.mp4 -d 30 -s 3

  -i, --input_video  Input filename with extension (required)
  -d, --duration     Requested total output duration in seconds (required)
  -s, --segment      Duration of each random clip in seconds (default: 3)

The actual output can be shorter when the input or available unique blocks
cannot satisfy the requested duration. Generated output is capped by a 1 GB
size estimate.
```

</details>

[⬆ back to top](#table-of-contents)

---

## Documentation

The Sphinx documentation includes installation, usage, examples, API reference, contributing, and CI/CD guides. Build it locally after installing the development extras:

```bash
cd docs
make clean
make html
```

Open `docs/_build/html/index.html` in a browser, or use the [published documentation](https://zlatanstajic.github.io/python_scripts/). The deployment workflow rebuilds and deploys the site for matching pushes to `master`. Pull requests targeting `master` build without deploying when they change `docs/**`, `src/**`, or `scripts/**`.

[⬆ back to top](#table-of-contents)

---

## Testing

The [`tests/`](tests/) directory contains unit and integration tests driven by pytest. Development dependencies enable coverage reporting through the settings in [`pyproject.toml`](pyproject.toml).

```bash
# Run the configured suite with verbose output and coverage
python -m pytest

# Run only integration test modules
python -m pytest tests/test_integration_*.py -v

# Run one test module
python -m pytest tests/test_generate_password.py -v
```

Install the repository-local pre-commit hook if you want isort, Black, flake8, Bandit, pydocstyle, mypy, and pytest checks to run before each commit:

```bash
python setup/install-pre-commit.py
```

[⬆ back to top](#table-of-contents)

---

## Continuous Integration

GitHub Actions runs the quality and test jobs across Python 3.10, 3.11, and 3.12. The quality job checks flake8, isort, Black, mypy, and pydocstyle; Bandit runs as an advisory check. The test job runs pytest with coverage and uploads `coverage.xml` to Codecov without making upload failures fatal. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Documentation is built with Sphinx on Python 3.10 and deployed to GitHub Pages after qualifying pushes to `master`. See [`.github/workflows/deploy-docs.yml`](.github/workflows/deploy-docs.yml).

[⬆ back to top](#table-of-contents)

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the supported branch naming convention, pull request guidance, code style, and testing expectations.

[⬆ back to top](#table-of-contents)

---

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.

[⬆ back to top](#table-of-contents)
