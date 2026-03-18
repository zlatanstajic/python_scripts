#!/usr/bin/env python3
import os

print("Creating pre-commit hook to run tests")

HOOK_DIR = ".git/hooks"
HOOK_FILE = os.path.join(HOOK_DIR, "pre-commit")

# Create the hook directory if it doesn't exist
os.makedirs(HOOK_DIR, exist_ok=True)

# Create the pre-commit hook
hook_content = """#!/bin/sh
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

echo "Running flake8..."
python -m flake8 src/ scripts/
if [ $? -ne 0 ]; then
    echo "Flake8 failed. Please fix the issues."
    exit 1
fi

echo "Running bandit for security checks..."
python -m bandit -r src/ scripts/ -ll
if [ $? -ne 0 ]; then
    echo "Bandit found security issues. Please fix them."
    exit 1
fi

echo "Running pydocstyle docstring validation..."
python -m pydocstyle src/ scripts/
if [ $? -ne 0 ]; then
    echo "Pydocstyle failed. Please fix docstrings."
    exit 1
fi

echo "Running mypy type checking..."
python -m mypy src/ scripts/
if [ $? -ne 0 ]; then
    echo "Mypy failed. Please fix type hints."
    exit 1
fi

echo "Running tests with coverage..."
python -m pytest tests/ --cov=src --cov-report=term-missing
if [ $? -ne 0 ]; then
    echo "Tests failed. Please fix them."
    exit 1
fi

echo "All checks passed!"
"""

with open(HOOK_FILE, "w") as f:
    f.write(hook_content)

# Make the hook executable
os.chmod(HOOK_FILE, 0o755)

print(
    f"Pre-commit hook created at {HOOK_FILE}. It will run isort, black, flake8, bandit, pydocstyle, mypy, and pytest with coverage before each commit."
)
