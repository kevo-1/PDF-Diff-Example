"""
Shared pytest fixtures for web-monitoring-pdf-diff tests.

Generates sample PDF documents using PyMuPDF so tests don't depend on
external files.
"""

import fitz  # PyMuPDF
import pytest


def _make_pdf(text: str) -> bytes:
    """Create a minimal single-page PDF containing the given text."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def sample_pdf():
    """A simple one-page PDF with known text."""
    return _make_pdf(
        "The quick brown fox jumps over the lazy dog. "
        "This is a sample document for testing PDF comparison."
    )


@pytest.fixture
def modified_pdf():
    """A modified version of the sample PDF with known differences."""
    return _make_pdf(
        "The quick red fox leaps over the lazy cat. "
        "This is a modified document for testing PDF comparison."
    )


@pytest.fixture
def identical_pdf():
    """Same text as sample_pdf, for identity tests."""
    return _make_pdf(
        "The quick brown fox jumps over the lazy dog. "
        "This is a sample document for testing PDF comparison."
    )


@pytest.fixture
def empty_pdf():
    """A PDF with no text content."""
    return _make_pdf("")


@pytest.fixture
def multi_page_pdf():
    """A multi-page PDF."""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"Page {i + 1} content here.", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
