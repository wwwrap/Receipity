# User-provided receipt photo cases

These four UTF-8 files are **manual transcriptions of selected visible text**
from the four photos supplied in chat, in the same order. They are not OCR output
and do not measure OCR accuracy. Names/identifiers unrelated to extraction were
redacted or omitted, and some item lines were omitted. Columns are joined into
reading order. Partially obscured but human-readable labels in photo 4 are
transcribed as complete labels; actual OCR may fail to recover them.

| Photo / file | Expected merchant | Expected date | Amount (PHP) |
| --- | --- | --- | ---: |
| 01_goldilocks.txt | Missing / review | 2025-06-16 | 810.00 |
| 02_grocery.txt | Missing / review | 2026-06-12 | 1696.35 |
| 03_north_park.txt | North Park Noodle House Inc. (confirm header) | Missing / review | 1540.00 |
| 04_coffee.txt | Missing / review | Missing / review | 460.43 |

Photo 1 has a Goldilocks website, but the merchant heading is clipped/faint.
The parser does not convert website domains or a mall branch into merchant
names. Photo 2's business header is outside the frame. Photo 4's product names
include PICKUP, which is insufficient to treat them as the merchant heading.
Photos 3 and 4 show no transaction date; none is supplied or inferred.

Photo 3 explicitly says it is not an official receipt. These tests extract text
fields only and do not establish a document's validity for reimbursement.

From the repository root, print one sample's result:

```console
python -m backend.extractor test/fixtures/receipts/02_grocery.txt
```

The command accepts multiple text file paths. Use the configured Python
executable if `python` is not installed on PATH.
