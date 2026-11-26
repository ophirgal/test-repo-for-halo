# HLD — Store newsletter signups and export them (SCRUM-103)

## 1. System overview

- **What:** the newsletter signup journey, built end to end in `ophirgal/test-repo-for-halo`. It covers a "Newsletter" footer link on `docs/index.html`, three server-rendered screens (Welcome, Signup form, Confirmation) served by `serve.py`, a durable file of signups, and a command-line CSV export (spec FR0a–FR7, scenarios 1–7).
- **Problem:** marketing collects addresses by hand today. The repo has no newsletter code. `serve.py` routes `/`, `/jungle`, `/healthz`, `/guestbook` and `/kv/`, and `POST` is accepted only at `/guestbook` (`serve.py` `do_POST`).
- **Responsibilities:** validate name and email on the server (FR0b, FR3), store each new address once with its UTC time (FR1, FR2, FR6), render the approved screens and their states (R1, R2, R4), and export every signup as CSV from a local command only (FR4, FR5, scenario 7).
- **Design source:** the approved screens are on branch `origin/halo/feat/scrum-102-20261123-172706`, under `stories/SCRUM-102/design/screens/` (with `tokens.css` and `structure/structure.md`). This branch reads them there and ports their markup and styles into the new package. It does not merge that branch.
- **Code vs spec:** `docs/index.html` has no footer today (only `<main><h1>Hello World</h1></main>`). The approved structure says the same ("The page has no footer today, so this story adds one"), so this story adds the footer. `docs/jungle.html` gets no footer: `smoke_test.py` (`JUNGLE_FORBIDDEN`) forbids any `<a` in that page.

## 2. Architecture overview

The design follows the SCRUM-126 guestbook pattern: a stdlib-only package with no HTTP knowledge, and routing in `serve.py`.

- **`newsletter/` package (new):**
  - `newsletter/signup.py`: the name and email rules, and normalising the address for duplicate checks.
  - `newsletter/store.py`: an append-only JSON Lines file with a process lock and an in-memory set of known addresses. Modelled on `guestbook/store.py` `GuestbookStore`.
  - `newsletter/export.py` and `newsletter/__main__.py`: the CSV export command.
  - `newsletter/pages.py`: renders Welcome, Form (in every state) and Confirmation, plus the static progressive-enhancement script. Modelled on `guestbook/page.py`.
- **`serve.py` (edited):** exact-path routes under `/newsletter`, a `POST` branch, and a lazily built shared store on `KVHTTPServer`, like `guestbook_store()`. Every existing route stays unchanged.
- **`docs/index.html` (edited):** adds a `<footer>` holding a "Newsletter" link to `/newsletter`. `GET /` stays byte-identical to the file, as `smoke_test.py` already asserts.
- **External dependencies:** none. Standard library only (Python ≥3.9 per `pyproject.toml`; verified on 3.13).
- **Ownership:** a single repo. The tickets are split by file lane (see `work-items.md`).

## 3. Data flow

All of it is synchronous. There are no events or queues.

1. The visitor opens `/` and follows the footer link to `GET /newsletter` (Welcome). "Subscribe" leads to `GET /newsletter/signup` (Form).
2. The form posts `name` and `email` (urlencoded) to `POST /newsletter/signup`. `serve.py` reads the body under the same Content-Length and 64 KiB rules as `/guestbook`.
3. `serve.py` validates both fields with the newsletter rules.
   - **Invalid input:** `400` with the form page, each error under its field and the typed values kept. Nothing is written.
   - **Valid input:** the store is called under its lock. A new normalised address is appended and fsynced. A known address is a no-op.
   - **Either valid outcome:** `303` to `GET /newsletter/thanks` (Confirmation). Both answers are byte-identical, so the response does not reveal whether the address was already subscribed.
   - **Store failure (`OSError`):** `500` with the form page in the "submission failed" state, values kept.
4. With script enabled, `/newsletter/form.js` disables Submit and shows the busy label when the form is submitted (the "submitting" state). Without script, the form still works.
5. **Export (offline, separate process):** an operator runs `python3 -m newsletter export [-o FILE]` on the host. It reads `NEWSLETTER_PATH` and writes the CSV to stdout or to `FILE`. The server is not involved, and no HTTP route ever returns signups.

## 4. Components

| Component | Responsibility | Inputs / outputs | Repo / ticket |
|---|---|---|---|
| Signup rules (`newsletter/signup.py`) | Name and email validation; the address key used for duplicates | raw strings → cleaned values + per-field error codes | test-repo-for-halo / t1 |
| Signup store (`newsletter/store.py`) | Append once per address, durable, thread-safe; read every record in order | cleaned name and email → "added" / "already there"; file → records | t1 |
| CSV export (`newsletter/export.py`, `newsletter/__main__.py`) | `python3 -m newsletter export` | signup file → CSV on stdout or a file; exit status | t1 |
| Pages (`newsletter/pages.py`) | Welcome, Form (default and error states, submission failed) and Confirmation HTML; the static `form.js` | form state → UTF-8 HTML bytes | t2 |
| Routing (`serve.py`) | `/newsletter*` routes, POST handling, shared store, headers | HTTP ↔ the components above | t2 |
| Footer (`docs/index.html`) | "Newsletter" link (R1) | — | t2 |
| Docs and tests | README section, `.gitignore` entry, unit and HTTP tests, smoke checks | — | t1 (store/export), t2 (journey) |

## 5. Interface contracts

**Validation rules.** Both rules are settled here and enforced on the server, whatever the browser sends.

- **Name.**
  - Every line break becomes a space, then both ends are trimmed. The length is counted in Unicode code points.
  - Empty after trimming → error `name_empty`.
  - Over 80 code points → error `name_too_long` (spec FR0b). The browser's `maxlength="80"` normally prevents this case. The error text sits under Name, in the approved error style.
- **Email.**
  - Both ends are trimmed.
  - Empty → error `email_empty`.
  - Otherwise the address must fully match: one `@`; no whitespace; a non-empty local part; a domain of two or more non-empty dot-separated labels; at most 254 characters. Anything else → error `email_malformed`.
  - Examples: `maya.levi@example` and `a@@b.co` are malformed; `x@y.zé` is accepted. These were verified against the probe pattern.
  - The address is stored as trimmed and keeps its case.
- **Several errors** can show at once, each under its own field. Focus is placed on the first field in error, through `autofocus` on that field.
- **Duplicate key:** the trimmed address passed through `str.lower()`. `casefold()` is not used, because it would treat `ß` and `ss` as the same address. The first record's name and time are kept.

**Signup file.** Set by `NEWSLETTER_PATH`; the default is `./newsletter.jsonl`, which is added to `.gitignore`.
- One JSON object per line, `{"t": "YYYY-MM-DDTHH:MM:SSZ", "n": "<name>", "e": "<email>"}`, appended oldest first. The time is UTC, to the second.
- Reading never creates the file or its directory. A missing file means no signups.
- A blank or invalid line (bad JSON, missing or wrong-typed field, bad time) is skipped with one stderr warning that names its line number. This includes a torn last line.
- Before appending, a file that does not end in `\n` first gets one.
- Each append is flushed and `fsync`ed before the visitor is redirected.

**HTTP routes (`serve.py`).** Paths match exactly; a query string is ignored.

| Method + path | Answer |
|---|---|
| `GET`/`HEAD /newsletter` | `200` Welcome |
| `GET`/`HEAD /newsletter/signup` | `200` Form, default state |
| `POST /newsletter/signup` | valid (new or known address) → `303`, `Location: /newsletter/thanks`, empty body; invalid fields → `400` Form with inline errors and values kept; store `OSError` → `500` Form in the "submission failed" state, values kept; bad or duplicate `Content-Length` or invalid UTF-8 → `400`; over 64 KiB → `413` (body not read); not `application/x-www-form-urlencoded` → `415` |
| `GET`/`HEAD /newsletter/thanks` | `200` Confirmation, the same bytes for every visitor |
| `GET`/`HEAD /newsletter/form.js` | `200` `text/javascript`, a fixed script |
| anything else under `/newsletter` (`/newsletter/`, `/newsletter/export.csv`, …) | `404` |
| `PUT`/`DELETE` on newsletter paths; `POST` to any other newsletter path | `501`, as today |

- **Page headers:** `text/html; charset=utf-8`, `X-Content-Type-Options: nosniff`, and `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`.
- **Escaping:** every echoed value is HTML-escaped.

**Export command.**
- **Usage:** `python3 -m newsletter export` writes to stdout; `python3 -m newsletter export -o FILE` writes `FILE`, overwriting it.
- **Format:** UTF-8 with no BOM; `csv` module default quoting and `\r\n` line endings.
- **Rows:** the header `name,email,signed_up_at`, then one row per stored record, oldest first, with the time as in the file (ISO 8601 UTC, `Z`). Empty store → the header only.
- **Formula-injection guard:** a cell that begins with `=`, `+`, `-`, `@`, a tab or a carriage return gets a leading `'`. This protects Excel users from values a public form can plant.
- **Exit codes:**
  - `0`: success.
  - `1`: `NEWSLETTER_PATH` unreadable or `FILE` unwritable. A one-line stderr message; no partial `FILE` is left behind.
  - `2`: a usage error, such as an unknown subcommand.

## 6. Key technical decisions

- **JSON Lines file plus a process lock, as in `guestbook/store.py`.** `kvstore` was rejected because its keys and TTL semantics fit poorly, and an append-only JSONL file is what the export reads directly. SQLite was rejected to keep the code consistent with the repo's stdlib file stores.
- **In-memory duplicate set.** The file is read once, on first use, and the set holds normalised addresses. A check-and-append under one `threading.Lock` makes two near-simultaneous submissions of the same address store once (spec edge case). The lock serialises within the single `serve.py` process; running several server processes on one file is unsupported and documented.
- **Server-side Post/Redirect/Get.** The approved screens use `<a>` stand-ins for Submit. They are built as a real `<form method="post" novalidate>` with a `<button type="submit">`, so the journey needs no script. A refresh on the confirmation page does not resubmit.
- **"Submitting" state through a static same-origin script.** `GET /newsletter/form.js`, allowed by `script-src 'self'`, disables Submit and shows the busy label on submit. No inline script is used, so the CSP stays strict.
- **Byte-identical confirmation for new and known addresses** (FR2, and the "Returning subscriber" persona in the design).
- **Export is a CLI only** (spec decision Q2). Scenario 7 is enforced by a test that no newsletter path returns the list.
- **Styles inline per page.** `tokens.css` and the screen markup are ported from the SCRUM-102 screens into `newsletter/pages.py` as inline `<style>`, as the guestbook page does. No new static-file route is added beyond `form.js`.

## 7. Risks, constraints and assumptions

- **Repo gates:** the repo has no `.factory/`, `CLAUDE.md`, `AGENTS.md` or CI. Every ticket must keep `python -m unittest discover -s tests` and `python3 smoke_test.py` passing (README; spec §6).
- **Regression (scenario 4):** "answer exactly as before" is read as: `/`, `/jungle`, `/healthz`, `/guestbook` and `/kv/` keep their status codes, headers and behaviour.
  - `GET /` still returns the exact bytes of `docs/index.html`, and that file gains the footer (R1 requires it). This is the only intended change to an existing page.
  - `tests/test_healthz.py:155` and `tests/test_guestbook.py:501` assert `serve.ROUTES` is unchanged, so the newsletter routes must not be added to `ROUTES`.
- **Personal data:** names and emails sit in a local file and the export.
  - The server binds to `127.0.0.1` by default.
  - With `HOST=0.0.0.0` anyone on the network can submit signups (RK1), but nobody can read them over HTTP.
  - The README warns about both.
- **Bots (RK1):** there is no challenge or rate limit in this story. The `signed_up_at` column lets the team count signups per hour.
- **Scale:** the in-memory set grows by one address per signup. At this site's scale that is negligible. The export streams the file line by line.
- **GitHub Pages:** `docs/` also has `.nojekyll`. If it is published as a static site, the footer link `/newsletter` returns 404 there, because only `serve.py` serves the journey. Accepted, because the spec's site is `serve.py`.
- **Assumption: CSV encoding.** UTF-8 without a BOM. Risk: older Excel versions may show non-ASCII names wrongly when the file is double-clicked. Importing it as UTF-8, or using the mailing tool, works.
- **Assumption: formula guard.** The guard prefixes `'` to cells that start with `=`, `+`, `-`, `@`, a tab or a carriage return. Risk: the exported value differs from the stored value by that one character. This is documented in the README.
- **Assumption: one server process.** Running two `serve.py` processes on the same `NEWSLETTER_PATH` could store one address twice.
