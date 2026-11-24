# Work-item breakdown — Add a /healthz endpoint to serve.py

| # | Ref | Title | Depends on |
|---|---|---|---|
| 1 | t1 | Add GET/HEAD /healthz to serve.py with unittest and README docs |  |

The fenced JSON below is the machine-readable breakdown the platform materializes on approval. Edits must keep it valid JSON with the same schema.

```json
[
  {
    "ref": "t1",
    "repoId": "2fa71342-de3d-4a4c-8e90-81ac772c4f3a",
    "title": "Add GET/HEAD /healthz to serve.py with unittest and README docs",
    "summary": "**Intent:** Add a fixed, store-independent health route to the existing stdlib server so a probe can tell the server is up, with a unittest and README documentation. One small vertical slice in this repo; the whole story.\n\n**Owns:** `serve.py` (a new health branch in `RootOnlyHandler.do_GET` / `do_HEAD`, and the module docstring's route list), new `tests/test_healthz.py`, `README.md` (new `/healthz` section).\n**Consumes (read-only, must keep passing unchanged):** `tests/test_http.py`, `smoke_test.py`, `kvstore/`, `docs/`.\n\n**Acceptance criteria:**\n- `GET /healthz` answers `200`, header `Content-Type: application/json`, a `Content-Length` matching the body, and a body that parses as JSON to exactly `{\"status\": \"ok\"}` (one key `status`, string value `\"ok\"`, ASCII).\n- `HEAD /healthz` answers `200` with the same `Content-Type` and `Content-Length` as GET and no body.\n- A query string is ignored: `GET`/`HEAD /healthz?x=1` answer exactly as `/healthz`.\n- Look-alikes keep the existing stock `404` (`text/html`): `/healthz/`, `/healthz.json`, `/HEALTHZ`, `/health`, `/healthzx`, for GET and HEAD.\n- `PUT`, `DELETE` and `POST` on `/healthz` keep the stock `501` answer, identical (status and body) to what a stock `BaseHTTPRequestHandler` answers.\n- `/healthz` answers `200` regardless of store state: with `KV_PATH` pointing at a log corrupt in the middle (where `/kv/` answers `503`) and at an unopenable path (where `/kv/` answers `500`); and a `/healthz` request never creates the store file.\n- No existing answer changes: `ROUTES` still equals exactly `{\"/\": INDEX, \"/jungle\": JUNGLE}`; `/`, `/jungle`, `/kv/...`, every existing 404 and 501 answer as before; `tests/test_http.py` and `python3 smoke_test.py` pass unmodified.\n- The `serve.py` module docstring lists `/healthz` and what it answers, still contains `/kv/`, `KV_PATH`, `./kv.log`, `python3 serve.py`, `PORT=`, `HOST=`, and does not contain \"root-only\" or \"exactly one document\" (case-insensitive).\n- `tests/test_healthz.py` is discovered by `python -m unittest discover -s tests`, starts the server on a free port (port 0) in-process, covers every criterion above for the new route, cleans up its server and temp files, and passes; standard library only, no new dependency.\n- `README.md` gains a `/healthz` section with a curl example (e.g. `curl -i http://127.0.0.1:8000/healthz`) stating it answers `200` with `{\"status\": \"ok\"}` as `application/json`, that `HEAD` works too, that it does not reflect the key-value store's state, and that it has no authentication; existing README content is kept.\n- No third-party dependency, no other new route, no change to `pyproject.toml`.",
    "dependsOn": [],
    "requirementRefs": []
  }
]
```
