# SCRUM-118 — Monthly expense report from a CSV ledger — High-Level Design

## 1. System Overview

- **What:** a new stdlib-only Python package `ledger` (src layout) that parses a UTF-8 CSV ledger into immutable transactions, builds a deterministic one-month report in a base currency, and exposes it as `python -m ledger report FILE --month YYYY-MM [--base] [--top] [--json]`.
- **Problem:** a terminal user wants a monthly summary without a spreadsheet; a bad row must be reported by its physical line number, never silently summed.
- **Responsibilities:** parse + validate (R1, R2), convert + aggregate + round once (R3, R4), CLI with exact text/JSON output and exit codes 0/2/3 (R5), and a new root `pyproject.toml` so `pip install -e .` then `pytest` works (Q1).
- **What the repository actually holds** (verified on `main` @ `51b3688`, the work branch @ `1ed2e3c`): `README.md`, `hello_world.sh`, `test_hello_world.sh`, `hello_world.txt`, `serve.py`, `smoke_test.py`, `docs/`, `stories/`. No Python manifest, no `src/`, no `tests/`, no `.factory/`, no `AGENTS.md`/`CLAUDE.md`, no CI workflow. The spec's §6 description matches the code. Everything this story adds is a new file; no existing file is touched.

## 2. Architecture Overview

Three layers in one package, each in its own module, each owned by one work item:

| Layer | Path | Owner | Depends on |
|---|---|---|---|
| Build manifest | `pyproject.toml` (repo root, new) | t1 | — |
| Model + parser | `src/ledger/__init__.py`, `src/ledger/model.py`, `src/ledger/parse.py` | t1 | stdlib `csv`, `decimal`, `datetime`, `re`, `dataclasses` |
| Report | `src/ledger/report.py` | t2 | `ledger.model` (Transaction) |
| CLI | `src/ledger/cli.py`, `src/ledger/__main__.py` | t3 | `ledger.parse`, `ledger.report`, stdlib `argparse`, `json` |
| Tests + fixtures | `tests/test_ledger_parse.py`, `tests/test_ledger_report.py`, `tests/test_ledger_cli.py`, `tests/fixtures/ledger/*.csv` | t1 / t2 / t3 (one test file each; fixtures created by t1, t3 adds `bad_amount.csv`) | pytest (dev only) |

- Boundaries: the parser knows nothing about months, rates or output; the report knows nothing about files or CSV; the CLI is the only place that touches `sys.argv`, stdout/stderr and exit codes.
- External dependencies: none at runtime. Build backend setuptools (PEP 660 editable install, ≥ 64); pytest is a test-only tool.

## 3. Data Flow Design

All synchronous, single process, one pass:

1. CLI parses arguments (argparse); bad arguments → exit 2 before any file I/O.
2. `parse_csv(FILE)` opens with `encoding="utf-8-sig", newline=""` and delegates to `parse_lines`, which yields `Transaction`s in file order or raises `LedgerError(line, reason)` at the first bad row. `OSError` / `UnicodeDecodeError` propagate unchanged (decode errors surface lazily, during iteration).
3. `monthly_report(transactions, month, base, top, rates)` filters to the month, converts each amount at full Decimal precision (`amount × rates[currency] ÷ rates[base]`), sums exact values, then quantizes each figure once to `0.01` with `ROUND_HALF_EVEN`.
4. CLI renders text (13 lines for the sample, `categories: none` when empty) or `json.dumps(report.to_dict())`, writes stdout, exits 0. `LedgerError` → stderr `error: {FILE}:{line}: {reason}`, exit 3. Unreadable file → stderr message, exit 2.

## 4. Component Breakdown

All components land in `ophirgal/test-repo-for-halo` (the only repository).

- **Manifest (t1)** — `pyproject.toml`: setuptools backend, packages found under `src/`, `requires-python >= 3.9`, no runtime `dependencies`, an optional `test` extra listing pytest, `[tool.pytest.ini_options] testpaths = ["tests"]`. Package discovery must be explicit (`where = ["src"]`): the root holds stray top-level `.py` files (`serve.py`, `smoke_test.py`) that setuptools' flat-layout auto-discovery would otherwise trip on.
- **Model + parser (t1)** — In: path or iterable of text lines. Out: `list[Transaction]` (frozen dataclass), `LedgerError(line, reason)`. Owns every row/header validation rule (§5.2).
- **Report (t2)** — In: transactions, month, base, top, rates. Out: a report value with `month, base, count, income, expense, net, categories` (`CategoryTotal(name, total, count)`) and `to_dict()`. Owns `RATES`, conversion, rounding, sorting, top-N, caller-argument validation (§5.3).
- **CLI (t3)** — In: argv. Out: stdout text/JSON, stderr messages, exit codes 0/2/3. Owns `python -m ledger` entry point (§5.4).

## 5. Interface Contracts

### 5.1 Public names
Importable from `ledger` (re-exported by `src/ledger/__init__.py` as each item lands): `Transaction`, `LedgerError`, `parse_csv`, `parse_lines` (t1); `monthly_report`, `CategoryTotal`, `RATES` (t2). Exact signatures are those the spec names (FR1–FR4).

### 5.2 Parser rules (t1) — edge cases settled here
Verified against Python 3.12 in this workspace: `Decimal()` accepts `1e3`, `NaN`, `Infinity`, `1_000`, `5.`, Arabic-Indic digits and surrounding spaces; `date.fromisoformat` (3.11+) accepts `20260301` and week dates like `2026-W01-1`; `csv.reader` yields `[]` for an empty line and `['   ']` for a whitespace-only one, a quoted field may span physical lines, and an unterminated quote at EOF is returned as a field rather than an error. So neither `Decimal` nor `fromisoformat` may be the validator on its own:

- **Header:** the first non-blank line. No non-blank line at all (including a zero-byte file) → `line 1: missing header`. Header cells are stripped (and a leading U+FEFF is removed, so `parse_lines` on BOM text equals `parse_csv`). Missing required columns → `missing column(s): a, b` in canonical order `id, date, amount, currency, category, memo`. A required column named twice → `duplicate column 'X'` on the header's line. Extra columns are ignored but counted in N.
- **Line numbers:** physical lines, header = its physical line (1 in every normal file), blank lines counted; a record whose quoted field spans lines is reported at the line it starts on.
- **Skipped rows:** a row that is empty or whose fields are all whitespace.
- **Check order per row** (first failure wins): field count (`expected N fields, got M`, N = header cell count) → `empty id` → `duplicate id 'X' (first seen on line L)` → date → amount → currency → `empty category`.
- **Date:** must match ASCII `^\d{4}-\d{2}-\d{2}$` else `date 'X' is not YYYY-MM-DD`; then must be a real calendar date else `date 'X' is not a calendar date`.
- **Amount:** must match ASCII `^[+-]?(\d+(\.\d+)?|\.\d+)$` else `amount 'X' is not a number` (refuses `1e3`, `NaN`, `Infinity`, `1_000`, `5.`, `1,000`, non-ASCII digits, empty). More than two digits after the point, counted in the text (so `1.500` is refused too) → `amount 'X' has more than 2 decimal places`. Numerically zero (`0`, `-0`, `0.00`) → `amount must not be zero`. The stored `Decimal` is built from the stripped text (`+5` → `Decimal("5")`, `12000.00` keeps its exponent).
- **Currency:** stripped, case-sensitive in `{ILS, USD, EUR}` else `unknown currency 'X'`.
- **Errors other than `LedgerError`:** `OSError` and `UnicodeDecodeError` from opening/reading propagate unchanged; `csv.Error` (e.g. a field over the csv size limit) is converted to `LedgerError` on the record's line with reason `malformed CSV: {message}`.

### 5.3 Report rules (t2)
- `month` must fully match `^\d{4}-(0[1-9]|1[0-2])$` (ASCII) else `ValueError`; `base` not in `rates` → `ValueError`; `top` not `None` and `< 1` → `ValueError`; a month transaction whose currency has no entry in `rates` → `ValueError` naming the currency. Never `LedgerError`.
- `income` = sum of converted positive amounts, `expense` = sum of converted negative amounts, `net` = sum of all, category `total` = sum of its converted amounts, `count` = number of transactions; each figure quantized once to `0.01` `ROUND_HALF_EVEN`, independently. A figure that quantizes to zero is `Decimal("0.00")`, never `-0.00`.
- Categories sorted by absolute rounded total descending, then name ascending; `top` truncates only `categories`.
- `to_dict()` → `{"month", "base", "count", "income", "expense", "net", "categories": [{"name", "total", "count"}]}`, amounts as strings with two places, `count` as int.

### 5.4 CLI contract (t3)
- `python -m ledger report FILE --month YYYY-MM [--base {ILS,USD,EUR}] [--top N] [--json]`; subcommand required (no subcommand → exit 2); `--month` required and validated in argparse (`2026-13` → exit 2); `--top` integer ≥ 1; `--base` default ILS.
- Text: `month:`, `base:`, `transactions:`, `income:`, `expense:`, `net:`, then `categories:` followed by `  {name}: {total} ({count})` lines, or `categories: none` when empty. JSON: one object, one line, trailing newline.
- Exit 2 for argparse errors and for a FILE that raises `OSError` or `UnicodeDecodeError` (stderr `error: cannot read {FILE}: …`, stdout empty). Exit 3 for `LedgerError`: stderr exactly `error: {FILE}:{line}: {reason}\n`, stdout empty. Output is buffered so nothing reaches stdout before a failure.

## 6. Key Technical Decisions

- **Regex gate before `Decimal` / `date`:** the stdlib parsers are too permissive (§5.2); explicit ASCII patterns make the accepted forms exact and the same on every supported Python.
- **Decimal end to end, round once:** default context (28 significant digits) is ample for ledger magnitudes; the sample's USD figures were checked by hand (12000.00 ÷ 3.70 = 3243.2432… → 3243.24; income 3493.2432… → 3493.24; expense −3025.50 ÷ 3.70 = −817.7027… → −817.70; net → 2675.54), so the spec's numbers are self-consistent.
- **argparse for the CLI:** it already exits 2 with a usage message on stderr, matching R5; `--month` validation reuses the report's month rule so the CLI and library agree.
- **setuptools backend, explicit `src/` discovery:** smallest manifest that makes `pip install -e .` work; alternatives (hatchling, flit) add nothing here.
- **`pyproject.toml` in t1:** the first item must already be installable and testable on its own.
- Alternatives rejected: `float` (precision), `csv.DictReader` (loses field-count check against extra columns), live rates (out of scope).

## 7. Risks & Constraints

- **RK-style risk — no repo gate:** there is no `.factory/testing.md` and no CI; the agreed gate is `pip install -e .` then `pytest` from the root. pytest is not installed in this workspace's Python 3.12, so each item installs it via the `test` extra (`pip install -e '.[test]'`).
- **Python version drift:** `date.fromisoformat` behaviour differs 3.9 vs 3.11+; the regex gate removes the difference.
- **Scale:** one pass, O(n) memory for the transaction list; fine for personal/small-team ledgers. No network, no file writes, no secrets.
- **Sibling infrastructure (spec Q1 risk):** if another story introduces a different Python setup, the manifest may need merging later.

## 8. Assumptions

- Edge cases the spec leaves open are settled in §5.2–§5.4 (duplicate header column, `5.`/`1.500` refused, multi-line record line number, `csv.Error` → `LedgerError`, negative-zero normalised, missing rate → `ValueError`). If the product owner wants any of these differently, only the owning item's criteria change.
- `requires-python >= 3.9` (verified locally on 3.12 only).
- Epic sources R1–R5 / RK1–RK2 were not available; identifiers are used as the story states them.
