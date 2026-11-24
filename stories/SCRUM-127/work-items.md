# Work-item breakdown — QA-20261124-N1 a helper that doubles a number

| # | Ref | Title | Depends on |
|---|---|---|---|
| 1 | t1 | Add testbed_utils.doubler.double(n) with pytest coverage |  |

The fenced JSON below is the machine-readable breakdown the platform materializes on approval. Edits must keep it valid JSON with the same schema.

```json
[
  {
    "ref": "t1",
    "repoId": "2fa71342-de3d-4a4c-8e90-81ac772c4f3a",
    "title": "Add testbed_utils.doubler.double(n) with pytest coverage",
    "summary": "**Intent:** Add a new `testbed_utils` package under `src/` whose `doubler` module provides `double(n)`, which returns `n * 2`, together with pytest tests for positive, zero and negative integers (spec FR1–FR4, AC1–AC3). The helper is part of this repository, so this repository owns it.\n\n**Owns (new files):** `src/testbed_utils/__init__.py`, `src/testbed_utils/doubler.py`, `tests/test_doubler.py`.\n**Consumes (read-only, unchanged):** `pyproject.toml` (its `packages.find where = [\"src\"]` and `testpaths = [\"tests\"]` already cover the new package and test). It follows the import pattern of `tests/test_ledger_parse.py`.\n\n**Acceptance criteria:**\n- After `pip install -e \".[test]\"`, `from testbed_utils.doubler import double` succeeds.\n- `double(n)` returns `n * 2` as an `int` for integer input: `double(3) == 6`, `double(0) == 0`, `double(-4) == -8`.\n- `tests/test_doubler.py` holds pytest tests that assert the result for at least one positive, one zero and one negative integer input.\n- `python -m pytest` (run after the install) collects the new tests and they pass. Every test that already existed still passes.\n- The function adds no type checks and raises no error of its own for non-integer input, and no test asserts non-integer behaviour (spec §2 non-goal).\n- No existing file is modified: `src/ledger/`, `kvstore/`, `linkcheck/`, `serve.py`, the existing tests, `pyproject.toml` and `README.md` stay unchanged. The change adds no runtime dependency, no `conftest.py` and no CI workflow.",
    "dependsOn": [],
    "requirementRefs": []
  }
]
```
