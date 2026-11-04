# HALO-119: Minimal one-page Snake game (intake draft, NOT READY)

## Story
As a player who opens the page in a desktop browser, I want to play a full round of Snake with the keyboard (start, steer, eat, grow, die, restart), so that I can play immediately with no installation, account or setup.

Epic: Snake Game (Test Trace ID), Epic PRD v2. Covers FR-1 to FR-8 and decisions D-1, D-2, D-3, D-5 and D-6. Priority: Must. Size: S (about 2 points).
Depends on: "עיצוב מסך המשחק המינימלי" (HALO-118). **No approved design for it is in the repository yet** (P0-1).

## Scope
**In scope:** one standalone page with classic Snake rules: walls end the round, no wrap-around, a steady pace, arrow keys plus WASD.
**Out of scope:** touch or mobile controls, high scores, levels, speed-up, pause, sound, themes, integration with the Halo UI or backend, hosting or deployment.

## Behaviour already pinned by the story and epic
- **On open (offline, current desktop browser):** a square grid play field, the snake (length 3), one food item and the score 0. The snake stays still until a key is pressed.
- **Start:** an arrow key or W/A/S/D starts movement in that key's direction, one cell per step, at a steady pace.
- **Steering:** a perpendicular key turns the snake on the next step. A key for the direction straight back (for example Left or A while moving right) is ignored, and the round continues.
- **Eating:** the length grows by 1, the score goes up by 1, and new food appears in a cell the snake does not occupy.
- **Wall hit:** the snake stops and "Game over" is shown with the final score. The snake does not reappear on the opposite side.
- **Body hit:** the snake stops and "Game over" is shown with the final score.
- **Restart:** one key press starts a new round with score 0, the starting length and one food item.
- **Cannot run:** a visible error message is shown instead of an empty or frozen field.
- **Self-contained:** no network requests, sounds, images, pause or score saving.

## Open (blocking)
- **P0-1:** wait for the HALO-118 design, or build to the PRD's text description now?
- **P0-2:** target repo and file path. Proposed: a new `docs/snake.html` in `ophirgal/test-repo-for-halo`, opened directly as a file, with the KAN-8 Hello World page and its checks unchanged.
- **P0-3:** which key(s) restart after Game over, and whether that key sets the first direction.
- **P0-4:** which "cannot run" situations must show the error, and the message wording.

## Open (important)
- **P1:** a checkable bar for the pace (steps per second) and the grid size.
- **P1:** behaviour when the snake fills every cell and no free cell is left for food.
- **P1:** behaviour when the first key points into the snake's own starting body.
- **P1:** the expected proof: a manual browser walkthrough, an automated check, or both.
- **P2:** exact wording of the Game over line and of any pre-start hint.
