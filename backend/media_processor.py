"""Convert uploaded receipt images into the RGB arrays expected by EasyOCR."""

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def prepare_image(image):
    """Return an RGB uint8 NumPy array.

    Supported inputs: a file path, raw image bytes, a Pillow image, or an RGB,
    grayscale, or RGBA NumPy array. Arrays are assumed RGB, not OpenCV BGR.
    """
    if image is None:
        raise ValueError("Please provide a receipt image.")

    if isinstance(image, (str, Path)):
        path = Path(image)
        if not path.is_file():
            raise FileNotFoundError(f"Receipt image does not exist: {path}")
        with Image.open(path) as opened:
            prepared = ImageOps.exif_transpose(opened).convert("RGB")

    elif isinstance(image, (bytes, bytearray)):
        with Image.open(BytesIO(image)) as opened:
            prepared = ImageOps.exif_transpose(opened).convert("RGB")

    elif isinstance(image, Image.Image):
        prepared = ImageOps.exif_transpose(image).convert("RGB")

    elif isinstance(image, np.ndarray):
        if image.dtype != np.uint8:
            raise ValueError("Image arrays must contain uint8 pixel values.")
        if image.ndim == 2:
            prepared = Image.fromarray(image, mode="L").convert("RGB")
        elif image.ndim == 3 and image.shape[2] in (3, 4):
            mode = "RGB" if image.shape[2] == 3 else "RGBA"
            prepared = Image.fromarray(image, mode=mode).convert("RGB")
        else:
            raise ValueError("Image arrays must be grayscale, RGB, or RGBA.")

    else:
        raise TypeError(
            "Unsupported image input. Use an image path, bytes, PIL Image, "
            "or NumPy array."
        )

    return np.array(prepared, dtype=np.uint8, copy=True)
