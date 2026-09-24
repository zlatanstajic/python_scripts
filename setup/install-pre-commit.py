#!/usr/bin/env python3
"""Install a Git pre-commit hook that runs the documented quality gate.

Run from anywhere inside the repository:
    python setup/install-pre-commit.py

A different existing pre-commit hook is renamed to the first free
``pre-commit.bak`` path before the new hook is written.
"""

import os
import subprocess
import sys

HOOK_CONTENT = """#!/bin/sh
echo "Running pre-commit checks..."

echo "Running isort..."
python -m isort . --profile black --check-only --diff
if [ $? -ne 0 ]; then
    echo "Isort failed. Please run 'python -m isort .' to fix."
    exit 1
fi

echo "Running black..."
python -m black . --check --diff
if [ $? -ne 0 ]; then
    echo "Black failed. Please run 'python -m black .' to fix."
    exit 1
fi

echo "Compiling Python files..."
python -m compileall -q scripts tests
if [ $? -ne 0 ]; then
    echo "Compilation failed. Please fix the syntax errors."
    exit 1
fi

echo "Running flake8..."
python -m flake8 scripts/
if [ $? -ne 0 ]; then
    echo "Flake8 failed. Please fix the issues."
    exit 1
fi

echo "Running bandit for security checks..."
python -m bandit -r scripts/ -ll
if [ $? -ne 0 ]; then
    echo "Bandit found security issues. Please fix them."
    exit 1
fi

echo "Running pydocstyle docstring validation..."
python -m pydocstyle scripts/
if [ $? -ne 0 ]; then
    echo "Pydocstyle failed. Please fix docstrings."
    exit 1
fi

echo "Running mypy type checking..."
python -m mypy scripts/
if [ $? -ne 0 ]; then
    echo "Mypy failed. Please fix type hints."
    exit 1
fi

echo "Running tests with coverage..."
python -m pytest tests/
if [ $? -ne 0 ]; then
    echo "Tests failed. Please fix them."
    exit 1
fi

echo "Building documentation with warnings as errors..."
python -m sphinx -W -b html docs docs/_build/html
if [ $? -ne 0 ]; then
    echo "Sphinx failed. Please fix the documentation warnings."
    exit 1
fi

echo "All checks passed!"
"""


def hooks_directory() -> str:
    """Return the hooks directory Git uses, including for linked worktrees."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.strip()


def backup_path(hook_file: str) -> str:
    """Return the first unused backup path for an existing hook."""
    candidate = f"{hook_file}.bak"
    number = 1
    while os.path.lexists(candidate):
        candidate = f"{hook_file}.bak.{number}"
        number += 1
    return candidate


def main() -> int:
    """Install the hook, keeping a different existing hook as a backup."""
    try:
        hook_dir = hooks_directory()
    except (OSError, subprocess.CalledProcessError):
        print("Error: run this script inside a Git checkout.", file=sys.stderr)
        return 1

    hook_file = os.path.join(hook_dir, "pre-commit")
    os.makedirs(hook_dir, exist_ok=True)

    if os.path.lexists(hook_file):
        try:
            with open(hook_file, "rb") as existing:
                unchanged = existing.read() == HOOK_CONTENT.encode()
        except OSError:
            unchanged = False
        if not unchanged:
            backup = backup_path(hook_file)
            os.rename(hook_file, backup)
            print(f"Backed up the existing hook to {backup}")

    with open(hook_file, "w", encoding="utf-8", newline="\n") as hook:
        hook.write(HOOK_CONTENT)
    os.chmod(hook_file, 0o755)

    print(
        f"Pre-commit hook installed at {hook_file}. It runs isort, Black, "
        "compileall, flake8, Bandit, pydocstyle, mypy, pytest with coverage, and "
        "a strict Sphinx build before each commit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
