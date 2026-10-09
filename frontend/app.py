"""Launch the Kivy receipt UI: python frontend/app.py."""
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from receiptwise.app import ReceiptWiseApp

if __name__ == "__main__":
    ReceiptWiseApp().run()
