# Feature Specification Document — SCRUM-122: Add a /healthz endpoint to serve.py

## 1. Feature Overview

> **Status: READY_FOR_SPEC.** The story states five concrete, testable acceptance criteria and an explicit out-of-scope list. The few edge behaviours it leaves open were decided by the intake, following the developer's standing instruction that agents decide open points themselves. They are listed in §8 so they can be reviewed and reversed before implementation starts.

**Summary:** Add a fixed `GET /healthz` (and `HEAD /healthz`) route to the existing standard-library server `serve.py`. It answers `200` with the JSON body `{"status": "ok"}`, so a probe can tell the server is up. Everything `serve.py` serves today stays exactly as it is. A unittest covers the new route, and the README documents it with a curl example.

**Problem statement:** Today `serve.py` serves only `/`, `/jungle` and `/kv/...`; every other path, `/healthz` included, answers `404` (`serve.py:61`, `serve.py:203-224`). An operator has no dedicated, cheap URL whose success means "the server process is up and answering HTTP". Probing `/` returns a whole HTML page, and probing `/kv/` depends on the store's state (it answers `503` when the log is corrupt, `serve.py:13-22`).

**Target users / actors:**
- An operator who runs `serve.py` and points a probe (a monitoring check, a script, curl) at it.
- Anyone already using `/`, `/jungle` or `/kv/`. Their experience must not change.

**Sources:** The Jira story SCRUM-122 as filed (title, description, five acceptance criteria and its out-of-scope line), and the repository at `main` (`8f41c2f`): `serve.py`, `smoke_test.py`, `tests/test_http.py` and `README.md`. No Epic PRD, User Story Backlog or Confluence research was supplied for this story, so this spec cites no requirement IDs.

## 2. Goals & Non-Goals

### Goals
- A probe can call `GET /healthz` or `HEAD /healthz` on a running `serve.py` and get `200` whenever the server is up and answering HTTP.
- The answer is a small, fixed JSON document, `{"status": "ok"}`, that a probe can match on.
- Every path `serve.py` served before answers exactly as before, and `smoke_test.py` still passes.
- The behaviour is covered by an automated unittest under `tests/` and documented in `README.md`.

### Non-Goals
- Any third-party dependency (from the story).
- Authentication on `/healthz` (from the story).
- Readiness/liveness distinctions (from the story): `/healthz` does not report the key-value store's state, and there is no `/readyz`, `/livez` or similar.
- Any other new route, and any change to how existing routes behave.
- Detail in the body beyond `{"status": "ok"}` (version, uptime, timestamps).

## 3. Functional Requirements

- **FR1 — GET /healthz.** A `GET` request whose path is exactly `/healthz` answers status `200`, header `Content-Type: application/json`, and the body `{"status": "ok"}`. The body parses as the JSON object with one key, `status`, whose value is the string `"ok"`.
- **FR2 — HEAD /healthz.** A `HEAD` request whose path is exactly `/healthz` answers status `200` with no body. Its headers match the `GET` answer's (decision D3).
- **FR3 — Exact path match, as the other fixed pages.** The path is matched exactly, the same way `/` and `/jungle` already are (`serve.py:3-10`):
  - a query string is ignored, so `/healthz?x=1` answers as `/healthz` (decision D1);
  - look-alikes such as `/healthz/`, `/healthz.json`, `/HEALTHZ` and `/health` keep answering `404`, as every unknown path does today (decision D1).
- **FR4 — Unconditional while the server answers.** `/healthz` answers `200` whatever the key-value store's state, including when `/kv/` answers `503` for a corrupt log or `500` for a store I/O error. It reports only that the server process is up, because readiness distinctions are out of scope (decision D2).
- **FR5 — Other methods unchanged.** `PUT` and `DELETE` on `/healthz` answer as they do on any non-`/kv/` path today: the standard `501` (`serve.py:226-232`). Methods the server does not implement keep their current answers (decision D4).
- **FR6 — No regression.** Every path `serve.py` served before (`/`, `/jungle`, `/kv/` and its sub-paths, and the `404` answers for every other path) answers exactly as before, for every method, and `smoke_test.py` still passes.
- **FR7 — Automated test.** A unittest under `tests/`, run by `python -m unittest discover -s tests`, starts the server on a free port and checks FR1 and FR2.
- **FR8 — Documentation.** `README.md` documents `/healthz` with a curl example, and states what it answers.

## 4. User Experience & Behavior

**Key flow (operator):**
1. The operator starts the server as today: `python3 serve.py` (or with a port argument, `PORT` or `HOST`).
2. The probe calls `curl -i http://127.0.0.1:8000/healthz`.
3. While the server is up, the probe sees `HTTP/1.0 200 OK`, `Content-Type: application/json` and the body `{"status": "ok"}`.
4. When the server is not running, the connection fails, as it does for any URL today. That failure is the "down" signal; the server sends no "unhealthy" answer.

**States the operator observes:** only two. Up: `200` with `{"status": "ok"}`. Down: no answer (connection refused or a timeout). There is no degraded state.

**Output format:** JSON, `Content-Type: application/json`, the object `{"status": "ok"}`. The exact byte spacing of the body is not part of the product: a probe should parse it or match the `status` value. It is plain ASCII.

**User-facing edge cases:**
- `/healthz?anything` answers as `/healthz`.
- `/healthz/` and other look-alikes answer `404`, as unknown paths do today.
- A corrupt key-value log does not affect `/healthz`: it still answers `200` while `/kv/` answers `503`.

There is no visual or interactive surface; the only look-and-feel requirement is the JSON answer above.

## 5. Acceptance Criteria

1. GET /healthz returns 200 with Content-Type application/json and body {"status": "ok"}.
2. HEAD /healthz returns 200 with no body.
3. Every path serve.py served before still answers exactly as before, and smoke_test.py still passes.
4. A unittest under tests/ covers criteria 1 and 2 by starting the server on a free port.
5. README.md documents the endpoint with a curl example.

## 6. Dependencies & Constraints (product-level)

- **Builds on the existing `serve.py`** at `main`, which already serves `/`, `/jungle` and `/kv/` (SCRUM-119, KAN-8, HALO-93). Its docstring lists its routes and `smoke_test.py` checks that docstring (`smoke_test.py:245-279`), so the docstring should mention `/healthz` too, without the words the smoke test rejects ("Root-only", "exactly one document").
- **`smoke_test.py` must keep passing unchanged in meaning.** It already asserts `404` for a fixed list of unknown paths (`smoke_test.py:20-39`); `/healthz` is not in that list, so adding the route does not collide with it.
- **Standard library only:** no third-party dependency (story).
- **Tests run with the repository's existing command** `python -m unittest discover -s tests` (README "Tests"), next to `python3 smoke_test.py`. The repository has no `AGENTS.md`, `CLAUDE.md`, `.factory/` folder or CI workflow, so no further gate applies.
- **Exposure:** like the rest of `serve.py`, the route binds to `127.0.0.1` by default and has no authentication (story: authentication out of scope). The answer carries no information beyond "ok".

## 7. Technical Design (deferred to STRUCTURE)

How the route is wired into `RootOnlyHandler`, how the test picks a free port (the existing `make_server(port=0)` already supports an ephemeral port, `serve.py:257-259`), and whether the new test lives in `tests/test_http.py` or a new file are decided in STRUCTURE. Constraints the product imposes: exact path matching as in FR3, an answer independent of the key-value store (FR4), and no change to any existing route's answer (FR6).

## 8. Open Questions

No blocking question remains. The intake made these decisions on points the story leaves open; each can be reversed before implementation starts:

- **D1 — Path matching.** `/healthz` matches exactly, a query string is ignored, and `/healthz/` and other look-alikes stay `404`. *Why:* this is how `/` and `/jungle` already behave, and the story asks that nothing else change.
- **D2 — Independent of the key-value store.** `/healthz` answers `200` even when `/kv/` answers `503` or `500`. *Why:* the story says probes check "the server is up", and readiness/liveness distinctions are out of scope.
- **D3 — HEAD headers.** `HEAD /healthz` sends the same headers as `GET` (including `Content-Type: application/json`), without the body. *Why:* the server already makes `HEAD` mirror `GET` for `/`, `/jungle` and `/kv/`.
- **D4 — Other methods.** `PUT`/`DELETE` on `/healthz` keep the standard `501` that every non-`/kv/` path answers today. *Why:* criterion 3 asks that existing answers not change.

Residual note: SCRUM-122 was read as filed; no parent epic, PRD or backlog was supplied with it.
