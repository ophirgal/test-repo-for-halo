# Feature Specification Document — SCRUM-119

## 1. Feature Overview

> **Status: READY_FOR_SPEC.** On 2026-11-23 the developer asked the intake to make the open decisions itself ("make your own decisions"). Every question raised earlier has been settled with the intake's recommended option. §8 lists each decision so it can be reviewed and reversed before implementation starts.

**Summary:** A small, standard-library-only Python package, `kvstore`, at the repository root. It keeps key-value pairs in one append-only log file of JSON lines, and each key can have its own expiry (TTL). It recovers from a torn last record, refuses to work on a log corrupted in the middle, and compacts the log atomically. The repository's existing `serve.py` serves it over HTTP under `/kv/`.

**Problem statement:** A developer running local tools and demos needs scripts to share small state across restarts. Today that means installing a database. There is also no guarantee that a crash leaves the state readable.

**Target users / actors:**
- A developer who calls the `kvstore` Python API from a script.
- A developer or script that calls the `/kv/` HTTP routes on a running `serve.py`, for example with curl.
- Anyone already using `serve.py`'s pages (`/` and `/jungle`). Their experience must not change.

**Sources:** This spec is based only on the Jira story SCRUM-119 (title, description and 13 acceptance criteria) and on the repository at `main` (`51b3688`). SCRUM-119 has no parent epic and no issue links in Jira. No Epic PRD, User Story Backlog or Confluence research exists for it, so this spec cites no requirement IDs.

## 2. Goals & Non-Goals

### Story context

The story adds a new, stdlib-only Python package `kvstore` at the repository root with its tests under `tests/`, in four dependent work items: the log format and recovery (t1), the store API with TTL (t2), compaction (t3) and the HTTP routes wired into `serve.py` (t4). Data lives in one append-only log file of JSON lines (`{"op":"set"|"del","k":..,"v":..,"exp":..,"crc":..}`) where `crc` is the CRC32 of the record without it; values are JSON values up to 64 KiB; keys are 1–128 printable characters. Time is injected (a `clock` callable) so tests never sleep. Out of scope: replication, transactions across keys, authentication, any third-party dependency, changes to existing behaviour of `serve.py` other than adding the `/kv/` routes.

### Goals
- Scripts can store and read JSON values by key, and the values survive a process restart.
- A key can expire after a set number of seconds. Expired keys behave as if they were absent.
- A crash never leaves the store unreadable. A torn last record is dropped with a warning. Corruption in the middle of the log is reported loudly and is never silently skipped.
- The log can be compacted without risking data loss, even if a crash happens during compaction.
- The same store is available over HTTP from the existing `serve.py`, and the README documents how to use it.
- Nothing `serve.py` serves today changes.

### Non-Goals
- Replication, and transactions across several keys.
- Authentication or authorization on the `/kv/` routes.
- Any third-party dependency, either at runtime or for tests.
- Any change to existing `serve.py` behavior beyond adding the `/kv/` routes.
- A query language, key prefixes or scans, beyond listing live keys.

## 3. Functional Requirements

Decisions settled at intake are marked with the §8 decision they come from (D1–D12).

**Log and recovery (t1)**
- FR1: All data lives in one append-only log file. Each line is one JSON record `{"op":"set"|"del","k":..,"v":..,"exp":..,"crc":..}`, where `crc` is the CRC32 of the record without the `crc` field.
- FR2: When the store opens, it replays the log, and the latest record for each key wins. A `del` removes the key.
- FR3: If only the **last** line is torn (truncated mid-record), the store drops it, truncates the file to the end of the last good record, and emits a Python `warnings` warning that names the byte offset. Under `serve.py` that warning appears on stderr. (D4)
- FR4: If a record **before** the last one fails its CRC check, opening raises `CorruptLogError` naming the line number. The store then refuses writes: every mutation attempted on it raises `CorruptLogError`, and nothing is appended. (D5)

**Store API with TTL (t2)**
- FR5: `set(k, v, ttl=None)`, `get(k)`, `delete(k)` and `keys()` behave like a dict. `get` and `delete` on a missing or expired key raise `KeyError`. Each mutation is durably written (appended and fsynced) before the call returns.
- FR6: With `ttl` set, a key expires at exactly `set time + ttl` on the injected `clock`. From that instant `get` raises `KeyError` and `keys()` omits the key. Fractional times and TTLs are allowed (AC5 uses 109.9). A `ttl` that is zero, negative or not a number raises `ValueError` and nothing is appended (D6). A `set` without `ttl` on a key that had one replaces the key fully, so the key no longer expires (D7).
- FR7: Validation. A key must be 1–128 characters and pass Python's `str.isprintable()` (Unicode and the space character are allowed; control characters are not) (D3). A value must be a JSON value whose compact UTF-8 serialization is at most 65,536 bytes; exactly 65,536 is allowed (D8). A violation raises `ValueError` naming the rule, and nothing is appended.
- FR8: Concurrent mutations from several threads in one process are never lost. Two threads each setting 500 distinct keys leave all 1000 keys present after reopening. One process per store file is supported; several processes sharing a file is out of scope (D10).
- FR9a: `keys()` returns the live, unexpired keys in ascending sorted order (D9).

**Compaction (t3)**
- FR9: `compact()` rewrites the log so it holds only live, unexpired records. It replaces the old log atomically (write a temp file, fsync, rename). Reads return the same values before and after. Called by hand, `compact()` always compacts, whatever the live ratio.
- FR9b: The store also compacts automatically after a mutation once live records are under 50% of all records in the log, with the same atomic replacement. No HTTP route triggers compaction; automatic compaction keeps a long-running `serve.py` log from growing forever. (D2)
- FR10: If a crash happens after the temp file is written but before the rename, the next open uses the old log and removes the stale temp file.

**HTTP routes in `serve.py` (t4)**
- FR11: `GET /kv/<key>` returns 200 with the JSON value, or 404. `PUT /kv/<key>` takes a JSON body and an optional `?ttl=<seconds>` and returns 204. `DELETE /kv/<key>` returns 204, or 404. `GET /kv/` returns the live keys as a JSON array, sorted ascending (D9).
- FR11a: `<key>` is the percent-decoded rest of the path after `/kv/`, without the query string. It may contain `/` (for example `/kv/app/config` is key `app/config`). The same key rules as the Python API apply, so both accept exactly the same keys. (D3)
- FR12: Errors. An invalid JSON body, an invalid key or an invalid `ttl` (zero, negative, not a number) returns 400 with `{"error": ...}` (D6). A body over 64 KiB (more than 65,536 bytes, judged from the declared request size) returns 413 without the server reading the whole body (D8).
- FR12a: If the log at `KV_PATH` is corrupt in the middle, `serve.py` still starts and serves `/` and `/jungle` as before, and every `/kv/` request answers `503` with `{"error": ...}` naming the corrupt line number. (D1)
- FR13: The store file location comes from `KV_PATH`, and defaults to `./kv.log`.
- FR14: Regression. Every path `serve.py` answered before still answers as before (see §4), and `smoke_test.py` still passes unchanged.
- FR15: README.md documents `KV_PATH` (default `./kv.log`) and every route with a curl example, and warns that binding with `HOST=0.0.0.0` exposes unauthenticated read and write access to the store (D11).
- FR16: `kv.log` is listed in `.gitignore`, so a demo run doesn't leave an untracked data file in the repository root (D12).

## 4. User Experience & Behavior

**Script developer (Python API):**
1. Open a store on a file path, with an optional `clock` for tests.
2. `set` / `get` / `delete` / `keys`, with dict-like errors (`KeyError`, and `ValueError` naming the broken rule).
3. Restart the process, reopen the store and see the same live keys.
4. After a crash that tore the last line, the store opens with a warning that names the byte offset. After corruption in the middle of the log, opening fails with `CorruptLogError` naming the line number.

**HTTP client (curl or a script against `python3 serve.py`):**
- `curl -X PUT --data '{"a":1}' 'http://127.0.0.1:8000/kv/cfg?ttl=60'` returns `204`.
- `curl http://127.0.0.1:8000/kv/cfg` returns `200` with `{"a":1}`. It returns `404` once the key has expired or been deleted.
- `curl http://127.0.0.1:8000/kv/` returns `200` with a JSON array of live keys.
- `curl -X PUT --data '1' http://127.0.0.1:8000/kv/app/config` stores key `app/config`; a key with spaces or Unicode is sent percent-encoded (`/kv/my%20key`).
- Errors return `400 {"error": "..."}` (bad JSON, bad key or bad `ttl`) and `413` (body over 64 KiB).

**Existing users of `serve.py` (unchanged):** `GET`/`HEAD /` and `/jungle` still return 200 with the same bytes. Every other non-`/kv/` path (for example `/foo/bar`, `/README.md`, `/jungle/`) still returns 404 for `GET` and `HEAD`. `PUT` and `DELETE` on non-`/kv/` paths keep today's answer (501, from the standard handler), because the story allows no change to existing behavior.

**Torn tail at start-up:** `serve.py` starts normally and the warning naming the byte offset appears on stderr.

**Corrupt log while serving:** `serve.py` starts and the pages work. Every `/kv/` request answers `503 {"error": "..."}`, and the error names the corrupt line, so the developer knows which file and line to fix.

## 5. Acceptance Criteria

1. Scenario 1 — Happy path: Given a log with three `set` records and one `del`, When the store opens it, Then the in-memory index holds the two live keys with their latest values.
2. Scenario 2 — Torn tail: Given a log whose last line is truncated mid-record, When the store opens it, Then the torn record is dropped, the file is truncated to the last good record, and a warning names the byte offset.
3. Scenario 3 — Corruption: Given a record in the middle whose `crc` does not match, Then opening raises `CorruptLogError` with the line number and the store refuses writes.
4. Scenario 4 — set/get/delete: `set(k, v, ttl=None)`, `get(k)` and `delete(k)` behave as a dict; every mutation is appended and fsynced before returning.
5. Scenario 5 — Expiry: Given `set("a", 1, ttl=10)` at clock 100, Then `get("a")` returns 1 at clock 109.9 and raises `KeyError` at clock 110; expired keys are not listed by `keys()`.
6. Scenario 6 — Validation: Given a key longer than 128 characters, a non-printable key or a value over 64 KiB once serialized, Then `ValueError` names the rule and nothing is appended.
7. Scenario 7 — Concurrency: Given two threads each setting 500 distinct keys, Then all 1000 are present after reopening the file.
8. Scenario 8 — Compaction: Given a log where live records are under 50% of all records, When `compact()` runs, Then a new log with only live, unexpired records replaces the old one atomically (write to temp, fsync, rename) and reads return the same values before and after.
9. Scenario 9 — Crash safety: Given a crash simulated after the temp file is written but before the rename, When the store reopens, Then it uses the old log and removes the stale temp file.
10. Scenario 10 — Routes: `GET /kv/<key>` returns 200 with the JSON value or 404; `PUT /kv/<key>` with a JSON body and optional `?ttl=<seconds>` returns 204; `DELETE /kv/<key>` returns 204 or 404; `GET /kv/` lists live keys as a JSON array.
11. Scenario 11 — Errors: an invalid JSON body or key returns 400 with `{"error": ...}`; a body over 64 KiB returns 413 without reading it fully.
12. Scenario 12 — Existing behaviour: every path `serve.py` served before still answers as before, and `smoke_test.py` still passes.
13. Scenario 13 — Docs: README.md documents the store file location (`KV_PATH`, default `./kv.log`) and the routes with curl examples.
14. Scenario 14 — Corrupt log under serve.py: Given `KV_PATH` points at a log with a corrupt record in the middle, When `serve.py` starts, Then `/` and `/jungle` answer as before and every `/kv/` request returns 503 with `{"error": ...}` naming the line number.
15. Scenario 15 — Automatic compaction: Given a store whose live records fall under 50% of all records after a mutation, Then the log is compacted atomically without calling `compact()`, and reads return the same values before and after; a manual `compact()` always compacts.
16. Scenario 16 — Keys: Given a key of 1–128 characters that passes `str.isprintable()` (including spaces, Unicode and `/`), Then the Python API accepts it, and `PUT /kv/<key>` with the key percent-encoded stores the same key, readable by `get` and by `GET /kv/<key>`; `GET /kv/` and `keys()` list keys sorted ascending.
17. Scenario 17 — Limits and TTL rules: A value whose compact UTF-8 JSON is exactly 65,536 bytes is accepted; a `ttl` that is zero, negative or not a number raises `ValueError` in the API and returns 400 over HTTP; `set` without `ttl` on a key that had one removes its expiry; a mutation on a store opened over a corrupt log raises `CorruptLogError`.
18. Scenario 18 — Housekeeping: README.md warns that `HOST=0.0.0.0` exposes the unauthenticated store, and `kv.log` is listed in `.gitignore`.

## 6. Dependencies & Constraints (product-level)

- **`serve.py`** (`serve.py:1-107`) is a fixed-route stdlib server. Its docstring promises that every path other than `/` and `/jungle` returns 404. It implements only `GET` and `HEAD`. The `/kv/` routes are the one permitted exception, so its usage docstring and that promise need updating to match.
- **`smoke_test.py` constrains the change.** It asserts `serve.ROUTES == {"/": serve.INDEX, "/jungle": serve.JUNGLE}` (`smoke_test.py:128-133`), and it asserts 404 for `/foo/bar`, `/README.md`, `/jungle/` and others. AC12 requires it to keep passing unchanged, so `/kv/` cannot be added to that route table. STRUCTURE chooses the mechanism. Changing `smoke_test.py` is not an option unless the PO widens AC12.
- **Test runner:** `python -m unittest discover -s tests`. `tests/` does not exist yet and this story creates it. The repository has no `AGENTS.md`, `CLAUDE.md`, `.factory/` or CI workflow, so no repository gate adds constraints beyond the above.
- **Standard library only**, in the package and in its tests.
- **Default bind is 127.0.0.1.** `HOST=0.0.0.0` exposes the unauthenticated `/kv/` routes to the network. Authentication is out of scope, so the README says this (D11).
- **One process per store file.** Several processes sharing one `KV_PATH` is out of scope (D10).

## 7. Technical Design (deferred to STRUCTURE)

The record format and CRC rule are fixed by the story. STRUCTURE decides:
- how the store is held inside the threaded server, and how writes are serialized;
- how `/kv/` is dispatched without touching `ROUTES`;
- how the torn-tail truncation and the temp-file naming and clean-up work;
- how the 413 is detected from `Content-Length` without reading the body;
- how the `clock` is injected.

## 8. Decisions & Open Questions

**Decisions settled at intake (2026-11-23).** The developer asked the intake to decide every open point itself. Each decision below is the option the intake recommended; any of them can be reversed by the developer before implementation.

- **D1. Corrupt log under `serve.py`:** start, serve `/` and `/jungle` as before, and answer every `/kv/` request with `503 {"error": ...}` naming the line. Chosen because it is the only option that keeps Scenario 12 true when the log is bad. (Rejected: refuse to start.)
- **D2. Compaction trigger:** automatic after a mutation once live records are under 50% of all records; a manual `compact()` always compacts. Chosen because no HTTP route triggers compaction, so a manual-only store would grow forever behind `serve.py`.
- **D3. Valid keys:** 1–128 characters passing `str.isprintable()`. Over HTTP, the key is the percent-decoded rest of the path after `/kv/`, query string excluded, and may contain `/`. Chosen so the Python API and the HTTP API accept exactly the same keys.
- **D4. Torn-tail warning:** a Python `warnings` warning naming the byte offset, shown on stderr under `serve.py`.
- **D5. Refused writes:** after opening over a corrupt log, every mutation raises `CorruptLogError` and appends nothing.
- **D6. Invalid `ttl`:** zero, negative or non-numeric gives `ValueError` in the API and 400 over HTTP; fractional values are allowed.
- **D7. Re-set without `ttl`:** replaces the key fully, clearing its old expiry, as a dict would.
- **D8. Size limit:** size is the UTF-8 byte length of the compact JSON serialization; exactly 65,536 bytes is allowed. The HTTP 413 judges the raw request body size from its declared length.
- **D9. Key order:** `keys()` and `GET /kv/` list keys sorted ascending.
- **D10. Processes:** one process per store file; sharing a file across processes is out of scope.
- **D11. README warning:** the README warns that `HOST=0.0.0.0` exposes unauthenticated read and write access.
- **D12. `.gitignore`:** `kv.log` is added to `.gitignore`.

**Story hygiene (recorded, not blocking).**
- The Jira size "L (≈8)" doesn't match Harel's story template, where L is about 5 points and XL about 8. With Scenarios 14–18 added, the story is XL (about 8). The ticket's size field should be corrected in Jira by a person; the factory does not edit it.
- The story has no "traces to" row, because SCRUM-119 has no parent epic or PRD.
- Scenarios 1 and 4 state internal outcomes. They are checked through what `get` and `keys()` return, and by reopening the file.

**Remaining open questions:** none at product level. The technical choices in §7 belong to STRUCTURE.
