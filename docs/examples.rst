Examples
========

Generate from a local Markdown file
-----------------------------------

.. code-block:: bash

   MARKDOWN_FILE_URL="portfolio/cv.md" \
   PDF_OUTPUT_LOCATION="build/cv.pdf" \
   python3 scripts/cv_generator.py

Capture configured sites
------------------------

.. code-block:: bash

   SCREENSHOT_SITES="https://example.com,https://www.python.org" \
   SCREENSHOT_OUTPUT_DIR="./screenshots" \
   python3 scripts/screenshot.py

Capture a different site
------------------------

.. code-block:: bash

   SCREENSHOT_SITES="https://example.com" \
   SCREENSHOT_OUTPUT_DIR="/tmp/screenshots" \
   python3 scripts/screenshot.py
