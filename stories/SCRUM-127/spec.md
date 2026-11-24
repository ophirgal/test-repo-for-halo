# Feature Specification Document — SCRUM-127: A helper that doubles a number

> Status: final specification (READY_FOR_SPEC). The developer has told agents to make open decisions themselves rather than ask (product memory). The one gap in the story was a garbled function name, which the intake decoded and recorded as decision D1 in §8.

## 1. Feature Overview

**What is being built.** A new Python module, `src/testbed_utils/doubler.py`, with a function `double(n)` that returns `n * 2`, plus a pytest test file, `tests/test_doubler.py`, that checks it with positive, zero and negative integers.

**Problem.** This is a QA probe story (the title tag is `QA-20261124-N1`). It needs a small change that is easy to check, so the factory pipeline can be run from intake through to a reviewed pull request.

**Target user.** A developer in this repository who imports `double` from `testbed_utils.doubler`. The person reviewing the factory's output uses the pull request to confirm that the pipeline delivered exactly what was asked.

**What the repository has today** (`ophirgal/test-repo-for-halo`, target branch `main`, at `561d3c7`):
- `src/` holds only the `ledger` package. There is no `testbed_utils` package and no `doubler.py`.
- `pyproject.toml` finds packages under `src` (`[tool.setuptools.packages.find] where = ["src"]`), lists `pytest` as the `test` extra and sets `testpaths = ["tests"]`. `tests/test_ledger_parse.py` already uses pytest and imports from a `src` package (`from ledger import ...`). So a pytest test under `tests/` that imports a `src` package follows an existing pattern.
- The repository has no `CLAUDE.md`, no `AGENTS.md`, no `.factory/` folder and no CI workflow (no `.github/`). No repository gate or rule conflicts with this story.

## 2. Goals & Non-Goals

### Goals

- A function `double(n)` can be imported from `testbed_utils.doubler` and returns `n * 2` for integers.
- A pytest test in `tests/test_doubler.py` covers a positive, a zero and a negative input, and passes.

### Non-Goals

- Defining, validating or testing what happens with non-integer inputs (floats, `bool`, strings, `None`). The story asks only about integers. The function does not need to reject other types, and no criterion checks them.
- A command-line entry point, HTTP route, README section or any other user-facing surface for the helper.
- Changes to existing files (`src/ledger/`, `kvstore/`, `linkcheck/`, `serve.py`, existing tests, `pyproject.toml`), unless STRUCTURE finds a change is strictly needed to make the new package importable from the tests.
- Adding a CI workflow.

## 3. Functional Requirements

- FR1: The new module `src/testbed_utils/doubler.py` defines a function `double(n)`, which can be imported as `from testbed_utils.doubler import double`.
- FR2: For any integer `n`, `double(n)` returns `n * 2` as an `int`. Examples: `double(3) == 6`, `double(0) == 0`, `double(-4) == -8`.
- FR3: The new test file `tests/test_doubler.py` holds pytest tests that check `double` with at least one positive, one zero and one negative integer input.
- FR4: Running the repository's pytest suite (`python -m pytest`, which collects from `tests/` per `pyproject.toml`) runs the new tests, and they pass. The tests that already exist keep passing.
- Edge cases: zero and negative integers are covered by FR2 and FR3. Behaviour for non-integer inputs is out of scope (§2 Non-Goals).

## 4. User Experience & Behavior

- **Developer flow:** the developer imports `double` from `testbed_utils.doubler`, calls it with an integer and gets back twice that integer. There is no UI, no output format and no error message. The story names no look-and-feel or other sensory requirement.
- **Reviewer flow:** the reviewer opens the pull request. It adds `src/testbed_utils/doubler.py` and `tests/test_doubler.py`, plus whatever minimal files STRUCTURE decides the package needs (for example `src/testbed_utils/__init__.py`). The reviewer sees the new tests pass.

## 5. Acceptance Criteria

1. double(n) returns n * 2 for integers.
2. A pytest test under tests/ covers positive, zero and negative inputs.
3. The repository's existing tests still pass after the change, and no existing source file under src/ledger/, kvstore/, linkcheck/ or serve.py is modified.

## 6. Dependencies & Constraints (product-level)

- Depends on no other story or feature. Nothing else in the repository uses the helper.
- The location (`src/testbed_utils/doubler.py`) and test file (`tests/test_doubler.py`) come from the story and are fixed.
- Testing uses pytest, which is already declared as the `test` extra in `pyproject.toml`. The change adds no new runtime dependency.

## 7. Technical Design (deferred to STRUCTURE)

These are left to STRUCTURE:
- How `testbed_utils` becomes importable from `tests/`. The options are an `__init__.py` and/or the way pytest is run, the same way the tests already import `ledger`.
- The README says the suite runs with `python -m unittest discover -s tests`, which does not collect plain pytest-style test functions. STRUCTURE decides whether the PR evidence uses `python -m pytest` (as `pyproject.toml` configures) and whether the README needs a note. This does not change the product requirement.

## 8. Open Questions (if any remain)

**Decisions taken at intake**
- **D1 — Function name is `double(n)`.** The story as imported reads `double👎` in its description and criterion 1. Jira wiki markup renders the emoticon `(n)` as a thumbs-down icon, so the text the author wrote was `double(n)`: a function named `double` with one parameter `n`, matching "returns n * 2". Criterion 1 is restored to `double(n)`; its meaning is unchanged. *Risk:* low. If the author meant another name, only the function name changes.
- **D2 — Regression criterion added (criterion 3).** The story template asks every story to have a regression or scope-boundary check, so the intake added one: the existing tests still pass, and existing source files are untouched.

**Residual (non-blocking)**
- None at product level.

---

Why did the integer refuse to be doubled? It didn't want to be two-faced.

This spec doubled as a skateboard ramp: it's twice as smooth on the way down.
