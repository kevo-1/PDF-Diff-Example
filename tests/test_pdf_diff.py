"""
Unit tests for web-monitoring-pdf-diff.

Validates that:
  - Output format matches web-monitoring-diff conventions.
  - Identical PDFs produce zero changes.
  - Different PDFs produce expected changes.
  - Invalid input raises UndiffableContentError.
"""

from web_monitoring_pdf_diff import pdf_text_diff, UndiffableContentError
import pytest

# TODO: Add new fields to the tests
class TestOutputFormat:
    """Verify the output dict matches web-monitoring-diff's contract."""

    def test_output_has_diff_key(self, sample_pdf, modified_pdf):
        result = pdf_text_diff(sample_pdf, modified_pdf)
        assert "diff" in result

    def test_output_has_change_count(self, sample_pdf, modified_pdf):
        result = pdf_text_diff(sample_pdf, modified_pdf)
        assert "change_count" in result
        assert isinstance(result["change_count"], int)

    def test_diff_is_list(self, sample_pdf, modified_pdf):
        result = pdf_text_diff(sample_pdf, modified_pdf)
        assert isinstance(result["diff"], list)

    def test_diff_entries_are_pairs(self, sample_pdf, modified_pdf):
        result = pdf_text_diff(sample_pdf, modified_pdf)
        for entry in result["diff"]:
            assert isinstance(entry, list), f"Expected list, got {type(entry)}"
            assert len(entry) == 2, f"Expected pair, got length {len(entry)}"

    def test_change_types_valid(self, sample_pdf, modified_pdf):
        result = pdf_text_diff(sample_pdf, modified_pdf)
        valid_types = {-1, 0, 1}
        for change_type, _text in result["diff"]:
            assert change_type in valid_types, (
                f"Invalid change type: {change_type}"
            )

    def test_diff_texts_are_strings(self, sample_pdf, modified_pdf):
        result = pdf_text_diff(sample_pdf, modified_pdf)
        for _change_type, text in result["diff"]:
            assert isinstance(text, str)


class TestDiffBehavior:
    """Verify diff logic produces correct results."""

    def test_identical_pdfs_no_changes(self, sample_pdf, identical_pdf):
        result = pdf_text_diff(sample_pdf, identical_pdf)
        assert result["change_count"] == 0
        # All entries should be unchanged (type 0)
        for change_type, _text in result["diff"]:
            assert change_type == 0

    def test_different_pdfs_has_changes(self, sample_pdf, modified_pdf):
        result = pdf_text_diff(sample_pdf, modified_pdf)
        assert result["change_count"] > 0
        # Should have at least one non-zero change type
        change_types = {ct for ct, _ in result["diff"]}
        assert change_types != {0}

    def test_empty_pdfs_no_changes(self, empty_pdf):
        result = pdf_text_diff(empty_pdf, empty_pdf)
        assert result["change_count"] == 0

    def test_diff_contains_expected_words(self, sample_pdf, modified_pdf):
        """The known modifications should appear in the diff."""
        result = pdf_text_diff(sample_pdf, modified_pdf)
        removed = " ".join(
            text for ct, text in result["diff"] if ct == -1
        )
        added = " ".join(
            text for ct, text in result["diff"] if ct == 1
        )
        # sample has "brown", modified has "red"
        assert "brown" in removed
        assert "red" in added

    def test_multi_page_pdf(self, multi_page_pdf, sample_pdf):
        """Multi-page PDFs should diff without errors."""
        result = pdf_text_diff(multi_page_pdf, sample_pdf)
        assert "diff" in result
        assert "change_count" in result
        assert result["change_count"] > 0


class TestErrorHandling:
    """Verify proper error handling for invalid inputs."""

    def test_invalid_input_raises(self):
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(b"not a pdf", b"also not a pdf")

    def test_invalid_first_input_raises(self, sample_pdf):
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(b"not a pdf", sample_pdf)

    def test_invalid_second_input_raises(self, sample_pdf):
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(sample_pdf, b"not a pdf")

    def test_empty_bytes_raises(self):
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(b"", b"")


class TestDuplicateDetection:
    """Verify the byte-hash and text-hash fast paths."""

    def test_byte_identical_short_circuits(self, sample_pdf):
        """Exact same bytes → identical=True, no diff computed."""
        result = pdf_text_diff(sample_pdf, sample_pdf)
        assert result["identical"] is True
        assert result["change_count"] == 0
        assert result["method"] == "byte_hash"

    def test_text_identical_short_circuits(self, sample_pdf, text_identical_pdf):
        """Different bytes, same text → identical=True via text hash."""
        # Sanity: the raw bytes really are different
        assert sample_pdf != text_identical_pdf
        result = pdf_text_diff(sample_pdf, text_identical_pdf)
        assert result["identical"] is True
        assert result["change_count"] == 0
        assert result["method"] == "text_hash"

    def test_different_pdfs_not_identical(self, sample_pdf, modified_pdf):
        """Genuinely different PDFs → identical=False."""
        result = pdf_text_diff(sample_pdf, modified_pdf)
        assert result["identical"] is False
        assert result["change_count"] > 0
        assert result["method"] == "full_diff"

    def test_empty_pdfs_identical(self, empty_pdf):
        """Two empty PDFs → identical=True, no diff entries."""
        result = pdf_text_diff(empty_pdf, empty_pdf)
        assert result["identical"] is True
        assert result["change_count"] == 0
        assert result["diff"] == []
        assert result["method"] == "byte_hash"

