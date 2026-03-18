Contributing
=============

We welcome contributions to this project! This guide will help you get started.

Code of Conduct
---------------

Please treat all contributors with respect. We're committed to providing a welcoming and inclusive environment for everyone.

Getting Started
---------------

1. **Fork the repository** on GitHub
2. **Clone your fork locally:**

   .. code-block:: bash

      git clone https://github.com/YOUR_USERNAME/python_scripts.git
      cd python_scripts

3. **Create a virtual environment:**

   .. code-block:: bash

      python3 -m venv .venv
      source .venv/bin/activate

4. **Install development dependencies:**

   Using traditional requirements files:

   .. code-block:: bash

      pip install -r requirements.txt
      pip install -r requirements-dev.txt

   Or using modern PEP 621 approach (recommended):

   .. code-block:: bash

      pip install -e ".[dev]"

5. **Install pre-commit hooks:**

   .. code-block:: bash

      python3 setup/install-pre-commit.py

Development Workflow
--------------------

1. **Create a feature branch:**

   .. code-block:: bash

      git checkout -b feature/your-feature-name

2. **Make your changes** and commit with descriptive messages:

   .. code-block:: bash

      git add .
      git commit -m "Add: description of your changes"

3. **Run tests and checks** before pushing:

   .. code-block:: bash

      # Run all pre-commit checks
      ./.git/hooks/pre-commit

      # Or run individually:
      python3 -m isort .
      python3 -m black .
      python3 -m flake8 src/ scripts/
      python3 -m mypy src/ scripts/
      python3 -m pytest tests/

4. **Push to your fork:**

   .. code-block:: bash

      git push origin feature/your-feature-name

5. **Create a Pull Request** on GitHub

Code Style Guidelines
---------------------

We follow strict code style guidelines to maintain consistency.

Python Style
~~~~~~~~~~~~

- **Follow PEP 8** for Python code style
- **Use type hints** for all function parameters and return values
- **Use docstrings** in Google style format:

  .. code-block:: python

     def example_function(param1: str, param2: int) -> bool:
         """Brief description of the function.

         Longer description if needed.

         Args:
             param1: Description of param1.
             param2: Description of param2.

         Returns:
             Description of return value.

         Raises:
             ValueError: When this error occurs.
         """
         pass

Import Organization
~~~~~~~~~~~~~~~~~~~~

Imports should be organized in the following order:

1. Standard library imports
2. Third-party imports
3. Local imports (prefixed with relative imports like ``from ..src``)

Use ``isort`` to automatically organize imports:

.. code-block:: bash

   python3 -m isort .

Code Formatting
~~~~~~~~~~~~~~~

Use ``black`` for consistent code formatting:

.. code-block:: bash

   python3 -m black .

We use the default black settings with a line length of 88 characters.

Type Checking
~~~~~~~~~~~~~

All code must pass ``mypy`` type checking:

.. code-block:: bash

   python3 -m mypy src/ scripts/

Fix type errors before submitting your PR:

.. code-block:: python

   # Good
   def process_name(name: str) -> str:
       return name.title()

   # Bad
   def process_name(name):
       return name.title()

Naming Conventions
~~~~~~~~~~~~~~~~~~

- **Functions and variables:** ``snake_case``
- **Classes:** ``PascalCase``
- **Constants:** ``UPPER_SNAKE_CASE``
- **Private members:** prefix with underscore (``_private_var``)

Testing
-------

All submissions must include tests. We aim for high code coverage.

Writing Tests
~~~~~~~~~~~~~

Create tests in the ``tests/`` directory:

- Unit tests: ``test_module_name.py``
- Integration tests: ``test_integration_module_name.py``

Example test:

.. code-block:: python

   import pytest
   from scripts.generate_password import generate_password

   class TestGeneratePassword:
       def test_generates_correct_length(self):
           """Test password has correct length."""
           password = generate_password(8, 4, 20)
           assert len(password) == 20

       def test_contains_all_character_types(self):
           """Test password contains all required character types."""
           password = generate_password(8, 4, 20)
           assert any(c.islower() for c in password)
           assert any(c.isupper() for c in password)
           assert any(c.isdigit() for c in password)

Running Tests
~~~~~~~~~~~~~

Run the full test suite:

.. code-block:: bash

   python3 -m pytest tests/ -v

Run tests with coverage:

.. code-block:: bash

   python3 -m pytest tests/ -v --cov=src --cov-report=term-missing

Run specific tests:

.. code-block:: bash

   python3 -m pytest tests/test_specific.py::TestClass::test_method -v

Creating Fixtures
~~~~~~~~~~~~~~~~~

Use pytest fixtures for reusable test setup:

.. code-block:: python

   import pytest
   import tempfile

   @pytest.fixture
   def temp_dir():
       """Create a temporary directory for test operations."""
       with tempfile.TemporaryDirectory() as tmp:
           yield tmp

   class TestMyFeature:
       def test_with_temp_dir(self, temp_dir):
           # temp_dir is automatically cleaned up after test
           pass

Documentation
--------------

Update documentation for your changes.

Docstring Format
~~~~~~~~~~~~~~~~

Use Google style docstrings:

.. code-block:: python

   def calculate_backup_size(directory: str) -> int:
       """Calculate total size of directory for backup.

       Args:
           directory: Path to directory to measure.

       Returns:
           Total size in bytes.

       Raises:
           FileNotFoundError: If directory doesn't exist.
           PermissionError: If unable to read directory.
       """
       pass

Update README
~~~~~~~~~~~~~

If your changes affect user-facing functionality:

1. Update the relevant section in README.md
2. Add examples showing how to use the new feature
3. Document any new environment variables

Update Sphinx Docs
~~~~~~~~~~~~~~~~~~

For API changes:

1. Update docstrings
2. Check API reference documentation renders correctly:

   .. code-block:: bash

      cd docs
      make html
      # Open _build/html/index.html in browser

Commit Messages
---------------

Write clear, descriptive commit messages:

- **Format:** ``Type: Description``
- **Types:** ``Add``, ``Fix``, ``Refactor``, ``Docs``, ``Test``, ``Chore``
- **Examples:**

  - ``Add: password generation with custom length``
  - ``Fix: handle empty directories in backup``
  - ``Refactor: simplify image splicing logic``
  - ``Docs: add examples for git copy script``
  - ``Test: add integration tests for hash filenames``

Good Practices
~~~~~~~~~~~~~~

- Keep commits focused on single changes
- Write in imperative mood ("Add feature" not "Added feature")
- Reference issues: ``Fix: resolve issue #123``

Pull Request Guidelines
-----------------------

When submitting a PR:

1. **Title:** Clear description of changes (e.g., "Add password strength validation")
2. **Description:** Explain what changed and why
3. **Link issues:** Reference related issues (e.g., "Closes #123")
4. **Tests:** Include tests for new functionality
5. **Documentation:** Update docs if needed
6. **Changelog:** Mention in PR description for release notes

Example PR Description:

.. code-block:: markdown

   ## Description
   Adds password strength validation to the generate_password script.

   ## Changes
   - Added `validate_password_strength()` function
   - Added tests for validation
   - Updated README with examples

   ## Related Issues
   Closes #42

   ## Testing
   - All existing tests pass ✓
   - Added 5 new tests for validation ✓
   - Tested with various password lengths ✓

Review Process
--------------

- At least one maintainer will review your PR
- Address any requested changes
- Once approved, your PR will be merged

Reporting Issues
----------------

Found a bug? Want a feature? Please open an issue!

Bug Reports
~~~~~~~~~~~

Include:

- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Python version, etc.)

Feature Requests
~~~~~~~~~~~~~~~~

Include:

- Clear description of the feature
- Why it would be useful
- Possible implementation approach (optional)

Setting Up Documentation Locally
--------------------------------

To build Sphinx documentation locally:

.. code-block:: bash

   cd docs
   pip install -r ../requirements-dev.txt
   make html
   open _build/html/index.html

Questions?
----------

Feel free to:

- Open an issue on GitHub
- Email the maintainers
- Join our discussions

Thank you for contributing!
