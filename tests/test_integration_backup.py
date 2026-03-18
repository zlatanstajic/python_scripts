"""Integration tests for backup script with real file operations."""

import json
import os
import shutil
import sys
import tempfile
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.backup import (
    do_deployments_backup,
    do_projects_backup,
    do_simple_backup,
    get_env,
    get_parent_folder_name,
    sudo_makedirs,
    sudo_rmtree,
)


class TestBackupIntegration:
    """Integration tests for real backup file operations."""

    def test_sudo_makedirs_creates_directory(self, temp_dir):
        """Test that sudo_makedirs creates directories."""
        new_dir = os.path.join(temp_dir, "new_folder", "subfolder")

        # Directory shouldn't exist yet
        assert not os.path.exists(new_dir)

        # Create it
        sudo_makedirs(new_dir)

        # Should exist now
        assert os.path.isdir(new_dir)

    def test_sudo_makedirs_idempotent(self, temp_dir):
        """Test that sudo_makedirs can be called multiple times safely."""
        test_dir = os.path.join(temp_dir, "idempotent")

        # Create multiple times
        sudo_makedirs(test_dir)
        sudo_makedirs(test_dir)
        sudo_makedirs(test_dir)

        # Should still exist and be a directory
        assert os.path.isdir(test_dir)

    def test_sudo_rmtree_deletes_directory(self, temp_dir):
        """Test that sudo_rmtree deletes directories."""
        test_dir = os.path.join(temp_dir, "to_delete")
        os.makedirs(test_dir, exist_ok=True)

        # Create some files
        for i in range(3):
            with open(os.path.join(test_dir, f"file{i}.txt"), "w") as f:
                f.write(f"Content {i}")

        assert os.path.exists(test_dir)

        # Delete
        sudo_rmtree(test_dir)

        # Should be gone
        assert not os.path.exists(test_dir)

    def test_sudo_rmtree_idempotent(self, temp_dir):
        """Test that sudo_rmtree can be called on non-existent paths."""
        non_existent = os.path.join(temp_dir, "does_not_exist")

        # Should not raise error
        sudo_rmtree(non_existent)

    def test_file_operations_in_sequence(self, temp_dir):
        """Test file operations work in sequence."""
        # Create
        test_dir = os.path.join(temp_dir, "test")
        sudo_makedirs(test_dir)
        assert os.path.isdir(test_dir)

        # Create file
        test_file = os.path.join(test_dir, "file.txt")
        with open(test_file, "w") as f:
            f.write("Content")
        assert os.path.exists(test_file)

        # Delete
        sudo_rmtree(test_dir)
        assert not os.path.exists(test_dir)

    def test_directory_creation_and_deletion_cycle(self, temp_dir):
        """Test create/delete cycle multiple times."""
        for i in range(5):
            test_dir = os.path.join(temp_dir, f"cycle_{i}")
            sudo_makedirs(test_dir)
            assert os.path.isdir(test_dir)
            sudo_rmtree(test_dir)
            assert not os.path.exists(test_dir)

    def test_get_parent_folder_name(self):
        """Test get_parent_folder_name utility function."""
        assert get_parent_folder_name("/home/user/projects/my_project") == "projects"
        assert get_parent_folder_name("/home/user/files") == "user"
        assert get_parent_folder_name("/root") == ""
