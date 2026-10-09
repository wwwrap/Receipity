import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reality_check.db")

def init_db():
    """Initializes the SQLite database and creates the expenses table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant TEXT,
            date TEXT,
            total REAL,
            category TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def save_expense(merchant: str, date: str, total: float, category: str = "General"):
    """Saves a scanned receipt expense to the database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO expenses (merchant, date, total, category)
        VALUES (?, ?, ?, ?)
    """, (merchant, date, total, category))
    
    conn.commit()
    conn.close()

def get_expenses():
    """Retrieves all stored expenses ordered by most recent."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
