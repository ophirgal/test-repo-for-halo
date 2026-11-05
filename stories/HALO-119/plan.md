# Implementation plan — HALO-119: Minimal one-page Snake game

## Context

HALO-119 delivers one self-contained page, `snake.html`. It runs classic single-player Snake when opened from disk (`file://`) in a current desktop browser and is played with the keyboard: start, steer, eat, grow, die, restart. It makes no network request. If start-up fails, it shows a visible error. The story has one work item, **t1 — "Minimal one-page Snake game (snake.html)"**, and its 13 acceptance criteria (spec §5 ACs 1–13, restated as work-item criteria 1–13) are the scope. Per `work-items.md` and HLD §7, t1 is provisionally assigned to `McK-Private/harel-pdlc-infra` on branch `halo/feat/halo-119` (integration branch `develop`), boxed into a new folder `halo-119-snake/`. The spec's home is `ophirgal/test-repo-for-halo` at the repo root. `spec.md`, `hld.md` and `work-items.md` sit beside this file in `stories/HALO-119/` of the spec repository.

## Research findings

**Target repository (provisional): `harel-pdlc-infra`**
- The checkout is on `halo/feat/halo-119` at `cae4e30` ("merge: bring halo/feat/halo-119 up to date with develop"), and the tree is clean.
- No `halo-119-snake/` folder exists. Both deliverables are new.
- `AGENTS.md` requires a doc update only for the file areas in its table: `chart/`, `scripts/`, `e2e/`, `deploy/harel/`, `langfuse-dev/`, `.env.example`. A new top-level `halo-119-snake/` matches no row, so no `docs/` change is owed.
- `CLAUDE.md` sets three rules: fail fast and never swallow errors, a PR into `develop`, and running the `verify` skill before the PR (`.claude/skills/verify/SKILL.md`).
- The canonical gate for infra is `make e2e-unit` (`Makefile:301-302`). It runs `python3 -m unittest discover -s scripts/tests` after `chart-deps` and the e2e venv, and it needs `helm`. Where `helm` is missing, the `verify` skill allows `python3 -m unittest discover -s scripts/tests` and asks that the substitution be stated. `shellcheck` covers only shell scripts under `scripts` (`.github/workflows/ci.yml:58-63`). This change adds none.
- CI (`.github/workflows/ci.yml`) runs the `helm`, `scripts-unit`, `shellcheck` and `vdi-isolation` jobs. Discovery is rooted at `scripts/tests`, so `halo-119-snake/test_snake.py` is **not** collected by CI. It is run explicitly.
- `local-dev-consistency.yml` is path-filtered (lines 23-30) and won't trigger.
- One existing test scans the whole tree: `scripts/tests/test_retired_keys.py:141-171` runs `git ls-files -co` and greps every file for the retired `HALO_*` env keys. The new files must not contain those names. They have no reason to.
- `.gitattributes` affects only `*.sh`. There is no `.factory/testing.md` and no `.factory/delivery-assets`. `.factory/` holds only `local-dev.json` and `runbook.md`, and there is no `.factory/memory/`.

**Spec home: `ophirgal/test-repo-for-halo` (read-only here)**
- It holds `README.md`, `hello_world.txt`, `docs/index.html`, `docs/.nojekyll`, `serve.py` and `smoke_test.py`.
- `serve.py:32` serves only `docs/index.html` at `/`.
- `smoke_test.py:22-28` checks a fixed path list, so a new root file can't break it.
- `smoke_test.py` is stdlib-only, script-style Python (the KAN-8 precedent for "no Node/Playwright").

**Contracts**
- There is no API, schema or cross-repo value. The only contract is the exact on-screen strings (HLD §5): `Score: N`, `Press an arrow key or WASD to start`, `Game over`, `Press Space or Enter to play again`, `Snake couldn't start in this browser.`
- There is one test hook: the query parameters `?simulate-error=canvas` and `?simulate-error=startup`.

**Unknowns after research**
- The final repository for t1 (see Clarification outcomes and the sidecar question).
- No browser exists in the implementation pod, so manual gameplay proof is a reviewer layer.

## Locked decisions and assumptions

**Locked decisions**
- One file, `snake.html`, with HTML, CSS and JS inline. No network, no external dependencies, and it works from `file://` (spec §7, FR1).
- A 20 × 20 grid. The snake starts 3 segments long in the middle row, head on the right, facing right. One step every ~125 ms with a constant pace. Space or Enter restarts. A full board ends the round as Game over (spec §3 FR2–FR11, §8).
- The exact English strings listed above (spec §3–§4, HLD §5).
- Canvas rendering. A fixed-interval step. An input buffer of at most two queued turns, each checked against the last committed or queued direction. Food picked from the list of free cells. The error message visible by default plus a `<noscript>` fallback. The `?simulate-error=canvas|startup` hook (HLD §6, §5).
- Static stdlib Python test `test_snake.py` only, with gameplay proven by hand in a real browser (HLD §6, work-item criterion 11 and 13).
- Placement: provisional `harel-pdlc-infra/halo-119-snake/` with nothing outside that folder modified. If t1 is re-pointed to the test repo, both files go at the repo root and `docs/**`, `serve.py`, `smoke_test.py`, `README.md` and `hello_world.txt` stay byte-identical (HLD §7–§8, `work-items.md` t1).
- HALO-118 is not a blocker. An approved design changes only colours, spacing and where the text sits (spec §4, §6).

**Assumptions**
- *A1 — Build in infra as assigned.* Evidence: `work-items.md` t1 `repoId` and HLD §8. If wrong (the developer re-points to the test repo), only the paths change (`halo-119-snake/` → repo root) and `python3 smoke_test.py` joins the gate. The steps are otherwise unchanged.
- *A2 — `test_snake.py` uses stdlib `unittest`* and runs with both `python3 halo-119-snake/test_snake.py` and `python3 -m unittest discover -s halo-119-snake`. Evidence: infra's tests are `unittest` (`Makefile:302`). If wrong, only the runner style changes.
- *A3 — Keys are matched on `KeyboardEvent.key`*, so `ArrowUp`…`ArrowRight`, `w`/`a`/`s`/`d` case-insensitively, `" "` and `Enter`, with `preventDefault` on handled keys so arrows and Space don't scroll the page. Evidence: no layout or keyboard requirement beyond US desktop keys (D-2). If wrong, non-QWERTY layouts map WASD differently. This is acceptable under D-2.
- *A4 — An unknown `simulate-error` value is ignored*, so the game starts normally. Evidence: HLD §5 only says the hook has no effect when absent. If wrong, a reviewer typo starts a normal game instead of an error. This is harmless.
- *A5 — Cell size of 20 px gives a 400 × 400 canvas.* It fits a typical desktop window without scrolling (spec §4). If wrong, it's a one-constant visual change.

## Solution proposal

**Approach.** One static file with no build step, laid out as the HLD's five logical parts, plus one static test. There is nothing in either candidate repo to reuse or integrate with. The change is purely additive and confined to `halo-119-snake/`.

**Page structure (`snake.html`)**
- `<!DOCTYPE html>`, `<meta charset="utf-8">`, a `<title>` and one inline `<style>`, with no `<link>`, `<img>`, web fonts or external `src`/`href`.
- An error element containing `Snake couldn't start in this browser.`, **visible in the markup by default**, plus the same text in `<noscript>`. A game container (a score line, a status line, a hint line and a `<canvas>`) is hidden by default. Start-up reveals the game and hides the error only after it fully succeeds. This covers FR12(a) structurally and makes "empty or frozen field" impossible for (b) and (c).
- Flat colours: a dark background, light grid lines, a green snake and a red food item (distinct from each other and the background). There are no animations.

**Script design (one inline `<script>` at the end of `<body>`, in an IIFE)**
- *Start-up guard.* Read `simulate-error` via `URLSearchParams(location.search)`. Get the canvas `getContext("2d")`. Treat a null context, or `simulate-error=canvas`, as failure (b). `simulate-error=startup` throws inside the guarded block for (c). Wrap the whole start-up in `try/catch`. The catch calls `showError(err)`, which hides the game, shows the message, stops the clock and logs the error with `console.error` (logged, never swallowed: D-5).
- *State.* `snake` is an array of `{x, y}`, head first. It also holds `dir`, the last committed direction; `queue`, the buffered turns (at most 2); `food`, `score`, and `mode` ∈ `ready | playing | over | error`. `reset()` builds the initial state: snake at `(9,10),(8,10),(7,10)` facing right, score 0, food placed, mode `ready`, start hint shown. Rendering happens once.
- *Input.* There is one `keydown` listener.
  - `ready`: Up/W, Down/S and Right/D set `dir` and switch to `playing`, which starts the clock and hides the hint. Left/A (opposite of the initial facing) and other keys are ignored.
  - `playing`: a direction is queued only if it is neither equal nor opposite to the last queued direction (or `dir` when the queue is empty), and the queue holds fewer than 2.
  - `over`: only Space/Enter call `reset()`. Arrows and WASD do nothing.
  - `error`: everything is ignored.
- *Clock.* `setInterval(step, 125)` starts on entering `playing` and is cleared on Game over, restart or error, so there is never more than one interval. The pace is constant (no speed-up).
- *Step.* Shift one direction off `queue` into `dir`, then compute the next head.
  - Off-grid → game over. Wrapping is never computed.
  - `eating = next equals food`.
  - Body collision is checked against the snake minus its tail when not eating (classic tail rule, FR8), and the whole snake when eating.
  - Otherwise, unshift the head. If eating, increment the score and place food, otherwise pop the tail.
  - If no free cell remains, it's game over (FR10).
  - Render. The body of `step` sits in `try/catch` → `showError` (an error in the game loop stops the game visibly: work-item criterion 9).
- *Food.* Build the list of free cells (all 400 cells minus the snake) and pick one with `Math.floor(Math.random() * free.length)`. With an empty list, return null, which the step treats as a full board.
- *Render.* Clear, draw the grid lines, draw the food, then the snake. Set the score text `Score: N`. Game over sets the status `Game over` and the hint `Press Space or Enter to play again`. The final frame stays drawn.

**Test design (`test_snake.py`)**
- A stdlib `unittest` test reads `snake.html` next to itself (`Path(__file__).resolve().parent`). It asserts:
  - no `http://` or `https://` substrings;
  - no `src=` or `href=` attribute whose value is external (any value other than an empty or `#` fragment, and no `src` at all on `<script>`);
  - no `<img>`, `<audio>`, `<video>`, `<link>`, `<iframe>` or `@import`;
  - no network or storage APIs (`fetch(`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`, `localStorage`, `sessionStorage`, `indexedDB`);
  - all five required strings present;
  - a `<noscript>` containing the error string;
  - a `<canvas>` present;
  - both `simulate-error` values present.
- A module docstring documents how to run it and how to open the page (KAN-8 header-usage precedent).

**Alternatives rejected**
- A DOM grid of 400 divs (HLD §6: heavier, with no clean "can't draw" signal).
- `requestAnimationFrame` with time accumulation (more code for no AC gain over a fixed interval).
- A Node/Playwright browser test (adds dependencies, against the HLD and the KAN-8 precedent).
- Embedding the page in infra's `docs/` book (it would couple it to infra docs, which D-6 rules out).

## Ordered implementation steps

1. **Create `halo-119-snake/snake.html` skeleton.** Add the doctype, meta charset, title and inline CSS. Add the visible-by-default error element and `<noscript>` with the exact error string. Add the hidden game container with the score, status and hint lines and a 400 × 400 `<canvas>`.
   - Advances: AC1 (structure), AC9(a), AC10, AC11 (look).
   - Covered by: `test_snake.py` (static) and manual browser checks.
2. **Add the start-up guard** in the inline script: the `simulate-error` parse, the `getContext("2d")` check, `try/catch` around start-up, and `showError` (hide game, show message, clear interval, `console.error`; never an empty catch).
   - Advances: AC9(b)(c) and the D-5 invariant.
   - Covered by: manual checks with `?simulate-error=canvas` and `?simulate-error=startup`, and the static test's hook-string assertion.
3. **Add state, `reset()`, food placement and render.** Initial snake `(9,10),(8,10),(7,10)` facing right, score 0, food from free cells, `Score: 0`, start hint, grid drawn, no clock running.
   - Advances: AC1 (snake still for 3 s), AC5 (food never on the snake).
   - Covered by: manual checks.
4. **Add the `keydown` handler** with the per-mode rules (Ready start keys with Left/A ignored, Playing queue with the reverse/same filter and a cap of 2, Over accepts only Space/Enter) and `preventDefault` on handled keys.
   - Advances: AC2, AC3, AC4, AC8 (arrows don't restart).
   - Covered by: manual checks in all four directions with both key sets.
5. **Add the clock and `step`.** A single 125 ms interval: committed direction, wall check without wrap, body check with the tail rule, eat/grow/score/new food, full-board end, Game over texts with the final frame frozen, clock cleared, and `try/catch` → `showError` around the step body.
   - Advances: AC2 and AC12 (steady pace), AC5, AC6, AC7, the FR10 full board, and loop-error visibility.
   - Covered by: manual checks. The full board is read from the code (no reviewer can reasonably fill 400 cells by hand), as the spec allows.
6. **Wire restart.** Space or Enter in `over` calls `reset()`, which returns to Ready with score 0, the initial snake, one food and the start hint, and waits for a direction key.
   - Advances: AC8.
   - Covered by: manual checks (separately for Space and Enter, from a score of 5).
7. **Create `halo-119-snake/test_snake.py`** with the static assertions from the Solution proposal and the usage docstring. Use stdlib only. Don't add `requirements.txt` or `__init__.py`.
   - Advances: work-item criterion 11, plus AC1 and AC10 (static half).
   - Covered by: it is the test layer itself.
8. **Run the gate** (see Verification), confirm `git diff --stat develop...HEAD` lists only the two new files, and record the manual browser results for spec ACs 1–12 in the PR description: the three error cases (JavaScript disabled, `?simulate-error=canvas`, `?simulate-error=startup`) and a network-panel check over a full round.
   - Advances: AC13 and work-item criteria 12 and 13.
   - Covered by: the gate, plus the manual layer.

Implicit invariants: authorization, tenancy and concurrency are not applicable (one local page, one player, single-threaded). Idempotency means one interval at most, which steps 5 and 6 cover. Validation and error paths are covered by steps 2 and 5. Dependencies: none to acquire. Generated deliverables: none. Both files are hand-written sources.

## Work-item mapping

| Step | Work item |
|---|---|
| 1–8 | t1 — Minimal one-page Snake game (snake.html) |

t1 is the only work item, and every step belongs to it. There is no planning gap.

## Verification and CI gate

Run these once, locally, on the committed SHA, in this order:
1. `python3 halo-119-snake/test_snake.py` passes (work-item criterion 11).
2. `make e2e-unit` (infra canonical gate, `Makefile:301`). It must stay green. It shows the new files don't disturb the repo-wide tests, notably `scripts/tests/test_retired_keys.py`. If `helm` is missing in the pod, run `python3 -m unittest discover -s scripts/tests` instead and say so in the PR, as the `verify` skill prescribes.
3. `shellcheck` is not applicable (no shell scripts added). Helm lint/template is unaffected (no chart change).
4. `git diff --name-status develop...HEAD` shows exactly `A halo-119-snake/snake.html` and `A halo-119-snake/test_snake.py` (AC13).

**If t1 is re-pointed to `ophirgal/test-repo-for-halo`**, the gate becomes `python3 test_snake.py` then `python3 smoke_test.py`, with the same diff check against `main`, listing only the two root files.

**Layers that cannot run in a pod**: real-browser gameplay (spec ACs 1–12, including JavaScript disabled and the network panel). No browser exists in the pod, and the HLD rules out adding Playwright. The reviewer runs these and records the results in the PR, as spec §5 "Proof" requires.

**Provider CI**: no change. CI doesn't collect `halo-119-snake/test_snake.py` (discovery is rooted at `scripts/tests`), and wiring it in would mean editing `ci.yml`/`Makefile`, which is out of scope. `.factory/testing.md` and `.factory/delivery-assets` don't exist, and neither is needed (no binary of 1 MiB or more).

**Done means**:
- the static test is green;
- `make e2e-unit` is green, or a stated substitution is green;
- the diff has exactly two added files;
- the PR records the manual results for every spec AC 1–12 with three-way AC9 and the `verify` skill's Verification section.

## Risks and scope guards

**Risks**
- *Placement conflict.* The spec home (test repo, D-6) differs from the assigned repo (infra). Mitigation: the folder is boxed so a move is a two-file relocation. A clarifying question has been raised. Don't open the PR against a repo the developer hasn't confirmed.
- *Fast-input reversal* (e.g. Up then Left within one step while moving right). The queue validates each turn against the last queued direction. The reviewer checks it by hand.
- *Hidden scroll.* Arrows and Space would scroll the page. `preventDefault` on handled keys prevents it.
- *Duplicate intervals on restart.* Always clear before starting.
- *HALO-118 drift.* A later design changes only colours, spacing and text placement. No behaviour changes.

**Scope guards (must NOT do)**
- Modify any file outside `halo-119-snake/` in infra: no `Makefile`, `ci.yml`, `docs/`, `AGENTS.md` or `README.md` edits. In the test repo, don't touch `docs/**`, `serve.py`, `smoke_test.py`, `README.md` or `hello_world.txt`.
- Edit `spec.md`, `hld.md` or `work-items.md`.
- Add high scores, storage, pause, levels, speed-up, wrap-around, sound, images, touch controls, themes, a win screen or a README.
- Add Node, npm, Playwright, `requirements.txt` or any dependency or CDN reference.
- Change any on-screen string from its exact spec text.
- Make any check green by deleting, skipping or weakening it. A failing pre-existing `scripts/tests` case is checked against `develop` and reported, never silenced.
- Swallow an error: every `catch` routes to `showError` and `console.error`.

## Clarification outcomes

One question was raised through the platform's plan conversation and is pending: should t1 land in `ophirgal/test-repo-for-halo` at the repo root (spec §6, D-6), or does the developer approve `McK-Private/harel-pdlc-infra` under `halo-119-snake/` as the home? Until it's answered, this plan follows assumption A1 (infra, as `work-items.md` assigns) and states the exact path and gate differences for the test-repo option.
