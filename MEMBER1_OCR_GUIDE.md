# Receipity — Member 1 (OCR) handoff

This part is already coded. The goal is to **run and verify** it on the team's
Windows demonstration laptop. It is not necessary to train a model.

## What changed

- `backend/model_loader.py`: downloads model weights for initial setup and
  loads them with `download_enabled=False` for offline inference.
- `backend/media_processor.py`: converts image files, Pillow images, byte
  buffers, and RGB NumPy arrays into an EasyOCR-compatible RGB array.
- `backend/inference_engine.py`: exposes `recognize_receipt(image) -> str`.
- `pre_download_models.py`: one-time setup command.
- `ocr_demo.py`: an independent receipt scanning demo.
- `test/test_ocr.py`: fast logic tests without downloading model weights.
- `requirements-ocr.txt`: installs EasyOCR and NumPy for desktop OCR.
- `.gitignore`: ignores local model weights (`models/`).

No frontend, annotation, sample image, or other team-owned file was replaced.

## 1. Open the project

In VS Code, open the folder containing `requirements.txt` and `backend/`.
Then open **Terminal → New Terminal**.

## 2. Set up Python (Windows / PowerShell)

Use Python 3.11 if available. Run these commands one line at a time:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
```

If `py -3.11` fails, install Python 3.11 (64-bit). The model may take time to
initialize on CPU, particularly on the first call.

## 3. Test the Python code without AI weights

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s test -p "test_ocr.py" -v
```

This checks image handling, the OCR output format, and the offline download
configuration using fake models. It **does not** establish real-world OCR
accuracy.

## 4. Download the pretrained AI model ONCE (internet required)

```powershell
.\.venv\Scripts\python.exe pre_download_models.py
```

The pretrained English EasyOCR weights will be stored in `models/easyocr/`.
Keep that folder local. It is excluded from Git.

## 5. Read the included sample receipt

```powershell
.\.venv\Scripts\python.exe ocr_demo.py
```

Or scan another file:

```powershell
.\.venv\Scripts\python.exe ocr_demo.py "C:\Users\YourName\Pictures\my_receipt.jpg"
```

The CORD sample receipts included in the repository are Indonesian and may
be especially challenging for an English-only model. **Do not claim every
line or total is guaranteed correct.** Verify using actual Philippine receipts
as well. Keep personally sensitive receipt photos outside the repository.

## 6. Prove local AI works with Wi-Fi off

1. Finish the initial download in Step 4.
2. Run the command in Step 5 once while online.
3. Disconnect Wi-Fi and any other network.
4. Re-run the same command. The text should still appear.
5. Screenshot the result for the hackathon demo.

If weights have not been downloaded, offline inference raises a helpful error
instead of reaching out to cloud services.

## 7. How teammates call Member 1's code

Run from the **repository root** so Python can import `backend`:

```python
from backend.inference_engine import recognize_receipt

text = recognize_receipt("sampleData/images/receipt_1.png")
print(text)
```

`recognize_receipt` returns a **plain string**, with recognized text separated
by newlines, not an extracted total or date. Member 2 should parse its output;
The Kivy desktop UI passes its imported receipt image to the same function. The model
is cached in memory after the first use for faster subsequent scans.

## 8. Upload just your work to GitHub

Use a branch such as `feature/ocr` and include only:

- `backend/model_loader.py`
- `backend/media_processor.py`
- `backend/inference_engine.py`
- `pre_download_models.py`
- `ocr_demo.py`
- `test/test_ocr.py`
- `MEMBER1_OCR_GUIDE.md`
- `.gitignore` (one additional ignore rule)
- `requirements.txt` (one additional dependency)

**Do not** upload `.venv/`, `models/`, `*.pth`, or personal receipt photos.
Create a pull request into `main`, and have your teammates review the code.

## Common errors

- **`No module named easyocr`**: install requirements inside your venv.
- **`Local EasyOCR weights were not found`**: run `pre_download_models.py`
  while online, then try again.
- **OCR returns poor text**: photograph the receipt flat, well lit, and in
  focus; ensure the printed total is legible.
- **`No module named backend`**: run the command from the repository root,
  not from inside the `backend` folder.
