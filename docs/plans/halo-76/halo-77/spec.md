# Feature Specification Document

## 1. Feature Overview

**Summary:** A minimal Python console application that presents the user with a menu of three topics — sports (ספורט), politics (פוליטיקה), and psychology (פסיכולוגיה) — and displays one pre-built question on whichever topic the user selects.

**Problem statement:** A user who wants to try answering a question in a subject they find interesting currently has no zero-install, zero-signup way to do so. This script provides that experience in a single terminal command.

**Target users / actors:** A casual user ("guest") who runs the script in a terminal. No authentication, no persistent identity.

## 2. Goals & Non-Goals

### Goals
- Present a selection menu with exactly three topics: ספורט, פוליטיקה, פסיכולוגיה.
- Display one pre-built question matching the user's chosen topic.
- Handle invalid input gracefully: show an error message and let the user retry without restarting.
- Run as a console-only Python script using only the standard library.

### Non-Goals (explicitly out of scope)
- More than one question per topic.
- Scoring, grading, or evaluating the user's answer.
- Tracking or storing user responses.
- Additional topics beyond the three specified.
- A graphical user interface of any kind.
- External Python packages.
- Automated tests (per explicit PO decision).

## 3. Functional Requirements

- **FR1 — Topic menu (traces to R1).** When the script starts, it displays a menu listing exactly three topics: ספורט, פוליטיקה, פסיכולוגיה. No other topics appear.
- **FR2 — Topic selection (traces to R1, R2).** The user provides input to select one of the three topics. The selection mechanism (numeric index, topic name, or other) is left to implementation.
- **FR3 — Question display (traces to R2, R3).** After a valid selection, the script displays exactly one pre-built question that corresponds to the chosen topic. Each topic has one and only one associated question, hardcoded in the source.
- **FR4 — Invalid input handling (traces to R5).** If the user enters a value that does not correspond to any menu option, the script displays an error message indicating the input is invalid and re-presents the choice opportunity — without requiring a restart of the script.
- **FR5 — Console-only execution (traces to R4).** The script runs in a terminal via Python. It uses only the Python standard library. It has no GUI, no web interface, and no dependency on any external package.
- **FR6 — Three questions total (traces to R3).** Exactly three questions exist in the codebase, one per topic, embedded directly in the source code.

### Inputs
- User keyboard input selecting a topic from the displayed menu.

### Outputs
- The topic menu (on script start and after invalid input).
- An error message (on invalid input).
- A single question matching the selected topic (on valid input).

### Core workflow
1. Script starts → menu displayed.
2. User types their selection.
3. If valid → display the corresponding question → script ends.
4. If invalid → display error message → return to step 2.

### Edge cases
- Empty input (user presses Enter with no text): treated as invalid input per FR4.
- Repeated invalid inputs: the retry loop continues indefinitely; the user is never locked out.

## 4. User Experience & Behavior

**Primary flow:** The user runs the script in a terminal. They immediately see a menu with three numbered or labelled topic options in Hebrew. They type their choice and press Enter. The script prints a question on their chosen topic. The interaction is complete.

**Error flow:** If the user types something that doesn't match a menu option, the script prints a short Hebrew-language message indicating the choice is invalid, then re-displays the menu or prompt so they can try again. This loop repeats until the user makes a valid selection.

**States the user observes:**
1. **Menu state** — the script is waiting for input; the menu is visible.
2. **Question state** — a valid topic was chosen; the question is displayed; the script is done.
3. **Error state** (transient) — invalid input was entered; an error message appears, then the script returns to the Menu state.

**Language:** All user-facing text (menu, questions, error messages) is in Hebrew, consistent with the language of the initiative description and the PRD.

**Look and feel:** Plain text in the terminal. No colors, no formatting beyond basic line breaks. The experience is intentionally minimal — no installation, no configuration, just run and interact.

## 5. Acceptance Criteria

1. **Scenario 1 — Happy path: valid topic selection.** Given the user has launched the script in a terminal, When they select a valid topic from the menu (ספורט, פוליטיקה, or פסיכולוגיה), Then the script displays exactly one pre-built question that corresponds to the selected topic.

2. **Scenario 2 — Happy path: three-topic menu.** Given the script has been launched, When the user sees the initial screen, Then a menu is displayed with exactly three topics: ספורט, פוליטיקה, and פסיכולוגיה — no more, no fewer.

3. **Scenario 3 — Edge case: invalid input.** Given the user has entered a value that does not match any menu option, When the script processes the input, Then an error message is displayed indicating the choice is invalid, And the user can select again without restarting the script.

4. **Scenario 4 — Boundary: console-only execution.** Given the script is ready for use, When its execution mode is examined, Then it runs as a Python script in the terminal only, with no graphical interface and no imports beyond the Python standard library.

## 6. Dependencies & Constraints (product-level)

- **No external dependencies.** The script uses only the Python standard library.
- **Engineering R1 compliance.** The project must declare `requires-python >= "3.10"` in a `pyproject.toml` file. (The script itself uses no version-specific features, but the engineering mandate applies to all Python deliverables in this repository.)
- **Engineering R7 compliance.** The pull request must reference story HALO-77 and epic HALO-76 for traceability.
- **Engineering R3 compliance.** The pull request merges only when all required CI checks pass.
- **No sibling story dependencies.** This is the only story in the epic.

## 7. Technical Design (deferred to STRUCTURE)

Architecture, file layout, the exact input-parsing mechanism (numeric vs. text-based selection), error-message wording, and `pyproject.toml` structure are determined by the tech lead in the STRUCTURE stage. The product spec constrains only the observable behavior described above.

## 8. Open Questions

- **Question content.** The exact text of the three questions (one per topic) is not specified in the PRD or story. The developer authors three reasonable, topically appropriate questions in Hebrew. If the PO wishes to supply specific question text, they should do so before implementation begins. Risk if unaddressed: low — the questions are trivial content, and any reasonable question satisfies the acceptance criteria.
- **Hebrew language confirmation.** The PRD assumption section marks the language choice as `[לאישור]` (to be confirmed). The entire initiative context is in Hebrew, making this the strong default. If a different language is required, the PO should flag it before implementation. Risk if wrong: the three questions and menu text would need to be rewritten — a small change.
