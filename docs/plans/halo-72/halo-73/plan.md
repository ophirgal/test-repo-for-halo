# Implementation Plan — HALO-73

## Context

Story HALO-73 adds a single file `shalom.txt` to the root of `ophirgal/test-repo-for-halo` containing exactly the Hebrew word "שלום" (UTF-8, no BOM, no trailing newline). The change validates that the PDLC system handles a Hebrew-authored initiative end-to-end. Acceptance criteria: (AC1) the file exists at root with byte-exact content after merge, (AC2) no existing file is modified or removed and no extra file is added. The work lands on branch `halo/feat/halo-73`. Planning inputs (`spec.md`, `hld.md`, `work-items.md`) sit beside this file in `docs/plans/halo-72/halo-73/`.

## Research findings

- **Repository root contents**: `hello_world.txt`, `smoke_test.py`, `serve.py`, `README.md`, `docs/`, `stories/`. No file named `shalom.txt` exists — risk RK1 is clear.
- **Encoding convention**: `hello_world.txt` is 11 bytes (`Hello World`), UTF-8, no trailing newline, no BOM. The new file follows the same convention.
- **Test gate**: `smoke_test.py` exercises `serve.py` via `python3 smoke_test.py`. No `.factory/testing.md`, no Makefile, no `package.json`, no `pyproject.toml`. The discoverable gate is `python3 smoke_test.py`.
- **CI**: No `.github/workflows/` directory. No provider CI pipeline exists.
- **Repo contracts**: No `AGENTS.md`, `CLAUDE.md`, `.factory/` directory, or `.factory/memory/`.
- **Change surface**: One new file at repo root (`shalom.txt`). Zero modifications to existing files. The smoke test exercises `serve.py` routes and does not reference `shalom.txt`, so it is unaffected.

## Locked decisions and assumptions

**Locked decisions:**

- File name is `shalom.txt` at the repository root (spec FR1; hld §6).
- Content is exactly the four Hebrew characters שלום — UTF-8 code points U+05E9 U+05DC U+05D5 U+05DD — totaling 8 bytes (`D7 A9 D7 9C D7 95 D7 9D`), no BOM, no trailing newline (spec FR2; hld §6).
- No existing file may be modified, deleted, or removed (spec FR4; AC2).
- No file other than `shalom.txt` may be added (spec FR5; AC2).
- PR must reference HALO-73 and HALO-72 (spec FR3) — platform-owned; not an implement concern.

**Assumptions:**

- The existing smoke test (`python3 smoke_test.py`) will continue to pass unchanged, because it exercises only `serve.py` routes and does not inspect the repo file listing. Evidence: `smoke_test.py:22-28` hard-codes its probe paths and none reference `shalom.txt`. Consequence if wrong: the smoke test fails unexpectedly and the gate is red, requiring investigation.

## Solution proposal

Write `shalom.txt` using a byte-exact method (e.g. `printf` piping the raw UTF-8 bytes, or Python `open(..., 'wb').write(...)`) to guarantee no editor auto-appends a trailing newline or BOM. Verify the result with `xxd` to confirm exactly 8 bytes matching `D7 A9 D7 9C D7 95 D7 9D`. This is the minimal change: one new file, zero modifications.

Alternative considered: creating the file with a text editor or `echo`. Rejected because `echo` appends `\n` by default and editors may insert a BOM or trailing newline, violating FR2.

## Ordered implementation steps

1. **Create `shalom.txt` at repo root with byte-exact content.** Write the 8 bytes `D7 A9 D7 9C D7 95 D7 9D` to `shalom.txt` using a method that prevents trailing newline or BOM insertion (e.g. `printf '\xD7\xA9\xD7\x9C\xD7\x95\xD7\x9D' > shalom.txt`). Advances AC1. No existing test layer covers this file; the spec explicitly excludes automated tests for it.

2. **Verify byte-exact content.** Run `xxd shalom.txt` and confirm output is exactly `D7 A9 D7 9C D7 95 D7 9D` (8 bytes, no BOM prefix, no trailing `0A`). Advances AC1.

3. **Run the existing gate.** Execute `python3 smoke_test.py` to confirm no regression. Advances AC2 (no existing file behavior changed).

4. **Commit.** Stage only `shalom.txt` (`git add shalom.txt`) and commit. The platform pushes and opens the PR.

## Work-item mapping

| Step | Work item | Title |
|------|-----------|-------|
| 1 | t1 | Add shalom.txt with Hebrew content to repo root |
| 2 | t1 | Add shalom.txt with Hebrew content to repo root |
| 3 | t1 | Add shalom.txt with Hebrew content to repo root |
| 4 | t1 | Add shalom.txt with Hebrew content to repo root |

## Verification and CI gate

The repository's discoverable gate is `python3 smoke_test.py`. No `.factory/testing.md` or provider CI pipeline exists; the spec explicitly excludes automated tests for the new file.

**Gate must show:** `python3 smoke_test.py` exits 0 with all checks passed. The committed tree contains exactly one new file (`shalom.txt`) and zero modified files, confirmed by `git diff --stat` against the base branch.

**Byte verification:** `xxd shalom.txt` produces exactly `d7a9 d79c d795 d79d` (8 bytes). This is a manual verification step, not a CI layer.

No new CI pipeline, `.factory/testing.md`, or `.factory/delivery-assets` is required — the file is 8 bytes of text, well under any threshold.

## Risks and scope guards

**Risks:**

| Risk | Mitigation |
|------|------------|
| Editor or tool appends trailing newline or BOM | Use byte-exact write method; verify with `xxd` before committing |
| File name collision (RK1) | Confirmed: `shalom.txt` does not exist on the branch or `main` |

**Scope guards — the implement phase must NOT:**

- Modify, delete, or rename any existing file (`hello_world.txt`, `smoke_test.py`, `serve.py`, `README.md`, `docs/`, `stories/`).
- Add any file other than `shalom.txt`.
- Add automated tests for `shalom.txt` (explicitly out of scope per the spec).
- Create or modify CI pipelines, `.factory/` files, or build manifests.
- Weaken or skip the existing `python3 smoke_test.py` gate.

## Clarification outcomes

None.
