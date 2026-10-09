from backend.database import init_db, save_expense, get_expenses, get_balance

def test_database():
    print("Initializing database...")
    init_db()

    print("Saving a test expense...")
    save_expense(merchant="Bebek Bengil", date="2026-10-10", total=1591.60, category="Food")

    print("\nFetching all expenses:")
    expenses = get_expenses()
    for exp in expenses:
        print(exp)

    print("\nChecking balance summary:")
    balance = get_balance()
    print(balance)

if __name__ == "__main__":
    test_database()