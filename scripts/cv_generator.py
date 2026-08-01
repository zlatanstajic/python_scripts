#!/usr/bin/env python3
"""CV generator: convert a Markdown CV into a single-page, ATS-friendly PDF.

The input Markdown file and output PDF file are configured in a `.env` file in
the current working directory:

    MARKDOWN_FILE_URL="cv.md"
    PDF_OUTPUT_LOCATION="cv.pdf"

Experience headings may use ``### Role / Company | Dates``. The text before
the final pipe is aligned left, while the dates are aligned right.
"""

from __future__ import annotations

import os
import sys
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree.ElementTree import Element

import markdown  # type: ignore[import-untyped]
from dotenv import load_dotenv
from markdown.extensions import Extension  # type: ignore[import-untyped]
from markdown.treeprocessors import Treeprocessor  # type: ignore[import-untyped]
from weasyprint import HTML

BASE_CSS = """
@page {
    size: A4;
    margin: 15mm 12mm;
}

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
}

body {
    color: #1a1a1a;
    font-family: Helvetica, Arial, sans-serif;
    font-size: var(--body-font-size);
    line-height: var(--body-line-height);
}

h1 {
    margin: 0 0 var(--space-2);
    font-size: var(--h1-font-size);
    font-weight: 700;
    letter-spacing: 0.6px;
    line-height: 1.1;
    text-align: center;
    text-transform: uppercase;
}

h1 + p {
    margin: 0 0 var(--space-9);
    color: #475569;
    font-size: 9pt;
    line-height: 1.3;
    text-align: center;
}

h2 {
    margin: var(--space-9) 0 var(--space-5);
    padding: 0 0 2px;
    border-bottom: 1px solid #cbd5e1;
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    line-height: 1.2;
    page-break-after: avoid;
    break-after: avoid;
    text-transform: uppercase;
}

h3.experience-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin: var(--space-6) 0 var(--space-1);
    font-size: 10pt;
    line-height: 1.3;
    page-break-after: avoid;
    break-after: avoid;
}

.experience-title {
    flex: 1 1 auto;
    font-weight: 700;
}

.experience-dates {
    flex: 0 0 auto;
    color: #64748b;
    font-size: 9pt;
    font-style: italic;
    font-weight: 400;
    white-space: nowrap;
}

p {
    margin: 0 0 var(--space-5);
    orphans: 2;
    widows: 2;
}

ul,
ol {
    margin: var(--space-2) 0 var(--space-5);
    padding-left: 16px;
}

li {
    margin: 0 0 var(--space-4);
    padding: 0;
}

li:last-child {
    margin-bottom: 0;
}

a {
    color: inherit;
    text-decoration: underline;
}

strong {
    font-weight: 700;
}
"""


@dataclass(frozen=True)
class RenderProfile:
    """Typography and spacing values for one deterministic render attempt."""

    body_font_size: float
    body_line_height: float
    h1_font_size: float
    spacing_scale: float


RENDER_PROFILES = (
    RenderProfile(10.0, 1.45, 19.0, 1.0),
    RenderProfile(9.5, 1.38, 19.0, 0.9),
    RenderProfile(9.0, 1.32, 18.5, 0.8),
    RenderProfile(8.5, 1.25, 18.0, 0.7),
)


def css_for_profile(profile: RenderProfile) -> str:
    """Return the CV stylesheet configured for a render profile."""
    variables = (
        ":root {\n"
        f"    --body-font-size: {profile.body_font_size:g}pt;\n"
        f"    --body-line-height: {profile.body_line_height:g};\n"
        f"    --h1-font-size: {profile.h1_font_size:g}pt;\n"
        f"    --space-1: {profile.spacing_scale:g}px;\n"
        f"    --space-2: {2 * profile.spacing_scale:g}px;\n"
        f"    --space-4: {4 * profile.spacing_scale:g}px;\n"
        f"    --space-5: {5 * profile.spacing_scale:g}px;\n"
        f"    --space-6: {6 * profile.spacing_scale:g}px;\n"
        f"    --space-9: {9 * profile.spacing_scale:g}px;\n"
        "}\n"
    )
    return variables + BASE_CSS


CSS = css_for_profile(RENDER_PROFILES[0])


def _append_text(element: Element, value: str) -> None:
    """Append text after the element's current final content node."""
    if not value:
        return
    if len(element):
        last_child = element[-1]
        last_child.tail = (last_child.tail or "") + value
    else:
        element.text = (element.text or "") + value


def _clone_range(
    element: Element, start: int, end: int, offset: int = 0
) -> tuple[Element | None, int]:
    """Clone the portion of an element whose text overlaps a character range."""
    clone = Element(element.tag, dict(element.attrib))
    cursor = offset

    text = element.text or ""
    text_end = cursor + len(text)
    if start < text_end and end > cursor:
        clone.text = text[max(start - cursor, 0) : min(end - cursor, len(text))]
    cursor = text_end

    for child in element:
        child_clone, cursor = _clone_range(child, start, end, cursor)
        if child_clone is not None:
            clone.append(child_clone)

        tail = child.tail or ""
        tail_end = cursor + len(tail)
        if start < tail_end and end > cursor:
            tail_slice = tail[max(start - cursor, 0) : min(end - cursor, len(tail))]
            _append_text(clone, tail_slice)
        cursor = tail_end

    has_content = bool(clone.text) or bool(len(clone))
    return (clone if has_content else None), cursor


def _copy_heading_range(
    heading: Element, target: Element, start: int, end: int
) -> None:
    """Copy a text range and its inline markup from a heading into a span."""
    clone, _ = _clone_range(deepcopy(heading), start, end)
    if clone is None:
        return
    target.text = clone.text
    for child in list(clone):
        clone.remove(child)
        target.append(child)


class ExperienceHeaderTreeprocessor(Treeprocessor):
    """Turn level-three headings into two-column experience headers."""

    def run(self, root: Element) -> Element:
        """Split each H3 at its final pipe and add layout spans."""
        for heading in root.iter("h3"):
            heading_text = "".join(heading.itertext()).strip()
            separator_index = heading_text.rfind("|")
            has_dates = (
                separator_index > 0
                and bool(heading_text[:separator_index].strip())
                and bool(heading_text[separator_index + 1 :].strip())
            )
            source_heading = deepcopy(heading)
            heading.clear()
            heading.set("class", "experience-header")

            title = Element("span", {"class": "experience-title"})
            title_end = separator_index if has_dates else len(heading_text)
            _copy_heading_range(source_heading, title, 0, title_end)
            heading.append(title)

            if has_dates:
                dates = Element("span", {"class": "experience-dates"})
                _copy_heading_range(
                    source_heading, dates, separator_index + 1, len(heading_text)
                )
                heading.append(dates)

        return root


class ExperienceHeaderExtension(Extension):
    """Register the CV experience-heading transformation."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # noqa: N802
        """Register the tree processor after inline Markdown is parsed."""
        processor = ExperienceHeaderTreeprocessor(md)
        md.treeprocessors.register(processor, "experience_headers", 5)


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


def local_path(value: str, base_directory: Path) -> Path:
    """Resolve a local path or file URL relative to the working directory."""
    parsed = urlparse(value)
    if parsed.scheme and parsed.scheme != "file":
        raise ValueError(f"Only local paths and file URLs are supported: {value}")

    raw_path = unquote(parsed.path) if parsed.scheme == "file" else value
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = base_directory / path
    return path.resolve()


def markdown_to_html(
    markdown_text: str, profile: RenderProfile = RENDER_PROFILES[0]
) -> str:
    """Convert Markdown source to a complete HTML document."""
    body = markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists", ExperienceHeaderExtension()],
        output_format="html5",
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>CV</title>\n"
        f"<style>{css_for_profile(profile)}</style>\n"
        "</head>\n"
        f"<body>{body}</body>\n"
        "</html>"
    )


def generate_pdf(source: Path, destination: Path) -> None:
    """Render one Markdown file as a single-page A4 PDF atomically."""
    if not source.is_file():
        raise FileNotFoundError(f"Markdown file not found: {source}")

    markdown_text = source.read_text(encoding="utf-8")
    document = None
    page_counts = []
    for profile in RENDER_PROFILES:
        html_text = markdown_to_html(markdown_text, profile)
        candidate = HTML(string=html_text, base_url=str(source.parent)).render()
        page_counts.append(len(candidate.pages))
        if len(candidate.pages) == 1:
            document = candidate
            break

    if document is None:
        raise ValueError(
            "The CV could not fit on one page without going below the supported "
            "8.5pt font and 1.25 line-height limits "
            f"(render attempts: {page_counts}). Shorten {source.name}; the existing "
            "output, if any, was left unchanged."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        document.write_pdf(str(temporary_path))
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    """Load configuration and generate the configured CV PDF."""
    try:
        working_directory = Path.cwd()
        load_environment(working_directory / ".env")
        source = local_path(required_setting("MARKDOWN_FILE_URL"), working_directory)
        destination = local_path(
            required_setting("PDF_OUTPUT_LOCATION"), working_directory
        )
        generate_pdf(source, destination)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print("PDF generated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
