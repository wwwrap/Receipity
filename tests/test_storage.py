import tempfile
import unittest
from pathlib import Path

from receiptwise.storage import ReceiptStore, validate_receipt, money


class ReceiptStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.image = self.root / "receipt.jpg"
        self.image.write_bytes(b"test image reference")
        self.store = ReceiptStore(self.root / "receipts.sqlite3")

    def test_save_persistence_and_duplicate_tap(self):
        self.assertEqual(self.store.recent(), [])
        args = ("draft-1", " Shop ", "2026-10-09", "245.50", str(self.image))
        self.assertTrue(self.store.save(*args))
        self.assertFalse(self.store.save(*args))
        reopened = ReceiptStore(self.store.path)
        self.assertEqual(len(reopened.recent()), 1)
        self.assertEqual(reopened.recent()[0]["total_cents"], 24550)
        self.assertEqual(reopened.recent()[0]["merchant"], "Shop")

    def test_invalid_input_does_not_save_receipt(self):
        for merchant, day, total in [("", "2026-10-09", "1"), ("Shop", "2026-02-30", "1"),
                                     ("Shop", "2026-10-09", "0"), ("Shop", "2026-10-09", "NaN")]:
            with self.subTest(merchant=merchant, day=day, total=total), self.assertRaises(ValueError):
                self.store.save("bad", merchant, day, total, str(self.image))
        self.assertEqual(self.store.recent(), [])

    def test_exact_receipt_amounts(self):
        for index, amount in enumerate(["0.10", "0.20", "1300"]):
            self.store.save(str(index), "Shop", "2026-10-09", amount, str(self.image))
        self.assertEqual([row["total_cents"] for row in self.store.recent()], [130000, 20, 10])
        self.assertEqual(money(130000), "PHP 1,300.00")

    def test_bad_amounts_and_dates(self):
        for total in ["-1", "1.001", "inf", "1e3", "1,000", "10000000", ""]:
            with self.subTest(total=total), self.assertRaises(ValueError):
                validate_receipt("Shop", "2026-10-09", total)
        for day in ["2026-2-01", "today", "2025-02-29"]:
            with self.subTest(day=day), self.assertRaises(ValueError):
                validate_receipt("Shop", day, "1")
        self.assertEqual(validate_receipt("Shop", "2024-02-29", "12.34")[2], 1234)

    def test_missing_image(self):
        with self.assertRaises(ValueError):
            self.store.save("bad", "Shop", "2026-10-09", "1", "missing.jpg")


if __name__ == "__main__":
    unittest.main()
