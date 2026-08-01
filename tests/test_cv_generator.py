"""Focused tests for the Markdown CV generator."""

from pathlib import Path

import pytest

from scripts import cv_generator


def test_experience_heading_preserves_inline_markup_and_links() -> None:
    """The split experience header keeps Markdown-generated inline elements."""
    html = cv_generator.markdown_to_html(
        "### [Engineer](https://example.com) / **Example Co** | *2020–2024*"
    )

    assert '<a href="https://example.com">Engineer</a>' in html
    assert "<strong>Example Co</strong>" in html
    assert '<span class="experience-dates"> <em>2020–2024</em></span>' in html


def test_load_environment_uses_dotenv_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quoted values, interpolation, comments, and overrides follow dotenv."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        'CV_ROOT="documents" # comment\n'
        'MARKDOWN_FILE_URL="${CV_ROOT}/cv.md"\n'
        "PDF_OUTPUT_LOCATION='generated cv.pdf'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CV_ROOT", "existing")
    monkeypatch.delenv("MARKDOWN_FILE_URL", raising=False)
    monkeypatch.delenv("PDF_OUTPUT_LOCATION", raising=False)

    cv_generator.load_environment(env_file)

    assert cv_generator.required_setting("CV_ROOT") == "existing"
    assert cv_generator.required_setting("MARKDOWN_FILE_URL") == "existing/cv.md"
    assert cv_generator.required_setting("PDF_OUTPUT_LOCATION") == "generated cv.pdf"


class _FakeDocument:
    """Minimal WeasyPrint document substitute."""

    def __init__(self, page_count: int, payload: bytes = b"new PDF") -> None:
        self.pages = [object()] * page_count
        self.payload = payload

    def write_pdf(self, destination: str) -> None:
        """Write a recognizable payload to the requested temporary path."""
        Path(destination).write_bytes(self.payload)


def test_generate_pdf_uses_next_fit_profile_and_replaces_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later one-page profile succeeds without writing candidates directly."""
    source = tmp_path / "cv.md"
    destination = tmp_path / "cv.pdf"
    source.write_text("# Candidate", encoding="utf-8")
    destination.write_bytes(b"old PDF")
    documents = iter((_FakeDocument(2), _FakeDocument(1)))

    class FakeHTML:
        """Return the configured fake documents in render order."""

        def __init__(self, **_: object) -> None:
            pass

        def render(self) -> _FakeDocument:
            return next(documents)

    monkeypatch.setattr(cv_generator, "HTML", FakeHTML)

    cv_generator.generate_pdf(source, destination)

    assert destination.read_bytes() == b"new PDF"
    assert not list(tmp_path.glob(".cv.pdf.*.tmp"))


def test_generate_pdf_preserves_existing_output_when_no_profile_fits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fit failure reports limits and never modifies an existing PDF."""
    source = tmp_path / "cv.md"
    destination = tmp_path / "cv.pdf"
    source.write_text("# Candidate", encoding="utf-8")
    destination.write_bytes(b"old PDF")

    class FakeHTML:
        """Always produce a two-page candidate."""

        def __init__(self, **_: object) -> None:
            pass

        def render(self) -> _FakeDocument:
            return _FakeDocument(2)

    monkeypatch.setattr(cv_generator, "HTML", FakeHTML)

    with pytest.raises(ValueError, match="8.5pt font"):
        cv_generator.generate_pdf(source, destination)

    assert destination.read_bytes() == b"old PDF"
    assert not list(tmp_path.glob(".cv.pdf.*.tmp"))


def test_generate_pdf_renders_a_real_pdf(tmp_path: Path) -> None:
    """The real renderer produces a PDF for a compact Markdown CV."""
    source = tmp_path / "cv.md"
    destination = tmp_path / "cv.pdf"
    source.write_text(
        "# Candidate Name\n\n"
        "candidate@example.com | +1 555 0100 | Example City\n\n"
        "## Experience\n\n"
        "### [Engineer](https://example.com) / Example Co | 2022–Present\n\n"
        "- Built reliable software.\n",
        encoding="utf-8",
    )

    cv_generator.generate_pdf(source, destination)

    assert destination.read_bytes().startswith(b"%PDF-")
