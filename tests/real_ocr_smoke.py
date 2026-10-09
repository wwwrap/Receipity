"""Optional actual image-to-text check; requires local EasyOCR packages/weights.

Run: python -m tests.real_ocr_smoke. Does not download anything or use mock OCR.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageFont
from receiptwise.scanner import read_receipt_text
from extractor import parse_receipt


def main():
    with TemporaryDirectory(prefix="receiptwise-real-ocr-") as directory:
        path = Path(directory) / "receipt.png"
        image = Image.new("RGB", (1100, 550), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=40)
        for index, line in enumerate(("Merchant: CORNER MARKET", "Date: 2026-10-09", "TOTAL PHP 78.25")):
            draw.text((50, 60 + index * 120), line, fill="black", font=font)
        image.save(path)
        text = read_receipt_text(path)
        print("Recognized text:\n" + text)
        result = parse_receipt(text)
        print("Extracted:", result)
        assert result["merchant"] == "CORNER MARKET", result
        assert result["date"] == "2026-10-09", result
        assert result["amount"] == "78.25", result
        print("PASS: actual image -> EasyOCR -> parsed fields, no sample-data fallback")


if __name__ == "__main__":
    main()
