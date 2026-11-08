# Intake draft: HALO-122 — סיפור מתחיל רק מתוך Jira (NOT READY)

## Story as published (kept as it is)

סיפור משתמש: בתור מפתח, אני רוצה שסיפור יתחיל ב-Halo מעצמו כשב-Jira יש לו את התווית AI-Factory, הוא בסטטוס In Progress ויש לו אחראי, וייעצר לפני התחנה הבאה כשאחד התנאים חסר, כדי שעבודה תתחיל רק ממה שתוכנן ב-Jira ולא תתחיל בטעות או מחוץ לספרינט.

הקשר ותיאור: בתוך הסיפור: התחלה אוטומטית לפי שלושת התנאים, הסרת "Start story", חסימת המעבר לתחנה הבאה עם הודעה כשתנאי חסר, וסיפורים שאינם ב-Jira. מחוץ לסיפור: הסיפור הקנוני של מפתחי Halo, שממשיך להתחיל מתוך Halo, והתחנות עצמן.

עוקב אחר: FR-1, FR-2, FR-3, FR-19, FR-20, FR-21 · סיכון: סיפורים מחוץ ל-Jira · סיכון: סיפורים שנחסמים באמצע הריצה · סיכון: תהליכי Jira שונים · סיכון: שינויים ב-Jira נראים באיחור · סיכון: שערי אישור

עדיפות: Must · גודל: XL (כ-8 נקודות) · חוסמים: אין · תלוי ב-: —

## Acceptance criteria (as published, not yet changed)

1. תרחיש 1: מסלול תקין — שלושת התנאים מתקיימים. **בהינתן** סיפור שפורסם ל-Jira ולא התחיל, **כאשר** ב-Jira מוסיפים לו את התווית AI-Factory, מקצים לו אחראי ומעבירים אותו ל-In Progress, **אז** הסיפור מתחיל ב-Halo בלי פעולה נוספת, **וגם** תחנת הקליטה (intake) שלו נפתחת כמו בסיפור שהתחיל היום.
2. תרחיש 2: מקרה קצה — תנאי אחד חסר. **בהינתן** סיפור שפורסם ל-Jira, עם התווית AI-Factory ובסטטוס In Progress אבל בלי אחראי, **כאשר** עובר זמן, **אז** הסיפור לא מתחיל ב-Halo, **וגם** אותו דבר כשחסרה רק התווית או כשהסטטוס אינו In Progress.
3. תרחיש 3: מסלול תקין — אין התחלה מתוך Halo. **בהינתן** סיפור שפורסם ולא התחיל, **כאשר** מפתח פותח אותו ב-Halo, **אז** הכפתור "Start story" אינו מוצג, **וגם** אין ב-Halo שום פעולה אחרת שמתחילה אותו.
4. תרחיש 4: גבול התחום — הסיפור הקנוני. **בהינתן** מפתח של Halo שטען סיפור בעזרת "Load canned story…", **כאשר** הוא פותח את הסיפור, **אז** הוא יכול להתחיל אותו מתוך Halo כמו היום.
5. תרחיש 5: גבול התחום — סיפור שאינו ב-Jira. **בהינתן** סיפור מקומי, או סיפור של אפיק שאינו מגובה ב-Jira, **כאשר** משתמש פותח אותו ב-Halo, **אז** אין שום פעולה שמתחילה אותו, **וגם** הוא לא מתחיל לעולם מעצמו.
6. תרחיש 6: רגרסיה — שערי האישור. **בהינתן** סיפור שהתחיל מתוך Jira, **כאשר** הוא מגיע לכל שער אישור (קליטה, בקשת המיזוג של התוכנית ושאר השערים), **אז** הוא ממתין לאישור של אדם בדיוק כמו סיפור שהתחיל היום, **וגם** אף שער אינו מדולג.
7. תרחיש 7: מקרה קצה — תנאי נשבר באמצע ריצה. **בהינתן** סיפור שרץ ונמצא באמצע תחנה, **כאשר** ב-Jira מסירים ממנו את התווית AI-Factory, **אז** התחנה הנוכחית מסתיימת כרגיל, **וגם** הסיפור נשאר בלשונית Active.
8. תרחיש 8: מקרה שגיאה — ניסיון להתקדם כשתנאי חסר. **בהינתן** סיפור שהתחנה שלו הסתיימה וב-Jira אין לו אחראי, **כאשר** המשתמש מאשר או ממשיך לתחנה הבאה, **אז** הסיפור לא מתקדם, **וגם** מוצגת הודעה שהסיפור חסום ושהתנאי החסר הוא האחראי.
9. תרחיש 9: מסלול תקין — התנאים חוזרים. **בהינתן** סיפור חסום שחסר לו רק הסטטוס In Progress, **כאשר** ב-Jira מחזירים אותו ל-In Progress והמשתמש מאשר או ממשיך, **אז** הסיפור עובר לתחנה הבאה, **וגם** הודעת החסימה אינה מוצגת עוד.

## What the intake has established so far

- Halo already starts a published story when its labelled Jira Story moves to an in-flight status. The new parts are: the assignee condition, removing the in-Halo "Start story", and blocking the next step with a message.
- Every Story Halo publishes already has the `AI-Factory` label. The label only decides the outcome if someone removes it.
- Halo itself moves a story's Jira issue to Done once the story is implemented. Teams may also move a story to "In Review" while its PR is open.
- The "Start story" button is the only place a developer picks per-story target branches.
- Some gates are passed outside Halo, such as merging the PR on the forge.

## Open points still blocking the spec

1. Which user actions count as "moving on to the next step" under FR-21. How forge-side merges are treated. Whether cancel and rewind are exempt.
2. Where the blocked message appears, and its content: one missing condition or all of them.
3. Which statuses count as "In Progress": exactly In Progress, or any in-flight status. This is decided separately for the start check and the mid-run check.
4. When a story is missing its assignee at start: does it silently not start, or move back to To Do with a Jira comment, as today's other start refusals do?
5. Whether labelled Jira Stories that Halo did not publish (imported stories) must also meet all three conditions.
6. The new meaning of removing the label: today it means "take the story out of Halo". Is the change intended, and should the Jira comment text change?
7. Losing the per-story target-branch choice.
8. Where the canned-story exception applies (all instances, or Halo-developer only), and whether design stories are in scope.
9. How to check criterion 7 before the Active tab from HALO-125 exists.
