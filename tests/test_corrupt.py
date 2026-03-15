"""
Tests for corrupt / malformed PDF inputs.

Verifies that ``pdf_text_diff`` raises ``UndiffableContentError`` when
given bytes that are not valid PDF documents.

Corrupt data is generated programmatically so the tests are fully
self-contained — no external files required.
"""

import os

import fitz  # PyMuPDF
import pytest

from web_monitoring_pdf_diff import pdf_text_diff, UndiffableContentError


# ---------------------------------------------------------------------------
# Corrupt byte sequences, generated inline
# ---------------------------------------------------------------------------

CORRUPT_INPUTS = {
    "truncated_pdf": (
        b"%PDF-1.4 CORRUPTED HEADER NO VALID OBJECTS"
        b"\x00\x01\x02\x03\xff\xfe\xfd"
    ),
    "random_garbage": os.urandom(512),
    "empty_bytes": b"",
    "null_bytes": b"\x00" * 256,
}


@pytest.fixture
def valid_pdf():
    """Minimal valid PDF for the 'other side' of the diff."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Valid document.", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestCorruptPDFs:
    """Corrupt / malformed inputs must raise UndiffableContentError."""

    @pytest.mark.parametrize("label, data", CORRUPT_INPUTS.items())
    def test_corrupt_as_old_pdf(self, label, data, valid_pdf):
        """Corrupt data as the 'old' input should raise."""
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(data, valid_pdf)

    @pytest.mark.parametrize("label, data", CORRUPT_INPUTS.items())
    def test_corrupt_as_new_pdf(self, label, data, valid_pdf):
        """Corrupt data as the 'new' input should raise."""
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(valid_pdf, data)

    @pytest.mark.parametrize("label, data", CORRUPT_INPUTS.items())
    def test_corrupt_both_inputs(self, label, data):
        """Both inputs corrupt should raise."""
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(data, data)
