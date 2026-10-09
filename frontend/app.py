from backend.database import init_db

def main():
    print("Starting RealityCheck application...")
    init_db()
    print("Database initialized successfully. Ready for frontend & OCR integration.")

if __name__ == "__main__":
    main()