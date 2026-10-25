# Implementation Plan — HALO-71: יצירת קובץ shalom.txt עם המילה "שלום"

## Solution proposal

Create a single file `shalom.txt` at the repository root containing the Hebrew word "שלום" encoded in UTF-8, with a trailing newline. This mirrors the pattern established by the existing `hello_world.txt` (also at the repo root) with one deviation: the HLD specifies a trailing newline for POSIX compliance, whereas `hello_world.txt` lacks one. The HLD made this an explicit design decision; the plan follows it.

No existing files are modified. The file is inert — `serve.py` only serves `docs/index.html` at `/`, and `smoke_test.py` does not reference `shalom.txt`. The change surface is exactly one new file.

## Research findings

**Repository structure:**
- Root contains: `README.md`, `hello_world.txt`, `serve.py`, `smoke_test.py`, `docs/`, `stories/`.
- `hello_world.txt` contains `Hello World` (11 bytes, ASCII, no trailing newline).
- `serve.py` — root-only HTTP server that serves only `docs/index.html` at `/`; all other paths return 404.
- `smoke_test.py` — 28 HTTP smoke checks exercising `serve.py`. Tests routing (200 on `/`, 404 on everything else), content (greeting in `<main>`, `<title>`), viewport, HEAD method, query strings. Does not inspect arbitrary repo files.
- No CI pipeline (no `.github/workflows/`, no Makefile, no `package.json`).
- No linters, formatters, or pre-commit hooks.
- No `.factory/` directory, no `CLAUDE.md`, no `AGENTS.md`.

**Change surface:**
- Files created: `shalom.txt` (1 new file, 9 bytes: 8 bytes UTF-8 Hebrew + 1 byte newline).
- Files modified: none.
- Files deleted: none.
- Upstream/downstream impact: none. The server ignores files outside `docs/index.html`. The smoke test does not reference `shalom.txt`.

**Encoding detail:**
- "שלום" in UTF-8: `D7 A9` (ש), `D7 9C` (ל), `D7 95` (ו), `D7 9D` (ם) = 8 bytes.
- Plus trailing `0A` (newline) = 9 bytes total.
- Git handles UTF-8 natively; no `.gitattributes` or encoding configuration is needed.

**Existing test gate:**
- `python3 smoke_test.py` — the sole discoverable test command. Exits 0 on pass, 1 with FAIL lines on failure. Standard-library only, no external dependencies.

**Pre-existence check:**
- No `shalom.txt` exists in the repository (confirmed via file listing). The AC precondition is satisfied.

## Locked source decisions

1. The file is named `shalom.txt` (spec FR1, epic assumption).
2. The sole content is the word "שלום" — no additional text, headings, metadata, or markup (spec FR1).
3. Encoding is UTF-8 (spec FR2, epic RK1 mitigation).
4. File placement is at the repository root (HLD section 6, following `hello_world.txt` precedent).
5. A trailing newline is included (HLD section 6, POSIX convention; the spec defines "content" as solely "שלום" and treats the newline as a file-format convention, not content).
6. No new tests are written (spec non-goal, epic exclusion).
7. No existing files are modified (work-item AC #4).

## Assumptions

1. **The smoke test will continue to pass with `shalom.txt` present.** Evidence: `smoke_test.py` does not scan the repo root for files; it only tests HTTP routes on `serve.py`, which serves exactly one hardcoded path. Consequence if wrong: the test gate fails and the issue is immediately visible.
2. **No `.gitattributes` or encoding normalisation is needed.** Evidence: the repo has none currently, and Git preserves UTF-8 bytes verbatim by default. Consequence if wrong: the file's bytes would be altered on checkout, which `file` or `xxd` verification would catch.

## Ordered implementation tasks

### Task 1 — Create `shalom.txt` at the repository root

**Work item:** t1 — Create shalom.txt with Hebrew content at repo root.
**Advances AC:** AC1 (correct file with correct content), AC2 (UTF-8 encoding).

**Action:** Create the file `shalom.txt` at the repository root with the content `שלום` followed by a single newline character (`0A`). The file must be written in UTF-8. No BOM.

**File:** `shalom.txt` (new, 9 bytes).

**Verification:**
- Confirm the file exists at the repo root.
- Confirm byte content is exactly `D7 A9 D7 9C D7 95 D7 9D 0A` (e.g., via `xxd shalom.txt`).
- Confirm `file shalom.txt` reports UTF-8.

### Task 2 — Run the existing test gate

**Work item:** t1 (same — the work item includes gate verification as AC #3).
**Advances AC:** AC3 (existing tests do not break).

**Action:** Run `python3 smoke_test.py` from the repository root and confirm all 28 checks pass with exit code 0.

**Verification:**
- Output includes `OK: 28 checks passed`.
- Exit code is 0.
- No FAIL lines in output.

### Task 3 — Commit the change

**Work item:** t1.
**Advances AC:** AC4 (no existing files modified — verified by `git status` showing only the new file).

**Action:** Stage only `shalom.txt` and commit. Confirm `git status` shows no modified existing files — only the one new file.

## Files and modules touched

| File | Action | Reason |
|------|--------|--------|
| `shalom.txt` | Create (new) | Sole deliverable of the story |

No other files are created, modified, or deleted.

## Existing test layers

| Layer | Command | Checks | Covers this change? |
|-------|---------|--------|---------------------|
| HTTP smoke test | `python3 smoke_test.py` | 28 | Indirectly — confirms the new file does not regress server behavior |

No new test layer is required (explicit scope exclusion). No test layer gap to report — the acceptance criteria require only that existing tests pass, not that new coverage be added.

## Validation gate

The repository's canonical gate is:

```
python3 smoke_test.py
```

"Done" means: this command exits 0 with `OK: 28 checks passed` from a clean temporary worktree at the committed SHA. No CI pipeline exists to run — the smoke test is the sole gate.

Additionally, the implementer should verify encoding with `xxd shalom.txt` to confirm the exact byte sequence `D7 A9 D7 9C D7 95 D7 9D 0A`, satisfying AC2.

## Risks and scope guards

**Risks:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| RK1 — Hebrew encoding in tooling | Low | No CI, linters, or formatters exist. Git handles UTF-8 natively. Verified by `xxd` byte check and smoke test pass. |
| RTL display in diffs | Cosmetic | Bytes are correct regardless of terminal rendering direction. Not a functional risk. |

**Scope guards — the implement phase must NOT:**

- Write any new tests (explicit product-owner exclusion).
- Modify any existing file in the repository.
- Add content beyond the single word "שלום" (plus trailing newline).
- Add a BOM (byte order mark) to the file.
- Create CI configuration (no CI exists; none is required by the acceptance criteria).
- Create or modify `.factory/`, `.gitattributes`, or any configuration file.

## Clarification outcomes

No clarifications needed. All source decisions are locked and consistent with the repository state.
