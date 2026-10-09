"""Member 1's OCR public API, ready for use by Member 2 and the frontend."""

from backend.media_processor import prepare_image
from backend.model_loader import get_reader
from extractor import parse_receipt


def recognize_receipt(image):
    """Read a receipt image locally and return the recognized text as a string.

    `image` can be a file path, Pillow Image, image bytes, or NumPy RGB array.
    Newlines separate recognized text fragments. Use extract_receipt for fields.

    Example:
        text = recognize_receipt("sampleData/images/receipt_1.png")
    """
    pixels = prepare_image(image)
    reader = get_reader()
    lines = reader.readtext(pixels, detail=0, paragraph=False)
    return "\n".join(
        text.strip() for text in lines if isinstance(text, str) and text.strip()
    )


def extract_receipt(image):
    """Return merchant/date/amount/notes, preserving uncertain fields as None."""
    return parse_receipt(recognize_receipt(image))
