Installation
============

Python 3.10 or newer is required.

.. code-block:: bash

   git clone https://github.com/zlatanstajic/python_scripts.git
   cd python_scripts
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   python -m playwright install chromium
   cp .env.example .env

WeasyPrint also requires platform libraries supplied by the operating system.
Consult the WeasyPrint installation guide for the packages appropriate to your
platform. Playwright's Chromium installation is required only for screenshots.
