Python Scripts Documentation
=============================

Welcome to the Python Scripts documentation! This project contains a collection of automation scripts for various common tasks.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage_guide
   api_reference
   examples
   contributing
   cicd
   github-pages-setup

Quick Start
-----------

1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/zlatanstajic/python_scripts.git
      cd python_scripts

2. **Set up virtual environment:**

   .. code-block:: bash

      python3 -m venv .venv
      source .venv/bin/activate

3. **Install dependencies:**

   .. code-block:: bash

      pip install -r requirements.txt

4. **Run a script:**

   .. code-block:: bash

      python3 scripts/generate_password.py -l 16

Available Scripts
-----------------

* :doc:`Generate Password </api_reference/scripts/generate_password>` - Create secure passwords
* :doc:`PHP Switch </api_reference/scripts/php_switch>` - Switch between PHP versions
* :doc:`Development Setup </api_reference/scripts/dev_setup>` - Set up Git branches for tasks
* :doc:`Backup Files </api_reference/scripts/backup>` - Backup system files and configurations
* :doc:`Git Copy </api_reference/scripts/git_copy>` - Copy changed files between commits
* :doc:`Restore VS Code </api_reference/scripts/restore_vscode_folder>` - Restore VS Code settings
* :doc:`Hash Filenames </api_reference/scripts/hash_filenames>` - Hash and organize filenames
* :doc:`Splice Images </api_reference/scripts/splice_images>` - Splice images horizontally
* :doc:`Splice Videos </api_reference/scripts/splice_videos>` - Splice video segments
* :ref:`CV Generator <cv-generator>` - Convert a Markdown CV to a single-page A4 PDF

Project Structure
-----------------

.. code-block::

   python_scripts/
   ├── src/
   │   ├── helpers/
   │   │   ├── arguments_helper.py
   │   │   └── wrapper_helper.py
   │   └── __init__.py
   ├── scripts/
   │   ├── backup.py
   │   ├── cv_generator.py
   │   ├── dev_setup.py
   │   ├── generate_password.py
   │   ├── git_copy.py
   │   ├── hash_filenames.py
   │   ├── php_switch.py
   │   ├── restore_vscode_folder.py
   │   ├── splice_images.py
   │   └── splice_videos.py
   ├── tests/
   │   ├── test_*.py
   │   ├── test_integration_*.py
   │   └── conftest.py
   ├── docs/
   ├── requirements.txt
   ├── requirements-dev.txt
   └── README.md

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
