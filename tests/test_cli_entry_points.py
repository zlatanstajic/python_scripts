"""Tests for the installable console-script entry points."""

import importlib
import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from scripts import cv_generator, screenshot, video_organizer

DISTRIBUTION_NAME = "python-scripts"

CONSOLE_SCRIPTS = {
    "cv-generator": cv_generator.main,
    "video-organizer": video_organizer.main,
    "website-screenshot": screenshot.main,
}

EXPECTED_TARGETS = {
    "cv-generator": "scripts.cv_generator:main",
    "video-organizer": "scripts.video_organizer:main",
    "website-screenshot": "scripts.screenshot:main",
}


def _pyproject_path() -> Path:
    """Return `pyproject.toml` found by walking up from this test file."""
    for directory in Path(__file__).resolve().parents:
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    raise AssertionError("pyproject.toml not found above the test file")


def _console_script(name: str) -> Path:
    """Return the installed console script, skipping when it is absent."""
    candidate = Path(sys.executable).parent / name
    if candidate.exists():
        return candidate
    resolved = shutil.which(name)
    if resolved:
        return Path(resolved)
    pytest.skip(f"console script not installed: {name}")


@pytest.mark.parametrize("module", [cv_generator, screenshot, video_organizer])
def test_module_exposes_a_callable_main(module: ModuleType) -> None:
    """All command modules import cleanly and expose a callable `main`."""
    assert hasattr(module, "main")
    assert callable(module.main)


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib needs Python 3.11")
def test_project_scripts_targets_resolve_to_the_real_functions() -> None:
    """The declared `[project.scripts]` targets point at the imported functions."""
    import tomllib

    declared = tomllib.loads(_pyproject_path().read_text(encoding="utf-8"))
    targets = declared["project"]["scripts"]

    assert targets == EXPECTED_TARGETS

    for name, target in targets.items():
        module_name, _, attribute = target.partition(":")
        module = importlib.import_module(module_name)
        assert getattr(module, attribute) is CONSOLE_SCRIPTS[name]


def test_installed_console_script_metadata_matches_the_functions() -> None:
    """Current installed metadata declares and loads all three commands."""
    distributions = list(importlib.metadata.distributions(name=DISTRIBUTION_NAME))
    if not distributions:
        pytest.skip(f"distribution not installed: {DISTRIBUTION_NAME}")

    entry_point_sets = [
        {
            entry_point.name: entry_point
            for entry_point in distribution.entry_points
            if entry_point.group == "console_scripts"
        }
        for distribution in distributions
    ]
    entry_points = next(
        (
            candidates
            for candidates in entry_point_sets
            if set(candidates) == set(CONSOLE_SCRIPTS)
        ),
        None,
    )

    assert entry_points is not None

    for name, entry_point in entry_points.items():
        assert entry_point.value == EXPECTED_TARGETS[name]
        assert entry_point.load() is CONSOLE_SCRIPTS[name]


@pytest.mark.parametrize("name", sorted(CONSOLE_SCRIPTS))
def test_console_script_help_exits_zero_from_any_directory(
    name: str, tmp_path: Path
) -> None:
    """Each installed command prints usage and exits 0 outside the repository."""
    executable = _console_script(name)

    result = subprocess.run(
        [str(executable), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
