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
                    with patch("receiptwise.scanner.read_receipt_text", return_value=
                               f"Merchant: {sample.stem}\nDate: 2026-10-09\nTotal: 123.45"):
                        result = scan_receipt(imported)
                    self.assertTrue(store.save(sample.stem, result["merchant"], result["date"],
                                               result["amount"], imported))
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

    def test_scan_uses_image_text_not_placeholder_values(self):
        sample = ROOT / "sampleData" / "images" / "receipt_1.png"
        with patch("backend.inference_engine.recognize_receipt", return_value=
                   "Merchant: Actual Photo Shop\nDate: 2026-10-01\nTOTAL 78.25") as recognize:
            result = scan_receipt(sample)
        recognize.assert_called_once_with(sample)
        self.assertEqual((result["merchant"], result["date"], result["amount"]),
                         ("Actual Photo Shop", "2026-10-01", "78.25"))

    def test_scan_leaves_empty_ocr_blank_and_propagates_failures(self):
        with patch("receiptwise.scanner.read_receipt_text", return_value=""):
            result = scan_receipt("image.png")
        self.assertTrue(all(result[key] is None for key in ("merchant", "date", "amount")))
        with patch("receiptwise.scanner.read_receipt_text", side_effect=RuntimeError("Unreadable")):
            with self.assertRaisesRegex(RuntimeError, "Unreadable"):
                scan_receipt("image.png")

    def test_backend_extraction_can_be_saved_without_type_conversion(self):
        from backend.inference_engine import extract_receipt
        sample = ROOT / "sampleData" / "images" / "receipt_1.png"
        with patch("backend.inference_engine.recognize_receipt", return_value=
                   "Merchant: Test Shop\nDate: 2026-10-09\nTotal: PHP 123.45"):
            result = extract_receipt(sample)
        with tempfile.TemporaryDirectory() as directory:
            store = ReceiptStore(Path(directory) / "test.sqlite3")
            store.save("parsed", result["merchant"], result["date"], result["amount"], sample)
            self.assertEqual(store.recent()[0]["total_cents"], 12345)
