# Feature Specification Document

**Story:** HALO-128 — מפתח מריץ סקריפט Bash ומקבל ברכת Hello World במסוף
**Epic:** Minimal Hello World Bash Script (HALO-127), from the epic's PRD "Hello World script" (סקריפט Hello World), Confluence pageId=34570241
**Target repository / base branch:** ophirgal/test-repo-for-halo, `main`

## 1. Feature Overview

**Summary.** The repository gets one small Bash script. Run from a terminal, it prints a single line, `Hello, World!`, and exits successfully. An automated test runs the script and checks its output and exit code.

**Problem statement.** Today a developer can see a Hello World greeting only as a web page (served by the existing page server) or as a text file (`hello_world.txt`). Nothing runs the greeting straight from the terminal, so there is no quick, dependency-free way to confirm that the environment runs scripts (PRD §1.1).

**Target users / actors.**
- **Developer or tester working in the repository.** Runs the script from a Bash terminal and reads the greeting.
- **PR reviewer.** Reads the recorded test results in the pull request. The repository has no CI (PRD risk RK1).

## 2. Goals & Non-Goals

### Story context

בתוך הסיפור: הסקריפט, ובדיקה אוטומטית שמריצה אותו ובודקת את הפלט ואת קוד היציאה; תוצאת הבדיקה מתועדת בבקשת המיזוג, שמציינת את הסיפור ואת מסמך הדרישות. מחוץ לסיפור: פרמטרים לברכה, מסופים שאינם Bash, ושינוי דף האינטרנט או קובץ הטקסט הקיימים.

### Goals
- A developer runs one Bash script from the terminal and gets exactly one line, `Hello, World!`, on standard output, with exit code 0 (PRD R1, R2).
- The script needs nothing installed beyond Bash itself (PRD R3; Engineering requirements R2, Dependencies).
- An automated test runs the script and checks its output and exit code, including when it is called with arguments. Its result is recorded in the pull request (PRD RK1 mitigation; story AC4).
- The existing Hello World web page and its smoke test keep working unchanged (PRD R4).
- The pull request names this story (HALO-128) and the PRD "Hello World script" (Engineering requirements R7, Traceability).

### Non-Goals
- Parameters or a name that customise the greeting. Arguments are ignored (PRD §8).
- Support for shells other than Bash, such as Windows PowerShell (PRD §8).
- Setting up automated tests or CI for the whole repository. That belongs to another epic (PRD §8).
- Any change to the existing web page (`docs/`, `serve.py`) or the existing text file (`hello_world.txt`) (PRD §8).
- Changing the existing greeting wording anywhere. The existing page says `Hello World` and the text file says `Hello World`; both stay as they are.

## 3. Functional Requirements

- **FR1 — Greeting output (PRD R1).** Running the script from a Bash terminal prints exactly one line to standard output: `Hello, World!`.
- **FR2 — Successful exit (PRD R2).** The script finishes with exit code 0.
- **FR3 — Arguments ignored (PRD §3, exception flow).** When the script gets arguments (for example `foo bar`), it ignores them, prints the same single line `Hello, World!`, and exits with code 0.
- **FR4 — No extra components (PRD R3).** The script works on a machine with Bash alone. The epic adds no package, tool or dependency.
- **FR5 — Automated test.** The repository contains an automated test that runs the script and checks both the output and the exit code, including the arguments case. The test passes, and its result is recorded in the pull request.
- **FR6 — No regression (PRD R4).** After the change, the existing smoke test for the Hello World page (`python3 smoke_test.py`, currently `OK: 87 checks passed`, exit 0) passes as before, and the page shows the same greeting.
- **FR7 — Traceability (Engineering requirements R7).** The pull request names story HALO-128 and the PRD "Hello World script" (סקריפט Hello World).

**Inputs:** none. The script reads no input and opens no files, and any arguments are ignored.
**Outputs:** one line, `Hello, World!`, on standard output, and exit code 0.
**Core workflow:** the developer runs the script, and the script prints the greeting and exits successfully.
**Edge cases:** the script is called with arguments, and the output and exit code are unchanged.

## 4. User Experience & Behavior

- **Flow (PRD §3):**
  1. The developer runs the script from a Bash terminal in the repository.
  2. The script prints `Hello, World!` on one line and exits with code 0.
- **States:** there are none to observe beyond the single run. The script has no prompts, options or interactive states.
- **Output format:** plain text, exactly `Hello, World!`, which is the conventional wording decided in PRD §7. It has the comma and the exclamation mark and fits on one line. It deliberately differs from `hello_world.txt` (`Hello World`).
- **Perceived performance:** the result appears immediately. The story's stated value is checking the environment "within seconds".
- **Design:** none needed. There is no UI, only terminal text (PRD §3).
- **User-facing errors:** none are defined. Arguments are the only exception flow, and they produce the normal greeting.

## 5. Acceptance Criteria

1. תרחיש 1: מסלול תקין — הרצה מהמסוף. **בהינתן** מסוף Bash בתיקיית המאגר, **כאשר** המפתח מריץ את הסקריפט, **אז** מודפסת לפלט הרגיל בדיוק שורה אחת, "Hello, World!", **וגם** קוד היציאה הוא 0.
2. תרחיש 2: מקרה קצה — הרצה עם פרמטרים. **בהינתן** מסוף Bash, **כאשר** המפתח מריץ את הסקריפט עם הפרמטרים "foo bar", **אז** מודפסת אותה שורה אחת, "Hello, World!", **וגם** קוד היציאה הוא 0.
3. תרחיש 3: גבול התחום — בלי רכיבים נוספים. **בהינתן** מחשב שמותקן בו Bash בלבד, בלי שום חבילה שהאפיק הוסיף, **כאשר** המפתח מריץ את הסקריפט, **אז** הפלט הוא "Hello, World!" וקוד היציאה הוא 0.
4. תרחיש 4: מסלול תקין — הבדיקה האוטומטית. **בהינתן** המאגר אחרי השינוי, **כאשר** מריצים את הבדיקה האוטומטית של הסקריפט, **אז** היא עוברת, **וגם** בקשת המיזוג מציגה את תוצאתה ומציינת את הסיפור הזה ואת מסמך הדרישות "סקריפט Hello World".
5. תרחיש 5: רגרסיה — דף האינטרנט הקיים. **בהינתן** המאגר אחרי השינוי, **כאשר** מריצים את בדיקת העשן הקיימת של דף ה-Hello World, **אז** היא עוברת כמו לפני השינוי, **וגם** הדף ממשיך להציג את אותה ברכה.

## 6. Dependencies & Constraints (product-level)

- **Dependencies:** none. No environment, service, permission or access key is needed (PRD §5), and no sibling stories exist. This is the only story in the epic, in wave 1 of the backlog.
- **Affects:** the existing Hello World web page (`serve.py`, `docs/`) and its smoke test (`smoke_test.py`) must keep behaving exactly as before. The smoke test also requires the server's routes to stay the same and every other path to return 404, so the new script must not be served as a page.
- **Engineering requirements — infrastructure, security, compliance:**
  - **R2 (Dependencies):** no new runtime or test dependency without a PRD note. The PRD has none, so the script and its test must use only Bash and what is already in the repository.
  - **R3 (CI is the gate):** the repository has no CI (PRD RK1), so the PR records the manual run of the new test and of `python3 smoke_test.py`. A person merges the PR after review.
  - **R4 (No secrets):** no tokens or personal data in the code, tests or commits.
  - **R7 (Traceability):** the PR names HALO-128 and the PRD.
- **Language decision (PRD §7, RK2):** the script is Bash, as the PO explicitly requested. A reviewer objection that it should be Python is answered by that recorded decision.

## 7. Technical Design (deferred to STRUCTURE)

The tech lead decides these in the STRUCTURE stage, within the constraints above:
- the script's file name and location in the repository (PRD §7);
- how the script is invoked, for example executable with a shebang, `bash <script>`, or both, and how that is documented (README or a header comment);
- what form the automated test takes, with no new dependency (for example a Bash test script, or a Python standard-library script following the `smoke_test.py` convention);
- how AC3 ("Bash only") is checked in practice;
- portability, for example avoiding features newer than the Bash 3.2 that ships with macOS.

## 8. Open Questions (if any remain)

None are blocking. Assumptions are recorded for STRUCTURE:
- "Exactly one line" is read as `Hello, World!` followed by a single newline. The criteria don't state whether anything may be written to standard error, so treat nothing on stderr as the expected default, not as an added criterion.
- The greeting wording `Hello, World!` is a PRD §7 decision, marked "for confirmation". If the PO later changes it, the change is one word in the script and its test.
