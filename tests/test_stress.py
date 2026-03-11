"""
Stress / large-PDF tests for web-monitoring-pdf-diff.

These tests generate large PDFs at runtime (rather than committing
multi-megabyte binaries) and verify that ``pdf_text_diff`` handles
them correctly within reasonable time.
"""

import fitz  # PyMuPDF
import pytest

from web_monitoring_pdf_diff import pdf_text_diff


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LARGE_PAGE_COUNT = 500

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
    "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
    "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
    "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
    "culpa qui officia deserunt mollit anim id est laborum."
)


@pytest.fixture(scope="module")
def large_pdf():
    """Generate a 500-page PDF at runtime."""
    doc = fitz.open()
    for i in range(LARGE_PAGE_COUNT):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"Page {i + 1}: {LOREM}", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture(scope="module")
def large_pdf_modified():
    """
    A variant of the large PDF with small changes on a handful of pages.
    """
    doc = fitz.open()
    for i in range(LARGE_PAGE_COUNT):
        text = f"Page {i + 1}: {LOREM}"
        # Change every 100th page
        if (i + 1) % 100 == 0:
            text = f"Page {i + 1}: MODIFIED — {LOREM[:100]}"
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLargePDFs:
    """Stress tests with programmatically generated large PDFs."""

    def test_large_pdf_identical(self, large_pdf):
        """Identical 500-page PDFs should report zero changes."""
        result = pdf_text_diff(large_pdf, large_pdf)
        assert result["change_count"] == 0
        assert isinstance(result["diff"], list)

    def test_large_pdf_with_changes(self, large_pdf, large_pdf_modified):
        """Diffing two 500-page PDFs with minor edits should succeed."""
        result = pdf_text_diff(large_pdf, large_pdf_modified)
        assert result["change_count"] > 0
        assert isinstance(result["diff"], list)
        # Verify output format
        for entry in result["diff"]:
            assert isinstance(entry, list)
            assert len(entry) == 2
            assert entry[0] in {-1, 0, 1}
            assert isinstance(entry[1], str)

    def test_large_pdf_output_has_required_keys(self, large_pdf):
        """Output schema should always have 'diff' and 'change_count'."""
        result = pdf_text_diff(large_pdf, large_pdf)
        assert "diff" in result
        assert "change_count" in result
