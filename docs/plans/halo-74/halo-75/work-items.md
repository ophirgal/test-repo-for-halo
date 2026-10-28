# Work-item breakdown — הוספת קובץ שלום בעברית לשורש המאגר

| # | Ref | Title | Tier | Depends on |
|---|---|---|---|---|
| 1 | t1 | Add shalom.txt with Hebrew content to repository root | T1 |  |

The fenced JSON below is the machine-readable breakdown the platform materializes on approval. Edits must keep it valid JSON with the same schema.

```json
[
  {
    "ref": "t1",
    "repoId": "c18b43ad-ca4d-44e9-a202-fdeeb989d4b2",
    "title": "Add shalom.txt with Hebrew content to repository root",
    "summary": "**Intent:** Create the file `shalom.txt` at the repository root containing the Hebrew word \"שלום\" in UTF-8, satisfying FR1–FR5 of the approved spec. This is the sole deliverable of the story.\n\n**Owns / Consumes:**\n- **Owns (creates):** `shalom.txt` at repo root\n- **Consumes (reads, not modified):** `hello_world.txt` (precedent for encoding and newline convention)\n\n**Acceptance criteria:**\n- A file named `shalom.txt` exists at the repository root (same directory as `hello_world.txt`).\n- The file content is exactly the 8-byte UTF-8 sequence `D7 A9 D7 9C D7 95 D7 9D` — the Hebrew word \"שלום\" — with no byte-order mark and no trailing newline.\n- `cat shalom.txt` in a standard UTF-8 terminal renders readable Hebrew, not garbled characters or encoding artifacts.\n- `file --mime-encoding shalom.txt` reports `utf-8` (or equivalent).\n- `python3 smoke_test.py` exits 0 with all existing checks passing — the new file does not break any test.\n- The pull request body references story HALO-75 and the epic PRD (\"אפיק בדיקה בעברית — מסמך אפיון\").",
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
        "scope_clarity": "Fully defined: one file, exact content specified down to the byte, exact location, exact encoding.",
        "technical_design_decisions": "None: follow the existing hello_world.txt pattern — same location, same no-trailing-newline convention, UTF-8.",
        "system_impact": "Single inert file in one repository; no code, no services, no integration points affected.",
        "async_distributed_complexity": "None: no async or distributed behavior involved in adding a static text file.",
        "validation_complexity": "Straightforward: verify file exists, check byte content with xxd, run existing smoke_test.py — all local, all deterministic.",
        "risk_unknowns": "Low and predictable: the only risk (encoding) is fully mitigated by verifying the byte sequence before commit."
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
