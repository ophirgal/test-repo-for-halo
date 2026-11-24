# High-Level Design — SCRUM-127: A helper that doubles a number

## 1. System Overview

- **What:** a new package `testbed_utils` under `src/`, with a module `src/testbed_utils/doubler.py` that defines `double(n)` and returns `n * 2`. A pytest file `tests/test_doubler.py` covers positive, zero and negative integers (spec FR1–FR4).
- **Why:** this is a QA probe story (`QA-20261124-N1`). It gives the factory a small change that is easy to check from intake through to a reviewed pull request.
- **Verified against the code** (`ophirgal/test-repo-for-halo`, work branch cut from `main` at `561d3c7`):
  - `src/` holds only `src/ledger/`. Neither `src/testbed_utils/` nor `tests/test_doubler.py` exists.
  - `pyproject.toml` finds packages with `[tool.setuptools.packages.find] where = ["src"]`, sets `testpaths = ["tests"]` and lists `pytest` as the `test` extra.
  - No `tests/conftest.py` exists and there is no `pythonpath` setting. `tests/test_ledger_parse.py` imports `from ledger import ...`, and `tests/test_ledger_cli.py:3` says it runs "the installed package". So `src` packages are importable only after the project is installed (`pip install -e .`). A plain `python -m pytest` without installing fails with `ModuleNotFoundError: No module named 'ledger'`, which I checked in this checkout.
  - The repo has no `CLAUDE.md`, `AGENTS.md`, `.factory/` or CI workflow, so no gate runs on the pull request beyond the review.

## 2. Architecture Overview

- **`src/testbed_utils/` (new package):** `__init__.py` (it can be empty) plus `doubler.py`. Because `packages.find` already searches `src`, setuptools picks the package up with no change to `pyproject.toml`. I checked this: after `pip install -e .` in a scratch copy, both `import testbed_utils` and `import ledger` succeed.
- **`tests/test_doubler.py` (new):** pytest tests. They import `from testbed_utils.doubler import double`, the same way the existing tests import `ledger`.
- **External dependencies:** none at runtime. `pytest` is needed for tests and is already declared.
- **Untouched:** `src/ledger/`, `kvstore/`, `linkcheck/`, `serve.py`, the existing tests, `pyproject.toml` and `README.md` (spec §2 and AC3).

## 3. Data Flow Design

- Synchronous, in-process call: `double(n)` → `n * 2`. There is no I/O, no state and no events.

## 4. Component Breakdown

| Component | Responsibility | Inputs / Outputs | Repository |
|---|---|---|---|
| `src/testbed_utils/__init__.py` | Marks the package so setuptools finds it | — | `ophirgal/test-repo-for-halo` |
| `src/testbed_utils/doubler.py` | Defines `double(n)` | int in, int (`n * 2`) out | `ophirgal/test-repo-for-halo` |
| `tests/test_doubler.py` | pytest coverage for positive, zero and negative inputs | — | `ophirgal/test-repo-for-halo` |

## 5. Interface Contracts

- `from testbed_utils.doubler import double` works once the project is installed (`pip install -e ".[test]"`).
- For every `int` `n`, `double(n) == n * 2` and the result is an `int`. Examples: `double(3) == 6`, `double(0) == 0`, `double(-4) == -8`. Python ints have arbitrary precision, so there is no overflow (`2**70` doubles exactly).
- Non-integer input is out of scope (spec §2). The function does no type checking and raises nothing of its own. Whatever `n * 2` does is what happens: `True` gives `2`, `3.5` gives `7.0`, `"a"` gives `"aa"`, and `None` raises `TypeError` from the `*` operator. No test asserts any of these.
- No cross-repo contracts.

## 6. Key Technical Decisions

- **D1 — Importability works through the existing install path, not a path hack.** The work item adds `src/testbed_utils/__init__.py` and changes neither `pyproject.toml` nor any `conftest.py`. This matches how `ledger` is consumed today. *Alternative rejected:* adding `pythonpath = ["src"]` to `pyproject.toml`. It would change shared config that the spec asks us not to touch.
- **D2 — Tests are plain pytest functions.** This follows `tests/test_ledger_parse.py`. The evidence on the pull request is `pip install -e ".[test]"` followed by `python -m pytest`, which is how `pyproject.toml` configures the suite.
- **D3 — README stays as it is.** The README's `python -m unittest discover -s tests` command is an existing inconsistency that `test_ledger_parse.py` already has (it imports pytest). The spec rules out a README section for the helper, so fixing that command is not part of this story.
- **D4 — One work item.** The change is three small new files with no consumers, so splitting it would only fragment it.

## 7. Risks & Constraints

- **Running the tests without installing the project** fails at import. This is true of the existing `ledger` tests too. The PR evidence must install first (D2). Risk: low.
- **Function name assumption** (spec D1): `double` was decoded from Jira's `(n)` emoticon. If it is wrong, only the name changes. Risk: low.
- **Scale, performance and security:** not applicable. The function is pure, has no I/O and takes no untrusted input.

---

Why did the helper function go to therapy? It had a doubling problem.
