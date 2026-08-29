Python Scripts
==============

**Practical Python tools for documents and the web.**

This project provides two Python command-line utilities: a Markdown-to-PDF CV
generator and a Playwright-based website screenshot tool.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   usage_guide
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

Installing the project puts both commands on the ``PATH``; see
:doc:`installation`. Running ``python scripts/cv_generator.py`` and
``python scripts/screenshot.py`` by file path remains supported.

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
