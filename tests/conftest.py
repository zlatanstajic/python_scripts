"""Pytest configuration and shared fixtures for integration tests."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test operations."""
    _temp_dir = tempfile.mkdtemp()
    yield _temp_dir
    # Cleanup
    if os.path.exists(_temp_dir):
        shutil.rmtree(_temp_dir)


@pytest.fixture
def temp_project_dir(temp_dir):
    """Create a temporary project directory structure."""
    project_dir = os.path.join(temp_dir, "test_project")
    os.makedirs(project_dir, exist_ok=True)
    yield project_dir


@pytest.fixture
def temp_files_dir(temp_dir):
    """Create a temporary directory with various test files."""
    files_dir = os.path.join(temp_dir, "files")
    os.makedirs(files_dir, exist_ok=True)

    # Create various test files
    test_files = ["file1.txt", "file2.txt", "config.json", "notes.md"]
    for filename in test_files:
        filepath = os.path.join(files_dir, filename)
        with open(filepath, "w") as f:
            f.write(f"Content of {filename}")

    yield files_dir


@pytest.fixture
def temp_env_file(temp_dir):
    """Create a temporary .env file for testing."""
    env_file = os.path.join(temp_dir, ".env")
    env_content = """
BACKUP_LOCATION={backup_path}
PROJECTS_DESTINATION_FOLDER_NAME=projects_backup
PROJECTS_SOURCE_PATHS={project_path}
SYSTEM_SOURCE_PATHS={system_path}
SYSTEM_DESTINATION_FOLDER_NAME=system_backup
VSCODE_SOURCE_PATHS={vscode_path}
VSCODE_DESTINATION_FOLDER_NAME=vscode_backup
DEPLOYMENT_SOURCE_PATHS={deploy_path}
DEPLOYMENTS_DESTINATION_FOLDER_NAME=deployments_backup
HASH_FILENAMES_FILE_EXTENSIONS=.jpg,.png,.txt
SPLICE_IMAGES_FILE_EXTENSIONS=.jpg,.png,.gif
""".format(
        backup_path=os.path.join(temp_dir, "backups"),
        project_path=os.path.join(temp_dir, "projects"),
        system_path=os.path.join(temp_dir, "system"),
        vscode_path=os.path.join(temp_dir, "vscode"),
        deploy_path=os.path.join(temp_dir, "deployments"),
    )

    with open(env_file, "w") as f:
        f.write(env_content)

    yield env_file


@pytest.fixture
def mock_json_file(temp_dir):
    """Create a temporary JSON file for testing."""
    json_file = os.path.join(temp_dir, "data.json")
    test_data = {"key1": "value1", "key2": "value2", "nested": {"key3": "value3"}}
    with open(json_file, "w") as f:
        json.dump(test_data, f)

    yield json_file


@pytest.fixture
def mock_mapping_file(temp_dir):
    """Create a temporary mapping file for hash_filenames tests."""
    mapping_file = os.path.join(temp_dir, "hash_filenames_mapping.txt")
    mapping_data = {
        "original_file.jpg": "a1b2c3d4e5",
        "another_file.png": "f6g7h8i9j0",
    }
    with open(mapping_file, "w") as f:
        json.dump(mapping_data, f)

    yield mapping_file
