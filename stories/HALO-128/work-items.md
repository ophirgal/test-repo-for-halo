# Work-item breakdown — מפתח מריץ סקריפט Bash ומקבל ברכת Hello World במסוף

| # | Ref | Title | Depends on |
|---|---|---|---|
| 1 | t1 | Add hello_world.sh Bash greeting script with automated Bash test |  |

The fenced JSON below is the machine-readable breakdown the platform materializes on approval. Edits must keep it valid JSON with the same schema.

```json
[
  {
    "ref": "t1",
    "repoId": "c18b43ad-ca4d-44e9-a202-fdeeb989d4b2",
    "title": "Add hello_world.sh Bash greeting script with automated Bash test",
    "summary": "**Intent:** add a Bash script that prints exactly `Hello, World!` and exits 0, plus a dependency-free Bash test that proves it. This delivers story HALO-128 (PRD \"Hello World script\" / סקריפט Hello World) end to end in this repository.\n\n**Owns:**\n- `hello_world.sh` (new, repo root, committed executable, `#!/usr/bin/env bash`)\n- `test_hello_world.sh` (new, repo root)\n- a short usage section in `README.md`\n\n**Consumes (unchanged, must not be edited):** `serve.py`, `smoke_test.py`, `docs/*`, `hello_world.txt`.\n\n**Acceptance criteria:**\n1. `bash hello_world.sh`, run from the repo root, writes to stdout exactly `Hello, World!` followed by one newline (14 bytes), writes nothing to stderr, and exits 0.\n2. `bash hello_world.sh foo bar` produces the identical stdout, an empty stderr and exit code 0. Arguments are ignored.\n3. Running the script with an empty environment and no startup files (`env -i /bin/bash --noprofile --norc hello_world.sh`) prints `Hello, World!` and exits 0. Nothing beyond Bash is needed, and no package, tool or dependency is added to the repo.\n4. `hello_world.sh` is committed with the executable bit, so `./hello_world.sh` produces the same result as `bash hello_world.sh`.\n5. `bash test_hello_world.sh` runs the script and checks:\n   - exact stdout bytes, including the single trailing newline;\n   - empty stderr;\n   - exit code 0;\n   - the `foo bar` arguments case;\n   - the empty-environment, no-profile case.\n6. The test exits 0 with a pass summary when all checks pass, and exits non-zero naming the failing check when any check fails.\n7. The script and the test use only Bash features that work in Bash 3.2 (the macOS `/bin/bash`) and need no test framework (no bats, shunit2 or shellcheck).\n8. `README.md` documents how to run the script (`bash hello_world.sh`) and its test (`bash test_hello_world.sh`).\n9. `python3 smoke_test.py` still prints `OK: 87 checks passed` and exits 0. The web page greeting, `serve.py`, `docs/` and `hello_world.txt` are unchanged.\n10. The pull request description names HALO-128 and the PRD \"Hello World script\" (סקריפט Hello World). It includes the recorded output of `bash test_hello_world.sh` and of `python3 smoke_test.py`, because the repo has no CI.\n11. The code, tests and commits contain no secrets or personal data.",
    "dependsOn": [],
    "requirementRefs": []
  }
]
```
