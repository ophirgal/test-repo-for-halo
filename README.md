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

## Health check (`/healthz`)

`serve.py` answers a fixed health check at `/healthz`, so a probe can tell the server is up:

```bash
python3 serve.py
curl -i http://127.0.0.1:8000/healthz
# HTTP/1.0 200 OK
# Content-Type: application/json
# ...
# {"status": "ok"}

curl -I http://127.0.0.1:8000/healthz   # HEAD: the same 200 and headers, no body
```

- **Answer:** `GET /healthz` answers `200` with `{"status": "ok"}` as `application/json`. `HEAD /healthz` works too, with the same headers and no body.
- **Path:** matched exactly; a query string is ignored (`/healthz?x=1` answers the same). `/healthz/` and other look-alikes answer `404`.
- **Store state:** it does not reflect the key-value store's state. It answers `200` even when `/kv/` answers `503` (corrupt log) or `500` (store I/O error), and it never creates the store file.
- **Down:** when the server is not running there is no answer (connection refused or a timeout); there is no "unhealthy" answer.
- **Authentication:** none, like the rest of `serve.py`. It binds to `127.0.0.1` by default and the answer carries nothing beyond "ok".

## Guestbook (`/guestbook`)

`serve.py` serves a guestbook page at `/guestbook`. A visitor, with no account and no sign-in, writes one line and presses Send; the page lists the latest messages, newest first, each with its send time:

```bash
python3 serve.py                                   # messages in ./guestbook.jsonl
GUESTBOOK_PATH=/tmp/guestbook.jsonl python3 serve.py
# open http://127.0.0.1:8000/guestbook in a browser
```

- **Messages:** one line of 1–200 characters (Unicode code points). Line breaks become a space and spaces at both ends are trimmed before the count. An empty message, or one over 200 characters, is not saved and never cut: the page answers `400`, keeps the text in the field and says why.
- **List:** the latest 20 messages, newest first, each with its send time as `YYYY-MM-DD HH:MM` (24-hour, the server's local time). Every message is shown as plain text, exactly as written.
- **Sending:** the form posts `message` (`application/x-www-form-urlencoded`) to `/guestbook`, which answers `303` back to the page, so a refresh does not send again. Other answers: `400` (bad `Content-Length` or not UTF-8), `413` (over 64 KiB, the body is not read), `415` (not a form) and `500` (the file cannot be read or written). `POST` to any other path answers `501` as before.
- **Message file:** `GUESTBOOK_PATH` sets it. The default is `./guestbook.jsonl`, relative to the directory you start the server from; it is listed in `.gitignore`. It holds one JSON object per line, `{"t": "<UTC time>", "m": "<text>"}`, oldest first. Opening the page never creates the file, and its directory is never created. A line that is not a valid record is skipped with a warning on stderr naming its line number.
- **Deleting a message:** remove its line from the file, then restart the server (the latest messages are read once, on first use).

> **Warning:** the guestbook has no authentication and no content filter. The server binds to `127.0.0.1` by default. `HOST=0.0.0.0 python3 serve.py` lets your whole network write to the guestbook without signing in.

## Newsletter export

Newsletter signups are kept in one file on the machine that runs `serve.py`. The marketing team exports them as CSV with a command run on that same machine. No web address returns the list.

```bash
python3 -m newsletter export                      # CSV to stdout
python3 -m newsletter export -o subscribers.csv   # CSV to a file (overwritten)
NEWSLETTER_PATH=/srv/newsletter.jsonl python3 -m newsletter export -o subscribers.csv
```

- **Signup file:** `NEWSLETTER_PATH` sets it. The default is `./newsletter.jsonl`, relative to the directory you run the command or the server from; it is listed in `.gitignore`. It holds one JSON object per line, `{"t": "<UTC time>", "n": "<name>", "e": "<email>"}`, oldest first. Each address is stored once: a repeat (ignoring letter case and surrounding spaces) keeps the first name and time. A line that is not a valid record is skipped with a warning on stderr naming its line number. Reading never creates the file.
- **Columns:** a header row `name,email,signed_up_at`, then one row per signup, oldest first. `signed_up_at` is ISO 8601 in UTC, to the second (`2026-11-26T09:03:07Z`), so signups can be counted per hour. An empty or missing file exports the header only.
- **Format:** UTF-8 without a BOM, standard CSV quoting (names with commas or quotes stay whole) and `\r\n` line endings. In Excel, import the file as UTF-8 so non-ASCII names show correctly.
- **Formula guard:** a cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return is written with a leading `'`, so a spreadsheet does not run it as a formula. Such a value differs from the stored one by that one character.
- **Exit codes:** `0` success; `1` the signup file cannot be read or the `-o` file cannot be written (one line on stderr, and no partial file is left); `2` a usage error, such as an unknown subcommand.
- **One server process:** run only one server process, `serve.py`, per signup file. Two processes on the same file could store one address twice.

> **Personal data:** the signup file and every export hold names and email addresses. Keep them off shared folders and out of version control, and delete old exports when they are no longer needed.

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
