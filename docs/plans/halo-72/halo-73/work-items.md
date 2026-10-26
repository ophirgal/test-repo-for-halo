# Work-item breakdown — הוספת קובץ טקסט עם המילה "שלום" לשורש המאגר

| # | Ref | Title | Tier | Depends on |
|---|---|---|---|---|
| 1 | t1 | Add shalom.txt with Hebrew content to repo root | T1 |  |

The fenced JSON below is the machine-readable breakdown the platform materializes on approval. Edits must keep it valid JSON with the same schema.

```json
[
  {
    "ref": "t1",
    "repoId": "c18b43ad-ca4d-44e9-a202-fdeeb989d4b2",
    "title": "Add shalom.txt with Hebrew content to repo root",
    "summary": "**Intent:** Create the file `shalom.txt` at the repository root containing exactly the Hebrew word \"שלום\" (UTF-8, no BOM, no trailing newline) and deliver it via a pull request referencing HALO-73 and HALO-72.\n\n**Owns:** `shalom.txt` (new file at repo root)\n**Consumes:** nothing\n\n**Acceptance criteria:**\n1. A file named `shalom.txt` exists at the repository root after the PR merges.\n2. The file content is exactly the four Hebrew characters שלום — UTF-8 encoded, 8 bytes total (`D7 A9 D7 9C D7 95 D7 9D`), with no byte-order mark, no trailing newline, and no other characters or whitespace.\n3. No existing file in the repository is modified, deleted, or removed by the PR.\n4. No file other than `shalom.txt` is added by the PR.\n5. The PR description references story HALO-73 and epic HALO-72.",
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
        "scope_clarity": "Fully defined: exact file name, path, content, encoding, and byte count are specified.",
        "technical_design_decisions": "No design decisions — write a known string to a known file.",
        "system_impact": "Single file addition to one repository, no other components affected.",
        "async_distributed_complexity": "No async or distributed behavior.",
        "validation_complexity": "Verification is a byte-level comparison of one 8-byte file.",
        "risk_unknowns": "All preconditions confirmed (file does not exist, no conflicting config). No unknowns."
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
