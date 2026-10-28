# Implementation Plan — HALO-77

## Context

Story HALO-77 delivers a minimal Python console quiz application for epic HALO-76. The script presents a three-topic menu in Hebrew (ספורט, פוליטיקה, פסיכולוגיה), accepts a numeric selection, handles invalid input with a retry loop, and displays one hardcoded question for the chosen topic. Two new files are created at the repository root: `quiz.py` and `pyproject.toml`. The change lands in `ophirgal/test-repo-for-halo` on branch `halo/feat/halo-77`. The planning inputs (`spec.md`, `hld.md`, `work-items.md`) sit in `docs/plans/halo-76/halo-77/` alongside this file.

## Research findings

**Repository layout.** The repo root contains `serve.py` (an HTTP server for a Hello World page, KAN-8), `smoke_test.py` (its smoke tests), `hello_world.txt`, `README.md`, and `docs/` (HTML page + plans). No `pyproject.toml`, no `.factory/`, no `CLAUDE.md`, no `AGENTS.md`, no `requirements.txt`, no `test/` directory.

**Change surface.** Two new files at the repo root:
- `quiz.py` (new) — the entire console application.
- `pyproject.toml` (new) — minimal project metadata.

No existing file is modified. `quiz.py` has no interaction with `serve.py`, `smoke_test.py`, or any other existing file.

**Existing test layers.** `smoke_test.py` at repo root tests `serve.py` via `import serve`. It is independent of `quiz.py` and will remain unaffected. There is no Harel merge-request pipeline (`Jenkinsfile-TestOnMergeRequest`), no `test/` directory, and no `requirements.txt`. The repo follows no Harel `test/` convention; existing tests live at the root. Automated tests for `quiz.py` are explicitly out of scope per PO decision (spec.md §2 Non-Goals).

**Canonical gate.** No `.factory/testing.md` exists. The discoverable gate is `python smoke_test.py` (or `python -m pytest` if pytest were installed, but there is no `requirements.txt`). The existing `smoke_test.py` is the only automated verification; it covers `serve.py` only.

**No external dependencies.** The script uses only Python builtins (`input`, `print`, `dict`). No imports are needed.

**No unknowns remain.** The exact question text is unspecified but is trivial content with low risk (spec.md §8). Three reasonable Hebrew questions will be authored by the implementer.

## Locked decisions and assumptions

**Locked decisions:**
- Three topics exactly: ספורט, פוליטיקה, פסיכולוגיה (spec.md FR1, hld.md §6).
- One hardcoded question per topic, three total (spec.md FR3, FR6).
- Numeric selection mechanism (1/2/3) — approved in hld.md §6.
- Invalid input triggers a Hebrew error message and retry without restart (spec.md FR4).
- Console-only, standard library only, no GUI, no external packages (spec.md FR5).
- `pyproject.toml` declares `requires-python >= "3.10"` with `[project]` containing `name`, `version`, `requires-python` only (hld.md §6, spec.md §6).
- All user-facing text in Hebrew (spec.md §4, hld.md §6).
- No automated tests (spec.md §2 Non-Goals, PO decision).

**Assumptions:**
- The three Hebrew questions will be authored by the implementer as reasonable, topically appropriate content. *Evidence:* spec.md §8 leaves question text to the developer. *If wrong:* the PO provides specific text and a minor rewrite is needed.
- `pyproject.toml` uses `name = "quiz"` and `version = "0.1.0"`. *Evidence:* hld.md §6 specifies minimal metadata; no other name or version is mandated. *If wrong:* a one-line edit.

## Solution proposal

Create two new files at the repo root — `quiz.py` and `pyproject.toml` — with no modifications to any existing file.

`quiz.py` implements a `while True` loop: print the numbered Hebrew menu, read input via `input()`, validate against the three valid keys (`"1"`, `"2"`, `"3"`), and either print the corresponding question from a `dict` and exit, or print a Hebrew error message and loop. The questions dict maps each key to a single Hebrew string. The script is guarded by `if __name__ == "__main__":` so it can be imported without side effects if needed later.

`pyproject.toml` contains a minimal `[project]` table with `name`, `version`, and `requires-python`.

The numeric-selection approach (from hld.md) avoids Hebrew input parsing, RTL whitespace issues, and case sensitivity. The `while True` loop satisfies the indefinite-retry requirement. No imports are needed — `input()`, `print()`, and `dict` are builtins.

No alternative was considered: the HLD already chose the single-file, numeric-selection, builtin-only design. The plan follows it without deviation.

## Ordered implementation steps

1. **Create `pyproject.toml` at the repo root.** Declare `[project]` with `name = "quiz"`, `version = "0.1.0"`, `requires-python = ">= 3.10"`. No `[build-system]`, no dependencies, no entry points. Advances AC 8. No existing test layer covers this file.

2. **Create `quiz.py` at the repo root.** Implement the full script:
   - Define a `dict` mapping `"1"` → a Hebrew sports question, `"2"` → a Hebrew politics question, `"3"` → a Hebrew psychology question (three distinct, topically appropriate questions). Advances AC 3, AC 9.
   - In a `main()` function guarded by `if __name__ == "__main__":`, implement a `while True` loop that:
     - Prints the Hebrew menu header and three numbered topic lines (ספורט, פוליטיקה, פסיכולוגיה). Advances AC 1.
     - Reads input via `input()`.
     - On valid input (`"1"`, `"2"`, `"3"`): prints the corresponding question and exits. Advances AC 2.
     - On any other input (including empty): prints a Hebrew error message and continues the loop. Advances AC 4, AC 5, AC 6.
   - Use no imports — only builtins. Advances AC 7.

3. **Manual verification.** Run `python quiz.py` and exercise:
   - Each of the three valid selections to confirm correct question output.
   - Invalid input (e.g., `"4"`, `"abc"`) to confirm error + retry.
   - Empty input (bare Enter) to confirm error + retry.
   - Confirm all displayed text is in Hebrew.

## Work-item mapping

| Step | Work item | Title |
|------|-----------|-------|
| 1 | t1 | HALO-77: Console quiz script and pyproject.toml |
| 2 | t1 | HALO-77: Console quiz script and pyproject.toml |
| 3 | t1 | HALO-77: Console quiz script and pyproject.toml |

All steps belong to the single work item. No planning gap.

## Verification and CI gate

**Canonical gate.** No `.factory/testing.md` defines a `test-gate:`. The discoverable gate is `python smoke_test.py`, which tests `serve.py` only. It must still pass after the change — `quiz.py` is independent and does not affect it.

**Required test layers.** None for `quiz.py` — automated tests are explicitly out of scope. The existing `smoke_test.py` is the regression layer for `serve.py`.

**Provider CI.** No CI pipeline exists in the repo (no GitHub Actions workflow, no `Jenkinsfile-TestOnMergeRequest`). None is required by this story.

**Gate pass criteria:**
- `python smoke_test.py` exits 0 (existing regression).
- `python -c "import quiz"` exits 0 (the script is importable without side effects).
- `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` confirms valid TOML (Python 3.11+; or manual inspection on 3.10).
- Manual exercise of `quiz.py` confirms all four acceptance scenarios from the spec.

## Risks and scope guards

**Risks:**
- *Question text quality.* The three questions are authored by the implementer. Mitigation: any reasonable, topically appropriate Hebrew question satisfies the AC. The PO can revise text in a follow-up if desired.
- *RTL terminal rendering.* Hebrew text may render differently across terminals. Mitigation: `print()` outputs correct UTF-8 bytes; display is the terminal's responsibility (hld.md §7). No code-level mitigation exists or is needed.

**Scope guards — the implement phase must NOT:**
- Modify `serve.py`, `smoke_test.py`, `hello_world.txt`, `docs/index.html`, or any existing file.
- Add more than one question per topic or more than three topics.
- Add scoring, answer tracking, or response evaluation.
- Add external package dependencies or imports beyond builtins.
- Add a GUI or web interface.
- Create automated tests for `quiz.py`.
- Create or modify CI configuration.
- Delete, skip, disable, or weaken `smoke_test.py` or any existing check.

## Clarification outcomes

None.
