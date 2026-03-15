"""
FastAPI web service for web-monitoring-pdf-diff.

Exposes ``pdf_text_diff`` via two POST endpoints:

- ``/pdf_text_diff/files`` — accepts two multipart file uploads.
- ``/pdf_text_diff/urls``  — accepts two HTTP/HTTPS URLs as form fields.

Run locally with::

    uvicorn web_monitoring_pdf_diff.web:app --reload

Example requests::

    # Two file uploads
    curl -X POST http://localhost:8000/pdf_text_diff/files \
         -F "old_pdf=@old.pdf" -F "new_pdf=@new.pdf"

    # Two URLs
    curl -X POST http://localhost:8000/pdf_text_diff/urls \
         -F "old_url=https://example.com/a.pdf" \
         -F "new_url=https://example.com/b.pdf"
"""

from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from .exceptions import (
    PdfConnectionError,
    PdfFetchError,
    PdfHttpError,
    PdfIncompleteDownloadError,
    PdfNotAPdfError,
    UndiffableContentError,
)
from .fetch import fetch_pdf, _MAX_PDF_BYTES
from .pdf_diff import pdf_text_diff

app = FastAPI(
    title="web-monitoring-pdf-diff",
    description=(
        "Diff two PDF documents and return changes in web-monitoring-diff format. "
        "Supply documents as file uploads (/pdf_text_diff/files) "
        "or as HTTP/HTTPS URLs (/pdf_text_diff/urls)."
    ),
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Shared error-handling helper
# ---------------------------------------------------------------------------

def _run_diff(old_bytes: bytes, new_bytes: bytes):
    """Execute the diff and return the result or an error response."""
    try:
        return pdf_text_diff(old_bytes, new_bytes)
    except UndiffableContentError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal error: {exc}"},
        )


# ---------------------------------------------------------------------------
# Endpoint: file uploads
# ---------------------------------------------------------------------------

@app.post("/pdf_text_diff/files")
async def diff_pdfs_files(
    old_pdf: UploadFile = File(..., description="'Old' PDF as a file upload"),
    new_pdf: UploadFile = File(..., description="'New' PDF as a file upload"),
):
    """
    Compare two PDF documents supplied as **multipart file uploads**.

    Returns ``{"diff": [[change_type, text], …], "change_count": N}``.

    ### Error responses

    | Status | Meaning |
    |--------|---------|
    | 422 | Content cannot be diffed (corrupt or non-PDF file) |
    | 500 | Unexpected internal error |
    """
    try:
        old_bytes = await old_pdf.read()
        new_bytes = await new_pdf.read()
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Failed to read uploaded files: {exc}"},
        )

    for label, data in [("old_pdf", old_bytes), ("new_pdf", new_bytes)]:
        if len(data) > _MAX_PDF_BYTES:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": (
                        f"'{label}' exceeds the "
                        f"{_MAX_PDF_BYTES // (1024 * 1024)} MB upload limit "
                        f"({len(data)} bytes received)"
                    )
                },
        )

    return _run_diff(old_bytes, new_bytes)


# ---------------------------------------------------------------------------
# Endpoint: URLs
# ---------------------------------------------------------------------------

@app.post("/pdf_text_diff/urls")
async def diff_pdfs_urls(
    old_url: str = Form(..., description="HTTP/HTTPS URL of the 'old' PDF"),
    new_url: str = Form(..., description="HTTP/HTTPS URL of the 'new' PDF"),
):
    """
    Compare two PDF documents fetched from **HTTP/HTTPS URLs**.

    Returns ``{"diff": [[change_type, text], …], "change_count": N}``.

    ### Error responses

    | Status | Meaning |
    |--------|---------|
    | 422 | Content cannot be diffed, or the downloaded file is not a PDF |
    | 502 | Remote server returned an HTTP error (404, 403, …) |
    | 504 | Connection / timeout failure reaching the remote URL |
    | 500 | Unexpected internal error |
    """
    try:
        old_bytes = fetch_pdf(old_url)
        new_bytes = fetch_pdf(new_url)

    except PdfHttpError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(exc),
                "remote_status": exc.status_code,
                "url": exc.url,
            },
        )

    except (PdfConnectionError, PdfIncompleteDownloadError) as exc:
        return JSONResponse(status_code=504, content={"detail": str(exc)})

    except (PdfNotAPdfError, PdfFetchError) as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return _run_diff(old_bytes, new_bytes)