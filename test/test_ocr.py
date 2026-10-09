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
    def test_rows_follow_geometry_not_ocr_fragment_order(self):
        def box(x, y, text, height=12):
            return ([[x, y], [x+40, y], [x+40, y+height], [x, y+height]], text, .9)
        detections = [box(150, 22, '810 .00'), box(0, 50, 'CASH'),
                      box(70, 20, 'DUE'), box(0, 20, 'TOTAL'),
                      box(0, 0, 'STORE'), box(150, 50, '1000.00')]
        self.assertEqual(inference_engine.receipt_lines(detections),
                         ['STORE', 'TOTAL DUE 810 .00', 'CASH 1000.00'])

    def test_adjacent_rows_do_not_merge_via_tall_box(self):
        detections = [([[0, 0], [40, 0], [40, 10], [0, 10]], 'TOTAL', .9),
                      ([[80, 0], [140, 0], [140, 14], [80, 14]], '120.00', .9),
                      ([[0, 16], [40, 16], [40, 26], [0, 26]], 'CASH', .9)]
        self.assertEqual(inference_engine.receipt_lines(detections), ['TOTAL 120.00', 'CASH'])

    def test_text_returned_for_member_two(self):
        class FakeReader:
            def readtext(self, pixels, detail, paragraph):
                self.pixels = pixels
                self.detail = detail
                self.paragraph = paragraph
                return [([[0, 0], [40, 0], [40, 10], [0, 10]], ' STORE ', .9),
                        ([[0, 20], [40, 20], [40, 30], [0, 30]], 'TOTAL', .9),
                        ([[80, 20], [120, 20], [120, 30], [80, 30]], ' 120.00 ', .9)]

        reader = FakeReader()
        with patch.object(inference_engine, "get_reader", return_value=reader):
            text = inference_engine.recognize_receipt(Image.new("RGB", (8, 8)))
        self.assertEqual(text, "STORE\nTOTAL 120.00")
        self.assertEqual(reader.pixels.shape, (8, 8, 3))
        self.assertEqual(reader.detail, 1)
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
