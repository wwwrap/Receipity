"""Member 1's OCR public API, ready for use by Member 2 and the frontend."""

from backend.media_processor import prepare_image
from backend.model_loader import get_reader
from statistics import median


def receipt_lines(detections):
    """Reassemble EasyOCR boxes into rows, ordered top-to-bottom/left-to-right.

    Match by vertical centers relative to text height, not a fixed pixel gap.
    Keep separate rows separate; never repair or replace recognized digits.
    """
    boxes = []
    for polygon, text, confidence in detections:
        if not isinstance(text, str) or not text.strip():
            continue
        xs, ys = zip(*polygon)
        boxes.append((min(xs), (min(ys) + max(ys)) / 2,
                      max(1, max(ys) - min(ys)), text.strip()))
    rows = []
    for box in sorted(boxes, key=lambda box: (box[1], box[0])):
        matching = [row for row in rows
                    if abs(box[1] - median(item[1] for item in row))
                    <= .6 * min(box[2], median(item[2] for item in row))]
        if matching:
            row = min(matching, key=lambda row: abs(box[1] - median(item[1] for item in row)))
            row.append(box)
        else:
            rows.append([box])
    return [' '.join(box[3] for box in sorted(row, key=lambda box: box[0]))
            for row in sorted(rows, key=lambda row: median(box[1] for box in row))]


def recognize_receipt(image):
    """Read a receipt image locally and return the recognized text as a string.

    `image` can be a file path, Pillow Image, image bytes, or NumPy RGB array.
    Newlines separate reconstructed text rows. Parsing merchant/date/total
    belongs to Member 2, not this function.

    Example:
        text = recognize_receipt("sampleData/images/receipt_1.png")
    """
    pixels = prepare_image(image)
    reader = get_reader()
    detections = reader.readtext(pixels, detail=1, paragraph=False)
    return "\n".join(receipt_lines(detections))
