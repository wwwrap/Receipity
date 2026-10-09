"""Check the pulled sample assets and text-only OCR/UI boundary."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from receiptwise.images import import_image
from receiptwise.scanner import read_receipt_text, scan_receipt
from receiptwise.storage import ReceiptStore

ROOT = Path(__file__).resolve().parents[1]


class RepositoryIntegrationTests(unittest.TestCase):
    def test_all_repository_samples_can_be_imported_scanned_and_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            store = ReceiptStore(folder / "receipts.sqlite3")
            samples = sorted((ROOT / "sampleData" / "images").glob("*.png"))
            self.assertEqual(len(samples), 3)
            for sample in samples:
                with self.subTest(sample=sample.name):
                    annotation = ROOT / "sampleData" / "annotations" / f"{sample.stem}.json"
                    self.assertIsInstance(json.loads(annotation.read_text(encoding="utf-8")), dict)
                    imported = import_image(sample, folder / "images")
                    with Image.open(imported) as image:
                        self.assertLessEqual(max(image.size), 1600)
                        self.assertEqual(image.mode, "RGB")
                    result = scan_receipt(imported)
                    self.assertTrue(store.save(sample.stem, result["merchant"], result["date"],
                                               result["total"], imported))
            self.assertEqual(len(ReceiptStore(store.path).recent()), 3)

    def test_real_ocr_adapter_returns_backend_text_unchanged(self):
        sample = ROOT / "sampleData" / "images" / "receipt_1.png"
        with patch("backend.inference_engine.recognize_receipt", return_value="SHOP\nTOTAL 10.00") as recognize:
            self.assertEqual(read_receipt_text(sample), "SHOP\nTOTAL 10.00")
            recognize.assert_called_once_with(sample)

    def test_real_ocr_failure_is_not_replaced_with_mock_values(self):
        sample = ROOT / "sampleData" / "images" / "receipt_1.png"
        with patch("backend.inference_engine.recognize_receipt", side_effect=RuntimeError("Missing model")):
            with self.assertRaisesRegex(RuntimeError, "Missing model"):
                read_receipt_text(sample)
