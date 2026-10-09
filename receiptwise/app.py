"""Kivy presentation and receipt workflow."""
import os
from pathlib import Path
import sqlite3
from threading import Thread
from uuid import uuid4

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.utils import platform

from receiptwise.picker import ImagePicker
from receiptwise.scanner import scan_receipt, read_receipt_text
from receiptwise.storage import ReceiptStore, money


class ReceiptWiseApp(App):
    title = "ReceiptWise"
    image_path = StringProperty("")
    status = StringProperty("Select a receipt image to get started.")
    status_error = BooleanProperty(False)
    history_text = StringProperty("No saved receipts yet.")
    saved = BooleanProperty(False)
    storage_ready = BooleanProperty(False)
    desktop_ocr = BooleanProperty(platform != "android")
    scanning = BooleanProperty(False)
    raw_text = StringProperty("")

    def build(self):
        Window.clearcolor = (.95, .96, .98, 1)
        Window.softinput_mode = "below_target"
        if platform != "android":
            Window.size = (390, 780)
        self.receipt_id = uuid4().hex
        self.data_folder = Path(os.environ.get("RECEIPTWISE_DATA_DIR", self.user_data_dir))
        self.picker = ImagePicker(self.data_folder / "images", self.image_selected, self.show_error)
        root = Builder.load_file(str(Path(__file__).with_name("interface.kv")))
        try:
            self.store = ReceiptStore(self.data_folder / "receipts.sqlite3")
            self.refresh_receipts()
            self.storage_ready = True
        except (OSError, sqlite3.Error):
            Clock.schedule_once(lambda dt: self.show_error("Cannot open local storage. Restart the app and try again."))
        return root

    def select_image(self):
        self.picker.open()

    def image_selected(self, path):
        self.clear_draft()
        self.image_path = path
        self.set_status("Image selected. Scan it or enter the details below.")

    def scan(self):
        if self.scanning or self.saved:
            return
        self.raw_text = ""
        try:
            result = scan_receipt(self.image_path)
        except ValueError as exc:
            self.show_error(str(exc))
            return
        for name in ("merchant", "date", "total"):
            self.root.ids[name].text = result[name]
        self.set_status("Scan successful (mock data). Check the details before saving.")

    def read_ocr(self):
        if self.scanning or not self.image_path or self.saved or not self.desktop_ocr:
            return
        draft_id = self.receipt_id
        image_path = self.image_path
        self.scanning = True
        self.raw_text = ""
        self.set_status("Reading receipt text locally. This may take a moment...")

        def worker():
            text, error = "", None
            try:
                text = read_receipt_text(image_path)
            except Exception as exc:
                error = str(exc) or "OCR could not read this image."
            Clock.schedule_once(lambda dt: finish(text, error))

        def finish(text, error):
            self.scanning = False
            if self.receipt_id != draft_id or self.saved:
                return
            if error:
                self.show_error(error)
                return
            self.raw_text = text
            # The upstream API has no field parser. Never retain mock values as OCR output.
            for name in ("merchant", "date", "total"):
                self.root.ids[name].text = ""
            self.set_status("OCR text ready. Enter merchant, date and total from the text below."
                            if text else "No readable text found. Try another photo or enter details manually.")

        Thread(target=worker, daemon=True).start()

    def save_receipt(self):
        if self.scanning:
            return
        if self.saved:
            self.set_status("This receipt is already saved. Tap New Receipt to add another.")
            return
        if not self.storage_ready:
            self.show_error("Local storage is unavailable. Restart the app and try again.")
            return
        try:
            if not self.image_path:
                raise ValueError("Select a receipt image before saving.")
            ids = self.root.ids
            inserted = self.store.save(self.receipt_id, ids.merchant.text, ids.date.text,
                                       ids.total.text, self.image_path)
        except ValueError as exc:
            self.show_error(str(exc))
            return
        except (OSError, sqlite3.Error):
            self.show_error("Could not save the receipt. Your details are still here; please try again.")
            return
        self.saved = True
        try:
            self.refresh_receipts()
        except sqlite3.Error:
            self.show_error("Receipt saved, but recent receipts could not refresh. Restart to reload them.")
            return
        self.set_status("Receipt saved successfully." if inserted else "This receipt is already saved.")

    def refresh_receipts(self):
        rows = self.store.recent()
        self.history_text = "\n\n".join(
            f"{row['merchant']}\n{row['transaction_date']}  |  {money(row['total_cents'])}"
            for row in rows) or "No saved receipts yet."

    def clear_draft(self):
        if self.image_path and not self.saved:
            try:
                Path(self.image_path).unlink(missing_ok=True)
            except OSError:
                pass
        self.image_path = ""
        self.raw_text = ""
        self.receipt_id = uuid4().hex
        self.saved = False
        for name in ("merchant", "date", "total"):
            self.root.ids[name].text = ""
        self.set_status("Select a receipt image to get started.")

    def set_status(self, message):
        self.status_error = False
        self.status = message

    def show_error(self, message):
        self.status_error = True
        self.status = message

    def on_pause(self):
        # Keep the activity alive when the Android document picker takes focus.
        return True

    def on_stop(self):
        self.picker.close()
