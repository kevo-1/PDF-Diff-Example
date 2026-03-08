"""
Core PDF diffing functions for web-monitoring-pdf-diff.

All public functions follow the web-monitoring-diff convention:
  - First two params are ``a_body`` and ``b_body`` (raw PDF bytes).
  - Return value is a dict with at least ``"diff"`` and ``"change_count"`` keys.
  - ``"diff"`` is a list of ``[change_type, text]`` pairs where
    change_type is -1 (removed), 0 (unchanged), or 1 (added).
"""

import difflib

import fitz  # PyMuPDF

from .exceptions import UndiffableContentError


def _extract_words(pdf_bytes: bytes) -> list[list[str]]:
    """
    Extract words from each page of a PDF.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw PDF file content.

    Returns
    -------
    list[list[str]]
        A list of pages, where each page is a list of word strings.

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

    pages: list[list[str]] = []
    for page in doc:
        # get_text("words") returns list of (x0, y0, x1, y1, word, block, line, word_n)
        raw_words = page.get_text("words")
        pages.append([w[4] for w in raw_words])
    doc.close()
    return pages


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
    a_pages = _extract_words(a_body)
    b_pages = _extract_words(b_body)

    a_words = _flatten_pages(a_pages)
    b_words = _flatten_pages(b_pages)

    matcher = difflib.SequenceMatcher(None, a_words, b_words)
    opcodes = matcher.get_opcodes()

    diff, change_count = _coalesce_opcodes(opcodes, a_words, b_words)

    return {
        "diff": diff,
        "change_count": change_count,
    }
