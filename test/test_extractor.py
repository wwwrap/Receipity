"""Synthetic Philippine-style OCR fixtures; run with unittest discovery."""

import unittest
from datetime import date
from pathlib import Path

from backend.extractor import extract_receipt, parse_receipt


class ExtractorTests(unittest.TestCase):
    def parse(self, text, **kwargs):
        return extract_receipt(text, reference_date=date(2026, 10, 10), **kwargs)

    def test_philippine_receipt(self):
        result = self.parse("""MABUHAY SUPERMARKET
123 Rizal Avenue, Quezon City
VAT REG TIN 123-456-789-000
SALES INVOICE
Date: September 30, 2026 14:35
Rice 250.00
VATable Sales 223.21
VAT 26.79
Subtotal 250.00
TOTAL PHP 250.00
TOTAL ITEMS 1
CASH 500.00
CHANGE 250.00
ATP No. 12345
Date Issued: 01/02/2024
""")
        self.assertEqual(result['merchant'], 'MABUHAY SUPERMARKET')
        self.assertEqual(result['date'], '2026-09-30')
        self.assertEqual(result['amount'], 250.0)
        self.assertTrue(any('Review merchant' in n for n in result['notes']))
        self.assertFalse(any('Review date' in n or 'Review amount' in n for n in result['notes']))

    def test_currency_and_grouping(self):
        for amount in ('₱1,234.50', 'PHP 1,234.50', 'P 1234.50', '1234.50 PHP', '1234.50 PESOS'):
            with self.subTest(amount=amount):
                self.assertEqual(self.parse('TOTAL: ' + amount)['amount'], 1234.5)

    def test_valid_dates(self):
        for raw in ('2026-09-30', '2026/09/30', '09/30/2026', '30/09/2026', '30-Sep-2026', 'Sep 30, 2026'):
            with self.subTest(raw=raw):
                self.assertEqual(self.parse('Date: ' + raw)['date'], '2026-09-30')

    def test_unsafe_dates_need_review(self):
        for raw in ('03/04/2026', '02/30/2026', '2025-02-29', '2026-13-01', '09/30/26', '2027-01-01', '2O26-09-30', 'not readable'):
            with self.subTest(raw=raw):
                result = self.parse('Date: ' + raw)
                self.assertIsNone(result['date'])
                self.assertTrue(any('Review date' in n for n in result['notes']))

    def test_explicit_date_order(self):
        self.assertEqual(self.parse('Date: 03/04/2026', date_order='MDY')['date'], '2026-03-04')
        self.assertEqual(self.parse('Date: 03/04/2026', date_order='DMY')['date'], '2026-04-03')
        self.assertIsNone(self.parse('Date: 30/09/2026', date_order='MDY')['date'])

    def test_leap_day_and_equal_month_day(self):
        self.assertEqual(self.parse('Date: 2024-02-29')['date'], '2024-02-29')
        self.assertEqual(self.parse('Date: 03/03/2026')['date'], '2026-03-03')

    def test_conflicting_dates(self):
        result = self.parse('Date: 2026-09-30\nDate: 2026-09-29')
        self.assertIsNone(result['date'])
        self.assertTrue(any('conflicting' in n for n in result['notes']))

    def test_duplicate_dates_are_ok(self):
        self.assertEqual(self.parse('Date: 2026-09-30\nDate: Sep 30, 2026')['date'], '2026-09-30')

    def test_transaction_date_over_unlabeled_date(self):
        self.assertEqual(self.parse('2024-01-01\nTransaction Date: 2026-09-30')['date'], '2026-09-30')

    def test_invalid_transaction_does_not_fall_back(self):
        self.assertIsNone(self.parse('2024-01-01\nTransaction Date: 2026-02-30')['date'])

    def test_permit_dates_are_not_transaction_dates(self):
        self.assertIsNone(self.parse('ATP Date Issued: 2024-01-01\nValid until 2026-12-31')['date'])
        self.assertIsNone(self.parse('Date Issued:\n2024-01-01')['date'])

    def test_conflicting_merchants(self):
        self.assertIsNone(self.parse('Merchant: Shop A\nMerchant: Shop B')['merchant'])

    def test_total_due_beats_gross_total(self):
        self.assertEqual(self.parse('TOTAL 100.00\nDiscount 20.00\nAMOUNT DUE 80.00\nCash 100.00')['amount'], 80.0)

    def test_conflicting_totals(self):
        for text in ('TOTAL 100.00\nTOTAL 200.00', 'GRAND TOTAL 100.00\nAMOUNT DUE 200.00'):
            with self.subTest(text=text):
                self.assertIsNone(self.parse(text)['amount'])

    def test_duplicate_totals(self):
        self.assertEqual(self.parse('TOTAL 100.00\nTOTAL PHP 100.00')['amount'], 100.0)

    def test_missing_total_not_invented(self):
        for text in ('Rice 100.00\nBread 50.00', 'Subtotal 100.00\nVAT 12.00\nCash 200.00\nChange 88.00', 'TOTAL ITEMS 2'):
            with self.subTest(text=text):
                result = self.parse(text)
                self.assertIsNone(result['amount'])
                self.assertTrue(any('Review amount' in n for n in result['notes']))

    def test_unreadable_totals(self):
        for value in ('1O0.00', '1,23.00', '100.0', '100.00 200.00', '-100.00', '(100.00)', 'USD 100.00', '100.001'):
            with self.subTest(value=value):
                self.assertIsNone(self.parse('TOTAL ' + value)['amount'])

    def test_bad_due_does_not_fall_back_to_total(self):
        self.assertIsNone(self.parse('TOTAL 100.00\nAMOUNT DUE ???')['amount'])

    def test_split_labels(self):
        result = self.parse('Merchant: Sari-Sari Store\nDate:\n2026-09-30\nTOTAL\n₱ 125.50')
        self.assertEqual(result, {'merchant': 'Sari-Sari Store', 'date': '2026-09-30', 'amount': 125.5, 'notes': []})

    def test_zero_and_integer_totals(self):
        self.assertEqual(self.parse('TOTAL 0.00')['amount'], 0.0)
        self.assertEqual(self.parse('TOTAL PHP 125')['amount'], 125.0)

    def test_empty_text(self):
        result = self.parse(' \n\t')
        self.assertEqual(set(result), {'merchant', 'date', 'amount', 'notes'})
        self.assertIsNone(result['merchant'])
        self.assertIsNone(result['date'])
        self.assertIsNone(result['amount'])
        self.assertEqual(len(result['notes']), 3)

    def test_merchant_header_noise(self):
        result = self.parse('OFFICIAL RECEIPT\nVAT REG TIN 123-456-789\n7-ELEVEN\nDate: 2026-09-30')
        self.assertEqual(result['merchant'], '7-ELEVEN')

    def test_missing_merchant_does_not_use_item(self):
        self.assertIsNone(self.parse('Date: 2026-09-30\nChocolate\nTOTAL 100.00')['merchant'])

    def test_input_validation(self):
        with self.assertRaises(TypeError):
            self.parse(None)
        with self.assertRaises(ValueError):
            self.parse('', date_order='YMD')
        self.assertIs(parse_receipt, extract_receipt)

    def test_user_photo_transcriptions(self):
        fixtures = Path(__file__).parent / 'fixtures' / 'receipts'
        cases = (
            ('01_goldilocks.txt', None, '2025-06-16', 810.0),
            ('02_grocery.txt', None, '2026-06-12', 1696.35),
            ('03_north_park.txt', 'North Park Noodle House Inc.', None, 1540.0),
            ('04_coffee.txt', None, None, 460.43),
        )
        for filename, merchant, transaction_date, amount in cases:
            with self.subTest(filename=filename):
                result = self.parse((fixtures / filename).read_text(encoding='utf-8'))
                self.assertEqual(result['merchant'], merchant)
                self.assertEqual(result['date'], transaction_date)
                self.assertEqual(result['amount'], amount)
                self.assertTrue(any('Review merchant' in n for n in result['notes']))
                self.assertEqual(any('Review date' in n for n in result['notes']), transaction_date is None)
                self.assertFalse(any('Review amount' in n for n in result['notes']))

    def test_abbreviated_total_due(self):
        for label in ('Total Amt Due', 'TOTAL AMT. DUE'):
            with self.subTest(label=label):
                self.assertEqual(self.parse('Total 1800.00\n' + label + ' Php 1,696.35')['amount'], 1696.35)

    def test_abbreviated_transaction_date(self):
        self.assertEqual(self.parse('2024-01-01\nTrans. Date: 2026-06-12')['date'], '2026-06-12')
        self.assertEqual(self.parse('Trans. Date:\n2026-06-12')['date'], '2026-06-12')
        self.assertIsNone(self.parse('Trans. Date: 2026-02-30\n2024-01-01')['date'])

    def test_cropped_receipt_product_is_not_merchant(self):
        for text in ('1 PICKUP Blend\nOriginal PICKUP Recipe', 'Take Away\nPICKUP Blend', '1.000 Iced Vanilla Latte'):
            with self.subTest(text=text):
                self.assertIsNone(self.parse(text)['merchant'])

    def test_occluded_total_label_needs_review(self):
        self.assertIsNone(self.parse('rand Total: P460.43\nCash P500.00\nChange P39.57')['amount'])


if __name__ == '__main__':
    unittest.main()
