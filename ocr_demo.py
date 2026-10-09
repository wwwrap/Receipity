"""Quick manual OCR test. Defaults to the first included sample receipt."""

import argparse
from pathlib import Path

from backend.inference_engine import recognize_receipt


def main():
    parser = argparse.ArgumentParser(description="Offline receipt OCR demo")
    parser.add_argument(
        "image",
        nargs="?",
        default=str(Path(__file__).resolve().parent / "sampleData" / "images" / "receipt_1.png"),
        help="Path to a receipt image (defaults to sampleData/images/receipt_1.png)",
    )
    args = parser.parse_args()
    print(f"Scanning locally: {args.image}")
    try:
        text = recognize_receipt(args.image)
    except (FileNotFoundError, RuntimeError, ValueError, ImportError, OSError) as exc:
        parser.exit(status=1, message=f"OCR could not run: {exc}\n")

    print("\n--- OCR TEXT ---")
    print(text if text else "No readable text detected; try a clearer image.")
    print("--- END ---")


if __name__ == "__main__":
    main()
