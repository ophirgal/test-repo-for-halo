# High-Level Design — BENCH-2: Last-login line on the user profile page

## 1. System Overview

- **What is being built:** A sign-in recording side-effect on the existing `GET /` route and a new `GET /profile` HTML page that displays the previous sign-in timestamp (or a first-sign-in label).
- **Problem statement:** The customer portal epic requires a last-login display. This story delivers a self-contained proof-of-concept within the existing minimal Python HTTP server — no auth, no database, no locale handling.
- **Key responsibilities:** (1) Record every `GET /` visit as a UTC timestamp in `signins.json`; (2) Serve a dynamic `/profile` page showing the previous sign-in or "first sign-in"; (3) Preserve existing behavior and pass existing smoke tests.

## 2. Architecture Overview

- **Single component:** The existing `RootOnlyHandler` in `serve.py` is extended in-place. No new modules or services.
- **Boundary:** `serve.py` owns all HTTP handling and file I/O for `signins.json`. `smoke_test.py` owns all test assertions. `docs/index.html` is read-only.
- **External dependencies:** None beyond Python stdlib (`json`, `datetime` added to existing imports).

## 3. Data Flow Design

- **Recording flow (GET /):** Request → handler reads and serves `docs/index.html` (unchanged) → handler appends `datetime.now(UTC).isoformat()` timestamp to `signins.json` → response sent.
- **Profile flow (GET /profile):** Request → handler reads `signins.json` (or handles missing/corrupt file) → determines second-most-recent timestamp or first-sign-in label → renders HTML string → 200 response.
- **All other paths:** 404 (unchanged).
- **Persistence:** `signins.json` is a plain JSON array of ISO 8601 UTC strings on disk, surviving restarts.

## 4. Component Breakdown

| Component | Responsibility | Inputs / Outputs | Repository |
|---|---|---|---|
| Sign-in recorder | Append UTC timestamp to `signins.json` on every `GET /` | In: HTTP request to `/` · Out: timestamp appended to file | ophirgal/test-repo-for-halo |
| Profile page renderer | Read `signins.json`, determine last-login display, return HTML | In: HTTP request to `/profile` · Out: HTML response with "Demo User" + last-login line | ophirgal/test-repo-for-halo |
| Existing root handler | Serve `docs/index.html` on `GET /`, 404 otherwise | Unchanged | ophirgal/test-repo-for-halo |

## 5. Interface Contracts

- **GET /:** Returns 200 with Hello World HTML (unchanged response). Side-effect: appends one ISO 8601 UTC timestamp to `signins.json`.
- **GET /profile:** Returns 200 with HTML page containing "Demo User" heading and "Last login: ..." line.
- **signins.json schema:** `string[]` — a JSON array of ISO 8601 UTC timestamp strings (e.g. `["2026-10-26T14:30:00Z"]`). Created on first `GET /` if absent.
- **All other paths:** 404 (unchanged).

## 6. Key Technical Decisions

- **Flat JSON file over database:** Matches the demo's minimal constraints; no external dependencies.
- **UTC ISO 8601 only:** No locale/timezone conversion — simplifies implementation, matches spec non-goals.
- **Side-effect recording (not middleware):** Recording is inline in the `GET /` handler; the server has no middleware concept.
- **Corrupted file → treat as empty:** Defensive read avoids server crashes on bad data.
- **No concurrency protection:** Accepted limitation for single-user demo; documented in spec.

## 7. Risks & Constraints

| Risk | Severity | Mitigation |
|---|---|---|
| Race condition on `signins.json` with `ThreadingHTTPServer` | Low (accepted) | Single-user demo; spec explicitly accepts this |
| `signins.json` grows unbounded | Low (accepted) | Out of scope for demo |
| `signins.json` left in working tree after tests | Low | Test cleanup deletes the file; no `.gitignore` change needed |
| Import-time side effects break test imports | Medium | All I/O stays inside request handlers; path constants are inert `Path` objects |

## Build Order

Single ticket — sign-in recording, profile page, and tests are delivered together as one vertical slice.
