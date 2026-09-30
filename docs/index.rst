Python Scripts
==============

**Practical Python tools for documents, the web, and media libraries.**

This project provides three Python command-line utilities: a Markdown-to-PDF
CV generator, a Playwright-based website screenshot tool, and a copy-only
media library organizer.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   usage_guide
   media_organizer
   examples
   api_reference
   contributing
   cicd
   github-pages-setup

Utilities
---------

* ``cv-generator`` (:mod:`scripts.cv_generator`) renders a single-page PDF
  CV from Markdown.
* ``website-screenshot`` (:mod:`scripts.screenshot`) captures 1600x900
  viewport JPEGs of websites.
* ``media-organizer`` (:mod:`scripts.media_organizer`) creates a verified,
  date-and-location-organized copy of a media library.

Installing the project puts all three commands on the ``PATH``; see
:doc:`installation`. Running each module by file path remains supported:
``python scripts/cv_generator.py``, ``python scripts/screenshot.py``, or
``python scripts/media_organizer.py``.

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
