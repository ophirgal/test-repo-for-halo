# Implementation Plan — BENCH-8: Add hello.py smoke-test script and README run instructions

## Context

Developers who clone the repository have no trivial way to verify their Python toolchain works. This change adds a one-line `hello.py` script at the repository root that prints `Hello, world!` and exits 0, plus a short section appended to the existing `README.md` explaining how to run it. The two files together give new contributors an instant setup-verification step.

## Approach

This is a single work item (t1) with no dependencies, no design decisions, and no interaction with existing code. The implementation is one atomic step: create `hello.py`, then append to `README.md`. Before writing, verify `hello.py` does not already exist (Scenario 5) and check whether `README.md` exists (Scenario 3 vs. 4). Research indicates `hello.py` is absent and `README.md` is present with a `# test-repo-for-halo` heading, but the implementation must confirm both at execution time.

## Steps

### Step 1 — Pre-flight checks (work item: t1)

- Confirm `hello.py` does **not** exist at the repository root. If it does, stop and report the conflict per Scenario 5.
- Confirm whether `README.md` exists at the repository root to choose the append path (Scenario 3) or the create path (Scenario 4).

### Step 2 — Create `hello.py` (work item: t1)

- **File:** `/hello.py` (new)
- **Content — the entire file:**

```python
print("Hello, world!")
```

- One line. No shebang, no imports, no license header, no comments. `print()` appends a newline and the process exits 0 implicitly.

### Step 3 — Append run instructions to `README.md` (work item: t1)

- **File:** `/README.md` (existing — preserve all current content)
- **If `README.md` exists (expected path, Scenario 3):** append the following block to the end of the file, preceded by a blank line to ensure Markdown separation from whatever precedes it:

```markdown

## Quick start

Verify your Python toolchain: `python3 hello.py`
```

- **If `README.md` does not exist (Scenario 4):** create a new file with only:

```markdown
## Quick start

Verify your Python toolchain: `python3 hello.py`
```

- The heading gives the line discoverability; the inline code names the exact command per FR4. The explicit mention of `hello.py` distinguishes it from the existing `hello_world.txt`.

### Step 4 — Commit and open PR (work item: t1)

- Stage only `hello.py` and `README.md`.
- Commit message: `Add hello.py smoke-test script and README run instructions`
- Open a single PR targeting `main`. Title: `Add hello.py smoke-test script and README run instructions`. Body traces to BENCH-8.
- Verify via `git diff --stat` that the PR touches exactly two files.

## Verification

| # | Check | Acceptance criterion |
|---|-------|---------------------|
| 1 | `python3 hello.py` prints exactly `Hello, world!` (with trailing newline) | Scenario 1 — FR2 |
| 2 | `python3 hello.py` exits with code 0 (`echo $?` → `0`) | Scenario 1 — FR3 |
| 3 | `README.md` contains the line `Verify your Python toolchain: \`python3 hello.py\`` | Scenario 2 — FR4 |
| 4 | All prior content of `README.md` (e.g. `# test-repo-for-halo`) is still present | Scenario 3 |
| 5 | `git diff --stat` shows exactly two files changed (`hello.py`, `README.md`) | Scope constraint |

No test framework or CI exists in this repo, so verification is manual command-line checks performed before opening the PR.

## Risks & open points

None. All requirements are fully specified, research has confirmed the preconditions (no `hello.py` conflict, `README.md` exists), and the repo has no linters or CI to satisfy. The only judgment call is where to place the appended content — end of file under a `## Quick start` heading — which is the least disruptive position and follows standard Markdown convention.
