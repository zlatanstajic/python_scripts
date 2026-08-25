Contributing
============

Create a focused branch, update the retained utility and its tests or
documentation together, and run the local checks before opening a pull request.

.. code-block:: bash

   python -m isort . --profile black --check-only --diff
   python -m black . --check --diff
   python -m flake8 scripts/
   python -m mypy scripts/
   python -m pydocstyle scripts/
   python -m pytest tests/

Keep command-line behavior documented in the README and usage guide. New runtime
dependencies belong in both ``pyproject.toml`` and ``requirements.txt``.
