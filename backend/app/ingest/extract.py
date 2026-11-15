"""Page text extraction: PyMuPDF primary, pypdf fallback, optional Tesseract OCR."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sys

MIN_TEXT_CHARS = 50
_OCR_WARNED = False


@dataclass
class PageText:
    page_no: int
    text: str
    ocr_used: bool = False


def _tesseract_cmd() -> str:
    cmd = os.environ.get("AEROVAULT_TESSERACT_CMD", "")
    if cmd:
        return cmd
    default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    return default if os.path.exists(default) else "tesseract"


def _ocr_fitz_page(page) -> str:
    """Render the page and OCR it. Scanned pages often have a dark frame and
    grey background that make full-page segmentation return nothing, so the
    margins are cropped and contrast normalised before OCR."""
    global _OCR_WARNED
    try:
        import io

        import pytesseract
        from PIL import Image, ImageOps

        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()
        pix = page.get_pixmap(dpi=300)
        image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        w, h = image.size
        image = image.crop((int(w * 0.06), int(h * 0.06), int(w * 0.94), int(h * 0.94)))
        image = ImageOps.autocontrast(image)
        return pytesseract.image_to_string(image, config="--psm 6")
    except Exception as exc:  # noqa: BLE001
        if not _OCR_WARNED:
            print(f"OCR warning: {type(exc).__name__}: {exc}", file=sys.stderr)
            _OCR_WARNED = True
        return ""


def _extract_fitz(path: Path, ocr: bool, password: str) -> list[PageText]:
    import fitz

    pages: list[PageText] = []
    with fitz.open(str(path)) as doc:
        if doc.needs_pass and password:
            doc.authenticate(password)
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            used = False
            if ocr and len(text.strip()) < MIN_TEXT_CHARS:
                ocr_text = _ocr_fitz_page(page)
                if ocr_text.strip():
                    text = ocr_text
                    used = True
            pages.append(PageText(i, text, used))
    return pages


def _extract_pypdf(path: Path, password: str) -> list[PageText]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        decrypted = False
        for candidate in ("", password):
            try:
                if reader.decrypt(candidate):
                    decrypted = True
                    break
            except Exception:  # noqa: BLE001
                continue
        if not decrypted:
            raise ValueError("PDF is encrypted and no valid password was provided")
    pages: list[PageText] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(PageText(i, text))
    return pages


def _extract_text(path: Path) -> list[PageText]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [PageText(1, text)] if text.strip() else []


def _extract_docx(path: Path) -> list[PageText]:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    text = "\n".join(parts)
    return [PageText(1, text)] if text.strip() else []


def extract_pages(path: Path, ocr: bool = False, password: str = "") -> tuple[list[PageText], str]:
    """Extract page text. Returns (pages, engine). Raises on unreadable files."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _extract_text(path), "text"
    if suffix == ".docx":
        return _extract_docx(path), "docx"
    if suffix == ".xml":
        from .regulatory import _xml_to_text

        return [PageText(1, _xml_to_text(path.read_bytes()))], "xml"
    try:
        return _extract_fitz(path, ocr, password), "pymupdf"
    except ImportError:
        return _extract_pypdf(path, password), "pypdf"
    except Exception:
        # Some AES-encrypted or damaged PDFs fail in PyMuPDF; pypdf often handles them.
        return _extract_pypdf(path, password), "pypdf"
