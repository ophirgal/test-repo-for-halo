# HLD — HALO-119: Minimal one-page Snake game

> **Status: not ready.** Where the page goes is unresolved; see §7 and the open question below. Everything else is designed and needs no further decisions.

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
- **External dependencies:** none. The page is not linked from `docs/index.html` and isn't reachable through `serve.py`; that's by design, since the player opens it from disk.
- **Verification:** a new standard-library Python test, `test_snake.py`, at the repo root, plus the manual browser checks the spec's Proof section requires.

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
| `snake.html` | The whole game: state, rules, clock, input, drawing and the error guard | Key events and clock steps → canvas frame, score and status text | `ophirgal/test-repo-for-halo` (**target registration pending**) |
| `test_snake.py` | Static self-containment check, run with standard-library Python | The `snake.html` source → pass or fail | same |

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
- **Location: repo root, `snake.html`.** It stays out of `docs/`, so it isn't published if GitHub Pages is ever enabled on `docs/`, and it leaves `serve.py`'s root-only site alone.
- **Automated checks: static only.** There's no JS runtime convention in the repo, and adding Node or Playwright would add dependencies (KAN-8 set the same precedent). Gameplay is checked by hand in a real browser.

## 7. Risks & Constraints
- **Blocker: placement.** `ophirgal/test-repo-for-halo` is registered in this project only as the spec or plan repo, and the platform never makes a spec repo a work-item target. The only targets offered are the five Halo platform repos, and the spec and D-6 forbid them. No ticket can be published until that repo is registered as a target again (it had a target id for KAN-8), or the product owner approves a different home.
- **No CI** in the target repo. Proof is the local `python3 smoke_test.py` and `python3 test_snake.py` runs plus the manual browser results recorded in the PR.
- **No regression (AC13):** `docs/index.html`, `serve.py` and `smoke_test.py` must stay byte-identical. The smoke test checks a fixed list of paths and never scans the file tree, so a new file can't break it.
- **Scale and security:** not applicable. It's one page and one player, with no network or stored data.
- **Design drift:** HALO-118 isn't approved. When it is, it may change colours, spacing and where the text sits, nothing else.

## 8. Ticket breakdown (held back until placement is resolved)
**t1 — Minimal one-page Snake game (`snake.html`)**. Target repo: `ophirgal/test-repo-for-halo`, once it's registered as a target. Depends on nothing.
- **Owns:** `snake.html` (new) and `test_snake.py` (new), both at the repo root.
- **Must not modify:** `docs/**`, `serve.py`, `smoke_test.py`, `README.md` or `hello_world.txt`.
- **Acceptance criteria:** spec §5, ACs 1–13 in full, plus these:
  - `test_snake.py` passes using standard-library Python only. It checks that the page has no `http(s)://` URLs and no external `src`/`href`, and that every required string is present.
  - `smoke_test.py` still passes.
  - The PR records the manual browser results for ACs 1–12, including AC9 run three ways: with JavaScript disabled, with `?simulate-error=canvas` and with `?simulate-error=startup`.

## Build order
One ticket, t1. It isn't blocked by HALO-118: the developer chose to build to the Epic PRD's text description.
