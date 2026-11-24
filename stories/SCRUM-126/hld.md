# SCRUM-126 — High-Level Design: the `/guestbook` page

## 1. System overview

- **What is built:** a server-rendered guestbook at `/guestbook` in the small site that `serve.py` serves. `GET` shows the form and the latest 20 messages, newest first, each with its send time. `POST` validates one line of at most 200 characters, appends it to a local file, and redirects back to the page. Spec: `stories/SCRUM-126/spec.md` FR1–FR10, AC 1–12.
- **Problem:** today `serve.py` serves only fixed routes (`ROUTES = {"/": INDEX, "/jungle": JUNGLE}`, `serve.py:68`), plus `/healthz` and `/kv/`. It has no `do_POST`, so every `POST` gets the stock 501 (`serve.py:251-260` covers `PUT`/`DELETE` only).
- **Responsibilities:** check and normalise a message, store it so it survives a restart, render the five approved screen states (default, no messages yet, message sent, error: empty, error: too long) as plain text with no client script, and leave `/`, `/jungle`, `/healthz`, `/kv/`, the 404s and the 501s exactly as they are today.
- **Design source:** the approved SCRUM-125 screens, read from `origin/halo/feat/scrum-125-20261124-080803:stories/SCRUM-125/design/screens/` (`guestbook-*.html`, desktop and `.mobile`). The screens fix the content, copy, states and hierarchy. They are a picture, not code to copy (§6 D8).

## 2. Architecture overview

```
browser ──GET/HEAD/POST /guestbook──▶ serve.py RootOnlyHandler (dispatch only)
                                         │
                                         ▼
                              guestbook/ package (new, stdlib only)
                               ├─ message rules: normalise + validate
                               ├─ store: JSON Lines file GUESTBOOK_PATH, last 20 kept in memory
                               └─ page: full HTML page for each state (html-escaped)
```

- **`serve.py` (existing, modified):** routes only. It adds `/guestbook` beside `/healthz`, matched exactly on the path with any query string ignored, the same pattern as `_health` (`serve.py:126-139`). It adds `do_POST`. The server class (`KVHTTPServer`, `serve.py:263`) gets a lazily opened guestbook store next to `kv_open`, using the same lock pattern. `ROUTES` is **not** changed, because `tests/test_http.py:351` asserts it is exactly `{"/", "/jungle"}`.
- **`guestbook/` (new package at the repo root, the sibling of `kvstore/`):** owns the message rules, the file format and the page rendering. It has no HTTP knowledge, so it can be unit-tested without a socket.
- **External dependencies:** none. Python standard library only (epic constraint; `pyproject.toml` has `dependencies = []`; runtime checked on Python 3.12, and `requires-python >= 3.9` means no 3.10+-only syntax).
- **Unchanged:** `docs/index.html`, `docs/jungle.html`, `kvstore/`, `smoke_test.py`, `linkcheck/`, `src/ledger/`.

## 3. Data flow

Everything is synchronous and request-scoped, with no background work.

1. **View:** `GET /guestbook` → the store returns its last 20 records (loaded from the file on first use) → page renders the default state, or the empty state when there are none → `200 text/html; charset=utf-8`. A missing file means the empty state, and a `GET` never creates the file.
2. **Send (valid):** `POST /guestbook` (`application/x-www-form-urlencoded`, field `message`) → body read within the size cap → normalise (each line break becomes one space, then trim the ends) → length 1–200 → append one line to the file under the lock, `flush` + `fsync`, then update the in-memory list → `303 See Other`, `Location: /guestbook` → the browser `GET`s the page, and the visitor's message is first (Post/Redirect/Get, so a refresh does not resend: FR4).
3. **Send (refused):** empty, or over 200 after normalising → nothing is written → `400` with the full page in the matching error state: the submitted text is kept in the field, the error sits under it, and the list is unchanged (FR6).
4. **Restart:** the file is read again on first use. Order is file order (append order) and times are the stored times, so the same three messages show in the same order with the same times (AC 9).

## 4. Component breakdown

| Component | Responsibility | In / Out | Repo |
| --- | --- | --- | --- |
| Message rules (`guestbook/`) | Normalise (line breaks → one space; trim with `str.strip()`), then classify as ok / empty / too long. Length is counted in Unicode code points (`len`) after normalising (spec §8.1). | raw submitted string → normalised text, or an error kind with the length N | `ophirgal/test-repo-for-halo` |
| Store (`guestbook/`) | Append records to the JSON Lines file at `GUESTBOOK_PATH` (default `./guestbook.jsonl`), keep the newest 20 in memory, and serialise writers with a lock. | record → appended line; → newest-first list of at most 20 | same |
| Page (`guestbook/`) | Render one full HTML document for any state. Every message and the kept field value go through `html.escape(..., quote=True)`. Each message gets `dir="auto"`, and each time a `<time datetime>` showing `YYYY-MM-DD HH:MM`. | state (records, error kind, N, kept text) → HTML bytes | same |
| Routing (`serve.py`) | Exact-path dispatch for `GET`/`HEAD`/`POST /guestbook`, body-size and content-type checks, the PRG redirect, status codes. Lazy store on the server object. | HTTP ↔ the components above | same |
| Tests (`tests/test_guestbook.py`) | Unit tests for rules, store and page, plus end-to-end HTTP tests on an ephemeral port (pattern: `tests/test_healthz.py:18-56`). | — | same |
| Docs (`README.md`, the `serve.py` docstring, `.gitignore`) | Document the route, `GUESTBOOK_PATH`, the file format and manual deletion; ignore `guestbook.jsonl`. | — | same |

## 5. Interface contracts

**HTTP: `/guestbook` (exact path; a query string is ignored for every method)**

| Request | Answer |
| --- | --- |
| `GET /guestbook` | `200`, `text/html; charset=utf-8`, the full page (default or empty state). Headers also carry `X-Content-Type-Options: nosniff` and a `Content-Security-Policy` that allows no script (inline style and same-origin form posts only). |
| `HEAD /guestbook` | The same status and headers as `GET`, no body. |
| `POST /guestbook`, valid message | `303 See Other`, `Location: /guestbook`, empty body. One record is appended. |
| `POST /guestbook`, empty / spaces only / missing `message` field | `400`, the full page in the "error: empty" state: "Message is empty." / "Nothing was saved. Write at least one character and press Send." Nothing is written. |
| `POST /guestbook`, over 200 code points after normalising | `400`, the full page in the "error: too long" state: "Message is too long — 200 characters at most." / "Yours has N. Nothing was saved or cut; shorten it and press Send." N is the normalised length. Nothing is written. |
| `POST /guestbook`, `Content-Length` missing, repeated with different values, or not digits | `400` (stock `send_error` HTML), connection closed, nothing written. |
| `POST /guestbook`, `Content-Length` > 65,536 bytes | `413`, the body is not read, connection closed, nothing written. |
| `POST /guestbook`, `Content-Type` not `application/x-www-form-urlencoded` (parameters such as `; charset=UTF-8` allowed) | `415`, nothing written. |
| `POST /guestbook`, form body not valid UTF-8 after percent-decoding | `400`, nothing written. |
| `POST /guestbook`, store file cannot be written (missing directory, permissions, disk) | `500`, nothing reported as saved. The directory is never created. |
| `GET`/`HEAD /guestbook`, store file exists but cannot be read | `500`. Other routes are unaffected. |
| `PUT`/`DELETE /guestbook` | The stock `501`, unchanged. |
| `POST` to any other path (`/`, `/kv/x`, `/guestbook/`, …) | Byte-identical to the stock `BaseHTTPRequestHandler` 501, as today (`tests/test_http.py:310-348`). |
| `GET`/`HEAD` on `/guestbook/`, `/guestbook.html`, `/Guestbook`, `/guestbookx` | `404`, as for any unknown path. |

Form fields: only `message` is read. When it is repeated, the first value is used, and other fields are ignored. `+` and percent-escapes are decoded as a browser sends them (`urllib.parse.parse_qs` with `keep_blank_values=True`, strict UTF-8).

**File format: `GUESTBOOK_PATH`, default `./guestbook.jsonl`**

- UTF-8, one JSON object per line: `{"t": "<UTC ISO-8601, seconds, Z>", "m": "<normalised text>"}`, appended in send order (newest last).
- When the file does not end in `\n` (a torn last write or a hand edit), the next append starts with a `\n`, so a good record is never glued onto a bad one.
- On load, a line that is blank, not JSON, or missing a string `t`/`m` is skipped with one warning on stderr naming its line number. The page still renders (unlike `/kv/`'s 503: a guestbook should not go dark over one hand-edited line).
- An operator deletes a message by removing its line, then restarts the server, because the in-memory list is loaded once (README documents this).

**Display time:** the stored UTC time is converted to the server's local time zone and shown as `YYYY-MM-DD HH:MM` (24-hour), with `<time datetime="...">` carrying the ISO value.

## 6. Key technical decisions

- **D1 — Post/Redirect/Get with 303.** This satisfies "refresh does not resave" (FR4) with no client script. The alternative, rendering the page directly from the `POST`, was rejected because a refresh would resubmit.
- **D2 — Error screens answer 400 with the full page.** Browsers render a 4xx HTML body normally, and the status is honest for tests and tools. Alternative: 200, rejected as it hides the refusal from tools.
- **D3 — JSON Lines file, separate from `kv.log`.** It is easy to edit by hand for RK1 (delete a line), append-only, and needs no compaction. Reusing `kvstore` was rejected: its CRC'd log is not hand-editable (a hand edit triggers its 503), and mixing guestbook data into the KV keyspace would change `/kv/` listings (R10).
- **D4 — Newest 20 kept in memory, loaded on first use.** A `GET` stays cheap even when the file grows past RK2's 5 MB threshold. The tradeoff is that hand deletions show after a restart, which is documented. The file is read in one streaming pass that keeps the last 20 records (a bounded deque), so memory stays flat whatever the file size.
- **D5 — Normalisation order:** first `\r\n`, then every other line separator `str.splitlines` recognises, each replaced by one space; then `str.strip()`; then the length check by code points. A message of exactly 200 code points plus surrounding spaces is saved trimmed (AC 4). 201 is refused and nothing is cut (AC 3).
- **D6 — Plain text only.** Every message and the kept field value are HTML-escaped with `quote=True` at render, and the stored text is the raw normalised text (escape on output, never on input). There is no client script, and a CSP with no script source is defence in depth for R7/RK3 (AC 7).
- **D7 — Request-size cap of 64 KiB (413), not 200 characters.** A long paste still reaches the friendly "too long" screen. Only absurd bodies are refused before reading, matching `/kv/`'s cap (`serve.py:59`).
- **D8 — Look:** the page is built in the product's own plain style (`docs/index.html`: `system-ui` font, `viewport` meta, `overflow-wrap: anywhere`, inline `<style>`). The design's `tokens.css`, markup and inline CSS are **not** copied. Its content, copy, states and hierarchy are binding: the "Guestbook" title; the "Your message" label; a single-line `type="text"` field with the "Write one line…" placeholder and **no** `maxlength`; the Send button; the hint "One line, up to 200 characters."; the "Latest messages" heading; an `<ol>` list; and the error under the field with `aria-invalid` / `aria-describedby` / `role="alert"`. The design's decorative SVG error icon is optional, and leaving it out is named as a visual deviation in the build summary.
- **D9 — Mobile (360 px):** the page uses a fluid layout with no fixed width above 360 px. The field can shrink (`min-width: 0`), message text uses `overflow-wrap: anywhere`, and the viewport meta is present. Tests assert these markers in the HTML. A real-browser check at 360 px is a manual step named in the build summary (§8 A3).
- **D10 — `ROUTES` untouched; dispatch beside `/healthz`.** This keeps `tests/test_http.py:351` and every existing 404/501 assertion green with no edits to existing tests.

## 7. Risks and constraints

- **Concurrency:** `ThreadingHTTPServer` serves requests on parallel threads. Append + in-memory update happen under one lock on the server object, so two simultaneous sends both land, in a single order, as whole lines.
- **Growth (RK2):** the file is unbounded by design (no rate limit is in scope). Memory is bounded by D4, and only disk grows. Past 5 MB a separate rate-limit epic is considered (PRD RK2).
- **Abuse (RK1):** there is no content filter. Removal is a manual file edit followed by a restart.
- **Exposure:** the server binds to `127.0.0.1` by default. `HOST=0.0.0.0` exposes an unauthenticated write form, and the README warns about this the same way it does for `/kv/`. CSRF is irrelevant: there are no accounts or sessions to abuse.
- **Regression (RK4/R10):** `tests/test_http.py` pins `ROUTES`, the stock 501 for `POST /` and `POST /kv/x`, the 404 list and that `smoke_test.py` passes without creating a store. `do_POST` must hand every non-`/guestbook` path to the stock 501 path unchanged. `smoke_test.py` is not changed and never touches `/guestbook`, so it never creates `guestbook.jsonl`.
- **Repo gates:** there is no `.factory/`, `CLAUDE.md`, `AGENTS.md` or CI workflow. The gate is the README's `python -m unittest discover -s tests` and `python3 smoke_test.py`, and both must pass. Tests are `unittest` style (pytest-compatible), with no new dependencies.
- **Timezone:** the display uses the server's local zone. Changing `TZ` between restarts changes the shown times (the stored UTC does not change). Tests pin the zone or compare formatted local time.

## 8. Assumptions

- **A1 — Single host, single process** (PRD §7). The lock is in-process. Two `serve.py` processes sharing one `GUESTBOOK_PATH` are unsupported. If wrong, appends could interleave, and a file lock would be needed.
- **A2 — The display time zone is the server's local zone** (spec §8.4 left the zone to this stage). If the product owner wants UTC or a fixed zone, only the formatting changes.
- **A3 — The 360 px check is structural in automated tests** (viewport meta, no fixed widths over 360 px, wrapping rules) plus one manual browser check, because the repo has no browser test harness, and adding one is out of scope. Risk: a CSS regression only a real browser would catch.
- **A4 — Hand edits take effect on restart** (D4). This is accepted given that RK1 removal is rare and manual.
- **A5 — `/healthz` (SCRUM-122) is an existing route** (spec §6) and stays unchanged.
- **A6 — Non-browser clients** that post without `Content-Length` (chunked) get 400, as `/kv/` does today.
