"""Legacy database checks use temporary storage, never the shared sample DB."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend import database


class DatabaseTests(unittest.TestCase):
    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(database, "DB_PATH", str(Path(directory) / "test.db")):
                database.init_db()
                database.save_expense("Bebek Bengil", "2026-10-10", 1591.60, "Food")
                rows = database.get_expenses()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["merchant"], "Bebek Bengil")
                self.assertEqual(rows[0]["total"], 1591.60)


if __name__ == "__main__":
    unittest.main()
