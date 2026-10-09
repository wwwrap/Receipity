"""Read and parse included samples; this is a manual check, not accuracy scoring."""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def evaluate_samples():
    from backend.inference_engine import recognize_receipt
    from extractor import parse_receipt

    image_dir = Path(__file__).resolve().parents[1] / "sampleData" / "images"
    for image in sorted(image_dir.glob("*.png")):
        print(f"\nProcessing: {image.name}")
        text = recognize_receipt(image)
        print(text or "No readable text detected.")
        print(parse_receipt(text))
    print("\nReview parsed fields and notes against each image; unknown values remain None.")


if __name__ == "__main__":
    try:
        evaluate_samples()
    except (ImportError, RuntimeError, OSError, ValueError) as exc:
        raise SystemExit(f"OCR could not run: {exc}") from None
