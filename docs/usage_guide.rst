Usage Guide
===========

Running Scripts
---------------

All scripts can be executed in several ways:

**Method 1: Direct execution**

.. code-block:: bash

   python3 scripts/generate_password.py --help

**Method 2: Module import (after installation)**

.. code-block:: bash

   python3 -m scripts.generate_password --help

**Method 3: Using aliases (optional)**

Add to your shell configuration file (``~/.bashrc``, ``~/.zshrc``, etc.):

.. code-block:: bash

   alias generate_password='python3 /path/to/python_scripts/scripts/generate_password.py'

Then use:

.. code-block:: bash

   generate_password --help

Project Configuration
---------------------

PEP 621 Compliance
~~~~~~~~~~~~~~~~~~

This project uses ``pyproject.toml`` for modern Python packaging and configuration management. This file centralizes:

* **Project metadata**: name, version, description, authors, license
* **Dependencies**: runtime and development dependencies
* **Tool configurations**: black, isort, pytest, mypy, bandit, coverage, flake8

Benefits of PEP 621
^^^^^^^^^^^^^^^^^^^

* Single source of truth for project configuration
* Compatible with modern Python tooling and package managers
* Standardized format across the Python ecosystem
* Easier dependency management and version pinning

Viewing Configuration
^^^^^^^^^^^^^^^^^^^^^

View the ``pyproject.toml`` file to see:

.. code-block:: bash

   cat pyproject.toml

Key sections:

* ``[project]`` - Project metadata and dependencies
* ``[project.optional-dependencies]`` - Development tools
* ``[tool.black]`` - Black formatter configuration
* ``[tool.isort]`` - Import sorting configuration
* ``[tool.pytest.ini_options]`` - Test runner configuration
* ``[tool.mypy]`` - Type checking configuration
* ``[tool.bandit]`` - Security scanner configuration

Common Patterns
---------------

Help Information
~~~~~~~~~~~~~~~~

All scripts support the ``--help`` or ``-h`` flag to show usage information:

.. code-block:: bash

   python3 scripts/backup.py --help

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Many scripts use environment variables from a ``.env`` file for configuration. Always ensure your ``.env`` file exists:

.. code-block:: bash

   # Copy the example file
   cp .env.example .env

   # Edit with your configuration
   nano .env

Verbose Output
~~~~~~~~~~~~~~

Scripts that support verbose output typically use the ``-v`` or ``--verbose`` flag:

.. code-block:: bash

   python3 scripts/hash_filenames.py -v

Testing Scripts
---------------

Before running a script in production, test it:

1. **Test with sample data:**

   .. code-block:: bash

      mkdir -p test_data
      cp sample_file.txt test_data/
      python3 scripts/hash_filenames.py -d test_data/ -v

2. **Run the test suite:**

   .. code-block:: bash

      python3 -m pytest tests/ -v

3. **Check specific script tests:**

   .. code-block:: bash

      python3 -m pytest tests/test_backup.py -v

Running Tests
-------------

Comprehensive Testing
~~~~~~~~~~~~~~~~~~~~~

Run all tests with coverage:

.. code-block:: bash

   python3 -m pytest tests/ -v --cov=src --cov-report=term-missing

Unit Tests
~~~~~~~~~~

Run only unit tests (excludes integration tests):

.. code-block:: bash

   python3 -m pytest tests/test_*.py -v

Integration Tests
~~~~~~~~~~~~~~~~~

Run only integration tests:

.. code-block:: bash

   python3 -m pytest tests/test_integration_*.py -v

Specific Script Tests
~~~~~~~~~~~~~~~~~~~~~

Test a specific script:

.. code-block:: bash

   python3 -m pytest tests/test_backup.py::TestBackupIntegration -v

Code Quality Checks
-------------------

Type Checking
~~~~~~~~~~~~~

Run type checking with mypy:

.. code-block:: bash

   python3 -m mypy src/ scripts/

Code Formatting
~~~~~~~~~~~~~~~

Check code formatting with black:

.. code-block:: bash

   python3 -m black --check .

Auto-format code:

.. code-block:: bash

   python3 -m black .

Import Sorting
~~~~~~~~~~~~~~

Check import order with isort:

.. code-block:: bash

   python3 -m isort --check-only .

Auto-sort imports:

.. code-block:: bash

   python3 -m isort .

Linting
~~~~~~~

Check code style with flake8:

.. code-block:: bash

   python3 -m flake8 src/ scripts/

Pre-commit Checks
~~~~~~~~~~~~~~~~~

Run all checks in sequence (recommended before committing):

.. code-block:: bash

   ./.git/hooks/pre-commit

Script-Specific Usage
---------------------

For detailed usage instructions for specific scripts, see:

* :doc:`Generate Password </api_reference/scripts/generate_password>` - ``scripts/generate_password.py``
* :doc:`PHP Switch </api_reference/scripts/php_switch>` - ``scripts/php_switch.py``
* :doc:`Development Setup </api_reference/scripts/dev_setup>` - ``scripts/dev_setup.py``
* :doc:`Backup Files </api_reference/scripts/backup>` - ``scripts/backup.py``
* :doc:`Git Copy </api_reference/scripts/git_copy>` - ``scripts/git_copy.py``
* :doc:`Restore VS Code </api_reference/scripts/restore_vscode_folder>` - ``scripts/restore_vscode_folder.py``
* :doc:`Hash Filenames </api_reference/scripts/hash_filenames>` - ``scripts/hash_filenames.py``
* :doc:`Splice Images </api_reference/scripts/splice_images>` - ``scripts/splice_images.py``
* :doc:`Splice Videos </api_reference/scripts/splice_videos>` - ``scripts/splice_videos.py``
* :ref:`CV Generator <cv-generator>` - ``scripts/cv_generator.py``
* :ref:`Screenshot <screenshot>` - ``scripts/screenshot.py``

Generate a CV PDF
~~~~~~~~~~~~~~~~~

Configure the Markdown input and PDF output in the ``.env`` file in your
current working directory:

.. code-block:: text

   MARKDOWN_FILE_URL="cv.md"
   PDF_OUTPUT_LOCATION="cv.pdf"

Then run:

.. code-block:: bash

   python3 scripts/cv_generator.py

Use a level-three heading with a final pipe to place experience dates on the
right while preserving inline links and emphasis:

.. code-block:: markdown

   ### [Senior Engineer](https://example.com) / **Example Co** | *2022–Present*

The command prints ``PDF generated successfully.`` when the CV fits on one
page. If it cannot fit using the supported compact profiles, it exits with an
error and leaves any existing output unchanged.

Capture Website Screenshots
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download the Chromium bundle once per machine:

.. code-block:: bash

   playwright install chromium

List the websites in the ``.env`` file in your current working directory.
``SCREENSHOT_SITES`` is required; ``SCREENSHOT_OUTPUT_DIR`` is optional and
defaults to ``~/Pictures``:

.. code-block:: text

   SCREENSHOT_SITES="https://example.com,https://example.org"
   SCREENSHOT_OUTPUT_DIR="/home/your-username/Pictures"

Then run:

.. code-block:: bash

   python3 scripts/screenshot.py

Each site is saved as a 1600x900 JPEG named after its hostname, so
``https://subdomain.example.com/page`` becomes ``subdomain.example.com.jpg``
and every run overwrites the previous file. The command prints an ``[OK]`` or
``[FAILED]`` line per site followed by a ``Finished: N succeeded, M failed.``
summary, and exits with a non-zero status when any site failed.

Error Handling
--------------

Handling Missing Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a script reports a missing module:

.. code-block:: bash

   ModuleNotFoundError: No module named 'PIL'

Install the missing dependency:

.. code-block:: bash

   pip install -r requirements.txt

Handling Permission Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some scripts require elevated privileges. If you see permission errors:

.. code-block:: bash

   PermissionError: [Errno 13] Permission denied

Run with appropriate permissions (the script will use ``sudo`` internally if needed):

.. code-block:: bash

   python3 scripts/backup.py

Debugging
---------

Enable Debug Output
~~~~~~~~~~~~~~~~~~~

Add verbose flags when available:

.. code-block:: bash

   python3 scripts/hash_filenames.py -v

Check Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify environment variables are set correctly:

.. code-block:: bash

   # Display all environment variables used by scripts
   env | grep -E 'BACKUP|PROJECTS|VSCODE|DEPLOYMENT|HASH|SPLICE'

Interpret Error Messages
~~~~~~~~~~~~~~~~~~~~~~~~~~

Most error messages are descriptive. Examples:

* ``Required environment variable 'BACKUP_LOCATION' is not set.`` - Add the variable to your ``.env`` file
* ``Could not get video duration`` - Ensure FFmpeg is installed and the video file is valid
* ``This script must be run in a git repository directory`` - Navigate to your Git repository first
