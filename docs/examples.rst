Examples
========

Generate from a local Markdown file
-----------------------------------

.. code-block:: bash

   MARKDOWN_FILE_URL="portfolio/cv.md" \
   PDF_OUTPUT_LOCATION="build/cv.pdf" \
   cv-generator

Capture configured sites
------------------------

.. code-block:: bash

   SCREENSHOT_SITES="https://example.com,https://www.python.org" \
   SCREENSHOT_OUTPUT_DIR="./screenshots" \
   website-screenshot

Capture a different site
------------------------

.. code-block:: bash

   SCREENSHOT_SITES="https://example.com" \
   SCREENSHOT_OUTPUT_DIR="/tmp/screenshots" \
   website-screenshot

Run without installing the commands
-----------------------------------

The file-path invocation stays supported for every example above:

.. code-block:: bash

   MARKDOWN_FILE_URL="portfolio/cv.md" \
   PDF_OUTPUT_LOCATION="build/cv.pdf" \
   python3 scripts/cv_generator.py
