# Work-item breakdown — Last-login line on the user profile page

| # | Ref | Title | Tier | Depends on |
|---|---|---|---|---|
| 1 | t1 | Add sign-in recording and /profile page with last-login display | T1 |  |

The fenced JSON below is the machine-readable breakdown the platform materializes on approval. Edits must keep it valid JSON with the same schema.

```json
[
  {
    "ref": "t1",
    "repoId": "1b17d991-ce92-4f6c-90b7-f76a25eb97b1",
    "title": "Add sign-in recording and /profile page with last-login display",
    "summary": "**Intent:** Deliver the complete last-login feature — sign-in recording on `GET /` and a new `GET /profile` HTML page — as a single vertical slice in the existing HTTP server.\n\n**Owns:** `serve.py` (modify — add recording logic, `/profile` route, profile HTML rendering, `json`/`datetime` imports, `SIGNINS` path constant), `smoke_test.py` (modify — add test checks for sign-in recording, profile page in all states, `signins.json` lifecycle management).\n\n**Consumes (read-only):** `docs/index.html` (served by `GET /`, unchanged).\n\n**Acceptance criteria:**\n1. `GET /` returns 200 with the same Hello World HTML as before the feature, AND appends a UTC ISO 8601 timestamp to `signins.json` (created if absent).\n2. `GET /profile` returns 200 with an HTML page showing \"Demo User\" and a \"Last login\" line directly under the name.\n3. When `signins.json` has two or more timestamps, `GET /profile` shows `Last login: <second-most-recent timestamp>` in ISO 8601 UTC format.\n4. When `signins.json` has zero or one timestamp (or does not exist, or is corrupted/unreadable), `GET /profile` shows `Last login: first sign-in`.\n5. All paths other than `/` and `/profile` return 404.\n6. All existing smoke tests pass without modification.\n7. New tests cover: returning-visitor display, first-sign-in display, no-signins display, sign-in recording appends to file, persistence (data survives handler re-reads), and `signins.json` is cleaned up after tests.\n8. `signins.json` data persists across server restarts (file-based, not in-memory).",
    "dependsOn": [],
    "requirementRefs": [],
    "complexity": {
      "scores": {
        "scope_clarity": 0,
        "technical_design_decisions": 0,
        "system_impact": 0,
        "async_distributed_complexity": 0,
        "validation_complexity": 1,
        "risk_unknowns": 0
      },
      "justifications": {
        "scope_clarity": "Fully defined — every behavior, edge case, and output format is specified in the feature spec and acceptance criteria.",
        "technical_design_decisions": "No real design decisions — follow the existing handler pattern, add a route and a file read/write using stdlib.",
        "system_impact": "Single component — only serve.py and its companion test file are touched.",
        "async_distributed_complexity": "None — synchronous HTTP handler with synchronous file I/O.",
        "validation_complexity": "Integration testing required — tests must start the HTTP server, make sequential requests, and verify file state between requests.",
        "risk_unknowns": "Low and predictable — stdlib-only changes to a small, well-understood server with no external dependencies."
      },
      "total_score": 1,
      "tier": "T1",
      "engineer_level": "junior",
      "reasoning_effort": "Low",
      "token_budget": "Small",
      "human_decision_required": false
    }
  }
]
```
