# Feature Specification Document — SCRUM-112 (draft, not ready)

## 1. Feature Overview

- **Summary:** add a new text file `qa/gap-hello.txt` to `ophirgal/test-repo-for-halo` whose content is `hello from gap`.
- **Problem statement:** the story title ("QA-20261122-GAP Start with a target-branch override") marks this as a QA run of the factory's story flow when a target branch is chosen at start. The deliverable itself is the file. The target branch is `main`, fixed when the story started.
- **Target users / actors:** the QA / factory team checking that a story started with a target-branch override delivers its change on the chosen branch. *(Assumption, to confirm: see Open Questions.)*
- **Repository today (verified):** the repo has no `qa/` directory on `main` or on any branch (`git log --all -- 'qa/*'` returns nothing). It has no `.factory/` folder, no `CLAUDE.md`/`AGENTS.md` and no CI workflow, so no repository gate applies beyond review.

## 2. Goals & Non-Goals

### Goals
- `qa/gap-hello.txt` exists on the work branch (and on `main` once a person merges the PR) with the text `hello from gap`.

### Non-Goals (proposed, to be confirmed: Q1)
- No change to any existing file (`README.md`, `hello_world.sh`, `hello_world.txt`, `serve.py`, `smoke_test.py`, `test_hello_world.sh`, `docs/`, `stories/` beyond this story's plan folder).
- No new test, script or documentation for the file.

## 3. Functional Requirements

- **FR1** — A new file at the repo-relative path `qa/gap-hello.txt` (creating the `qa/` directory).
- **FR2** — Its content is the text `hello from gap`: lowercase, no surrounding quotes. Exact bytes (single line; trailing newline or none) are open: Q1.
- **FR3** — Proposed: no other file in the repository changes (Q1).

## 4. User Experience & Behavior

- The person reviewing the PR sees exactly one added file, `qa/gap-hello.txt`, and on opening it reads `hello from gap`.
- No UI, look-and-feel, or runtime behavior is involved.

## 5. Acceptance Criteria

1. qa/gap-hello.txt exists with the text 'hello from gap'.
2. *(Proposed, pending Q1 — scope boundary)* No file other than `qa/gap-hello.txt` is added, changed or removed by the pull request.

## 6. Dependencies & Constraints (product-level)

- Target branch: `main` of `ophirgal/test-repo-for-halo` (fixed at story start).
- No sibling-story dependency found; no repository gates (`.factory/`, CI) exist to satisfy.
- A person merges the PR; the factory does not.

## 7. Technical Design (deferred to STRUCTURE)

Nothing to design beyond creating one file; deferred to STRUCTURE.

## 8. Open Questions

- **Q1 (P0)** — Scope boundary and exact content: is this PR limited to adding `qa/gap-hello.txt` only (no README or test changes), and should the file hold exactly `hello from gap` with no trailing newline? *Recommendation:* yes to both: the story asks for nothing else, and the repo's only similar file, `hello_world.txt`, has no trailing newline. Say so if you want one. *Working assumption until answered:* as recommended.
