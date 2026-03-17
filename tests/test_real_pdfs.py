import os
import pytest
from web_monitoring_pdf_diff import pdf_text_diff

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

def get_fixture_pdfs():
    """Return a list of paths to downloaded real PDFs in the fixtures dir."""
    if not os.path.isdir(FIXTURES_DIR):
        return []
    pdfs = []
    for f in os.listdir(FIXTURES_DIR):
        if f.endswith('.pdf'):
            pdfs.append(os.path.join(FIXTURES_DIR, f))
    return pdfs

class TestRealPdfs:
    """Offline unit tests using downloaded real-world PDFs."""
    
    @pytest.mark.parametrize("pdf_path", get_fixture_pdfs())
    def test_real_pdf_identical(self, pdf_path):
        """Test a real PDF against itself to ensure identical detection works on real files."""
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            
        result = pdf_text_diff(pdf_bytes, pdf_bytes)
        
        assert "diff" in result
        assert "change_count" in result
        assert result["change_count"] == 0
        assert result["identical"] is True
        assert result["method"] == "byte_hash"

    def test_real_pdfs_diff(self):
        """Test diffing two different real PDFs against each other."""
        pdfs = get_fixture_pdfs()
        if len(pdfs) < 2:
            pytest.skip("Not enough fixture PDFs downloaded.")
            
        with open(pdfs[0], 'rb') as f1, open(pdfs[1], 'rb') as f2:
            bytes1 = f1.read()
            bytes2 = f2.read()
            
        result = pdf_text_diff(bytes1, bytes2)
        
        # When comparing two mostly unrelated documents, they should not be identical
        # However, they might both be scanned images with zero text. In that case, 
        # identical=True and change_count=0 (text_hash method). We must handle both.
        if result["identical"]:
            assert result["change_count"] == 0
        else:
            assert result["change_count"] > 0
            assert result["method"] == "full_diff"
            
    def test_real_pdf_vs_empty(self):
        """Test diffing a real PDF against an empty byte string (raises UndiffableContentError)."""
        from web_monitoring_pdf_diff import UndiffableContentError
        pdfs = get_fixture_pdfs()
        if not pdfs:
            pytest.skip("No fixture PDFs.")
            
        with open(pdfs[0], 'rb') as f:
            pdf_bytes = f.read()
            
        with pytest.raises(UndiffableContentError):
            pdf_text_diff(pdf_bytes, b"")
