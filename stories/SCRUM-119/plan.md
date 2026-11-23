# SCRUM-119 — Implementation plan: append-only key-value store with TTL, compaction and an HTTP API

## Context

SCRUM-119 adds `kvstore`, a new Python package at the repository root that uses only the standard library. It keeps JSON values by key in one append-only JSON-lines log with CRC32 per record and an optional per-key TTL on an injected clock. It recovers from a torn last record, refuses a log corrupted in the middle, and compacts atomically, both manually and automatically. The existing `serve.py` exposes the store under `/kv/` without changing any answer it gives today. That covers AC1–AC18: replay, torn tail, corruption, dict API, expiry, validation, concurrency, compaction, crash safety, routes, errors, regression, docs, 503 on a corrupt log, auto-compaction, key rules, limits and TTL rules, and housekeeping. The change lands in `ophirgal/test-repo-for-halo` on `halo/feat/scrum-119-20261123-173828`, which merges into `main`. `spec.md` (FR1–FR16, AC1–AC18, decisions D1–D12), `hld.md` (contracts §5, decisions §6, assumptions A1–A5) and `work-items.md` (t1–t4) sit beside this file in `stories/SCRUM-119/`.

## Research findings

**Repository layout (fact).** The root is flat: `serve.py`, `smoke_test.py`, `hello_world.sh`, `test_hello_world.sh`, `README.md`, `docs/` and `stories/`. None of these exist: `kvstore/`, `tests/`, `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `.factory/`, `.github/`, a package manifest, a linter or formatter config. An untracked `__pycache__/` exists at the root because there is no `.gitignore`. The interpreter is Python 3.12.15.

**Change surface.**
- New: `kvstore/__init__.py`, `kvstore/log.py`, `kvstore/store.py`, `kvstore/compaction.py`, `tests/test_log.py`, `tests/test_store.py`, `tests/test_compaction.py`, `tests/test_http.py`, `.gitignore`.
- Edited: `serve.py` and `README.md`.
- `serve.py` facts:
  - The module docstring promises "Every other path returns 404" (`serve.py:6`). Its usage block is at `serve.py:11-17`.
  - `ROUTES = {"/": INDEX, "/jungle": JUNGLE}` is at `serve.py:38`.
  - `RootOnlyHandler` is at `serve.py:41-75`. It implements only `_route`, `do_GET` and `do_HEAD`, and its docstring says "everything else 404" (`serve.py:42`).
  - `make_server(host, port, handler)` returns a `ThreadingHTTPServer` (`serve.py:78-80`).
  - `main(argv)` builds the server, prints `serving Hello World on …` and serves (`serve.py:96-108`).
  - The handler keeps the default `protocol_version` (HTTP/1.0).
- `PUT`, `DELETE` and `POST` currently fall through to `BaseHTTPRequestHandler`, which answers `send_error(501, "Unsupported method (%r)" % self.command)`.

**Contracts that `smoke_test.py` pins (fact; AC12 says the file stays unchanged).**
- `serve.ROUTES == {"/": serve.INDEX, "/jungle": serve.JUNGLE}` (`smoke_test.py:128-133`).
- The module docstring must contain `python3 serve.py`, `PORT=` and `HOST=` (`smoke_test.py:275-281`). Its lowercased text must not contain `root-only` or `exactly one document` (`smoke_test.py:245-248`).
- The smoke test subclasses `RootOnlyHandler` as `QuietHandler` (`smoke_test.py:56-60`) and builds `make_server("127.0.0.1", 0, QuietHandler)` (`smoke_test.py:383`). The `/kv/` logic therefore has to live in `RootOnlyHandler`'s methods, and `make_server`'s signature stays as it is.
- Some paths must still answer 404, among them `/foo/bar`, `/README.md`, `/jungle/` and `/docs/index.html` (`smoke_test.py:22-39`).

**Contracts this story creates.** `hld.md` §5 locks the record format, the canonical CRC serialization, the recovery rules, the Python API rules and their `ValueError` rule names (`key length`, `key printable`, `value JSON`, `value size`, `ttl`), and the HTTP route/status table. They are quoted there and not repeated here.

**Existing test layers and gate (fact).**
- `python3 smoke_test.py` prints `OK: <n> checks passed`, exit 0.
- `bash test_hello_world.sh` prints `OK: 13 checks passed`.
- The spec fixes `python -m unittest discover -s tests` as the runner for the new `tests/` layer (`spec.md` §6).
- No CI exists and no build or lint step exists.
- `run-tests-gate.sh` resolves its command from `DEV_TOOLKIT_TEST_CMD`, then from `local-test-gate:` in `.factory/testing.md`, then by discovery (Makefile `test`, `npm test`, `go test`, pytest config). None of these exists here, so the local gate records `not_declared` unless the platform configures `DEV_TOOLKIT_TEST_CMD`.

**Import path (fact).** Running `python -m unittest discover -s tests` from the root puts the working directory on `sys.path`, so tests can `import kvstore` and `import serve`. `tests/` does not need `__init__.py` because the top-level directory defaults to the start directory.

**External data.** None. The work uses only the standard library and no other system.

**Unknowns left after research.** None block the work. New public names not fixed by any source are listed as assumptions below.

## Locked decisions and assumptions

**Locked decisions**
- The package is stdlib only, including its tests, and lives at the root as `kvstore/`. Tests live in `tests/` and run with `python -m unittest discover -s tests` (`spec.md` §2, §6).
- Record format, CRC rule and recovery split: torn last record versus corruption earlier in the log (`hld.md` §5.1–5.2; FR1–FR4).
- API rules (`hld.md` §5.3; FR5–FR9a):
  - Keys are 1–128 characters and pass `str.isprintable()` (D3).
  - Values are at most 65,536 bytes as compact UTF-8 JSON, and exactly 65,536 is allowed (D8).
  - `ttl` is finite and `> 0`. It is not a `bool` (D6).
  - A re-set without `ttl` clears the expiry (D7).
  - `keys()` returns keys sorted ascending (D9).
  - One process per file is supported (D10).
- The torn-tail warning is a `warnings` warning that names the byte offset (D4). After a corrupt open, every mutation raises `CorruptLogError` and appends nothing (D5).
- Compaction (`hld.md` §6.6–6.7; FR9–FR10; D2):
  - Records are written to `<path>.compact.tmp` in the same directory, which is fsynced, then `os.replace`d over the log, then the directory is fsynced.
  - Automatic compaction runs when live ÷ records is strictly below 0.5.
  - A manual `compact()` always compacts.
  - A stale temp file is removed on open.
- HTTP (`hld.md` §5.4, §6.1–6.2; FR11–FR16; D1, D11, D12):
  - `/kv/` is dispatched by prefix inside `RootOnlyHandler`, and `ROUTES` is untouched.
  - The server shares one store. `main()` opens it eagerly and `make_server` opens it lazily.
  - Every `/kv/` request answers 503 on a corrupt log.
  - A `Content-Length` over 65,536 gets 413 with the body unread.
  - `PUT`/`DELETE` outside `/kv/` and `POST` keep the 501 answer.
  - `KV_PATH` defaults to `./kv.log`.
  - The README carries a `HOST=0.0.0.0` warning, and `.gitignore` lists `kv.log`.
- File ownership per work item, with t3 and t4 disjoint (`hld.md` §6.9; `work-items.md`).

**Assumptions** (new names; no source fixes them)
- The store class is `KVStore`, exported from `kvstore` (from the `hld.md` §2 diagram). If wrong, rename one symbol; no behaviour changes.
- The torn-tail warning class is a new `TornTailWarning(UserWarning)` in `kvstore/log.py`. Evidence: `hld.md` §5.2 requires a `UserWarning` subclass. If wrong, only the class name changes.
- `CorruptLogError` carries `path`, `lineno` and `store`. `store` is the refused instance (hld A1). If wrong, only how the AC3/AC17 tests reach the instance changes.
- The log helper's replay returns the record count along with the index and the good-prefix length, so t3 can compute the ratio without editing `kvstore/log.py`. If wrong, t3 makes an additive change to `log.py`, which it does not own.
- A file ending in `\n\n` has an empty last record, which is treated as torn and truncated. Evidence: `hld.md` §5.1 makes an empty line invalid, and §5.2 treats any invalid last record as torn. If wrong, one edge test changes.
- HEAD under `/kv/` mirrors GET (hld A2). A missing or invalid `Content-Length` on PUT returns 400 (hld A3). Automatic compaction has no minimum log size (hld A4). Deleting an expired key raises `KeyError` and appends nothing (hld A5).

## Solution proposal

**Layering.** The work has four layers, each owned by one work item and covered by its own `tests/test_*.py`:
1. `kvstore/log.py` is pure record I/O.
2. `kvstore/store.py` holds state, rules and the lock.
3. `kvstore/compaction.py` holds the file-swap mechanics.
4. `serve.py` is a thin HTTP adapter.

`kvstore` knows nothing about HTTP. `serve.py` uses only the public `kvstore` API and maps exceptions to statuses: `ValueError` → 400, `KeyError` → 404, `CorruptLogError` → 503.

**Log (t1).**
- `encode_record(op, k, v, exp)` builds the record without `crc`. It serializes the record canonically with `separators=(",", ":")`, `sort_keys=True`, `ensure_ascii=False`, `allow_nan=False`, sets `crc = zlib.crc32(bytes)`, and returns the line with `crc` added and a trailing `\n`.
- `replay(path)` works in this order:
  1. Read the file as bytes and split on `\n`, tracking each record's start offset.
  2. Validate every record: UTF-8, a JSON object, the exact key set, `op`, the key rule, a finite numeric or null `exp`, and the CRC recomputed after removing `crc`.
  3. Raise `CorruptLogError` without writing if any record other than the last is invalid. Validating everything before deciding keeps the file untouched when the middle is corrupt and the tail is also torn.
  4. Otherwise, if the last record is invalid, truncate to its start offset and warn with `TornTailWarning`, naming the offset.
  5. Return the index (`k → (v, exp)`), the record count, and whether the file ends without `\n`.
- A missing file is created empty.
- The key rule is one shared function in `log.py`, so replay, the store and HTTP accept exactly the same keys.

**Store (t2).**
- The signature is `KVStore(path, *, clock=time.time)`.
- Open replays through `log.py` and then opens an append handle.
- If the file ended without `\n`, the first append writes `\n` before its record.
- One `threading.Lock` per instance covers every public method.
- A mutation runs in this order: validate (key, value, `ttl`) → `exp = clock() + ttl` → write → `flush` → `os.fsync` (called through the `os` module so tests can patch it) → update the index and record count.
- Reads treat `exp is not None and exp <= clock()` as absent. At clock 110 with `exp` 110 the key is absent, as AC5 requires.
- On a corrupt log, `__init__` marks the instance refused, attaches it to the error and re-raises. A refused instance raises `CorruptLogError` from every method except `close()`.
- `close()`, `__enter__` and `__exit__` support context-manager use.

**Compaction (t3).**
- `compaction.write_and_swap(path, records)` runs in this order:
  1. Write the `set` records, keeping each key's `exp`, to `<path>.compact.tmp`.
  2. `flush` and `os.fsync` the temp file.
  3. `os.replace` it over the log.
  4. Fsync the directory with `os.open(dir, os.O_RDONLY)`. Skip this step when `os.name == "nt"`.
- `compaction.remove_stale_temp(path)` runs first in `KVStore.__init__`.
- The store's `compact()` checks the refused state, closes the append handle, swaps, reopens the handle and resets the record count. All of this happens under the lock.
- The automatic trigger runs at the end of each successful mutation, still under the lock, and compacts when `live_unexpired / records < 0.5`.

**HTTP (t4).**
- `do_GET`, `do_HEAD`, `do_PUT` and `do_DELETE` first check whether `urlsplit(self.path).path` starts with `/kv/`.
  - If it does, the request goes to a `_kv_dispatch` method.
  - If it doesn't, `do_GET` and `do_HEAD` run their current code unchanged. `do_PUT` and `do_DELETE` call `self.send_error(501, "Unsupported method (%r)" % self.command)`, which reproduces today's answer byte for byte.
- `/kv` without the trailing slash keeps the existing 404.
- Store state lives on the server object. `_kv_store(self)` reads `self.server`:
  - If a store is already attached, use it.
  - If not, open `KV_PATH` once under a module-level lock.
  - If the open raised `CorruptLogError`, keep the error on the server, and every `/kv/` request answers 503 with that message.
- `main()` opens the store before `serve_forever()`, so a torn-tail warning appears on stderr at start-up. It catches `CorruptLogError`, prints it to stderr, keeps it on the server, and still serves.
- Key decoding: take the path text after `/kv/` and apply `urllib.parse.unquote(…, encoding="utf-8", errors="strict")`. A `UnicodeDecodeError` gives 400. Validate with the shared key rule.
- `ttl`: `parse_qs(query, keep_blank_values=True)`, then reject the value if it is repeated or empty, if `float()` fails, if it is not `math.isfinite`, or if it is `<= 0`.
- PUT checks `Content-Length` before reading:
  - Missing or not a non-negative integer → 400.
  - Over 65,536 → 413, with `Connection: close` and `self.close_connection = True`, and the body is never read.
  - Otherwise read exactly that many bytes, decode as strict UTF-8, then `json.loads` with a `parse_constant` that rejects `NaN`/`Infinity`. A BOM fails in `json.loads`, an integer over 4,300 digits raises `ValueError`, and `1e400` becomes `inf`, which the store's `allow_nan=False` check rejects.
- Every `/kv/` answer goes through one `_kv_send(status, payload)` helper. It writes `application/json` with `Content-Length`, writes no body for HEAD or 204, and wraps errors as `{"error": msg}`.

**Alternatives rejected.**
- Adding `/kv/` to `ROUTES`. `smoke_test.py:128-133` forbids it.
- A separate HTTP server module. The spec requires the routes in `serve.py`.
- A per-key lock or a writer thread. They add complexity without meeting any stated need (`hld.md` §6.3).
- Checking the ratio on a timer. The work would need background threads, and `hld.md` §3 rules them out.
- A monotonic clock default. `exp` has to stay meaningful across restarts.

## Ordered implementation steps

**t1 — log format, replay, recovery**
1. Create `kvstore/log.py` with `CorruptLogError(Exception)` (`path`, `lineno`, `store=None`), `TornTailWarning(UserWarning)`, the shared key-rule check, `encode_record` and `replay` as described in the Solution proposal. Create `kvstore/__init__.py` exporting `CorruptLogError` and `TornTailWarning`. Advances AC1, AC2 and AC3 (detection). Layer: unittest (`tests/`).
2. Create `tests/test_log.py`. Cover:
   - an independent CRC computation that matches the encoded `crc`;
   - three `set` records and one `del` replaying to two live keys with their latest values (AC1);
   - a missing file and an empty file;
   - torn tails: truncated mid-record, bad CRC, not JSON, extra or missing keys, unknown `op`, invalid `k`, an empty last line, each with and without a trailing `\n`. Each case uses `warnings.catch_warnings(record=True)`, checks that the message contains the offset, and checks the exact file bytes after truncation (AC2);
   - a valid last record without `\n` that is kept;
   - a corrupt middle record and an empty middle line, both giving `CorruptLogError.lineno` as a 1-based number with the path in the message, and the file bytes unchanged even with a torn tail as well (AC3);
   - Unicode keys and values, and values with embedded `\n`, round-tripping.

   Layer: unittest.

**t2 — store API**
3. Create `kvstore/store.py` with `KVStore` covering the lock, the clock, validation in the hld order with the `ValueError` rule names, `set`, `get`, `delete`, `keys`, `close` and the context manager. Fsync each mutation through `os.fsync`. Write the pending-newline prefix on the first append. Implement the refused instance on a corrupt open. Add `KVStore` to the exports in `kvstore/__init__.py` (handoff from t1). Advances AC4–AC7, AC16 (API) and AC17 (API). Layer: unittest.
4. Create `tests/test_store.py`. Cover:
   - dict semantics, and `KeyError` on a missing or expired key;
   - `patch("os.fsync", wraps=os.fsync)`, with the call count rising on each mutation, and a reopen that sees every value (AC4);
   - a fake clock: `set("a", 1, ttl=10)` at 100, a value at 109.9, `KeyError` at 110 and after, `keys()` without the key, and expiry surviving a reopen (AC5);
   - deleting an expired key leaving the log bytes unchanged;
   - re-set without `ttl` clearing the expiry (AC17);
   - key rules: 129 characters, empty, `"\x00"`, `"​"`, a lone surrogate and non-`str` keys rejected, with the log bytes unchanged; space, Unicode and `/` accepted (AC6, AC16);
   - value rules: exactly 65,536 bytes accepted, 65,537 rejected with `value size`, and NaN, a set, bytes and a lone-surrogate string rejected with `value JSON` (AC6, AC17);
   - `ttl` values 0, -1, `nan`, `inf`, `True` and `"5"` rejected with `ttl`, and 0.5 accepted (AC17);
   - two threads each setting 500 distinct keys, then a reopen with all 1000 present (AC7);
   - a corrupt open whose `err.store` raises `CorruptLogError` on `set`, `delete`, `get` and `keys`, with the bytes unchanged (AC3, AC17);
   - a torn tail at open, after which writes still work.

   No `time.sleep`. Layer: unittest.

**t3 — compaction** (parallel with t4)
5. Create `kvstore/compaction.py` with `write_and_swap` and `remove_stale_temp`. Edit `kvstore/store.py` (handoff from t2) to:
   - call `remove_stale_temp` before replay;
   - add `compact()`, which raises `CorruptLogError` on a refused store before touching any file;
   - add the automatic trigger after a successful `set` or `delete`;
   - reopen the append handle and reset the record count after a swap.

   All of this runs under the store lock. Advances AC8, AC9 and AC15. Layer: unittest.
6. Create `tests/test_compaction.py`. Cover:
   - `compact()` leaving exactly one CRC-valid `set` per live key with its `exp` kept, no `del` or expired records, and the same `get`/`keys()` results before, after and after a reopen (AC8);
   - an order check with `os.fsync` and `os.replace` patched to wrap and record calls: temp fsync, then replace, then directory fsync (AC8);
   - a manual `compact()` on a fully live log still rewriting;
   - automatic compaction when the ratio is below 0.5 (for example `set a` three times), and no rewrite at exactly 0.5 (`set a` twice) (AC15);
   - writes after a compaction surviving a reopen;
   - `os.replace` patched to raise after the temp file is written, leaving the original log byte-identical, with the reopen deleting `<path>.compact.tmp` (AC9);
   - a refused store whose `compact()` raises, with no temp file created;
   - threaded sets interleaved with `compact()` losing no key after a reopen.

   Layer: unittest.

**t4 — HTTP, README, .gitignore** (parallel with t3)
7. Edit `serve.py`:
   - add the store state on the server, `_kv_store`, `_kv_dispatch`, `_kv_send`, the `/kv/` prefix check in `do_GET`/`do_HEAD`, and new `do_PUT`/`do_DELETE`;
   - open `KV_PATH` eagerly in `main()`, handling `CorruptLogError`;
   - add imports from the standard library only (`json`, `math`, `threading`, `kvstore`).

   `ROUTES`, `make_server`'s signature and the `serving Hello World …` line stay unchanged. Advances AC10, AC11, AC12, AC14, AC16 (HTTP) and AC17 (HTTP). Layer: unittest plus `smoke_test.py`.
8. Edit the `serve.py` module docstring and the `RootOnlyHandler` docstring:
   - state the `/kv/` exception to "every other path returns 404";
   - add a `KV_PATH=… python3 serve.py` usage line;
   - keep the `python3 serve.py`, `PORT=` and `HOST=` lines;
   - never write the phrases `root-only` or `exactly one document`.

   Advances AC12. Layer: `smoke_test.py` docstring checks.
9. Create `tests/test_http.py`. Start `make_server("127.0.0.1", 0, quiet subclass)` in a thread with `KV_PATH` set to a temp file. Use `urllib.request` for normal calls and `http.client` or a raw socket for malformed ones. Cover:
   - every route in AC10, including `Content-Type: application/json` and the sorted list;
   - HEAD mirroring GET;
   - `/kv/app/config` and `/kv/app%2Fconfig` being the same key, and a percent-encoded space or Unicode key being readable through `KVStore.get` on a reopened file (AC16);
   - every 400 case in work item t4: bad JSON, BOM, invalid UTF-8, `NaN`, `1e400`, an integer over 4,300 digits, an invalid or empty key, undecodable percent-encoding, each bad `ttl`, a missing or invalid `Content-Length`, and a value the store rejects (AC11, AC17);
   - a raw socket sending `Content-Length: 100000` with a tiny body and getting a 413 JSON answer within a timeout (AC11);
   - a body of exactly 65,536 bytes being accepted;
   - TTL expiry, with the server's store given a fake clock by pre-attaching a `KVStore(path, clock=…)` to the server;
   - a restart (a new server on the same `KV_PATH`) that keeps the data;
   - a corrupt `KV_PATH` answering 503 with the line number for GET, HEAD, PUT and DELETE, `/` and `/jungle` still answering 200, and the file unchanged (AC14);
   - regression: `/kv`, `/foo/bar` and `/jungle/` still 404 for GET and HEAD; PUT and DELETE on `/` and `/foo` still 501 with the same body as before; `POST /kv/x` still 501 (AC12);
   - a subprocess `python3 smoke_test.py` with `KV_PATH` set to an absent temp path, exiting 0 with the path still absent (AC12, lazy open);
   - a subprocess `python3 serve.py 0` with a torn `KV_PATH` that prints the offset warning on stderr before the `serving` line, then is terminated.

   Layer: unittest (end-to-end over localhost).
10. Edit `README.md`. Keep the Hello World section and add a key-value store section covering:
    - `KV_PATH` and its default `./kv.log`;
    - curl examples for GET key, GET list, PUT with and without `?ttl=`, DELETE, a key containing `/`, and a percent-encoded key;
    - the 400/404/413/503 meanings;
    - the `HOST=0.0.0.0` warning about unauthenticated read and write.

    Advances AC13 and AC18. Layer: none automated, so the reviewer checks it. Optionally, `tests/test_http.py` asserts that README contains `KV_PATH`, `./kv.log`, `/kv/` and `HOST=0.0.0.0`.
11. Create `.gitignore` containing `kv.log`. Advances AC18. Layer: a `tests/test_http.py` assertion that `.gitignore` lists `kv.log`.

**Invariants every step covers.**
- Validation and error paths come before any write, and nothing is appended on an error.
- All state access is serialized under the store lock, and the HTTP lazy open is serialized under its own lock.
- A corrupt open never modifies the log. Only the stale temp file may be removed.
- There is no authorization or tenancy, by design (out of scope).
- There are no dependencies to acquire: the standard library only, and no network beyond localhost in tests.
- There are no generated deliverables and no binaries.

## Work-item mapping

| Step | Work item |
|---|---|
| 1, 2 | t1 — kvstore log format, replay and crash recovery |
| 3, 4 | t2 — kvstore store API with TTL, validation, durability and thread safety |
| 5, 6 | t3 — kvstore atomic compaction, manual and automatic, with crash-safe temp files |
| 7, 8, 9, 10, 11 | t4 — Serve the store under /kv/ in serve.py, with README and .gitignore |

Every work item has steps. t3 and t4 touch disjoint files: t3 owns `kvstore/compaction.py` and `kvstore/store.py`; t4 owns `serve.py`, `tests/test_http.py`, `README.md` and `.gitignore`. Either can land first after t2.

## Verification and CI gate

**Canonical gate.** Run from the repository root, in this order:
1. `python -m unittest discover -s tests`
2. `python3 smoke_test.py`
3. `bash test_hello_world.sh` (unchanged, for regression)

No provider CI exists, so nothing runs the gate at the head on the provider side, and this story adds none.

**Local run.** The one local run is `run-tests-gate.sh --run` on each work item's committed SHA. No `.factory/testing.md` exists and nothing is discoverable, so the gate records `not_declared` unless the platform supplies `DEV_TOOLKIT_TEST_CMD`. That status is to be reported as it is, not worked around.

**Pod limits.** Every layer runs in a pod. The HTTP tests bind only to `127.0.0.1` on ephemeral ports. Directory fsync is POSIX, and the Windows skip branch is not exercised.

**Done means:**
- after each work item, all `tests/` modules present at that point pass, and `smoke_test.py` prints `OK: <n> checks passed` with the same `<n>` as on `main`;
- after t4, every AC1–AC18 has at least one passing test, except AC13's prose, which the reviewer checks;
- no test sleeps;
- no `kv.log` appears in the working tree after the gate.

**Not applicable.** `.factory/delivery-assets` has no new binaries to declare. There is no CI configuration task.

## Risks and scope guards

**Risks**
- **Regression in `serve.py`.** Mitigation: the prefix check comes first, and the non-`/kv/` branches keep the existing code. The t4 tests compare PUT/DELETE/POST 501 bodies with the standard handler's, and `smoke_test.py` runs unchanged.
- **The 413 test hanging.** If the server read the body, a raw-socket test with a short body would block. Use a socket timeout so a regression fails instead of hanging.
- **fsync cost.** The 1000-key concurrency test does 1000 fsyncs, which takes seconds on slow disks. That is acceptable, and it uses no sleeps.
- **Float expiry boundary.** `100 + 10 == 110` exactly, so AC5 is safe. Tests use exactly representable clock values.
- **The gate reports `not_declared`.** Without a declared local gate, the factory cannot record a green run on its own. Declaring one in `.factory/testing.md` is not part of any work item. Whether to add it is the developer's call, outside this story.
- **Auto-compaction churn.** Repeatedly overwriting one key compacts every few writes. This is accepted under D2/A4.

**The implement phase must NOT:**
- edit `smoke_test.py`, `test_hello_world.sh`, `hello_world.sh`, `docs/` or any other story's folder;
- change `serve.ROUTES`, the `make_server` signature, `_resolve_port`, the default host or port, or the `serving Hello World …` line;
- add any third-party dependency, `requirements.txt`, `pyproject.toml`, a test framework other than `unittest`, or a CI workflow;
- add `__pycache__/` or anything other than `kv.log` to `.gitignore`;
- add authentication, replication, multi-key transactions, prefix scans or an HTTP compaction route;
- let t4 touch `kvstore/*` or t3 touch `serve.py`;
- skip, weaken or delete a failing check, including the smoke test's docstring checks. A blocked check is reported as blocked.
- write the phrases `root-only` or `exactly one document` in `serve.py`'s module docstring.

## Clarification outcomes

None.
