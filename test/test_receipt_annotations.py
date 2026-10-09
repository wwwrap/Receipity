"""Check image/annotation/fixture links and manually labeled parser outcomes."""

import json
import unittest
from datetime import date
from pathlib import Path
import struct

from backend.extractor import extract_receipt


class ReceiptAnnotationTests(unittest.TestCase):
    def test_annotated_samples(self):
        root = Path(__file__).resolve().parents[1] / 'sampleData' / 'user_receipts'
        dataset = json.loads((root / 'annotations.json').read_text(encoding='utf-8'))
        self.assertEqual(len(dataset['receipts']), 4)
        for receipt in dataset['receipts']:
            with self.subTest(receipt=receipt['id']):
                image = (root / receipt['image']).read_bytes()
                self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
                width, height = struct.unpack('>II', image[16:24])
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                text = (root / receipt['transcription']).read_text(encoding='utf-8')
                result = extract_receipt(text, reference_date=date.fromisoformat(dataset['reference_date']))
                for name, expected in receipt['expected_parser'].items():
                    self.assertEqual(result[name], expected)
                    field = receipt['fields'][name]
                    if field['bbox'] is not None:
                        left, top, right, bottom = field['bbox']
                        self.assertTrue(0 <= left < right <= 1)
                        self.assertTrue(0 <= top < bottom <= 1)
                    if expected is None:
                        self.assertTrue(any(f'Review {name}:' in note for note in result['notes']))


if __name__ == '__main__':
    unittest.main()
