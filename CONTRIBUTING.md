# Contributing

Contributions are welcome. To propose a change:

1. **Open an issue, fork, and branch.** Open or identify the issue for the
   change, fork the repository, then create a branch off `master`. Every
   contribution branch must use the `issues/` prefix followed by a
   kebab-case name: `issues/<issue-number>-<short-description>` (for example,
   `issues/12-add-cv-generator`). Write the description in lowercase words
   separated by single hyphens — never `snake_case`, camelCase, or spaces.
2. **Edit the source files.** Application code belongs in [`scripts/`](scripts/),
   tests in [`tests/`](tests/), documentation in [`docs/`](docs/), and
   maintainer-only utilities in [`tools/`](tools/). Keep changes focused and
   add or update tests whenever behavior changes.
3. **Match the conventions.** Target Python 3.10 or newer, follow PEP 8, use
   `snake_case`, add type hints where practical, and write Google-style
   docstrings. Keep lines within 88 characters. Read configuration through
   `python-dotenv`, document new keys in [`.env.example`](.env.example), and
   never commit a real `.env` file or secret.
4. **Keep documentation and dependencies synchronized.** Update
   [`README.md`](README.md) and the relevant Sphinx pages when commands,
   configuration, or behavior change. Add runtime dependencies to both
   [`pyproject.toml`](pyproject.toml) and
   [`requirements.txt`](requirements.txt); add development dependencies to
   `pyproject.toml` and [`requirements-dev.txt`](requirements-dev.txt).
5. **Test before submitting.** Install the development dependencies, then run
   the project checks:

   ```bash
   python -m pytest tests/
   python -m compileall -q scripts tests
   python -m flake8 scripts/
   python -m mypy scripts/
   python -m pydocstyle scripts/
   python -m bandit -r scripts/ -ll
   python -m isort . --profile black --check-only --diff
   python -m black . --check --diff
   python -m sphinx -W -b html docs docs/_build/html
   ```

6. **Open a pull request.** Push the `issues/` branch and open a PR against
   `master`. Keep it focused, link the issue (for example, `Fixes #123`),
   explain what changed and why, list the checks you ran, and include examples,
   command output, or screenshots when useful.

By contributing, you agree that your contribution will be licensed under the
repository's [MIT License](LICENSE.md). Be respectful in issues and pull
requests.
