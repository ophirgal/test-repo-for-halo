# High-Level Design — HALO-75: הוספת קובץ שלום בעברית לשורש המאגר

## 1. System Overview

- **What is being built:** A single static text file (`shalom.txt`) containing the Hebrew word "שלום", placed at the repository root.
- **Problem statement:** The team has no artifact to prove the distribution pipeline handles Hebrew (RTL, multi-byte UTF-8) content correctly.
- **Key responsibilities:** The file serves as a validation artifact — its mere presence and correct encoding prove Hebrew support.

## 2. Architecture Overview

- **Components:** One static file; no services, modules, or code.
- **Boundaries:** The file is inert — it is not read, imported, or served by any component (`serve.py` serves only `docs/`; `smoke_test.py` tests HTTP responses, not disk files).
- **Ownership:** Owned entirely within `ophirgal/test-repo-for-halo`.
- **External dependencies:** None.

## 3. Data Flow Design

- No runtime data flow. The file is a static asset committed to version control.
- The only "flow" is: commit → push → PR → merge → file visible in main branch.

## 4. Component Breakdown

| Component | Responsibility | Inputs / Outputs | Repository |
|---|---|---|---|
| `shalom.txt` | Carry the Hebrew word "שלום" in valid UTF-8 | None → 8-byte file on disk | ophirgal/test-repo-for-halo |

## 5. Interface Contracts

- No APIs, no events, no cross-repo contracts. The file is consumed only by human viewers and standard text tools.

## 6. Key Technical Decisions

- **UTF-8 without BOM:** Matches the repo's existing encoding convention (`docs/index.html` declares `charset=utf-8`) and avoids BOM-related tool quirks.
- **No trailing newline:** Matches the precedent set by `hello_world.txt` (11 bytes, no terminator). The file is exactly 8 bytes.
- **No automated content tests:** Explicitly excluded by the product owner. Encoding is verified manually before opening the PR.

## 7. Risks & Constraints

- **RK1 — Encoding corruption:** If the file is written in a non-UTF-8 encoding, Hebrew characters render as garbled text. Mitigation: verify the exact byte sequence (D7 A9 D7 9C D7 95 D7 9D) before committing.
- **No CI pipeline files:** The repo has no `.github/workflows/` or CI config. "CI compliance" means `python3 smoke_test.py` passes locally; the PR does not need to wait for a remote CI runner.

## Build order

Single ticket, no dependencies. One PR, one commit.
