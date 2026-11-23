"""CSV ledger parsing with line-numbered validation."""

import csv
import datetime
import re
from decimal import Decimal

from .model import LedgerError, Transaction

COLUMNS = ("id", "date", "amount", "currency", "category", "memo")
CURRENCIES = frozenset({"ILS", "USD", "EUR"})

_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_AMOUNT_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.([0-9]+))?|\.([0-9]+))")


def parse_csv(path):
    """Parse the ledger file at ``path`` (UTF-8, optional BOM)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return parse_lines(f)


def parse_lines(lines):
    """Parse ledger text given as an iterable of lines into transactions."""
    reader = csv.reader(_strip_bom(lines))
    records = _records(reader)

    header = None
    for line, row in records:
        if _is_blank(row):
            continue
        header = (line, [cell.strip() for cell in row])
        break
    if header is None:
        raise LedgerError(1, "missing header")
    header_line, names = header
    index = _column_index(header_line, names)
    width = len(names)

    transactions = []
    seen = {}
    for line, row in records:
        if _is_blank(row):
            continue
        txn = _transaction(line, row, width, index, seen)
        seen[txn.id] = line
        transactions.append(txn)
    return transactions


def _strip_bom(lines):
    first = True
    for text in lines:
        if first:
            first = False
            if text.startswith("\ufeff"):
                text = text[1:]
        yield text


def _records(reader):
    """Yield (start line, row), turning csv.Error into LedgerError."""
    while True:
        start = reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            return
        except csv.Error as e:
            raise LedgerError(start, f"malformed CSV: {e}") from e
        yield start, row


def _is_blank(row):
    return all(not cell.strip() for cell in row)


def _column_index(line, names):
    missing = [c for c in COLUMNS if c not in names]
    if missing:
        raise LedgerError(line, f"missing column(s): {', '.join(missing)}")
    for c in COLUMNS:
        if names.count(c) > 1:
            raise LedgerError(line, f"duplicate column '{c}'")
    return {c: names.index(c) for c in COLUMNS}


def _transaction(line, row, width, index, seen):
    if len(row) != width:
        raise LedgerError(line, f"expected {width} fields, got {len(row)}")
    f = {c: row[i].strip() for c, i in index.items()}

    if not f["id"]:
        raise LedgerError(line, "empty id")
    if f["id"] in seen:
        raise LedgerError(
            line, f"duplicate id '{f['id']}' (first seen on line {seen[f['id']]})"
        )

    text = f["date"]
    if not _DATE_RE.fullmatch(text):
        raise LedgerError(line, f"date '{text}' is not YYYY-MM-DD")
    try:
        date = datetime.date(int(text[0:4]), int(text[5:7]), int(text[8:10]))
    except ValueError:
        raise LedgerError(line, f"date '{text}' is not a calendar date") from None

    text = f["amount"]
    m = _AMOUNT_RE.fullmatch(text)
    if not m:
        raise LedgerError(line, f"amount '{text}' is not a number")
    fraction = m.group(1) or m.group(2) or ""
    if len(fraction) > 2:
        raise LedgerError(line, f"amount '{text}' has more than 2 decimal places")
    amount = Decimal(text)
    if amount == 0:
        raise LedgerError(line, "amount must not be zero")

    if f["currency"] not in CURRENCIES:
        raise LedgerError(line, f"unknown currency '{f['currency']}'")
    if not f["category"]:
        raise LedgerError(line, "empty category")

    return Transaction(
        id=f["id"],
        date=date,
        amount=amount,
        currency=f["currency"],
        category=f["category"],
        memo=f["memo"],
    )
