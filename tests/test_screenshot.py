"""Focused tests for the website screenshot script."""

import sys
from pathlib import Path

import pytest

from scripts import screenshot


def _write_env(directory: Path, content: str) -> None:
    """Write a `.env` file with the given content into a directory."""
    (directory / ".env").write_text(content, encoding="utf-8")


@pytest.fixture
def env_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return an isolated working directory without inherited settings."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SCREENSHOT_SITES", raising=False)
    monkeypatch.delenv("SCREENSHOT_OUTPUT_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path


def test_load_config_parses_sites_and_creates_output_directory(
    env_directory: Path,
) -> None:
    """Whitespace is stripped, empty entries drop out, and the directory appears."""
    output_directory = env_directory / "images" / "shots"
    _write_env(
        env_directory,
        'SCREENSHOT_SITES=" https://example.com , ,https://example.org/page "\n'
        f'SCREENSHOT_OUTPUT_DIR="{output_directory}"\n',
    )

    sites, resolved_directory = screenshot.load_config()

    assert sites == ["https://example.com", "https://example.org/page"]
    assert resolved_directory == output_directory
    assert output_directory.is_dir()


def test_load_config_requires_sites(env_directory: Path) -> None:
    """A `.env` without the site list names the missing setting."""
    _write_env(env_directory, 'SCREENSHOT_OUTPUT_DIR="shots"\n')

    with pytest.raises(ValueError, match="SCREENSHOT_SITES"):
        screenshot.load_config()


def test_load_config_rejects_empty_sites(env_directory: Path) -> None:
    """A whitespace-only site list is treated as missing."""
    _write_env(env_directory, 'SCREENSHOT_SITES="   "\n')

    with pytest.raises(ValueError, match="SCREENSHOT_SITES"):
        screenshot.load_config()


def test_load_config_rejects_a_list_of_separators_only(env_directory: Path) -> None:
    """Commas without any URL report an empty site list."""
    _write_env(env_directory, 'SCREENSHOT_SITES=" , , "\n')

    with pytest.raises(ValueError, match="No websites listed"):
        screenshot.load_config()


@pytest.mark.parametrize("site", ["example.com", "ftp://example.com", "https://"])
def test_load_config_rejects_malformed_urls(env_directory: Path, site: str) -> None:
    """A URL without an http(s) scheme and hostname is rejected by name."""
    _write_env(env_directory, f'SCREENSHOT_SITES="{site}"\n')

    with pytest.raises(ValueError, match="Invalid website URL"):
        screenshot.load_config()


def test_load_config_missing_env_file_is_reported(env_directory: Path) -> None:
    """A working directory without a `.env` file raises a clear error."""
    with pytest.raises(FileNotFoundError, match=".env"):
        screenshot.load_config()


@pytest.mark.parametrize("configured", ["", '""', '"   "'])
def test_load_config_falls_back_to_the_default_directory(
    env_directory: Path, configured: str
) -> None:
    """Unset, empty, and whitespace-only values resolve the home-based default."""
    lines = ['SCREENSHOT_SITES="https://example.com"']
    if configured:
        lines.append(f"SCREENSHOT_OUTPUT_DIR={configured}")
    _write_env(env_directory, "\n".join(lines) + "\n")

    _, resolved_directory = screenshot.load_config()

    expected = env_directory / "home" / "Pictures"
    assert resolved_directory == expected
    assert expected.is_dir()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com", "example.com.jpg"),
        ("https://www.example.com/", "www.example.com.jpg"),
        ("https://subdomain.example.com/page", "subdomain.example.com.jpg"),
        ("https://zlatanstajic.github.io/shell-scripts/", "shell-scripts.jpg"),
        ("https://zlatanstajic.github.io/shell-scripts", "shell-scripts.jpg"),
        ("https://zlatanstajic.github.io/python_scripts/", "python-scripts.jpg"),
        ("https://zlatanstajic.github.io/_leading/", "-leading.jpg"),
        ("https://zlatanstajic.github.io/", "zlatanstajic.github.io.jpg"),
        ("https://zlatanstajic.github.io", "zlatanstajic.github.io.jpg"),
        ("https://zlatanstajic.github.io/../etc/", "zlatanstajic.github.io.jpg"),
    ],
)
def test_hostname_to_filename(url: str, expected: str) -> None:
    """The hostname names the file, except GitHub Pages repository sites."""
    filename = screenshot.hostname_to_filename(url)

    assert filename == expected
    assert filename.endswith(".jpg")


def test_hostname_to_filename_rejects_a_url_without_a_hostname() -> None:
    """A URL that carries no hostname raises instead of writing a bare `.jpg`."""
    with pytest.raises(ValueError, match="Invalid website URL"):
        screenshot.hostname_to_filename("not a url")


class _FakePage:
    """Record selector evaluations and fail for one configured selector."""

    def __init__(self, failing_selector: str) -> None:
        self.failing_selector = failing_selector
        self.selectors: list[str] = []

    def eval_on_selector_all(self, selector: str, expression: str) -> None:
        """Record the selector, raising for the configured failure case."""
        self.selectors.append(selector)
        if selector == self.failing_selector:
            raise RuntimeError(f"unsupported selector: {selector}")


def test_hide_cookie_banners_tries_every_selector_despite_failures() -> None:
    """A selector that raises does not stop the remaining removals."""
    failing_selector = screenshot.COOKIE_BANNER_SELECTORS[0]
    page = _FakePage(failing_selector)

    screenshot.hide_cookie_banners(page)  # type: ignore[arg-type]

    assert page.selectors == list(screenshot.COOKIE_BANNER_SELECTORS)


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_parse_arguments_help_exits_zero_with_usage(
    flag: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both help flags print a usage block naming both settings and exit 0."""
    monkeypatch.setattr(sys, "argv", ["screenshot.py", flag])

    with pytest.raises(SystemExit) as exit_info:
        screenshot.parse_arguments()

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "SCREENSHOT_SITES" in captured.out
    assert "SCREENSHOT_OUTPUT_DIR" in captured.out


def test_parse_arguments_rejects_an_unknown_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unrecognised argument exits 2 with a usage message on stderr."""
    monkeypatch.setattr(sys, "argv", ["screenshot.py", "--bogus"])

    with pytest.raises(SystemExit) as exit_info:
        screenshot.parse_arguments()

    assert exit_info.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_parse_arguments_accepts_no_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bare invocation parses cleanly and yields nothing to read."""
    monkeypatch.setattr(sys, "argv", ["screenshot.py"])

    assert screenshot.parse_arguments() is None
