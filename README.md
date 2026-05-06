# Python Scripts

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> A collection of automation scripts written in Python for various tasks.

## Table of Contents

* [Project Overview](#project-overview)
* [Requirements](#requirements)
* [How to Install](#how-to-install)
* [Project Configuration](#project-configuration)
* [Running Tests](#running-tests)
* [Documentation](#documentation)
* [CI/CD Pipeline](#cicd-pipeline)
* [Setting Up Aliases (Optional)](#setting-up-aliases-optional)
* [Available Scripts](#available-scripts)
  * [Generate password](#generate-password)
  * [Switch PHP version](#switch-php-version)
  * [Development setup](#development-setup)
  * [Backup files](#backup-files)
  * [Copy changed files between git commits](#copy-changed-files-between-git-commits)
  * [Restore VS Code folder](#restore-vs-code-folder)
  * [Hash and Move Filenames](#hash-and-move-filenames)
  * [Splice Images](#splice-images)
  * [Splice Videos](#splice-videos)
* [Contributing](#contributing)
* [License](#license)

## Project Overview

This repository contains Python scripts designed to automate common tasks and improve productivity. Each script is standalone and can be run from the command line.

## Requirements

* Python 3.10+
* pip
* [pyperclip](https://pypi.org/project/pyperclip/) (for clipboard functionality)
* [python-dotenv](https://pypi.org/project/python-dotenv/) (for `.env` support)
* **Linux:** For clipboard support, you may need to install `xclip` or `xsel` (see notes below).

All required Python packages are listed in [`requirements.txt`](requirements.txt).

[⬆ back to top](#table-of-contents)

## How to Install

1. **Clone the repository:**

   ```bash
   git clone https://github.com/zlatanstajic/python_scripts.git
   cd python_scripts
   ```

2. **Create a virtual environment:**

   ```bash
   python3 -m venv .venv
   ```

3. **Activate the virtual environment:**

   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

5. **Install development dependencies (optional):**

   If you plan to run tests or contribute to the project, install the development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

6. **Install pre-commit hooks (optional):**

    ```bash
    chmod +x setup/install-pre-commit.py
    python3 ./setup/install-pre-commit.py
    ```

**Note:**  
For clipboard support on Linux, you may need to install `xclip` or `xsel`:

```bash
sudo apt-get install xclip
# or
sudo apt-get install xsel
```

## Project Configuration

This project uses **PEP 621 compliant `pyproject.toml`** for dependency and tool configuration. All project metadata, dependencies, and tool settings are centralized in [`pyproject.toml`](pyproject.toml).

**Key Configuration Details:**

- **Python Version**: 3.10+
- **Build System**: setuptools with wheel backend
- **Core Dependencies**: pyperclip, python-dotenv, pillow
- **Development Tools Configuration**:
  - **Black**: Line length 88, Python 3.10+
  - **isort**: Black-compatible profile
  - **pytest**: Test discovery and coverage reporting
  - **mypy**: Type checking with Python 3.10+ compatibility
  - **bandit**: Security scanning with high-confidence filtering
  - **Sphinx**: Documentation generation (see docs/ directory)

**Install with optional development dependencies:**

```bash
# Install with dev dependencies using extras syntax
pip install -e ".[dev]"
```

[⬆ back to top](#table-of-contents)

## Running Tests

To run the test suite, first install the development dependencies, then execute the tests:

```bash
# Install development dependencies (includes pytest)
pip install -r requirements-dev.txt

# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Run only integration tests
python -m pytest tests/test_integration_*.py -v
```

[⬆ back to top](#table-of-contents)

## Documentation

Comprehensive documentation is available in the `docs/` directory and includes:

### Online Documentation

This project's documentation is automatically built and deployed to GitHub Pages on every push to the main branch:

**View Online Documentation:** https://zlatanstajic.github.io/python_scripts/

The documentation is built and deployed automatically when:
- Code is pushed to `main` or `master` branch
- Documentation files in `docs/` are modified
- Source code in `src/` or `scripts/` is modified
- Project configuration changes

See [CI/CD Pipeline Documentation](docs/cicd.rst) for details on the automated deployment workflow.

### Building Documentation Locally

```bash
# Install Sphinx documentation tools
pip install -r requirements-dev.txt

# Build HTML documentation
cd docs
make html

# Open in browser (Linux/macOS)
open _build/html/index.html

# Open in browser (Windows)
start _build/html/index.html
```

### Documentation Structure

* **[Installation Guide](docs/installation.rst)** - Detailed setup instructions
* **[Usage Guide](docs/usage_guide.rst)** - How to run tests, code quality checks, and scripts
* **[Examples](docs/examples.rst)** - Real-world use cases and workflows
* **[API Reference](docs/api_reference.rst)** - Complete API documentation for all modules
* **[Contributing Guide](docs/contributing.rst)** - Guidelines for contributing to the project
* **[CI/CD Pipeline](docs/cicd.rst)** - Automated testing, code quality checks, and documentation deployment

### Online Documentation

For a rendered version of the documentation, see the [docs/](docs/index.rst) directory.

[⬆ back to top](#table-of-contents)

## CI/CD Pipeline

This project uses **GitHub Actions** for automated continuous integration and continuous deployment:

### Automated Workflows

**1. Deploy Documentation** (`.github/workflows/deploy-docs.yml`)
- Builds Sphinx documentation on every push to main branch
- Automatically deploys to GitHub Pages
- Triggers on changes to docs, source code, or configuration

**2. Code Quality & Testing** (`.github/workflows/ci.yml`)
- Runs across Python 3.10, 3.11, and 3.12
- Performs linting (flake8), import checking (isort), code formatting (black)
- Type checking (mypy) and security scanning (bandit)
- Executes full test suite with coverage reporting
- Uploads coverage metrics to Codecov

### Automated Checks Before Each Commit

All quality checks run automatically via pre-commit hooks:

```bash
# Install pre-commit hooks
python3 setup/install-pre-commit.py

# Checks run automatically on: git commit
# Includes: isort, black, flake8, bandit, mypy, pytest
```

### View Workflow Status

- **GitHub Actions Tab:** Check workflow runs and logs in the repository
- **Status Badges:** Visible on README and pull requests
- **Coverage:** Track code coverage trends at Codecov.io

For detailed information, see [CI/CD Pipeline Documentation](docs/cicd.rst).

[⬆ back to top](#table-of-contents)

## Setting Up Aliases (Optional)

To make running these scripts even easier, you can set up shell aliases in your `~/.bashrc`, `~/.zshrc`, or other shell configuration file. This allows you to run scripts with a simple command from anywhere.

**Example:**

```bash
# Add these lines to your ~/.bashrc or ~/.zshrc
alias generate_password='python3 /path/to/python_scripts/scripts/generate_password.py'
alias php_switch='python3 /path/to/python_scripts/scripts/php_switch.py'
alias dev_setup='python3 /path/to/python_scripts/scripts/dev_setup.py'
alias backup='python3 /path/to/python_scripts/scripts/backup.py'
alias git_copy='python3 /path/to/python_scripts/scripts/git_copy.py'
alias restore_vscode='python3 /path/to/python_scripts/scripts/restore_vscode_folder.py'
```

After editing your shell config, reload it:

```bash
source ~/.bashrc
# or
source ~/.zshrc
```

Now you can run, for example, `generate_password -l 16` or `git_copy` from any directory.

[⬆ back to top](#table-of-contents)

## Available Scripts

* [Generate password](#generate-password)
* [Switch PHP version](#switch-php-version)
* [Development setup](#development-setup)
* [Backup files](#backup-files)
* [Copy changed files between git commits](#copy-changed-files-between-git-commits)
* [Restore VS Code folder](#restore-vs-code-folder)
* [Hash and Move Filenames](#hash-and-move-filenames)
* [Splice Images](#splice-images)
* [Splice Videos](#splice-videos)

[⬆ back to top](#table-of-contents)

---

<details>
<summary>

### Generate password

</summary>

* **File:** [`scripts/generate_password.py`](scripts/generate_password.py)
* **Parameters:** Optional (`-l`, `--length`)
* **Description:** Generate a strong and secure password. The password is automatically copied to your clipboard.

**Notes:**
- **Password length must be at least 8 and divisible by 4** (e.g., 8, 12, 16, 20, ...).
- Uses `pyperclip` to copy the password to your clipboard. On Linux, you may need to install `xclip` or `xsel`.
- Passwords contain lowercase, uppercase, digits, and special characters.

**Usage:**

```bash
# Show help
python3 scripts/generate_password.py --help

# Generate password with 20 characters (default)
python3 scripts/generate_password.py

# Generate password with 16 characters
python3 scripts/generate_password.py -l 16

# Generate and use in a command
PASSWORD=$(python3 scripts/generate_password.py 2>&1 | head -1)
echo $PASSWORD
```

**Example output:**
```
Generated password: aB3@kL9!mQ2$rT5^zX8%
Password copied to clipboard!
```

**Common Use Cases:**

1. **Generate password for new account:**

   ```bash
   python3 scripts/generate_password.py -l 32
   # Paste the generated password into the account creation form
   ```

2. **Batch generation:**

   ```bash
   for i in {1..5}; do
       echo "Password $i:"
       python3 scripts/generate_password.py
   done
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Switch PHP version

</summary>

* **File:** [`scripts/php_switch.py`](scripts/php_switch.py)
* **Parameters:** Optional (`-v`, `--version`)
* **Description:** Switch between installed PHP versions using `update-alternatives`. The script only allows switching to a version that is already installed on your system.

**Requirements:**
- Must be run on a system using `update-alternatives` for PHP (e.g., Debian/Ubuntu).
- Requires `sudo` privileges to switch PHP versions.

**Usage:**

```bash
# Show help
python3 scripts/php_switch.py --help

# List installed PHP versions and interactively select one
python3 scripts/php_switch.py

# Switch to a specific PHP version (e.g., 8.3)
python3 scripts/php_switch.py -v 8.3
```

**Features:**
- Lists all installed PHP versions.
- Shows the currently set PHP version.
- Prevents switching if the selected version is already set.
- Displays the PHP version after switching.
- Handles user interruptions (`Ctrl+C`, `Ctrl+D`) gracefully.

**Example output:**
```
Installed PHP versions:
1. PHP 8.3 (/usr/bin/php8.3)
2. PHP 8.2 (/usr/bin/php8.2)
Select the PHP version to switch to (by number): 1
Currently set PHP version: /usr/bin/php8.2
✅ Successfully switched to PHP version at /usr/bin/php8.3.
Current PHP version:
PHP 8.3.7 (cli) (built: Jun  1 2025 12:00:00) ( NTS )
...
```

**Common Use Cases:**

1. **Quick switch for a specific project:**

   ```bash
   # Project requires PHP 8.0
   python3 scripts/php_switch.py -v 8.0
   cd ~/projects/my-project
   composer install
   ./vendor/bin/phpunit
   ```

2. **Test compatibility across multiple PHP versions:**

   ```bash
   #!/bin/bash
   VERSIONS=(7.4 8.0 8.1 8.2 8.3)
   
   for version in "${VERSIONS[@]}"; do
       python3 scripts/php_switch.py -v "$version"
       php -v
       composer test
   done
   ```

3. **Switch back to development version after deployment:**

   ```bash
   # Deploy with PHP 7.4
   python3 scripts/php_switch.py -v 7.4
   ./deploy.sh
   
   # Switch back to development version
   python3 scripts/php_switch.py -v 8.3
   ```

4. **Check which extensions are available in a PHP version:**

   ```bash
   python3 scripts/php_switch.py -v 8.0
   php -m | grep -E 'pdo|json|curl'
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Development setup

</summary>

* **File:** [`scripts/dev_setup.py`](scripts/dev_setup.py)
* **Parameters:** `--number` (required), `--name` (required)
* **Description:** This script helps set up a new Git branch for a development task based on an issue number and title. It allows you to select a base branch, creates a new branch with a formatted name, checks it out, optionally pushes it to the remote repository, and copies a formatted commit message to the clipboard.

**Environment Variables:**  
You can configure the script using a `.env` file (see `.env.example`):

- `BRANCH_PREFIX` (default: `issues`)
- `REQUEST_PREFIX` (default: `refs:`)
- `ISSUE_BASE_PATH` (used for issue link in the commit message; if set to `https://github.com/zlatanstajic`, the script will auto-detect the repo name from the current folder and construct the full repo URL for the issue link)

**Usage:**

```bash
# Show help
python3 scripts/dev_setup.py --help

# Create and push a new branch for issue 123 with title "Fix login bug"
python3 scripts/dev_setup.py --number 123 --name "Fix login bug"
```

**Features:**
- Checks if you are in a Git repository.
- Lets you select the base branch interactively.
- Creates a new branch with a formatted name.
- Optionally pushes the branch to remote.
- Copies a formatted commit message to your clipboard (requires `pyperclip` and clipboard support).
  - If `ISSUE_BASE_PATH` is set to a GitHub user URL (e.g., `https://github.com/username`), the script will append the current folder name as the repo name and use it for the issue link.
  - If not, only the name is copied (and printed).
- Cleans up if you cancel before pushing.
- Handles user interruptions (`Ctrl+C`, `Ctrl+D`) gracefully.
- Exits with an error if required arguments are missing.

**Example output:**
```
Located in directory: myproject

Available branches:
1. main
2. develop
3. feature/old-task

Select the branch number to create new branch from: 2
Will create branch issues/123_fix_login_bug from develop

Do you wish to proceed? [y/n]: y

Will push local branch to remote
Do you wish to proceed? [y/n]: y

Copied message description to the clipboard:

Based on issues [#123](https://github.com/username/myproject/issues/123)

Copied message name info to the clipboard:

refs: #123 Fix login bug
```

**Note:**  
For clipboard support, you may need to install `xclip` or `xsel` on Linux.

**Common Use Cases:**

1. **Start a new feature from GitHub issue:**

   ```bash
   # Create branch and get message ready for commit
   python3 scripts/dev_setup.py --number 456 --name "Add user authentication"
   # Branch created: issues/456_add_user_authentication
   # Commit message copied: "Based on issues [#456](https://...)"
   ```

2. **Track bug fix with proper branch naming:**

   ```bash
   python3 scripts/dev_setup.py --number 789 --name "Fix login validation"
   # Creates issues/789_fix_login_validation
   # Ready to commit with reference to issue
   ```

3. **Push branch immediately and start work:**

   ```bash
   python3 scripts/dev_setup.py --number 321 --name "Update documentation" << EOF
   2
   y
   y
   EOF
   # Non-interactive mode: select branch 2, create, and push
   ```

4. **Create multiple related branches:**

   ```bash
   for issue_id in 111 222 333; do
       python3 scripts/dev_setup.py --number "$issue_id" --name "Feature part $issue_id"
   done
   # Creates multiple related feature branches
   ```

5. **Pre-push verification:**

   ```bash
   python3 scripts/dev_setup.py --number 555 --name "Refactor payment module"
   # Review branch name is correct and message is formatted
   # Before pushing, run tests
   python -m pytest tests/ -v
   # Then push if tests pass
   git push origin issues/555_refactor_payment_module
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Backup files

</summary>

* **File:** [`scripts/backup.py`](scripts/backup.py)
* **Parameters:** None (use `-h` for help)
* **Description:** Backup important files, folders, and environment files from your system to a specified backup location. All paths and backup options are configured via the `.env` file.

**Environment Variables:**  
Configure backup sources and destinations in your `.env` file (see `.env.example`):

- `BACKUP_LOCATION`: Destination directory for backups.
- `SYSTEM_DESTINATION_FOLDER_NAME`: Name for the system backup folder.
- `SYSTEM_SOURCE_PATHS`: Comma-separated list of system files to back up.
- `VSCODE_DESTINATION_FOLDER_NAME`: Name for the VS Code backup folder.
- `VSCODE_SOURCE_PATHS`: Comma-separated list of VS Code settings/snippets to back up.
- `PROJECTS_DESTINATION_FOLDER_NAME`: Name for the projects backup folder.
- `PROJECTS_SOURCE_PATHS`: Comma-separated list of project directories to back up (absolute paths).
- `DEPLOYMENTS_DESTINATION_FOLDER_NAME`: Name for the deployments backup folder.
- `DEPLOYMENT_SOURCE_PATHS`: Comma-separated list of deployment directories to back up (absolute paths).

**Usage:**

```bash
# Show help
python3 scripts/backup.py -h

# Run backup
python3 scripts/backup.py
```

**Features:**
- Reads all configuration from `.env` file.
- Backs up system files, VS Code settings, project environment files, and deployment folders.
- For each project in `PROJECTS_SOURCE_PATHS`, backs up `.env` or `.env.rb` if present, and also backs up the `.vscode` folder if it exists.
- Uses `sudo` privileges to create/remove backup directories if needed.
- Handles permission errors gracefully.
- Handles user interruptions (`Ctrl+C`, `Ctrl+D`) gracefully.
- Prints errors for any files or folders that could not be copied.

**Example .env settings:**
```env
BACKUP_LOCATION="/home/your-username/Documents/backup/automated"
SYSTEM_DESTINATION_FOLDER_NAME="system"
SYSTEM_SOURCE_PATHS="/home/your-username/.bashrc,/home/your-username/.gitconfig,/etc/hosts"
VSCODE_DESTINATION_FOLDER_NAME="vscode"
VSCODE_SOURCE_PATHS="/home/your-username/.config/Code/User/settings.json,/home/your-username/.config/Code/User/snippets/global-snippets.code-snippets"
PROJECTS_DESTINATION_FOLDER_NAME="environments"
PROJECTS_SOURCE_PATHS="/var/www/project-one,/var/www/project-two"
DEPLOYMENTS_DESTINATION_FOLDER_NAME="deployments"
DEPLOYMENT_SOURCE_PATHS="/var/www/project-one/deploy,/var/www/project-two/deploy"
```

**Example output:**
```
Completed all backup steps.
```

**Common Use Cases:**

1. **Regular daily backups of critical configuration:**

   ```bash
   # Add to crontab to run daily at 2 AM
   0 2 * * * /home/username/python_scripts/scripts/backup.py
   
   # Or with logging
   0 2 * * * /home/username/python_scripts/scripts/backup.py >> ~/.backup.log 2>&1
   ```

2. **Backup before major system updates:**

   ```bash
   python3 scripts/backup.py
   echo "Backup complete. Ready for system update."
   sudo apt update && sudo apt upgrade -y
   ```

3. **Restore from backup after corrupted configuration:**

   ```bash
   # After running backup
   cp -r ~/Documents/backup/automated/vscode/* ~/.config/Code/User/
   # Or restore specific settings
   cp ~/Documents/backup/automated/system/.bashrc ~
   ```

4. **Selective backup of only VS Code settings:**

   ```bash
   # Edit .env to include only VSCODE_SOURCE_PATHS
   # Then run:
   python3 scripts/backup.py
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Copy changed files between git commits

</summary>

* **File:** [`scripts/git_copy.py`](scripts/git_copy.py)
* **Parameters:** Optional (`start_commit_hash`, `end_commit_hash`, `target_directory_path`)
* **Description:** Copy all files and folders changed between two git commits to a target directory, zip the result (with a timestamp), and delete the copied folder. The `.vscode` folder is always included if it exists.

**Environment Variables:**  
Configure the default target directory in your `.env` file (see `.env.example`):

- `TARGET_DIRECTORY_PATH`: Base directory for copied files.

**Usage:**

```bash
# Show help
python3 scripts/git_copy.py --help

# Copy changed files between the last two commits (default)
python3 scripts/git_copy.py

# Specify custom commit hashes and/or target directory
python3 scripts/git_copy.py <start_commit_hash> <end_commit_hash> <target_directory_path>
```

**Features:**
- Uses the penultimate and last git commit hashes as defaults.
- Copies all files changed between the two commits to the target directory.
- Always copies the `.vscode` folder if it exists.
- Zips the copied folder with a timestamp in the filename.
- Deletes the copied folder after zipping.
- Handles user interruptions (`Ctrl+C`, `Ctrl+D`) gracefully.
- Prints warnings for any files that could not be copied.

**Example output:**
```
Using default start_commit_hash (penultimate): 123abc456def
Using default end_commit_hash (last): 789ghi012jkl
Current directory: myproject
Files copied to /home/your-username/Documents/git_copy/myproject directory
.vscode folder copied to /home/your-username/Documents/git_copy/myproject/.vscode
Zipping folder /home/your-username/Documents/git_copy/myproject to /home/your-username/Documents/git_copy/myproject_20250619_153000.zip
Zipped folder created at /home/your-username/Documents/git_copy/myproject_20250619_153000.zip
Deleted copied folder: /home/your-username/Documents/git_copy/myproject
```

**Common Use Cases:**

1. **Create deployment package from latest changes:**

   ```bash
   cd ~/projects/my-app
   python3 scripts/git_copy.py
   # Creates: ~/Documents/git_copy/my-app_TIMESTAMP.zip
   # Ready to upload to server
   ```

2. **Copy changes between specific commits for review:**

   ```bash
   # Get commit hashes
   git log --oneline | head -10
   
   # Copy files between two commits
   python3 scripts/git_copy.py 123abc456 789def012
   ```

3. **Create backup of recent changes:**

   ```bash
   # Copy last 5 commits worth of changes
   python3 scripts/git_copy.py \
     $(git log --oneline -6 | tail -1 | cut -d' ' -f1) \
     $(git log --oneline -1 | cut -d' ' -f1)
   ```

4. **Archive for client delivery:**

   ```bash
   python3 scripts/git_copy.py
   # The created zip includes only the changed files + .vscode settings
   # Perfect for sending to clients without entire project
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Restore VS Code folder

</summary>

* **File:** [`scripts/restore_vscode_folder.py`](scripts/restore_vscode_folder.py)
* **Parameters:** None (use `-h` or `--help` for help)
* **Description:** Restores the `.vscode` folder from a backup location to the current directory if it does not already exist. The script uses environment variables from the `.env` file to determine the backup location and project folder structure.

**Environment Variables:**  
Configure the backup source in your `.env` file:

- `BACKUP_LOCATION`: Base directory where backups are stored.
- `PROJECTS_DESTINATION_FOLDER_NAME`: Name of the folder under the backup location containing project backups.

**Usage:**

```bash
# Show help
python3 scripts/restore_vscode_folder.py --help

# Restore the .vscode folder in the current directory (if missing)
python3 scripts/restore_vscode_folder.py
```

**Features:**
- Checks if the `.vscode` folder exists in the current directory. If it does, the script exits with a message.
- If the folder does not exist, attempts to copy it from the backup location:  
  `$BACKUP_LOCATION/$PROJECTS_DESTINATION_FOLDER_NAME/<current_folder_name>/.vscode`
- Prints a message if the backup is missing or if the copy fails.
- Handles user interruptions (`Ctrl+C`, `Ctrl+D`) gracefully.
- Prints a success message when the folder is restored.

**Example output:**
```
.vscode folder already exists in /var/www/html/open-source/python_scripts. Nothing to do.
```
or
```
.vscode folder restored from backup: /home/your-username/Documents/backup/automated/projects/python_scripts/.vscode
```
or
```
No backup found at /home/your-username/Documents/backup/automated/projects/python_scripts/.vscode. Cannot restore .vscode folder.
```

**Common Use Cases:**

1. **Restore settings when cloning a project:**

   ```bash
   git clone https://github.com/user/myproject.git
   cd myproject
   python3 scripts/restore_vscode_folder.py
   # .vscode folder is now restored from backup
   code .
   ```

2. **Setup new development environment with consistent settings:**

   ```bash
   # Clone multiple projects
   for project in project-a project-b project-c; do
       git clone https://github.com/user/$project.git
       cd $project
       python3 scripts/restore_vscode_folder.py
       cd ..
   done
   ```

3. **Restore after accidental deletion:**

   ```bash
   # Oops, deleted .vscode folder!
   rm -rf .vscode
   
   # Restore it
   python3 scripts/restore_vscode_folder.py
   ```

4. **Verify backup exists before deployment:**

   ```bash
   cd ~/projects/production-app
   python3 scripts/restore_vscode_folder.py
   
   if [ -d .vscode ]; then
       echo "Settings restored, ready for deployment"
   else
       echo "Warning: Could not restore .vscode folder"
   fi
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Hash and Move Filenames

</summary>

* **File:** [`scripts/hash_filenames.py`](scripts/hash_filenames.py)
* **Parameters:** Optional (`-d`, `--directory`, `-v`, `--verbose`, `-m`, `--move`)
* **Description:** Renames files in a directory to random hash-based filenames (if not already hashed) and optionally moves hashed files into batch folders.

**Environment Variables:**  
Configure file extensions to process in your `.env` file:

- `HASH_FILENAMES_FILE_EXTENSIONS`: Comma-separated list of file extensions to hash (e.g., `.jpg,.png,.mp4`).

**Usage:**

```bash
# Show help
python3 scripts/hash_filenames.py --help

# Hash filenames in the current directory
python3 scripts/hash_filenames.py

# Hash filenames in a specific directory with verbose output
python3 scripts/hash_filenames.py -d /path/to/dir -v

# Hash and then move hashed files into batch folders
python3 scripts/hash_filenames.py -d /path/to/dir -m
```

**Features:**
- Reads file extensions to process from `.env` (`HASH_FILENAMES_FILE_EXTENSIONS`).
- Renames files to a random 10-character hash if not already hashed.
- Skips files that are already hashed or if a hash collision would overwrite an existing file.
- Optionally moves hashed files into folders named `hashed_001`, `hashed_002`, etc., in batches of 100.
- Cleans up any empty `hashed_` folders after moving.
- Supports verbose output for all operations.

**Example .env setting:**
```env
HASH_FILENAMES_FILE_EXTENSIONS=.jpg,.jpeg,.png,.gif,.mp4,.mov
```

**Example output:**
```
Renamed: /path/to/dir/photo.jpg -> /path/to/dir/aB3kLm9QzX.jpg
Moved: /path/to/dir/aB3kLm9QzX.jpg -> /path/to/dir/hashed_001/aB3kLm9QzX.jpg
Deleted empty folder:
```

**Common Use Cases:**

1. **Rename photo batch before upload:**

   ```bash
   cd ~/Desktop/photos
   python3 scripts/hash_filenames.py -v
   # All photos renamed to random hashes
   # Perfect for anonymous uploads
   ```

2. **Organize large media library into batches:**

   ```bash
   cd /media/archive
   python3 scripts/hash_filenames.py -m -v
   # Files renamed to hashes
   # Automatically organized into hashed_001/, hashed_002/, etc. (100 files per folder)
   ```

3. **Process a specific directory without changing current location:**

   ```bash
   python3 scripts/hash_filenames.py -d ~/Downloads -m -v
   # Files will be organized into batch folders immediately
   ```

4. **Verify hash status without modifying files:**

   ```bash
   # Use verbose to see which files are already hashed
   python3 scripts/hash_filenames.py -d ~/photos -v
   # Only processes files matching extensions in .env
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Splice Images

</summary>

* **File:** [`scripts/splice_images.py`](scripts/splice_images.py)
* **Parameters:** Optional (`-i`, `--images`, `-o`, `--output`, `--width`, `--height`, `-n`, `--number`)
* **Description:** Horizontally splices multiple images together using ffmpeg. You can specify images directly or let the script pick random images from the current directory. Output is saved in a `spliced_images` folder, and originals are moved to `standalone_images`.

**Environment Variables:**  
Configure file extensions to process in your `.env` file:

- `SPLICE_IMAGES_FILE_EXTENSIONS`: Comma-separated list of image file extensions (e.g., `.jpg,.png,.jpeg`).

**Usage:**

```bash
# Show help
python3 scripts/splice_images.py --help

# Splice 3 random images from the current directory
python3 scripts/splice_images.py -n 3

# Splice specific images and set output filename
python3 scripts/splice_images.py -i img1.jpg img2.jpg img3.jpg -o result.jpg

# Splice images with a specific height
python3 scripts/splice_images.py -n 2 --height 600
```

**Features:**
- Reads valid image extensions from `.env` (`SPLICE_IMAGES_FILE_EXTENSIONS`).
- Splices images horizontally using ffmpeg.
- Can select random images from a directory or use specified files.
- Output is saved in `spliced_images/` with a random hash filename (or your chosen name).
- Original images are moved to `standalone_images/` after processing.
- Handles missing environment variables and errors gracefully.

**Example .env setting:**
```env
SPLICE_IMAGES_FILE_EXTENSIONS=.jpg,.jpeg,.png
```

**Example output:**
```
Moved img1.jpg to standalone_images/img1.jpg
Moved img2.jpg to standalone_images/img2.jpg
Moved img3.jpg to standalone_images/img3.jpg
```

**Common Use Cases:**

1. **Create photo collage from random images:**

   ```bash
   cd ~/Desktop/vacation_photos
   python3 scripts/splice_images.py -n 4 --height 800
   # Creates spliced_images/HASH.jpg with 4 random vacation photos
   ```

2. **Combine specific images for presentation:**

   ```bash
   python3 scripts/splice_images.py \
     -i logo.png header.png footer.png \
     -o presentation_header.png
   # Creates a custom header combining 3 specific images
   ```

3. **Create product showcase from product images:**

   ```bash
   cd ~/marketing/product_images
   python3 scripts/splice_images.py -n 3 -o product_showcase.jpg --width 1200 --height 400
   # Creates a product showcase banner
   ```

4. **Batch process multiple sets:**

   ```bash
   for folder in ~/images/set1 ~/images/set2 ~/images/set3; do
       cd "$folder"
       python3 scripts/splice_images.py -n 5
   done
   # Creates spliced images in each set's folder
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

<details>
<summary>

### Splice Videos

</summary>

* **File:** [`scripts/splice_videos.py`](scripts/splice_videos.py)
* **Parameters:** Required (`-i`, `--input_video`, `-d`, `--duration`), Optional (`-s`, `--segment`)
* **Description:** Randomly splices together short segments from a source video to create a new video of a specified total duration. Segments are chosen from the middle 80% of the video (ignoring the first and last 10%), and the script ensures the output does not exceed 1 GB. Uses FFmpeg for segment extraction and concatenation. Existing random clips are reused if present.

**Usage:**

```bash
# Show help
python3 scripts/splice_videos.py --help

# Splice 10 seconds of random 3-second clips from example.mp4
python3 scripts/splice_videos.py -i example.mp4 -d 10

# Splice 30 seconds of random 5-second clips from input.mp4
python3 scripts/splice_videos.py -i input.mp4 -d 30 -s 5
```

**Features:**
- Selects random segments from the input video, skipping the first and last 10%.
- Ensures the output video does not exceed 1 GB (reduces segments if needed).
- Uses FFmpeg for fast segment extraction and concatenation.
- Reuses existing random clips if present in `assets/random_clips/`.
- Prints a detailed report after processing.
- Handles errors and interruptions gracefully.

**Example output:**
```
Input video:       example.mp4
Input duration:    120.00s
Clips generated:   3
Clip duration:     3s each
Output file:       assets/spliced/output_from_example.mp4
Output duration:   9.00s
Output location:   /home/your-username/repos/python_scripts/assets/spliced/output_from_example.mp4
```

**Common Use Cases:**

1. **Create video preview from long recording:**

   ```bash
   # Extract 15 seconds of highlights from 2-hour recording
   python3 scripts/splice_videos.py -i conference.mp4 -d 15 -s 2
   # Creates random 2-second clips totaling approximately 15 seconds
   ```

2. **Generate promotional video from gameplay:**

   ```bash
   cd ~/videos
   python3 scripts/splice_videos.py -i gameplay-1hr.mp4 -d 30 -s 3
   # Creates 30-second promotional video from random 3-second gameplay segments
   ```

3. **Extract highlights from live stream recording:**

   ```bash
   python3 scripts/splice_videos.py -i live_stream.mp4 -d 60 -s 5
   # Creates 60-second highlight reel from random 5-second segments
   ```

4. **Create social media snippet:**

   ```bash
   python3 scripts/splice_videos.py -i long_video.mp4 -d 10
   # Creates 10-second video for TikTok/Shorts from random clips
   # Output file automatically saved to assets/spliced/
   ```

5. **Preview video before importing to editor:**

   ```bash
   python3 scripts/splice_videos.py -i raw_footage.mp4 -d 5 -s 1
   # Quick 5-second preview before committing to full import
   ```

</details>

[⬆ back to available scripts](#available-scripts)

---

[⬆ back to top](#table-of-contents)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

[⬆ back to top](#table-of-contents)

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

[⬆ back to top](#table-of-contents)

---
