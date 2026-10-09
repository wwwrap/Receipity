"""Receipt validation and persistence, independent of the UI."""
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sqlite3

def validate_receipt(merchant, transaction_date, total):
    merchant = merchant.strip()
    if not merchant or len(merchant) > 120:
        raise ValueError("Enter a merchant name (1–120 characters).")
    transaction_date = transaction_date.strip()
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", transaction_date):
            raise ValueError
        date.fromisoformat(transaction_date)
    except ValueError:
        raise ValueError("Enter a real date in YYYY-MM-DD format.") from None
    total = total.strip()
    if not re.fullmatch(r"\d{1,7}(?:\.\d{1,2})?", total):
        raise ValueError("Enter a positive amount with at most 2 decimal places.")
    try:
        amount = Decimal(total)
    except InvalidOperation:
        raise ValueError("Enter a valid total amount.") from None
    if amount <= 0:
        raise ValueError("The total must be greater than zero.")
    return merchant, transaction_date, int(amount * 100)


def money(cents):
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"PHP {sign}{whole:,}.{fraction:02d}"


class ReceiptStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY, merchant TEXT NOT NULL,
                transaction_date TEXT NOT NULL,
                total_cents INTEGER NOT NULL CHECK (total_cents > 0),
                image_path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    def connect(self):
        # Context manager commits/rolls back and always closes the connection.
        from contextlib import contextmanager

        @contextmanager
        def connection():
            db = sqlite3.connect(self.path)
            db.row_factory = sqlite3.Row
            try:
                with db:
                    yield db
            finally:
                db.close()
        return connection()

    def save(self, receipt_id, merchant, transaction_date, total, image_path):
        merchant, transaction_date, cents = validate_receipt(merchant, transaction_date, total)
        if not Path(image_path).is_file():
            raise ValueError("Select a receipt image before saving.")
        with self.connect() as db:
            result = db.execute("""INSERT INTO receipts
                (id, merchant, transaction_date, total_cents, image_path)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO NOTHING""",
                (receipt_id, merchant, transaction_date, cents, str(image_path)))
            return result.rowcount == 1

    def recent(self):
        with self.connect() as db:
            return db.execute("SELECT * FROM receipts ORDER BY rowid DESC LIMIT 5").fetchall()
