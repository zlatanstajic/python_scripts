CI/CD
=====

The CI workflow runs on every push to ``master`` and every pull request targeting
``master``. On Python 3.10, 3.11, 3.12, and 3.13 it checks all three installed
entry points, runs the test suite with coverage, compiles Python files, and runs
flake8, isort, Black, mypy, pydocstyle, and Bandit. These checks are blocking.
Coverage upload to Codecov runs on Python 3.12 and is advisory.

The documentation workflow builds this Sphinx site with warnings treated as
errors on every pull request to ``master`` and on relevant pushes. Pushes to
``master`` deploy the generated HTML to GitHub Pages; pull requests build
without deploying. Only the deployment job has Pages write permission.
Pull request builds can cancel older runs for the same pull request. Deployments
on ``master`` run separately and do not cancel an active deployment.

Equivalent local checks
-----------------------

.. code-block:: bash

   python -m pytest tests/
   python -m compileall -q scripts tests
   python -m flake8 scripts/
   python -m mypy scripts/
   python -m pydocstyle scripts/
   python -m bandit -r scripts/ -ll
   python -m isort . --profile black --check-only --diff
   python -m black . --check --diff
   python -m sphinx -W -b html docs docs/_build/html
