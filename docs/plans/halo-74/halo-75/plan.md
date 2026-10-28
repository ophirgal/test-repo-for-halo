# Implementation Plan — HALO-75: הוספת קובץ שלום בעברית לשורש המאגר

## Context

Story HALO-75 adds a single static text file, `shalom.txt`, to the root of `ophirgal/test-repo-for-halo` (branch `halo/feat/halo-75`). The file contains the Hebrew word "שלום" in UTF-8 with no BOM and no trailing newline, validating that the distribution pipeline handles Hebrew content correctly. The acceptance criteria require the file to exist with correct content and encoding, and the PR to pass all CI checks and carry traceability to the story and epic PRD. The sibling planning documents (`spec.md`, `hld.md`, `work-items.md`) sit in `docs/plans/halo-74/halo-75/` beside this file.

## Research findings

**Repository layout (root):**

| File | Purpose |
|---|---|
| `hello_world.txt` | 11-byte ASCII file, content "Hello World", no trailing newline — the precedent for `shalom.txt` |
| `serve.py` | Root-only HTTP server; serves only `docs/index.html` at `/`; does not serve root text files |
| `smoke_test.py` | HTTP smoke tests for `serve.py`; starts a server on an ephemeral port and checks routes, status codes, content |
| `docs/index.html` | The served page; declares `<meta charset="utf-8">` — establishes UTF-8 as the repo's encoding convention |
| `README.md` | Repository readme |
| `docs/.nojekyll` | GitHub Pages config |

**Change surface:** One new file at root (`shalom.txt`). No existing file is modified. No code, no imports, no APIs, no schemas touched.

**Existing test gate:** `python3 smoke_test.py` (`smoke_test.py:1–222`). The test starts `serve.py` on port 0, exercises HTTP routes (`/` → 200, non-root paths → 404), checks content, viewport meta, title, and recovery after 404s. It does not scan disk files or check for the existence of `hello_world.txt` or any other root file. A new static file at root cannot affect any test assertion.

**CI configuration:** No `.github/workflows/`, no `Jenkinsfile-*`, no `.factory/testing.md`, no `requirements.txt`. The repo has no provider-visible CI pipeline. "CI compliance" means `python3 smoke_test.py` passes locally (confirmed by `hld.md`).

**UTF-8 byte sequence for "שלום":** `D7 A9 D7 9C D7 95 D7 9D` — 8 bytes, verified via `printf 'שלום' | xxd`. This matches the HLD's specification (`hld.md:39`).

**Encoding precedent:** `hello_world.txt` is `us-ascii` (a strict subset of UTF-8); `docs/index.html:4` declares `charset=utf-8`. UTF-8 is the established convention.

**No `.factory/` directory, no `AGENTS.md`, no `CLAUDE.md`, no `.factory/memory/`.**

## Locked decisions and assumptions

**Locked decisions:**

- File name is `shalom.txt` at repository root (`spec.md` FR1, `hld.md:25`).
- Content is exactly "שלום" — the 8-byte UTF-8 sequence `D7 A9 D7 9C D7 95 D7 9D` (`spec.md` FR2–FR3, `hld.md:34`).
- No BOM (`spec.md:42`, `hld.md:33`).
- No trailing newline — matches `hello_world.txt` precedent (`hld.md:34`).
- No automated content tests for the file (`spec.md` Non-Goals, `work-items.md` AC).
- PR body references HALO-75 and the epic PRD (`spec.md` FR5).

**Assumptions:**

- The `file` command on the build agent reports `utf-8` for an 8-byte Hebrew-only file. Evidence: `file --mime-encoding` on standard systems classifies valid multi-byte UTF-8 as `utf-8`. Consequence if wrong: the encoding verification step reports a different label (e.g. `binary`), but the byte content is still correct; verification falls back to `xxd` comparison.

## Solution proposal

Create a single file `shalom.txt` at the repository root containing the 8-byte UTF-8 string "שלום" with no BOM and no trailing newline, mirroring the `hello_world.txt` pattern. The file is written with explicit UTF-8 encoding to mitigate RK1 (encoding corruption). Before committing, verify the exact byte sequence with `xxd` and confirm `python3 smoke_test.py` passes. This is the minimal change that satisfies all acceptance criteria — one new inert file, no code, no test changes, no configuration changes.

No alternatives were considered; the spec, HLD, and work-items are unanimous on approach and there is no design decision to make.

## Ordered implementation steps

1. **Create `shalom.txt` at repository root.** Write the file with content "שלום" (UTF-8, no BOM, no trailing newline). The file is 8 bytes: `D7 A9 D7 9C D7 95 D7 9D`. Advances AC scenario 1 (file exists with correct content) and AC scenario 2 (encoding supports Hebrew). Files: `shalom.txt` (new). No existing test layer covers this file (by design — product owner excluded content tests); verification is manual byte-level inspection.

2. **Verify encoding.** Run `xxd shalom.txt` and confirm the output is exactly `d7a9 d79c d795 d79d` (8 bytes). Run `file --mime-encoding shalom.txt` and confirm it reports `utf-8`. Advances AC scenario 2. No test layer — manual verification.

3. **Run the existing test gate.** Execute `python3 smoke_test.py` from the repository root and confirm exit code 0 with all checks passing. Advances AC scenario 3 (PR passes checks). Test layer: `smoke_test.py:200–222` (`main()`). The new file is inert and cannot affect any assertion, but the gate must be green.

4. **PR traceability.** The platform opens the PR; its body must reference story HALO-75 and the epic PRD ("אפיק בדיקה בעברית — מסמך אפיון", Confluence page ID 20938753). Advances AC scenario 3 (traceability). No test layer.

## Work-item mapping

| Step | Work item ref | Work item title |
|---|---|---|
| 1 | t1 | Add shalom.txt with Hebrew content to repository root |
| 2 | t1 | Add shalom.txt with Hebrew content to repository root |
| 3 | t1 | Add shalom.txt with Hebrew content to repository root |
| 4 | t1 | Add shalom.txt with Hebrew content to repository root |

All steps belong to the single work item `t1`. No planning gap.

## Verification and CI gate

**Canonical gate:** `python3 smoke_test.py` from the repository root. There is no `.factory/testing.md` and no provider CI pipeline; this is the only gate.

**Gate must show:** Exit code 0, all existing checks pass (currently 20+ assertions covering HTTP status codes, content, headers, viewport, 404 handling, and recovery). The new file does not interact with any tested path.

**Layers that cannot run in a pod:** None. The smoke test uses only the standard library and localhost HTTP — no network, no external dependencies, no browser.

**Provider CI:** Not applicable — the repo has no `.github/workflows/` or other CI configuration. The HLD (`hld.md:41`) confirms no remote CI runner is needed.

**`.factory/testing.md`:** Not applicable — no CI pipeline is being added or changed.

**`.factory/delivery-assets`:** Not applicable — the new file is 8 bytes.

## Risks and scope guards

**Risks:**

| Risk | Mitigation |
|---|---|
| RK1 — File saved in wrong encoding, Hebrew renders as garbled text | Write with explicit UTF-8 encoding; verify exact byte sequence `D7 A9 D7 9C D7 95 D7 9D` with `xxd` before committing |
| Editor or tool inserts a BOM or trailing newline | Verify file size is exactly 8 bytes after writing |

**Scope guards — the implement phase must NOT:**

- Modify any existing file (`hello_world.txt`, `serve.py`, `smoke_test.py`, `docs/index.html`, `README.md`, or anything else).
- Add automated tests for `shalom.txt` (explicitly excluded by the product owner).
- Add code that reads or processes `shalom.txt`.
- Create or modify CI configuration (`.github/workflows/`, `.factory/testing.md`).
- Create or modify anything under `.factory/`.
- Make the smoke test gate green by deleting, skipping, disabling, or weakening any check.

## Clarification outcomes

None.
