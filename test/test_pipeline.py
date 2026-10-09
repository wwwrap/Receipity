"""Manually evaluate real OCR and extraction on the supplied receipt photos."""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def evaluate_samples():
    import json
    from receiptwise.scanner import scan_receipt

    image_dir = Path(__file__).resolve().parents[1] / "sampleData" / "user_receipts" / "images"
    for image in sorted(image_dir.glob("*.png")):
        print(f"\nProcessing: {image.name}")
        print(json.dumps(scan_receipt(image), indent=2, ensure_ascii=True))
    print("\nReview extracted fields against sampleData/user_receipts/annotations.json.")


if __name__ == "__main__":
    try:
        evaluate_samples()
    except (ImportError, RuntimeError, OSError, ValueError) as exc:
        raise SystemExit(f"OCR could not run: {exc}") from None
