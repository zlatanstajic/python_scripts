Installation Guide
===================

System Requirements
-------------------

* Python 3.10 or higher
* pip (Python package manager)
* Virtual environment support (venv)

Optional Dependencies
---------------------

* ``xclip`` or ``xsel`` - For clipboard support on Linux systems
* ``ffmpeg`` - For video and image splicing scripts
* Playwright Chromium build - For the website screenshot script
* ``git`` - For git-related scripts

Installation Steps
------------------

1. Clone the Repository
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone <repository-url>
   cd python_scripts

2. Create a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python3 -m venv .venv

3. Activate the Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Linux/macOS:

.. code-block:: bash

   source .venv/bin/activate

On Windows (Command Prompt):

.. code-block:: cmd

   .venv\Scripts\activate

On Windows (PowerShell):

.. code-block:: powershell

   .venv\Scripts\Activate.ps1

4. Install Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

Install runtime dependencies:

.. code-block:: bash

   pip install -r requirements.txt

This installs the Markdown and WeasyPrint packages required by the CV
generator, the Playwright package required by the screenshot script, and
the dependencies used by the other scripts.

Playwright needs a Chromium build that ``pip`` does not download. Install it
once per machine before running the screenshot script; it is a separate
download of several hundred megabytes:

.. code-block:: bash

   playwright install chromium

Install development dependencies (for testing and contributing):

.. code-block:: bash

   pip install -r requirements-dev.txt

**Alternative: Install using pyproject.toml (PEP 621)**

This project uses ``pyproject.toml`` for configuration and dependency management:

.. code-block:: bash

   # Install with development dependencies using extras
   pip install -e ".[dev]"

   # Install only runtime dependencies
   pip install -e .

This approach is recommended for new installations as it follows modern Python packaging standards.

5. (Optional) Install Pre-commit Hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   chmod +x setup/install-pre-commit.py
   python3 setup/install-pre-commit.py

This will install git hooks that automatically run:

* ``isort`` - Import sorting
* ``black`` - Code formatting
* ``flake8`` - Linting
* ``mypy`` - Type checking
* ``pytest`` - Testing

Linux-Specific Setup
--------------------

**For Clipboard Support:**

If you plan to use scripts with clipboard functionality, install clipboard tools:

.. code-block:: bash

   # For Debian/Ubuntu:
   sudo apt-get install xclip

   # For Fedora:
   sudo dnf install xclip

   # For macOS (with Homebrew):
   brew install xclip

**For Video/Image Processing:**

For scripts that splice images or videos:

.. code-block:: bash

   # For Debian/Ubuntu:
   sudo apt-get install ffmpeg

   # For Fedora:
   sudo dnf install ffmpeg

   # For macOS (with Homebrew):
   brew install ffmpeg

**For Website Screenshots:**

The screenshot script drives a headless Chromium build that Playwright
downloads separately from the Python packages:

.. code-block:: bash

   playwright install chromium

   # Install the shared libraries Chromium needs (Debian/Ubuntu):
   sudo playwright install-deps chromium

Troubleshooting
---------------

**Import Errors After Installation**

If you encounter import errors, ensure your virtual environment is activated:

.. code-block:: bash

   source .venv/bin/activate
   pip install -r requirements.txt

**Permission Denied on Scripts**

Some scripts require sudo privileges for certain operations (e.g., ``backup.py``, ``php_switch.py``).
Ensure your user has proper sudo access or the scripts may fail.

Online Documentation
--------------------

This project's documentation is automatically deployed to GitHub Pages on
each push to the ``master`` branch.

**To access the online documentation:**

1. Visit the GitHub repository: https://github.com/zlatanstajic/python_scripts
2. Go to the **Pages** section in the repository settings
3. The documentation will be deployed at: ``https://zlatanstajic.github.io/python_scripts/``

**Documentation is built and deployed automatically when:**

* Code is pushed to the ``master`` branch
* Documentation files in ``docs/`` are modified
* Source code in ``src/`` or ``scripts/`` is modified
* Project configuration (``pyproject.toml``) is changed

The current CI/CD pipeline ensures:

* Documentation is always up-to-date with the latest code
* Code quality checks pass before deployment
* All tests pass successfully
* Type checking and security scanning complete without errors

**Clipboard Not Working**

If clipboard functionality isn't working on Linux:

1. Check if ``xclip`` or ``xsel`` is installed
2. Ensure your display server is running properly (X11 or Wayland)
3. Try manually copying/pasting instead of using clipboard functions

**FFmpeg Not Found**

If video/image splicing scripts fail:

1. Verify ffmpeg is installed: ``which ffmpeg``
2. Install ffmpeg using your package manager (see Linux-Specific Setup above)
3. Ensure ffmpeg is in your system PATH

**Chromium Browser Not Found**

If the screenshot script reports a missing executable or a failure to launch
the browser:

1. Download the browser bundle: ``playwright install chromium``
2. Install the shared libraries Chromium needs:
   ``sudo playwright install-deps chromium``
3. Verify the Python package is installed in the active environment:
   ``pip show playwright``

Environment Configuration
---------------------------

Create a ``.env`` file in the project root to configure scripts:

.. code-block:: bash

   cp .env.example .env
   # Edit .env with your configuration

Each script documents its required environment variables in the documentation and README.

Updating Dependencies
---------------------

To update all dependencies to their latest versions:

.. code-block:: bash

   pip install --upgrade -r requirements.txt
   pip install --upgrade -r requirements-dev.txt

To update a specific package:

.. code-block:: bash

   pip install --upgrade <package-name>
