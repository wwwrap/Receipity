"""Replace scan_receipt's body when an OCR module becomes available."""
from pathlib import Path


def scan_receipt(image_path):
    if not Path(image_path).is_file():
        raise ValueError("Select a receipt image first.")
    return {"merchant": "Jollibee", "date": "2026-10-09", "total": "245.50"}


def read_receipt_text(image_path):
    """Use the team's offline desktop OCR API; it returns text, not fields."""
    if not Path(image_path).is_file():
        raise ValueError("Select a receipt image first.")
    try:
        from backend.inference_engine import recognize_receipt
    except ImportError as exc:
        raise RuntimeError("Install requirements-ocr.txt and run pre_download_models.py to enable desktop OCR.") from exc
    return recognize_receipt(image_path)
