"""Conservative OCR text parsing. No model, network, UI, or database dependency.

parse_receipt(text) returns merchant/date/amount (strings or None) and notes
(list[str]). Dates use ISO YYYY-MM-DD; amounts use exact two-decimal strings.
None means manual review is required. Never substitute today's date or sum items.
"""
from datetime import date
from decimal import Decimal
import re

MONTHS = {name.lower(): index for index, names in enumerate([
    ("Jan", "January"), ("Feb", "February"), ("Mar", "March"),
    ("Apr", "April"), ("May",), ("Jun", "June"), ("Jul", "July"),
    ("Aug", "August"), ("Sep", "Sept", "September"), ("Oct", "October"),
    ("Nov", "November"), ("Dec", "December")], 1) for name in names}
MONTH = "(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")"
DATE_TOKEN = re.compile(
    rf"(?<!\w)(?:\d{{4}}[-/.]\d{{1,2}}[-/.]\d{{1,2}}|"
    rf"\d{{1,2}}[-/.]\d{{1,2}}[-/.]\d{{2,4}}|"
    rf"\d{{1,2}}[ -]{MONTH}[ ,.-]+\d{{4}}|"
    rf"{MONTH}[ .-]+\d{{1,2}}[ ,.-]+\d{{4}})(?!\w)", re.I)
DATE_LABEL = re.compile(r"^(?:(?:transaction|purchase|receipt|sale|issued)\s+)?date\b", re.I)
NON_TRANSACTION_DATE = re.compile(r"\b(?:exp(?:iry|iration)?|expires|valid|birth|printed|print|due)\b", re.I)
MERCHANT_LABEL = re.compile(r"^(?:merchant(?: name)?|store(?: name)?|seller)\s*[:=]\s*(.*)$", re.I)
TOTAL_LABEL = re.compile(
    r"^(grand\s+total|amount\s+due|total\s+due|balance\s+due|net\s+total|total(?:\s+amount)?)"
    r"\b\s*[:=]?\s*(.*)$", re.I)
MONEY = re.compile(r"(?:(?:PHP|P|₱)\s*)?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?(?:\s*PHP)?", re.I)
NON_MERCHANT = re.compile(
    r"\b(?:receipt|invoice|welcome|thank|address|street|road|avenue|branch|"
    r"tel|phone|tin|vat|cashier|terminal|register|date|time|total|subtotal|"
    r"cash|change|amount|payment|qty|quantity|item|tax|www|com)\b", re.I)


def _choose(values, field, notes):
    unique = list(dict.fromkeys(values))
    if len(unique) == 1:
        return unique[0]
    notes.append(f"{field}: " + ("conflicting candidates; review " + ", ".join(unique)
                                 if unique else "not found; enter manually."))
    return None


def _merchant(lines, notes):
    labeled = []
    has_label = False
    for index, line in enumerate(lines):
        match = MERCHANT_LABEL.match(line)
        if match:
            has_label = True
            value = match[1].strip() or (lines[index + 1] if index + 1 < len(lines) else "")
            if _merchant_candidate(value):
                labeled.append(value)
            else:
                notes.append("Merchant: labeled name is unreadable; enter manually.")
                return None
    if has_label:
        return _choose(labeled, "Merchant", notes)
    candidates = []
    # Only inspect the header, stopping at dates, addresses, or transaction rows.
    for line in lines[:5]:
        if (DATE_TOKEN.search(line) or re.search(r"[:=@]|\d+\.\d{2}|^\d+\s|^\d+$", line)):
            break
        if NON_MERCHANT.search(line):
            if re.fullmatch(r"(?:official |sales )?(?:receipt|invoice)|welcome", line, re.I):
                continue
            break
        if _merchant_candidate(line):
            candidates.append(line)
    merchant = _choose(candidates, "Merchant", notes)
    if merchant:
        notes.append("Merchant: selected from the receipt header; verify the name.")
    return merchant


def _merchant_candidate(value):
    return bool(2 <= len(value) <= 120 and re.search(r"[^\W\d_]", value, re.UNICODE)
                and not NON_MERCHANT.search(value) and not DATE_TOKEN.search(value)
                and not re.search(r"\d+\.\d{2}\b|https?://|@", value))


def _date_value(token):
    parts = re.findall(r"[A-Za-z]+|\d+", token)
    if any(part.isalpha() for part in parts):
        if parts[0].isalpha():
            month, day, year = MONTHS[parts[0].lower()], int(parts[1]), int(parts[2])
        else:
            day, month, year = int(parts[0]), MONTHS[parts[1].lower()], int(parts[2])
        return date(year, month, day).isoformat()
    first, second, third = parts
    if len(first) == 4:
        return date(int(first), int(second), int(third)).isoformat()
    if len(third) != 4:
        raise ValueError("two-digit year")
    a, b, year = int(first), int(second), int(third)
    if a != b and 1 <= a <= 12 and 1 <= b <= 12:
        raise ValueError("ambiguous day/month order")
    day, month = (a, b) if a > 12 else (b, a)
    return date(year, month, day).isoformat()


def _transaction_date(lines, notes):
    labeled, other = [], []
    ignored = set()
    for index, line in enumerate(lines):
        if index in ignored:
            continue
        if NON_TRANSACTION_DATE.search(line):
            if (not DATE_TOKEN.search(line) and index + 1 < len(lines)
                    and DATE_TOKEN.fullmatch(lines[index + 1])):
                ignored.add(index + 1)
            continue
        tokens = DATE_TOKEN.findall(line)
        if DATE_LABEL.match(line):
            if not tokens and index + 1 < len(lines):
                tokens = DATE_TOKEN.findall(lines[index + 1])
            labeled.extend(tokens or [""])
        else:
            other.extend(tokens)
    values = []
    for token in labeled or other:
        try:
            values.append(_date_value(token))
        except (ValueError, KeyError):
            notes.append(f"Date: invalid, incomplete, or ambiguous ({token or 'unreadable'}); enter manually.")
            return None
    return _choose(values, "Date", notes)


def _amount(lines, notes):
    candidates = []
    for index, line in enumerate(lines):
        match = TOTAL_LABEL.match(line)
        if not match:
            continue
        label, value = match.groups()
        # Item counts and tax breakdowns are not final totals.
        if re.match(r"(?:items?|qty|quantity|tax|savings|discount|vat)\b", value, re.I):
            continue
        rank = 1 if label.lower() in ("total", "total amount") else 2
        if not value and index + 1 < len(lines):
            value = lines[index + 1]
        match_money = MONEY.fullmatch(value.strip())
        amount = None
        if match_money:
            number = Decimal(match_money[1].replace(",", "") + "." + (match_money[2] or "0"))
            if 0 < number <= Decimal("9999999.99"):
                amount = f"{number:.2f}"
        candidates.append((rank, amount, value))
    if not candidates:
        notes.append("Amount: no labeled final total found; enter manually (items are not summed).")
        return None
    highest = max(rank for rank, _, _ in candidates)
    chosen = [amount for rank, amount, _ in candidates if rank == highest]
    if None in chosen:
        notes.append("Amount: labeled total is unreadable, non-positive, unsupported currency/format, or too large; enter manually.")
        return None
    result = _choose(chosen, "Amount", notes)
    if result and any(amount != result for rank, amount, _ in candidates if rank < highest):
        notes.append("Amount: selected the final amount due/grand total over a different total; verify it.")
    return result


def parse_receipt(text):
    """Return {merchant, date, amount, notes}; unknown/ambiguous fields are None.

    Recognizes ISO and unambiguous numeric or English month-name dates. Amounts
    use PHP-style decimal points and optional thousands commas. Other formats
    require review. No OCR character substitutions or locale guesses are made.
    """
    if not isinstance(text, str):
        raise TypeError("OCR text must be a string.")
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    notes = []
    return {"merchant": _merchant(lines, notes),
            "date": _transaction_date(lines, notes),
            "amount": _amount(lines, notes), "notes": notes}
