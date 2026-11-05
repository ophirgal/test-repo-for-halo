# HLD — HALO-119: Minimal one-page Snake game

> **Status: not ready.** Placement is unresolved (see §7). Work item t1 is assigned for now to `McK-Private/harel-pdlc-infra` and kept in its own folder, `halo-119-snake/`. That's only because the output contract requires a target repo, and this one goes against spec §6 / D-6. The ticket moves to `ophirgal/test-repo-for-halo` (repo root) once that repo is registered as a target. Everything else is designed and needs no further decisions.

## 1. System Overview
- **What:** one self-contained page, `snake.html`, running classic single-player Snake in a current desktop browser (Chrome, Edge, Firefox, Safari). It's played with the keyboard, works when opened from disk (`file://`) and makes no network requests.
- **Problem:** it's the test payload for the Halo end-to-end trace. A player must be able to play a full round (start, steer, eat, grow, die, restart) with no setup.
- **Responsibilities:** draw a 20×20 field, run the game rules, take keyboard input, show the score and status text, and show a visible message whenever start-up fails.

## 2. Architecture Overview
- **One file, no build step and no dependencies.** HTML, CSS and JS all sit inline in `snake.html`. It loads no fonts, scripts, images or analytics.
- **Logical parts inside the file** (one owner, one PR):
  - **Game state and rules:** the snake, its direction, the input buffer, the food, the score and the current state (Ready, Playing, Game over or Error).
  - **Clock:** a fixed 125 ms step.
  - **Input:** the arrow keys, WASD, Space and Enter.
  - **Renderer:** a `<canvas>` for the grid, snake and food. DOM text holds the score and status lines.
  - **Start-up and error guard:** the error message `Snake couldn't start in this browser.`
- **External dependencies:** none. Nothing links to the page and no server serves it; the player opens it from disk.
- **Verification:** a new standard-library Python test, `test_snake.py`, next to the page, plus the manual browser checks the spec's Proof section requires.

## 3. Data Flow Design
- Everything happens in the page, synchronously on the browser's main thread. There's no async I/O, server or storage.
- `keydown` puts a direction into the input buffer during Playing, or changes state during Ready and Game over.
- On each step, the next direction comes from the buffer, checked against the direction last committed. The head moves, then the step checks for a wall, the body (the tail cell counts as free when the snake isn't eating), food, and a full board. After that, state and score update and the frame redraws.
- **State transitions:**
  - Ready → Playing: Up/W, Down/S or Right/D. Left/A and every other key are ignored.
  - Playing → Game over: a wall, the body, or a full board.
  - Game over → Ready: Space or Enter. The arrow and WASD keys are ignored.
  - Error is terminal.

## 4. Component Breakdown
| Part | Responsibility | Inputs → Outputs | Repo |
|---|---|---|---|
| `snake.html` | The whole game: state, rules, clock, input, drawing and the error guard | Key events and clock steps → canvas frame, score and status text | Spec home: `ophirgal/test-repo-for-halo` (root). Provisional: `McK-Private/harel-pdlc-infra` under `halo-119-snake/` |
| `test_snake.py` | Static self-containment check, run with standard-library Python | The `snake.html` source → pass or fail | same as above |

## 5. Interface Contracts
- There are no APIs, events or cross-repo contracts.
- **Contract for players and reviewers:** the exact on-screen strings from the spec:
  - `Score: N`
  - `Press an arrow key or WASD to start`
  - `Game over`
  - `Press Space or Enter to play again`
  - `Snake couldn't start in this browser.`
- **Test hook:** the URL parameters `?simulate-error=canvas` and `?simulate-error=startup` force start-up failures (b) and (c), so AC9 can be checked in a browser. The hook only ever leads to the error state and has no effect when the parameter is absent.

## 6. Key Technical Decisions
- **Canvas rather than a DOM grid.** One element is simple to draw, and "the browser can't draw the play field" maps directly onto canvas support. The alternative, a grid of 400 divs, was rejected: it's heavier and gives no clean way to detect that failure.
- **A fixed-interval step at 125 ms.** The rate never depends on score or length (FR4, AC12). If the loop throws, the error is caught, the loop stops and the error message is shown, so nothing fails silently (D-5).
- **Input buffering.** Key presses queue up, at most two per step. Each one is checked against the last committed or queued direction: a reverse or same-direction press is dropped. So fast key presses can't turn the snake back onto itself (FR5).
- **Food placement.** The food goes in a random cell picked from the list of free cells, so it never lands on the snake. If there are no free cells, the round ends with Game over (FR10).
- **Error message visible by default.** The message is in the markup and is hidden only after start-up succeeds. That covers (a) JavaScript disabled, plus a `<noscript>` fallback. A failed canvas context covers (b), and a try/catch around start-up covers (c).
- **Location.** In `ophirgal/test-repo-for-halo`, the page goes at the repo root, not in `docs/`, so it isn't published if GitHub Pages is ever enabled and `serve.py`'s root-only site is left alone. In the provisional infra home, it goes in a new self-contained folder, `halo-119-snake/`, that nothing else references.
- **Automated checks: static only.** Adding Node or Playwright would add dependencies (KAN-8 set the same precedent). Gameplay is checked by hand in a real browser.

## 7. Risks & Constraints
- **Blocker: placement.** `ophirgal/test-repo-for-halo` is registered in this project only as the spec or plan repo, and the platform never makes a spec repo a work-item target. The only targets offered are the five Halo platform repos, and spec §6 and D-6 forbid them. t1 is assigned to `harel-pdlc-infra` only because the contract requires a target, and it is boxed into `halo-119-snake/`. Fix: register the test repo as a target (it had one for KAN-8) and re-run this step, or have the product owner explicitly approve infra as the home.
- **No CI** for the page. Proof is the local `python3 test_snake.py` run (plus `python3 smoke_test.py` if the page lands in the test repo) and the manual browser results recorded in the PR.
- **No regression (AC13):** in the test repo, `docs/index.html`, `serve.py` and `smoke_test.py` must stay byte-identical. The smoke test checks a fixed list of paths, so a new file can't break it. In the provisional infra home, nothing outside `halo-119-snake/` may change.
- **Scale and security:** not applicable. It's one page and one player, with no network or stored data.
- **Design drift:** HALO-118 isn't approved. When it is, it may change colours, spacing and where the text sits, nothing else.

## 8. Ticket breakdown
**t1 — Minimal one-page Snake game (`snake.html`)**. Depends on nothing. Provisional repo: `McK-Private/harel-pdlc-infra`, folder `halo-119-snake/`. It moves to `ophirgal/test-repo-for-halo` (repo root) once that repo is registered as a target.
- **Owns:** `snake.html` (new) and `test_snake.py` (new).
- **Must not modify:** anything outside its own files: in the test repo `docs/**`, `serve.py`, `smoke_test.py`, `README.md` and `hello_world.txt`; in infra, anything outside `halo-119-snake/`.
- **Acceptance criteria:** spec §5, ACs 1–13 in full, plus the static test and the manually recorded browser results, including AC9 run three ways.

## Build order
One ticket, t1. It isn't blocked by HALO-118: the developer chose to build to the Epic PRD's text description.
