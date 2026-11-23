# Feature Specification Document — SCRUM-119 (draft, not ready)

## 1. Feature Overview

> **Status: PARTIALLY_READY.** This is the in-progress draft. The open P0 questions in §8 must be answered before this becomes the final specification.

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

Items marked **[open]** depend on a question in §8. The behavior written next to them is the working assumption, not a settled requirement.

**Log and recovery (t1)**
- FR1: All data lives in one append-only log file. Each line is one JSON record `{"op":"set"|"del","k":..,"v":..,"exp":..,"crc":..}`, where `crc` is the CRC32 of the record without the `crc` field.
- FR2: When the store opens, it replays the log, and the latest record for each key wins. A `del` removes the key.
- FR3: If only the **last** line is torn (truncated mid-record), the store drops it, truncates the file to the end of the last good record, and emits a warning that names the byte offset. **[open, P1-1: where the warning appears]**
- FR4: If a record **before** the last one fails its CRC check, opening raises `CorruptLogError` naming the line number, and the store refuses writes. **[open, P1-2: what a refused write looks like; P0-1: what `serve.py` does then]**

**Store API with TTL (t2)**
- FR5: `set(k, v, ttl=None)`, `get(k)`, `delete(k)` and `keys()` behave like a dict. `get` and `delete` on a missing key raise `KeyError`. Each mutation is durably written (appended and fsynced) before the call returns.
- FR6: With `ttl` set, a key expires at exactly `set time + ttl` on the injected `clock`. From that instant `get` raises `KeyError` and `keys()` omits the key. Fractional times and TTLs are allowed (AC5 uses 109.9). **[open, P1-3: invalid ttl values; P1-4: whether `set` without `ttl` on a key that had a TTL clears it]**
- FR7: Validation. A key must be 1–128 printable characters, and a value must be a JSON value of at most 64 KiB once serialized. A violation raises `ValueError` naming the rule, and nothing is appended. **[open, P0-3: what "printable" means and how keys travel in URLs; P1-5: whether exactly 64 KiB is allowed and how size is counted]**
- FR8: Concurrent mutations from several threads in one process are never lost. Two threads each setting 500 distinct keys leave all 1000 keys present after reopening.

**Compaction (t3)**
- FR9: `compact()` rewrites the log so it holds only live, unexpired records. It replaces the old log atomically (write a temp file, fsync, rename). Reads return the same values before and after. **[open, P0-2: what triggers compaction and what the 50% figure means]**
- FR10: If a crash happens after the temp file is written but before the rename, the next open uses the old log and removes the stale temp file.

**HTTP routes in `serve.py` (t4)**
- FR11: `GET /kv/<key>` returns 200 with the JSON value, or 404. `PUT /kv/<key>` takes a JSON body and an optional `?ttl=<seconds>` and returns 204. `DELETE /kv/<key>` returns 204, or 404. `GET /kv/` returns the live keys as a JSON array. **[open, P1-6: list order]**
- FR12: Errors. An invalid JSON body or an invalid key returns 400 with `{"error": ...}`. A body over 64 KiB returns 413 without the server reading the whole body.
- FR13: The store file location comes from `KV_PATH`, and defaults to `./kv.log`.
- FR14: Regression. Every path `serve.py` answered before still answers as before (see §4), and `smoke_test.py` still passes.
- FR15: README.md documents `KV_PATH` (default `./kv.log`) and every route with a curl example.

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
- Errors return `400 {"error": "..."}` (bad JSON or bad key) and `413` (body over 64 KiB).

**Existing users of `serve.py` (unchanged):** `GET`/`HEAD /` and `/jungle` still return 200 with the same bytes. Every other non-`/kv/` path (for example `/foo/bar`, `/README.md`, `/jungle/`) still returns 404 for `GET` and `HEAD`. Working assumption: `PUT` and `DELETE` on non-`/kv/` paths keep today's answer (501, from the standard handler), because the story allows no change to existing behavior.

**Corrupt log while serving:** what the HTTP user sees is open question P0-1.

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

## 6. Dependencies & Constraints (product-level)

- **`serve.py`** (`serve.py:1-107`) is a fixed-route stdlib server. Its docstring promises that every path other than `/` and `/jungle` returns 404. It implements only `GET` and `HEAD`. The `/kv/` routes are the one permitted exception, so its usage docstring and that promise need updating to match.
- **`smoke_test.py` constrains the change.** It asserts `serve.ROUTES == {"/": serve.INDEX, "/jungle": serve.JUNGLE}` (`smoke_test.py:128-133`), and it asserts 404 for `/foo/bar`, `/README.md`, `/jungle/` and others. AC12 requires it to keep passing unchanged, so `/kv/` cannot be added to that route table. STRUCTURE chooses the mechanism. Changing `smoke_test.py` is not an option unless the PO widens AC12.
- **Test runner:** `python -m unittest discover -s tests`. `tests/` does not exist yet and this story creates it. The repository has no `AGENTS.md`, `CLAUDE.md`, `.factory/` or CI workflow, so no repository gate adds constraints beyond the above.
- **Standard library only**, in the package and in its tests.
- **Default bind is 127.0.0.1.** `HOST=0.0.0.0` exposes the unauthenticated `/kv/` routes to the network. Authentication is out of scope, so the README should say this (P2-1).

## 7. Technical Design (deferred to STRUCTURE)

The record format and CRC rule are fixed by the story. STRUCTURE decides:
- how the store is held inside the threaded server, and how writes are serialized;
- how `/kv/` is dispatched without touching `ROUTES`;
- how the torn-tail truncation and the temp-file naming and clean-up work;
- how the 413 is detected from `Content-Length` without reading the body;
- how the `clock` is injected.

## 8. Open Questions

**P0 — blocking**
- **P0-1. Corrupt log under `serve.py`.** AC3 makes opening raise `CorruptLogError`, and AC12 says everything `serve.py` served before must keep working. When `KV_PATH` points at a log corrupted in the middle, what should `serve.py` do?
  - (a) Refuse to start, with an error naming the line.
  - (b) Start, serve `/` and `/jungle` as before, and answer every `/kv/` request with `503 {"error": "...line N..."}`.

  *Recommendation: (b).* It is the only option that keeps AC12 true when the log is bad. A PO answer that the KV store matters more than the pages would change the pick to (a).
- **P0-2. Compaction trigger.** AC8 says "live records are under 50% … when `compact()` runs". Who runs compaction, and what is the 50% figure?
  - (a) Manual only. `compact()` always compacts when called, and 50% is just the test setup.
  - (b) The store runs it automatically after a mutation once live records drop under 50% of all records. `compact()` stays callable by hand.
  - (c) Automatic as in (b), but `compact()` called by hand does nothing while live records are at or above 50%.

  *Recommendation: (b).* No HTTP route triggers compaction, so under (a) a `serve.py` log grows forever. An answer that the HTTP server is restarted often enough not to care would make (a) acceptable.
- **P0-3. What counts as a valid key, and how it travels in a URL.** "Printable" could mean:
  - (a) Python `str.isprintable()`, which allows Unicode and the space character.
  - (b) ASCII 0x21–0x7E only.

  Separately, is `<key>` in `/kv/<key>` percent-decoded, and may a key contain `/`?

  *Recommendation:* (a) on the percent-decoded rest of the path after `/kv/`, so `/` is allowed and the query string is excluded. That keeps the Python API and the HTTP API accepting exactly the same keys. An answer that keys must be shell-safe without quoting would change the pick to (b).

**P1 — important (working assumptions in brackets)**
- **P1-1.** Where does the torn-tail warning appear? [A Python `warnings` warning, which `serve.py` shows on stderr.]
- **P1-2.** What does a refused write after corruption look like in the API? [Every mutation raises `CorruptLogError`. Reads also raise it, because opening failed.]
- **P1-3.** Invalid `ttl` values: zero, negative, non-numeric or fractional, in both the API and `?ttl=`. [Zero, negative and non-numeric give `ValueError` / 400. Fractional values are allowed.]
- **P1-4.** Does `set` / `PUT` without a ttl on a key that had one clear the old expiry? [Yes, the new write replaces the key fully, as in a dict.]
- **P1-5.** Is exactly 64 KiB (65,536 bytes) allowed, and is size counted as UTF-8 bytes of the compact JSON serialization? [Yes and yes. The HTTP 413 check applies to the raw request body size.]
- **P1-6.** What order does `GET /kv/` (and `keys()`) use? [Sorted ascending.]
- **P1-7.** Is several processes sharing one `KV_PATH` out of scope? [Yes, only one process per file. AC7 covers threads only.]
- **P1-8. Story hygiene against Harel's story template.**
  - The size "L (≈8)" doesn't match the template's scale, where L is about 5 and XL about 8. [XL (about 8).]
  - The story has no "traces to" row, because there is no epic or PRD.
  - AC1 ("the in-memory index holds…") and AC4 ("appended and fsynced") state internal outcomes. [Check AC1 by what `get` and `keys()` return, and AC4 by reopening the file.]

**P2 — notes**
- **P2-1.** README should warn that `HOST=0.0.0.0` exposes unauthenticated read and write access to the store.
- **P2-2.** Should `kv.log` be added to `.gitignore` so a demo run doesn't leave an untracked data file in the repository root?
