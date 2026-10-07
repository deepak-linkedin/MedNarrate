from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.core.config import get_settings
from app.services.ocr_service import extract_text_from_image, extract_text_from_scanned_pdf

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}


def extract_text(filename: str, content: bytes) -> str:
    settings = get_settings()
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("Unsupported file type. Please upload PDF, TXT, PNG, JPG, or JPEG.")

    if suffix == ".txt":
        text = content.decode("utf-8", errors="replace")

    elif suffix in {".png", ".jpg", ".jpeg"}:
        text = extract_text_from_image(content)

    else:
        reader = PdfReader(BytesIO(content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        # If the PDF is scanned/image-only, transparently fall back to OCR.
        if len(text) < 40:
            text = extract_text_from_scanned_pdf(content)

    text = text.strip()
    if not text:
        raise ValueError(
            "No readable text was found. Try a clearer image/PDF or ensure the report text is visible."
        )
    if len(text) > settings.max_extracted_chars:
        text = text[: settings.max_extracted_chars]
    return text
