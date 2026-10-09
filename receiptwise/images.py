"""Validate and normalize imported images into app-private JPEG files."""
from pathlib import Path
from uuid import uuid4
import warnings

from PIL import Image, ImageOps

MAX_BYTES = 20 * 1024 * 1024


def import_image(source, destination):
    source = Path(source)
    if not source.is_file() or source.stat().st_size > MAX_BYTES:
        raise ValueError("Choose an image smaller than 20 MB.")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{uuid4().hex}.jpg"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1600, 1600))
                image.convert("RGB").save(target, "JPEG", quality=90)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise ValueError("Cannot open this image. Choose a valid JPG, PNG or WebP.") from exc
    return str(target)
