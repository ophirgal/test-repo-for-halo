# Work-item breakdown — שאלון קונסולה — בחירת נושא ושאלה מוכנה מראש

| # | Ref | Title | Tier | Depends on |
|---|---|---|---|---|
| 1 | t1 | HALO-77: Console quiz script and pyproject.toml | T1 |  |

The fenced JSON below is the machine-readable breakdown the platform materializes on approval. Edits must keep it valid JSON with the same schema.

```json
[
  {
    "ref": "t1",
    "repoId": "c18b43ad-ca4d-44e9-a202-fdeeb989d4b2",
    "title": "HALO-77: Console quiz script and pyproject.toml",
    "summary": "**Intent:** Deliver the complete console quiz application — a Python script that displays a three-topic menu in Hebrew, accepts user selection, handles invalid input with a retry loop, and prints one hardcoded question for the chosen topic. Also delivers the `pyproject.toml` mandated by Engineering R1.\n\n**Owns:** `quiz.py` (new), `pyproject.toml` (new).\n**Consumes:** nothing — fully independent of all existing repo files.\n\n**Acceptance criteria:**\n1. Running `python quiz.py` in a terminal displays a menu with exactly three topics: ספורט, פוליטיקה, פסיכולוגיה — no more, no fewer.\n2. Selecting a valid topic displays exactly one pre-built Hebrew question corresponding to that topic, then the script exits.\n3. Each of the three topics produces a different, topically appropriate question (three distinct questions total, hardcoded in source).\n4. Entering a value that does not match any menu option displays a Hebrew error message and lets the user select again without restarting the script.\n5. Empty input (pressing Enter with no text) is treated as invalid input per criterion 4.\n6. Repeated invalid inputs never lock the user out — the retry loop continues indefinitely.\n7. The script uses only Python builtins/standard library — no external packages, no GUI, no web interface.\n8. A `pyproject.toml` exists at the repo root declaring `requires-python >= \"3.10\"`.\n9. All user-facing text (menu, questions, error messages) is in Hebrew.\n10. The PR references story HALO-77 and epic HALO-76 for traceability.",
    "dependsOn": [],
    "requirementRefs": [],
    "complexity": {
      "scores": {
        "scope_clarity": 0,
        "technical_design_decisions": 0,
        "system_impact": 0,
        "async_distributed_complexity": 0,
        "validation_complexity": 0,
        "risk_unknowns": 0
      },
      "justifications": {
        "scope_clarity": "Fully defined by the spec — menu topics, question count, input handling, output format, and language are all specified.",
        "technical_design_decisions": "No design decisions: a dict lookup inside a while-input loop. The spec leaves only trivial choices (numeric selection, question text).",
        "system_impact": "Single standalone script, no interaction with any existing component.",
        "async_distributed_complexity": "None — synchronous stdin/stdout only.",
        "validation_complexity": "Manual verification only (automated tests explicitly out of scope). Run script, try each topic, try invalid input.",
        "risk_unknowns": "Zero risk — trivial script with fully known requirements and no dependencies."
      },
      "total_score": 0,
      "tier": "T1",
      "engineer_level": "junior",
      "reasoning_effort": "Very Low",
      "token_budget": "Small",
      "human_decision_required": false
    }
  }
]
```
