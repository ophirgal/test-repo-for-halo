# SCRUM-119 — High-Level Design: append-only key-value store with TTL, compaction and an HTTP API

## 1. System Overview

- **What:** a new stdlib-only Python package `kvstore/` at the repository root that keeps key → JSON value pairs, with an optional per-key TTL, in one append-only JSON-lines log. It recovers from a torn last record, refuses a log corrupted in the middle, and compacts atomically (manually and automatically). The existing `serve.py` exposes the same store under `/kv/`.
- **Problem:** local scripts and demos need small state that survives restarts and crashes without installing a database.
- **Responsibilities:** durable append and replay, CRC integrity, TTL expiry on an injected clock, validation, thread safety within one process, atomic compaction, and an HTTP adapter that leaves every existing `serve.py` answer unchanged.
- **Grounding in the code (`main` at `51b3688`, branch at `8d8f712`):** the repository has no Python package, no `tests/`, no `.gitignore`, no `AGENTS.md`/`CLAUDE.md`/`.factory/` and no CI workflow. `serve.py` is a `ThreadingHTTPServer` (`serve.py:79-81`) with a `RootOnlyHandler` that implements only `do_GET`/`do_HEAD` (`serve.py:42-76`) over a fixed `ROUTES` table (`serve.py:39`). `smoke_test.py` subclasses that handler (`smoke_test.py:57-61`), builds the server with `make_server("127.0.0.1", 0, QuietHandler)` (`smoke_test.py:341`) and asserts `ROUTES` holds exactly two entries (`smoke_test.py:128-133`). The code agrees with what the spec says exists.

## 2. Architecture Overview

```
script ──► kvstore.KVStore ──► kvstore.log (encode / replay / recover) ──► <KV_PATH> (JSON lines)
                 ▲      └──► compaction (temp file → fsync → rename)  ──► <KV_PATH>.compact.tmp
curl ──► serve.py RootOnlyHandler ──/kv/ prefix──► one shared KVStore per server
                                  └─ "/" and "/jungle" via ROUTES (unchanged)
```

| Module | Owner ticket | Role |
|---|---|---|
| `kvstore/log.py` | t1 | Record encoding with CRC32, replay, torn-tail truncation, `CorruptLogError` |
| `kvstore/__init__.py` | t1 creates; t2 extends the exports | Public surface: the store class and `CorruptLogError` |
| `kvstore/store.py` | t2 creates; t3 extends (handoff) | Store API, validation, TTL, the lock, fsync'd appends |
| `kvstore/compaction.py` | t3 | Writing the compacted temp file and swapping it in; stale-temp clean-up |
| `serve.py` | t4 | `/kv/` dispatch, HTTP error mapping, `KV_PATH`, docstring update |
| `tests/` | each ticket owns its own `test_*.py` | `python -m unittest discover -s tests` |
| `README.md`, `.gitignore` | t4 | Docs and housekeeping |

- **Boundaries:** `kvstore` knows nothing about HTTP; `serve.py` only calls the public `kvstore` API and maps its exceptions to statuses. No third-party dependency anywhere.
- **External dependencies:** Python standard library only (`json`, `zlib`, `os`, `threading`, `warnings`, `http.server`, `urllib.parse`). Checked on Python 3.12; nothing used is newer than 3.8.

## 3. Data Flow Design

All processing is synchronous; there are no background threads or events.

- **Open:** remove a stale `<path>.compact.tmp` if present (t3) → read the log as bytes and split on `\n` → verify each record (JSON object, CRC, well-formed fields) → latest record per key wins, `del` removes → an invalid *last* record is torn: truncate the file to the end of the last good record and warn with that byte offset → an invalid *earlier* record raises `CorruptLogError` with its 1-based line number and the file is left byte-for-byte untouched (no truncation, no temp clean-up beyond the stale temp file).
- **Mutation (`set` / `delete`):** take the store lock → validate (key, value, ttl) → compute `exp = clock() + ttl` → append one line, flush, `os.fsync` → update the in-memory index → if live records are under 50 % of the records in the log, compact → release the lock → return.
- **Read (`get` / `keys`):** under the lock, look up the index and treat any entry with `exp <= clock()` as absent.
- **Compaction:** under the lock, write every live, unexpired record to `<path>.compact.tmp`, flush and fsync it, `os.replace` it over the log, fsync the directory, then reopen the append handle on the new file.
- **HTTP:** `RootOnlyHandler` sees a path starting with `/kv/` → percent-decode the rest as the key → call the shared store → map the outcome to a status with a JSON body. Every other path follows the existing code unchanged.

## 4. Component Breakdown

- **Log format and recovery** (`kvstore/log.py`, t1). In: a log file path. Out: the replayed index (key → value, exp), the byte length of the good prefix, a torn-tail warning, or `CorruptLogError`. Also encodes one record as a line.
- **Store API with TTL** (`kvstore/store.py`, t2). In: path, optional `clock` (defaults to `time.time`). Out: `set`/`get`/`delete`/`keys`, `ValueError`, `KeyError`, `CorruptLogError`, durable appends.
- **Compaction** (`kvstore/compaction.py` plus t3's handoff edit of `kvstore/store.py`). In: the live index. Out: an atomically replaced log; stale temp files removed on open.
- **HTTP adapter** (`serve.py`, t4). In: HTTP requests under `/kv/`, `KV_PATH`. Out: JSON responses and status codes; `/` and `/jungle` untouched.

All components live in repository `ophirgal/test-repo-for-halo`.

## 5. Interface Contracts

### 5.1 Log record (fixed by the story)

- One record per line, UTF-8, terminated by `\n`: a JSON object with exactly the keys `op`, `k`, `v`, `exp`, `crc`.
- `op` is `"set"` or `"del"`. A `del` record carries `"v": null` and `"exp": null`. A `set` without TTL carries `"exp": null`; with TTL, `exp` is the absolute expiry time on the store's clock (a number).
- `crc` is `zlib.crc32` of the UTF-8 bytes of the record *without* `crc`, serialized canonically: compact separators `(",", ":")`, `sort_keys=True`, `ensure_ascii=False`, `allow_nan=False`. Verification re-serializes the parsed record minus `crc` the same way and compares.
- A record is **invalid** if it is not valid UTF-8, not a JSON object, has missing or extra keys, an unknown `op`, a `k` that breaks the key rule, a non-numeric or non-finite `exp`, or a CRC mismatch. An empty line before the end of the file is an invalid record.

### 5.2 Recovery rules

- **Missing file** → created empty on open; the store is empty. **Empty file** → empty store.
- **Last record invalid** (whether or not it ends in `\n`) → torn: the file is truncated to the byte offset where that record starts, and a `warnings.warn` (a `UserWarning` subclass) message names that offset. A valid last record without a trailing `\n` is kept and a `\n` is appended before the next record.
- **Any earlier record invalid** → `CorruptLogError` (subclass of `Exception`) whose message names the path and the 1-based line number; the line number is also exposed as an attribute. The file is not modified.

### 5.3 Python API (public surface of `kvstore`)

- Opening a store on a path, with optional keyword `clock` (a zero-argument callable returning seconds; default `time.time`, a wall clock, because `exp` must stay meaningful across restarts).
- `set(k, v, ttl=None)`, `get(k)`, `delete(k)`, `keys()` (sorted ascending list of live keys), `compact()`, and `close()` / context-manager use.
- **Key rule:** a `str` of 1–128 characters with `str.isprintable()` true. Space, Unicode and `/` pass; control characters, lone surrogates and zero-width/format characters fail. A non-`str` key fails.
- **Value rule:** serializable as JSON with `allow_nan=False`; compact UTF-8 serialization (`ensure_ascii=False`) at most 65,536 bytes. `NaN`/`Infinity`, non-JSON types (sets, bytes, objects) and strings with lone surrogates fail. `bool`, `None`, numbers, strings, lists and dicts with string keys pass.
- **TTL rule:** `None`, or an `int`/`float` (not `bool`) that is finite and `> 0`.
- Every violation raises `ValueError` whose message names the broken rule (`key length`, `key printable`, `value JSON`, `value size`, `ttl`), and nothing is appended.
- `get`/`delete` of a missing or expired key raise `KeyError`. Deleting an expired key appends nothing.
- **Corrupt open:** opening raises `CorruptLogError`. The error also exposes the refused store instance; on it every mutation (`set`, `delete`, `compact`) raises `CorruptLogError` and appends nothing, and reads raise `CorruptLogError` too.
- **Concurrency:** one lock per store instance serializes every operation; one process per file (D10).

### 5.4 HTTP routes (`serve.py`)

| Request | Success | Errors |
|---|---|---|
| `GET /kv/` (query string ignored) | 200, JSON array of live keys sorted ascending | 503 on a corrupt log |
| `GET /kv/<key>` | 200, `Content-Type: application/json`, the value's JSON | 404 missing/expired; 400 invalid key |
| `HEAD /kv/…` | Same status and headers as `GET`, no body | as `GET` |
| `PUT /kv/<key>[?ttl=<s>]` | 204 | 400 invalid key / JSON / ttl / missing or invalid `Content-Length`; 413 `Content-Length` > 65,536 |
| `DELETE /kv/<key>` | 204 | 404 missing/expired; 400 invalid key |

- Every error under `/kv/` answers `application/json` with `{"error": "<message>"}`; 503 means the log is corrupt and the message names the line number.
- `<key>` = the path (from `urlsplit`, query excluded) after the `/kv/` prefix, percent-decoded as UTF-8 with `errors="strict"`. Undecodable bytes → 400. `/kv/app/config` and `/kv/app%2Fconfig` are both key `app/config`. `PUT`/`DELETE /kv/` (empty key) → 400.
- `ttl` comes from the query string: absent → no TTL; present once → parsed with `float()`, must be finite and `> 0`; empty, repeated, non-numeric, `nan`, `inf`, zero or negative → 400. Other query parameters are ignored.
- The body is judged from `Content-Length` before reading: > 65,536 → 413 with the connection closed and the body never read; otherwise exactly that many bytes are read, decoded as strict UTF-8 and parsed as JSON. Invalid UTF-8, a BOM, invalid JSON, `NaN`/`Infinity`/`1e400`, or an integer the runtime refuses (over 4,300 digits) → 400. A value the store rejects (`ValueError`) → 400.
- `/kv` without the trailing slash is not a store route (404, as today). `POST` anywhere, and `PUT`/`DELETE` outside `/kv/`, keep today's `501 Unsupported method` answer from the standard handler.
- `KV_PATH` (default `./kv.log`, resolved against the working directory) selects the file.

## 6. Key Technical Decisions

1. **`/kv/` dispatched by prefix inside `RootOnlyHandler`, not through `ROUTES`.** `smoke_test.py:128-133` pins `ROUTES` to two entries and `smoke_test.py:57-61,341` builds its server from a `RootOnlyHandler` subclass, so the prefix check must live in the handler's own methods. `do_PUT`/`do_DELETE` are added; outside `/kv/` they reproduce the standard `send_error(501, "Unsupported method ('PUT')")` answer the handler gives today (checked: `PUT`/`DELETE`/`POST` on any path return 501 now).
2. **One shared store per server, opened at start-up by `main()`, lazily otherwise.** `main()` opens the store from `KV_PATH` before serving, so a torn-tail warning appears on stderr at start-up and a corrupt log is detected at start-up. A server built by `make_server` without a store (as `smoke_test.py` does) opens it on the first `/kv/` request, under a lock, so the smoke test never creates `kv.log`. A `CorruptLogError` at open is kept on the server; every `/kv/` request then answers 503 naming the line, while `/` and `/jungle` serve as before (D1).
3. **Serialized writes with one `threading.Lock` per store.** Validation, append, `fsync`, index update and any automatic compaction happen under it; reads take it too. Simple and correct for one process (D10); throughput is bounded by one fsync per mutation, acceptable for local tools. Rejected: an `RLock` per key, or a writer thread — more moving parts for no stated need.
4. **Canonical CRC serialization** (`sort_keys`, compact, `ensure_ascii=False`, `allow_nan=False`) so the CRC is reproducible from the parsed record, independent of key order in the line.
5. **The last record is the only one that can be torn.** Any invalid last record is dropped and truncated; any invalid earlier record is corruption. This is exactly the story's split; a corrupt open never modifies the file.
6. **Compaction temp file at `<path>.compact.tmp` in the same directory**, so `os.replace` is atomic on one filesystem; the directory is fsynced after the rename (POSIX). On open, a stale temp file is deleted before replay; the log itself is always the authority.
7. **Automatic compaction ratio** = live unexpired keys ÷ records in the log, checked after each successful mutation, compacting when strictly below 0.5. No minimum log size, so a store whose only key is deleted compacts to an empty file. Manual `compact()` always rewrites.
8. **Wall-clock default for `clock`** (`time.time`) because absolute `exp` values persist across restarts; tests inject a fake clock and never sleep.
9. **Ticket split follows the story's own four items** (log → store → compaction → HTTP), each landing with its own tests in `tests/`. Compaction gets its own module so t3's edit of `store.py` is a small, declared handoff. t3 and t4 both depend only on t2 and own disjoint files (t3: `kvstore/compaction.py`, `kvstore/store.py`, `tests/test_compaction.py`; t4: `serve.py`, `tests/test_http.py`, `README.md`, `.gitignore`), so they can be built in parallel; t4 uses only the public store API, which t3 does not change.

## 7. Risks & Constraints

- **Regression of `serve.py` (AC12):** `smoke_test.py` must pass unchanged, including its docstring checks (`smoke_test.py:244-248,275-280`: the docstring must keep `python3 serve.py`, `PORT=`, `HOST=` and must not say "root-only" or "exactly one document"). t4 runs it and adds tests for `PUT`/`DELETE` → 501 outside `/kv/`.
- **Unread request body on 413:** the handler speaks HTTP/1.0 (`protocol_version` default), so the connection closes after each response; t4 still marks the 413 response to close the connection so an unread body can never be parsed as a next request.
- **fsync cost:** one fsync per mutation; the concurrency test (1000 sets) takes seconds on slow disks but needs no sleeping.
- **Wall-clock jumps** can expire keys early or late; acceptable for local tools and documented as a property of the default clock.
- **Memory:** the whole index lives in memory; with 64 KiB values this is fine for the stated use (small shared state), not for large data sets.
- **Security:** no authentication (out of scope). Default bind stays `127.0.0.1`; the README warns about `HOST=0.0.0.0` (D11). Keys never reach the filesystem, so there is no path traversal surface; request bodies are capped before reading.
- **Platforms:** atomic `os.replace` and directory fsync are POSIX behaviour; on Windows the directory fsync is skipped.

## 8. Assumptions

- **A1 — Refused store is reachable from the error.** The spec wants both "opening raises `CorruptLogError`" and "a mutation on a store opened over a corrupt log raises `CorruptLogError`". The design exposes the refused instance on the error. Risk if wrong: low; it only changes how AC17's test reaches the instance.
- **A2 — HEAD under `/kv/` mirrors GET.** The spec is silent; `serve.py`'s convention is that HEAD routes like GET (`smoke_test.py:346-350`). Risk: none for existing paths, which keep 404.
- **A3 — Missing or invalid `Content-Length` on PUT returns 400.** The spec judges size from the declared length and names no status for its absence; chunked uploads are not supported by `BaseHTTPRequestHandler` anyway.
- **A4 — No minimum log size before automatic compaction**, following the spec's 50 % rule literally.
- **A5 — Deleting an expired key raises `KeyError` and appends nothing**, matching "expired keys behave as if absent".
