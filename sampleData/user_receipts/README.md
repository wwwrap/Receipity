# User receipt samples

Open `index.html` in a browser for photos, field boxes, and review explanations.
The original photos are copied unchanged into `images/`. `annotations.json`
links each image to its existing manual text fixture in `test/fixtures/receipts`.
Existing sampleData images/annotations are a separate dataset and are unchanged.

Annotations include merchant/date/amount values, visibility/review status,
evidence text, and approximate normalized field rectangles. A null value means
missing or insufficient evidence, not zero. The first photo's merchant rectangle
highlights website evidence, not a readable business heading.

The coffee total's label is partly covered. Its manual transcription completes
that label; the expected parser result applies to the transcription. Actual OCR
with `rand Total` must still leave the amount empty for review. No OCR evaluation
or full line-by-line annotation is claimed. Photos are originals and contain
personal details; selected text fixtures omit unrelated identifiers.

Run tests from the repository root:

```console
python -m unittest discover -s test -v
```

After editing annotations, regenerate the viewer:

```console
python sampleData/user_receipts/build_preview.py
```
