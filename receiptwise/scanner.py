"""Real OCR and extraction adapters. Never substitute example receipt data."""
from pathlib import Path
from extractor import parse_receipt


def scan_receipt(image_path):
    """Return merchant/date/amount/notes from the actual selected image."""
    return parse_receipt(read_receipt_text(image_path))


def read_receipt_text(image_path):
    """Use the team's offline desktop OCR API; it returns text, not fields."""
    if not Path(image_path).is_file():
        raise ValueError("Select a receipt image first.")
    try:
        from backend.inference_engine import recognize_receipt
    except ImportError as exc:
        raise RuntimeError("Install requirements-ocr.txt and run pre_download_models.py to enable desktop OCR.") from exc
    return recognize_receipt(image_path)
