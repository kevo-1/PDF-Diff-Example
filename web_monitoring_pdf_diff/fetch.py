"""
Utilities for downloading a PDF document from an HTTP/HTTPS URL.

All failure modes raise a :class:`~web_monitoring_pdf_diff.exceptions.PdfFetchError`
sub-class so callers can surface a precise, human-readable error message.
"""

from __future__ import annotations

import urllib.parse

import httpx

from .exceptions import (
    PdfConnectionError,
    PdfFetchError,
    PdfHttpError,
    PdfIncompleteDownloadError,
    PdfNotAPdfError,
)

# A valid PDF file always begins with this byte sequence.
_PDF_MAGIC = b"%PDF-"

# Safety cap: refuse to buffer more than 50 MB per document.
_MAX_PDF_BYTES = 50 * 1024 * 1024

# Human-readable descriptions for common HTTP error codes.
_HTTP_REASONS: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized / access denied",
    403: "Forbidden / access denied",
    404: "Not Found",
    408: "Request Timeout",
    410: "Gone",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}


def fetch_pdf(url: str) -> bytes:
    """
    Download *url* and return its raw bytes.

    The URL fragment (e.g. ``#page=2.00``) is stripped before the request
    is sent — it is a client-side hint and must not be forwarded to the
    server.

    Parameters:
        url:
            A fully qualified ``http://`` or ``https://`` URL.

    Returns:
        bytes
            The raw PDF bytes.

    Raises:
        PdfHttpError
            The remote server returned a non-2xx HTTP status code.
        PdfConnectionError
            A network-level error occurred (DNS failure, refused connection,
            timeout, TLS error, …).
        PdfIncompleteDownloadError
            The server advertised a ``Content-Length`` but closed the connection
            before all bytes were delivered.
        PdfNotAPdfError
            The downloaded bytes do not start with ``%PDF-`` — the URL likely
            points to an HTML error page or other non-PDF resource.
        PdfFetchError
            The downloaded file exceeds the 50 MB safety cap.
    """
    # Strip any fragment — not sent to the server and confuses some proxies.
    clean_url = urllib.parse.urldefrag(url).url

    try:
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            with client.stream("GET", clean_url) as response:
                _check_status(url, response)
                data, received = _read_body(url, response)
                _check_content_length(url, response, received)

    except httpx.ConnectError as exc:
        raise PdfConnectionError(url, f"Could not connect — {exc}") from exc
    except httpx.TimeoutException as exc:
        raise PdfConnectionError(url, f"Request timed out — {exc}") from exc
    except httpx.RemoteProtocolError as exc:
        raise PdfConnectionError(url, f"Protocol error — {exc}") from exc
    except httpx.TooManyRedirects as exc:
        raise PdfConnectionError(url, f"Too many redirects — {exc}") from exc
    except httpx.HTTPError as exc:
        # Catch-all for any remaining httpx transport-level errors.
        raise PdfConnectionError(url, str(exc)) from exc
    except PdfFetchError:
        # Already the right type — let it propagate unchanged.
        raise

    _check_pdf_magic(url, data, response.headers.get("content-type", ""))
    return data


def _check_status(url: str, response: httpx.Response) -> None:
    """Raise :class:`PdfHttpError` for any non-2xx response."""
    code = response.status_code
    if code < 400:
        return
    reason = _HTTP_REASONS.get(code) or response.reason_phrase or ""
    raise PdfHttpError(url, code, reason)


def _read_body(url: str, response: httpx.Response) -> tuple[bytes, int]:
    """Stream the response body, enforcing the size cap."""
    chunks: list[bytes] = []
    received = 0
    for chunk in response.iter_bytes(chunk_size=65_536):
        received += len(chunk)
        if received > _MAX_PDF_BYTES:
            raise PdfFetchError(
                f"PDF at {url!r} exceeds the "
                f"{_MAX_PDF_BYTES // (1024 * 1024)} MB download limit"
            )
        chunks.append(chunk)
    return b"".join(chunks), received


def _check_content_length(
    url: str, response: httpx.Response, received: int
) -> None:
    """Raise :class:`PdfIncompleteDownloadError` if fewer bytes arrived than advertised."""
    raw = response.headers.get("content-length")
    if raw is None:
        return
    try:
        expected = int(raw)
    except ValueError:
        return
    if received < expected:
        raise PdfIncompleteDownloadError(url, received, expected)


def _check_pdf_magic(url: str, data: bytes, content_type: str) -> None:
    """Raise :class:`PdfNotAPdfError` if *data* does not start with ``%PDF-``."""
    if not data.startswith(_PDF_MAGIC):
        raise PdfNotAPdfError(url, content_type)