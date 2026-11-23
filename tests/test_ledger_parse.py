"""Unit tests for ledger parsing and row validation (SCRUM-118 t1)."""

import csv
import dataclasses
import datetime
import io
from decimal import Decimal
from pathlib import Path

import pytest

from ledger import LedgerError, Transaction, parse_csv, parse_lines

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ledger"
HEADER = "id,date,amount,currency,category,memo\n"
GOOD = "t1,2026-03-01,-10.00,ILS,food,lunch\n"


def parse_text(text):
    return parse_lines(io.StringIO(text))


def error_of(text):
    with pytest.raises(LedgerError) as info:
        parse_text(text)
    return info.value


def row(id="t1", date="2026-03-01", amount="-10.00", currency="ILS",
        category="food", memo="lunch"):
    return f"{id},{date},{amount},{currency},{category},{memo}\n"


# Scenario 1 -----------------------------------------------------------------

def test_sample_parses_nine_transactions_in_file_order():
    txns = parse_csv(FIXTURES / "sample.csv")
    assert [t.id for t in txns] == [f"t00{i}" for i in range(1, 10)]
    second = txns[1]
    assert second == Transaction(
        id="t002", date=datetime.date(2026, 3, 1), amount=Decimal("12000.00"),
        currency="ILS", category="salary", memo="March salary",
    )
    assert str(second.amount) == "12000.00"
    assert sum(1 for t in txns if (t.date.year, t.date.month) == (2026, 3)) == 7
    assert txns[0].date == datetime.date(2026, 2, 27)
    assert txns[-1].date == datetime.date(2026, 4, 1)
    assert any(t.memo == "" for t in txns)
    for t in txns:
        assert isinstance(t.id, str) and isinstance(t.date, datetime.date)
        assert isinstance(t.amount, Decimal)
        assert isinstance(t.currency, str) and isinstance(t.category, str)
        assert isinstance(t.memo, str)


def test_transaction_is_frozen():
    t = parse_text(HEADER + GOOD)[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.amount = Decimal("1")


# Scenario 2 -----------------------------------------------------------------

def test_columns_matched_by_name_fields_stripped_extra_ignored():
    text = ("memo, category ,currency,amount,date,id,extra\n"
            "  a note , food ,  USD , 12.50 , 2026-03-04 , x1 , junk\n")
    (t,) = parse_text(text)
    assert t == Transaction("x1", datetime.date(2026, 3, 4), Decimal("12.50"),
                            "USD", "food", "a note")


# Scenario 3 -----------------------------------------------------------------

def test_bom_blank_fixture_bytes():
    data = (FIXTURES / "bom_blank.csv").read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    assert b"\n\n" in data and b"\n   \n" in data


def test_bom_blank_lines_empty_and_quoted_memo():
    first, second = parse_csv(FIXTURES / "bom_blank.csv")
    assert first.id == "b1" and first.memo == ""
    assert second.id == "b2" and second.memo == "birthday, aunt"


def test_parse_lines_with_leading_bom_char_equals_parse_csv():
    path = FIXTURES / "bom_blank.csv"
    text = path.read_bytes().decode("utf-8")
    assert text.startswith("\ufeff")
    assert parse_lines(io.StringIO(text)) == parse_csv(path)


# Scenario 4 -----------------------------------------------------------------

def test_header_only_returns_empty_list():
    assert parse_text(HEADER) == []
    assert parse_text(HEADER.rstrip("\n")) == []


# Scenario 5 -----------------------------------------------------------------

def test_ledger_error_shape():
    e = LedgerError(7, "empty id")
    assert (e.line, e.reason) == (7, "empty id")
    assert str(e) == "line 7: empty id"


@pytest.mark.parametrize("bad_row, reason", [
    (row(date="2026-3-1"), "date '2026-3-1' is not YYYY-MM-DD"),
    (row(date="20260301"), "date '20260301' is not YYYY-MM-DD"),
    (row(date="2026-W01-1"), "date '2026-W01-1' is not YYYY-MM-DD"),
    (row(date="２０２６-03-01"), "date '２０２６-03-01' is not YYYY-MM-DD"),
    (row(date="2026-02-30"), "date '2026-02-30' is not a calendar date"),
    (row(date="2026-13-01"), "date '2026-13-01' is not a calendar date"),
    (row(amount="abc"), "amount 'abc' is not a number"),
    (row(amount="1e3"), "amount '1e3' is not a number"),
    (row(amount="NaN"), "amount 'NaN' is not a number"),
    (row(amount="Infinity"), "amount 'Infinity' is not a number"),
    (row(amount="1_000"), "amount '1_000' is not a number"),
    (row(amount="5."), "amount '5.' is not a number"),
    (row(amount='"1,000"'), "amount '1,000' is not a number"),
    (row(amount=""), "amount '' is not a number"),
    (row(amount="٥"), "amount '٥' is not a number"),
    (row(amount="1.505"), "amount '1.505' has more than 2 decimal places"),
    (row(amount="1.500"), "amount '1.500' has more than 2 decimal places"),
    (row(amount="0"), "amount must not be zero"),
    (row(amount="-0"), "amount must not be zero"),
    (row(amount="0.00"), "amount must not be zero"),
    (row(currency="usd"), "unknown currency 'usd'"),
    (row(currency="GBP"), "unknown currency 'GBP'"),
    (row(category=" "), "empty category"),
    (row(id=""), "empty id"),
    ("t1,2026-03-01,-10.00,ILS,food\n", "expected 6 fields, got 5"),
    ("t1,2026-03-01,-10.00,ILS,food,a,b\n", "expected 6 fields, got 7"),
])
def test_bad_row_reasons(bad_row, reason):
    e = error_of(HEADER + GOOD.replace("t1", "t0") + bad_row)
    assert (e.line, e.reason) == (3, reason)
    assert str(e) == f"line 3: {reason}"


@pytest.mark.parametrize("bad_row, reason", [
    (row(id="", date="x"), "empty id"),
    (row(date="x", amount="x"), "date 'x' is not YYYY-MM-DD"),
    (row(amount="x", currency="x"), "amount 'x' is not a number"),
    (row(currency="x", category=""), "unknown currency 'x'"),
    ("t1,x,x,x,x\n", "expected 6 fields, got 5"),
])
def test_checks_run_in_documented_order(bad_row, reason):
    assert error_of(HEADER + bad_row).reason == reason


def test_field_count_includes_extra_header_columns():
    e = error_of("id,date,amount,currency,category,memo,note\n" + GOOD)
    assert (e.line, e.reason) == (2, "expected 7 fields, got 6")


@pytest.mark.parametrize("amount, expected", [
    ("+5", Decimal("5")), ("-2.50", Decimal("-2.50")), (".50", Decimal("0.50")),
    ("7", Decimal("7")), ("-.5", Decimal("-0.5")),
])
def test_accepted_amount_forms(amount, expected):
    (t,) = parse_text(HEADER + row(amount=amount))
    assert t.amount == expected


def test_line_numbers_count_blank_lines_and_parsing_stops_at_first_bad_row():
    text = HEADER + "\n   \n" + GOOD + "\n" + row(id="t2", amount="x") + row(id="t3", date="x")
    e = error_of(text)
    assert (e.line, e.reason) == (6, "amount 'x' is not a number")


def test_multiline_quoted_record_reported_at_first_line():
    text = HEADER + 't1,2026-03-01,-1.00,ILS,food,"two\nlines"\n' + row(id="t2", amount="x")
    assert error_of(text).line == 4
    text = HEADER + 't1,2026-03-01,x,ILS,food,"two\nlines"\n'
    assert error_of(text).line == 2


def test_multiline_memo_is_kept():
    (t,) = parse_text(HEADER + 't1,2026-03-01,-1.00,ILS,food,"two\nlines"\n')
    assert t.memo == "two\nlines"


# Scenario 6 -----------------------------------------------------------------

def test_duplicate_id_names_second_line_and_first_line():
    e = error_of(HEADER + GOOD + "\n" + GOOD)
    assert (e.line, e.reason) == (4, "duplicate id 't1' (first seen on line 2)")


# Scenario 7 -----------------------------------------------------------------

def test_missing_columns_in_canonical_order():
    e = error_of("memo,amount,id,date\n" + GOOD)
    assert (e.line, e.reason) == (1, "missing column(s): currency, category")
    e = error_of("id,date,amount\n")
    assert (e.line, e.reason) == (1, "missing column(s): currency, category, memo")


def test_duplicate_required_column():
    e = error_of("id,date,amount,currency,category,memo,date\n")
    assert (e.line, e.reason) == (1, "duplicate column 'date'")


def test_empty_file_is_missing_header():
    path = FIXTURES / "empty.csv"
    assert path.stat().st_size == 0
    with pytest.raises(LedgerError) as info:
        parse_csv(path)
    assert (info.value.line, info.value.reason) == (1, "missing header")
    assert str(info.value) == "line 1: missing header"


def test_only_blank_lines_is_missing_header():
    e = error_of("\n  \n\n")
    assert (e.line, e.reason) == (1, "missing header")


# Errors other than LedgerError ------------------------------------------------

def test_csv_error_becomes_ledger_error():
    old = csv.field_size_limit(10)
    try:
        e = error_of(HEADER + GOOD + row(id="t2", memo="x" * 50))
    finally:
        csv.field_size_limit(old)
    assert e.line == 3
    assert e.reason.startswith("malformed CSV: ")


def test_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        parse_csv(tmp_path / "nope.csv")


def test_invalid_utf8_raises_unicode_decode_error(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_bytes(HEADER.encode() + b"t1,2026-03-01,-1.00,ILS,food,\xff\n")
    with pytest.raises(UnicodeDecodeError):
        parse_csv(path)


# Scenario 8 -----------------------------------------------------------------

@pytest.mark.parametrize("name", ["sample.csv", "bom_blank.csv"])
def test_parse_lines_matches_parse_csv(name):
    path = FIXTURES / name
    text = path.read_text(encoding="utf-8-sig")
    assert parse_lines(io.StringIO(text)) == parse_csv(path)
    assert parse_lines(text.splitlines(keepends=True)) == parse_csv(path)


def test_parse_csv_on_bad_file_matches_parse_lines(tmp_path):
    text = HEADER + "\n" + row(amount="1.505")
    path = tmp_path / "bad.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(LedgerError) as from_file:
        parse_csv(path)
    assert str(from_file.value) == str(error_of(text)) == "line 3: amount '1.505' has more than 2 decimal places"
