# Feature Specification Document — QA-20261122-S4: a script that prints the project's QA_S4_MARKER value

## 1. Feature Overview

- **What is being built:** one small shell script, `qa/s4_marker.sh`, in the target repository `ophirgal/test-repo-for-halo`. It prints the value of the environment variable `QA_S4_MARKER`.
- **Problem:** a developer can't easily see which environment a pod is running with. The `QA_S4_MARKER` value identifies that environment, and the script shows it on demand.
- **Target user:** a developer who runs the script from a shell inside the pod (or anywhere the repository is checked out).

## 2. Goals & Non-Goals

### Goals
- Running `qa/s4_marker.sh` prints the exact value of `QA_S4_MARKER` on stdout, followed by a single newline.
- When `QA_S4_MARKER` is unset, the script prints `QA_S4_MARKER is not set` on stderr and exits with status 1.
- The change is limited to files whose paths match `qa/s4_*`.

### Non-Goals
- Changes to any file outside `qa/s4_*`. This includes `README.md`, the existing `hello_world.sh` and `test_hello_world.sh`, `serve.py`, `smoke_test.py` and `docs/`.
- Setting, defaulting, validating or interpreting `QA_S4_MARKER`. The script only reports the value it finds.
- Printing any other environment variable, or any formatting such as a label, prefix or quotes around the value.

## 3. Functional Requirements

- **FR1 — Location and invocation.** The script is the file `qa/s4_marker.sh` and has the executable bit set, so `./qa/s4_marker.sh` runs it directly.
- **FR2 — Variable set.** When `QA_S4_MARKER` is set, stdout holds exactly the variable's value followed by one newline (`\n`) and nothing else, and the script exits 0. "Exactly" means the value is not trimmed, interpreted, escape-expanded or decorated. For example, a value of `-n` or `a\tb` is printed literally.
- **FR3 — Variable unset.** When `QA_S4_MARKER` is unset, stderr holds the message `QA_S4_MARKER is not set` (followed by a newline), nothing is written to stdout, and the exit status is 1.
- **FR4 — Set but empty (literal reading of the ticket).** A variable that is set to the empty string counts as *set*, not unset, so FR2 applies: stdout holds just a newline and the exit status is 0. The ticket's error case says "unset", and this spec follows that wording. See §8.
- **FR5 — Arguments.** The ticket says nothing about arguments, so the script defines no argument behavior. Arguments do not change FR2 to FR4.
- **FR6 — Scope.** The change adds or changes only files under `qa/s4_*`. Any automated test that goes with the script must also live under `qa/s4_*`.

## 4. User Experience & Behavior

Main flow:

```bash
$ QA_S4_MARKER=staging-eu ./qa/s4_marker.sh
staging-eu
$ echo $?
0
```

Error flow:

```bash
$ unset QA_S4_MARKER; ./qa/s4_marker.sh
QA_S4_MARKER is not set        # on stderr
$ echo $?
1
```

- **Output format:** only the raw value on stdout, so a caller can capture it with `$(./qa/s4_marker.sh)`. There is no label, prompt or colour.
- **Error message:** exactly `QA_S4_MARKER is not set`, written to stderr.

## 5. Acceptance Criteria

1. qa/s4_marker.sh exists, is executable, and prints exactly the value of QA_S4_MARKER followed by a newline.
2. When QA_S4_MARKER is unset, the script prints 'QA_S4_MARKER is not set' to stderr and exits 1.
3. No file outside qa/s4_* is changed.

## 6. Dependencies & Constraints (product-level)

- **Repository rules checked:** at commit `51b3688`, the target repository has no `CLAUDE.md`, no `AGENTS.md`, no `.factory/` directory (so no gate skills and no `testing.md`) and no CI workflow (no `.github/`). Nothing in the repository's own rules conflicts with this story.
- **Existing conventions (for reference only):** the repository already has a script with its own test (`hello_world.sh` and `test_hello_world.sh` at the root, documented in `README.md`). This story must not follow that layout: under AC3, neither the README nor any root file is touched, and any test lives under `qa/s4_*`.
- **The `qa/` directory does not exist yet.** This story creates it.

## 7. Technical Design (deferred to STRUCTURE)

These are left to the STRUCTURE stage:

- the interpreter and shebang (POSIX `sh` or Bash);
- how the script tells an unset variable from an empty one;
- how the value is printed verbatim (for example `printf '%s\n'` rather than `echo`);
- whether to add an automated test under `qa/s4_*` and what form it takes.

## 8. Open Questions (if any remain)

- **Set-but-empty `QA_S4_MARKER` (P2, assumption recorded).** This spec follows the ticket literally: only an *unset* variable is an error, so an empty value prints a blank line and exits 0 (FR4). If an empty value should be treated like unset (error message, exit 1), the developer needs to say so before implementation. I recommend keeping the literal reading: it matches the ticket's wording ("unset"), and it lets someone running the script tell "deployed with an empty marker" apart from "deployed without one".
