Usage Guide
===========

Installing the project provides ``cv-generator``, ``website-screenshot``, and
``video-organizer``. The first two read configuration from ``.env``. Copy
``.env.example`` to ``.env`` and adjust its retained settings.

Where ``.env`` is read from
---------------------------

Both commands load ``.env`` from the **current working directory**, not from
the repository root and not from the installation directory. The file is loaded
with ``override=False``, so real environment variables win over the values in
the file, and a missing ``.env`` is a hard error.

.. code-block:: bash

   cd ~/some/project && website-screenshot   # uses ~/some/project/.env

Generate a CV
-------------

Configure the Markdown input and PDF output:

.. code-block:: bash

   MARKDOWN_FILE_URL="cv.md"
   PDF_OUTPUT_LOCATION="cv.pdf"
   cv-generator

The input may be a local path or a ``file://`` URL. Relative input and output
paths are based on the current working directory.

Capture websites
----------------

Configure one or more comma-separated sites and an output directory:

.. code-block:: bash

   SCREENSHOT_SITES="https://example.com,https://zlatanstajic.com"
   SCREENSHOT_OUTPUT_DIR="$HOME/Pictures"
   website-screenshot

The tool runs Chromium headlessly and saves each site's visible 1600x900
viewport as ``<hostname>.jpg``. GitHub Pages project sites are named after
the repository instead of the shared user hostname, with underscores replaced
by hyphens, so ``https://username.github.io/my_project/`` is written as
``my-project.jpg``. Both
commands accept no options other than ``-h``/``--help``; configure sites and
destinations only through ``.env``.

Organize a video library
------------------------

The video organizer takes command-line paths rather than ``.env`` settings.
Its workflow deliberately separates inspection, approval, and copying:

.. code-block:: bash

   video-organizer scan --input "/home/user/Videos" --verbose
   video-organizer plan --input "/home/user/Videos" --output "/home/user/Organized" --verbose
   video-organizer apply --plan "/home/user/Organized/organization-plan.json" --verbose

The source directory is recursively scanned and remains unchanged throughout.
The plan and report default to the output directory and are removed after a
fully successful apply. They remain available when an entry fails.
The optional ``--verbose`` flag shows detailed progress during every phase.
See :doc:`video_organizer` for the complete safety and metadata behavior.

Running the modules by file path
--------------------------------

The original file-path invocation remains supported and behaves identically to
the installed commands:

.. code-block:: bash

   python3 scripts/cv_generator.py
   python3 scripts/screenshot.py
   python3 scripts/video_organizer.py --help

Development commands
--------------------

.. code-block:: bash

   python3 -m pytest tests/
   python3 -m compileall -q scripts tests
   python3 -m flake8 scripts/
   python3 -m mypy scripts/
   python3 -m sphinx -W -b html docs docs/_build/html
