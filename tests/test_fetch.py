"""
Unit tests for web_monitoring_pdf_diff.fetch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All HTTP interactions are intercepted with ``httpx``'s built-in
``MockTransport`` / ``MockResponse`` mechanism so the tests are fully
offline and deterministic.
"""

from __future__ import annotations

import pytest
import httpx

import fitz  # PyMuPDF — used to generate a minimal real PDF in memory

from web_monitoring_pdf_diff.fetch import fetch_pdf
from web_monitoring_pdf_diff.exceptions import (
    PdfConnectionError,
    PdfFetchError,
    PdfHttpError,
    PdfIncompleteDownloadError,
    PdfNotAPdfError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(text: str = "Hello PDF") -> bytes:
    """Return a minimal valid single-page PDF as bytes."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def _mock_transport(
    status_code: int = 200,
    body: bytes = b"",
    headers: dict | None = None,
    raise_on_connect: Exception | None = None,
) -> httpx.MockTransport:
    """
    Build an ``httpx.MockTransport`` that always returns the given response.

    ``raise_on_connect`` — if provided, *raise* that exception instead of
    returning a response (simulates network errors).
    """
    _headers = {"content-type": "application/pdf"}
    if headers:
        _headers.update(headers)

    def handler(request: httpx.Request) -> httpx.Response:
        if raise_on_connect is not None:
            raise raise_on_connect
        return httpx.Response(
            status_code=status_code,
            headers=_headers,
            content=body,
        )

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Patch helper: replace httpx.Client with one using a mock transport
# ---------------------------------------------------------------------------

class _PatchedClient:
    """Context manager that monkeypatches ``httpx.Client``."""

    def __init__(self, transport: httpx.MockTransport):
        self._transport = transport
        self._original = None

    def __enter__(self):
        import web_monitoring_pdf_diff.fetch as fetch_mod
        self._fetch_mod = fetch_mod
        self._original = fetch_mod.httpx.Client

        transport = self._transport

        class _MockClient(httpx.Client):
            def __init__(self, **kwargs):
                kwargs["transport"] = transport
                super().__init__(**kwargs)

        fetch_mod.httpx.Client = _MockClient
        return self

    def __exit__(self, *_):
        self._fetch_mod.httpx.Client = self._original


# ---------------------------------------------------------------------------
# Tests: success path
# ---------------------------------------------------------------------------

class TestFetchPdfSuccess:

    def test_valid_pdf_returned(self):
        pdf_bytes = _make_pdf("Test document")
        transport = _mock_transport(body=pdf_bytes)
        with _PatchedClient(transport):
            result = fetch_pdf("https://example.com/doc.pdf")
        assert result == pdf_bytes

    def test_url_fragment_stripped(self):
        """#page=2 fragments must be silently stripped before the request."""
        pdf_bytes = _make_pdf()
        transport = _mock_transport(body=pdf_bytes)
        with _PatchedClient(transport):
            # Should not raise even though the URL has a fragment.
            result = fetch_pdf("https://example.com/doc.pdf#page=2.00")
        assert result.startswith(b"%PDF-")

    def test_wayback_machine_style_url(self):
        """The real Wayback URL pattern (with embedded URL + fragment) works."""
        pdf_bytes = _make_pdf("Wayback content")
        transport = _mock_transport(body=pdf_bytes)
        with _PatchedClient(transport):
            result = fetch_pdf(
                "https://web.archive.org/web/20220520042238id_/"
                "http://spbi.cz/res/file/sizawuwigip.pdf#page=2.00"
            )
        assert result.startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# Tests: HTTP errors
# ---------------------------------------------------------------------------

class TestFetchPdfHttpErrors:

    @pytest.mark.parametrize("status_code, expected_in_msg", [
        (404, "404"),
        (403, "403"),
        (401, "401"),
        (500, "500"),
        (503, "503"),
    ])
    def test_http_error_codes_raise_pdf_http_error(self, status_code, expected_in_msg):
        transport = _mock_transport(status_code=status_code, body=b"error page")
        with _PatchedClient(transport):
            with pytest.raises(PdfHttpError) as exc_info:
                fetch_pdf("https://example.com/doc.pdf")
        assert expected_in_msg in str(exc_info.value)
        assert exc_info.value.status_code == status_code

    def test_404_error_carries_url(self):
        url = "https://example.com/missing.pdf"
        transport = _mock_transport(status_code=404)
        with _PatchedClient(transport):
            with pytest.raises(PdfHttpError) as exc_info:
                fetch_pdf(url)
        assert url in str(exc_info.value)
        assert exc_info.value.url == url

    def test_403_message_mentions_access_denied(self):
        transport = _mock_transport(status_code=403)
        with _PatchedClient(transport):
            with pytest.raises(PdfHttpError) as exc_info:
                fetch_pdf("https://example.com/private.pdf")
        assert "access denied" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Tests: connection / network errors
# ---------------------------------------------------------------------------

class TestFetchPdfConnectionErrors:

    def test_connect_error_raises_pdf_connection_error(self):
        transport = _mock_transport(
            raise_on_connect=httpx.ConnectError("Name or service not known")
        )
        with _PatchedClient(transport):
            with pytest.raises(PdfConnectionError):
                fetch_pdf("https://nonexistent.invalid/doc.pdf")

    def test_timeout_raises_pdf_connection_error(self):
        transport = _mock_transport(
            raise_on_connect=httpx.ReadTimeout("timed out")
        )
        with _PatchedClient(transport):
            with pytest.raises(PdfConnectionError) as exc_info:
                fetch_pdf("https://slow.example.com/doc.pdf")
        assert "timed out" in str(exc_info.value).lower()

    def test_remote_protocol_error_raises_pdf_connection_error(self):
        transport = _mock_transport(
            raise_on_connect=httpx.RemoteProtocolError("connection closed")
        )
        with _PatchedClient(transport):
            with pytest.raises(PdfConnectionError):
                fetch_pdf("https://example.com/doc.pdf")


# ---------------------------------------------------------------------------
# Tests: incomplete download
# ---------------------------------------------------------------------------

class TestFetchPdfIncompleteDownload:

    def test_incomplete_download_raises(self):
        pdf_bytes = _make_pdf()
        # Advertise more bytes than we actually return.
        transport = _mock_transport(
            body=pdf_bytes,
            headers={
                "content-type": "application/pdf",
                "content-length": str(len(pdf_bytes) + 5_000),
            },
        )
        with _PatchedClient(transport):
            with pytest.raises(PdfIncompleteDownloadError) as exc_info:
                fetch_pdf("https://example.com/doc.pdf")
        msg = str(exc_info.value)
        assert str(len(pdf_bytes)) in msg   # received bytes in message

    def test_correct_content_length_does_not_raise(self):
        pdf_bytes = _make_pdf()
        transport = _mock_transport(
            body=pdf_bytes,
            headers={
                "content-type": "application/pdf",
                "content-length": str(len(pdf_bytes)),
            },
        )
        with _PatchedClient(transport):
            result = fetch_pdf("https://example.com/doc.pdf")
        assert result == pdf_bytes

    def test_missing_content_length_does_not_raise(self):
        """No Content-Length header → no incomplete-download check."""
        pdf_bytes = _make_pdf()
        transport = _mock_transport(body=pdf_bytes)  # no content-length header
        with _PatchedClient(transport):
            result = fetch_pdf("https://example.com/doc.pdf")
        assert result == pdf_bytes


# ---------------------------------------------------------------------------
# Tests: not a PDF
# ---------------------------------------------------------------------------

class TestFetchPdfNotAPdf:

    def test_html_body_raises_pdf_not_a_pdf_error(self):
        html = b"<html><body>Not a PDF</body></html>"
        transport = _mock_transport(
            body=html,
            headers={"content-type": "text/html"},
        )
        with _PatchedClient(transport):
            with pytest.raises(PdfNotAPdfError) as exc_info:
                fetch_pdf("https://example.com/oops.pdf")
        assert "not a valid pdf" in str(exc_info.value).lower()

    def test_empty_body_raises_pdf_not_a_pdf_error(self):
        transport = _mock_transport(body=b"")
        with _PatchedClient(transport):
            with pytest.raises(PdfNotAPdfError):
                fetch_pdf("https://example.com/empty.pdf")

    def test_random_bytes_raises_pdf_not_a_pdf_error(self):
        transport = _mock_transport(body=b"\x00\x01\x02\x03" * 100)
        with _PatchedClient(transport):
            with pytest.raises(PdfNotAPdfError):
                fetch_pdf("https://example.com/garbage.pdf")

    def test_content_type_included_in_error(self):
        transport = _mock_transport(
            body=b"<html>not a pdf</html>",
            headers={"content-type": "text/html; charset=utf-8"},
        )
        with _PatchedClient(transport):
            with pytest.raises(PdfNotAPdfError) as exc_info:
                fetch_pdf("https://example.com/doc.pdf")
        assert "text/html" in str(exc_info.value)