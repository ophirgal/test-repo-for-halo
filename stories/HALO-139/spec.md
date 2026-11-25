# HALO-139 — Make the Story Start button's error message user friendly (intake draft — NOT READY)

## 1. Feature Overview

**Status:** in-progress intake draft. The story has no acceptance criteria, and the screenshot its description refers to ("as shown in the screenshot below") did not reach the intake. The blocking questions are in §8.

**Summary.** On the Workspace's **Not Started** tab, a row the user may start has a one-click ▶ start button. When the start fails, the failure text appears under the button, in the row's last cell. The story asks for a short, user-friendly message there instead of the long technical one, and for the message to stop breaking the table's layout.

**Problem (as observed in the code).** The row shows the raw API error message (`harel-pdlc-frontend` `src/halo/workspace/WorkspaceAllItems.tsx:485`: `start.error.message`). That text is framed as `API error <status>: <detail> (request <request-id>)` (`src/lib/apiError.ts:30`). For a Jira failure, the detail is `could not start <KEY> in Jira: <raw error from Jira>` (`harel-pdlc-backend` `internal/httpapi/workspace_not_started.go:212`), which can be long. The text is rendered as a block in the narrow action column with no length limit (`WorkspaceAllItems.css:298`), so it stretches the row and the table.

**Target user.** A project member who starts their own Jira Story from Halo's Not Started tab.

## 2. Goals & Non-Goals

### Goals
- When the start fails, the user sees a short message in plain language that says what went wrong and what they can do next.
- The message never pushes content outside the table and never breaks the table's layout.

### Non-Goals (proposed; awaiting confirmation, see Q3)
- Changing *when* a start is refused (ownership, the AI-Factory label, Done status, dependencies). Only how a failure is shown changes.
- Error messages anywhere else, including the "Start story" button inside a story's conversation and the Not Started tab's whole-table load error.

## 3. Functional Requirements

Draft only. Each item depends on the answers in §8.

- **FR1 — Failure kinds.** A start can fail in these ways, each needing a user-facing message:
  - refused, not your Story
  - refused, the AI-Factory label is needed but cannot be added
  - refused, the Story is Done
  - refused, blocked by an unfinished Story
  - refused, not signed in with a work account
  - no permission on the project (403)
  - Jira itself failed (502)
  - any other or unknown failure

  What each kind should say is **Q1**.
- **FR2 — Technical detail.** What happens to the technical detail (HTTP status, raw Jira text, request id) is **Q2**. The frontend's rules say the request id is how a failure is traced in the logs and must not be stripped from error text (`harel-pdlc-frontend/CLAUDE.md`, "Backend access").
- **FR3 — Containment.** The message stays inside the row's action cell and never widens the table. Its length limit and overflow behaviour are **Q2**.
- **FR4 — Retry.** After a failure the ▶ button stays enabled, so the user can try again (this is how it works today).

## 4. User Experience & Behavior

- **Flow:** the user clicks ▶ on a Not Started row. The button shows it is busy. On failure, a red message appears in that row's action cell. On success, a ✓ appears, as it does today.
- **Look (to be confirmed, Q2):**
  - The message is at most one or two short lines.
  - It sits within the action column, and the row's height and the table's width do not jump.
  - The full detail is reachable without leaving the page.
- **Message wording (Q1):** not settled yet. The draft does not invent sentences.

## 5. Acceptance Criteria

1. תרחיש 1: מסלול תקין — כשל בהתחלת סיפור. **בהינתן** שורה בלשונית "Not Started" שהמשתמש רשאי להתחיל, **כאשר** הוא לוחץ ▶ וההתחלה נכשלת, **אז** מוצגת בתא הפעולה של השורה הודעה קצרה בשפה פשוטה (הנוסח לפי Q1), **וגם** לא מוצגים בה קוד HTTP, הקידומת "API error" או טקסט גולמי מ-Jira.
2. תרחיש 2: מקרה שגיאה — הודעה ארוכה. **בהינתן** כשל שהפרטים שלו ארוכים, **כאשר** ההודעה מוצגת, **אז** היא נשארת בתוך תא הפעולה, **וגם** רוחב הטבלה ומיקום העמודות לא משתנים.
3. תרחיש 3: רגרסיה — התחלה מצליחה. **בהינתן** שורה שהמשתמש רשאי להתחיל, **כאשר** הוא לוחץ ▶ וההתחלה מצליחה, **אז** הכפתור מציג ✓ ולא מוצגת הודעת שגיאה, כמו היום.

## 6. Dependencies & Constraints (product-level)

- The frontend's own rules:
  - Errors are never swallowed or hidden.
  - The request id is the string a user copies to trace a failure, so it is not stripped (`harel-pdlc-frontend/CLAUDE.md`).
  - A friendlier message must therefore still leave the detail available somewhere the user can reach.
- The refusal sentences come from the backend's start endpoint (`harel-pdlc-backend` `internal/httpapi/workspace_not_started.go:194`). Changing their wording would also touch the backend repository.

## 7. Technical Design (deferred to STRUCTURE)

These are left to STRUCTURE:
- where the friendly text is produced (frontend mapping or backend wording)
- how the detail is revealed
- the styling mechanism

## 8. Open Questions

- **Q1 (P0)** — Message wording: one sentence per failure kind, or one generic sentence?
- **Q2 (P0)** — Technical detail and layout: hidden behind hover/expand, or shown in full?
- **Q3 (P0)** — Scope: the Not Started ▶ only, or also the other start-button errors?
- **Q4 (P1)** — The missing screenshot: which error did the reporter see?

The full wording of each question, with a recommendation, is in the chat reply and the scorecard.

Note: a product memory says to decide open points without asking. This intake was explicitly told to ask instead, so the recommendations above are not yet adopted.
