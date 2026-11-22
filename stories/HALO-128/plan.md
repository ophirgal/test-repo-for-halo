# HALO-128 — Implementation plan: Hello World Bash script

## Context

Story HALO-128 (epic HALO-127, PRD "Hello World script" / סקריפט Hello World) adds one Bash script that prints exactly `Hello, World!` on one line to stdout and exits 0, whatever arguments it gets and without needing anything beyond Bash. It also adds a dependency-free Bash test that proves this, and the PR records that test's result because the repo has no CI. The existing web page and its smoke test must keep passing unchanged. The change lands in `ophirgal/test-repo-for-halo` on the work branch `halo/feat/halo-128-20261109-175926` and merges into `main`. `spec.md` (requirement and AC1–AC5), `hld.md` (design) and `work-items.md` (single work item `t1`) sit beside this file in `stories/HALO-128/`.

## Research findings

**Repository layout (fact).** The repo root is flat, with `serve.py`, `smoke_test.py`, `hello_world.txt`, `README.md`, `docs/` and `stories/`. There is no `AGENTS.md`, `CLAUDE.md`, `.factory/`, `.github/`, package manifest, linter or formatter config.

**Change surface.** The change creates two files and edits one:
- `hello_world.sh` (new): does not exist today.
- `test_hello_world.sh` (new): does not exist today.
- `README.md` (edit): it is one line today (`# test-repo-for-halo`). The usage note is appended.

**Contracts touched.**
- CLI contract of `hello_world.sh` (from `hld.md` §5):
  - stdout is exactly `Hello, World!\n` (14 bytes);
  - stderr is empty;
  - the exit code is 0;
  - arguments are ignored.
- Test contract of `test_hello_world.sh`: it exits 0 with a pass summary, and exits non-zero naming the failing check.
- There are no APIs, schemas or cross-repo values.

**Web stack isolation (fact).**
- `serve.py:38` defines `ROUTES = {"/": INDEX, "/jungle": JUNGLE}`.
- `serve.py:51-53` resolves only exact paths through `ROUTES.get(...)` and never builds a file path from the request.
- New root files therefore cannot be served, and the 404 checks in `smoke_test.py:158-168` and `smoke_test.py:356-365` are unaffected.
- `smoke_test.py:130` asserts the `ROUTES` table is unchanged.

**Existing gate (fact).**
- No CI and no build or lint step exist.
- The only automated test is `python3 smoke_test.py`. It starts `serve.py` on an ephemeral port and prints `OK: <n> checks passed` with exit 0 (`smoke_test.py:382-400`).
- `spec.md` FR6 records the current count as `OK: 87 checks passed`.

**File modes (fact).** `git ls-files -s` shows every tracked file as `100644`, and `core.fileMode` is `true` in this checkout. `hello_world.sh` will be the repo's first `100755` file.

**Bash versions available (fact).**
- `/bin/bash` is `GNU bash, version 3.2.57` (the macOS system Bash).
- `bash` on `PATH` is 5.3.20.
- The test can therefore exercise both versions locally.

**External data.** The change depends on no external data.

**Unknowns.** None remain. The script's name, location, invocation, test form, how AC3 is checked and the stderr expectation are settled in `hld.md` ("Resolved open questions").

## Locked decisions and assumptions

**Locked decisions**

| # | Decision | Source |
| --- | --- | --- |
| 1 | The greeting text is exactly `Hello, World!`, with the comma and exclamation mark. | PRD §7; `spec.md` §4 |
| 2 | The script is written in Bash, not Python. | PO request; PRD §7 and RK2 |
| 3 | The script is `hello_world.sh` at the repo root, with a `#!/usr/bin/env bash` shebang. | `hld.md` §6 |
| 4 | The script is committed as executable (mode `100755`), and `bash hello_world.sh` is the documented way to run it. | `hld.md` §6; `t1` AC4 and AC8 |
| 5 | The script prints with `printf` and a single-quoted literal. It does not use `echo`. | `hld.md` §6 |
| 6 | The test is a standalone Bash script, `test_hello_world.sh`. It is separate from `smoke_test.py` and uses no framework (no bats, shunit2 or shellcheck). | `hld.md` §6; `t1` AC7; Engineering requirements R2 |
| 7 | AC3 is checked by running the script with an empty environment and no startup files: `env -i <bash> --noprofile --norc hello_world.sh`. | `hld.md` §6; `t1` AC3 |
| 8 | The test asserts that stderr is empty. | `hld.md` §6; `spec.md` §8 |
| 9 | The script and the test use only Bash 3.2 features. | `hld.md` §6; `t1` AC7 |
| 10 | `serve.py`, `smoke_test.py`, `docs/*` and `hello_world.txt` are not changed. | PRD §8; `t1` "Consumes" |
| 11 | The PR names HALO-128 and the PRD, and includes the recorded output of both tests. | Engineering requirements R7; PRD RK1; `t1` AC10 |

**Assumptions**

| # | Assumption | Evidence | Consequence if wrong |
| --- | --- | --- | --- |
| A1 | The test finds the script relative to its own location (`${BASH_SOURCE[0]}`'s directory), so it works from any working directory. | `hld.md` §5 documents only "from the repo root". | If wrong, a run from another directory fails falsely. The relative lookup is harmless either way. |
| A2 | The AC3 run uses `/bin/bash` when it exists and otherwise the Bash running the test (`$BASH`). | `t1` AC3 names `/bin/bash`, but some Linux hosts have Bash elsewhere. | If wrong, the check is either unportable or does not test the system Bash. |
| A3 | The test compares exact bytes by capturing stdout and stderr into temp files (`mktemp`) and comparing them with `cmp` against an expected file written by `printf`. It removes the temp files on `EXIT` with a `trap`. | Command substitution strips trailing newlines, so it cannot check the 14 bytes. `mktemp` and `cmp` are standard utilities, not added dependencies. | If wrong, a missing or doubled newline would go undetected. |
| A4 | The smoke-test baseline is still `OK: 87 checks passed` on `main`. | `spec.md` FR6; this stage did not run it. | If the count differs on `main`, AC5 means "same result as before the change". Record the before and after outputs. |

## Solution proposal

The approach adds two self-contained root-level files next to the existing flat layout, plus a README note, and touches nothing in the web stack.

**`hello_world.sh`**
- It has the shebang and a one-line header comment naming HALO-128.
- Its single statement is `printf '%s\n' 'Hello, World!'`, which writes the 14 bytes exactly.
- It does not use `echo`, because `echo` behaves differently between implementations, and `!` inside double quotes could trigger history expansion in interactive shells.
- It does not reference `$@`, so arguments are ignored by construction.
- It reads no input, opens no files and sources nothing, so it runs the same under `env -i ... --noprofile --norc`.
- Its exit status is that of `printf`, which is 0.
- It does not use `set -euo pipefail`. That buys nothing for one statement and is not needed by any AC.

**`test_hello_world.sh`**
- A small `check NAME CONDITION` style helper counts passes and records failures by name.
- Each case runs the script, captures stdout and stderr to temp files and records the exit code. It then checks:
  1. stdout bytes are equal to the expected `Hello, World!\n` file (`cmp -s`);
  2. stderr is empty (`[ ! -s file ]`);
  3. the exit code is `0`.
- It covers four cases:
  1. `bash hello_world.sh` (AC1);
  2. `bash hello_world.sh foo bar` (AC2);
  3. `env -i <bash> --noprofile --norc hello_world.sh` (AC3);
  4. `./hello_world.sh`, executed directly, which checks the committed executable bit (`t1` AC4).
- At the end it prints `OK: <n> checks passed` and exits 0. On any failure it prints each failing check's name and `<k> check(s) failed, <n> passed`, then exits 1. This mirrors the summary format of `smoke_test.py:393-400`.
- It uses only Bash 3.2 constructs: plain indexed arrays or string accumulation, `[ ]` and `[[ ]]`, and `$(( ))`. It avoids `mapfile`, associative arrays and `${var,,}`.

**`README.md`**
- Append a short "Hello World script" section.
- The section shows `bash hello_world.sh` and the expected output, and `bash test_hello_world.sh`.

**Alternatives rejected**
- A Python test in `smoke_test.py`. It would change the `87 checks` baseline and mix concerns, and `hld.md` §6 rejected it.
- A `scripts/` folder. It is unnecessary for one file (`hld.md` §6).
- bats or shunit2. Either would be a new dependency, which R2 forbids.
- `echo "Hello, World!"`. It has the portability and history-expansion problems described above.

## Ordered implementation steps

1. **Create the script.** Create `hello_world.sh` with the `#!/usr/bin/env bash` shebang, a header comment and the single `printf '%s\n' 'Hello, World!'` statement. Set mode `100755` with `chmod +x hello_world.sh`, so git records the executable bit.
   - Advances AC1, AC2 and AC3 (`t1` AC1–AC4, AC7).
   - Covered by the new Bash test from step 2. The repo has no other layer that fits a shell script.
2. **Create the test.** Create `test_hello_world.sh` with the check helper, temp-file capture with a `trap` cleanup, and the expected-bytes file. Add the four cases in this order: plain run, `foo bar`, `env -i` with no profile, `./` executed directly.
   - Locate the script through the test's own directory (A1).
   - Choose the AC3 Bash as `/bin/bash` when it is executable, otherwise `$BASH` (A2).
   - Error paths: a missing or non-executable script must fail the matching check with its name, never abort silently. Do not use `set -e` around the cases, so every check reports.
   - Advances AC4 and covers AC1–AC3 (`t1` AC5–AC7). This test is itself the layer.
3. **Check the test can fail.** Before finalizing, confirm locally that the test really fails: temporarily change the greeting or drop the newline in a scratch copy, and confirm the test exits non-zero and names the failing check. Do not commit this change.
   - Advances AC4 (`t1` AC6). Covered by `test_hello_world.sh`.
4. **Document usage.** Append the usage section to `README.md`.
   - Advances `t1` AC8. This is documentation and has no test layer.
5. **Run both tests and record the outputs.** Run `bash test_hello_world.sh`, then `/bin/bash test_hello_world.sh` to cover Bash 3.2, then `python3 smoke_test.py`. Keep their verbatim outputs for the PR.
   - Advances AC4 and AC5 (`t1` AC9–AC10). Covered by `test_hello_world.sh` and `smoke_test.py`.
6. **Write the PR description.** It names HALO-128 and the PRD "Hello World script" (סקריפט Hello World), and pastes both outputs from step 5. Check the diff for secrets and personal data. There should be none: the diff is a literal greeting.
   - Advances AC4 (`t1` AC10–AC11). This is a review check and has no test layer.

Implicit invariants:
- Authorization, tenancy and concurrency do not apply: there is no input, no state and no network.
- Idempotency is inherent: every run produces the same bytes.
- Dependencies: nothing is installed. `bash`, `env`, `mktemp`, `cmp`, `rm` and `python3` (used only by the existing smoke test) are already present.
- There are no generated deliverables and no binaries, so no `.factory/delivery-assets` entry is needed.

## Work-item mapping

| Step | Work item |
| --- | --- |
| 1 — create `hello_world.sh` (executable) | `t1` — Add hello_world.sh Bash greeting script with automated Bash test |
| 2 — create `test_hello_world.sh` | `t1` |
| 3 — check the test fails on a wrong greeting | `t1` |
| 4 — add the usage note to `README.md` | `t1` |
| 5 — run both tests and record outputs | `t1` |
| 6 — PR description: traceability and recorded outputs | `t1` |

`t1` is the only work item, and every step maps to it.

## Verification and CI gate

The repo has no CI, build, lint or formatter configuration, and no `.factory/testing.md` or `.factory/delivery-assets`.

**Canonical gate.** Run it once locally, from the repo root, on the committed SHA, in this order:
1. `bash test_hello_world.sh`, the new test. It must print `OK: <n> checks passed` with no failures and exit 0. It covers AC1, AC2, AC3, executed-directly (`t1` AC4) and AC4's "the test passes".
2. `/bin/bash test_hello_world.sh`, the Bash 3.2 run (`t1` AC7). It must show the same result. On a host without `/bin/bash` at 3.2, report this run as not possible, with the reason.
3. `python3 smoke_test.py`, the existing regression layer. It must print `OK: 87 checks passed` and exit 0 (AC5, `t1` AC9). If the baseline count on `main` differs, it must match that baseline (A4).

**Further checks the change must pass**
- `git ls-files -s hello_world.sh` shows mode `100755`.
- `git diff --stat main...HEAD` lists only `hello_world.sh`, `test_hello_world.sh`, `README.md` and the `stories/HALO-128/` folder.

**Where the layers run.** All layers run in a pod: they need only Bash, coreutils and Python 3, with no network beyond loopback. The Bash 3.2 run needs a macOS-style `/bin/bash`, or else it is reported as not covered.

**Provider CI.** Adding provider CI is out of scope (PRD §8). The PR description carries the recorded outputs instead (RK1).

## Risks and scope guards

**Risks**
- **Executable bit lost** on checkouts with `core.fileMode=false`.
  - Mitigation: the documented invocation is `bash hello_world.sh`.
  - The `./` case in the test detects a missing bit in this checkout.
- **Bash 3.2 incompatibility** slipping in through newer syntax.
  - Mitigation: step 5 runs the test explicitly under `/bin/bash` 3.2.57.
- **Newline-stripping false pass** if the test compares `$(...)` output.
  - Mitigation: compare bytes from files with `cmp`, as in A3.
- **Reviewer objection to Bash** (RK2).
  - Mitigation: cite PRD §7 in the PR.
- **Wording mismatch** with `hello_world.txt` (`Hello World.`) is intentional (PRD §7). Do not "fix" it.

**Scope guards (the implement phase must NOT)**
- Edit `serve.py`, `smoke_test.py`, `docs/*`, `hello_world.txt` or any other `stories/*` folder.
- Add CI workflows, a `Makefile`, `package.json`, `requirements.txt`, bats, shunit2, shellcheck or any other dependency or tool.
- Add argument handling, a name parameter, flags, colour or extra output lines to the script.
- Fold the Bash checks into `smoke_test.py`, or change its check count.
- Make a failing check pass by deleting, skipping or loosening it. That includes the stderr-empty assertion, the exact-byte comparison and the `env -i` case. A check that cannot run on a given host is reported as blocked, with the reason.

## Clarification outcomes

None.
