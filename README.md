# ReceiptWise — Kivy Android prototype

A native Python/Kivy interface for selecting receipt images, running local OCR,
correcting receipt details, and saving receipts locally. Launch **main.py at this
directory's root**, inside the `realitychck` project. `frontend/app.py` also
launches the same Kivy UI. The application does not use Gradio.

## Run on desktop

Use Python 3.10–3.12 (3.12 recommended):

```powershell
cd C:\Personal\College\ReceiptWise\realitychck
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-mobile.txt
.\.venv\Scripts\python.exe main.py
```

If the local environment is already installed, only the `cd` and final launch
command are needed. Both `requirements.txt` and `requirements-mobile.txt` install
the mobile prototype. Optional desktop OCR dependencies are separate.

On Linux/macOS, use `.venv/bin/python` in place of the Windows executable.
The desktop window starts at 390 × 780. Resize it to check the scrollable layout.
The desktop picker browses local files; Android uses its system image picker.

## Pulled repository integration

- `main.py`, `python frontend/app.py`, and `python -m frontend.app` open the same UI.
- `sampleData/images/` contains three usable receipt photos. The annotation JSON
  files are ground truth, not extracted merchant/date/total values.
- `backend.inference_engine.recognize_receipt` returns raw text only. On desktop,
  **Scan Receipt** runs this API and `extractor.parse_receipt`
  in a background worker. It fills supported fields, displays review notes,
  and preserves raw text for comparison. There is no sample-data fallback.
- To enable desktop OCR, run these commands in the virtual environment:

  ```powershell
  .\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
  .\.venv\Scripts\python.exe pre_download_models.py
  ```

  Initial model setup requires internet. Actual scans use the offline backend.
  Missing packages/weights produce an error in the UI, not fake OCR results.
- The current Android APK excludes EasyOCR/PyTorch, models, sample data, and
  desktop utilities. Android supports image selection and manual receipt entry;
  tapping Scan Receipt explains that OCR is currently available on desktop.
- The UI continues using its validated `receiptwise/storage.py` SQLite store in
  app-private storage. `backend/database.py` and `data/reality_check.db` are the
  team's separate legacy database; those records are not automatically imported
  or double-written. The database demo uses temporary storage during testing.
- `test/test_pipeline.py` displays OCR text and parsed fields/notes for manual
  evaluation. It does not claim to measure extraction accuracy against the dataset.
- `requirements-dev.txt` adds optional dataset tools. `fetch_samples.py` saves
  in the repository's sample folder regardless of the launch directory.

## Use the prototype

1. Tap **Select Receipt Image** and select an image from the device's images or
   document provider. Canceling preserves the current receipt.
2. Tap **Scan Receipt** on desktop. It reads your selected photo and fills the
   supported fields. The examples are hints only; fields initially contain no text.
3. Edit the merchant, date, or total. Scanning is optional if entering manually.
4. Tap **Save Receipt**. A merchant, real ISO date (`YYYY-MM-DD`), positive amount
   with up to two decimal places, and selected image are required.
5. Check the recent receipts. Tap **New Receipt** to clear
   the form, or select another image to begin another receipt.

For desktop OCR, use **Scan Receipt** after model setup.
The parser fills only supported values. Read the notes in **Check receipt details**
and compare with the photo and raw OCR text. Missing fields stay blank; Save
Receipt requires you to correct them first. Parsed values are never saved automatically.

## Parser contract

```python
from extractor import parse_receipt

result = parse_receipt("Merchant: Jollibee\nDate: 2026-10-09\nTotal: PHP 245.50")
# {"merchant": "Jollibee", "date": "2026-10-09", "amount": "245.50", "notes": []}
```

`merchant`, `date`, and `amount` are strings or `None`; `notes` is a list of review
messages. `amount` maps to the UI's Total Amount field. Decimal strings preserve
centavos without float conversion. For image input, the backend also exposes
`backend.inference_engine.extract_receipt(image)` with the same four-key result.

- Explicit merchant labels are preferred; a single plausible header name is a
  suggestion with a verification note. Conflicting names remain `None`.
- Dates require a complete four-digit year and a real calendar date. ISO,
  English month names, and unambiguous numeric dates are supported. `09/10/2026`
  stays blank because day/month order is unknown. Invalid dates, conflicting
  transaction dates, and two-digit years require review. Expiry/printed dates are
  excluded. The parser never substitutes today's date or repairs OCR characters.
- Amounts require a labeled final total. Grand total/amount due take precedence
  over plain total, with a note when they differ. Conflicting final totals,
  unreadable/negative/zero values, unsupported currency/number formats, or missing
  totals remain `None`. Cash, change, tax, subtotal, and item sums are not used.
- Amount parsing expects PHP-style decimal points with optional thousands commas.
  This is a rule-based prototype, not a guarantee of extraction accuracy: a plausible
  but incorrectly recognized value still needs human comparison with the photo.

Run parser-only tests without Kivy, NumPy, or models:
`python -m unittest tests.test_extractor -v`.

Amounts use integer centavos to avoid floating-point rounding errors. Repeated
save taps on the same draft do not create another transaction. Deliberately
selecting the same photo again starts a new draft and can create another receipt.

SQLite and imported JPEG copies live in Kivy's `App.user_data_dir`. Android uses
app-private storage; no server or internet is needed at runtime. Images are capped
at 20 MB and normalized to at most 1600 × 1600 for the preview. Saved images and
receipt details survive restart; unsaved form fields are not restored after process
termination. Uninstalling or clearing app data removes stored receipts. For desktop
testing, `RECEIPTWISE_DATA_DIR` can point to an isolated data directory.

## Package an Android debug APK

Buildozer requires Linux or macOS. On Windows use **WSL2 with Ubuntu 24.04** and
build inside the Linux filesystem. The following is a debug/sideload workflow,
not a Play Store release configuration. Follow the current official
[Buildozer installation guide](https://buildozer.readthedocs.io/en/latest/installation/)
for platform prerequisites and toolchain changes.

In Ubuntu/WSL:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git zip unzip openjdk-17-jdk \
  autoconf automake libtool pkg-config zlib1g-dev libncurses-dev \
  libtinfo6 cmake libffi-dev libssl-dev autopoint gettext
mkdir -p ~/ReceiptWise/receiptwise
cp /mnt/c/Personal/College/ReceiptWise/realitychck/main.py ~/ReceiptWise/
cp /mnt/c/Personal/College/ReceiptWise/realitychck/extractor.py ~/ReceiptWise/
cp /mnt/c/Personal/College/ReceiptWise/realitychck/buildozer.spec ~/ReceiptWise/
cp /mnt/c/Personal/College/ReceiptWise/realitychck/receiptwise/*.py ~/ReceiptWise/receiptwise/
cp /mnt/c/Personal/College/ReceiptWise/realitychck/receiptwise/*.kv ~/ReceiptWise/receiptwise/
cd ~/ReceiptWise
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install buildozer setuptools 'cython==0.29.34'
buildozer -v android debug
```

The first build downloads the SDK/NDK and asks you to accept Android licenses.
If the current toolchain requires Rust, install it using the official Buildozer
prerequisite instructions. The spec targets API 35, minimum API 23, with ARM64
for phones and x86_64 for emulators. APKs are written to `bin/`.

Copy the APK to Windows when building under WSL, then use Windows Android SDK
platform-tools with a USB-debugging device or running Android Studio emulator:

```powershell
adb devices
adb install -r "C:\path\to\receiptwise-debug.apk"
adb shell am start -n org.receiptwise.receiptwise/org.kivy.android.PythonActivity
```

For native Linux with a connected device, `buildozer android deploy run logcat`
can install and launch it. The Android picker uses `ACTION_OPEN_DOCUMENT` and
copies the returned `content://` stream into private storage. It does not treat
content URIs as paths or require broad gallery/storage permission. See
[Android's Storage Access Framework](https://developer.android.com/training/data-storage/shared/documents-files).

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s test -v
.\.venv\Scripts\python.exe -m unittest test_db -v
.\.venv\Scripts\python.exe -m tests.smoke_ui
```

Unit tests cover validation, exact receipt amounts, duplicate-save handling,
SQLite persistence, repository sample imports, and the OCR adapter. The upstream
OCR tests require NumPy (`python -m pip install numpy`) and use fake models.
No test downloads weights or establishes real OCR accuracy. The final command opens a
Kivy window, exercises the desktop picker and button handlers, and saves a small
screen preview to `.test-data/mobile-preview.png`. It uses temporary test data.

Before considering the Android build device-verified, test on a phone/emulator:

- Pick a gallery image, cancel the picker, and select a replacement.
- Scan, edit all three fields, reject an impossible date/zero amount, then save.
- Confirm receipt totals, repeated-save protection, and New Receipt behavior.
- Restart and confirm recent receipts persist.
- Check keyboard visibility and scrolling on a small phone; test a large or
  unsupported image and opening an image from a cloud document provider.

## Code map

- `main.py`: packaging and desktop entry point.
- `receiptwise/app.py` / `interface.kv`: actions and touch-friendly vertical UI.
- `receiptwise/picker.py` / `images.py`: platform selection and private image import.
- `receiptwise/storage.py`: receipt validation, SQLite records, and currency formatting.
- `extractor.py`: dependency-free parsing into `{merchant, date, amount, notes}`.
- `receiptwise/scanner.py`: real scan/extraction and the offline OCR text adapter.
- `tests/real_ocr_smoke.py`: optional real image-to-text check using installed models;
  run `python -m tests.real_ocr_smoke`. It does not download models or mock OCR.
- `backend/inference_engine.py`: raw OCR and combined image extraction APIs.
