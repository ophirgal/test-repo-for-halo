# SCRUM-122 — Implementation plan: `/healthz` endpoint in `serve.py`

## Context

SCRUM-122 adds a fixed `GET /healthz` and `HEAD /healthz` route to the standard-library server `serve.py`. The route answers `200`, `Content-Type: application/json`, body `{"status": "ok"}`, and leaves every existing answer unchanged. Acceptance criteria in brief: AC1 GET answers 200 JSON `{"status": "ok"}`; AC2 HEAD answers 200 with no body; AC3 no existing path changes and `smoke_test.py` still passes; AC4 a unittest under `tests/` covers AC1/AC2 on a free port; AC5 `README.md` documents the route with a curl example. The change lands in `ophirgal/test-repo-for-halo` on the work branch `halo/feat/scrum-122-20261124-075743`, cut from `main`. The approved requirement is `spec.md`, the design is `hld.md`, and the one work item (`t1`) is in `work-items.md`, all beside this file in `stories/SCRUM-122/`.

## Research findings

**Change surface (facts, read at `bd03b61`):**
- `serve.py:193-204` `do_GET`: `/kv/` prefix → `_kv_dispatch`; otherwise `_route()` (`serve.py:105-107`, exact match of `urllib.parse.urlsplit(self.path).path` against `ROUTES`); a miss → `self.send_error(404)`.
- `serve.py:206-215` `do_HEAD`: the same dispatch, headers only, through `_send_index_headers` (`serve.py:109-113`, `text/html; charset=utf-8`).
- `serve.py:217-226` `_kv_only` is bound to `do_PUT`/`do_DELETE`, and answers `send_error(501, "Unsupported method (%r)" % self.command)` outside `/kv/`. There is no `do_POST`, so the stock `BaseHTTPRequestHandler` gives `POST` its 501.
- `serve.py:63` `ROUTES = {"/": INDEX, "/jungle": JUNGLE}`. The route table maps paths to HTML files only.
- `serve.py:124-136` `_kv_send` already has the JSON-response pattern: `send_response`, `Content-Type: application/json`, `Content-Length`, `end_headers`, and the body written unless `self.command == "HEAD"`. Its body format is compact (`separators=(",", ":")`). That format does not match the spec literal `{"status": "ok"}`, so `_kv_send` is not reused.
- `serve.py:1-37` is the module docstring that documents the routes and usage.
- `serve.py:238-253` `KVHTTPServer.kv_open()` is the only path that opens or creates `KV_PATH`. The health branch must not call it.
- `serve.py:261-263` `make_server(host, port, handler)`: port `0` picks an ephemeral port.

**Contracts that pin existing behaviour (must keep passing unmodified):**
- `tests/test_http.py:351-352` `test_routes_table_unchanged` pins `serve.ROUTES == {"/": serve.INDEX, "/jungle": serve.JUNGLE}`.
- `tests/test_http.py:334-349` `test_non_kv_paths_unchanged`: 404 `text/html` for look-alikes, and 501 bodies identical to a stock handler (`standard_501`, `tests/test_http.py:310-332`).
- `tests/test_http.py:354-362` runs `smoke_test.py` as a subprocess and asserts that no store file is created.
- `tests/test_http.py:421-424` requires `/kv/`, `KV_PATH`, `./kv.log`, `python3 serve.py`, `PORT=`, `HOST=` in `serve.__doc__`.
- `smoke_test.py:245-248` rejects `root-only` and `exactly one document` (case-insensitive) in `serve.__doc__`. `smoke_test.py:276-282` requires `python3 serve.py`, `PORT=`, `HOST=`.
- `smoke_test.py:22-39` lists 404 paths. `/healthz` is not among them.
- README needles: `tests/test_http.py:428-435` and `tests/test_cli.py:295-300`. The change only adds README text, so both stay true.

**Test layers and gate:**
- Unit/integration: `unittest`, discovered with `python -m unittest discover -s tests` (README "Tests"). `tests/` is not a package. `import serve` resolves because the command runs from the repository root. `tests/test_http.py:21-68` holds the in-process pattern: `QuietHandler`, `make_server("127.0.0.1", 0, ...)`, a daemon `serve_forever` thread, `http.client`, and `KV_PATH` patched into a temporary directory.
- Smoke: `python3 smoke_test.py` (stand-alone HTTP checks).
- The repository has no `.factory/`, `AGENTS.md`, `CLAUDE.md`, `.github/` or other CI configuration (checked with `ls -a`).

**Exists versus new:** `serve.py` and `README.md` are edited. `tests/test_healthz.py` is new. No other file changes.

**Remaining unknowns:** none that block the work. One gate risk is a pre-existing condition: `tests/test_ledger_*.py` import `pytest`, which `hld.md` §7 records as not installed in this environment (see Verification and Risks).

## Locked decisions and assumptions

**Locked decisions:**
- Exact-path match on the parsed path, the same way as `_route`. A query string is ignored, and look-alikes (`/healthz/`, `/healthz.json`, `/HEALTHZ`, `/health`, `/healthzx`) stay stock 404. Source: `spec.md` FR3/D1, `work-items.md` t1.
- The answer does not depend on the store: no `kv_open()` call, `200` even when `/kv/` answers 503 or 500, and the store file is never created. Source: `spec.md` FR4/D2, `hld.md` §6.
- `HEAD` sends the same `Content-Type` and `Content-Length` as `GET`, with no body. Source: `spec.md` FR2/D3.
- `PUT`/`DELETE`/`POST` on `/healthz` keep the stock 501, so `_kv_only` stays untouched and no `do_POST` is added. Source: `spec.md` FR5/D4.
- The route is a separate branch in `do_GET`/`do_HEAD`, not a `ROUTES` entry. Source: `hld.md` §2 and §6, plus the `tests/test_http.py:351-352` contract.
- The test lives in the new file `tests/test_healthz.py`. Its helpers are copied from `tests/test_http.py` rather than imported. Source: `hld.md` §6.
- Standard library only, no change to `pyproject.toml`, no other new route. Source: `spec.md` §2, `work-items.md` t1.

**Assumptions:**
- The body bytes are `b'{"status": "ok"}'`, the spec literal. Evidence: `spec.md` FR1 and `hld.md` §6 call the spacing non-contractual and recommend this literal. If wrong, only the byte-level check in the test changes, because the test asserts the parsed JSON.
- `GET` sends no `Cache-Control` header or other extra header beyond `Content-Type` and `Content-Length` (plus the `Server`/`Date` headers that `send_response` adds itself). Evidence: no source asks for more. If wrong, it is an additive header change.
- The health check sits after the `/kv/` check and before `_route()`. That order is safe because `/healthz` matches neither `/kv/` nor `ROUTES`. If the order were wrong, `/kv/` and `ROUTES` behaviour would still be unaffected, because the paths do not overlap.

## Solution proposal

Add a third branch to `RootOnlyHandler`'s dispatch. Define two module constants next to `ROUTES`: `HEALTH_PATH = "/healthz"` and `HEALTH_BODY = b'{"status": "ok"}'`. Add one private method, `_health()`. It returns early when `urllib.parse.urlsplit(self.path).path != HEALTH_PATH`. Otherwise it sends `200`, `Content-Type: application/json` and `Content-Length: len(HEALTH_BODY)`, ends the headers, and writes the body only when `self.command != "HEAD"`. It returns `True` when it answered. `do_GET` and `do_HEAD` each call it once, after the `/kv/` branch and before `_route()`, and return when it answered. This mirrors the existing `HEAD` handling in `_kv_send` and keeps one code path for both methods, so the HEAD headers cannot drift from GET's.

Key design properties:
- The branch never touches `self.server`, the file system or request input beyond the path. That gives FR4 independence from the store and adds no new attack surface.
- `ROUTES`, `_route`, `_send_index_headers`, `_kv_*` and `_kv_only` stay byte-identical, so every existing answer stays the same (AC3).
- The docstring gains one short paragraph on `/healthz`. All existing text is kept, so both docstring checks stay true.

Alternatives rejected:
- Add `/healthz` to `ROUTES`. Rejected because that table serves files as `text/html` and `tests/test_http.py:351-352` pins it.
- Generalise `ROUTES` to carry content types or handlers. Rejected as a refactor of existing routes beyond scope.
- Reuse `_kv_send`. Rejected because its compact separators produce `{"status":"ok"}` rather than the spec literal, and it couples the health route to the `/kv/` helper.
- Add the tests to `tests/test_http.py`. Rejected in `hld.md` §6, which keeps SCRUM-119's file untouched.

## Ordered implementation steps

1. **Add the health branch to `serve.py`.** Add `HEALTH_PATH` and `HEALTH_BODY` near `serve.py:63`, and add `_health()` to `RootOnlyHandler`. Call it in `do_GET` (`serve.py:193`) and `do_HEAD` (`serve.py:206`) after the `/kv/` branch and before `_route()`. Do not call `self.server.kv_open()`. Leave `_kv_only`, `ROUTES` and the 404 path unchanged. Advances AC1, AC2 and AC3. Covered by the new `tests/test_healthz.py` (unittest) and the existing `tests/test_http.py` `RegressionTest` and `smoke_test.py`.
2. **Update the `serve.py` module docstring** (`serve.py:1-37`). Add a short paragraph after the fixed-pages paragraph: `GET`/`HEAD /healthz` answers `200` `application/json` `{"status": "ok"}`, a query string is ignored, and the answer is independent of the store. Adjust the opening paragraph so it does not claim the fixed pages and `/kv/` are the only non-404 answers. Keep `/kv/`, `KV_PATH`, `./kv.log`, `python3 serve.py`, `PORT=` and `HOST=`. Do not introduce "root-only" or "exactly one document". Optionally extend the `RootOnlyHandler` class docstring (`serve.py:95-96`) in the same way. Advances AC3 (docstring contract). Covered by `smoke_test.py:245-248`, `tests/test_http.py:421-424`, and a new docstring test in step 3.
3. **Create `tests/test_healthz.py`** (new, unittest, standard library only). Copy the minimal harness from `tests/test_http.py:21-68`: a quiet handler subclass, `KV_PATH` patched to a file in a `tempfile.TemporaryDirectory`, `serve.make_server("127.0.0.1", 0, ...)` on a daemon thread with `addCleanup` shutdown and `server_close`, and an `http.client` request helper. Add tests for:
   - GET `/healthz`: `200`, `Content-Type == "application/json"`, `Content-Length == len(body)`, `json.loads(body) == {"status": "ok"}`, and the body is ASCII (AC1).
   - HEAD `/healthz`: `200`, the same `Content-Type` and `Content-Length` as GET, and an empty body (AC2).
   - `/healthz?x=1` for GET and HEAD answers identically to `/healthz` (FR3).
   - Look-alikes `/healthz/`, `/healthz.json`, `/HEALTHZ`, `/health` and `/healthzx` answer 404 with `text/html` for GET and HEAD (FR3, AC3).
   - `PUT`, `DELETE` and `POST` `/healthz` answer status and body equal to a stock `BaseHTTPRequestHandler` (copy the `standard_501` approach from `tests/test_http.py:310-332`), and the status is 501 (FR5, AC3).
   - Store independence: with `KV_PATH` holding a log corrupt in the middle, built with `kvstore.encode_record` as in `tests/test_http.py:289-291`, `/kv/a` answers 503 and `/healthz` answers 200. With `KV_PATH` under a missing directory, `/kv/a` answers 500 and `/healthz` answers 200. After `/healthz`-only requests, the `KV_PATH` file does not exist (FR4).
   - The docstring mentions `/healthz` and still contains the needles that `tests/test_http.py:421-424` checks.
   - `README.md` contains `/healthz` and `curl -i http://127.0.0.1:8000/healthz` (AC5).

   Advances AC4 and covers AC1, AC2, AC3 and AC5. Layer: unittest via `python -m unittest discover -s tests`.
4. **Add a `/healthz` section to `README.md`.** Place it after the Hello World section and before "Key-value store (`/kv/`)", as `## Health check (`/healthz`)`. Include a curl example (`curl -i http://127.0.0.1:8000/healthz`) and a `curl -I` example for HEAD. State that the route answers `200` with `{"status": "ok"}` as `application/json`, that `HEAD` works too, that a query string is ignored, that it does not reflect the key-value store's state, that "down" means no answer, and that it has no authentication. Edit nothing else in the README. Advances AC5. Covered by the README test in step 3, and the existing README needle tests (`tests/test_http.py:428-435`, `tests/test_cli.py:295-300`) stay green.

Implicit invariants: authorization and tenancy do not apply (no auth by spec, a single local server). Concurrency: the branch is stateless and runs per request on `ThreadingHTTPServer` threads, with no lock needed. Idempotency: the answer is constant. Validation: only the parsed path is compared, and the query is ignored, never parsed or reflected. Error path: none on the branch itself, and unknown paths keep the stock 404. Dependencies: none to acquire, because everything is standard library and the existing `kvstore` package is in the repository. Generated deliverables: none.

## Work-item mapping

| Step | Work item | Title |
|---|---|---|
| 1 | t1 | Add GET/HEAD /healthz to serve.py with unittest and README docs |
| 2 | t1 | Add GET/HEAD /healthz to serve.py with unittest and README docs |
| 3 | t1 | Add GET/HEAD /healthz to serve.py with unittest and README docs |
| 4 | t1 | Add GET/HEAD /healthz to serve.py with unittest and README docs |

Every work item (only `t1`) maps to at least one step.

## Verification and CI gate

- **Canonical gate** (README "Tests", in order): `python -m unittest discover -s tests`, then `python3 smoke_test.py`, both run from the repository root. The repository has no provider CI configuration. The gate is these commands run at the exact committed head.
- **One local run:** dev-toolkit's `run-tests-gate.sh --run` on the committed SHA, which discovers the gate above. Do not also run the canonical commands by hand, and do not use a second worktree.
- **Layers:** unittest (new `tests/test_healthz.py`, plus the existing `tests/test_http.py`, which also runs `smoke_test.py` as a subprocess) and the stand-alone smoke script. Both run in a pod: they bind only `127.0.0.1` on ephemeral or local ports and need no network or external service.
- **What the gate must show:** `tests/test_healthz.py` is discovered and every test passes; `tests/test_http.py` passes unmodified; `python3 smoke_test.py` prints `OK:` and exits 0. Pre-existing condition: `tests/test_ledger_cli.py`, `tests/test_ledger_parse.py` and `tests/test_ledger_report.py` import `pytest`. Where `pytest` is absent, `unittest discover` reports 3 import errors (`hld.md` §7) that this story neither causes nor fixes. Report them as pre-existing and blocked with the gate's output. Do not install around them, skip them or edit them. No new error or failure beyond those three is acceptable.
- **`.factory/testing.md` and `.factory/delivery-assets`:** not present and not needed. No binary deliverable is added.
- **CI configuration:** none to add, because CI is not a deliverable of this story.

## Risks and scope guards

Risks:
- **Regression in dispatch.** A misplaced branch could shadow `/kv/` or `ROUTES`. Mitigation: exact equality on the parsed path, placed after the `/kv/` check. The existing `RegressionTest` and `smoke_test.py` guard the rest.
- **Docstring checks.** Rewording the docstring could drop a required needle or add a banned phrase. Mitigation: add text, keep existing lines, and rely on the step 3 docstring test plus the existing checks.
- **Accidental store creation.** Calling `kv_open()` would create `kv.log`. Mitigation: no `self.server` access in the branch, asserted by the store-independence test.
- **Test-harness leaks.** Mitigation: every server is shut down with `addCleanup`, and temporary directories are cleaned up, as in `tests/test_http.py`.
- **Pre-existing `pytest` import errors** in the ledger tests could be mistaken for this story's failures. Mitigation: name them explicitly in the gate report.

The implement phase must NOT:
- Edit `tests/test_http.py`, `smoke_test.py`, `kvstore/`, `docs/`, `linkcheck/`, `src/`, `pyproject.toml` or `.gitignore`.
- Change `ROUTES`, `_route`, `_send_index_headers`, any `_kv_*` method, `_kv_only`, `KVHTTPServer`, `make_server` or `main`, or add `do_POST`.
- Add `/readyz`, `/livez`, store status, version, uptime, authentication or any other route or field.
- Add a third-party dependency, a new test framework, or CI configuration.
- Make a check green by deleting, skipping, disabling or weakening it. That includes the ledger tests' `pytest` import errors, which are reported as pre-existing, not silenced.
- Reword unrelated README sections.

## Clarification outcomes

None. No question was needed: the spec's decisions D1–D4 and the HLD settle every open point, and the repository does not conflict with them.
