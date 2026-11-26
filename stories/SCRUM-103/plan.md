# Implementation plan — Store newsletter signups and export them (SCRUM-103)

## Context

SCRUM-103 builds the newsletter signup journey end to end in `ophirgal/test-repo-for-halo`, on work branch `halo/feat/scrum-103-20261125-161220` off `main`. It adds a "Newsletter" footer link on `docs/index.html` and three screens served by `serve.py`: Welcome, a validated name-and-email form, and Confirmation. Each valid signup is stored once per address with its UTC time in a durable file. Marketing exports the list with a host-only CSV command. Acceptance criteria 1–7 in `spec.md` §5 cover: a new signup is stored and confirmed; a repeated address is confirmed and stored only once; the export gives one CSV row per signup; existing routes do not regress; the journey matches the approved designs at desktop and mobile widths; invalid input shows an inline error and stores nothing; no route returns the list. The approved requirement is `spec.md`, the design is `hld.md`, and the two work items (t1, t2) are in `work-items.md`. All three sit beside this file in `stories/SCRUM-103/`.

## Research findings

**Change surface (read on this branch).**
- `serve.py:87`: `ROUTES = {"/": INDEX, "/jungle": JUNGLE}` is the fixed-file table. `tests/test_healthz.py:155` and `smoke_test.py:130` assert it is exactly this. Newsletter routes therefore go in handler methods, as `_health` (`serve.py:152`) and `_guestbook` (`serve.py:169`) do.
- `serve.py:306` `do_GET` and `serve.py:321` `do_HEAD` chain `self._health() or self._guestbook()` before `_route()`. `serve.py:345` `do_POST` answers only `_guestbook()` and sends the stock 501 everywhere else. `serve.py:342` maps `do_PUT`/`do_DELETE` to `_kv_only`, which answers 501 outside `/kv/`. Newsletter `PUT`/`DELETE` therefore get 501 with no change.
- `serve.py:194` `_guestbook_post` is the POST template. It reads the body with `_kv_body()` (`serve.py:251`), which rejects a duplicate or invalid `Content-Length` with 400 and anything over `KV_MAX_BODY` (65536) with 413 before reading the body. It then checks `FORM_TYPE` (415) and runs `parse_qs(..., errors="strict")` (400 on bad UTF-8).
- `serve.py:184` `_guestbook_page` sends `text/html; charset=utf-8`, `nosniff` and `GUESTBOOK_CSP` (`serve.py:97`). The newsletter CSP adds `script-src 'self'` (hld §5), so it needs its own constant.
- `serve.py:351` `KVHTTPServer` holds the lazily built shared stores, each behind its own lock (`guestbook_store`, `serve.py:379`). The newsletter store follows the same pattern.
- `serve.py:1-60` is the module docstring. `tests/test_healthz.py`, `tests/test_http.py:421` and `tests/test_guestbook.py:520` assert needles in it. New text is added there; no existing text is removed.

**Pattern package.**
- `guestbook/__init__.py`, `guestbook/message.py`, `guestbook/store.py` and `guestbook/page.py` are the model.
- `guestbook/store.py:76` `append` shows the pattern to copy: lock, lazy `_load`, `a+b` open, newline repair, `flush` + `os.fsync`, and update memory only after a successful write.
- `guestbook/store.py:22` `_decode` shows how invalid lines are skipped, with one stderr warning that names the line number (`guestbook/store.py:65`).

**Tests and gate.**
- Every test is `unittest` under `tests/`. `tests/test_guestbook.py:203` `GuestbookHTTPTestCase` is the HTTP harness:
  - a temporary directory, with environment paths set through `mock.patch.dict`
  - `serve.make_server("127.0.0.1", 0, QuietHandler)`
  - `http.client` requests
  - `raw_send` for malformed requests
  - `standard_501` (`tests/test_guestbook.py:459`) to compare 501s with the stock handler
- `smoke_test.py` is a standalone HTTP checker. It starts `serve.make_server` and sets no store paths, so its requests use the default `./kv.log`/`./guestbook.jsonl`. Two of its checks constrain `docs/index.html`:
  - `smoke_test.py:139`: `GET /` must be byte-identical to `docs/index.html`.
  - `smoke_test.py:332-343`: the page may declare no width or min-width over 375 px. The regex also matches `@media (min-width: …px)`.
- The canonical gate (README "Tests"; spec §6; hld §7) is `python -m unittest discover -s tests`, then `python3 smoke_test.py`. The repo has no CI, no `.factory/`, no `CLAUDE.md`/`AGENTS.md` and no linter. Local Python is 3.13.1; `pyproject.toml` asks for ≥3.9.

**Design source.** The design is read from `origin/halo/feat/scrum-102-20261123-172706:stories/SCRUM-102/design/`. The inventory's "Based on" column gives each screen's source:
- **Footer link:** `docs/index.html`, changed in place. The page gains a footer with a "Newsletter" link, and its content is centred.
- **Welcome:** new. The heading is "Get our newsletter", followed by the pitch, a "Subscribe" button and "← Back to site".
- **Signup form:** new.
  - Shared elements: the heading "Subscribe to the newsletter", the stepper "Progress, step 2 of 3" and "← Back".
  - Name (`maxlength="80"`, hint "Up to 80 characters.") and Email (`type="email"`, hint "For example, name@example.com. We only use it to send the newsletter.").
  - Error texts: "Enter your name.", "Enter your email address." and "Enter an email address in the format name@example.com.". Each has an icon, an `sr-only` "Error: " prefix, `aria-invalid="true"`, `aria-describedby="<field>-error <field>-hint"` and `autofocus`.
  - Submitting state: Submit disabled, with a spinner and "Submitting…", and the fields read-only.
  - Submission-failed state: a `role="alert"` box, "Your signup didn’t go through", with the values kept.
- **Confirmation:** new. The heading is "You’re subscribed".
- **Styles and markup:** a 77-line `screens/tokens.css`. The markup uses `<a>` stand-ins for Submit.

**Unknowns left.**
- The design has no "name too long" error. It relies on `maxlength`, while spec FR0b asks for an error over 80 characters; this is resolved under the locked decisions below.
- The design's Confirmation copy names the visitor ("Thanks, Maya. …"), but hld §5 requires identical bytes for every visitor; also resolved under the locked decisions below.

## Locked decisions and assumptions

**Locked decisions.**
- **Scope:** the story builds the footer link and all three screens as well as storage and export (spec Q1). The export is a host command only, and no route returns signups (spec Q2, AC 7).
- **Package and storage:** a stdlib-only `newsletter/` package. The signup file is a JSON Lines file at `NEWSLETTER_PATH` (default `./newsletter.jsonl`), with records `{"t","n","e"}`, a process lock and an in-memory set of address keys (hld §2, §5, §6).
- **Validation and duplicates:**
  - Name: line breaks become spaces, trimmed, 1–80 code points; errors `name_empty` and `name_too_long`.
  - Email: trimmed; errors `email_empty` and `email_malformed`, by the pattern in hld §5, with at most 254 characters.
  - Duplicate key: the trimmed address with `str.lower()`, not `casefold()`. The first record is kept (hld §5; spec Q3).
- **HTTP contract:** routes, statuses, headers and CSP exactly as in the hld §5 table. A valid POST answers 303 to `/newsletter/thanks` for both a new and a known address, with an identical response.
- **Export contract:**
  - Command: `python3 -m newsletter export [-o FILE]`, writing UTF-8 with no BOM.
  - Rows: the header `name,email,signed_up_at`, then records oldest first.
  - Formula guard: a cell starting with `=`, `+`, `-`, `@`, a tab or a carriage return gets a leading `'`.
  - Exit codes: 0, 1 (with no partial FILE left) and 2 (hld §5; spec Q4).
- **`serve.ROUTES` stays unchanged**, and `docs/jungle.html` gets no footer (hld §7; `smoke_test.py` `JUNGLE_FORBIDDEN`).
- **Design copy and states** are locked: flow, screens, error texts, states and focus behaviour. The look is intent, ported into inline `<style>` (hld §6).
- **`name_too_long` stays a server error under Name**, because spec FR0b and t1/t2 require it. The design's "no name too long error" covers what the browser shows, since `maxlength` prevents the case there. The spec is the higher source on behaviour.

**Assumptions.**
- **A1 — Confirmation copy.** It drops the visitor's name and address ("Thanks, Maya…"). It keeps the heading "You’re subscribed" and a fixed message, because hld §5 and t2 require byte-identical Confirmation bytes for every visitor and scenario 7 forbids echoing stored data. Evidence: hld §5 "the same bytes for every visitor". If wrong, Confirmation would need a per-request name, which breaks the "identical response" decision and needs a hld change.
- **A2 — Submitting state.** The design shows the fields read-only during submitting. `form.js` sets `readOnly` on both inputs as well as disabling Submit. Evidence: `signup-form.submitting.html:17,22`. If wrong, only cosmetic.
- **A3 — Submission-failed copy.** The design text "We couldn’t reach the server" is kept verbatim for the server-rendered 500 page. Evidence: the state is locked. If wrong, the copy changes, not the behaviour.
- **A4 — Footer CSS in `docs/index.html`.** Sizes use `rem`/`%` and no `px` width or media query above 375 px, so `smoke_test.py:332` stays green. If wrong, the smoke check fails.
- **A5 — Smoke checks write nothing to the working directory.** The new smoke checks use `GET`/`HEAD` only, plus one invalid `POST` that stores nothing. The valid-POST path is covered by `tests/test_newsletter_http.py` with a temporary `NEWSLETTER_PATH`. If wrong, the smoke run leaves a `newsletter.jsonl` behind; it is gitignored.

## Solution proposal

Mirror the SCRUM-126 guestbook architecture. The `newsletter/` package holds every rule, the storage, the rendering and the export, and knows nothing about HTTP. `serve.py` gains one routing method, `_newsletter()`, plus a lazily built shared store, and leaves every existing branch byte-for-byte alone.

- **`newsletter/signup.py`:**
  - `normalise_name`, which reuses the line-break handling of `guestbook.message.normalise`. Call it, or copy its separator set, so the two rules stay identical.
  - `check(name_raw, email_raw)`, which returns the cleaned values and a dict of field → error code.
  - `address_key(email)`, which is `strip().lower()`.
  - The email rule is one compiled `re.fullmatch` that follows hld §5: no whitespace, exactly one `@`, a non-empty local part, a domain of two or more non-empty dot-separated labels, and `len <= 254`.
- **`newsletter/store.py`, `SignupStore(path)`:**
  - `Record(time, name, email)`.
  - `add(name, email, now=None)`, which returns `True` when the address is new and `False` when it is already known. Under one `threading.Lock` it lazy-loads the file and the key set, checks the key, appends and fsyncs, then adds the key. A write `OSError` propagates and leaves memory untouched.
  - `records()`, which streams valid records oldest first and never creates the file.
  - `add` re-checks the input with `signup.check` and raises `ValueError` on invalid input. FR3, "never stored whatever the caller", is then enforced at the store, not only in `serve.py`.
- **`newsletter/export.py` and `newsletter/__main__.py`:**
  - `argparse` with one subcommand, `export`, and `-o FILE`.
  - Writes through `csv.writer` (default dialect, `\r\n`) with the formula guard applied per cell.
  - For `-o`, writes to a temporary file in the target's directory and `os.replace`s it on success. This removes the temporary file on error, so a failure leaves no partial FILE.
  - Exit 1 with one stderr line for an `OSError` on read or write. Usage errors exit 2, which is argparse's default.
- **`newsletter/pages.py`:**
  - `render_welcome()`, `render_form(values=None, errors=None, failed=False)`, `render_thanks()` and `FORM_JS` (bytes).
  - One shared inline `<style>`, ported from `screens/tokens.css` and the screen markup.
  - The design's `<a>` Submit stand-ins become `<form method="post" action="/newsletter/signup" novalidate>` with `<button type="submit">`. The Welcome "Subscribe" stays a link to `/newsletter/signup`.
  - Every echoed value goes through `html.escape`.
  - `autofocus` goes on the first field in error.
- **`serve.py`:**
  - Add the constants `NEWSLETTER_ROUTE = "/newsletter"`, `NEWSLETTER_SIGNUP`, `NEWSLETTER_THANKS`, `NEWSLETTER_JS`, `DEFAULT_NEWSLETTER_PATH` and `NEWSLETTER_CSP`.
  - Add `_newsletter()`, which matches the exact paths. `/newsletter/` and every other look-alike falls through to the existing 404.
  - Add `_newsletter_post()`, which copies `_guestbook_post`'s body, type and UTF-8 handling (do not refactor the guestbook code to share it), validates the fields and calls `store.add`. It answers 303, 400 or 500 as in the hld.
  - Add `KVHTTPServer.newsletter_store()`.
  - Chain `_newsletter()` after `_guestbook()` in `do_GET`, `do_HEAD` and `do_POST`. In `do_POST` it answers only `/newsletter/signup`, so a POST to any other newsletter path still gets the stock 501.

**Alternatives rejected.**
- `kvstore` as storage: its keys and TTL semantics fit poorly (hld §6).
- SQLite: it is inconsistent with the repo's file stores (hld §6).
- A shared `_form_post` helper refactored out of the guestbook: it touches tested guestbook code beyond scope.
- Adding entries to `ROUTES`: tests pin that table.
- An export URL: forbidden by spec Q2 and AC 7.
- Client-side-only validation: FR3 requires server enforcement.

## Ordered implementation steps

**t1 — rules, store and export**

1. **Signup rules.** Add `newsletter/signup.py` and `newsletter/__init__.py` (export `check`, the error-code constants, `MAX_NAME`, `address_key`, `SignupStore`, `Record` and `export`).
   - Covers the name and email rules, the error codes and `address_key`.
   - Advances AC 6 (rule half) and FR3.
   - Test layer: unit tests in new `tests/test_newsletter_store.py`, class `SignupRulesTest`. Cover every valid and malformed example listed in t1, both fields failing together, 80 and 81 code points with Hebrew, and line breaks becoming spaces.
2. **Signup store.** Add `newsletter/store.py`.
   - Covers the JSONL format `{"t","n","e"}` (UTC to the second, `Z`, compact `ensure_ascii=False`), the lazy load, missing-file handling, bad-line warnings, newline repair, fsync, the key set and the lock.
   - Advances AC 1 (store half), AC 2 (store half) and FR6.
   - Test layer: unit tests in `tests/test_newsletter_store.py`, class `SignupStoreTest`:
     - the record format;
     - a new address adds one line, and a duplicate in another case or with spaces adds nothing and keeps the first name and time; `ß@x.co` and `ss@x.co` are both stored;
     - 20 threads adding the same address leave one line;
     - a fresh store on the same file knows earlier addresses;
     - reading a missing file creates nothing, including in a missing directory;
     - bad, blank and torn lines are skipped with a stderr warning naming the line number;
     - newline repair before the next append;
     - an append into a missing directory raises `OSError`, after which the address is not in memory;
     - invalid input raises `ValueError` and writes nothing.
3. **CSV export.** Add `newsletter/export.py` and `newsletter/__main__.py`.
   - Advances AC 3 and FR4/FR5.
   - Test layer: unit tests plus `subprocess` runs of `sys.executable -m newsletter export` (as `tests/test_guestbook.py` already imports `subprocess`) in new `tests/test_newsletter_export.py`:
     - three stored signups give a header and exactly three rows, read back with `csv.reader`;
     - an empty or missing store gives the header only;
     - commas, quotes and non-ASCII text round-trip;
     - the formula guard covers all six leading characters;
     - `-o FILE` writes UTF-8 with no BOM and exits 0;
     - an unwritable FILE (missing directory) exits 1 with one stderr line and leaves no file;
     - an unreadable `NEWSLETTER_PATH` (a directory) exits 1;
     - an unknown subcommand exits 2.
4. **Repo housekeeping.** Add `newsletter.jsonl` to `.gitignore`. Add a README section "## Newsletter export" covering the command, `NEWSLETTER_PATH`, the default `./newsletter.jsonl`, the columns, the formula guard, the one-server-process limit and the personal-data note.
   - Advances AC 3 (operability).
   - Test layer: a `DocsTest` in `tests/test_newsletter_export.py` with README needles and the `.gitignore` entry, as `tests/test_guestbook.py:514-526` does.

**t2 — journey**

5. **Pages.** Add `newsletter/pages.py` and export the render functions from `newsletter/__init__.py` (additive only).
   - Port `screens/tokens.css` and the markup of `welcome.default`, every `signup-form.*` state and `confirmation.default` from the SCRUM-102 branch, all marked new.
   - Each page has `<meta name="viewport" content="width=device-width, initial-scale=1">`, labels for every input, the design's focus order (Back → stepper → fields → Submit) and the approved tokens for contrast.
   - Add the `name_too_long` text under Name in the approved error style.
   - `FORM_JS` disables Submit, shows "Submitting…" with the spinner and makes the fields read-only on `submit` (A2).
   - Advances AC 5, AC 6 (display) and R4.
   - Test layer: unit tests in new `tests/test_newsletter_http.py`, class `PagesTest`:
     - the approved texts for each state;
     - `aria-invalid`/`aria-describedby`/`autofocus` on the first error only, with both errors at once;
     - escaping of `<script>` and `"`;
     - the viewport meta;
     - no fixed width over 320 px in the CSS (a static check, as `smoke_test.py:332` does);
     - `render_thanks()` contains no input;
     - `FORM_JS` holds no inline-unsafe constructs.
   - The 4.5:1 and 3:1 contrast is checked by a unit test that computes the WCAG ratio of the token colour pairs used for text and focus (stdlib arithmetic in the test only). Rendering at 320 px and desktop widths is a manual browser check, as `smoke_test.py:315` already notes for the index page.
6. **Routing.** In `serve.py`:
   - Add the constants, `_newsletter`, `_newsletter_page` (headers per hld §5) and `_newsletter_post`.
   - Add `KVHTTPServer.newsletter_store()` and its lock.
   - Chain `_newsletter()` in `do_GET`, `do_HEAD` and `do_POST`.
   - Document the routes and `NEWSLETTER_PATH` in the module docstring, adding to it only.
   - Advances AC 1, AC 2, AC 6 and AC 7.
   - Test layer: HTTP tests in `tests/test_newsletter_http.py` on a copy of the `GuestbookHTTPTestCase` harness, with `NEWSLETTER_PATH` in a temporary directory:
     - GET and HEAD on all four routes;
     - a valid POST → 303 to `/newsletter/thanks` and one record;
     - a repeat in another case or with spaces → 303 with headers and body identical to the first answer, and still one record;
     - each invalid combination → 400, values kept and escaped, nothing stored;
     - 81 code points → 400;
     - a store `OSError` (path in a missing directory) → 500 in the failed state with values kept;
     - bad or duplicate Content-Length and bad UTF-8 → 400 (`raw_send`), over 64 KiB → 413, wrong type → 415;
     - the content type, `nosniff` and the exact CSP;
     - a query string is ignored;
     - the look-alikes `/newsletter/`, `/newsletter/export.csv`, `/newsletter/thanks/` and `/newsletters` → 404;
     - `PUT`/`DELETE`/`POST` to other newsletter paths equal `standard_501`;
     - scenario 7: after storing a unique name and email, GET every newsletter path and the look-alikes, `/`, `/jungle`, `/healthz`, `/guestbook` and `/kv/`, and assert no body contains either value.
7. **Footer link.** Change `docs/index.html` in place to add `<footer><a href="/newsletter">Newsletter</a></footer>` after `<main>` and centre the content, per `site-page-footer-link.default`. Use only `rem`/`%` sizes (A4) and keep `<main><h1>Hello World</h1></main>` and the `<title>`. Leave `docs/jungle.html` untouched.
   - Advances AC 5.
   - Test layer: an HTTP test asserting `GET /` equals the file's bytes and contains the link, plus a check in `smoke_test.py`.
8. **Regression.**
   - Advances AC 4 and FR7.
   - Test layer: the existing suites `tests/test_http.py`, `tests/test_guestbook.py`, `tests/test_healthz.py` and `smoke_test.py` stay unchanged and green.
   - Add a `RegressionTest` in `tests/test_newsletter_http.py`: `/jungle` equals its bytes; `/healthz` gives the same body; `/guestbook` GET/POST statuses are unchanged; `/kv/` gives 200 `[]`; `POST /` and `POST /jungle` equal `standard_501`; `serve.ROUTES` is unchanged.
9. **Smoke checks and README.**
   - Add a `run_newsletter_checks(base, checks)` to `smoke_test.py`, called from `run_checks`. It covers:
     - GET status and content type of `/newsletter`, `/newsletter/signup` and `/newsletter/thanks`;
     - the footer link on `/`;
     - a 404 for `/newsletter/export.csv`;
     - an empty-field POST → 400 with nothing stored (A5).
   - Add README section "## Newsletter signup (`/newsletter`)", covering the routes, `NEWSLETTER_PATH`, the identical confirmation and the `HOST=0.0.0.0` warning (anyone can submit; no route can read). Do not change t1's section.
   - Advances AC 4, AC 5 and AC 7.
   - Test layer: the smoke run itself, plus README needles in `tests/test_newsletter_http.py`.

**Invariants the steps must hold.**
- No authentication exists or is added. Network exposure is controlled by `HOST`, and the README warns about it.
- Concurrency: one lock covers the check and the append (step 2). A single process is assumed.
- Idempotency: a repeated address is a no-op with an identical answer (steps 2 and 6).
- Validation runs on the server and again in the store (steps 1, 2 and 6).
- Dependencies: the standard library only, with nothing to install.
- Generated deliverables: none. The CSS and markup are hand-ported from the design branch and committed as source.

## Work-item mapping

| Step | Work item |
|---|---|
| 1. Signup rules | t1 — Newsletter signup rules, durable signup store and CSV export command |
| 2. Signup store | t1 — Newsletter signup rules, durable signup store and CSV export command |
| 3. CSV export | t1 — Newsletter signup rules, durable signup store and CSV export command |
| 4. `.gitignore` + README export section | t1 — Newsletter signup rules, durable signup store and CSV export command |
| 5. Pages | t2 — Newsletter signup journey: footer link, Welcome, form and Confirmation served by serve.py |
| 6. Routing in `serve.py` | t2 — Newsletter signup journey: footer link, Welcome, form and Confirmation served by serve.py |
| 7. Footer link | t2 — Newsletter signup journey: footer link, Welcome, form and Confirmation served by serve.py |
| 8. Regression | t2 — Newsletter signup journey: footer link, Welcome, form and Confirmation served by serve.py |
| 9. Smoke checks + README journey section | t2 — Newsletter signup journey: footer link, Welcome, form and Confirmation served by serve.py |

## Verification and CI gate

- **Canonical gate, in order** (README "Tests"; spec §6):
  1. `python -m unittest discover -s tests`
  2. `python3 smoke_test.py`
- **Where it runs:** the repo has no provider CI, so this gate at the exact head is the only gate. Both steps run in a pod with the standard library only: no network, no browser and no extra packages.
- **The one local run** is the implement turn's gate run (`run-tests-gate.sh --run` on the committed SHA). Nothing else is run by hand beside it.
- **Each work item passes the gate on its own.** t1 adds only the package, its two test files, `.gitignore` and README. t2 then adds the rest.
- **Test layers:**
  - `unittest` unit tests: rules, store, export, pages and contrast arithmetic.
  - `unittest` HTTP tests against an ephemeral `serve.make_server`.
  - `subprocess` CLI tests.
  - The smoke HTTP checker.
- **Outside the gate:** the visual check at 320 px and desktop widths, and keyboard and screen-reader focus order in a real browser, cannot run in a pod. They remain a manual review item against the SCRUM-102 screens, as the existing index-page check already is (`smoke_test.py:315`).
- **No obligations:** the repo has no `.factory/testing.md` or `.factory/delivery-assets`, and no binaries are added.
- **Done means:**
  - Both commands exit 0.
  - The unittest run shows the new newsletter tests run with zero failures, errors or skips.
  - The existing guestbook, healthz, http and kv suites pass unchanged.
  - `smoke_test.py` prints `OK: N checks passed`, including the new newsletter checks.

## Risks and scope guards

**Risks.**
- **Footer vs smoke width check:** a `px` media query or width over 375 in `docs/index.html` fails `smoke_test.py:332`. Mitigation: A4.
- **`ROUTES` assertions:** adding newsletter paths to `ROUTES` fails `tests/test_healthz.py:155` and `smoke_test.py:130`. Mitigation: handler-method routing only.
- **501 parity:** `do_POST` must still produce the stock 501 for `/`, `/jungle`, `/healthz`, `/guestbook/` and other newsletter paths. Mitigation: `_newsletter()` returns False for anything except the exact paths, and step 6 compares with `standard_501`.
- **Design vs hld on Confirmation copy:** resolved by A1, and noted for the reviewer.
- **Bots (RK1):** there is no rate limit or challenge. The `signed_up_at` column enables counting signups per hour.
- **Personal data in `newsletter.jsonl`:** gitignored, and documented in the README.
- **Multiple server processes on one file** can store a duplicate. This is documented as unsupported.

**Scope guards — the implement phase must NOT:**
- edit `guestbook/`, `kvstore/`, `linkcheck/`, `src/ledger/`, `docs/jungle.html` or `stories/SCRUM-103/{spec,hld,work-items}.md`;
- refactor `_guestbook_post` or `_kv_body` to share code;
- change any existing route, status, header or body, `GUESTBOOK_CSP` or the existing docstring text;
- add entries to `serve.ROUTES`;
- add an export URL, an authentication or password mechanism, a confirmation email, unsubscribe, a consent checkbox, a rate limit or a bot challenge;
- add third-party dependencies, a static-file route beyond `/newsletter/form.js`, or a new test framework or CI pipeline;
- merge or rebase onto `origin/halo/feat/scrum-102-20261123-172706`, which is read for the design only;
- delete, skip or weaken any existing test or smoke check to make the gate green. A failing check is reported blocked, not edited away.

## Clarification outcomes

None. The developer has standing instructions to decide open points without asking. The design-versus-spec points (the `name_too_long` error, Confirmation copy, the read-only fields while submitting) are settled above as locked decisions or as assumptions A1–A3.
