"""Fast tests that do not download model weights or access the internet."""

import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from backend import inference_engine, model_loader
from backend.media_processor import prepare_image


class ImagePreparationTests(unittest.TestCase):
    def setUp(self):
        self.rgb = Image.new("RGB", (16, 20), (50, 100, 150))

    def test_pil_to_rgb_array(self):
        pixels = prepare_image(self.rgb)
        self.assertEqual(pixels.shape, (20, 16, 3))
        self.assertEqual(pixels.dtype, np.uint8)
        self.assertEqual(pixels[0, 0].tolist(), [50, 100, 150])

    def test_grayscale_and_rgba_arrays(self):
        self.assertEqual(prepare_image(np.zeros((10, 10), dtype=np.uint8)).shape, (10, 10, 3))
        self.assertEqual(prepare_image(np.zeros((10, 10, 4), dtype=np.uint8)).shape, (10, 10, 3))

    def test_file_path_and_image_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "receipt.png"
            self.rgb.save(file)
            self.assertEqual(prepare_image(file).shape, (20, 16, 3))
        buf = io.BytesIO()
        self.rgb.save(buf, format="PNG")
        self.assertEqual(prepare_image(buf.getvalue()).shape, (20, 16, 3))

    def test_missing_and_invalid_images(self):
        with self.assertRaises(FileNotFoundError):
            prepare_image("a-file-that-does-not-exist.png")
        with self.assertRaises(ValueError):
            prepare_image(None)
        with self.assertRaises(TypeError):
            prepare_image(12345)
        with self.assertRaises(ValueError):
            prepare_image(np.zeros((5, 5, 3), dtype=np.float32))


class InferenceTests(unittest.TestCase):
    def test_text_returned_for_member_two(self):
        class FakeReader:
            def readtext(self, pixels, detail, paragraph):
                self.pixels = pixels
                self.detail = detail
                self.paragraph = paragraph
                return [" STORE ", "TOTAL", " 120.00 ", " "]

        reader = FakeReader()
        with patch.object(inference_engine, "get_reader", return_value=reader):
            text = inference_engine.recognize_receipt(Image.new("RGB", (8, 8)))
        self.assertEqual(text, "STORE\nTOTAL\n120.00")
        self.assertEqual(reader.pixels.shape, (8, 8, 3))
        self.assertEqual(reader.detail, 0)
        self.assertIs(reader.paragraph, False)


class ModelLoaderTests(unittest.TestCase):
    def tearDown(self):
        model_loader.get_reader.cache_clear()

    def test_offline_reader_reuses_loaded_weights(self):
        reader_calls = []

        class FakeReader:
            def __init__(self, *args, **kwargs):
                reader_calls.append(kwargs)

        with tempfile.TemporaryDirectory() as folder:
            model_folder = Path(folder)
            (model_folder / "demo.pth").touch()
            with patch.object(model_loader, "MODEL_DIR", model_folder), patch.dict(
                sys.modules, {"easyocr": types.SimpleNamespace(Reader=FakeReader)}
            ):
                model_loader.get_reader.cache_clear()
                first = model_loader.get_reader()
                second = model_loader.get_reader()
                self.assertIs(first, second)
                self.assertEqual(len(reader_calls), 1)
                self.assertIs(reader_calls[0]["download_enabled"], False)
                self.assertIs(reader_calls[0]["gpu"], False)

    def test_missing_weights_have_clear_instructions(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(model_loader, "MODEL_DIR", Path(folder)), patch.dict(
                sys.modules, {"easyocr": types.SimpleNamespace(Reader=object)}
            ):
                model_loader.get_reader.cache_clear()
                with self.assertRaisesRegex(FileNotFoundError, "pre_download_models.py"):
                    model_loader.get_reader()

    def test_explicit_download_enables_network_for_first_setup(self):
        calls = []

        def fake_reader(*args, **kwargs):
            calls.append(kwargs)
            return object()

        with tempfile.TemporaryDirectory() as folder:
            with patch.object(model_loader, "MODEL_DIR", Path(folder)), patch.dict(
                sys.modules, {"easyocr": types.SimpleNamespace(Reader=fake_reader)}
            ):
                model_loader.download_models()
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["download_enabled"], True)


if __name__ == "__main__":
    unittest.main()
