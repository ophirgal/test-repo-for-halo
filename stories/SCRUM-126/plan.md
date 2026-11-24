# SCRUM-126 — Implementation plan: the `/guestbook` page

## Context

SCRUM-126 adds a server-rendered guestbook at `/guestbook` to the small site `serve.py` serves. An anonymous visitor posts one line of at most 200 characters (trimmed, line breaks flattened) and sees the newest 20 messages, newest first, each with its send time. Messages persist in a local JSON Lines file across restarts. Empty or over-long messages are refused with the full page in an error state. Everything is plain text, and `/`, `/jungle`, `/healthz`, `/kv/`, the 404s and the 501s stay byte-for-byte as today. The change lands in `ophirgal/test-repo-for-halo` on the work branch `halo/feat/scrum-126-20261124-082308`, cut from `main`. `spec.md` (AC 1–12), `hld.md` (contracts and decisions D1–D10) and `work-items.md` (one work item, `t1`, with its criteria 1–17) sit beside this file in `stories/SCRUM-126/`. The screens come from the approved SCRUM-125 design, read from the copy at `/halo-out/design-reference/SCRUM-125/`.

## Research findings

**Change surface (facts read from the checkout at `172f73399a89`):**

- `serve.py:70` — `ROUTES = {"/": INDEX, "/jungle": JUNGLE}`. Exact-path dispatch through `_route` (`serve.py:116-118`). `hld.md` cites this as `serve.py:68`; the line is 70.
- `serve.py:72-74,126-139` — `HEALTH_PATH` and `_health()`: exact path match on `urllib.parse.urlsplit(self.path).path`, so the query string is ignored. This is the pattern `/guestbook` copies.
- `serve.py:219-245` — `do_GET` / `do_HEAD`: first `/kv/`, then `_health()`, then `ROUTES`, then `send_error(404)`. The `/guestbook` check goes beside `_health()`.
- `serve.py:247-256` — `_kv_only` answers non-`/kv/` paths with `send_error(501, "Unsupported method (%r)" % self.command)`. That is the same call the stock handler makes, so its output is byte-identical. The class has **no** `do_POST`, so every `POST` gets the stock 501 today.
- `serve.py:164-174` — `_kv_body`: the `Content-Length` validation (one distinct value, digits only, 400 + close; over `KV_MAX_BODY` = 65536 → 413 + close, unread). The guestbook POST needs the same checks. Reuse the logic by sharing a helper, not by copying it.
- `serve.py:259-288` — `KVHTTPServer`: a lazy `kv_open()` under `_kv_lock`, and `server_close()` closes the store. The guestbook store is added here the same way.
- `serve.py:1-44` — the module docstring lists every route. `tests/test_http.py:421-424` and `smoke_test.py` (`serve.__doc__` checks at about lines 245-275) assert its content, including the absence of "root-only" and "exactly one document".
- `kvstore/log.py:162` — `os.fsync` after an append. This is the repository precedent for a durable append.
- `docs/index.html` — the style reference: `lang="en"`, `viewport` meta `width=device-width, initial-scale=1`, `font-family: system-ui, sans-serif`, an inline `<style>`, `<main>`, `overflow-wrap: anywhere`.
- `.gitignore` — holds only `kv.log`. `tests/test_http.py:437-439` asserts this by splitting on whitespace, so adding a line is safe.

**Contracts that must not move:**

- `tests/test_http.py:351-352` and `smoke_test.py:130` assert that `serve.ROUTES == {"/": serve.INDEX, "/jungle": serve.JUNGLE}`.
- `tests/test_http.py:334-349` asserts that `POST /` and `POST /kv/x` (and `PUT`/`DELETE` elsewhere) are byte-identical to the stock 501 (`standard_501`, `tests/test_http.py:310-332`).
- `tests/test_http.py:354-362` runs `smoke_test.py` and asserts that no store file is created. The guestbook file must likewise never be created by a `GET` or by the smoke test.
- `tests/test_http.py:427-435` (`DocsTest`) checks README needles. Adding a section must keep every existing needle.

**Test layers that exist:** `unittest` modules in `tests/`, one per feature (`tests/test_healthz.py` is the closest pattern: a `QuietHandler`, `make_server("127.0.0.1", 0, …)` on a thread, `http.client` requests, `mock.patch.dict(os.environ, …)` for the path variable, `tests/test_healthz.py:18-56`), plus the stand-alone `smoke_test.py`. `pyproject.toml` declares a `pytest` extra with `testpaths = ["tests"]`, and the tests are pytest-compatible. There is no browser harness.

**Gate:** the repository has no CI workflow, no `.factory/`, no `CLAUDE.md` and no `AGENTS.md`. The gate the README documents (README "Tests") is `python -m unittest discover -s tests`, then `python3 smoke_test.py`.

**External data:** none. The design screens are read-only input from the copy at `/halo-out/design-reference/SCRUM-125/screens/`.

**Design screens (from `structure/structure.md` screen inventory and `screens/index.html`):** all five screens are `new` (no `/guestbook` route exists). They are `guestbook-default` (desktop + mobile), `guestbook-no-messages-yet` (empty), `guestbook-message-sent`, `guestbook-error-empty-message` and `guestbook-error-message-too-long`. Content read from the pages:

- Title "Guestbook".
- `<label for="message">Your message</label>`, then a `type="text"` field (`placeholder="Write one line…"`, `autocomplete="off"`, no `maxlength`) and the "Send" button on one row, at desktop and at 360 px.
- Hint "One line, up to 200 characters.". In an error state, the error **replaces** the hint (`index.html` note on the error screens).
- In an error state: `aria-invalid="true"`, `aria-describedby="message-error"` and `<p id="message-error" role="alert">` with a bold first sentence followed by the explanation.
- Section heading "Latest messages", then an `<ol>` of `<li>` items, each holding the message in `dir="auto"` and a `<time datetime>` in `YYYY-MM-DD HH:MM`.
- On a phone, the time sits above the text. On desktop, it sits on the right.
- No link to `/` or `/jungle`.

**Unknowns remaining:** none that block. The real-browser 360 px check cannot be automated in this repository (see Verification).

## Locked decisions and assumptions

**Locked decisions**

- Route `/guestbook`, exact path, query ignored; `/guestbook/`, `/guestbook.html`, `/Guestbook` and `/guestbookx` answer 404 — spec FR1, work item `t1` criterion 1.
- Validation: each line break becomes one space, then `strip()`, then a length of 1–200 code points. Over 200 is refused, never cut. Empty or whitespace-only is refused — spec FR3, §8.1–8.2, HLD D5.
- Post/Redirect/Get: a valid POST answers `303`, `Location: /guestbook`. Refusals answer `400` with the full page — HLD D1, D2.
- Exact copy as written in spec §4 and HLD §5: "Message is empty." / "Nothing was saved. Write at least one character and press Send."; "Message is too long — 200 characters at most." / "Yours has N. Nothing was saved or cut; shorten it and press Send."; "No messages yet. Be the first to leave one."
- Storage: JSON Lines at `GUESTBOOK_PATH`, default `./guestbook.jsonl`, records `{"t": "<UTC ISO-8601 seconds Z>", "m": "<text>"}`. A bad line is skipped with a stderr warning. A missing trailing `\n` is repaired before the next append. The newest 20 are kept in memory — HLD §5, D3, D4.
- Request limits: `Content-Length` checks as in `/kv/` (400/413). A `Content-Type` other than `application/x-www-form-urlencoded` → 415. Invalid UTF-8 → 400. Only the first `message` value is used — HLD §5, D7.
- Headers on the page: `X-Content-Type-Options: nosniff` and a `Content-Security-Policy` with no script source — HLD §5, D6.
- Escaping is done on output (`html.escape(..., quote=True)`), never on input — HLD D6, spec FR7.
- `ROUTES`, existing tests, `smoke_test.py`, `docs/*.html` and `kvstore/` are not changed — HLD D10, §2.
- Look: the product's plain style (`docs/index.html`). The design's markup, inline CSS and `tokens.css` are not copied. Content, states and hierarchy are binding — HLD D8, the UI design rules.
- Display time is the server's local zone, `YYYY-MM-DD HH:MM` — HLD A2.
- Standard library only, Python ≥ 3.9 syntax — `pyproject.toml` `requires-python = ">=3.9"`, epic constraint.

**Assumptions**

- **A-1:** The error replaces the hint, as the design's `index.html` notes. The spec table lists only the error text, so this follows the design, which is binding on content. If wrong, the hint is rendered as well, a one-line change.
- **A-2:** The "too long" error's N is the length after normalising (HLD §5), not the raw length. If wrong, only the number shown changes.
- **A-3:** Single process (HLD A1). An in-process lock is enough. If wrong, appends from two processes could interleave.
- **A-4:** The 360 px requirement is verified structurally in tests plus one manual browser check (HLD A3), because no browser harness exists. If wrong, a CSS-only overflow could ship unnoticed.
- **A-5:** The design's decorative error SVG icon and its `<ol reversed>` numbering are visual choices. The build uses a plain `<ol>` and may omit the icon; each such deviation is named in the build summary.

## Solution proposal

Add a new standard-library package `guestbook/` at the repo root, a sibling of `kvstore/`. It holds the three pure concerns, and `serve.py` gets a thin route.

1. **`guestbook/message.py` (new)** — `normalise(raw)` and `check(raw)`. The check returns either the accepted text or an error kind (`"empty"` / `"too_long"`) with the normalised length. Constant `MAX_LEN = 200`. To normalise, replace `\r\n` first, then every separator `str.splitlines` recognises (`\n \r \v \f \x1c \x1d \x1e \x85 \u2028 \u2029`), each with one space, then `strip()`.
2. **`guestbook/store.py` (new)** — class `GuestbookStore(path)`:
   - Loading is lazy: on the first read, one streaming pass over the file fills a `collections.deque(maxlen=20)`, skipping and warning on bad lines (`print(..., file=sys.stderr)` naming the line number). A missing file means empty, and it is never created.
   - `append(text, now)`: under a `threading.Lock`, opens the file in `"a"` mode. It does **not** create a missing directory, so `OSError` propagates. Before writing, it checks whether the file is non-empty and does not end in `\n`, and if so writes a `\n` first. It writes one compact JSON line, flushes, `os.fsync`s, and only then pushes to the deque.
   - `latest()` returns the records newest first.
   - Timestamps are made at append time from `datetime.now(timezone.utc)`, which can be injected for tests.
3. **`guestbook/page.py` (new)** — `render(records, error=None, value="")` returns UTF-8 bytes for one full HTML document:
   - The head follows `docs/index.html`: `lang="en"`, charset, `viewport` meta and an inline `<style>`. The style uses `system-ui`, a fluid layout with no fixed width over 360 px, the field with `flex: 1; min-width: 0` beside the button, `overflow-wrap: anywhere` on message text, and the time beside the text on desktop and above it under a media query for narrow screens.
   - The body holds the content and states listed under Research findings, and no `<script>`.
   - Every message and the kept `value` go through `html.escape(…, quote=True)`.
   - Times are converted to local time (`astimezone()`) and shown as `%Y-%m-%d %H:%M` inside `<time datetime="<ISO>">`.
4. **`guestbook/__init__.py` (new)** — re-exports the public names, like `kvstore/__init__.py`.
5. **`serve.py` (edit)**:
   - Add constants `GUESTBOOK_PATH = "/guestbook"`, `DEFAULT_GUESTBOOK_FILE = "./guestbook.jsonl"` and the page header values (CSP and `nosniff`).
   - Add `_guestbook()`, which mirrors `_health()`: it returns False when the path is not exactly `/guestbook`. Otherwise it serves GET/HEAD (200 page, body skipped for HEAD) and POST.
   - Call `_guestbook()` in `do_GET` and `do_HEAD` right after `_health()`.
   - Add `do_POST`. It calls `_guestbook()` when the path matches, and otherwise calls `self.send_error(501, "Unsupported method (%r)" % self.command)`, the same call `_kv_only` uses, so the response stays byte-identical to the stock handler.
   - Factor the `Content-Length` check out of `_kv_body` into a shared helper with a parameterised error type, so `/kv/` behaviour and messages stay identical. Alternatively, call `_kv_body` and translate its `KVRequestError` into `send_error(status)` with `Connection: close`. Pick whichever leaves `/kv/` answers unchanged.
   - `KVHTTPServer` gets `guestbook_store()`, which lazily builds a `GuestbookStore` from `os.environ.get("GUESTBOOK_PATH") or DEFAULT_GUESTBOOK_FILE` under its own lock. A GET read error (`OSError` from an unreadable file) answers `500` via `send_error`. An append `OSError` answers `500`.
   - Update the module docstring with the route and `GUESTBOOK_PATH`.

**Alternatives rejected:**

- Putting `/guestbook` into `ROUTES`: that breaks `tests/test_http.py:351` and `smoke_test.py:130`, and `ROUTES` maps to static files.
- Reusing `kvstore` for storage: it cannot be edited by hand, and the data would show in `/kv/` listings (HLD D3).
- A static `docs/guestbook.html` template with placeholders: `linkcheck` would crawl it, and the page has no static form. Rendering in Python keeps the escaping in one place.
- A client-side script: forbidden by the design (no client scripts) and by the CSP.
- Rendering the page directly from the POST: a refresh would resubmit (HLD D1).

## Ordered implementation steps

All steps belong to work item `t1`. The criteria cited are `t1`'s (C1–C17), with the story's ACs in brackets. The test layer is the `unittest` suite in the new `tests/test_guestbook.py`, unless stated otherwise.

1. **Message rules.** Create `guestbook/message.py` and `guestbook/__init__.py`.
   - Covers C6, C7, C8 and C9 [AC 3, 4, 5, 6].
   - Unit tests:
     - 200 code points with surrounding spaces is accepted trimmed.
     - 201 is refused with length 201.
     - `""`, `"   "` and `"\n"` are refused as empty.
     - `\r\n`, `\r`, `\n` and `\u2028` each become one space.
     - A Hebrew string counts per code point.
2. **File store.** Create `guestbook/store.py`.
   - Covers C3, C4, C11 and C12 [AC 2, 8, 9]. Invariants: concurrency (the lock), durability (`fsync`), no partial writes on a refusal (the store is never called), and no directory creation.
   - Unit tests against a temporary directory:
     - 25 appends → `latest()` returns 20, newest first.
     - A missing file is empty and is not created.
     - A blank line and a garbage line are skipped, each with one stderr warning naming its line (capture `sys.stderr`).
     - A file without a trailing newline gets the next record on a new line.
     - 10 threads appending produce 10 whole JSON lines.
     - A path in a missing directory raises `OSError` and the directory is not created.
     - A new instance on the same path shows the same order and times (restart).
3. **Page rendering.** Create `guestbook/page.py`.
   - Builds the designed screens, all `new`: `guestbook-default` (desktop + mobile), `guestbook-no-messages-yet` (empty), `guestbook-message-sent`, `guestbook-error-empty-message` (error) and `guestbook-error-message-too-long` (error).
   - Covers C2, C3, C4, C7, C8, C10, C14 and C15 [AC 1, 2, 3, 5, 7, 8, 10].
   - Unit tests on the rendered HTML:
     - The order of the elements (title, label, field, Send, hint, heading, list).
     - No `maxlength`, no `<script`, no `href="/"` and no `/jungle`.
     - The empty line appears in place of the list.
     - The exact error copy, with `aria-invalid`, `aria-describedby` and `role="alert"`, and the error in place of the hint.
     - `<b>שלום</b><script>alert(1)</script>` comes out escaped, and a `"` in the kept value is escaped.
     - Every message carries `dir="auto"`.
     - Times use the `YYYY-MM-DD HH:MM` format. Compare against `time.localtime`-based formatting, or pin `TZ` with `mock.patch.dict(os.environ, {"TZ": …})` + `time.tzset()` where it is available.
     - The 360 px markers are present: the viewport meta, `overflow-wrap: anywhere` and `min-width: 0`, and no `width:` over 360 px.
4. **HTTP route.** Edit `serve.py` as in the Solution proposal (dispatch, `do_POST`, the shared `Content-Length` check, the lazy store on `KVHTTPServer`, 303/400/413/415/500, headers).
   - Covers C1, C5, C11, C12, C13 and C16 [AC 1, 9, 11, 12].
   - End-to-end tests in `tests/test_guestbook.py`, following the `tests/test_healthz.py:18-56` harness, with `GUESTBOOK_PATH` and `KV_PATH` patched to a temporary directory:
     - GET/HEAD on `/guestbook` and `/guestbook?x=1` answer 200 with the right headers. The look-alikes answer 404.
     - `POST message=שלום מכולם` (urlencoded) answers 303 to `/guestbook`. The next GET shows it first with an empty field. Repeating the GET adds nothing (the line count does not change).
     - A 201-character post and an empty post each answer 400 with the error page and the file unchanged.
     - A POST with no `message` field answers 400 (empty). A repeated `message` uses the first value.
     - Missing or invalid `Content-Length` → 400. `Content-Length` 65537 → 413. `Content-Type: text/plain` → 415. `%FF` → 400. None of these writes anything.
     - An unwritable path answers 500, and its directory is not created.
     - An unreadable existing file (a directory at the path, or `chmod 000` skipped when running as root) makes GET answer 500 while `/`, `/jungle`, `/healthz` and `/kv/` answer as usual.
     - A server restarted on the same file shows the 3 messages in the same order with the same times.
     - `PUT`/`DELETE /guestbook` and `POST` to `/`, `/kv/x` and `/guestbook/` are byte-identical to the stock 501. Copy the `standard_501` approach from `tests/test_http.py:310-332` into the new test module; do not edit `tests/test_http.py`.
     - `ROUTES` is unchanged.
5. **Docs and ignore.**
   - Add a `## Guestbook (/guestbook)` section to `README.md`. It covers the purpose, `GUESTBOOK_PATH` and its default, the 200-character and 20-message rules, the file format, deleting a message by removing its line and restarting, and the `HOST=0.0.0.0` no-auth warning.
   - Add `guestbook.jsonl` to `.gitignore`.
   - Update the `serve.py` docstring (route, `GUESTBOOK_PATH`, usage line).
   - Covers C17 [AC 11].
   - Test layer: `DocsTest`-style asserts in `tests/test_guestbook.py`, covering the README needles, the `.gitignore` entry and the docstring needles. The existing `tests/test_http.py:421-439` must stay green unedited.

Dependencies are standard library only, so nothing is installed and no cache is assumed. There are no generated deliverables and no binaries.

## Work-item mapping

| Step | Work item | Title |
| --- | --- | --- |
| 1 — Message rules | `t1` | Guestbook page at /guestbook: post one line, list the latest 20, stored in a local file |
| 2 — File store | `t1` | (same) |
| 3 — Page rendering | `t1` | (same) |
| 4 — HTTP route | `t1` | (same) |
| 5 — Docs and ignore | `t1` | (same) |

`t1` is the only work item, and every step belongs to it.

## Verification and CI gate

- **Canonical gate, in order (README "Tests"):** `python -m unittest discover -s tests`, then `python3 smoke_test.py`. The repository has no provider CI configuration, and this story adds none.
- **Local run:** the single gate run is the implement turn's `run-tests-gate.sh --run` on the committed SHA. Do not run the canonical commands separately beside it.
- **What the gate must show:**
  - Every existing test passes unedited (`tests/test_http.py`, `tests/test_healthz.py`, `tests/test_store.py`, the others).
  - The new `tests/test_guestbook.py` passes, with at least one test per `t1` criterion C1–C16 and C17's docs checks.
  - `smoke_test.py` passes and creates neither `kv.log` nor `guestbook.jsonl` (already asserted for the KV store by `tests/test_http.py:354-362`; the new module adds the same check for `GUESTBOOK_PATH`).
- **Pod limits:** every automated layer runs in a pod (in-process server on an ephemeral port, temporary directories). Two things cannot be automated here:
  - The real-browser 360 px check for AC 10 / C14. There is no browser harness, and adding one is out of scope. The build summary records it as a manual check: read the list, type and send a 200-character message, with no sideways scrolling and no zoom.
  - The unreadable-file test, which must not depend on `chmod` when the pod runs as root. Use a directory at `GUESTBOOK_PATH` to force the `OSError`.
- **`.factory/testing.md` / `.factory/delivery-assets`:** these do not exist in the repository, and no binary is added.

## Risks and scope guards

**Risks:**

- **Regression on the stock 501 for `POST /` and `POST /kv/x`.** Mitigation: `do_POST` hands every non-`/guestbook` path to the same `send_error(501, …)` call `_kv_only` uses, and the new tests compare it byte for byte.
- **`/kv/` behaviour drift when sharing the `Content-Length` check.** Mitigation: keep the `/kv/` messages and close semantics identical. `tests/test_http.py:245-286` guards this.
- **XSS through a message or the kept value.** Mitigation: escape on output with `quote=True`, no script, and the CSP. AC 7's literal payload is tested.
- **Timezone-dependent tests.** Mitigation: compute the expected text with the same local conversion, or pin `TZ`.
- **Unbounded file growth (RK2) and no moderation (RK1).** Both are accepted by the PRD. Memory stays bounded by the deque.

**Scope guards — the implement phase must NOT:**

- Edit `ROUTES`, `docs/index.html`, `docs/jungle.html`, `kvstore/`, `linkcheck/`, `src/ledger/`, `smoke_test.py`, or any existing test file.
- Add a link to `/guestbook` from `/` or `/jungle`, or from the guestbook to them.
- Copy the design pages' markup, inline CSS or `tokens.css`, or the design folder, into the repository.
- Add `maxlength`, a live counter, client JavaScript, a sender name, paging, deletion from the page, rate limiting, or any dependency outside the standard library.
- Use Python 3.10+-only syntax.
- Create the store directory, or create `guestbook.jsonl` on a `GET`.
- Add a CI pipeline or a browser test harness.
- Make a failing check pass by deleting, skipping or weakening it. Report it as blocked instead.
- Tidy adjacent code (for example the stale `serve.py:68` citation in `hld.md`, or refactoring `_kv_body` beyond what sharing it needs).

## Clarification outcomes

None. No question was needed: the spec, HLD and design settle every decision, and the remaining gaps are stated as assumptions A-1 to A-5.
