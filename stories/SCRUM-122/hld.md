# SCRUM-122 — High-Level Design: `/healthz` endpoint in `serve.py`

## 1. System Overview

- **What:** one new fixed route, `GET /healthz` and `HEAD /healthz`, in the existing standard-library server `serve.py`. It answers `200`, `Content-Type: application/json`, body `{"status": "ok"}`.
- **Problem:** today `/healthz` answers the stock `404` HTML page (verified by running the server: `GET /healthz` → 404 `text/html`). No cheap probe URL exists: `/` returns a full HTML page and `/kv/` depends on store state (`serve.py:174-189`, 503/500).
- **Responsibilities:** answer the probe; leave every existing path's answer byte-identical; a unittest and README docs.

## 2. Architecture Overview

- Single process, `http.server.ThreadingHTTPServer` subclass `KVHTTPServer` (`serve.py:229-258`) with handler `RootOnlyHandler` (`serve.py:94-226`). No new module, no new dependency.
- Dispatch today, in `do_GET` / `do_HEAD` (`serve.py:193-215`): `/kv/` prefix → store; else exact-path lookup in `ROUTES` (`serve.py:63`, files served as `text/html`); else `send_error(404)`. `PUT`/`DELETE` go through `_kv_only` (`serve.py:217-226`) → stock `501` outside `/kv/`. Other methods (e.g. `POST`) have no `do_*` and get the stock `501`.
- The health route is a **third branch in `do_GET`/`do_HEAD`**, matched on the exact URL path (query ignored, same `urlsplit(...).path` as `_route`, `serve.py:105-107`), answered from a constant JSON body. It never calls `self.server.kv_open()`.
- It is deliberately **not** an entry in `ROUTES`: that table maps paths to HTML files, and `tests/test_http.py:351-352` (`test_routes_table_unchanged`) pins it to exactly `{"/", "/jungle"}`.
- Ownership: all changes live in `ophirgal/test-repo-for-halo` — `serve.py`, a new test file under `tests/`, `README.md`.

## 3. Data Flow Design

- Synchronous only. Probe → `GET|HEAD /healthz[?query]` → handler thread → exact path equals `/healthz` → `200` + headers `Content-Type: application/json`, `Content-Length` → body written for `GET` only.
- No state is read or written: no store open, no file read, no `kv.log` created. Answer is the same whatever the store's state (missing, corrupt → `/kv/` 503, unopenable → `/kv/` 500).
- Down = no HTTP answer (connection refused/timeout); there is no "unhealthy" response.

## 4. Component Breakdown

| Component | Responsibility | In / Out | Repo |
|---|---|---|---|
| Health branch in `RootOnlyHandler.do_GET` / `do_HEAD` (`serve.py`) | Answer exact `/healthz` with the fixed JSON | In: method + path. Out: 200 JSON (GET) / headers only (HEAD) | `ophirgal/test-repo-for-halo` |
| `serve.py` module docstring (`serve.py:1-37`) | List `/healthz` beside the other routes; must keep the words `smoke_test.py:276-279` and `tests/test_http.py:421-424` check for and avoid "root-only"/"exactly one document" | — | same |
| New test module `tests/test_healthz.py` | Start the server on port 0 (`make_server(..., 0, ...)`, `serve.py:261-263`) and check GET/HEAD, query, look-alikes, other methods, store independence | — | same |
| `README.md` | New `/healthz` section with a curl example and what it answers | — | same |

## 5. Interface Contracts

| Request | Status | Headers | Body |
|---|---|---|---|
| `GET /healthz` (any query string) | 200 | `Content-Type: application/json`, `Content-Length` matching the body | `{"status": "ok"}` — parses to an object with exactly one key `status` = `"ok"`; ASCII |
| `HEAD /healthz` (any query string) | 200 | same as GET, `Content-Length` = GET body length | none |
| `GET`/`HEAD` `/healthz/`, `/healthz.json`, `/HEALTHZ`, `/health`, `/healthzx` | 404 | unchanged stock `text/html` error | unchanged |
| `PUT`/`DELETE`/`POST` `/healthz` | 501 | unchanged stock answer (identical to a stock `BaseHTTPRequestHandler`, as `tests/test_http.py:310-331` compares) | unchanged |
| Every other existing path/method | unchanged | unchanged | unchanged |

No cross-repo contract; no event schema.

## 6. Key Technical Decisions

- **Separate branch, not a `ROUTES` entry.** `ROUTES` serves files as HTML and is pinned by an existing test; a JSON route there would need a content-type special case and break that test. Alternative (generalise `ROUTES` to carry content types) rejected as a change to existing routes beyond scope.
- **Exact match on the parsed path**, the same way `_route` does — query ignored, look-alikes 404 (spec D1).
- **No store access** on the health path, so it is independent of store state and never creates `kv.log` (spec D2/FR4).
- **HEAD mirrors GET headers** (spec D3), matching how `/`, `/jungle` and `/kv/` already behave.
- **PUT/DELETE/POST untouched** (spec D4): `_kv_only` and the missing `do_POST` are not changed.
- **New test file `tests/test_healthz.py`** rather than growing `tests/test_http.py` (SCRUM-119's file): keeps the change reviewable and its ownership clear. It may reuse the same pattern (quiet handler subclass, `make_server("127.0.0.1", 0, ...)`, `http.client`), copied rather than imported, since `tests/` is not a package.
- Body bytes spacing is not part of the contract (spec §4); `{"status": "ok"}` as written in the spec is the recommended literal.

## 7. Risks & Constraints

- **Regression risk** is the main one: the branch must sit so `/kv/` and `ROUTES` dispatch are untouched. Guarded by the existing `tests/test_http.py` (`RegressionTest`, incl. running `smoke_test.py`) and `smoke_test.py` itself (87 checks, passing at `cb04466`).
- **Docstring checks:** `smoke_test.py:276-279` rejects "root-only"/"exactly one document" in `serve.__doc__`; `tests/test_http.py:421-424` requires `/kv/`, `KV_PATH`, `./kv.log`, `python3 serve.py`, `PORT=`, `HOST=` in it. The docstring edit must keep both true.
- **README check:** `tests/test_http.py:428-435` requires existing README strings; the new section is additive.
- **Security/exposure:** no auth (out of scope); binds to `127.0.0.1` by default; answer reveals nothing beyond "ok". Constant body, no input reflected, no file access — no new attack surface.
- **Performance:** constant-time, no I/O beyond the socket; runs on the existing per-request thread.
- **Pre-existing, unrelated:** at `cb04466`, `python -m unittest discover -s tests` reports 3 import errors (`tests/test_ledger_*.py` need `pytest`, which is not installed in this environment). Not caused or fixed by this story; the gate for this story is that `tests/test_healthz.py`, `tests/test_http.py` and `smoke_test.py` pass.

## 8. Assumptions & Verified Facts

- Verified by running the server (Python 3.12): today `GET`/`HEAD /healthz`, `/healthz?x`, `/healthz/` → 404 `text/html`; `PUT`/`POST /healthz` → 501. The spec's description of the code matches the code.
- Repo has no `AGENTS.md`, `CLAUDE.md`, `.factory/` or CI workflow; gates are the README's `python -m unittest discover -s tests` and `python3 smoke_test.py`.
- `pyproject.toml` declares `requires-python >=3.9`; the design uses only `http.server`/`json`/`urllib.parse` behaviour stable across 3.9+.
- No open engineering question. Spec decisions D1–D4 are adopted as written.
