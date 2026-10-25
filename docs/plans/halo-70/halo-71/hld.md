# High-Level Design — HALO-71: יצירת קובץ shalom.txt עם המילה "שלום"

## 1. System Overview

- **What is being built:** A single text file (`shalom.txt`) containing the Hebrew word "שלום" in UTF-8 encoding, added to the repository root.
- **Problem statement:** The platform team needs to validate that the Halo PDLC can process a minimal Hebrew-language epic end-to-end.
- **Key responsibilities:** File creation with correct content and encoding; no regression to existing tests.

## 2. Architecture Overview

- **Components:** One static text file — no services, no modules, no runtime behavior.
- **Boundaries:** The file is inert; it is not served, imported, or referenced by any existing component (`serve.py` only serves `docs/index.html` at `/`).
- **External dependencies:** None.

## 3. Data Flow Design

- No data flow — this is a static file with no runtime interaction.

## 4. Component Breakdown

| Component | Responsibility | Repository |
|-----------|---------------|------------|
| `shalom.txt` | Contains the word "שלום" in UTF-8 | ophirgal/test-repo-for-halo |

## 5. Interface Contracts

- No APIs, events, or cross-repo contracts. The file is self-contained.

## 6. Key Technical Decisions

- **File placement:** Repository root — matches the precedent set by `hello_world.txt`.
- **Trailing newline:** Include a trailing newline (POSIX convention; most editors and `git diff` handle this cleanly). The spec requires the *content* to be solely "שלום"; a trailing newline is a file-format convention, not content.
- **Encoding:** UTF-8, producing an 8-byte Hebrew payload (each of the 4 characters is 2 bytes in UTF-8) plus the newline byte.

## 7. Risks & Constraints

| Risk | Severity | Mitigation |
|------|----------|------------|
| RK1 — Hebrew encoding in tooling | Low | Repo has no CI, linters, or formatters. Git handles UTF-8 natively. Smoke test does not reference the file. |
| RTL display in diffs | Cosmetic | Bytes are correct regardless of terminal rendering. |
