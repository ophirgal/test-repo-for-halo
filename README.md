# test-repo-for-halo

## Hello World script

Print the greeting from a Bash terminal (needs nothing beyond Bash; arguments are ignored):

```bash
bash hello_world.sh
# Hello, World!
```

Run its automated test:

```bash
bash test_hello_world.sh
# OK: 13 checks passed
```

## Key-value store (`/kv/`)

`kvstore` is a small key-value store that uses only the Python standard library. It keeps JSON values by key in one append-only log file, and each key can have its own expiry (TTL). `serve.py` serves it under `/kv/`, next to the Hello World pages:

```bash
python3 serve.py                        # store file ./kv.log
KV_PATH=/tmp/demo-kv.log python3 serve.py
```

- **Store file:** `KV_PATH` sets where the log lives. The default is `./kv.log`, relative to the directory you start the server from. `kv.log` is listed in `.gitignore`.
- **Keys:** 1–128 printable characters. Spaces, Unicode and `/` are allowed. Over HTTP, the key is the percent-decoded rest of the path after `/kv/`.
- **Values:** any JSON value whose compact UTF-8 JSON is at most 64 KiB (65,536 bytes).
- **TTL:** `?ttl=<seconds>` on a `PUT`, a number greater than 0 (fractions allowed). A `PUT` without `ttl` removes any earlier expiry.

### Routes

```bash
# Store a value (204 No Content)
curl -i -X PUT --data '{"theme":"dark"}' http://127.0.0.1:8000/kv/settings

# Store a value that expires after 60 seconds
curl -i -X PUT --data '"temporary"' 'http://127.0.0.1:8000/kv/session?ttl=60'

# Read a value (200 with the JSON value, or 404)
curl -i http://127.0.0.1:8000/kv/settings

# List the live keys (200 with a JSON array, sorted)
curl -i http://127.0.0.1:8000/kv/

# A key may contain "/"; /kv/app/config and /kv/app%2Fconfig are the same key
curl -i -X PUT --data '1' http://127.0.0.1:8000/kv/app/config
curl -i http://127.0.0.1:8000/kv/app%2Fconfig

# Percent-encode spaces and Unicode in keys
curl -i -X PUT --data '"hi"' http://127.0.0.1:8000/kv/my%20key

# Delete a key (204, or 404 if it is missing or expired)
curl -i -X DELETE http://127.0.0.1:8000/kv/settings
```

`HEAD` on a `/kv/` path answers like `GET`, without the body.

### Errors

Every error under `/kv/` answers with `Content-Type: application/json` and a body `{"error": "..."}`:

| Status | When |
|---|---|
| 400 | The body is not valid JSON (including invalid UTF-8, a BOM, `NaN`/`Infinity`), the key is invalid, `ttl` is invalid (zero, negative, empty, repeated, not a number), the value is rejected (over 64 KiB once serialized), or a `PUT` has no valid `Content-Length` |
| 404 | The key does not exist or has expired |
| 413 | The `PUT`'s `Content-Length` is over 65,536 bytes; the body is not read |
| 503 | The log is corrupt before its last line. The message names the line. `/` and `/jungle` still work; fix or move the file and restart |

If the last line of the log was torn by a crash, the server drops it at start-up, truncates the file, and prints a warning on stderr that names the byte offset.

> **Warning:** the store has no authentication. The server binds to `127.0.0.1` by default. `HOST=0.0.0.0 python3 serve.py` exposes unauthenticated read and write access to the store to your whole network.

### Tests

```bash
python -m unittest discover -s tests
python3 smoke_test.py
```

## Link checker (linkcheck)

Check every HTML page of the docs site for broken internal links and missing
anchors, offline (standard library only, Python 3; nothing is ever fetched):

```bash
python -m linkcheck docs/
# no output and exit code 0 when every link resolves
```

Usage:

```bash
python -m linkcheck <dir> [--json FILE] [--markdown FILE] [--ignore PATTERN ...]
```

- `<dir>` — the directory to crawl; every `.html` file under it is checked.
  Only `href`/`src` on `a`, `link`, `img` and `script` count. A link starting
  with `/` resolves against `<dir>`; `guide/` resolves to `guide/index.html`.
- `--json FILE` — write a report `{"pages", "links", "ignored", "external", "findings"}`,
  sorted by path then line, byte-identical across runs.
- `--markdown FILE` — write a summary table and one section per page with
  findings, ready for a CI job summary.
- `--ignore PATTERN` — skip links whose target matches the `fnmatch` pattern
  (case-sensitive, repeatable, e.g. `--ignore 'drafts/*'`); they are counted as ignored.

Each finding is printed on its own line as `path:line: kind: target`, with the
path relative to `<dir>`:

```text
guide/intro.html:12: missing-target: guide/setup.html
```

| Kind | Meaning |
| --- | --- |
| `empty-link` | `href`/`src` is empty |
| `missing-target` | the linked file does not exist (target is its path relative to `<dir>`) |
| `missing-anchor` | the linked page has no element with that `id` (or `a` with that `name`) |
| `outside-root` | the link resolves outside `<dir>` (never read) |
| `decode-error` | the page is not valid UTF-8 (target is `byte <offset>`) |

External links (`https:`, `mailto:`, `//host/...` and any other scheme except
`file:`) are listed in the JSON report but never fetched and never a finding.

Exit codes: `0` no findings, `1` one or more findings, `2` usage error (missing
or non-directory `<dir>`, bad option), an unreadable page, or a report that
cannot be written.

In CI (for example a GitHub Actions `run:` step), keep the job failing on
broken links while always publishing the report to the job summary:

```bash
status=0
python -m linkcheck docs/ --markdown linkcheck.md || status=$?
cat linkcheck.md >> "$GITHUB_STEP_SUMMARY"
exit $status
```

Run the link checker's tests:

```bash
python -m unittest discover -s tests
```
