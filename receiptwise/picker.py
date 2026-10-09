"""Android system image picker with a desktop file chooser fallback."""
from pathlib import Path
from threading import Thread

from kivy.clock import Clock
from kivy.utils import platform

from receiptwise.images import MAX_BYTES, import_image


class ImagePicker:
    REQUEST_CODE = 8123

    def __init__(self, folder, on_selected, on_error):
        self.folder = Path(folder)
        self.on_selected = on_selected
        self.on_error = on_error
        self.busy = False
        if platform == "android":
            from android import activity
            activity.bind(on_activity_result=self._activity_result)

    def open(self):
        if self.busy:
            return
        if platform == "android":
            from android.runnable import run_on_ui_thread
            from jnius import autoclass

            @run_on_ui_thread
            def launch():
                try:
                    intent_class = autoclass("android.content.Intent")
                    intent = intent_class(intent_class.ACTION_OPEN_DOCUMENT)
                    intent.addCategory(intent_class.CATEGORY_OPENABLE)
                    intent.setType("image/*")
                    autoclass("org.kivy.android.PythonActivity").mActivity.startActivityForResult(
                        intent, self.REQUEST_CODE)
                except Exception:
                    Clock.schedule_once(lambda dt: self._finish(None, "Unable to open the image picker."))
            self.busy = True
            launch()
        else:
            self._desktop()

    def _desktop(self):
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from kivy.metrics import dp

        chooser = FileChooserListView(path=str(Path.home()), filters=[
            "*.[pP][nN][gG]", "*.[jJ][pP][gG]", "*.[jJ][pP][eE][gG]", "*.[wW][eE][bB][pP]"])
        body = BoxLayout(orientation="vertical", spacing=dp(8))
        body.add_widget(chooser)
        actions = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        cancel, select = Button(text="Cancel"), Button(text="Use image")
        actions.add_widget(cancel)
        actions.add_widget(select)
        body.add_widget(actions)
        popup = Popup(title="Select a receipt image", content=body, size_hint=(.95, .9))
        cancel.bind(on_release=lambda *_: popup.dismiss())

        def choose(*_):
            if chooser.selection:
                popup.dismiss()
                self.busy = True
                self._run_import(chooser.selection[0])
        select.bind(on_release=choose)
        popup.open()

    def _activity_result(self, request_code, result_code, intent):
        if request_code != self.REQUEST_CODE:
            return
        if result_code != -1 or intent is None:
            Clock.schedule_once(lambda dt: self._finish(None, None))
            return
        uri = intent.getData()
        self._run_import(uri, android_uri=True)

    def _run_import(self, source, android_uri=False):
        def worker():
            temporary = None
            result, error = None, None
            try:
                if android_uri:
                    # content:// URIs are streams, never ordinary filesystem paths.
                    from jnius import autoclass
                    self.folder.mkdir(parents=True, exist_ok=True)
                    temporary = self.folder / "picker-import.tmp"
                    activity = autoclass("org.kivy.android.PythonActivity").mActivity
                    stream = activity.getContentResolver().openInputStream(source)
                    if stream is None:
                        raise ValueError("The selected image is unavailable.")
                    try:
                        buffer = bytearray(65536)
                        total = 0
                        with temporary.open("wb") as output:
                            while True:
                                count = stream.read(buffer)
                                if count == -1:
                                    break
                                total += count
                                if total > MAX_BYTES:
                                    raise ValueError("Choose an image smaller than 20 MB.")
                                output.write(buffer[:count])
                    finally:
                        stream.close()
                    source_path = temporary
                else:
                    source_path = source
                result = import_image(source_path, self.folder)
            except Exception as exc:
                error = str(exc) if isinstance(exc, ValueError) else "Unable to import the image. Please try again."
            finally:
                if temporary:
                    temporary.unlink(missing_ok=True)
            Clock.schedule_once(lambda dt: self._finish(result, error))
        Thread(target=worker, daemon=True).start()

    def _finish(self, result, error):
        self.busy = False
        if error:
            self.on_error(error)
        elif result:
            self.on_selected(result)

    def close(self):
        if platform == "android":
            from android import activity
            activity.unbind(on_activity_result=self._activity_result)
