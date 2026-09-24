Usage Guide
===========

Installing the project provides ``cv-generator``, ``website-screenshot``, and
``media-organizer``. The first two read configuration from ``.env``. Copy
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

Organize a media library
------------------------

The media organizer takes command-line paths rather than ``.env`` settings.
Its workflow deliberately separates inspection, approval, and copying:

.. code-block:: bash

   media-organizer scan --input "/home/user/Media" --verbose
   media-organizer plan --input "/home/user/Media" --output "/home/user/Organized" --verbose
   media-organizer apply --plan "/home/user/Organized/organization-plan.json" --verbose

The source directory is recursively scanned and remains unchanged throughout.
The plan and report default to the output directory and are removed after a
fully successful apply. They remain available when an entry fails.
The optional ``--verbose`` flag shows detailed progress during every phase.

Run ``media-organizer report`` inside the organized library to save a JSON
inventory of its photos, videos, formats, orientations, and locations as
``media-report.json`` in the current directory.
See :doc:`media_organizer` for the complete safety and metadata behavior.

Running the modules by file path
--------------------------------

The original file-path invocation remains supported and behaves identically to
the installed commands:

.. code-block:: bash

   python3 scripts/cv_generator.py
   python3 scripts/screenshot.py
   python3 scripts/media_organizer.py --help

Development commands
--------------------

The complete local quality gate is listed in :doc:`contributing`, and
:doc:`cicd` describes which of those checks CI runs.
