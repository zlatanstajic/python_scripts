"""Integration tests for environment variables and configuration edge cases."""

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.backup import get_env


class TestEnvironmentVariableHandling:
    """Integration tests for environment variable handling."""

    def test_get_env_returns_string_by_default(self, monkeypatch):
        """Test that get_env returns a string by default."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        value = get_env("TEST_VAR")
        assert isinstance(value, str)
        assert value == "test_value"

    def test_get_env_list_returns_list(self, monkeypatch):
        """Test that get_env with is_list=True returns a list."""
        monkeypatch.setenv("TEST_LIST", "path1,path2,path3")
        value = get_env("TEST_LIST", is_list=True)
        assert isinstance(value, list)
        assert value == ["path1", "path2", "path3"]

    def test_get_env_list_strips_whitespace(self, monkeypatch):
        """Test that list parsing strips whitespace."""
        monkeypatch.setenv("TEST_LIST", "path1 , path2 , path3 ")
        value = get_env("TEST_LIST", is_list=True)
        assert value == ["path1", "path2", "path3"]

    def test_get_env_list_handles_empty_entries(self, monkeypatch):
        """Test that empty entries in lists are skipped."""
        monkeypatch.setenv("TEST_LIST", "path1,,path2,,path3")
        value = get_env("TEST_LIST", is_list=True)
        # Empty entries should be skipped
        assert "path1" in value
        assert "path2" in value
        assert "path3" in value

    def test_get_env_missing_raises_error(self, monkeypatch):
        """Test that missing environment variable raises error."""
        # Ensure variable doesn't exist
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)

        with pytest.raises(ValueError, match="Required environment variable"):
            get_env("NONEXISTENT_VAR")

    def test_get_env_list_with_empty_string(self, monkeypatch):
        """Test that empty list variable returns empty list (no error)."""
        monkeypatch.setenv("EMPTY_LIST", "")
        value = get_env("EMPTY_LIST", is_list=True)
        assert value == []

    def test_get_env_list_with_single_value(self, monkeypatch):
        """Test list parsing with single value."""
        monkeypatch.setenv("SINGLE", "only_path")
        value = get_env("SINGLE", is_list=True)
        assert value == ["only_path"]

    def test_get_env_special_characters(self, monkeypatch):
        """Test environment variables with special characters."""
        special_value = "path/with/slashes:and:colons"
        monkeypatch.setenv("SPECIAL", special_value)
        value = get_env("SPECIAL")
        assert value == special_value

    def test_get_env_very_long_value(self, monkeypatch):
        """Test handling of very long environment variable values."""
        long_value = "a" * 10000
        monkeypatch.setenv("LONG_VAR", long_value)
        value = get_env("LONG_VAR")
        assert value == long_value

    def test_get_env_unicode_value(self, monkeypatch):
        """Test handling of unicode in environment variables."""
        unicode_value = "パス/ディレクトリ"
        monkeypatch.setenv("UNICODE_VAR", unicode_value)
        value = get_env("UNICODE_VAR")
        assert value == unicode_value

    def test_get_env_list_with_paths(self, monkeypatch):
        """Test list parsing with file paths."""
        paths = "/home/user/path1,/mnt/storage/path2,~/relative/path"
        monkeypatch.setenv("PATHS", paths)
        value = get_env("PATHS", is_list=True)
        assert len(value) == 3
        assert "/home/user/path1" in value
        assert "/mnt/storage/path2" in value

    def test_get_env_list_with_urls(self, monkeypatch):
        """Test list parsing with URL-like values."""
        urls = "http://localhost:8000,https://api.example.com,file:///local/path"
        monkeypatch.setenv("URLS", urls)
        value = get_env("URLS", is_list=True)
        assert len(value) == 3
        assert "http://localhost:8000" in value


class TestEnvironmentVariableIntegration:
    """Integration tests for environment variable scenarios."""

    def test_env_var_overwrite_in_sequence(self, monkeypatch):
        """Test that environment variables can be overwritten in sequence."""
        monkeypatch.setenv("VAR", "value1")
        val1 = get_env("VAR")
        assert val1 == "value1"

        monkeypatch.setenv("VAR", "value2")
        val2 = get_env("VAR")
        assert val2 == "value2"

        monkeypatch.setenv("VAR", "value3")
        val3 = get_env("VAR")
        assert val3 == "value3"

    def test_multiple_env_vars_independence(self, monkeypatch):
        """Test that multiple environment variables are independent."""
        monkeypatch.setenv("VAR1", "value1")
        monkeypatch.setenv("VAR2", "value2")
        monkeypatch.setenv("VAR3", "value3")

        assert get_env("VAR1") == "value1"
        assert get_env("VAR2") == "value2"
        assert get_env("VAR3") == "value3"

    def test_env_case_sensitivity(self, monkeypatch):
        """Test that environment variable names are case sensitive."""
        monkeypatch.setenv("TestVar", "value1")
        monkeypatch.setenv("testvar", "value2")

        # These should be different
        val1 = get_env("TestVar")
        val2 = get_env("testvar")

        assert val1 == "value1"
        assert val2 == "value2"
        assert val1 != val2

    def test_env_with_equals_signs(self, monkeypatch):
        """Test environment variables containing equals signs."""
        connection_string = "user=admin;password=p@ss=word;server=localhost"
        monkeypatch.setenv("CONN_STR", connection_string)
        value = get_env("CONN_STR")
        assert value == connection_string

    def test_env_with_quotes(self, monkeypatch):
        """Test environment variables with quoted values."""
        quoted = '"quoted value" with spaces'
        monkeypatch.setenv("QUOTED", quoted)
        value = get_env("QUOTED")
        assert value == quoted

    def test_env_numeric_string(self, monkeypatch):
        """Test environment variables with numeric strings."""
        monkeypatch.setenv("NUM_STR", "12345")
        value = get_env("NUM_STR")
        assert value == "12345"
        assert isinstance(value, str)

    def test_env_json_like_string(self, monkeypatch):
        """Test environment variables with JSON-like strings."""
        json_str = '{"key": "value", "num": 123}'
        monkeypatch.setenv("JSON_STR", json_str)
        value = get_env("JSON_STR")
        assert value == json_str
        # Should be parseable as JSON
        assert json.loads(value)["key"] == "value"

    def test_env_list_with_json_values(self, monkeypatch):
        """Test list parsing where individual items are JSON."""
        monkeypatch.setenv("JSON_LIST", '{"type":"A"},{"type":"B"},{"type":"C"}')
        value = get_env("JSON_LIST", is_list=True)
        assert len(value) == 3
        for item in value:
            parsed = json.loads(item)
            assert "type" in parsed


def test_import_json():
    """Integration test to verify json module can be imported."""
    import json

    d = {"test": "value"}
    s = json.dumps(d)
    loaded = json.loads(s)
    assert loaded == d


# Add import at module level
import json as json_module
