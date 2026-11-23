"""End-to-end tests of ``python -m ledger report`` (SCRUM-118 t3).

Every case runs the installed package through subprocess, with no sys.path change.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = "tests/fixtures/ledger/sample.csv"
BAD_AMOUNT = "tests/fixtures/ledger/bad_amount.csv"


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "ledger", *args],
        capture_output=True, text=True, cwd=ROOT,
    )


# Scenario 19
def test_text_report():
    p = run("report", SAMPLE, "--month", "2026-03")
    assert p.returncode == 0
    assert p.stderr == ""
    assert p.stdout == (
        "month: 2026-03\n"
        "base: ILS\n"
        "transactions: 7\n"
        "income: 12925.00\n"
        "expense: -3025.50\n"
        "net: 9899.50\n"
        "categories:\n"
        "  salary: 12000.00 (1)\n"
        "  rent: -1500.00 (1)\n"
        "  freelance: 925.00 (1)\n"
        "  groceries: -760.50 (2)\n"
        "  software: -444.00 (1)\n"
        "  travel: -321.00 (1)\n"
    )
    assert len(p.stdout.splitlines()) == 13


# Scenario 20
def test_json_with_base_and_top():
    p = run("report", SAMPLE, "--month", "2026-03", "--base", "USD", "--top", "1", "--json")
    assert p.returncode == 0
    assert p.stderr == ""
    assert json.loads(p.stdout) == {
        "month": "2026-03", "base": "USD", "count": 7, "income": "3493.24",
        "expense": "-817.70", "net": "2675.54",
        "categories": [{"name": "salary", "total": "3243.24", "count": 1}],
    }
    assert p.stdout.endswith("}\n") and p.stdout.count("\n") == 1


@pytest.mark.parametrize("base", ["ILS", "USD", "EUR"])
def test_each_base_accepted(base):
    p = run("report", SAMPLE, "--month", "2026-03", "--base", base, "--json")
    assert p.returncode == 0
    assert json.loads(p.stdout)["base"] == base


# Scenario 21
def test_empty_month():
    p = run("report", SAMPLE, "--month", "2026-05")
    assert p.returncode == 0
    assert p.stdout.splitlines()[-4:] == [
        "income: 0.00", "expense: 0.00", "net: 0.00", "categories: none",
    ]


# Scenario 22
@pytest.mark.parametrize("args", [
    [],
    ["report", SAMPLE],
    ["report", SAMPLE, "--month", "2026-13"],
    ["report", SAMPLE, "--month", "2026-3"],
    ["report", SAMPLE, "--month", "2026-03", "--top", "0"],
    ["report", SAMPLE, "--month", "2026-03", "--top", "x"],
    ["report", SAMPLE, "--month", "2026-03", "--base", "GBP"],
    ["report", SAMPLE, "--month", "2026-03", "--base", "usd"],
    ["report", "--month", "2026-03"],
    ["report", "tests/fixtures/ledger/does-not-exist.csv", "--month", "2026-03"],
    ["report", "tests/fixtures/ledger", "--month", "2026-03"],
])
def test_usage_errors_exit_2(args):
    p = run(*args)
    assert p.returncode == 2
    assert p.stdout == ""
    assert p.stderr.strip() != ""


def test_non_utf8_file_exits_2(tmp_path):
    path = tmp_path / "latin1.csv"
    path.write_bytes(b"id,date,amount,currency,category,memo\nt1,2026-03-01,-1.00,ILS,food,caf\xe9\n")
    p = run("report", str(path), "--month", "2026-03")
    assert p.returncode == 2
    assert p.stdout == ""
    assert "cannot read" in p.stderr


# Scenario 23
def test_bad_row_exits_3_with_exact_message():
    p = run("report", BAD_AMOUNT, "--month", "2026-03")
    assert p.returncode == 3
    assert p.stdout == ""
    assert p.stderr == f"error: {BAD_AMOUNT}:3: amount '-2.505' has more than 2 decimal places\n"


def test_bad_row_message_uses_path_as_typed():
    path = "./" + BAD_AMOUNT
    p = run("report", path, "--month", "2026-03", "--json")
    assert p.returncode == 3
    assert p.stdout == ""
    assert p.stderr == f"error: {path}:3: amount '-2.505' has more than 2 decimal places\n"


# Scenario 24
def test_help():
    p = run("report", "--help")
    assert p.returncode == 0
    assert "--month" in p.stdout


# Determinism
@pytest.mark.parametrize("extra", [[], ["--json", "--base", "EUR"]])
def test_output_is_byte_identical(extra):
    first = run("report", SAMPLE, "--month", "2026-03", *extra)
    second = run("report", SAMPLE, "--month", "2026-03", *extra)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout and first.stderr == second.stderr
