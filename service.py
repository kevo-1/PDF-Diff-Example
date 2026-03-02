"""
PDF comparison service — text diff with word-level highlights.

Uses PyMuPDF (fitz) for rendering/text extraction and Pillow for highlight drawing.
"""

import base64
import io
import difflib
from dataclasses import dataclass, asdict

import fitz  # PyMuPDF
from PIL import Image, ImageDraw


DPI = 150
SCALE = DPI / 72  # PDF points → pixels


@dataclass
class Change:
    """One detected change (for the sidebar/changes panel)."""
    id: int
    page: int
    kind: str          # "del", "add", "mod"
    old_text: str
    new_text: str
    y_pct: float       # vertical position as 0-1 fraction (for scroll-to)


def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def _render_page(page: fitz.Page) -> Image.Image:
    mat = fitz.Matrix(SCALE, SCALE)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


@dataclass
class WordInfo:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int


def _extract_words(pdf_bytes: bytes):
    """Extract words with bounding boxes and render page images."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_words = []
    all_images = []

    for page_idx, page in enumerate(doc):
        all_images.append(_render_page(page))
        words_raw = page.get_text("words")
        page_words = []
        for w in words_raw:
            page_words.append(WordInfo(
                text=w[4],
                x0=w[0] * SCALE, y0=w[1] * SCALE,
                x1=w[2] * SCALE, y1=w[3] * SCALE,
                page=page_idx,
            ))
        all_words.append(page_words)

    doc.close()
    return all_words, all_images


def compute_text_diff(old_pdf: bytes, new_pdf: bytes) -> dict:
    """
    Word-level text diff with highlighted page images + change metadata.
    """
    old_words, old_images = _extract_words(old_pdf)
    new_words, new_images = _extract_words(new_pdf)

    # Pad to equal page counts
    max_pg = max(len(old_images), len(new_images))
    default_size = (int(612 * SCALE), int(792 * SCALE))
    while len(old_words) < max_pg:
        old_words.append([])
        size = new_images[len(old_images)].size if len(old_images) < len(new_images) else default_size
        old_images.append(Image.new("RGB", size, (255, 255, 255)))
    while len(new_words) < max_pg:
        new_words.append([])
        size = old_images[len(new_images)].size if len(new_images) < len(old_images) else default_size
        new_images.append(Image.new("RGB", size, (255, 255, 255)))

    all_changes = []
    change_id = 0
    pages_out = []

    for pg in range(max_pg):
        ow = old_words[pg]
        nw = new_words[pg]
        old_texts = [w.text for w in ow]
        new_texts = [w.text for w in nw]

        sm = difflib.SequenceMatcher(None, old_texts, new_texts)

        old_highlights = []
        new_highlights = []

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue

            old_chunk = " ".join(old_texts[i1:i2]) if i1 < i2 else ""
            new_chunk = " ".join(new_texts[j1:j2]) if j1 < j2 else ""

            if tag == "delete":
                kind = "del"
                for w in ow[i1:i2]:
                    old_highlights.append(w)
                y_pct = ow[i1].y0 / old_images[pg].height if ow else 0
            elif tag == "insert":
                kind = "add"
                for w in nw[j1:j2]:
                    new_highlights.append(w)
                y_pct = nw[j1].y0 / new_images[pg].height if nw else 0
            else:
                kind = "mod"
                for w in ow[i1:i2]:
                    old_highlights.append(w)
                for w in nw[j1:j2]:
                    new_highlights.append(w)
                y_pct = ow[i1].y0 / old_images[pg].height if ow else 0

            change_id += 1
            all_changes.append(Change(
                id=change_id, page=pg, kind=kind,
                old_text=old_chunk, new_text=new_chunk,
                y_pct=round(y_pct, 4),
            ))

        # Draw highlights
        old_img = old_images[pg].copy().convert("RGBA")
        new_img = new_images[pg].copy().convert("RGBA")

        old_ov = Image.new("RGBA", old_img.size, (0, 0, 0, 0))
        new_ov = Image.new("RGBA", new_img.size, (0, 0, 0, 0))
        old_draw = ImageDraw.Draw(old_ov)
        new_draw = ImageDraw.Draw(new_ov)

        for w in old_highlights:
            old_draw.rectangle(
                [w.x0 - 1, w.y0 - 1, w.x1 + 1, w.y1 + 1],
                fill=(255, 100, 100, 70), outline=(220, 50, 50, 160), width=1,
            )
        for w in new_highlights:
            new_draw.rectangle(
                [w.x0 - 1, w.y0 - 1, w.x1 + 1, w.y1 + 1],
                fill=(100, 200, 100, 70), outline=(50, 180, 50, 160), width=1,
            )

        old_img = Image.alpha_composite(old_img, old_ov).convert("RGB")
        new_img = Image.alpha_composite(new_img, new_ov).convert("RGB")

        pages_out.append({
            "page_num": pg + 1,
            "old_img": _img_to_b64(old_img),
            "new_img": _img_to_b64(new_img),
        })

    return {
        "pages": pages_out,
        "changes": [asdict(c) for c in all_changes],
    }