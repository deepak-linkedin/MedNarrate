from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _get_engine():
    try:
        from rapidocr import RapidOCR
    except ImportError as exc:
        raise RuntimeError(
            "OCR dependencies are not installed. Install rapidocr and onnxruntime."
        ) from exc
    return RapidOCR()


def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text only. This service intentionally performs no medical reasoning."""
    settings = get_settings()
    if not settings.ocr_enabled:
        raise ValueError("OCR is disabled on this deployment.")

    try:
        result = _get_engine()(image_bytes)
    except Exception as exc:
        raise ValueError(f"OCR could not read this image: {exc}") from exc

    txts = getattr(result, "txts", None) or []
    scores = getattr(result, "scores", None) or []

    lines: list[str] = []
    for index, text in enumerate(txts):
        if not text or not str(text).strip():
            continue
        score = float(scores[index]) if index < len(scores) else 1.0
        if score >= settings.ocr_min_confidence:
            lines.append(str(text).strip())

    return "\n".join(lines).strip()


def extract_text_from_scanned_pdf(content: bytes) -> str:
    """Render PDF pages to images and OCR them when normal PDF text extraction fails."""
    settings = get_settings()
    if not settings.ocr_enabled:
        return ""

    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("Scanned-PDF OCR requires pymupdf.") from exc

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open PDF for OCR: {exc}") from exc

    scale = max(settings.ocr_pdf_dpi, 72) / 72.0
    matrix = fitz.Matrix(scale, scale)
    page_texts: list[str] = []
    try:
        for page_number, page in enumerate(document):
            if page_number >= settings.max_pdf_ocr_pages:
                break
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            text = extract_text_from_image(pixmap.tobytes("png"))
            if text:
                page_texts.append(text)
    finally:
        document.close()

    return "\n\n".join(page_texts).strip()
