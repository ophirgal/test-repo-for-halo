# HALO-128 — High-Level Design: Hello World Bash script

## 1. System Overview
- **What is being built:** one Bash script that prints `Hello, World!` on one line to standard output and exits 0. It comes with one automated Bash test that runs the script and checks its behaviour.
- **Problem:** today the greeting exists only as a web page (`serve.py` with `docs/`) or as a text file (`hello_world.txt`). Nothing runs it from the terminal, so there is no quick, dependency-free check that the environment runs scripts.
- **Responsibilities:**
  - The script prints the greeting and exits successfully.
  - The test proves the output, the exit code, the arguments case and that only Bash is needed.
  - The PR records the test results, because the repo has no CI.

## 2. Architecture Overview
- **Components:** two new files at the repo root, following the existing flat layout (`serve.py`, `smoke_test.py`, `hello_world.txt`):
  - `hello_world.sh` is the deliverable.
  - `test_hello_world.sh` is its automated test.
  - `README.md` gets a short usage note.
- **Boundaries:** the new files are fully separate from the web stack. `serve.py` serves only the two paths in its `ROUTES` table and never builds a file path from the request. A new file in the repo therefore can't be served, and `smoke_test.py`'s 404 checks for other paths still hold.
- **Ownership:** a single work item (t1) owns the new files and the README note.
- **External dependencies:** none beyond Bash itself and standard utilities. No bats, shunit2 or shellcheck (Engineering requirements R2).

## 3. Data Flow Design
- **Script:** the developer runs `bash hello_world.sh` (or `./hello_world.sh`). The script writes `Hello, World!` plus a newline to stdout and exits 0. It is synchronous, reads no input, opens no files, keeps no state and ignores arguments.
- **Test:** `bash test_hello_world.sh` runs the script in several ways and compares stdout, stderr and the exit code with the expected values. It prints a summary and exits 0 when every check passes and non-zero otherwise.
- There are no events and no asynchronous processing.

## 4. Component Breakdown
| Component | Responsibility | Inputs / Outputs | Repository |
| --- | --- | --- | --- |
| `hello_world.sh` | Print the greeting and exit 0 | In: none (arguments ignored). Out: stdout `Hello, World!\n`, empty stderr, exit 0 | ophirgal/test-repo-for-halo |
| `test_hello_world.sh` | Automated check of the script (AC1–AC3, FR5) | In: the script path. Out: a pass/fail summary, exit 0 on success and non-zero on any failure | ophirgal/test-repo-for-halo |
| `README.md` (usage note) | Document how to run the script and its test | — | ophirgal/test-repo-for-halo |
| Existing `serve.py`, `docs/`, `hello_world.txt`, `smoke_test.py` | Unchanged; regression check only (AC5) | `python3 smoke_test.py` prints `OK: 87 checks passed` and exits 0 | ophirgal/test-repo-for-halo |

## 5. Interface Contracts
- **CLI contract (`hello_world.sh`):**
  - It is run with `bash hello_world.sh [any args]`, or as `./hello_world.sh` when the executable bit is present.
  - stdout is exactly the 14 bytes `Hello, World!` followed by a newline.
  - stderr is empty.
  - The exit code is 0, whatever arguments are passed.
- **Test contract (`test_hello_world.sh`):**
  - It is run with `bash test_hello_world.sh` from the repo root.
  - It exits 0 and prints a pass summary when every check passes.
  - It exits non-zero and names the failing check otherwise.
- There are no cross-repo contracts, APIs or events.

## 6. Key Technical Decisions
- **Location and name:** the script is `hello_world.sh` at the repo root, which matches the flat layout and the existing `hello_world.txt` naming. A new `scripts/` folder was considered and rejected as unnecessary for one file.
- **Invocation:**
  - `#!/usr/bin/env bash` shebang.
  - The executable bit is committed (mode 100755). This would be the repo's first executable file.
  - `bash hello_world.sh` is the documented form, because it works even on checkouts that lose the bit, for example where `core.fileMode=false`.
- **Printing:** the script prints with `printf` and a single-quoted literal. That avoids any history expansion of `!` and the differences between `echo` implementations.
- **Portability:** the script and the test use only features that also work in Bash 3.2, the version macOS ships as `/bin/bash`. That rules out `mapfile`, associative arrays and case-modification expansions.
- **Test form:**
  - The test is a Bash script with no dependency, rather than Python, so the story stays Bash-only (PRD §7, RK2).
  - It is kept separate from `smoke_test.py`, so the web smoke test stays focused and its `87 checks` count doesn't change.
  - It captures stdout and stderr separately, without command substitution stripping the newline, so it checks the exact bytes, including the single trailing newline.
- **AC3 check ("Bash only"):** the test runs the script with `env -i <bash> --noprofile --norc`, which means an empty environment and no profile. This proves the script depends on nothing the user or the epic installed.
- **Stderr:** the test asserts stderr is empty, which is the spec's default reading of "exactly one line".

## 7. Risks & Constraints
- **No CI (RK1):** the PR must include the output of `bash test_hello_world.sh` and of `python3 smoke_test.py`.
- **Executable bit:** it may be lost on some checkouts. The test and the docs use `bash <script>`, so behaviour doesn't depend on the bit.
- **Bash 3.2 compatibility:** the implementer must avoid features newer than 3.2. Where possible, the test should be run once with `/bin/bash` on macOS.
- **Wording difference:** the script prints `Hello, World!` while `hello_world.txt` says `Hello World`. This is deliberate (PRD §7), and the text file is out of scope.
- **Language objection (RK2):** a reviewer may ask for Python. Bash is the PO's explicit decision, recorded in PRD §7.
- **Scale and performance:** not applicable. The script runs instantly and has no security surface (no input, no secrets, R4).

## Resolved open questions
- **Script name and location:** `hello_world.sh` at the repo root.
- **How it's run:** `bash hello_world.sh` is documented, and the executable bit is also committed.
- **Test form and file:** a standalone Bash test, `test_hello_world.sh`, separate from `smoke_test.py`.
- **Checking AC3:** an empty-environment, no-profile Bash run inside the test.
- **Stderr:** asserted empty.

## Build order
1. **t1:** the script, its test and the README note (the only work item).
