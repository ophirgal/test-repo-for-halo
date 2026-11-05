# Feature Specification Document: HALO-119, a minimal one-page Snake game

Epic: Snake Game (Test Trace ID), Epic PRD version 2. Covers FR-1 to FR-8 and decisions D-1, D-2, D-3, D-5 and D-6. Priority: Must. Size: S (about 2 points). The game is built in the `ophirgal/test-repo-for-halo` repository.

## 1. Feature Overview

**Summary.** One self-contained web page that runs a classic single-player Snake game in a current desktop browser, played with the keyboard. The player opens the file and plays a full round right away: start, steer, eat, grow, die, restart. There's no installation, account, server or network.

**Problem statement.** The epic's hypothesis is that a small, low-risk initiative can go from idea to merged code through the Halo stages quickly. This game is the test payload for that end-to-end trace. Success means a player can open the page and play a full round with no setup (Epic PRD, Summary and hypothesis).

**Target users / actors.**
- **Player:** anyone who opens the page in a current desktop browser and plays with a keyboard (Epic PRD, Users; D-2).

## 2. Goals & Non-Goals

### Goals
- A full round can be played on one page with no setup and no network.
- Classic rules (D-1): walls end the round, there's no wrap-around, and the snake can't reverse into itself.
- A minimal look: a square grid field, the snake, one food item and a score line, in plain colours (FR-2, D-3).
- Start-up failures are shown to the player and never swallowed (FR-8, D-5).

### Non-Goals
- Touch or mobile controls, and responsive layout tuning (D-2).
- High scores, leaderboards, accounts or any saved data (D-3).
- Levels, speed-up, obstacles, pause, sound, themes or settings (D-3).
- A separate win screen.
- Integration with the Halo product UI or backend (D-6).
- Hosting or deployment beyond the page file itself.
- Any change to the existing "Hello World" page (`docs/index.html`), its local server (`serve.py`) or its smoke test (`smoke_test.py`) in the target repository.

## 3. Functional Requirements

- **FR1 Standalone page (FR-1).** The game is one file, `snake.html`, placed in `ophirgal/test-repo-for-halo` (STRUCTURE picks the folder). The player opens it directly from disk in a current desktop browser (Chrome, Edge, Firefox or Safari). It works offline and makes no network request of any kind: no fonts, libraries, images or analytics.
- **FR2 Field and initial state (FR-2).** On open, the page shows:
  - a square play field of 20 × 20 cells, with the grid visible;
  - a snake 3 segments long, lying horizontally in the middle row with its head on the right (facing right);
  - exactly one food item, in a cell the snake does not occupy;
  - the score line `Score: 0`;
  - the hint `Press an arrow key or WASD to start`.

  The snake stays still until the player presses a valid direction key.
- **FR3 Starting movement (FR-3, FR-4).** Before the round starts, any of Up/W, Down/S or Right/D starts the snake moving in that direction, and the start hint goes away. Left/A points straight back into the starting body, so it's ignored: the snake keeps waiting and the round does not end. All other keys are ignored.
- **FR4 Steady pace (FR-4).** The snake moves exactly one cell per step, at about 8 steps per second (a step every 125 ms, give or take). The pace stays the same all round. It doesn't change with score or length.
- **FR5 Steering (FR-3).** While the snake is moving, an arrow key or its WASD equivalent for a perpendicular direction turns the snake on the next step. A key for the current direction does nothing. A key for the opposite direction is ignored: the snake keeps going the same way and the round does not end. If several keys are pressed within one step, the snake still never turns straight back onto its own neck.
- **FR6 Eating (FR-5).** When the head enters the food's cell:
  - the snake grows by exactly one segment;
  - the score goes up by exactly 1, and the score line updates at once;
  - one new food item appears straight away, in a random cell the snake does not occupy.

  There is never more than one food item on the field.
- **FR7 Wall collision (FR-6, D-1).** If the next step would take the head outside the field, the round ends. The snake stops where it was and never reappears on the opposite side.
- **FR8 Body collision (FR-6).** If the next step would take the head into a cell the snake's body occupies, the round ends and the snake stops. The tail cell counts as occupied unless the tail moves away on that same step, as in classic Snake.
- **FR9 Game over (FR-6).** When the round ends, the field stays visible in its final state, the snake stops, and the page shows:
  - `Game over`;
  - the final score, as `Score: N`;
  - the hint `Press Space or Enter to play again`.

  While Game over is shown, arrow and WASD keys do nothing.
- **FR10 Full board.** If the snake fills every cell, so no free cell is left for food, the round ends exactly as in FR9, with the final score.
- **FR11 Restart (FR-7).** While Game over is shown, one press of Space or Enter starts a new round. The page returns to the initial state of FR2: score 0, a 3-segment snake in its starting position, one food item in a free cell, and the start hint. The snake waits for a direction key, as in FR3.
- **FR12 Visible start-up error (FR-8, D-5).** If the game can't start, the page shows the visible message `Snake couldn't start in this browser.` instead of an empty or frozen field. The three cases are:
  - (a) JavaScript is disabled;
  - (b) the browser can't draw the play field;
  - (c) any other failure while the game starts up.

  The message is shown on the page itself, not only in the browser console.

## 4. User Experience & Behavior

**States and transitions.**
1. **Ready (before the round).** The field, the still snake, one food item, `Score: 0` and the hint `Press an arrow key or WASD to start`. A valid direction key moves the page to Playing.
2. **Playing.** The snake moves at a steady pace. The score line shows the current score and there's no hint. A collision, or a full board, moves the page to Game over.
3. **Game over.** The frozen field, `Game over`, `Score: N` and `Press Space or Enter to play again`. Space or Enter moves the page back to Ready.
4. **Error.** Only the message `Snake couldn't start in this browser.` is shown. There are no transitions out of this state.

**Look and feel (FR-2, D-3).**
- Minimal: a square grid field with visible cell lines, the snake, one food item, and the score and status text above or below the field.
- Plain, flat colours. The snake and the food are clearly different colours and both stand out from the background.
- No images, icons, sounds, animation effects or decoration.
- On a typical desktop window, the whole field and the score line are visible without scrolling.
- All on-screen text is in English, exactly as written above.
- When the HALO-118 design ("עיצוב מסך המשחק המינימלי") is approved, it decides the look only: colours, spacing and where the text sits. It changes nothing in sections 3 to 5.

**Edge cases the player sees.**
- Left/A pressed before the round starts: nothing happens.
- A reverse key pressed while moving: nothing happens, and the round goes on.
- Mashing keys at the moment of death: Game over stays up until Space or Enter is pressed.
- Food never appears under the snake.

## 5. Acceptance Criteria

The story's 10 criteria, made checkable:

1. **Open (AC1).** In a current desktop browser with no network connection, opening `snake.html` from disk shows a 20 × 20 square grid, a 3-segment snake, exactly one food item, `Score: 0` and the start hint. For 3 seconds with no key pressed, the snake doesn't move.
2. **Start (AC2).** From Ready, pressing Up/W, Down/S or Right/D moves the snake one cell per step, in that direction, at a steady pace of about 8 steps per second. Pressing Left/A in Ready does nothing.
3. **Steer (AC3).** While the snake moves, a perpendicular arrow key or WASD key turns it on the next step. Both key sets work for all four directions.
4. **No reverse (AC4).** While the snake moves right, pressing Left or A leaves it moving right, and the round does not end. The same holds for each of the other three directions.
5. **Eat (AC5).** A 3-segment snake with score 0 eats food: its length becomes 4, the score line shows `Score: 1`, and exactly one new food item appears in a cell the snake doesn't occupy.
6. **Wall (AC6).** Steering the head off any of the four edges ends the round. The snake stops, the page shows `Game over` with the final score, and no part of the snake appears on the opposite edge.
7. **Body (AC7).** Steering the head into the snake's own body ends the round. The snake stops, and the page shows `Game over` with the final score.
8. **Restart (AC8).** With `Game over` and a score of 5 on screen, one press of Space (and, separately, of Enter) starts a new round: `Score: 0`, a 3-segment snake in its starting position, and exactly one food item. Arrow and WASD keys do not restart.
9. **Error (AC9).**
   - With JavaScript disabled, opening the page shows `Snake couldn't start in this browser.`
   - When the drawing support or start-up is made to fail (STRUCTURE decides how to test this), the same message is shown instead of an empty or frozen field.
10. **Self-contained (AC10).** The browser's network panel shows no request made during a full round (start, eat, die, restart), beyond loading the local file itself. The page has no sound, images, pause or saved scores.
11. **Look (FR-2).** During play, the page shows only the grid field, the snake, one food item and the score line, in plain colours, with no images or decoration.
12. **Steady pace (FR-4).** The pace is the same at score 0 and after eating several items.
13. **No regression.** In `ophirgal/test-repo-for-halo`, the existing `docs/index.html`, `serve.py` and `smoke_test.py` are unchanged, and `smoke_test.py` still passes.

**Proof.** A reviewer runs criteria 1 to 12 in a real current desktop browser and records the results in the PR. STRUCTURE may add automated checks on top.

## 6. Dependencies & Constraints (product-level)

- **"עיצוב מסך המשחק המינימלי" (HALO-118).** The backlog orders it first. No approved design exists yet, and the developer chose to go ahead without waiting. This story builds to the Epic PRD's text description. An approved HALO-118 design decides the look only (see §4).
- **Placement (D-6).** The page goes in `ophirgal/test-repo-for-halo`. None of the five Halo platform repositories is touched.
- **Halo engineering conventions.** "Fail fast; never swallow errors" (Halo (PDLC), §5) applies to start-up and to the game loop.
- **Human gates.** Every Halo gate still needs human approval (Halo (PDLC), §1).
- **Scope.** D-1, D-2, D-3, D-5 and D-6 all apply as approved.

## 7. Technical Design (deferred to STRUCTURE)

The tech lead decides all of the following in the STRUCTURE stage:
- how the field is rendered;
- the exact file location;
- how input is buffered within a step;
- how food placement is randomised;
- how errors are detected for each FR12 case;
- whether to add an automated test and how;
- how to keep the existing smoke test passing.

The product imposes these constraints:
- one file, everything inline;
- no network access;
- it works when opened from disk (`file://`);
- no external dependencies.

## 8. Open Questions

- None block the work. The decisions below were made by the agent on the developer's instruction ("make your own decisions reasonably and do not ask me anything"). The product owner can override any of them before approving:
  - 20 × 20 grid;
  - about 8 steps per second;
  - Space or Enter to restart;
  - the on-screen text;
  - a full board ends the round as Game over;
  - the file name `snake.html`.
- Visual details may change once HALO-118 is approved.
