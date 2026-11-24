# Implementation plan — SCRUM-127: A helper that doubles a number

## Context

SCRUM-127 (QA probe `QA-20261124-N1`) adds a pure helper `double(n)` that returns `n * 2`, importable as `from testbed_utils.doubler import double`, plus pytest coverage for positive, zero and negative integers. The acceptance criteria are: AC1 `double(n)` returns `n * 2` for integers; AC2 a pytest test under `tests/` covers positive, zero and negative inputs; AC3 existing tests still pass and no existing source under `src/ledger/`, `kvstore/`, `linkcheck/` or `serve.py` is modified. The change lands in `ophirgal/test-repo-for-halo` on work branch `halo/feat/scrum-127-20261124-084416`, cut from `main`. The approved requirement is `spec.md`, the design is `hld.md` and the breakdown (one work item, `t1`) is `work-items.md`, all beside this file in `stories/SCRUM-127/`.

## Research findings

- **Change surface: new files only.** `src/` holds only `src/ledger/` (`__init__.py`, `__main__.py`, `cli.py`, `model.py`, `parse.py`, `report.py`). `src/testbed_utils/` and `tests/test_doubler.py` do not exist.
- **Packaging contract.** `pyproject.toml:17-18` declares `[tool.setuptools.packages.find] where = ["src"]`, so a new `src/testbed_utils/` package with an `__init__.py` is picked up with no config change. `pyproject.toml:14-15` declares the `test` extra as `["pytest"]`. `pyproject.toml:20-21` sets `testpaths = ["tests"]`.
- **Import pattern.** `tests/test_ledger_parse.py:10-12` does `import pytest` and `from ledger import ...`, and defines plain module-level `def test_*` functions (`tests/test_ledger_parse.py:36`). There is no `tests/conftest.py`, no `tests/__init__.py` and no `pythonpath` setting, so `src` packages import only after `pip install -e ".[test]"`. Verified in this environment: `python3 -c "import ledger"` fails with `ModuleNotFoundError`, and no `pytest` is on `PATH`.
- **Package docstring convention.** `src/ledger/__init__.py:1` opens with a one-line module docstring; the new `__init__.py` follows that.
- **Gate.** The repository has no `CLAUDE.md`, `AGENTS.md`, `.factory/` or `.github/`, so there is no provider CI and no `local-test-gate:`. dev-toolkit's `run-tests-gate.sh` discovers plain `pytest` when `pytest` is on `PATH` and `pyproject.toml` contains `[tool.pytest` (`run-tests-gate.sh:801-807`). This repo meets the second condition. The suite as configured is `pip install -e ".[test]"` then `python -m pytest` (hld D2). The README's `python -m unittest discover -s tests` does not collect plain pytest functions; that inconsistency predates this story (hld D3).
- **External data:** none. No cross-repo contract.
- **Unknowns after research:** none that block. Whether the gate's runner has the project installed is an environment property, covered under risks.

## Locked decisions and assumptions

**Locked decisions**
- Module path `src/testbed_utils/doubler.py`, function `double(n)`, test file `tests/test_doubler.py` (spec §6; spec §8 D1 decoded the name from Jira's `(n)` emoticon).
- `double(n)` returns `n * 2`; for `int` input the result is an `int` (spec FR2; hld §5).
- No type checks, no own exceptions, no tests of non-integer behaviour (spec §2 Non-Goals; hld §5).
- Importability through the existing install path: add `src/testbed_utils/__init__.py`; do not touch `pyproject.toml` or add a `conftest.py` (hld D1).
- Plain pytest functions, following `tests/test_ledger_parse.py` (hld D2).
- README unchanged (spec §2; hld D3). No CI workflow (spec §2).
- One work item, `t1` (hld D4; `work-items.md`).

**Assumptions**
- The gate's environment installs the project (`pip install -e ".[test]"`) before running pytest. Evidence: the existing `ledger` tests already require it (`tests/test_ledger_cli.py:3` says it runs "the installed package"). If wrong, the new test fails at import exactly as the existing `ledger` tests do; the result is reported as an environment failure, not fixed with a path hack.
- Parametrizing the three cases with `pytest.mark.parametrize` is acceptable style. Evidence: pytest is the declared test framework; nothing in the repo forbids it. If a reviewer prefers separate functions, only test layout changes.

## Solution proposal

Add a new top-level package `testbed_utils` beside `ledger` under `src/`, discovered by the existing `packages.find where = ["src"]`. It holds:

- `src/testbed_utils/__init__.py` — a one-line module docstring only; it does not re-export `double`, because the contract is `from testbed_utils.doubler import double` (FR1) and nothing else consumes the package.
- `src/testbed_utils/doubler.py` — module docstring plus `def double(n):` with a docstring, whose body is `return n * 2`. No type annotations that imply enforcement, no `isinstance` checks, no `try`/`except`.
- `tests/test_doubler.py` — plain pytest module importing `from testbed_utils.doubler import double`, with one parametrized test over `(3, 6)`, `(0, 0)`, `(-4, -8)` asserting both value and `type(result) is int`. Each case is its own collected test ID, so a failing sign is visible by name.

Key decisions: the install path is the import mechanism (hld D1), so no shared config changes and AC3 holds by construction. Alternatives rejected: `pythonpath = ["src"]` in `pyproject.toml` or a `conftest.py` that edits `sys.path` (changes shared config or adds a path hack the hld rules out); a root-level `testbed_utils/` like `kvstore/` (contradicts the locked path in the spec); re-exporting `double` from `__init__.py` (adds surface no criterion asks for).

## Ordered implementation steps

1. **Create the package marker.** Add `src/testbed_utils/__init__.py` (new) with a one-line docstring. Advances AC1 (importability, FR1). Covered by the import in step 3's test module at the pytest layer.
2. **Add the helper.** Add `src/testbed_utils/doubler.py` (new) defining `double(n)` returning `n * 2`, with docstrings stating it doubles an integer. No validation or error path is added: non-integer input is a non-goal and its behaviour is whatever `*` does. No authorization, tenancy, concurrency or idempotency concern applies: the function is pure, stateless and does no I/O. Advances AC1 (FR1, FR2). Covered by step 3 at the pytest layer.
3. **Add the tests.** Add `tests/test_doubler.py` (new): `import pytest`, `from testbed_utils.doubler import double`, one `@pytest.mark.parametrize` test over positive `3 → 6`, zero `0 → 0` and negative `-4 → -8`, asserting the value and that the result is an `int`. Advances AC1 and AC2 (FR3). Existing pytest layer under `tests/`, collected via `testpaths = ["tests"]`.
4. **Confirm the boundary.** Check that the diff contains only the three new files: no change to `src/ledger/`, `kvstore/`, `linkcheck/`, `serve.py`, any existing test, `pyproject.toml` or `README.md`. Advances AC3. Covered by the full pytest suite at the gate (FR4) and by the diff itself.

Dependencies are acquired by `pip install -e ".[test]"` from `pyproject.toml`; no warm cache is assumed and no new dependency is added. There are no generated deliverables and no binaries, so `.factory/delivery-assets` does not apply.

## Work-item mapping

| Step | Work item | Title |
|---|---|---|
| 1 | t1 | Add testbed_utils.doubler.double(n) with pytest coverage |
| 2 | t1 | Add testbed_utils.doubler.double(n) with pytest coverage |
| 3 | t1 | Add testbed_utils.doubler.double(n) with pytest coverage |
| 4 | t1 | Add testbed_utils.doubler.double(n) with pytest coverage |

Every work item (`t1` is the only one) maps to at least one step.

## Verification and CI gate

- **Canonical gate, in order:** `pip install -e ".[test]"`, then `python -m pytest` from the repository root (collects `tests/` per `pyproject.toml:20-21`). There is no provider CI in this repository, and the story adds none.
- **The one local run** is dev-toolkit's `run-tests-gate.sh --run` on the committed SHA. The repo has no `local-test-gate:`; the script discovers `pytest` from `[tool.pytest.ini_options]` in `pyproject.toml` provided `pytest` is on `PATH`, and otherwise records `not_declared` unless the platform sets `DEV_TOOLKIT_TEST_CMD`. Whatever it records is reported as is; `not_declared` is not a pass. No hand-run of the canonical command beside it and no second worktree.
- **Test layers:** the pytest unit layer under `tests/` is the only one touched, and it runs in a pod. The existing `bash test_hello_world.sh` and `python3 smoke_test.py` checks are unaffected by this change and need nothing new.
- **`.factory/testing.md` / `.factory/delivery-assets`:** neither exists; neither is required by this change.
- **Done means:** the gate run shows the three new `test_doubler.py` cases collected and passing, and every previously existing test passing (AC1–AC3), on a diff that adds only `src/testbed_utils/__init__.py`, `src/testbed_utils/doubler.py` and `tests/test_doubler.py`.

## Risks and scope guards

**Risks**
- *Gate environment without the project installed:* both the new test and the existing `ledger` tests fail at import. Mitigation: the canonical order installs first; if the runner does not, report the failure with its output rather than working around it.
- *Gate records `not_declared`* if `pytest` is not on `PATH` in the runner. Mitigation: report the record honestly; adding `.factory/testing.md` is outside `t1`'s "Owns" list and is not planned.
- *Function name decoding* (spec §8 D1): if the author meant another name, only the name changes. Low.

**Scope guards — the implement phase must NOT:**
- Modify `src/ledger/`, `kvstore/`, `linkcheck/`, `serve.py`, any existing test, `pyproject.toml` or `README.md` (including the README's `unittest` command).
- Add a `conftest.py`, `tests/__init__.py`, a `pythonpath` setting or any `sys.path` manipulation.
- Add type checks, `TypeError`/`ValueError` raising, or tests for floats, `bool`, strings or `None`.
- Add a CLI entry point, HTTP route, README section, runtime dependency, or CI workflow.
- Re-export `double` from `testbed_utils/__init__.py` or add other helpers to the package.
- Make any check green by deleting, skipping, disabling or weakening it; a failing or blocked check is reported as such.

## Clarification outcomes

None.
