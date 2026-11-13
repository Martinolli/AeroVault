"""Page text extraction: PyMuPDF primary, pypdf fallback, optional Tesseract OCR."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MIN_TEXT_CHARS = 50


@dataclass
class PageText:
    page_no: int
    text: str
    ocr_used: bool = False


def _ocr_fitz_page(page) -> str:
    try:
        import io

        import pytesseract
        from PIL import Image

        pix = page.get_pixmap(dpi=300)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(image)
    except Exception:
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


def extract_pages(path: Path, ocr: bool = False, password: str = "") -> tuple[list[PageText], str]:
    """Extract page text. Returns (pages, engine). Raises on unreadable files."""
    try:
        return _extract_fitz(path, ocr, password), "pymupdf"
    except ImportError:
        return _extract_pypdf(path, password), "pypdf"
    except Exception:
        # Some AES-encrypted or damaged PDFs fail in PyMuPDF; pypdf often handles them.
        return _extract_pypdf(path, password), "pypdf"
