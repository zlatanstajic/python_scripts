Usage Guide
===========

Both utilities load configuration from ``.env`` by default. Copy
``.env.example`` to ``.env`` and adjust its retained settings.

Generate a CV
-------------

Configure the Markdown input and PDF output:

.. code-block:: bash

   MARKDOWN_FILE_URL="cv.md"
   PDF_OUTPUT_LOCATION="cv.pdf"
   python3 scripts/cv_generator.py

The input may be a local path or a ``file://`` URL. Relative input and output
paths are based on the current working directory.

Capture websites
----------------

Configure one or more comma-separated sites and an output directory:

.. code-block:: bash

   SCREENSHOT_SITES="https://example.com,https://zlatanstajic.com"
   SCREENSHOT_OUTPUT_DIR="$HOME/Pictures"
   python3 scripts/screenshot.py

The tool runs Chromium headlessly and saves each site's visible 1600x900
viewport as ``<hostname>.jpg``. The CLI accepts no options other than
``-h``/``--help``; configure sites and the destination only through ``.env``.

Development commands
--------------------

.. code-block:: bash

   python3 -m pytest tests/
   python3 -m compileall -q scripts tests
   python3 -m flake8 scripts/
   python3 -m mypy scripts/
   python3 -m sphinx -W -b html docs docs/_build/html
