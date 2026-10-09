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
    
    # Table to store user's budget/allowance configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    """)
    
    # Initialize default allowance if not set (e.g., 5000 budget)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('allowance', 5000.0)")
    
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

def get_balance():
    """Calculates remaining balance based on initial allowance minus total expenses."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get total starting allowance
    cursor.execute("SELECT value FROM settings WHERE key = 'allowance'")
    row = cursor.fetchone()
    allowance = row[0] if row else 5000.0
    
    # Get sum of all expenses
    cursor.execute("SELECT SUM(total) FROM expenses")
    sum_row = cursor.fetchone()
    total_spent = sum_row[0] if sum_row and sum_row[0] is not None else 0.0
    
    conn.close()
    
    remaining = allowance - total_spent
    return {
        "allowance": allowance,
        "total_spent": total_spent,
        "remaining": remaining
    }