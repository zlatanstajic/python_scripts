CI/CD Pipeline & Continuous Integration
=========================================

This project uses GitHub Actions for automated testing, code quality checks, and documentation deployment.

Overview
--------

The CI/CD pipeline consists of three main workflows:

1. **Deploy Documentation** (deploy-docs.yml)
2. **Code Quality & Testing** (ci.yml)
3. **Pre-commit Hooks** (local verification)

Workflows
---------

Deploy Documentation to GitHub Pages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**File:** ``.github/workflows/deploy-docs.yml``

**Trigger Events:**

* Push to ``main`` or ``master`` branch
* Changes to documentation (``docs/``)
* Changes to source code (``src/``, ``scripts/``)
* Changes to configuration (``pyproject.toml``, ``requirements*.txt``)
* Manual trigger via workflow_dispatch

**Steps:**

1. Checkout the repository
2. Set up Python 3.10
3. Install project dependencies with development extras
4. Build Sphinx documentation
5. Upload build artifacts
6. Deploy to GitHub Pages

**Access Deployed Documentation:**

After deployment, documentation is available at:
``https://zlatanstajic.github.io/python_scripts/``

The workflow automatically keeps documentation in sync with the main branch.

Code Quality & Testing
~~~~~~~~~~~~~~~~~~~~~~

**File:** ``.github/workflows/ci.yml``

**Trigger Events:**

* Push to ``main``, ``master``, or ``develop`` branches
* Pull requests to those branches
* Changes to code, tests, or configuration
* Manual trigger via workflow_dispatch

**Matrix Testing:**

Tests run across multiple Python versions:

* Python 3.10 (minimum supported)
* Python 3.11
* Python 3.12

**Quality Checks Performed:**

1. **flake8** - Code style linting
2. **isort** - Import statement organization
3. **black** - Code formatting verification
4. **mypy** - Static type checking
5. **bandit** - Security vulnerability scanning
6. **pytest** - Unit and integration tests with coverage
7. **codecov** - Coverage metrics tracking

**Coverage Reporting:**

Test coverage reports are uploaded to Codecov.io for tracking coverage trends over time.

Local Verification
~~~~~~~~~~~~~~~~~~

Before pushing, run the pre-commit checks locally:

.. code-block:: bash

   # Install pre-commit hooks
   python3 setup/install-pre-commit.py

   # Run all checks before commit
   ./.git/hooks/pre-commit

Or run individual checks:

.. code-block:: bash

   # Format imports and code
   python -m isort .
   python -m black .

   # Check code quality
   python -m flake8 src/ scripts/
   python -m mypy src/ scripts/
   python -m bandit -r src/ scripts/ -ll

   # Run tests
   python -m pytest tests/ -v --cov=src

Setting Up GitHub Pages
-----------------------

If this is your first deployment:

1. **Enable GitHub Pages:**

   * Go to repository **Settings**
   * Navigate to **Pages** section
   * Under "Build and deployment"
   * Select "GitHub Actions" as the deployment source
   * Save settings

2. **Verify Workflow Permissions:**

   * Go to repository **Settings**
   * Navigate to **Actions** > **General**
   * Under "Workflow permissions"
   * Select "Read and write permissions"
   * Enable "Allow GitHub Actions to create and approve pull requests"

3. **First Deployment:**

   * Push to main branch or trigger workflow manually
   * Check **Actions** tab for workflow status
   * Once complete, documentation will be available at GitHub Pages URL

Troubleshooting
---------------

**Workflow fails with "Permission denied"**

Ensure your GitHub repository has:

* Workflows enabled under Settings > Actions > General
* Write permissions for GitHub Actions (Settings > Actions > General)
* GitHub Pages configured to use GitHub Actions as source

**Documentation not updating**

1. Check the workflow run status in the **Actions** tab
2. Review workflow logs for build errors
3. Verify Sphinx build completes without errors locally:

   .. code-block:: bash

      cd docs
      make clean
      make html

**Tests failing in CI but passing locally**

* Ensure you're running tests in the same Python version as CI
* Check for environment-specific issues
* Verify all dependencies are installed:

   .. code-block:: bash

      pip install -e ".[dev]"

**Coverage not uploading to Codecov**

This is non-critical and won't block deployments. ensure:

* Public repository (Codecov.io has free tier for public repos)
* Coverage report is generated (``coverage.xml``)
* Network connectivity is available during workflow run

Customization
-------------

**Modifying Workflows:**

1. Edit ``.github/workflows/deploy-docs.yml`` or ``.github/workflows/ci.yml``
2. Make your changes
3. Commit and push to trigger the updated workflow

**Triggering Workflows Manually:**

* Go to **Actions** tab in repository
* Select desired workflow
* Click **Run workflow**
* Select branch and click **Run workflow**

**Python Versions:**

Edit the ``strategy.matrix.python-version`` in ``ci.yml`` to test different versions.

**Documentation Triggers:**

The deployment workflow watches specific paths. Edit the ``paths`` section in ``deploy-docs.yml`` to change what triggers documentation rebuilds.

Best Practices
--------------

1. **Always run pre-commit checks locally before pushing:**

   .. code-block:: bash

      ./.git/hooks/pre-commit

2. **Keep configuration in sync:**

   * Run ``pip install -e ".[dev]"`` after pulling changes
   * Don't modify workflows without testing locally

3. **Monitor workflow runs:**

   * Check the **Actions** tab regularly
   * Fix failing workflows promptly
   * Review coverage reports to identify gaps

4. **Document changes:**

   * Update CHANGELOG.md with significant changes
   * Add docstrings to new functions
   * Keep documentation in sync with code changes
