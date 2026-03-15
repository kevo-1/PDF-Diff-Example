"""
web-monitoring-pdf-diff
~~~~~~~~~~~~~~~~~~~~~~~

A standalone package for diffing PDF documents, producing output
compatible with web-monitoring-diff's JSON format.

Usage::

    from web_monitoring_pdf_diff import pdf_text_diff

    result = pdf_text_diff(old_pdf_bytes, new_pdf_bytes)
    # result == {"diff": [[-1, "removed"], [0, "same"], [1, "added"]], "change_count": 2}
"""

__version__ = "0.1.0"

from .pdf_diff import pdf_text_diff  # noqa: F401
from .exceptions import (  # noqa: F401
    UndiffableContentError,
    PdfFetchError,
    PdfHttpError,
    PdfConnectionError,
    PdfIncompleteDownloadError,
    PdfNotAPdfError,
)
from .fetch import fetch_pdf  # noqa: F401