"""Local EasyOCR model setup and loading for the Receipity project.

Run `python pre_download_models.py` once ONLINE before doing OCR.
All actual scans use the cached model with downloading disabled.
"""

from functools import lru_cache
from pathlib import Path

# This folder is local to each developer's laptop, not committed to GitHub.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "easyocr"
LANGUAGES = ["en"]


def download_models():
    """Download EasyOCR model weights once (internet required)."""
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError(
            "EasyOCR is missing. Install project packages: "
            "python -m pip install -r requirements-ocr.txt"
        ) from exc

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    reader = easyocr.Reader(
        LANGUAGES,
        gpu=False,
        model_storage_directory=str(MODEL_DIR),
        download_enabled=True,
        verbose=False,
    )
    # EasyOCR's constructor downloads the detection and recognition weights.
    return reader


@lru_cache(maxsize=1)
def get_reader():
    """Return one cached EasyOCR reader without any network downloads."""
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError(
            "EasyOCR is missing. Install project packages: "
            "python -m pip install -r requirements-ocr.txt"
        ) from exc

    if not MODEL_DIR.is_dir() or not any(MODEL_DIR.glob("*.pth")):
        raise FileNotFoundError(
            f"Local EasyOCR weights were not found in {MODEL_DIR}. "
            "Connect to the internet ONCE and run: python pre_download_models.py"
        )

    # IMPORTANT: never permit downloads when scanning a receipt.
    return easyocr.Reader(
        LANGUAGES,
        gpu=False,
        model_storage_directory=str(MODEL_DIR),
        download_enabled=False,
        verbose=False,
    )
