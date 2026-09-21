GitHub Pages Setup Guide
========================

This guide explains how to publish the Sphinx documentation with GitHub Pages.

Prerequisites
-------------

* Your repository on GitHub
* Admin or write access to the repository
* GitHub Actions enabled

Step-by-Step Setup
------------------

1. Enable GitHub Pages
~~~~~~~~~~~~~~~~~~~~~~~

**For repositories you own:**

a. Go to your GitHub repository
b. Click on **Settings** (top navigation bar)
c. In the left sidebar, click **Pages** (under "Code and automation")
d. Under "Build and deployment" > "Source"
e. Select **GitHub Actions** as the source
f. Click **Save**

2. Check Workflow Permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The committed workflow gives the build job read-only access and grants the
deployment job ``pages: write`` and ``id-token: write``. Repository-wide
read-and-write permission and pull-request approval permission are unnecessary.

3. Verify Workflow Files
~~~~~~~~~~~~~~~~~~~~~~~~

Ensure these committed files exist in your repository:

* ``.github/workflows/deploy-docs.yml`` - Handles documentation deployment
* ``.github/workflows/ci.yml`` - Handles code quality checks

You can view these files in the ``.github/workflows/`` directory.

4. Trigger Initial Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Option A: Automatic**

Merge a change to documentation, scripts, dependencies, or the deployment
workflow into ``master``. The workflow builds and deploys the documentation.

**Option B: Manual Trigger**

a. Go to the **Actions** tab in your repository
b. On the left, select **"Deploy Documentation to GitHub Pages"**
c. Click the **"Run workflow"** button (right side)
d. Select the **master** branch
e. Click **"Run workflow"**

5. Wait for Deployment
~~~~~~~~~~~~~~~~~~~~~~

a. Go to the **Actions** tab
b. Watch the workflow run:

   * **build** job: Builds documentation and uploads the artifact
   * **deploy** job: Publishes that artifact to GitHub Pages

6. Access Your Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once deployment completes:

a. Go to **Settings** > **Pages** to see your GitHub Pages URL
b. Your documentation will be available at:
   ``https://zlatanstajic.github.io/python_scripts/``

Customizing Deployment
----------------------

Changing the Repository URL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The workflow uses the Pages deployment URL returned by GitHub. If you fork the
repository, update any documentation links that still point to this project's
canonical URL: ``https://zlatanstajic.github.io/python_scripts/``.

Changing Python Version
~~~~~~~~~~~~~~~~~~~~~~~~

To use a different Python version for building documentation:

**In .github/workflows/deploy-docs.yml:**

Find the "Set up Python" step and change:

.. code-block:: yaml

   python-version: '3.10'

To your preferred version (3.10, 3.11, 3.12, etc.).

Triggering on Different Branches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To deploy from a different branch:

**In .github/workflows/deploy-docs.yml:**

Change both ``on.push.branches`` and the ``deploy`` job's branch condition:

.. code-block:: yaml

   on:
     push:
       branches:
         - master    # Change to your branch name

The job's ``if`` expression must check the same branch under ``github.ref``.

Excluding Paths From Triggering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To avoid rebuilding docs on certain file changes:

**In .github/workflows/deploy-docs.yml:**

Modify the ``paths`` section under ``push`` or remove it entirely to trigger on all changes.

Troubleshooting
---------------

**Workflow appears stuck or not running**

1. Check that GitHub Actions is enabled under **Settings** > **Actions**.
2. Check the workflow's branch and path filters. Manual runs are available from
   the **Actions** tab.

**Pages not showing deployed documentation**

1. Verify GitHub Pages is enabled:
   * Settings > Pages > Source should be "GitHub Actions"

2. Check that the ``deploy`` job has ``pages: write`` and ``id-token: write``
   permissions and targets the ``github-pages`` environment.

3. Check for build errors:
   * Go to Actions tab
   * Click on the failed workflow run
   * Expand the "Build" job to see error messages

**Documentation shows old version**

1. Clear browser cache (Ctrl+Shift+Del or Cmd+Shift+Del)
2. Wait a few minutes for GitHub Pages to update
3. Check the Actions tab to confirm latest deployment completed

More Help
---------

* `GitHub Pages Documentation <https://docs.github.com/en/pages>`_
* `GitHub Actions Documentation <https://docs.github.com/en/actions>`_
* `Sphinx Documentation <https://www.sphinx-doc.org/>`_

For project-specific help, see the `CI/CD Pipeline Documentation <cicd.rst>`_.
