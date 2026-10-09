"""Run once WITH internet to cache EasyOCR weights for offline inference."""

from backend.model_loader import MODEL_DIR, download_models


def main():
    print("Preparing English EasyOCR weights (first run requires internet)...")
    download_models()
    print(f"EasyOCR ready. Weights stored in: {MODEL_DIR}")
    print("You can now disconnect from Wi-Fi and run: python ocr_demo.py")


if __name__ == "__main__":
    main()
