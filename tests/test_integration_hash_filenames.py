"""Integration tests for hash_filenames script."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.hash_filenames import (
    generate_random_hash,
    get_file_extensions,
    get_mapping_file_path,
    hash_files,
    is_file_in_mapping,
    is_hashed,
    load_mapping,
    move_hashed_files,
    save_mapping,
)


class TestHashFilenamesIntegration:
    """Integration tests for real file operations in hash_filenames."""

    def test_hash_files_creates_mapping(self, temp_dir, monkeypatch):
        """Test that hash_files creates files and mapping correctly."""
        # Setup
        test_dir = os.path.join(temp_dir, "test_images")
        os.makedirs(test_dir, exist_ok=True)

        # Create test files with target extensions
        test_files = ["image1.jpg", "photo.png", "document.txt"]
        for filename in test_files:
            filepath = os.path.join(test_dir, filename)
            with open(filepath, "w") as f:
                f.write(f"Content of {filename}")

        # Set environment variable
        monkeypatch.setenv("HASH_FILENAMES_FILE_EXTENSIONS", ".jpg,.png,.txt")

        # Execute
        hash_files(test_dir, verbose=True)

        # Verify mapping was created
        mapping_file = get_mapping_file_path(test_dir)
        assert os.path.exists(mapping_file)

        mapping = load_mapping(mapping_file)
        assert len(mapping) > 0
        assert "image1.jpg" in mapping or any("image1" in k for k in mapping.keys())

    def test_hash_files_skips_already_hashed(self, temp_dir, monkeypatch):
        """Test that hash_files skips already hashed files."""
        test_dir = os.path.join(temp_dir, "test_hashed")
        os.makedirs(test_dir, exist_ok=True)

        # Create a file
        filepath = os.path.join(test_dir, "image1.jpg")
        with open(filepath, "w") as f:
            f.write("Image content")

        # Create mapping showing file is already hashed
        mapping_file = get_mapping_file_path(test_dir)
        mapping = {"image1.jpg": "a1b2c3d4e5"}
        save_mapping(mapping_file, mapping)

        monkeypatch.setenv("HASH_FILENAMES_FILE_EXTENSIONS", ".jpg,.png")

        # Hash again
        hash_files(test_dir, verbose=True)

        # Verify file wasn't duplicated in mapping
        updated_mapping = load_mapping(mapping_file)
        assert updated_mapping == mapping

    def test_hash_files_skips_non_target_extensions(self, temp_dir, monkeypatch):
        """Test that hash_files skips files with non-target extensions."""
        test_dir = os.path.join(temp_dir, "test_extensions")
        os.makedirs(test_dir, exist_ok=True)

        # Create files with different extensions
        files = ["image.jpg", "document.pdf", "note.md"]
        for filename in files:
            filepath = os.path.join(test_dir, filename)
            with open(filepath, "w") as f:
                f.write("Content")

        monkeypatch.setenv("HASH_FILENAMES_FILE_EXTENSIONS", ".jpg,.png")

        hash_files(test_dir)

        # Verify only .jpg files are in mapping
        mapping_file = get_mapping_file_path(test_dir)
        mapping = load_mapping(mapping_file)

        # Only image.jpg should be hashed
        assert "image.jpg" in mapping
        assert "document.pdf" not in mapping
        assert "note.md" not in mapping

    def test_load_and_save_mapping_roundtrip(self, temp_dir):
        """Test that mappings can be saved and loaded correctly."""
        mapping_file = os.path.join(temp_dir, "mapping.txt")
        original_mapping = {"file1.jpg": "hash1", "file2.png": "hash2"}

        # Save
        save_mapping(mapping_file, original_mapping)

        # Load
        loaded_mapping = load_mapping(mapping_file)

        # Verify
        assert loaded_mapping == original_mapping

    def test_is_file_in_mapping(self):
        """Test checking if file exists in mapping."""
        mapping = {"file1.jpg": "hash1", "file2.png": "hash2"}

        assert is_file_in_mapping(mapping, "file1.jpg") is True
        assert is_file_in_mapping(mapping, "nonexistent.jpg") is False

    def test_is_hashed_recognizes_hashed_names(self):
        """Test that is_hashed correctly identifies hashed filenames."""
        # 10-character alphanumeric strings should be recognized as hashed
        assert is_hashed("a1b2c3d4e5") is True
        assert is_hashed("aBcDeFgHiJ") is True

        # Other patterns should not be recognized as hashed
        assert is_hashed("image_1234") is False
        assert is_hashed("file-name") is False
        assert is_hashed("short") is False

    def test_generate_random_hash_uniqueness(self):
        """Test that generated hashes are unique."""
        hashes = {generate_random_hash(10) for _ in range(100)}
        assert len(hashes) == 100  # All should be unique

    def test_generate_random_hash_length(self):
        """Test that hash length matches requested length."""
        for length in [5, 10, 15, 20]:
            hash_val = generate_random_hash(length)
            assert len(hash_val) == length

    def test_mapping_file_excluded_from_hashing(self, temp_dir, monkeypatch):
        """Test that the mapping file itself is never hashed."""
        test_dir = os.path.join(temp_dir, "test_mapping_exclude")
        os.makedirs(test_dir, exist_ok=True)

        # Create test file
        filepath = os.path.join(test_dir, "image.jpg")
        with open(filepath, "w") as f:
            f.write("Image")

        monkeypatch.setenv("HASH_FILENAMES_FILE_EXTENSIONS", ".jpg,.txt")

        hash_files(test_dir)

        # Get mapping
        mapping_file = get_mapping_file_path(test_dir)
        mapping = load_mapping(mapping_file)

        # Mapping file itself should never be in the mapping
        assert "hash_filenames_mapping.txt" not in mapping

    def test_empty_directory_handling(self, temp_dir, monkeypatch):
        """Test handling of empty directories."""
        test_dir = os.path.join(temp_dir, "empty_dir")
        os.makedirs(test_dir, exist_ok=True)

        monkeypatch.setenv("HASH_FILENAMES_FILE_EXTENSIONS", ".jpg")

        # Should not raise any errors
        hash_files(test_dir)

        # No mapping should be created for empty directory
        mapping_file = get_mapping_file_path(test_dir)
        if os.path.exists(mapping_file):
            mapping = load_mapping(mapping_file)
            assert len(mapping) == 0

    def test_subdirectory_file_hashing(self, temp_dir, monkeypatch):
        """Test that files in subdirectories are hashed."""
        test_dir = os.path.join(temp_dir, "test_subdirs")
        subdir = os.path.join(test_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)

        # Create files in root and subdirectory
        root_file = os.path.join(test_dir, "root.jpg")
        sub_file = os.path.join(subdir, "sub.jpg")

        with open(root_file, "w") as f:
            f.write("Root image")
        with open(sub_file, "w") as f:
            f.write("Sub image")

        monkeypatch.setenv("HASH_FILENAMES_FILE_EXTENSIONS", ".jpg")

        hash_files(test_dir)

        # Both files should be in mapping
        mapping_file = get_mapping_file_path(test_dir)
        mapping = load_mapping(mapping_file)

        assert "root.jpg" in mapping
        assert "sub.jpg" in mapping
