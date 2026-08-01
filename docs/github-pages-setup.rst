GitHub Pages Setup Guide
========================

This guide explains how to set up GitHub Pages for this project to enable automatic documentation deployment.

Prerequisites
-------------

* Your repository on GitHub
* Admin or write access to the repository
* GitHub Actions enabled (usually enabled by default)

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

2. Configure Workflow Permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

a. Go to **Settings** > **Actions** > **General** (left sidebar)
b. Under "Workflow permissions" section:

   * Select **Read and write permissions**
   * Check the box: "Allow GitHub Actions to create and approve pull requests"

c. Click **Save**

3. Verify Workflow Files
~~~~~~~~~~~~~~~~~~~~~~~~

Ensure these files exist in your repository (automatically created):

* ``.github/workflows/deploy-docs.yml`` - Handles documentation deployment
* ``.github/workflows/ci.yml`` - Handles code quality checks

You can view these files by navigating to the `.github/workflows/` directory in your repository.

4. Trigger Initial Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Option A: Automatic (Recommended)**

Push code to the ``master`` branch:

.. code-block:: bash

   git add .
   git commit -m "Enable GitHub Pages deployment"
   git push origin master

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

   * **deploy** job: Builds documentation (5-10 minutes usually)
   * **deploy** job: Deploys to GitHub Pages (1-2 minutes)

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

The deploy workflow references the example GitHub Pages URL. If you forked this repository, update the documentation URL:

**In docs/installation.rst:**

This project is configured with the GitHub username **zlatanstajic** and repository name **python_scripts**.

If you forked this repository to your own account, update the URL in documentation files:
   Change: ``https://zlatanstajic.github.io/python_scripts/``
   To: ``https://<your-username>.github.io/<your-repo-name>/``

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

Change the ``on.push.branches`` section:

.. code-block:: yaml

   on:
     push:
       branches:
         - master    # Change to your branch name

Excluding Paths From Triggering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To avoid rebuilding docs on certain file changes:

**In .github/workflows/deploy-docs.yml:**

Modify the ``paths`` section under ``push`` or remove it entirely to trigger on all changes.

Troubleshooting
---------------

**Workflow appears stuck or not running**

1. Check if GitHub Actions is enabled:
   * Settings > Actions > General > "Actions permissions"
   * Select: "Allow all actions and reusable workflows"

2. Verify branch protection rules don't block workflows:
   * Settings > Branches > Branch protection rules
   * Uncheck: "Require status checks to pass before merging"

**Pages not showing deployed documentation**

1. Verify GitHub Pages is enabled:
   * Settings > Pages > Source should be "GitHub Actions"

2. Check workflow has read-write permissions:
   * Settings > Actions > General > Workflow permissions
   * Ensure "Read and write permissions" is selected

3. Check for build errors:
   * Go to Actions tab
   * Click on the failed workflow run
   * Expand the "Build" job to see error messages

**Getting "Permission denied" error**

1. Go to Settings > Actions > General
2. Under "Workflow permissions"
3. Select "Read and write permissions"
4. Check "Allow GitHub Actions to create and approve pull requests"
5. Click Save

**Documentation shows old version**

1. Clear browser cache (Ctrl+Shift+Del or Cmd+Shift+Del)
2. Wait a few minutes for GitHub Pages to update
3. Check the Actions tab to confirm latest deployment completed

**Domain not pointing correctly**

This typically happens with custom domains:

1. Check that CNAME file exists in your docs directory
2. Verify DNS settings for your custom domain
3. Check GitHub Pages settings for proper domain configuration

More Help
---------

* `GitHub Pages Documentation <https://docs.github.com/en/pages>`_
* `GitHub Actions Documentation <https://docs.github.com/en/actions>`_
* `Sphinx Documentation <https://www.sphinx-doc.org/>`_

For project-specific help, see the `CI/CD Pipeline Documentation <cicd.rst>`_.
