"""Conservative extraction from plain OCR text; no OCR/network dependencies.

``extract_receipt(text)`` returns merchant (str | None), date (ISO str | None),
amount (float | None, pesos), and notes (list[str]). Any nonempty notes should
send the receipt for human review. Numeric dates are not assumed to be MDY:
03/04/2026 is ambiguous unless ``date_order="MDY"`` or ``"DMY"`` is supplied.
No missing values, OCR digit substitutions, or item sums are invented.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict


class Receipt(TypedDict):
    merchant: str | None
    date: str | None
    amount: float | None
    notes: list[str]


_MONTHS = {name: i for i, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
)}
_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE = re.compile(
    rf"(?<!\w)(?:\d{{4}}[-/.]\d{{1,2}}[-/.]\d{{1,2}}|"
    rf"\d{{1,2}}[-/.]\d{{1,2}}[-/.](?:\d{{4}}|\d{{2}})|"
    rf"{_MONTH}[ .-]+\d{{1,2}}(?:,?\s+|[.-])\d{{4}}|"
    rf"\d{{1,2}}[ .-]+{_MONTH}(?:,?\s+|[.-])\d{{4}})(?!\w)", re.I
)
_ADMIN_DATE = re.compile(r"\b(?:valid|expiry|expires|expiration|issued|issuance|accreditation|permit|ATP|PTU|printed|printing)\b", re.I)
_TRANSACTION_DATE = re.compile(r"\b(?:(?:transaction|trans\.?|purchase|sale|invoice|receipt)\s+date|date\s+of\s+(?:sale|purchase))\b", re.I)
_TOTAL = re.compile(
    r"^(?P<label>grand\s+total|total\s+(?:amount|amt\.?)\s+due|total\s+due|amount\s+due|"
    r"balance\s+due|total\s+amount|net\s+total|total\s+sales|total)\b"
    r"\s*[:=]?\s*(?P<value>.*)$", re.I
)
_CURRENCY = r"(?:PHP|PhP|₱|P|PESO[S]?)"
_MONEY = re.compile(
    rf"(?:{_CURRENCY}\s*)?(?P<amount>(?:\d{{1,3}}(?:,\d{{3}})+|\d+)(?:\.\d{{2}})?)(?:\s*{_CURRENCY})?", re.I
)
_HEADER_NOISE = re.compile(
    r"\b(?:receipt|invoice|TIN|VAT|NON-VAT|BIR|registered|reg|address|street|st|road|rd|"
    r"avenue|ave|barangay|brgy|city|province|telephone|tel|phone|mobile|cashier|"
    r"terminal|date|time|customer|sold\s+to|bill\s+to|total|subtotal|cash|change|"
    r"permit|ATP|PTU|accreditation|serial|machine|welcome|thank|www|com|"
    r"branch|floor|highway|philippines)\b", re.I
)


def _parse_date(raw: str, order: str | None) -> date:
    parts = re.split(r"[\s,./-]+", raw.strip())
    if parts[0].isalpha():
        month, day, year = _MONTHS[parts[0][:3].lower()], int(parts[1]), int(parts[2])
    elif parts[1].isalpha():
        day, month, year = int(parts[0]), _MONTHS[parts[1][:3].lower()], int(parts[2])
    elif len(parts[0]) == 4:
        year, month, day = map(int, parts)
    else:
        if len(parts[2]) != 4:
            raise ValueError("two-digit year")
        first, second, year = map(int, parts)
        if order == "MDY":
            month, day = first, second
        elif order == "DMY":
            day, month = first, second
        elif first > 12:
            day, month = first, second
        elif second > 12 or first == second:
            month, day = first, second
        else:
            raise ValueError("ambiguous day/month order")
    return date(year, month, day)


def _extract_date(lines: list[str], order: str | None, today: date, notes: list[str]) -> str | None:
    candidates: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if _ADMIN_DATE.search(line):
            continue
        if index and _ADMIN_DATE.search(lines[index - 1]) and re.fullmatch(r"[\w\s]+:\s*", lines[index - 1]):
            continue
        rank = 1 if _TRANSACTION_DATE.search(line) or re.match(r"^date\b", line, re.I) else 0
        matches = list(_DATE.finditer(line))
        if rank and not matches:
            # OCR can put a label and its value on separate lines.
            if re.fullmatch(r"(?:(?:transaction|trans\.?|purchase|sale|invoice|receipt) )?date\s*:?", line, re.I) and index + 1 < len(lines):
                matches = list(_DATE.finditer(lines[index + 1]))
            if not matches:
                candidates.append((rank, "unreadable date"))
        candidates.extend((rank, match.group()) for match in matches)
    if not candidates:
        notes.append("Review date: no transaction date found.")
        return None
    best = max(rank for rank, _ in candidates)
    values = set()
    for rank, raw in candidates:
        if rank != best:
            continue
        try:
            parsed = _parse_date(raw, order)
            if parsed > today:
                raise ValueError("future date")
            values.add(parsed.isoformat())
        except (ValueError, KeyError, IndexError) as error:
            notes.append(f"Review date: {raw!r} is invalid or ambiguous ({error}).")
            return None
    if len(values) != 1:
        notes.append("Review date: conflicting transaction dates.")
        return None
    return values.pop()


def _extract_amount(lines: list[str], notes: list[str]) -> float | None:
    candidates: list[tuple[int, Decimal | None]] = []
    for index, line in enumerate(lines):
        match = _TOTAL.match(line)
        if not match:
            continue
        label = match['label'].lower()
        if label == 'total' and re.match(r"^(?:items?|qty|quantity|discounts?|VAT|tax|savings)\b", match['value'], re.I):
            continue
        rank = 2 if 'due' in label or label.startswith('grand') else 1
        value = match['value']
        if not value and index + 1 < len(lines):
            value = lines[index + 1]
        money = _MONEY.fullmatch(value.strip())
        candidates.append((rank, Decimal(money['amount'].replace(',', '')) if money else None))
    if not candidates:
        notes.append("Review amount: no explicitly labeled total found.")
        return None
    best = max(rank for rank, _ in candidates)
    values = {amount for rank, amount in candidates if rank == best}
    if None in values:
        notes.append("Review amount: total is missing or unreadable.")
        return None
    if len(values) != 1:
        notes.append("Review amount: conflicting totals.")
        return None
    return float(values.pop())


def _extract_merchant(lines: list[str], notes: list[str]) -> str | None:
    explicit_names = {
        match[1].strip() for line in lines[:10]
        if (match := re.match(r"^(?:merchant|store|business\s+name)\s*:\s*(.+)$", line, re.I))
        and re.search(r"[a-z]", match[1], re.I)
    }
    if len(explicit_names) > 1:
        notes.append("Review merchant: conflicting business names.")
        return None
    if explicit_names:
        return explicit_names.pop()
    for line in lines[:10]:
        # Stop at transaction content so an item/customer cannot become merchant.
        if (_TOTAL.match(line) or re.match(r"^(?:date|cashier|customer|sold\s+to|qty|item|description|take\s+away|take[ -]out)\b", line, re.I)
                or re.match(r"^\d+(?:\.\d+)?\s+[A-Za-z]", line) or _DATE.search(line)):
            break
        if (_HEADER_NOISE.search(line) or re.search(r"\d{3,}|\d+\.\d{2}|[@:/]", line)
                or not re.search(r"[a-z]{2}", line, re.I)):
            continue
        notes.append("Review merchant: inferred from receipt header; confirm the business name.")
        return line
    notes.append("Review merchant: no clear business name found.")
    return None


def extract_receipt(
    text: str, *, date_order: Literal["MDY", "DMY"] | None = None,
    reference_date: date | None = None,
) -> Receipt:
    """Extract a receipt; leave missing/unsafe fields as None with review notes.

    date_order must come from a known receipt format, not a guess. reference_date
    supplies the local processing date for future-date validation and stable tests.
    Header-based merchant selection is heuristic and always flagged for review.
    """
    if not isinstance(text, str):
        raise TypeError("text must be an OCR string")
    if date_order not in (None, "MDY", "DMY"):
        raise ValueError("date_order must be MDY, DMY, or None")
    lines = [' '.join(line.split()) for line in text.splitlines() if line.strip()]
    notes: list[str] = []
    return {
        "merchant": _extract_merchant(lines, notes),
        "date": _extract_date(lines, date_order, reference_date or date.today(), notes),
        "amount": _extract_amount(lines, notes),
        "notes": notes,
    }


# Readable alternative for callers referring to this component as the parser.
parse_receipt = extract_receipt


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description='Parse UTF-8 receipt text files (not images).')
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--date-order', choices=['MDY', 'DMY'])
    args = parser.parse_args()
    for path in args.files:
        print(json.dumps({'file': str(path), **extract_receipt(
            path.read_text(encoding='utf-8-sig'), date_order=args.date_order,
        )}, indent=2, ensure_ascii=True))
