"""
Core PDF diffing functions for web-monitoring-pdf-diff.

All public functions follow the web-monitoring-diff convention:
  - First two params are ``a_body`` and ``b_body`` (raw PDF bytes).
  - Return value is a dict with at least ``"diff"`` and ``"change_count"`` keys.
  - ``"diff"`` is a list of ``[change_type, text]`` pairs where
    change_type is -1 (removed), 0 (unchanged), or 1 (added).
"""

import difflib
import hashlib
import os

import fitz  # PyMuPDF

from .exceptions import UndiffableContentError

# Maximum number of pages to process per PDF.  Set via the
# ``MAX_DIFF_PAGES`` environment variable; defaults to 100.
MAX_DIFF_PAGES: int = int(os.environ.get("MAX_DIFF_PAGES", "100"))


def _extract_words(
    pdf_bytes: bytes,
    max_pages: int | None = None,
) -> tuple[list[list[str]], int, bool]:
    """
    Extract words from each page of a PDF.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw PDF file content.
    max_pages : int | None
        If set, only the first *max_pages* pages are processed.

    Returns
    -------
    tuple[list[list[str]], int, bool]
        ``(pages, total_pages, truncated)`` where *pages* is a list of
        pages (each a list of word strings), *total_pages* is the
        document's full page count, and *truncated* is ``True`` when
        pages were skipped.

    Raises
    ------
    UndiffableContentError
        If the bytes cannot be opened as a PDF.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise UndiffableContentError(
            f"Could not open content as PDF: {exc}"
        ) from exc

    total_pages = len(doc)
    limit = max_pages if max_pages is not None else total_pages
    truncated = total_pages > limit

    pages: list[list[str]] = []
    for idx, page in enumerate(doc):
        if idx >= limit:
            break
        # get_text("words") returns list of (x0, y0, x1, y1, word, block, line, word_n)
        raw_words = page.get_text("words")
        pages.append([w[4] for w in raw_words])
    doc.close()
    return pages, total_pages, truncated


def _flatten_pages(pages: list[list[str]]) -> list[str]:
    """
    Flatten a list-of-pages-of-words into a single word list.

    Inserts a newline token between pages to preserve page boundaries
    in the diff output.
    """
    flat: list[str] = []
    for i, page_words in enumerate(pages):
        if i > 0:
            flat.append("\n")
        flat.extend(page_words)
    return flat


def _content_hash(pages: list[list[str]]) -> str:
    """
    Return a SHA-256 hex digest of the normalised text content.

    All words across all pages are joined with a single space
    (page boundaries marked with ``\n``) so that metadata or
    compression differences are ignored.
    """
    flat = _flatten_pages(pages)
    text = " ".join(flat)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coalesce_opcodes(
    opcodes: list[tuple[str, int, int, int, int]],
    a_words: list[str],
    b_words: list[str],
) -> list[list]:
    """
    Convert SequenceMatcher opcodes into the web-monitoring-diff output format.

    Returns a list of ``[change_type, text]`` pairs, where adjacent operations
    of the same type are merged into a single entry.
    """
    result: list[list] = []
    change_count = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            text = " ".join(a_words[i1:i2])
            _append_chunk(result, 0, text)
        elif tag == "delete":
            text = " ".join(a_words[i1:i2])
            _append_chunk(result, -1, text)
            change_count += 1
        elif tag == "insert":
            text = " ".join(b_words[j1:j2])
            _append_chunk(result, 1, text)
            change_count += 1
        elif tag == "replace":
            old_text = " ".join(a_words[i1:i2])
            new_text = " ".join(b_words[j1:j2])
            _append_chunk(result, -1, old_text)
            _append_chunk(result, 1, new_text)
            change_count += 1

    return result, change_count


def _append_chunk(result: list[list], change_type: int, text: str):
    """Append a chunk to result, merging with previous if same type."""
    if result and result[-1][0] == change_type:
        result[-1][1] += " " + text
    else:
        result.append([change_type, text])


def pdf_text_diff(a_body: bytes, b_body: bytes) -> dict:
    """
    Compute a word-level text diff between two PDF documents.

    This follows the web-monitoring-diff output convention so the result
    can be consumed directly by the Wayback Machine diff UI.

    Only the first :data:`MAX_DIFF_PAGES` pages of each document are
    processed.  When truncation occurs the response includes
    ``"truncated": true`` and ``"pages_processed"``.

    Parameters
    ----------
    a_body : bytes
        Raw bytes of the "from" / "old" PDF document.
    b_body : bytes
        Raw bytes of the "to" / "new" PDF document.

    Returns
    -------
    dict
        A dictionary with:
        - ``"diff"``: list of ``[change_type, text]`` pairs where
          change_type is -1 (removed), 0 (unchanged), or 1 (added).
        - ``"change_count"``: integer count of changes.
        - ``"truncated"``: bool indicating whether pages were skipped.
        - ``"pages_processed"``: number of pages actually compared.

    Raises
    ------
    UndiffableContentError
        If either input cannot be read as a PDF.

    Examples
    --------
    >>> result = pdf_text_diff(old_pdf_bytes, new_pdf_bytes)
    >>> result["diff"]
    [[-1, "old words"], [0, "shared words"], [1, "new words"]]
    >>> result["change_count"]
    2
    """
    # -------------------------------------------------------------------
    # Fast path 1: byte-identical PDFs (exact same file)
    # -------------------------------------------------------------------
    byte_identical = (
        hashlib.sha256(a_body).hexdigest()
        == hashlib.sha256(b_body).hexdigest()
    )
    if byte_identical:
        a_pages, a_total, a_trunc = _extract_words(a_body, MAX_DIFF_PAGES)
        a_words = _flatten_pages(a_pages)
        return {
            "diff": [[0, " ".join(a_words)]] if a_words else [],
            "change_count": 0,
            "identical": True,
            "method": "byte_hash",
            "truncated": a_trunc,
            "pages_processed": len(a_pages),
        }

    # -------------------------------------------------------------------
    # Extract text (needed for both fast-path-2 and the full diff)
    # -------------------------------------------------------------------
    a_pages, a_total, a_trunc = _extract_words(a_body, MAX_DIFF_PAGES)
    b_pages, b_total, b_trunc = _extract_words(b_body, MAX_DIFF_PAGES)

    a_words = _flatten_pages(a_pages)
    b_words = _flatten_pages(b_pages)

    # -------------------------------------------------------------------
    # Fast path 2: different bytes but identical text content
    # -------------------------------------------------------------------
    if _content_hash(a_pages) == _content_hash(b_pages):
        truncated = a_trunc or b_trunc
        return {
            "diff": [[0, " ".join(a_words)]] if a_words else [],
            "change_count": 0,
            "identical": True,
            "method": "text_hash",
            "truncated": truncated,
            "pages_processed": min(len(a_pages), len(b_pages)),
        }

    # -------------------------------------------------------------------
    # Full diff
    # -------------------------------------------------------------------
    matcher = difflib.SequenceMatcher(None, a_words, b_words)
    opcodes = matcher.get_opcodes()

    diff, change_count = _coalesce_opcodes(opcodes, a_words, b_words)

    truncated = a_trunc or b_trunc
    pages_processed = min(len(a_pages), len(b_pages))

    return {
        "diff": diff,
        "change_count": change_count,
        "identical": False,
        "method": "full_diff",
        "truncated": truncated,
        "pages_processed": pages_processed,
    }
