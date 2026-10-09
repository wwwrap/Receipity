# Receipt extraction

Requires Python 3.10 or newer, with no additional packages.

```python
from datetime import date
from backend.extractor import extract_receipt

receipt = extract_receipt(
    ocr_text,
    reference_date=date(2026, 10, 10),  # supply the local processing date
)
# {'merchant': str | None, 'date': 'YYYY-MM-DD' | None,
#  'amount': float | None, 'notes': list[str]}
needs_review = bool(receipt['notes'])
```

`parse_receipt` is an alias. Blank input returns three missing fields and review
notes. Non-string input raises `TypeError`. Amount is in pesos; zero is valid.

- Dates must be valid calendar dates and cannot exceed the reference date
  (defaults to the host's current date). Two-digit years and ambiguous numeric
  dates are left empty. Supply `date_order="MDY"` or `"DMY"` only for a known
  receipt format. Explicit transaction dates take precedence over unlabeled
  dates; recognized permit, printing, and expiry date lines are excluded.
- Explicit grand totals and amounts due take precedence over ordinary totals.
  Conflicting values at the selected priority, missing values, malformed money,
  negative totals, and uncertain OCR digits require review. Item prices,
  subtotals, VAT amounts, cash, and change are not used to calculate a total.
- Explicit merchant labels are preferred. Otherwise, the first plausible header
  is returned with a review note. Conflicting explicit names are left empty.
- Labels and values can be on separate consecutive nonblank lines. Multi-column
  OCR still needs upstream reading-order normalization.

Run from the repository root:

```console
python -m unittest discover -s test -v
```

Tests use synthetic Philippine-style receipt text plus manual transcriptions of
four user-provided photos in `test/fixtures/receipts`. These test parsing, not OCR
accuracy. Validate actual OCR output before treating extraction quality as
production-ready. Print a supplied sample's parsed result with:

```console
python -m backend.extractor test/fixtures/receipts/02_grocery.txt
```

The desktop UI now calls this function after local OCR through
`receiptwise.scanner.scan_receipt`. It fills the form, leaves None values blank,
and displays notes in the review section. Launch `python main.py`; scanning needs
the packages in `requirements-ocr.txt` and models from `pre_download_models.py`.
Android supports manual entry only. `python test/test_pipeline.py` runs real OCR
and extraction on all four user-supplied images for manual comparison.
