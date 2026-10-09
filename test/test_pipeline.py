"""Read the included samples with the team's text-only OCR API."""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def evaluate_samples():
    from backend.inference_engine import recognize_receipt

    image_dir = Path(__file__).resolve().parents[1] / "sampleData" / "images"
    for image in sorted(image_dir.glob("*.png")):
        print(f"\nProcessing: {image.name}")
        print(recognize_receipt(image) or "No readable text detected.")
    print("\nText-only evaluation complete. Field parsing is not implemented yet.")


if __name__ == "__main__":
    try:
        evaluate_samples()
    except (ImportError, RuntimeError, OSError, ValueError) as exc:
        raise SystemExit(f"OCR could not run: {exc}") from None
