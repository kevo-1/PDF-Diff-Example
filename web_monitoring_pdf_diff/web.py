"""
FastAPI web service for web-monitoring-pdf-diff.

Exposes ``pdf_text_diff`` as a POST endpoint that accepts two PDF file
uploads and returns the diff in the standard web-monitoring-diff JSON
format.

Run locally with::

    uvicorn web_monitoring_pdf_diff.web:app --reload
"""

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from .exceptions import UndiffableContentError
from .pdf_diff import pdf_text_diff

app = FastAPI(
    title="web-monitoring-pdf-diff",
    description="Diff two PDF documents and return changes in web-monitoring-diff format.",
    version="0.1.0",
)


@app.post("/pdf_text_diff")
async def diff_pdfs(
    old_pdf: UploadFile = File(..., description="The 'old' / 'from' PDF document"),
    new_pdf: UploadFile = File(..., description="The 'new' / 'to' PDF document"),
):
    """
    Compare two uploaded PDF documents and return a word-level text diff.

    Returns a JSON object with ``diff`` (list of ``[change_type, text]``
    pairs) and ``change_count`` (integer).
    """
    try:
        old_bytes = await old_pdf.read()
        new_bytes = await new_pdf.read()
        result = pdf_text_diff(old_bytes, new_bytes)
        return result
    except UndiffableContentError as exc:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal error: {exc}"},
        )
