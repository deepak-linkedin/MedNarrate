import pytest
import app.services.document_service as document_service


def test_txt_extraction():
    assert "Hemoglobin" in document_service.extract_text("report.txt", b"Hemoglobin: 8.2 g/dL")


def test_image_uses_ocr(monkeypatch):
    monkeypatch.setattr(document_service, "extract_text_from_image", lambda content: "Hemoglobin: 8.2 g/dL")
    assert "Hemoglobin" in document_service.extract_text("report.jpg", b"fake-image")


def test_supported_image_extensions(monkeypatch):
    monkeypatch.setattr(document_service, "extract_text_from_image", lambda content: "Glucose: 95 mg/dL")
    for name in ("report.png", "report.jpg", "report.jpeg"):
        assert "Glucose" in document_service.extract_text(name, b"fake")


def test_unsupported_extension():
    with pytest.raises(ValueError):
        document_service.extract_text("report.docx", b"x")
