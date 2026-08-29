Installation
============

Python 3.10 or newer is required.

Development install
-------------------

.. code-block:: bash

   git clone https://github.com/zlatanstajic/python_scripts.git
   cd python_scripts
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   python -m playwright install chromium
   cp .env.example .env

The editable install puts two commands on the ``PATH`` of the activated
environment:

.. code-block:: bash

   which cv-generator
   which website-screenshot

Source edits under ``scripts/`` take effect immediately for those commands.
Command names come from ``[project.scripts]`` in ``pyproject.toml`` and are
packaging metadata, so a new or renamed command appears only after re-running
``python -m pip install -e ".[dev]"``.

Optional user-level install with pipx
-------------------------------------

``pipx install .`` installs the same two commands into an isolated environment
that never needs activating. It suits ``cv-generator``, which requires only the
WeasyPrint system libraries.

Neither ``pip`` nor ``pipx`` ever installs the Chromium binary that
``website-screenshot`` drives; only ``python -m playwright install chromium``,
run with the interpreter of the environment holding the command, does. That
step is not verified for a pipx-managed environment here, so use the virtual
environment described above when you need ``website-screenshot``.

System requirements
-------------------

WeasyPrint also requires platform libraries supplied by the operating system.
Consult the WeasyPrint installation guide for the packages appropriate to your
platform. Playwright's Chromium installation is required only for screenshots.
