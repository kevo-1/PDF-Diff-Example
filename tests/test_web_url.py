"""
Integration tests for the /pdf_text_diff/urls and /pdf_text_diff/files endpoints.

Uses FastAPI's ``TestClient`` (backed by ``httpx``) for HTTP-level testing
and patches ``web_monitoring_pdf_diff.fetch.fetch_pdf`` to avoid real
network calls.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import fitz
import pytest
from fastapi.testclient import TestClient

from web_monitoring_pdf_diff.web import app
from web_monitoring_pdf_diff.exceptions import (
    PdfConnectionError,
    PdfHttpError,
    PdfIncompleteDownloadError,
    PdfNotAPdfError,
    PdfFetchError,
)

client = TestClient(app, raise_server_exceptions=False)

OLD_URL = "https://example.com/old.pdf"
NEW_URL = "https://example.com/new.pdf"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(text: str = "Sample") -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def _patch_fetch(side_effects: list):
    """
    Patch ``fetch_pdf`` with sequential ``side_effects``.

    Each element may be ``bytes`` (return value) or an ``Exception``
    instance (will be raised).
    """
    values = list(side_effects)

    def _fake_fetch(url: str) -> bytes:
        val = values.pop(0)
        if isinstance(val, Exception):
            raise val
        return val

    return patch("web_monitoring_pdf_diff.web.fetch_pdf", side_effect=_fake_fetch)


# ===========================================================================
# /pdf_text_diff/urls — URL-based endpoint
# ===========================================================================


class TestUrlInputSuccess:

    def test_two_urls_returns_diff(self):
        old = _make_pdf("The quick brown fox")
        new = _make_pdf("The quick red fox")
        with _patch_fetch([old, new]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "diff" in body
        assert "change_count" in body
        assert body["change_count"] > 0

    def test_identical_urls_zero_changes(self):
        pdf = _make_pdf("Same content")
        with _patch_fetch([pdf, pdf]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert resp.status_code == 200
        assert resp.json()["change_count"] == 0

    def test_url_fragment_accepted(self):
        """Fragment in URL must not cause a 400/422."""
        old = _make_pdf("Page content")
        new = _make_pdf("Page content modified")
        wayback = (
            "https://web.archive.org/web/20220520042238id_/"
            "http://spbi.cz/res/file/sizawuwigip.pdf#page=2.00"
        )
        with _patch_fetch([old, new]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": wayback, "new_url": NEW_URL},
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /pdf_text_diff/urls — missing parameters
# ---------------------------------------------------------------------------

class TestUrlMissingParameters:

    def test_no_params_returns_422(self):
        resp = client.post("/pdf_text_diff/urls")
        assert resp.status_code == 422

    def test_only_old_url_returns_422(self):
        resp = client.post("/pdf_text_diff/urls", data={"old_url": OLD_URL})
        assert resp.status_code == 422

    def test_only_new_url_returns_422(self):
        resp = client.post("/pdf_text_diff/urls", data={"new_url": NEW_URL})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /pdf_text_diff/urls — 502 remote HTTP errors
# ---------------------------------------------------------------------------

class TestRemoteHttpErrors:

    @pytest.mark.parametrize("status_code", [404, 403, 401, 500])
    def test_remote_http_error_returns_502(self, status_code):
        exc = PdfHttpError(OLD_URL, status_code, "error")
        with _patch_fetch([exc, _make_pdf()]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert resp.status_code == 502
        body = resp.json()
        assert body["remote_status"] == status_code
        assert body["url"] == OLD_URL

    def test_502_body_contains_detail(self):
        exc = PdfHttpError(OLD_URL, 404, "Not Found")
        with _patch_fetch([exc, _make_pdf()]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert "404" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /pdf_text_diff/urls — 504 connection / incomplete download errors
# ---------------------------------------------------------------------------

class TestConnectionErrors:

    def test_connection_error_returns_504(self):
        exc = PdfConnectionError(OLD_URL, "Could not connect")
        with _patch_fetch([exc, _make_pdf()]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert resp.status_code == 504

    def test_incomplete_download_returns_504(self):
        exc = PdfIncompleteDownloadError(OLD_URL, received=1000, expected=5000)
        with _patch_fetch([exc, _make_pdf()]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert resp.status_code == 504

    def test_504_body_contains_detail(self):
        exc = PdfConnectionError(OLD_URL, "Name or service not known")
        with _patch_fetch([exc, _make_pdf()]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# /pdf_text_diff/urls — 422 not a PDF / size limit / undiffable
# ---------------------------------------------------------------------------

class TestNotPdfErrors:

    def test_not_a_pdf_returns_422(self):
        exc = PdfNotAPdfError(OLD_URL, "text/html")
        with _patch_fetch([exc, _make_pdf()]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert resp.status_code == 422
        assert "not a valid pdf" in resp.json()["detail"].lower()

    def test_size_limit_exceeded_returns_422(self):
        exc = PdfFetchError(f"PDF at {OLD_URL!r} exceeds the 50 MB download limit")
        with _patch_fetch([exc, _make_pdf()]):
            resp = client.post(
                "/pdf_text_diff/urls",
                data={"old_url": OLD_URL, "new_url": NEW_URL},
            )
        assert resp.status_code == 422


# ===========================================================================
# /pdf_text_diff/files — file-upload-based endpoint
# ===========================================================================


class TestFileUploadSuccess:

    def test_two_files_returns_diff(self):
        old = _make_pdf("The quick brown fox")
        new = _make_pdf("The quick red fox")
        resp = client.post(
            "/pdf_text_diff/files",
            files={
                "old_pdf": ("old.pdf", old, "application/pdf"),
                "new_pdf": ("new.pdf", new, "application/pdf"),
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "diff" in body
        assert "change_count" in body
        assert body["change_count"] > 0

    def test_identical_files_zero_changes(self):
        pdf = _make_pdf("Same content")
        resp = client.post(
            "/pdf_text_diff/files",
            files={
                "old_pdf": ("old.pdf", pdf, "application/pdf"),
                "new_pdf": ("new.pdf", pdf, "application/pdf"),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["change_count"] == 0


class TestFileUploadMissingParameters:

    def test_no_files_returns_422(self):
        resp = client.post("/pdf_text_diff/files")
        assert resp.status_code == 422

    def test_only_old_file_returns_422(self):
        pdf = _make_pdf()
        resp = client.post(
            "/pdf_text_diff/files",
            files={"old_pdf": ("old.pdf", pdf, "application/pdf")},
        )
        assert resp.status_code == 422

    def test_only_new_file_returns_422(self):
        pdf = _make_pdf()
        resp = client.post(
            "/pdf_text_diff/files",
            files={"new_pdf": ("new.pdf", pdf, "application/pdf")},
        )
        assert resp.status_code == 422