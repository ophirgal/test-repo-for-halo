# Feature Specification Document

## 1. Feature Overview

**Summary:** Add a "Last login" line to a new `/profile` page in the existing Python HTTP server, showing the date and time of the demo user's previous visit to the root page (`/`). Each `GET /` is recorded as a "sign-in" in a JSON file (`signins.json`) stored alongside the server. The profile page displays the previous sign-in timestamp in UTC ISO 8601 format, or "Last login: first sign-in" when no previous visit exists.

**Problem statement:** The customer portal epic requires a last-login display feature. The target repository contains only a minimal Python HTTP server with a static Hello World page. This re-scoped story delivers a self-contained, minimal proof-of-concept of the last-login pattern within the existing server, without requiring authentication, a database, or locale infrastructure.

**Target users / actors:** Any visitor to the demo server, treated as a single hardcoded "Demo User." There is no authentication; all visitors share the same sign-in record.

---

## 2. Goals & Non-Goals

### Goals

- Display a "Last login" line on a new `/profile` page showing the previous sign-in timestamp.
- Record each visit to `GET /` as a sign-in event, persisted across server restarts.
- Handle the first-sign-in case with a clear label.
- Preserve the existing Hello World page behavior and pass existing smoke tests.

### Non-Goals

- **Authentication or sessions** — no login flow, no user identity, no cookies.
- **Multiple users** — one hardcoded demo user; all visitors share the same record.
- **Database** — sign-in records are stored in a flat JSON file, not a database.
- **Locale or time zone handling** — all timestamps are UTC only, ISO 8601 format.
- **Login history list** — only the single most recent previous sign-in is shown.
- **Alerts or notifications** on suspicious activity.
- **Admin views** of user login data.
- **New API endpoints** — `/profile` is an HTML page, not a JSON API.
- **Changes to the sign-in flow** — `GET /` continues to serve the Hello World page; sign-in recording is a transparent side effect.

---

## 3. Functional Requirements

- **FR1: Sign-in recording.** Every `GET /` request appends a UTC ISO 8601 timestamp to a JSON file (`signins.json`) located in the same directory as the server. The file is created automatically on the first `GET /` if it does not exist. The Hello World HTML response is unaffected — the recording is a side effect, not a change to the response.

- **FR2: Profile page.** A new `GET /profile` route returns an HTML page displaying:
  - The user's name: "Demo User" (hardcoded).
  - A "Last login" line directly under the name.

- **FR3: Last-login display — returning visitor.** When `signins.json` contains two or more timestamps, the "Last login" line shows the second-most-recent timestamp (the visit before the latest one). Format: `Last login: <ISO 8601 UTC timestamp>` (e.g., `Last login: 2026-10-26T14:30:00Z`).

- **FR4: Last-login display — first sign-in.** When `signins.json` contains zero or one timestamp (no previous visit, or the user visits `/profile` before ever visiting `/`), the line reads: `Last login: first sign-in`.

- **FR5: Backward compatibility.** The existing `GET /` route continues to serve the Hello World HTML page. The existing smoke tests pass without modification. All other routes (non-`/`, non-`/profile`) continue to return 404.

- **FR6: Persistence.** `signins.json` survives server restarts. Sign-in history is cumulative.

---

## 4. User Experience & Behavior

### Key user flows

**Flow A — First visit:**
1. User visits `GET /` → sees the Hello World page (unchanged). A timestamp is recorded in `signins.json`.
2. User visits `GET /profile` → sees "Demo User" and "Last login: first sign-in" (only one timestamp exists, which is the current visit — no *previous* visit to show).

**Flow B — Returning visit:**
1. User has previously visited `GET /` one or more times.
2. User visits `GET /` again → sees the Hello World page. A new timestamp is appended.
3. User visits `GET /profile` → sees "Demo User" and "Last login: 2026-10-26T14:30:00Z" (the timestamp of the visit before the most recent one).

**Flow C — Profile without any sign-in:**
1. User visits `GET /profile` without ever visiting `GET /` (no `signins.json` exists).
2. Sees "Demo User" and "Last login: first sign-in."

### States and transitions

| State | Condition | "Last login" displays |
|---|---|---|
| No sign-ins | `signins.json` does not exist or is empty | `Last login: first sign-in` |
| Single sign-in | `signins.json` has exactly one entry | `Last login: first sign-in` |
| Multiple sign-ins | `signins.json` has two or more entries | `Last login: <second-most-recent timestamp>` |

### Edge cases

- **Corrupted or unreadable `signins.json`:** The profile page treats this as "no sign-ins" and displays "Last login: first sign-in." The server does not crash.
- **All visitors share one record:** This is by design (no auth). The spec does not attempt user isolation.

---

## 5. Acceptance Criteria

1. **Scenario 1 — Happy path: returning visitor.** Given `signins.json` contains two or more timestamps from previous `GET /` requests, when a user visits `GET /profile`, then the page displays "Demo User" followed by a "Last login" line showing the second-most-recent timestamp in UTC ISO 8601 format.

2. **Scenario 2 — Edge case: first sign-in.** Given `signins.json` contains exactly one timestamp (or does not exist), when a user visits `GET /profile`, then the "Last login" line reads "Last login: first sign-in".

3. **Scenario 3 — Edge case: no sign-ins at all.** Given `signins.json` does not exist (user has never visited `GET /`), when a user visits `GET /profile`, then the page displays "Demo User" and "Last login: first sign-in".

4. **Scenario 4 — Sign-in recording.** Given a user visits `GET /`, then a UTC ISO 8601 timestamp is appended to `signins.json`, and the Hello World HTML response is identical to the pre-feature behavior.

5. **Scenario 5 — Backward compatibility.** Given the existing smoke tests, when run against the server with this feature deployed, then all existing tests pass without modification, `GET /` returns the Hello World page with a 200 status, and non-routed paths return 404.

6. **Scenario 6 — Persistence across restarts.** Given timestamps have been recorded in `signins.json`, when the server is stopped and restarted, then `GET /profile` still shows the correct "Last login" timestamp from the data recorded before the restart.

---

## 6. Dependencies & Constraints (product-level)

- **Depends on:** The existing `serve.py` HTTP server and `docs/index.html` Hello World page in `ophirgal/test-repo-for-halo`.
- **Constraint:** No new Python dependencies beyond the standard library.
- **Constraint:** `signins.json` is a flat file in the server's working directory — no external storage.
- **Constraint:** All timestamps are UTC, ISO 8601. No locale or time zone conversion.
- **Known limitation:** No concurrency protection on `signins.json` writes. Acceptable for a single-user demo; a production version would need proper locking or a database.
- **Known limitation:** All visitors share one sign-in record (no user isolation). By design for this demo scope.

---

## 7. Technical Design (deferred to STRUCTURE)

Architecture, data model for `signins.json`, error-handling strategy, the HTTP handler structure, and test design are produced by the tech lead in the STRUCTURE stage from this approved product spec.

---

## 8. Open Questions

- **Q1 (resolved):** Localization — resolved as out of scope; UTC and English only.
- **Q2 (resolved):** Timestamp precision — resolved as ISO 8601 UTC (includes seconds as part of the standard format; precision to the second is the ISO 8601 default).

No remaining open questions.
