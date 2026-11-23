# SCRUM-118 — Monthly expense report from a CSV ledger — Implementation plan

## Context

SCRUM-118 adds a new stdlib-only Python package `ledger` (src layout) to `ophirgal/test-repo-for-halo`. The package parses a UTF-8 CSV ledger into frozen `Transaction`s and reports each bad row by its physical line number. It builds a one-month report in a base currency at fixed rates, rounding once with `ROUND_HALF_EVEN`. It runs as `python -m ledger report FILE --month YYYY-MM [--base] [--top] [--json]` with exit codes 0/2/3. A new root `pyproject.toml` makes `pip install -e .` followed by `pytest` work. The acceptance criteria are Scenarios 1–26 of `spec.md`. The work lands on `halo/feat/scrum-118-20261123-173829`, cut from `main` (`51b3688`), and merges into `main`. The approved requirement is `spec.md`, the design is `hld.md` and the three work items (t1 → t2 → t3) are in `work-items.md`. All three sit beside this file in `stories/SCRUM-118/`.

## Research findings

- **Repository contents (fact).** `main` @ `51b3688` tracks `README.md`, `docs/.nojekyll`, `docs/index.html`, `docs/jungle.html`, `docs/plans/_.txt`, `hello_world.sh`, `hello_world.txt`, `serve.py`, `smoke_test.py`, `test_hello_world.sh` and `stories/`. It has no `pyproject.toml`, `setup.cfg` or `setup.py`. It has no `src/`, `tests/`, `.gitignore`, `.factory/`, `.github/`, `AGENTS.md` or `CLAUDE.md`. No remote branch carries `pyproject.toml`, `src/ledger` or `tests/`, so no sibling Python setup exists to merge with today.
- **Change surface.** Every file is new. No existing file is edited (spec §2 Non-Goals, Scenario 26):
  - `pyproject.toml` (repo root)
  - `src/ledger/__init__.py`, `src/ledger/model.py`, `src/ledger/parse.py`, `src/ledger/report.py`, `src/ledger/cli.py`, `src/ledger/__main__.py`
  - `tests/test_ledger_parse.py`, `tests/test_ledger_report.py`, `tests/test_ledger_cli.py`
  - `tests/fixtures/ledger/sample.csv`, `bom_blank.csv`, `empty.csv`, `bad_amount.csv`
- **Root Python files that interact with tooling (fact).**
  - `serve.py` and `smoke_test.py` are top-level modules. setuptools' flat-layout auto-discovery would refuse them, so discovery must be explicit: `where = ["src"]` (`hld.md` §4).
  - `smoke_test.py` matches pytest's default `*_test.py` pattern and starts an HTTP server on import (`smoke_test.py:15-20` imports `serve`). `testpaths = ["tests"]` keeps a bare `pytest` from collecting it.
- **Contracts (locked by the spec and the HLD, quoted exactly):**
  - Public names from `ledger`: `Transaction`, `LedgerError`, `parse_csv`, `parse_lines`, `monthly_report`, `CategoryTotal`, `RATES`.
  - `RATES = {"ILS": Decimal("1"), "USD": Decimal("3.70"), "EUR": Decimal("4.00")}`.
  - Error text formats: `line {line}: {reason}`, `error: {FILE}:{line}: {reason}`, and every reason string in Scenario 5–7 and `hld.md` §5.2.
  - Output layouts: the 13-line text layout (Scenario 19), `categories: none`, and the `to_dict()` JSON keys `month, base, count, income, expense, net, categories[name,total,count]`.
- **Toolchain in the pod (fact).**
  - Python 3.12.15 at `/opt/venv/bin/python3`, with setuptools 84.0.0 (≥ 64, so PEP 660 editable installs work).
  - pytest is **not** installed. `pip download pytest` reaches the index from this pod.
- **Gate discovery (fact).** dev-toolkit's `run-tests-gate.sh` has no `.factory/testing.md` to read. It discovers `pytest` only when both of these hold (`run-tests-gate.sh:801-807`):
  - `pytest` is on PATH.
  - `pyproject.toml` contains `[tool.pytest`.
- **Stdlib behaviour that drives the parser (fact, `hld.md` §5.2, checked on 3.12):**
  - `Decimal()` accepts `1e3`, `NaN`, `Infinity`, `1_000` and `5.`.
  - `date.fromisoformat` accepts `20260301` and `2026-W01-1`.
  - `csv.reader` yields `[]` for an empty line and `['   ']` for a whitespace-only line.
  - `reader.line_num` counts physical lines consumed, including the lines inside a multi-line quoted field.
- **Arithmetic check (fact, recomputed from the t1 fixture rows).**
  - March in ILS: salary 12000.00, rent -1500.00, freelance 250×3.70 = 925.00, groceries -420.25-340.25 = -760.50, software -120×3.70 = -444.00, travel -80.25×4.00 = -321.00. These give income 12925.00, expense -3025.50 and net 9899.50, matching Scenario 9.
  - The USD figures in Scenario 20 match `hld.md` §6.
- **Unknowns remaining:** none that block. The repository has no canonical gate; the agreed gate comes from spec §6.

## Locked decisions and assumptions

**Locked decisions**
- Stdlib only at runtime. The `decimal.Decimal` type is used end to end. Each figure is rounded once to `0.01` with `ROUND_HALF_EVEN` (spec FR5, Scenario 11).
- A new root `pyproject.toml` (decision Q1 (a), spec §8; FR11, Scenario 26):
  - setuptools backend with packages found under `src/`
  - `requires-python >= 3.9` and no runtime `dependencies`
  - a `test` extra listing pytest
  - `[tool.pytest.ini_options] testpaths = ["tests"]`
- Module split and ownership follow `hld.md` §2 and `work-items.md`:
  - t1 owns `model.py`, `parse.py`, `__init__.py`, `pyproject.toml` and three fixtures.
  - t2 owns `report.py` and only appends re-exports to `__init__.py`.
  - t3 owns `cli.py`, `__main__.py` and `bad_amount.csv`, and does not touch `__init__.py`.
- Parser rules, check order and exact reasons come from `hld.md` §5.2. They include the ASCII regex gates for the date (`^\d{4}-\d{2}-\d{2}$`) and the amount (`^[+-]?(\d+(\.\d+)?|\.\d+)$`), `duplicate column 'X'`, and `malformed CSV: {message}`.
- Report rules come from `hld.md` §5.3:
  - The month regex is `^\d{4}-(0[1-9]|1[0-2])$`.
  - A missing rate for a counted transaction raises `ValueError`.
  - `-0.00` is normalised to `0.00`.
  - Categories sort by absolute rounded total, then by name.
- The CLI contract comes from `hld.md` §5.4: argparse; exit 2 on argparse errors, `OSError` or `UnicodeDecodeError`; exit 3 on `LedgerError`; nothing is written to stdout before a failure.
- CLI tests use `subprocess` with `[sys.executable, "-m", "ledger", ...]` against the installed package and never touch `sys.path` (Scenario 25).
- No existing file changes, including `README.md` (spec §6).

**Assumptions**
- **The implement pod can reach the package index**, as this pod can. Without it, `pip install -e '.[test]'` cannot fetch pytest, and the gate records `unavailable` rather than green. That is reported as blocked, never worked around.
- **No `.gitignore` is added.** Evidence: the spec lists the only new paths as `pyproject.toml`, `src/ledger/`, `tests/`. Consequence if wrong: the build outputs below sit untracked, and an over-broad stage could commit them. Step 9 guards against that.
  - `src/ledger.egg-info/`
  - `__pycache__/`
  - `.pytest_cache/`
- **The CLI and the library share one month rule** through a small helper in `src/ledger/report.py`, imported by `cli.py` from `ledger.report`. Consequence if wrong: none for behaviour. An argparse-local regex would also satisfy Scenario 22, but the HLD prefers one rule.
- **Help text goes to stdout, not stderr.** argparse prints `--help` to stdout, which meets Scenario 24.

## Solution proposal

The package is a three-layer pipeline with one module per responsibility, as in `hld.md` §2–§3. The parser knows only text. The report knows only `Transaction`s. The CLI is the only place that sees argv, streams and exit codes.

- **Manifest first (t1).** `pyproject.toml` declares:
  - `[build-system] requires = ["setuptools>=64"]` and `build-backend = "setuptools.build_meta"`
  - `[project] name = "ledger"`, `requires-python = ">=3.9"`, `dependencies = []`, `optional-dependencies.test = ["pytest"]`
  - `[tool.setuptools.packages.find] where = ["src"]`
  - `[tool.pytest.ini_options] testpaths = ["tests"]`

  The `[tool.pytest` table also makes `run-tests-gate.sh` discover `pytest` as the gate. Explicit `src/` discovery avoids the flat-layout error that `serve.py` and `smoke_test.py` would cause.
- **Parser (t1).** `parse_lines` wraps the iterable in `csv.reader`. It tracks each record's start line as the previous `reader.line_num + 1`.
  - Rows that are empty or all-whitespace are skipped until the first non-blank row, which is the header.
  - Header cells are stripped and a leading U+FEFF is removed. Missing columns are checked in canonical order, then duplicate required columns.
  - The column-name → index map comes from the header. N is the header cell count.
  - Each data row is validated in the HLD order, and the first failure raises `LedgerError`. A `csv.Error` from iteration is caught and re-raised as `LedgerError(start_line, f"malformed CSV: {e}")`.
  - `Transaction` is a `@dataclass(frozen=True)`. `amount` is `Decimal(stripped_text)`, so the exponent is kept: `12000.00` stays `12000.00`.
  - `LedgerError(Exception)` stores `line` and `reason`, and its `__str__` returns `line {line}: {reason}`.
  - `parse_csv(path)` opens the file with `encoding="utf-8-sig", newline=""` and returns `parse_lines(f)` inside the `with` block. `OSError` and `UnicodeDecodeError` propagate.
- **Report (t2).** `monthly_report` validates its arguments before it touches the data. It filters by `t.date.strftime("%Y-%m") == month`.
  - Each amount converts as `amount * rates[currency] / rates[base]` under the default Decimal context.
  - Running sums are exact: positive amounts, negative amounts, the total, and per-category total and count.
  - Each figure is quantized independently by one `_money()` helper: `quantize(Decimal("0.01"), ROUND_HALF_EVEN)`, then `+ Decimal("0.00")` when it is zero, so `-0.00` cannot appear.
  - Categories sort by `(-abs(total), name)` and are then cut to `top`.
  - The report value is a frozen dataclass with `to_dict()`, which renders amounts with `str()`. Quantized values always have two places.
- **CLI (t3).** `main(argv=None) -> int` builds an argparse parser.
  - The `report` subparser is required. `FILE` is positional. `--month` is required and its `type=` callable reuses the report's month check.
  - `--base` has `choices=["ILS","USD","EUR"]` and `default="ILS"`. `--top` uses a `type=` callable that parses an int ≥ 1. `--json` is a flag.
  - `parse_csv` and `monthly_report` run inside the error handlers. The output is built as one string and written to stdout only on success.
  - `__main__.py` is `raise SystemExit(main())`.
- **Alternatives rejected** (`hld.md` §6): `float` (loses precision); `csv.DictReader` (cannot compare field counts against extra columns); `Decimal` or `fromisoformat` as the only validator (too permissive); hatchling or flit (no gain); a console-script entry point (not required, since `python -m` is the contract).

## Ordered implementation steps

**Work item t1 — scaffold, model, parser**

1. Create `pyproject.toml` with the tables in the Solution proposal. This advances Scenario 26 and FR11. Coverage: the pytest run itself (collection succeeds), plus an assertion in `tests/test_ledger_parse.py` that `from ledger import Transaction, LedgerError, parse_csv, parse_lines` works.
2. Create `src/ledger/model.py` with `Transaction` (frozen dataclass: `id`, `date`, `amount`, `currency`, `category`, `memo`) and `LedgerError(line, reason)`. Create `src/ledger/__init__.py` re-exporting t1's four names with an `__all__`. This advances Scenarios 1 and 5, covered by pytest unit tests in `tests/test_ledger_parse.py`.
3. Create `src/ledger/parse.py` with `parse_lines` and `parse_csv` per `hld.md` §5.2: header detection, BOM strip, missing and duplicate columns, physical line numbers, skipping blank rows, per-row checks in the fixed order, and the `csv.Error` conversion. This advances Scenarios 1–8, FR9 and FR10, covered by pytest unit tests.
4. Create the fixtures:
   - `tests/fixtures/ledger/sample.csv`: the nine rows exactly as listed in t1's criteria, with at least one empty memo.
   - `tests/fixtures/ledger/bom_blank.csv`: starts with the bytes `EF BB BF`; has an empty line and a whitespace-only line between its two rows; one row has an empty memo and the other a `"…,…"` quoted memo.
   - `tests/fixtures/ledger/empty.csv`: zero bytes.

   Verify the BOM and zero-byte content at the byte level, because editors strip them. This advances Scenarios 1, 3 and 7.
5. Write `tests/test_ledger_parse.py`. Use parametrized cases for every reason string and every listed accepted and refused form:
   - Accepted: `+5`, `-2.50`, `.50`.
   - Refused: `1e3`, `NaN`, `Infinity`, `1_000`, `5.`, `1,000`, empty, non-ASCII digits, `1.500`, `0`, `-0`, `0.00`, `usd`, `20260301`, `2026-W01-1`.
   - Header: column order, extra columns and N, missing and duplicate columns, header-only, a file of only blank lines.
   - Line numbers: a duplicate id across a blank line (Scenario 6), and the start line of a multi-line quoted record.
   - Entry points: `parse_lines(io.StringIO(...))` equals `parse_csv` on each fixture, including text prefixed with U+FEFF (Scenario 8).
   - Errors: a malformed-CSV case if one can be triggered (field size limit). `OSError` propagates.

   This advances Scenarios 1–8, at the pytest unit layer.

**Work item t2 — monthly report**

6. Create `src/ledger/report.py`:
   - `RATES`, `CategoryTotal` (frozen dataclass `name, total, count`), the frozen report dataclass with `to_dict()`, the month-validation helper, `_money()` and `monthly_report`, per `hld.md` §5.3.
   - The validation errors: `ValueError` for a bad month, a base missing from `rates`, `top < 1`, or a missing rate for a counted transaction.

   Append `monthly_report`, `CategoryTotal` and `RATES` to `src/ledger/__init__.py`, and change nothing else there. This advances Scenarios 9–18, covered by pytest unit tests.
7. Write `tests/test_ledger_report.py`:
   - Sample-based reports: Scenario 9 (ILS), Scenario 10 (USD, with the expected income, expense and net from t2's criteria), Scenario 13 (`top=2`, `top` larger than the category count, `None`), Scenario 15 (`2026-05`, including `to_dict()` equality) and Scenario 16 (`2026-02`).
   - Built `Transaction`s: Scenario 11 (one and three × 0.05 ILS in EUR → `0.01` and `0.04`), Scenario 12 (`str()` gives `5.00`, `-2.00`, `3.00`), Scenario 14 (a tie ordered by name), Scenario 17 (custom `rates`), a `-0.00` normalisation case, and a missing-rate `ValueError`.
   - Scenario 18: every bad `month`, `base` and `top` raises `ValueError` and is not an instance of `LedgerError`.
   - A repeated call returns an equal result.

   This is the pytest unit layer.

**Work item t3 — command line**

8. Create `src/ledger/cli.py` (`main(argv=None) -> int`) and `src/ledger/__main__.py`. Follow `hld.md` §5.4:
   - argparse with a required subcommand and the `--month`, `--top`, `--base` and `--json` rules from the Solution proposal.
   - Catch `OSError` and `UnicodeDecodeError` around parsing and reporting → stderr `error: cannot read {FILE}: {e}`, exit 2.
   - Catch `LedgerError` → stderr `error: {FILE}:{e.line}: {e.reason}\n`, exit 3.
   - Text rendering produces the 13-line layout, or `categories: none` when there are no categories. JSON rendering is `json.dumps(report.to_dict())` plus `\n`.
   - stdout is written once, only on success.

   This advances Scenarios 19–24. Coverage is the subprocess tests in step 10.
9. Create `tests/fixtures/ledger/bad_amount.csv`: a valid header on line 1, one valid row on line 2 and amount `-2.505` on line 3. This advances Scenario 23.
10. Write `tests/test_ledger_cli.py`. Each case runs `subprocess.run([sys.executable, "-m", "ledger", ...], capture_output=True, text=True, cwd=<repo root from Path(__file__).resolve().parents[1]>)`, with no `sys.path` edit and no `PYTHONPATH`. FILE is passed as the relative `tests/fixtures/ledger/...` path. Cases:
    - Scenario 19: exact stdout, empty stderr, exit 0.
    - Scenario 20: `json.loads` equality.
    - Scenario 21: the trailing four lines.
    - Scenario 22: each usage error gives exit 2, empty stdout and non-empty stderr. FILE errors cover a missing path, a directory, and a non-UTF-8 file written to `tmp_path`.
    - Scenario 23: exact stderr bytes and exit 3.
    - Scenario 24: `--help` exits 0 and stdout contains `--month`.
    - Two identical runs give byte-identical output.

    This advances Scenarios 19–25, at the pytest subprocess layer (an end-to-end check of the real entry point).
11. Stage only the owned paths: `pyproject.toml`, `src/ledger/*.py` and `tests/**`. Leave out the untracked outputs of the install and the gate (`src/ledger.egg-info/`, `__pycache__/`, `.pytest_cache/`). Confirm that `git diff --name-status main...HEAD` shows only `A` entries outside `stories/` (Scenario 26: no existing file changed). This applies to every work item.

Invariants the implement phase covers:
- **Authorization and tenancy:** none apply. The tool is a local, single-user CLI with no network access, no file writes and no secrets.
- **Concurrency and idempotency:** the tool is a pure function over its input, and the determinism checks are in steps 7 and 10.
- **Validation and error paths:** steps 5, 7 and 10 cover every reason, `ValueError` and exit code.
- **Dependencies:** acquire them with `python3 -m pip install -e '.[test]'` from the repository root in each work item before its gate run, and assume no warm cache.
- **Generated deliverables:** none. Every fixture is hand-written text, and no binary is added, so `.factory/delivery-assets` does not apply.

## Work-item mapping

| Step | Work item | Title (`work-items.md`) |
|---|---|---|
| 1–5, 11 | t1 | SCRUM-118: ledger package scaffold, Transaction model and CSV parser with line-numbered validation |
| 6–7, 11 | t2 | SCRUM-118: monthly report with fixed-rate base-currency conversion, round-once half-even, sorting and top-N |
| 8–10, 11 | t3 | SCRUM-118: `python -m ledger report` command line with text/JSON output and exit codes 0/2/3 |

Every work item has at least one step. Each item builds and passes `pytest` on its own: t1's tests need only t1's files, and t2's need t1 plus `report.py`.

## Verification and CI gate

- **Canonical gate:** the repository declares none. It has no `.factory/testing.md` and no provider CI configuration. The gate agreed in spec §6 and Scenario 26 is, from the repository root, in order:
  1. `pip install -e .` (with the `test` extra, `pip install -e '.[test]'`, so pytest is present)
  2. `pytest`
- **The one local run:** dev-toolkit's `run-tests-gate.sh --run` on each work item's committed SHA. Once `pyproject.toml` carries `[tool.pytest.ini_options]` and the install has put `pytest` on PATH (`/opt/venv/bin`), the script discovers `pytest` (`run-tests-gate.sh:801-807`). The install is dependency acquisition, not a test run. Do not run `pytest` by hand beside the gate, and do not use a second worktree.
- **Test layers:**
  - pytest unit tests for `parse` and `report`.
  - pytest subprocess tests for the CLI against the editable install.
  
  Both run in the pod. No layer needs another environment.
- **What the gate must show:**
  - pytest collects `tests/test_ledger_parse.py`, plus `test_ledger_report.py` and `test_ledger_cli.py` from the work items that add them.
  - Every test passes, with 0 failed, 0 errors and 0 skipped.
  - `smoke_test.py` is not collected.
  - The final diff against `main` is additions only, outside `stories/`.
- **Provider CI configuration:** none is needed or planned. CI is not part of this story.
- **`.factory/testing.md` and `.factory/delivery-assets`:** neither exists or applies.
- **Existing checks:** `bash test_hello_world.sh` and `python3 smoke_test.py` are unaffected, because no file they use changes. They are not part of this story's gate.

## Risks and scope guards

**Risks**
- **No pytest or no index access in the implement pod.** The gate records `unavailable`. Report it as blocked, and do not vendor pytest or fake the result.
- **Editors silently drop the BOM or the zero-byte content in fixtures.** Write those fixtures as bytes and assert their leading bytes and length in the tests.
- **Negative zero, or a regex accidentally accepting non-ASCII digits.** Use `[0-9]` or `re.ASCII` so `\d` cannot match other digits. Explicit tests cover both.
- **Decimal context precision.** The default 28 digits is enough for ledger magnitudes (`hld.md` §6). Do not change the global context.
- **Build outputs getting committed** (`src/ledger.egg-info/`, `__pycache__/`, `.pytest_cache/`). Step 11 guards against this.
- **A future story introducing a different Python setup** (spec Q1 risk). Merging is out of scope here.

**The implement phase must NOT:**
- Modify any file that exists on `main`, including `README.md`, `serve.py`, `smoke_test.py`, the hello-world files, `docs/` and other stories' folders.
- Add `.gitignore`, `.factory/testing.md`, CI workflows, a console-script entry point, or any runtime dependency.
- Use `float`, live rates, or rounding before summing.
- Change any reason string, output line or exit code from the spec or the HLD.
- Edit `src/ledger/__init__.py` in t3, or add anything to it in t2 beyond the three re-exports.
- Manipulate `sys.path` or `PYTHONPATH` in tests.
- Edit `spec.md`, `hld.md` or `work-items.md`.
- Make a failing or unavailable check green by deleting, skipping, `xfail`-marking or weakening a test. Report it as blocked instead.

## Clarification outcomes

None.
