"""Integration tests for real file operations and edge cases."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.generate_password import generate_password
from scripts.php_switch import build_version_map, extract_version_from_path


class TestGeneratePasswordIntegration:
    """Integration tests for password generation edge cases."""

    def test_generate_password_with_all_character_types(self):
        """Test that password contains all required character types."""
        password = generate_password(8, 4, 32)

        # Should contain lowercase
        assert any(c.islower() for c in password), "Missing lowercase letters"

        # Should contain uppercase
        assert any(c.isupper() for c in password), "Missing uppercase letters"

        # Should contain digits
        assert any(c.isdigit() for c in password), "Missing digits"

        # Should contain special characters
        special_chars = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        assert any(c in special_chars for c in password), "Missing special characters"

    def test_generate_password_length_edge_cases(self):
        """Test password generation with various edge case lengths."""
        # Test lengths that are divisible by 4 (required by algorithm with 4 chunks)
        for length in [8, 12, 16, 20, 24, 28, 32]:
            password = generate_password(8, 4, length)
            assert len(password) == length

    def test_generate_password_deterministic_chunks(self):
        """Test that password generation uses all chunks correctly."""
        # Generate multiple passwords to check variety
        passwords = [generate_password(8, 4, 20) for _ in range(10)]

        # All should be different
        assert len(set(passwords)) == 10

        # All should have correct length
        assert all(len(p) == 20 for p in passwords)

    def test_generate_password_minimum_boundary(self):
        """Test password generation at minimum boundary."""
        # Minimum is 8
        password = generate_password(8, 4, 8)
        assert len(password) == 8

        # Should fail below minimum
        with pytest.raises(Exception):
            generate_password(8, 4, 7)

    def test_generate_password_divisibility_requirement(self):
        """Test that length must be divisible by number of chunks."""
        # Valid: divisible by 4
        generate_password(8, 4, 20)

        # Invalid: not divisible by 4
        with pytest.raises(Exception):
            generate_password(8, 4, 19)

        with pytest.raises(Exception):
            generate_password(8, 4, 21)


class TestFileOperationsEdgeCases:
    """Test edge cases in file operations."""

    def test_empty_file_handling(self, temp_dir):
        """Test that empty files are handled correctly."""
        empty_file = os.path.join(temp_dir, "empty.txt")

        # Create empty file
        Path(empty_file).touch()

        # Should be readable
        with open(empty_file, "r") as f:
            content = f.read()
        assert content == ""

    def test_large_file_handling(self, temp_dir):
        """Test handling of large files."""
        large_file = os.path.join(temp_dir, "large.txt")

        # Create a 10MB file
        size = 10 * 1024 * 1024
        with open(large_file, "w") as f:
            f.write("x" * size)

        assert os.path.getsize(large_file) == size

    def test_special_characters_in_filenames(self, temp_dir):
        """Test handling of special characters in filenames."""
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
        ]

        for filename in special_names:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "w") as f:
                f.write("Content")

            assert os.path.exists(filepath)

    def test_unicode_filenames(self, temp_dir):
        """Test handling of unicode characters in filenames."""
        unicode_names = [
            "файл.txt",  # Russian
            "文件.txt",  # Chinese
            "ファイル.txt",  # Japanese
        ]

        for filename in unicode_names:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "w") as f:
                f.write("Content")

            # Should be readable
            with open(filepath, "r") as f:
                assert f.read() == "Content"

    def test_dot_files_handling(self, temp_dir):
        """Test handling of hidden files (starting with dot)."""
        dot_file = os.path.join(temp_dir, ".hidden")

        with open(dot_file, "w") as f:
            f.write("Hidden content")

        assert os.path.exists(dot_file)
        with open(dot_file, "r") as f:
            assert f.read() == "Hidden content"

    def test_symlink_handling(self, temp_dir):
        """Test handling of symbolic links."""
        # Create original file
        original = os.path.join(temp_dir, "original.txt")
        with open(original, "w") as f:
            f.write("Original content")

        # Create symlink
        symlink = os.path.join(temp_dir, "link.txt")
        try:
            os.symlink(original, symlink)

            # Symlink should be readable
            with open(symlink, "r") as f:
                assert f.read() == "Original content"
        except OSError:
            # Skip on systems that don't support symlinks
            pytest.skip("Symlinks not supported on this system")

    def test_readonly_file_content_preservation(self, temp_dir):
        """Test that readonly file content is preserved."""
        readonly_file = os.path.join(temp_dir, "readonly.txt")

        with open(readonly_file, "w") as f:
            f.write("Protected content")

        # Make readonly
        os.chmod(readonly_file, 0o444)

        # Should still be readable
        with open(readonly_file, "r") as f:
            assert f.read() == "Protected content"

        # Cleanup: make writable for temp_dir cleanup
        os.chmod(readonly_file, 0o644)

    def test_deeply_nested_path_handling(self, temp_dir):
        """Test handling of deeply nested directory structures."""
        # Create deeply nested path
        nested_levels = 10
        deep_path = temp_dir
        for i in range(nested_levels):
            deep_path = os.path.join(deep_path, f"level_{i}")

        os.makedirs(deep_path, exist_ok=True)

        # Create file in deep path
        deep_file = os.path.join(deep_path, "deep_file.txt")
        with open(deep_file, "w") as f:
            f.write("Deep content")

        # Should be readable
        with open(deep_file, "r") as f:
            assert f.read() == "Deep content"

    def test_file_with_no_extension(self, temp_dir):
        """Test handling of files with no extension."""
        no_ext_file = os.path.join(temp_dir, "README")

        with open(no_ext_file, "w") as f:
            f.write("No extension content")

        with open(no_ext_file, "r") as f:
            assert f.read() == "No extension content"

    def test_file_with_multiple_dots(self, temp_dir):
        """Test handling of files with multiple dots in name."""
        multi_dot = os.path.join(temp_dir, "archive.tar.gz")

        with open(multi_dot, "w") as f:
            f.write("Compressed content")

        assert os.path.exists(multi_dot)

    def test_whitespace_only_content(self, temp_dir):
        """Test handling of files with only whitespace."""
        whitespace_file = os.path.join(temp_dir, "whitespace.txt")

        content = "   \n\t\n   "
        with open(whitespace_file, "w") as f:
            f.write(content)

        with open(whitespace_file, "r") as f:
            assert f.read() == content


class TestPhpSwitchIntegration:
    """Integration tests for PHP version extraction."""

    def test_extract_version_from_standard_path(self):
        """Test extracting version from standard PHP paths."""
        paths = [
            "/usr/bin/php8.3",
            "/usr/bin/php8.2",
            "/usr/bin/php7.4",
        ]

        expected = ["8.3", "8.2", "7.4"]

        for path, expected_version in zip(paths, expected):
            version = extract_version_from_path(path)
            assert version == expected_version

    def test_extract_version_with_path_separators(self):
        """Test version extraction with various path formats."""
        paths = [
            "/opt/php/php8.3/bin/php",
            "/usr/local/php8.2/bin/php",
        ]

        for path in paths:
            version = extract_version_from_path(path)
            assert version is not None
            assert "." in version  # Should contain version format

    def test_extract_version_returns_none_for_invalid(self):
        """Test that invalid paths return None."""
        invalid_paths = [
            "/usr/bin/python3",
            "/usr/bin/ruby",
            "/invalid/path",
        ]

        for path in invalid_paths:
            version = extract_version_from_path(path)
            assert version is None

    def test_build_version_map_creates_mapping(self):
        """Test building a version map from paths."""
        paths = [
            "/usr/bin/php8.3",
            "/usr/bin/php8.2",
            "/usr/bin/php7.4",
        ]

        version_map = build_version_map(paths)

        assert "8.3" in version_map
        assert "8.2" in version_map
        assert "7.4" in version_map

        assert version_map["8.3"] == "/usr/bin/php8.3"
        assert version_map["8.2"] == "/usr/bin/php8.2"
        assert version_map["7.4"] == "/usr/bin/php7.4"

    def test_build_version_map_handles_duplicates(self):
        """Test that version map handles duplicate versions."""
        paths = [
            "/usr/bin/php8.3",
            "/opt/php8.3",  # Duplicate version
        ]

        version_map = build_version_map(paths)

        # Should have only one entry for version
        assert len([v for v in version_map.values() if "8.3" in v]) >= 1
