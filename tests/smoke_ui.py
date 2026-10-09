"""Run with `python -m tests.smoke_ui`; opens a window and exits after checks."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

test_directory = TemporaryDirectory(prefix="receiptwise-ui-")
os.environ["RECEIPTWISE_DATA_DIR"] = test_directory.name

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from receiptwise.app import ReceiptWiseApp
from receiptwise.storage import ReceiptStore


class SmokeApp(ReceiptWiseApp):
    failure = None
    ticks = 0

    def on_start(self):
        Clock.schedule_once(self.start_checks, .3)

    def click(self, text, root=None):
        button = next(widget for widget in (root or self.root).walk()
                      if isinstance(widget, Button) and widget.text == text)
        assert not button.disabled, text
        button.dispatch("on_release")

    def start_checks(self, dt):
        try:
            assert self.history_text == "No saved receipts yet."
            self.click("Save Receipt")
            assert self.status_error
            source = Path(__file__).resolve().parents[1] / "sampleData" / "user_receipts" / "images" / "02_grocery.png"
            self.click("Select Receipt Image")
            popup = next(child for child in Window.children if isinstance(child, Popup))
            chooser = next(widget for widget in popup.walk() if isinstance(widget, FileChooserListView))
            address = next(widget for widget in popup.walk() if isinstance(widget, TextInput))
            address.text = str(source.parent)
            self.click('Go', popup)
            assert Path(chooser.path) == source.parent
            self.picker_popup, self.chooser, self.source = popup, chooser, source
            Clock.schedule_once(self.check_picker, .5)
        except Exception as exc:
            self.failure = exc
            self.stop()

    def check_picker(self, dt):
        try:
            assert str(self.source) in self.chooser.files, self.chooser.files
            assert any(widget.text == 'Folders / drives' for widget in self.picker_popup.walk()
                       if isinstance(widget, Spinner))
            filters = next(widget for widget in self.picker_popup.walk()
                           if isinstance(widget, Spinner) and widget.text == 'Images')
            self.test_image_filter = self.chooser.filters[0]
            for name in ('PHOTO.JPG', 'photo.jpeg', 'photo.PNG', 'photo.webp', 'scan.TIFF', 'scan.bmp'):
                assert self.test_image_filter('', name), name
            assert not self.test_image_filter('', 'notes.txt')
            filters.text = 'All files'
            assert self.chooser.filters == []
            self.chooser.selection = [str(self.source)]
            self.click('Use image', self.picker_popup)
            Clock.schedule_interval(self.finish_checks, .2)
        except Exception as exc:
            self.failure = exc
            self.stop()

    def finish_checks(self, dt):
        self.ticks += 1
        if not self.image_path and self.ticks < 50:
            return True
        try:
            assert self.image_path, self.status
            self.ocr_patch = patch('receiptwise.scanner.read_receipt_text', return_value='Merchant: Test Shop\nDate: 2026-06-12\nTOTAL 245.50')
            self.ocr_patch.start()
            self.click("Scan Receipt")
            self.ticks = 0
            Clock.schedule_interval(self.finish_scan, .2)
        except Exception as exc:
            self.failure = exc
            self.stop()
        return False

    def finish_scan(self, dt):
        self.ticks += 1
        if self.scanning and self.ticks < 50:
            return True
        self.ocr_patch.stop()
        try:
            assert not self.scanning and not self.status_error, self.status
            assert self.root.ids.merchant.text == "Test Shop"
            assert self.root.ids.date.text == "2026-06-12"
            assert self.root.ids.total.text == "245.50"
            assert not self.review_notes
            self.root.ids.date.text = "2026-02-30"
            self.click("Save Receipt")
            assert self.status_error and not self.saved
            self.root.ids.date.text = "2026-10-09"
            self.root.ids.total.text = "100.25"
            self.click("Save Receipt")
            assert self.saved and not self.status_error
            assert "PHP 100.25" in self.history_text
            self.save_receipt()
            assert len(ReceiptStore(self.store.path).recent()) == 1
            # Exercise background OCR with the real UI and a controlled backend.
            self.saved = False
            self.ocr_patch = patch("receiptwise.scanner.read_receipt_text", side_effect=RuntimeError("Missing model"))
            self.ocr_patch.start()
            self.click("Scan Receipt")
            self.ticks = 0
            Clock.schedule_interval(self.check_ocr_error, .2)
        except Exception as exc:
            self.failure = exc
            self.stop()
        return False

    def check_ocr_error(self, dt):
        self.ticks += 1
        if self.scanning and self.ticks < 50:
            return True
        self.ocr_patch.stop()
        try:
            assert not self.scanning and self.status_error
            assert self.status == "Missing model"
            assert self.root.ids.total.text == "100.25"
            self.ocr_patch = patch("receiptwise.scanner.read_receipt_text", return_value="REAL SHOP\nDate: 2026-02-30\nTOTAL 42.00")
            self.ocr_patch.start()
            self.click("Scan Receipt")
            self.ticks = 0
            Clock.schedule_interval(self.check_ocr_success, .2)
        except Exception as exc:
            self.failure = exc
            self.stop()
        return False

    def check_ocr_success(self, dt):
        self.ticks += 1
        if self.scanning and self.ticks < 50:
            return True
        self.ocr_patch.stop()
        try:
            assert not self.scanning and not self.status_error
            assert self.raw_text == "REAL SHOP\nDate: 2026-02-30\nTOTAL 42.00"
            assert self.root.ids.merchant.text == 'REAL SHOP'
            assert self.root.ids.date.text == ''
            assert self.root.ids.total.text == '42.00'
            assert 'Review date:' in self.review_notes
            self.click('Save Receipt')
            assert self.status_error and not self.saved
            self.ocr_patch = patch('receiptwise.scanner.read_receipt_text', return_value='')
            self.ocr_patch.start()
            self.click('Scan Receipt')
            self.ticks = 0
            Clock.schedule_interval(self.check_empty_scan, .2)
        except Exception as exc:
            self.failure = exc
            self.stop()
        return False

    def check_empty_scan(self, dt):
        self.ticks += 1
        if self.scanning and self.ticks < 50:
            return True
        self.ocr_patch.stop()
        try:
            assert not self.scanning and not self.status_error, self.status
            assert all(not self.root.ids[name].text for name in ('merchant', 'date', 'total'))
            assert 'Review amount:' in self.review_notes
            assert 'Review date:' in self.review_notes
            # Keep the saved photo retained when resetting this test draft.
            self.saved = True
            self.click("New Receipt")
            assert not self.image_path and not self.root.ids.total.text
            assert not self.review_notes and not self.raw_text
            assert "PHP 100.25" in self.history_text
            Window.size = (320, 640)
            assert not self.root.ids.merchant.disabled
            Clock.schedule_once(self.capture, .4)
        except Exception as exc:
            self.failure = exc
            self.stop()
        return False

    def capture(self, dt):
        try:
            output = Path(".test-data")
            output.mkdir(exist_ok=True)
            self.root.export_to_png(str(output / "mobile-preview.png"))
            scroll = next(widget for widget in self.root.walk() if isinstance(widget, ScrollView))
            scroll.scroll_y = 0
            Clock.schedule_once(self.capture_form, .3)
            print("PASS: image picker, OCR/parser scan, validation, save, duplicate protection, scan errors, invalid/missing fields, review notes, reset, 320px layout")
        except Exception as exc:
            self.failure = exc
            self.stop()

    def capture_form(self, dt):
        try:
            self.root.export_to_png(str(Path(".test-data") / "form-preview.png"))
        except Exception as exc:
            self.failure = exc
        self.stop()


if __name__ == "__main__":
    try:
        app = SmokeApp()
        app.run()
        if app.failure:
            raise app.failure
    finally:
        test_directory.cleanup()
