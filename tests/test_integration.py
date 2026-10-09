"""Exercise the scan/parser boundary using controlled OCR text, without models."""
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
                    # OCR is controlled here; never save invented production scan data.
                    with patch('receiptwise.scanner.read_receipt_text', return_value='Merchant: Test Shop\nDate: 2026-06-12\nTOTAL 123.45'):
                        result = scan_receipt(imported)
                    self.assertTrue(store.save(sample.stem, result["merchant"], result["date"],
                                               f'{result["amount"]:.2f}', imported))
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
                scan_receipt(sample)

    def test_user_photos_flow_through_parser_with_review_notes(self):
        root = ROOT / 'sampleData' / 'user_receipts'
        annotations = json.loads((root / 'annotations.json').read_text(encoding='utf-8'))
        for sample in annotations['receipts']:
            with self.subTest(sample=sample['id']):
                text = (root / sample['transcription']).read_text(encoding='utf-8')
                with patch('receiptwise.scanner.read_receipt_text', return_value=text):
                    result = scan_receipt(root / sample['image'])
                self.assertEqual(result['raw_text'], text)
                for field, expected in sample['expected_parser'].items():
                    self.assertEqual(result[field], expected)
                self.assertTrue(result['notes'])

    def test_bad_dates_and_missing_totals_stay_empty(self):
        for text in ('Merchant: Test Shop\nDate: 2026-02-30\nCash 100.00', '',
                     'Date: 03/04/2026\nSubtotal 20.00'):
            with self.subTest(text=text), patch('receiptwise.scanner.read_receipt_text', return_value=text):
                result = scan_receipt('controlled-test-input')
                self.assertIsNone(result['date'])
                self.assertIsNone(result['amount'])
                self.assertTrue(any('Review date:' in note for note in result['notes']))
                self.assertTrue(any('Review amount:' in note for note in result['notes']))

    def test_missing_image_does_not_produce_example_data(self):
        with self.assertRaisesRegex(ValueError, 'Select a receipt image'):
            scan_receipt('does-not-exist.png')
