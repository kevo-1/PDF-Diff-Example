"""
Custom exceptions for web-monitoring-pdf-diff.

Mirrors the exception structure used in web-monitoring-diff.
"""


class UndiffableContentError(Exception):
    """
    Raised when the content provided cannot be diffed.

    For example, if the input is not a valid PDF document or if the PDF
    is encrypted and cannot be read.
    """
    pass


class PdfFetchError(Exception):
    """Base class for all failures that occur when fetching a PDF via HTTP."""
    pass


class PdfHttpError(PdfFetchError):
    """Remote server returned a non-2xx HTTP status code."""

    def __init__(self, url: str, status_code: int, reason: str = ""):
        self.url = url
        self.status_code = status_code
        self.reason = reason
        super().__init__(
            f"HTTP {status_code}"
            + (f" {reason}" if reason else "")
            + f" — could not download PDF from: {url}"
        )


class PdfConnectionError(PdfFetchError):
    """Network-level failure (DNS lookup, refused connection, timeout, …)."""

    def __init__(self, url: str, detail: str):
        self.url = url
        super().__init__(f"Connection failed for {url!r}: {detail}")


class PdfIncompleteDownloadError(PdfFetchError):
    """Server closed the connection before the full response was received."""

    def __init__(self, url: str, received: int, expected: int | None):
        self.url = url
        exp_str = str(expected) if expected is not None else "unknown"
        super().__init__(
            f"Incomplete download from {url!r}: "
            f"received {received} bytes, Content-Length was {exp_str}"
        )


class PdfNotAPdfError(PdfFetchError):
    """The downloaded bytes do not start with the PDF magic number ``%PDF-``."""

    def __init__(self, url: str, content_type: str = ""):
        self.url = url
        ct_hint = f" (Content-Type: {content_type})" if content_type else ""
        super().__init__(
            f"Downloaded file is not a valid PDF{ct_hint}: {url}"
        )