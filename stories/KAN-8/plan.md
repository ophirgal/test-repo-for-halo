# Implementation Plan — KAN-8: Simple Hello World webpage

Work item: **t1** — "KAN-8: Hello World page with root-only server and smoke test"  
Repository: `ophirgal/test-repo-for-halo` (id `03b40291-ca08-4b8d-8c13-6389b0a66054`)  
Branch: `halo/feat/kan-8` → base `main`

## 1. Context

The epic's only deliverable is a proof of life: a visitor opens the site's root URL and sees "Hello World" on the page and in the tab title. The approved design is a single static page under `docs/` served by a dependency-free Python standard-library server that returns 200 for `/` and 404 for every other path, plus a stdlib smoke test that proves the HTTP contract. The pre-existing KAN-6 files (`README.md`, `hello_world.txt`) stay untouched.

**Verified starting state (2026-10-05):** `main` holds exactly `README.md` and `hello_world.txt`. There is no `AGENTS.md`, `CLAUDE.md`, `.factory/memory/`, CI config, manifest, or linter. `halo/feat/kan-8` does not exist yet. The implementation pod has Python 3.11.2.

## 2. Approach

One work item, one wave, one PR. Work proceeds bottom-up so each file can be checked as soon as it exists: page first (AC2–AC4 by construction), then the server that serves it (AC1, AC5, AC6), then the smoke test that imports the server (AC7), then local verification and the scope check (AC8). Nothing in the repo is reused — it is effectively empty — so the only conventions inherited are the `halo/feat/<ticket>` branch name from KAN-6 and the HLD's decision to use `docs/` as the served root. No dependency-graph constraints: `dependsOn` is empty.

Deliverables (exactly four new files):

| File | Purpose | Satisfies |
| --- | --- | --- |
| `docs/index.html` | The greeting page | AC2, AC3, AC4 |
| `docs/.nojekyll` | Empty marker; opts out of Jekyll if Pages is ever enabled | HLD §2 |
| `serve.py` | Root-only HTTP server, stdlib only; usage in header comment | AC1, AC2, AC5, AC6 |
| `smoke_test.py` | Starts the server on an ephemeral port and asserts the HTTP contract | AC7 |

Not added: `.gitignore`, `requirements.txt`, CI workflows, README changes.

## 3. Steps

### Step 1 (t1) — Branch

```
git clone https://github.com/ophirgal/test-repo-for-halo.git && cd test-repo-for-halo
git checkout -b halo/feat/kan-8 main
```

### Step 2 (t1) — Create `docs/index.html`

- `<!DOCTYPE html>`, `<html lang="en">`, `<meta charset="utf-8">`.
- `<meta name="viewport" content="width=device-width, initial-scale=1">` — the smoke test greps for `name="viewport"` and `width=device-width`.
- `<title>Hello World</title>`.
- Body is literally `<main><h1>Hello World</h1></main>` so "main content area" is unambiguous for the test.
- A short inline `<style>` only: `html,body{margin:0;padding:0}`, `body{font-family:system-ui,sans-serif}`, `main{padding:1rem}`, `h1{overflow-wrap:anywhere}`. No fixed widths, no external CSS/JS, no images. Keep the file under ~25 lines.

### Step 3 (t1) — Create `docs/.nojekyll`

- Empty file (`touch docs/.nojekyll`). Git tracks empty files; no content needed.

### Step 4 (t1) — Create `serve.py`

- Header comment / module docstring documenting usage (this is where run instructions live, not the README):
  - `python3 serve.py` → serves on `127.0.0.1:8000`
  - `python3 serve.py 9000` or `PORT=9000 python3 serve.py` → alternate port; the argument wins over the env var
  - `HOST=0.0.0.0 python3 serve.py` → bind all interfaces (opt-in; default is localhost)
  - `python3 smoke_test.py` → run the checks
- Imports limited to `http.server`, `os`, `sys`, `pathlib`, `urllib.parse`.
- `INDEX = Path(__file__).resolve().parent / "docs" / "index.html"` so the server works regardless of cwd.
- `class RootOnlyHandler(http.server.BaseHTTPRequestHandler)` — deliberately **not** `SimpleHTTPRequestHandler`, so there are no directory semantics, no listing, and no path-traversal surface.
  - `do_GET`: strip any query string with `urllib.parse.urlsplit(self.path).path`; if the result is exactly `"/"`, read `INDEX` bytes and send `200` with `Content-Type: text/html; charset=utf-8` and `Content-Length`; otherwise `self.send_error(404)`. Default `send_error` body is kept (spec leaves the 404 body unspecified).
  - `do_HEAD`: same routing, headers only. Trivial and keeps probes consistent.
  - Leave default stderr request logging in place; the smoke test may silence it via a subclass.
- `def make_server(host, port) -> http.server.ThreadingHTTPServer` so the smoke test can import it and bind port 0.
- `def main(argv)`: resolve port (`argv[1]` → `PORT` env → `8000`) and host (`HOST` env → `127.0.0.1`), print the URL, `serve_forever()`, exit cleanly on `KeyboardInterrupt`. Guard with `if __name__ == "__main__"`.
- No special-casing of `/index.html`: per the HLD's strict reading of FR4, `/index.html`, `/docs/index.html`, `/hello_world.txt`, `/README.md`, and `/foo/bar` are all 404.

### Step 5 (t1) — Create `smoke_test.py`

- Stdlib only: `threading`, `urllib.request`, `urllib.error`, `re`, `sys`; `from serve import make_server` (same directory, no packaging).
- Flow:
  1. `srv = make_server("127.0.0.1", 0)`; read the ephemeral port from `srv.server_address[1]`; run `srv.serve_forever` in a daemon thread.
  2. Helper `get(path) -> (status, headers, body_text)` that catches `HTTPError` and returns its code instead of raising.
  3. A tiny `check(cond, msg)` collector so every failure is reported in one run.
  4. Assertions:
     - `GET /` → 200; `Content-Type` starts with `text/html`; body matches `<title>[^<]*Hello World[^<]*</title>`; the `<main>…</main>` block's text contains "Hello World" (AC2, AC3).
     - Body contains `name="viewport"` and `width=device-width` (AC4, automated portion).
     - `GET /?x=1` → 200 (query string on root still counts as root; documented local decision).
     - Each of `/index.html`, `/docs/index.html`, `/hello_world.txt`, `/README.md`, `/foo/bar` → 404, and none of those bodies contains `Directory listing` (AC5).
     - After the 404 round, `GET /` → 200 with "Hello World" again (AC6).
  5. `srv.shutdown()`; on success print `OK: N checks passed` and exit 0; otherwise print each `FAIL: <check> — expected X, got Y` and exit 1.

### Step 6 (t1) — Local verification

```
python3 -m py_compile serve.py smoke_test.py        # syntax
python3 smoke_test.py                               # must print OK and exit 0
python3 serve.py 8765 &                             # manual probes
curl -si http://127.0.0.1:8765/               | head -1   # 200
curl -si http://127.0.0.1:8765/index.html     | head -1   # 404
curl -si http://127.0.0.1:8765/hello_world.txt | head -1  # 404
curl -si http://127.0.0.1:8765/               | head -1   # 200 again
kill %1
git diff main --stat                                # only the 4 new files
git diff main -- README.md hello_world.txt          # must be empty
```

- Also force one assertion to fail locally once (e.g. temporarily change the expected title) to confirm the smoke test exits non-zero with a readable message, then revert.
- Manual 375px check (AC4): open `http://127.0.0.1:8765/` in a browser, DevTools device mode at 375×667, confirm the heading is fully visible and `document.documentElement.scrollWidth <= 375`. Record browser, version, and result in the PR. If no browser is available on the pod, say so explicitly in the PR and ask the reviewer to perform it — do not claim it was done.

### Step 7 (t1) — Commit and open the PR

- One commit on `halo/feat/kan-8`:
  ```
  KAN-8: add Hello World page, root-only server and smoke test

  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  ```
- Push and open a PR against `main` titled `KAN-8: Hello World page with root-only server and smoke test`.
- PR description contains: the KAN-8 key; an AC1–AC8 checklist with evidence (smoke test output and `git diff main --stat` pasted); the manual 375px check result or the explicit statement that it could not be run; a note that enabling GitHub Pages (source `main` / `/docs`) is an optional post-merge human step and that under Pages `/index.html` would return 200, outside this story's verified scope; and the trailer `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Do not merge. Do not change repository settings (Pages, branch protection). The human approval gate applies.

## 4. Verification

Tests added: `smoke_test.py` (Step 5) is the only automated test; it runs against a real server on an ephemeral port. There is no CI, so it runs locally in Step 6 and its output is pasted into the PR.

| AC | Where it is met | How it is verified |
| --- | --- | --- |
| 1 | `serve.py` header + `main()` | Read header; run with an argument and with `PORT`; confirm default bind is `127.0.0.1` |
| 2 | `RootOnlyHandler.do_GET` + `<main>` in `docs/index.html` | `smoke_test.py`; curl |
| 3 | `<title>Hello World</title>` | `smoke_test.py` |
| 4 | viewport meta, no fixed widths, wrapping text | meta tag via `smoke_test.py`; width via manual 375px check recorded in the PR |
| 5 | non-root → `send_error(404)`; `BaseHTTPRequestHandler` (no listing) | `smoke_test.py` on the five named paths; curl |
| 6 | stateless handler | `smoke_test.py` re-requests `/` after the 404s |
| 7 | `smoke_test.py` | exit code 0 on pass; forced failure once to confirm non-zero + message |
| 8 | only four files added | `git diff main --stat`; `git diff main -- README.md hello_world.txt` empty |

Final acceptance against the story's four scenarios: Scenario 1 and 2 → smoke test + curl; Scenario 3 → manual 375px check; Scenario 4 → smoke test's 404 round followed by the repeat `GET /`.

## 5. Risks & open points

- **Browser availability on the pod is unknown.** AC4's width check cannot be automated without adding a browser-automation dependency, which the HLD rejects. If no browser exists, the PR must say so and hand the check to the reviewer.
- **Strict FR4 vs. a future Pages deployment.** `serve.py` returns 404 for `/index.html`; GitHub Pages would return 200 for it. This is a known, documented divergence outside the story's verified scope, noted in the PR for whoever enables Pages.
- **Local decisions the reviewer may want to confirm:** query string on root counts as root (200); `//` and other non-exact variants are 404 (no normalisation); `ThreadingHTTPServer` is used so the test can `shutdown()` cleanly; the default `send_error` 404 body and `Server:` header are kept as-is.
- **Port collision** during manual probes: pick another port; the smoke test binds port 0 and is unaffected.
- **Scope creep** in an empty repo (`.gitignore`, README edits, CI): the AC8 diff check in Step 6 catches it; nothing beyond the four files is added.
- **Out of scope, do not do:** edit `README.md` or `hello_world.txt`; enable Pages or any repo setting; add dependencies, manifests, CI, linters, Dockerfiles, or browser tests; serve any file other than `docs/index.html` on `/`.
