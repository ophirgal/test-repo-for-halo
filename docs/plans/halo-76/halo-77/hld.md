# High-Level Design — HALO-77: Console Quiz Script

## 1. System Overview

A single-file Python console application that presents a three-topic menu in Hebrew, accepts user input, handles invalid selections with a retry loop, and displays one hardcoded question for the chosen topic. The script is fully standalone — no imports beyond builtins, no interaction with existing repo code.

## 2. Architecture Overview

- **Single component:** one Python script (`quiz.py`) at the repo root.
- **No services, no modules, no packages.** The script uses `input()` and `print()` only.
- **No integration points** with `serve.py`, `smoke_test.py`, or any other existing file.
- **One new metadata file:** `pyproject.toml` at the repo root, declaring `requires-python >= "3.10"` per Engineering R1.

## 3. Data Flow Design

1. Script starts → prints Hebrew menu with three numbered topics.
2. `input()` captures user text.
3. If input matches a valid option → look up question from a dict → `print()` the question → exit.
4. If input is invalid (including empty) → `print()` error message in Hebrew → loop back to step 2.

All data is in-memory, hardcoded. No files read, no network, no persistence.

## 4. Component Breakdown

| Component | Responsibility | Repository |
|---|---|---|
| `quiz.py` | Menu display, input loop, question lookup, output | ophirgal/test-repo-for-halo |
| `pyproject.toml` | Declare `requires-python >= "3.10"` | ophirgal/test-repo-for-halo |

## 5. Interface Contracts

None. The script has no API, no events, no cross-repo contracts. Its only interface is stdin/stdout in a terminal.

## 6. Key Technical Decisions

- **Numeric selection (1/2/3):** avoids Hebrew input parsing, RTL issues, and whitespace sensitivity. The spec leaves the mechanism to implementation.
- **All user-facing text in Hebrew:** consistent with the PRD and spec's strong default.
- **No imports:** `input()`, `print()`, `dict` are builtins. Zero import lines needed.
- **Minimal `pyproject.toml`:** only `[project]` with `name`, `version`, `requires-python`. No build system, no dependencies, no entry points.

## 7. Risks & Constraints

- **Scope creep (RK1):** mitigated by the spec's explicit out-of-scope list. The ticket's acceptance criteria enforce the boundary.
- **RTL terminal rendering:** a terminal concern, not a code concern. `print()` outputs correct bytes; display is the terminal's job.
- **No CI:** Engineering R3 is vacuously satisfied. Manual verification is sufficient for this story.
