CI/CD
=====

The CI workflow runs on supported Python versions and checks the retained
``scripts/`` package with flake8, isort, Black, mypy, pydocstyle, and Bandit.
It then runs the complete test suite with coverage measured against ``scripts``.

The documentation workflow builds this Sphinx site for relevant documentation,
script, dependency, and workflow changes. Pushes to the default branch deploy
the generated HTML to GitHub Pages; pull requests build without deploying.

Equivalent local checks
-----------------------

.. code-block:: bash

   python -m flake8 scripts/
   python -m mypy scripts/
   python -m pydocstyle scripts/
   python -m bandit -r scripts/ -ll
   python -m pytest tests/ --cov=scripts --cov-report=term-missing
   python -m sphinx -W -b html docs docs/_build/html
