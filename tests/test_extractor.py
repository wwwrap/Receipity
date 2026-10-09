"""Parser expectations: missing/ambiguous information must never be invented."""
import unittest
from extractor import parse_receipt


class ExtractorTests(unittest.TestCase):
    def test_complete_receipt(self):
        result = parse_receipt("Merchant: Jollibee\nDate: 2026-10-09\nTOTAL PHP 1,245.50")
        self.assertEqual(result, {"merchant": "Jollibee", "date": "2026-10-09",
                                  "amount": "1245.50", "notes": []})

    def test_header_and_split_labels(self):
        result = parse_receipt("OFFICIAL RECEIPT\n7-Eleven\n123 Main Street\nDate:\n2026-10-09\nTOTAL\n₱ 89.5")
        self.assertEqual((result["merchant"], result["date"], result["amount"]),
                         ("7-Eleven", "2026-10-09", "89.50"))
        self.assertTrue(result["notes"])

    def test_unambiguous_dates(self):
        for text, expected in [("13/10/2026", "2026-10-13"), ("10/13/2026", "2026-10-13"),
                               ("10/10/2026", "2026-10-10"), ("29 Feb 2024", "2024-02-29"),
                               ("October 9, 2026", "2026-10-09"), ("2026/10/09", "2026-10-09")]:
            with self.subTest(text=text):
                self.assertEqual(parse_receipt("Date: " + text)["date"], expected)

    def test_wrong_or_ambiguous_dates_stay_empty(self):
        for text in ("2026-02-30", "2025-02-29", "2026-13-01", "09/10/2026", "09/10/26",
                     "2026-00-12", "October 40, 2026", "2026-1O-09", "yesterday", ""):
            with self.subTest(text=text):
                result = parse_receipt("Date: " + text)
                self.assertIsNone(result["date"])
                self.assertTrue(any(note.startswith("Date:") for note in result["notes"]))

    def test_conflicting_dates_and_duplicate_dates(self):
        self.assertIsNone(parse_receipt("Date: 2026-10-09\nDate: 2026-10-10")["date"])
        self.assertEqual(parse_receipt("Date: 2026-10-09\nDate: 2026-10-09")["date"], "2026-10-09")

    def test_transaction_date_preferred_over_other_dates(self):
        result = parse_receipt("Expiry: 2027-01-01\nDate: 2026-10-09\n2020-01-01")
        self.assertEqual(result["date"], "2026-10-09")
        self.assertIsNone(parse_receipt("Expiry: 2027-01-01")["date"])
        self.assertIsNone(parse_receipt("Expiry:\n2027-01-01")["date"])
        self.assertIsNone(parse_receipt("Date: 2026-02-30\n2026-10-09")["date"])

    def test_missing_total_not_inferred_from_items_cash_or_subtotal(self):
        result = parse_receipt("SHOP\nItem A 30.00\nItem B 20.00\nSUBTOTAL 50.00\nCash 100.00\nChange 50.00")
        self.assertIsNone(result["amount"])

    def test_final_total_precedence(self):
        result = parse_receipt("Subtotal 100.00\nTOTAL 100.00\nTax 12.00\nGRAND TOTAL 112.00\nCash 200.00")
        self.assertEqual(result["amount"], "112.00")
        self.assertTrue(any(note.startswith("Amount:") for note in result["notes"]))

    def test_conflicting_totals_not_guessed(self):
        for text in ("TOTAL 10.00\nTOTAL 20.00", "Grand Total 10.00\nAmount Due 20.00",
                     "TOTAL 10.00\nGrand Total unreadable", "TOTAL 10.00\nTOTAL ?"):
            with self.subTest(text=text):
                self.assertIsNone(parse_receipt(text)["amount"])
        self.assertEqual(parse_receipt("TOTAL 10.00\nTOTAL 10.0")["amount"], "10.00")

    def test_amount_formats(self):
        for text, expected in [("PHP 1,234.56", "1234.56"), ("₱42", "42.00"),
                               ("P 42.5", "42.50"), ("42.50 PHP", "42.50"), ("0.01", "0.01")]:
            with self.subTest(text=text):
                self.assertEqual(parse_receipt("Total: " + text)["amount"], expected)

    def test_bad_amounts_never_corrected_or_rounded(self):
        for text in ("-10.00", "0", "1O.00", "1.234", "12,34.00", "10,50", "1e3",
                     "NaN", "$ 10.00", "IDR 10000", "10000000", "10.00 20.00", "(10.00)"):
            with self.subTest(text=text):
                self.assertIsNone(parse_receipt("TOTAL " + text)["amount"])

    def test_non_final_total_labels_are_ignored(self):
        for line in ("TOTAL ITEMS 3", "TOTAL TAX 12.00", "TOTAL SAVINGS 5.00", "SUB TOTAL 100.00"):
            with self.subTest(line=line):
                self.assertIsNone(parse_receipt(line)["amount"])

    def test_merchant_ambiguity(self):
        for text in ("ACME CORP\nOTHER SHOP\nDate: 2026-10-09", "Merchant: A Shop\nMerchant: B Shop"):
            with self.subTest(text=text):
                self.assertIsNone(parse_receipt(text)["merchant"])
        self.assertEqual(parse_receipt("LOGO\nMerchant: A Shop")["merchant"], "A Shop")

    def test_empty_input(self):
        result = parse_receipt(" \n\t ")
        self.assertTrue(all(result[field] is None for field in ("merchant", "date", "amount")))
        self.assertEqual(len(result["notes"]), 3)

    def test_requires_text(self):
        with self.assertRaises(TypeError):
            parse_receipt(None)
