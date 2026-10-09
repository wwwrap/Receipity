"""Receipt image -> local OCR -> conservative field extraction."""
from pathlib import Path


def scan_receipt(image_path):
    # Lazy import keeps the manually entered Android flow independent of OCR.
    from backend.extractor import extract_receipt

    text = read_receipt_text(image_path)
    return {**extract_receipt(text), "raw_text": text}


def read_receipt_text(image_path):
    """Use the team's offline desktop OCR API; it returns text, not fields."""
    if not Path(image_path).is_file():
        raise ValueError("Select a receipt image first.")
    try:
        from backend.inference_engine import recognize_receipt
    except ImportError as exc:
        raise RuntimeError("Install requirements-ocr.txt and run pre_download_models.py to enable desktop OCR.") from exc
    return recognize_receipt(image_path)
