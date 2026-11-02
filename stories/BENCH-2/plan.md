# Implementation Plan — BENCH-2: Last-login line on the user profile page

## Research findings

### Repository state

- **Server:** `serve.py` — a stdlib-only `ThreadingHTTPServer` with `RootOnlyHandler` (extends `BaseHTTPRequestHandler`). Routes: `GET /` serves `docs/index.html`, everything else returns 404. `do_HEAD` mirrors `do_GET` routing. No middleware, no auth, no sessions.
- **Tests:** `smoke_test.py` — 28 checks, all passing. Starts the server on an ephemeral port via `make_server("127.0.0.1", 0, QuietHandler)`, exercises the HTTP contract, then shuts down. `QuietHandler` subclasses `RootOnlyHandler` to silence logging.
- **Static page:** `docs/index.html` — minimal HTML with `<main><h1>Hello World</h1></main>`.
- **Dependencies:** Python stdlib only. No `requirements.txt`, no `pyproject.toml`.
- **Test gate:** `python3 smoke_test.py` — exits 0 on pass, 1 on failure. No CI pipeline, no `.factory/testing.md`.
- **Branch:** `halo/feat/bench-2` checked out.
- **No `.factory/` directory**, no `CLAUDE.md`, no `AGENTS.md`.

### Change surface

| File | Action | What changes |
|---|---|---|
| `serve.py` | Modify | Add `json`, `datetime` imports; add `SIGNINS` path constant; extend `do_GET` to record timestamps on `/` and serve `/profile`; add profile-rendering helper |
| `smoke_test.py` | Modify | Add test checks for sign-in recording, profile page (returning visitor, first sign-in, no sign-ins), `signins.json` cleanup |
| `docs/index.html` | None | Read-only, unchanged |
| `signins.json` | Runtime artifact | Created at runtime by `GET /`, never committed |

### Contracts and constraints

- The `_is_root()` check in `RootOnlyHandler` uses `urllib.parse.urlsplit(self.path).path == "/"`. The new `/profile` route must be added as a second path check in `do_GET` before the 404 fallback.
- `do_HEAD` must also route `/profile` (returning headers only) to stay consistent with the existing HEAD/GET parity pattern.
- `smoke_test.py` imports `serve`, `RootOnlyHandler`, and `make_server` by name. These must not be renamed or removed.
- Existing 404 checks in `smoke_test.py` test specific paths (`/index.html`, `/docs/index.html`, `/hello_world.txt`, `/README.md`, `/foo/bar`). None of these conflict with `/profile`.
- `SIGNINS` path constant must be `Path(__file__).resolve().parent / "signins.json"` (same directory as `serve.py`), matching the `INDEX` constant pattern.

### Resolved unknowns

- **Timestamp format:** UTC ISO 8601 with seconds (e.g. `2026-10-26T14:30:00+00:00`). Python's `datetime.now(datetime.timezone.utc).isoformat()` produces this.
- **"Previous sign-in" definition:** The second-most-recent entry in `signins.json` — the entry before the latest one.
- **Concurrency:** Not protected. Accepted limitation per spec and HLD.
- **Locale:** Not applicable. UTC English only.

## Solution proposal

Extend `RootOnlyHandler` in `serve.py` with two capabilities:

1. **Sign-in recording (side-effect on `GET /`):** After serving `docs/index.html`, read `signins.json` (or start with an empty list if missing/corrupt), append the current UTC ISO 8601 timestamp, and write back. The file is a JSON array of strings.

2. **Profile page (`GET /profile`):** Read `signins.json`, determine the display value: if fewer than two entries, show `Last login: first sign-in`; otherwise show `Last login: <second-most-recent timestamp>`. Return an HTML page with "Demo User" as a heading and the last-login line directly underneath.

The routing change is minimal: `do_GET` checks for `/profile` as a second explicit path (no dynamic routing), falling through to 404 for all other paths. `do_HEAD` mirrors the same routing.

Tests in `smoke_test.py` follow the existing `Checks` pattern — sequential HTTP requests with assertions. Tests must manage `signins.json` lifecycle (delete before/after test runs) to avoid cross-contamination with manual server usage.

No new files are created (aside from the runtime `signins.json`). No new dependencies. No changes to `docs/index.html`.

## Ordered implementation tasks

### Task 1 — Add sign-in recording to `GET /` (work item: t1)

**File:** `serve.py`

- Add imports: `import json` and `from datetime import datetime, timezone`.
- Add path constant: `SIGNINS = Path(__file__).resolve().parent / "signins.json"` (after the existing `INDEX` constant).
- In `do_GET`, after the existing `GET /` response is sent (after `self.wfile.write(body)`), append the current UTC timestamp to `signins.json`:
  - Read existing array from `SIGNINS` (empty list on `FileNotFoundError` or `json.JSONDecodeError`).
  - Append `datetime.now(timezone.utc).isoformat()`.
  - Write the updated array back to `SIGNINS`.
- The Hello World HTML response must be identical to current behavior — the recording is a post-response side-effect.

**Advances:** AC 4 (sign-in recording), AC 5 (backward compatibility), AC 6 (persistence).

### Task 2 — Add `/profile` route with last-login display (work item: t1)

**File:** `serve.py`

- Extract the path from `self.path` using the existing `urlsplit` pattern. Add a helper `_parsed_path()` returning `urllib.parse.urlsplit(self.path).path` (or inline the check).
- In `do_GET`, add a branch for `/profile` before the 404 fallback:
  - Read `signins.json` (empty list on missing/corrupt).
  - If fewer than 2 entries: `last_login = "first sign-in"`.
  - Otherwise: `last_login = entries[-2]` (second-most-recent).
  - Build an HTML string with "Demo User" heading and `Last login: {last_login}` line directly under it.
  - Send 200 with `Content-Type: text/html; charset=utf-8`.
- In `do_HEAD`, add the same `/profile` branch (send headers only, no body).
- Restructure `do_GET` routing: check `path == "/"` → serve index + record; check `path == "/profile"` → serve profile; else → 404.

**Advances:** AC 1 (returning visitor), AC 2 (first sign-in), AC 3 (no sign-ins), AC 4 (visibility).

### Task 3 — Add test checks for the new behavior (work item: t1)

**File:** `smoke_test.py`

- Add `signins.json` cleanup: delete the file before `run_checks` starts and after it finishes (in a `finally` block), to prevent cross-contamination.
- Add checks in `run_checks`, after the existing checks:
  1. **No sign-ins → first sign-in:** `GET /profile` before any `GET /` → response contains "Demo User" and "Last login: first sign-in".
  2. **Single sign-in → first sign-in:** `GET /` once, then `GET /profile` → still "Last login: first sign-in" (only one entry).
  3. **Returning visitor:** `GET /` a second time, then `GET /profile` → "Last login:" followed by a timestamp (not "first sign-in").
  4. **Sign-in recording:** After the `GET /` calls above, verify `signins.json` exists and contains a JSON array with the expected number of entries.
  5. **Backward compatibility recheck:** `GET /` still returns 200 with "Hello World" after all profile checks.
  6. **404 on non-routed paths:** Existing 404 checks already cover this; no change needed.
- Import `json` and `Path` in `smoke_test.py` for `signins.json` assertions.
- Determine `SIGNINS` path relative to `serve.py`'s location (import from `serve` or compute independently).

**Advances:** AC 7 (new test coverage), AC 5 (existing tests pass).

## Files and test layers

| File | Role | Test layer |
|---|---|---|
| `serve.py` | Production code — HTTP handler | `smoke_test.py` (integration — real HTTP requests) |
| `smoke_test.py` | Test code | Self-verifying (exit code) |
| `docs/index.html` | Static asset (unchanged) | Covered by existing smoke checks |
| `signins.json` | Runtime data (never committed) | Managed by test cleanup |

**Existing test layer:** `smoke_test.py` — integration tests using real HTTP requests against an ephemeral server. No unit test layer exists; no new layer is invented.

## Verification

The test gate must show:

```
python3 smoke_test.py
```

Exit 0, all checks passed (existing 28 + new checks for sign-in recording and profile page). Specifically:

| # | Check | Criterion |
|---|---|---|
| 1 | `GET /profile` with no prior sign-ins shows "Last login: first sign-in" | AC 2, AC 3 |
| 2 | `GET /profile` after one `GET /` shows "Last login: first sign-in" | AC 2 |
| 3 | `GET /profile` after two+ `GET /` shows a timestamp (not "first sign-in") | AC 1 |
| 4 | `GET /` appends a timestamp to `signins.json` | AC 4 |
| 5 | `GET /` still returns 200 with "Hello World" | AC 5 |
| 6 | All 28 existing checks still pass | AC 5, AC 6 |
| 7 | `signins.json` cleaned up after tests | AC 7 |

No CI pipeline exists; verification is `python3 smoke_test.py` from the repository root.

## Risks and scope guards

| Risk | Severity | Mitigation |
|---|---|---|
| Race condition on `signins.json` under `ThreadingHTTPServer` | Low (accepted) | Single-user demo; spec and HLD explicitly accept this |
| `signins.json` grows unbounded | Low (accepted) | Out of scope per spec |
| Test ordering dependency (checks rely on cumulative `GET /` state) | Low | Tests run in a deterministic sequence within a single `run_checks` call; cleanup before and after |
| `signins.json` left on disk after manual server use | Low | Not committed (not in the repo tree by default); test cleanup handles the test path |

**Scope guards — the implement phase must NOT:**

- Change the sign-in flow (no new prompts, redirects, or delays on `GET /`).
- Create a new API endpoint (JSON). `/profile` is HTML only.
- Add authentication, sessions, cookies, or multi-user support.
- Add locale or timezone conversion — UTC ISO 8601 only.
- Add external dependencies — stdlib only.
- Modify `docs/index.html`.
- Commit `signins.json`.
- Create or modify CI pipelines.

## Clarification outcomes

No clarifications needed. All requirements are fully specified in the approved spec and HLD, and the repository's current state confirms every precondition.
