#!/usr/bin/env python3
"""Website screenshot: capture one 1600x900 desktop JPEG per configured site.

The site list and the output directory are configured in a `.env` file in the
current working directory:

    SCREENSHOT_SITES="https://example.com,https://example.org"
    SCREENSHOT_OUTPUT_DIR="/home/your-username/Pictures"

`SCREENSHOT_SITES` is a comma-separated list of `http`/`https` URLs and is
required. `SCREENSHOT_OUTPUT_DIR` is optional and defaults to ``~/Pictures``;
the directory is created when absent.

Each site is captured in a fresh Chromium context sized to a 1600x900 viewport
at scale factor 1, and the visible viewport is written as
``<hostname>.jpg``, overwriting the file from the previous run.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.sync_api import Browser, Page, sync_playwright

VIEWPORT_WIDTH = 1600
VIEWPORT_HEIGHT = 900
DEVICE_SCALE_FACTOR = 1
NAVIGATION_TIMEOUT_MS = 60000
SETTLE_DELAY_MS = 500
JPEG_QUALITY = 85

DISABLE_ANIMATIONS_CSS = """
*,
*::before,
*::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
}
"""

REMOVE_ELEMENTS_SCRIPT = "elements => elements.forEach(element => element.remove())"

COOKIE_BANNER_SELECTORS: tuple[str, ...] = (
    "#onetrust-consent-sdk",
    "#CybotCookiebotDialog",
    "#usercentrics-root",
    "#cookiescript_injected",
    ".cc-window",
    ".cookie-banner",
    ".cookie-consent",
    ".cookie-notice",
    "[id*='cookie-banner']",
    "[class*='cookie-consent']",
    '[aria-label*="cookie" i]',
)


def load_environment(env_file: Path) -> None:
    """Load an environment file using standard python-dotenv semantics.

    Existing environment variables take precedence over values in the file.
    """
    if not env_file.is_file():
        raise FileNotFoundError(f"Environment file not found: {env_file}")
    load_dotenv(dotenv_path=env_file, override=False)


def required_setting(name: str) -> str:
    """Return a required environment setting or raise a clear error."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required .env setting: {name}")
    return value


def default_output_directory() -> Path:
    """Return the screenshot directory used when none is configured."""
    return Path.home() / "Pictures"


def parse_sites(value: str) -> list[str]:
    """Return the validated website URLs listed in a comma-separated value."""
    sites = [entry.strip() for entry in value.split(",")]
    sites = [entry for entry in sites if entry]
    if not sites:
        raise ValueError("No websites listed in .env setting: SCREENSHOT_SITES")

    for site in sites:
        parsed = urlparse(site)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"Invalid website URL in SCREENSHOT_SITES: {site}")
    return sites


def load_config() -> tuple[list[str], Path]:
    """Return the configured sites and the prepared output directory."""
    working_directory = Path.cwd()
    load_environment(working_directory / ".env")

    sites = parse_sites(required_setting("SCREENSHOT_SITES"))

    configured_directory = os.environ.get("SCREENSHOT_OUTPUT_DIR", "").strip()
    if configured_directory:
        output_directory = Path(configured_directory).expanduser()
    else:
        output_directory = default_output_directory()
    output_directory.mkdir(parents=True, exist_ok=True)

    return sites, output_directory


def hostname_to_filename(url: str) -> str:
    """Return the `<hostname>.jpg` filename for a website URL."""
    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError(f"Invalid website URL: {url}")
    return f"{hostname}.jpg"


def hide_cookie_banners(page: Page) -> None:
    """Remove known cookie-banner elements, ignoring selectors that fail."""
    for selector in COOKIE_BANNER_SELECTORS:
        try:
            page.eval_on_selector_all(selector, REMOVE_ELEMENTS_SCRIPT)
        except Exception:
            continue


def capture_website(browser: Browser, url: str, output_directory: Path) -> None:
    """Capture one website as a 1600x900 JPEG in the output directory."""
    destination = output_directory / hostname_to_filename(url)
    context = browser.new_context(
        viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        device_scale_factor=DEVICE_SCALE_FACTOR,
    )
    try:
        page = context.new_page()
        page.emulate_media(reduced_motion="reduce")
        page.goto(url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT_MS)
        page.add_style_tag(content=DISABLE_ANIMATIONS_CSS)
        hide_cookie_banners(page)
        page.wait_for_timeout(SETTLE_DELAY_MS)
        page.screenshot(
            path=str(destination),
            type="jpeg",
            quality=JPEG_QUALITY,
            full_page=False,
            animations="disabled",
        )
    finally:
        context.close()


def parse_arguments() -> None:
    """Parse command-line arguments, providing `-h`/`--help` and rejecting others."""
    parser = argparse.ArgumentParser(
        description="Capture one 1600x900 desktop JPEG per website listed in "
        "SCREENSHOT_SITES, saved to SCREENSHOT_OUTPUT_DIR (default ~/Pictures). "
        "Both settings are read from the .env file in the current working directory."
    )
    parser.parse_args()


def main() -> int:
    """Capture every configured website and report the per-site outcome."""
    parse_arguments()

    try:
        sites, output_directory = load_config()
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    succeeded = 0
    failed = 0
    try:
        with sync_playwright() as engine:
            browser = engine.chromium.launch(headless=True)
            try:
                for site in sites:
                    try:
                        capture_website(browser, site, output_directory)
                    except Exception as error:
                        failed += 1
                        print(f"[FAILED] {site}")
                        print(f"Error: {error}", file=sys.stderr)
                    else:
                        succeeded += 1
                        print(f"[OK] {site}")
            finally:
                browser.close()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Finished: {succeeded} succeeded, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
