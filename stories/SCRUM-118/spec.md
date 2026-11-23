# דוח הוצאות חודשי מתוך פנקס CSV (SCRUM-118) — מפרט

> סטטוס: **READY_FOR_SPEC**. המפתח העביר את ההכרעות לצוות ("make your own decisions"). Q1 הוכרע באפשרות (א): הסיפור מוסיף קובץ `pyproject.toml` חדש. Q2–Q4 הוכרעו לפי הנחות העבודה (סעיף 8).

## 1. Feature Overview

- **מה בונים:** חבילת Python חדשה בשם `ledger`, שמשתמשת רק בספרייה הסטנדרטית. היא קוראת פנקס CSV, מסכמת חודש אחד לפי קטגוריה במטבע בסיס, ונפתחת דרך `python -m ledger report`. העבודה מחולקת לשלושה פריטים תלויים: המודל ופענוח ה-CSV (t1), הדוח החודשי (t2) ושורת הפקודה (t3).
- **הבעיה:** מפתח שמנהל פנקס אישי או של צוות קטן בקובץ CSV רוצה סיכום חודשי מהמסוף בלי גיליון אלקטרוני. הסיכום צריך להיות דטרמיניסטי, ושורה פגומה צריכה להיות מוצבעת לפי מספר השורה שלה במקום להפיק סכום שגוי.
- **המשתמש:** מפתח שמנהל פנקס CSV (אישי או של צוות קטן) ועובד מהמסוף.
- **מקורות:** הסיפור כפי שנקלט מ-Jira (SCRUM-118). מסמך הדרישות של האפיק וצבר הסיפורים שלו לא צורפו לתור הזה, ולכן המזהים R1–R5 ו-RK1, RK2 מופיעים כאן כפי שהסיפור מציין אותם.

## 2. Goals & Non-Goals

### Story context

The story adds a new, stdlib-only Python package `ledger` under `src/` (src layout, discovered by the repository's manifest) with its tests under `tests/`, in three dependent work items: the model and CSV parser (t1), the monthly report (t2) and the command line (t3). A ledger is a UTF-8 CSV file with a header row naming the columns `id`, `date`, `amount`, `currency`, `category` and `memo`, in any order. Amounts are decimal numbers with at most two decimal places, positive for income and negative for expense. Currencies are ILS, USD or EUR, converted at fixed rates expressed in ILS per unit (ILS 1, USD 3.70, EUR 4.00), never fetched. Money is `decimal.Decimal` end to end; figures are rounded once, after summing, with `ROUND_HALF_EVEN`. Out of scope: other file formats, live exchange rates, persistent configuration, charts, any third-party dependency, changes to any existing file of the repository. Because the repository has no Python manifest yet, the story also adds one new `pyproject.toml` at the repository root that discovers packages under `src/` and sets pytest's `testpaths` to `tests/`, so that `pip install -e .` followed by `pytest` from the repository root installs the package and runs its tests; no existing file changes.

### Goals

- פענוח פנקס CSV לרשימת תנועות לפי סדר הקובץ, כשעמודות מזוהות לפי שם (R1).
- אימות כל שורה, ועצירה בשורה הפגומה הראשונה עם השגיאה `line {n}: {reason}` וסיבה מדויקת (R2).
- דוח חודשי שכולל הכנסות, הוצאות, נטו, מספר תנועות וסכומים לפי קטגוריה, ממוין לפי ערך מוחלט, עם אפשרות להגביל ל-N הקטגוריות המובילות (R3).
- המרה למטבע בסיס לפי שערים קבועים, ועיגול אחד אחרי הסכימה, חצי לזוגי (R4).
- `python -m ledger report FILE --month YYYY-MM [--base] [--top] [--json]` עם פלט טקסט או JSON מדויק, וקודי יציאה 0, 2 ו-3 (R5).
- קובץ `pyproject.toml` חדש בשורש המאגר, שמאפשר `pip install -e .` ואחריו `pytest` משורש המאגר, בלי לשנות קובץ קיים (הכרעת Q1).
- עדיפות Must, גודל M (כ-5 נקודות). עוקב אחר R1–R5 · שלבים 1–8 · סיכונים RK1, RK2.

### Non-Goals

- פורמטים אחרים של קבצים (Excel, JSON כקלט וכו').
- שערי חליפין חיים או שליפת שערים מהרשת.
- הגדרות שנשמרות בין הרצות.
- גרפים.
- כל תלות צד שלישי בחבילה.
- שינוי של קובץ כלשהו שכבר קיים במאגר.

## 3. Functional Requirements

- **FR1 — קלט (t1):** קובץ CSV בקידוד UTF-8, שיכול להתחיל ב-BOM. שורת הכותרת מכילה את `id, date, amount, currency, category, memo` בכל סדר, ועמודות נוספות לא נלקחות בחשבון. מסירים רווחים בקצות השדות, ומדלגים על שורות ריקות ועל שורות שיש בהן רק רווחים. יש שתי נקודות כניסה: `parse_csv(path)` ו-`parse_lines(lines)`, ושתיהן מתנהגות אותו דבר.
- **FR2 — פלט הפענוח:** רשימה של `Transaction` (dataclass קפוא) לפי סדר הקובץ, עם `id`, `date` (`datetime.date`), `amount` (`Decimal` בדיוק כפי שנכתב בטקסט), `currency`, `category` ו-`memo`. קובץ שיש בו רק כותרת מחזיר רשימה ריקה.
- **FR3 — אימות (t1):** השגיאה `LedgerError(line, reason)` מציינת את מספר השורה הפיזי בקובץ (הכותרת היא שורה 1, ושורות ריקות נספרות), ו-`str()` שלה הוא `line {line}: {reason}`. הסיבות המדויקות הן אלה שבתרחישים 5–7. הפענוח עוצר בשגיאה הראשונה.
- **FR4 — דוח (t2):** `monthly_report(transactions, month, base="ILS", top=None, rates=RATES)` מחזיר `month`, `base`, `count`, `income`, `expense`, `net` ו-`categories` (רשימה של `CategoryTotal(name, total, count)`), וגם `to_dict()` שבו הסכומים הם מחרוזות.
- **FR5 — המרה ועיגול (t2):** כל סכום מומר לפי `amount × RATES[currency] ÷ RATES[base]` בדיוק מלא, הסכומים נסכמים, ורק אז כל נתון מעוגל לשתי ספרות לפי `ROUND_HALF_EVEN`, בנפרד משאר הנתונים. לכן הנתונים לא חייבים להסתכם זה לזה.
- **FR6 — מיון ובחירה (t2):** קטגוריות ממוינות לפי ערך מוחלט יורד, ובשוויון לפי שם עולה. `top` מגביל רק את `categories`. רק תנועות של החודש המבוקש נספרות. חודש בלי תנועות מחזיר דוח של אפסים.
- **FR7 — שגיאות קריאה (t2):** חודש שאינו `YYYY-MM` עם חודש בין 01 ל-12, `base` שלא מופיע ב-`rates`, או `top` קטן מ-1, מעלים `ValueError` ולעולם לא `LedgerError`.
- **FR8 — שורת פקודה (t3):** `python -m ledger report FILE --month YYYY-MM [--base ILS|USD|EUR] [--top N] [--json]`. הפלט הוא טקסט של שלוש-עשרה שורות או JSON, כמו בתרחישים 19–21. קודי היציאה: 0 להצלחה, 2 לשימוש שגוי (כולל קובץ שאי אפשר לפתוח או שאינו UTF-8 תקין), 3 לשורה פגומה, עם השגיאה `error: {FILE}:{line}: {reason}`.
- **FR9 — צורת הסכום (t1):** סכום תקין הוא מספר עשרוני רגיל עם סימן אופציונלי (`+5`, `-2.50`, `.50` מתקבלים). כתיב מדעי (`1e3`), `NaN` ו-`Infinity` נדחים עם `amount '…' is not a number`.
- **FR10 — מספר השדות (t1):** בהודעה `expected N fields, got M`, ‏N הוא מספר השדות בשורת הכותרת (כולל עמודות נוספות), ו-M הוא מספר השדות בשורה.
- **FR11 — התקנה והרצת בדיקות:** קובץ `pyproject.toml` חדש מגלה את החבילה תחת `src/` ומגדיר את `testpaths` של pytest ל-`tests/`. ‏`pip install -e .` ואחריו `pytest` משורש המאגר מתקינים את החבילה ומריצים את בדיקותיה.

## 4. User Experience & Behavior

- **מסלול רגיל:** המפתח מריץ `python -m ledger report ledger.csv --month 2026-03` ומקבל במסוף שבע שורות סיכום, ואחריהן שורה לכל קטגוריה עם הזחה של שני רווחים. הערוץ stderr נשאר ריק, וקוד היציאה הוא 0.
- **JSON:** עם `--json` הפלט הוא אובייקט JSON אחד, והסכומים בו הם מחרוזות כדי שלא יאבד דיוק. הוא מתאים להעברה בצינור לכלי אחר.
- **חודש ריק:** הסכומים מוצגים כ-`0.00`, ובמקום רשימת הקטגוריות מופיעה השורה `categories: none`.
- **שורה פגומה:** stdout נשאר ריק, ו-stderr מציג שורה אחת בדיוק: `error: {FILE}:{line}: {reason}`, כשהנתיב מוצג כפי שהוקלד. קוד היציאה הוא 3. המפתח פותח את הקובץ בשורה הזאת ומתקן אותה.
- **שימוש שגוי:** stdout נשאר ריק, ב-stderr מופיעה הודעה, וקוד היציאה הוא 2.
- **עזרה:** `python -m ledger report --help` מתעד את `--month`, וקוד היציאה הוא 0.
- **דטרמיניזם:** אותו קובץ ואותם ארגומנטים מפיקים תמיד את אותו פלט.

## 5. Acceptance Criteria

1. Scenario 1 — Happy path: a valid file parses in order. Given `tests/fixtures/ledger/sample.csv` holds the header and nine valid rows (seven dated 2026-03, one 2026-02-27, one 2026-04-01; ids `t001`…`t009`), When `parse_csv(path)` is called, Then it returns nine `Transaction` values in file order, each a frozen dataclass with `id` (str), `date` (`datetime.date`), `amount` (`Decimal`, exactly the text's value, so `12000.00` stays `Decimal("12000.00")`), `currency` (str), `category` (str) and `memo` (str, possibly empty).
2. Scenario 2 — Happy path: header order is free and fields are stripped. Given a header `memo,category,currency,amount,date,id` and a row whose fields carry surrounding spaces, When the text is parsed, Then the transaction holds the trimmed values and the columns are matched by name, not by position. Columns beyond the six named ones are ignored.
3. Scenario 3 — Boundary: BOM, blank lines and a quoted memo. Given `tests/fixtures/ledger/bom_blank.csv` starts with a UTF-8 BOM, has blank and whitespace-only lines between rows, an empty memo on one row and a memo quoted because it contains a comma on another, When parsed, Then two transactions are returned, the BOM and the blank lines are ignored, the empty memo is `""` and the quoted memo keeps its comma.
4. Scenario 4 — Boundary: header only. Given a file with the header row and no data rows, When parsed, Then an empty list is returned and no error is raised.
5. Scenario 5 — Error: a bad row raises `LedgerError(line, reason)`. Given a row that cannot become a transaction, When parsed, Then `LedgerError` is raised carrying `line` (the physical line number in the file: the header is line 1 and blank lines count) and `reason`, with `str(error)` equal to `line {line}: {reason}`, and the reason for each case is exactly: a date not matching `YYYY-MM-DD` → `date '2026-3-1' is not YYYY-MM-DD`; a well-formed date that is not a calendar date → `date '2026-02-30' is not a calendar date`; an amount that is not a decimal number, including `NaN` and `Infinity` → `amount 'abc' is not a number`; an amount with more than two decimal places → `amount '1.505' has more than 2 decimal places`; a zero amount → `amount must not be zero`; a currency outside ILS/USD/EUR, compared case-sensitively → `unknown currency 'usd'`; an empty category → `empty category`; an empty id → `empty id`; a row whose field count differs from the header's → `expected 6 fields, got 5`. Parsing stops at the first bad row.
6. Scenario 6 — Error: duplicate id. Given two rows share an id, with a blank line between them, When parsed, Then the error names the second row's line and reads `duplicate id 't1' (first seen on line 2)`.
7. Scenario 7 — Error: header problems. Given a header lacking required columns, When parsed, Then `LedgerError(1, "missing column(s): currency, category, memo")` lists the missing names in the canonical order `id, date, amount, currency, category, memo`; Given an empty file (`tests/fixtures/ledger/empty.csv`, zero bytes), When parsed, Then `LedgerError(1, "missing header")`.
8. Scenario 8 — Edge: two entry points. Given ledger text as any iterable of lines (for example an `io.StringIO`), When `parse_lines(lines)` is called, Then it behaves exactly as `parse_csv` does on a file; `parse_csv(path)` opens the path with encoding `utf-8-sig` and `newline=""` and delegates to `parse_lines`.
9. Scenario 9 — Happy path: March of the sample in ILS. Given the nine sample transactions, When `monthly_report(transactions, "2026-03")` is called, Then the report has `month` `2026-03`, `base` `ILS`, `count` 7, `income` `Decimal("12925.00")`, `expense` `Decimal("-3025.50")`, `net` `Decimal("9899.50")`, and `categories` is the list of `CategoryTotal(name, total, count)` ordered by absolute total descending: salary 12000.00 (1), rent -1500.00 (1), freelance 925.00 (1), groceries -760.50 (2), software -444.00 (1), travel -321.00 (1).
10. Scenario 10 — Happy path: another base currency. Given the sample, When the report is built with `base="USD"`, Then every amount is converted as `amount × RATES[currency] ÷ RATES[base]` at full Decimal precision before summing, so salary totals `3243.24` and freelance `250.00`, and the report's `base` reads `USD`. `RATES` is a module constant mapping `ILS` → `Decimal("1")`, `USD` → `Decimal("3.70")`, `EUR` → `Decimal("4.00")`.
11. Scenario 11 — Boundary: rounding happens once, after summing, half to even. Given one transaction of 0.05 ILS, When reported in base EUR, Then `income` is `0.01` (the exact 0.0125 rounded once); Given three such transactions, Then `income` is `0.04` (the exact sum 0.0375 rounded once), not `0.03` (three individually rounded cents). Every figure (`income`, `expense`, `net`, each category total) is the exact sum quantized to two places with `ROUND_HALF_EVEN`, independently of the others, so the report does not force them to add up.
12. Scenario 12 — Boundary: two places always. Given transactions of 5 ILS and -2 ILS, When reported, Then `str(income)` is `5.00`, `str(expense)` is `-2.00` and `str(net)` is `3.00`.
13. Scenario 13 — Happy path: top-N. Given the sample, When the report is built with `top=2`, Then `categories` is salary then rent only, while `income`, `expense`, `net` and `count` still cover all seven transactions; a `top` larger than the number of categories keeps them all; `top=None` (the default) keeps them all.
14. Scenario 14 — Edge: ties. Given two categories with equal absolute totals, When reported, Then they are ordered by category name ascending.
15. Scenario 15 — Edge: empty month is a zero report. Given the sample, When the report is built for `2026-05`, Then `count` is 0, `income`, `expense` and `net` are `Decimal("0.00")`, `categories` is empty, and `report.to_dict()` is `{"month": "2026-05", "base": "ILS", "count": 0, "income": "0.00", "expense": "0.00", "net": "0.00", "categories": []}`.
16. Scenario 16 — Edge: only the month's transactions count. Given the sample, When the report is built for `2026-02`, Then `categories` is exactly groceries -99.99 (1).
17. Scenario 17 — Edge: rates are a parameter. Given `rates={"ILS": 1, "USD": 2, "EUR": 4}` as Decimals, When a 10 USD transaction is reported in ILS, Then `income` is `20.00`.
18. Scenario 18 — Error: arguments. When `month` is not `YYYY-MM` with a month of 01–12 (`2026-3`, `2026-13`, `2026-00`, `March 2026`, `202603`, the empty string), Then `ValueError` is raised; when `base` is not a key of `rates`, Then `ValueError`; when `top` is less than 1, Then `ValueError`. These are caller errors, never `LedgerError`.
19. Scenario 19 — Happy path: text report. When `python -m ledger report tests/fixtures/ledger/sample.csv --month 2026-03` runs, Then it exits 0 with nothing on stderr and stdout is exactly these thirteen lines: `month: 2026-03`, `base: ILS`, `transactions: 7`, `income: 12925.00`, `expense: -3025.50`, `net: 9899.50`, `categories:`, then one line per category, indented by two spaces, in report order: `  salary: 12000.00 (1)`, `  rent: -1500.00 (1)`, `  freelance: 925.00 (1)`, `  groceries: -760.50 (2)`, `  software: -444.00 (1)`, `  travel: -321.00 (1)`.
20. Scenario 20 — Happy path: JSON with base and top. When the same command runs with `--base USD --top 1 --json`, Then it exits 0 and stdout parses as the JSON object `{"month": "2026-03", "base": "USD", "count": 7, "income": "3493.24", "expense": "-817.70", "net": "2675.54", "categories": [{"name": "salary", "total": "3243.24", "count": 1}]}` — amounts are strings, so no precision is lost.
21. Scenario 21 — Edge: empty month on the command line. When the command runs with `--month 2026-05`, Then it exits 0 and stdout ends with the lines `income: 0.00`, `expense: 0.00`, `net: 0.00`, `categories: none`.
22. Scenario 22 — Error: usage. When the command line is wrong — no subcommand; `--month` missing; `--month 2026-13`; `--top 0`; `--base GBP`; a FILE that cannot be opened — Then the process exits 2, prints nothing on stdout and a message on stderr. `--base` accepts exactly ILS, USD and EUR and defaults to ILS; `--top` accepts integers of at least 1.
23. Scenario 23 — Error: data. When the FILE has a bad row (`tests/fixtures/ledger/bad_amount.csv`, whose third line carries the amount `-2.505`), Then the process exits 3, prints nothing on stdout and stderr is exactly `error: {FILE}:3: amount '-2.505' has more than 2 decimal places` followed by a newline, FILE being the path as given on the command line.
24. Scenario 24 — Happy path: help. When `python -m ledger report --help` runs, Then it exits 0 and stdout documents `--month`.
25. Scenario 25 — Edge: the tests run the real entry point. Given `tests/test_ledger_cli.py`, When it drives the command, Then it does so through `subprocess` with `[sys.executable, "-m", "ledger", ...]`, relying on the installed package and on no `sys.path` manipulation.
26. Scenario 26 — Setup: the package installs and its tests run. Given a fresh checkout of the work branch, When `pip install -e .` and then `pytest` run from the repository root, Then the install succeeds using only the new root `pyproject.toml` (which discovers packages under `src/` and sets `testpaths = ["tests"]`), pytest collects the `tests/test_ledger_*.py` files and all of them pass, the package declares no runtime dependency, and no file that existed on `main` before the story is changed.

## 6. Dependencies & Constraints (product-level)

- **תנאי הקדם הוחלף בהכרעה:** הסיפור הניח מאגר Python מוכן עם תבנית src ועם pytest. בענף היעד `main` (בקומיט `51b3688`) ובכל הענפים המרוחקים אין קובץ הגדרות פרויקט (`pyproject.toml`, `setup.cfg` או `setup.py`), אין הגדרת pytest, אין `src/` ואין `tests/`, אין תיקיית `.factory/` ואין `.github/workflows`. לכן הסיפור עצמו מוסיף קובץ `pyproject.toml` **חדש** בשורש המאגר (FR11, תרחיש 26). קובץ חדש אינו שינוי של קובץ קיים, ולכן גבול התחום "בלי לשנות קבצים קיימים" נשמר.
- **ספרייה סטנדרטית בלבד:** אין לחבילה תלות צד שלישי בזמן ריצה. ‏backend הבנייה (למשל setuptools) ו-pytest הם כלי בנייה ובדיקה, לא תלויות של החבילה.
- **שערים קבועים:** ILS 1, USD 3.70, EUR 4.00 (ב-ILS ליחידה). לא נשלפים מהרשת.
- **בלי לשנות קבצים קיימים:** הסיפור רק מוסיף קבצים חדשים (`pyproject.toml`, `src/ledger/`, `tests/`). ה-README לא מתעדכן.
- **אין שער בדיקות במאגר:** אין `.factory/testing.md` ואין CI. הבדיקה המוסכמת של הסיפור היא `pip install -e .` ואחריה `pytest` משורש המאגר (תרחיש 26).

## 7. Technical Design (deferred to STRUCTURE)

המבנה הפנימי של החבילה, חלוקת המודולים, אופן הפענוח וטיפול הפרסר בארגומנטים נקבעים בשלב STRUCTURE, וכך גם תוכן `pyproject.toml`: בחירת backend הבנייה, גילוי החבילות תחת `src/` וההגדרה `testpaths`. המגבלות הטכניות שהמוצר מציב כבר מוגדרות בסיפור: `Decimal` לאורך כל הדרך, עיגול אחד לפי `ROUND_HALF_EVEN`, פתיחת הקובץ בקידוד `utf-8-sig` ועם `newline=""`, ובדיקות שורת הפקודה דרך `subprocess`. ‏STRUCTURE גם יחליט באיזה פריט עבודה (כנראה t1, הראשון) נכנס `pyproject.toml`.

## 8. Open Questions

אין שאלות פתוחות. המפתח ביקש שהצוות יכריע בעצמו, וההכרעות הן:

- **Q1 — תשתית Python חסרה:** הוכרע (א). הסיפור מוסיף `pyproject.toml` חדש (FR11, תרחיש 26). *סיכון:* אם סיפור אחר באפיק מתכנן להקים תשתית Python אחרת, ייתכן שיידרש איחוד בהמשך.
- **Q2 — צורות מספר גבוליות:** מספר עשרוני רגיל עם סימן אופציונלי, כולל `+5` ו-`.50`. כתיב מדעי נדחה עם `amount '…' is not a number` (FR9).
- **Q3 — קובץ שאינו UTF-8 תקין:** נחשב כקובץ שאי אפשר לקרוא, ולכן קוד יציאה 2, stdout ריק והודעה ב-stderr (FR8).
- **Q4 — מספר השדות הצפוי:** N הוא מספר השדות בשורת הכותרת, כולל עמודות נוספות (FR10).
- **מקורות האפיק:** מסמך הדרישות וצבר הסיפורים של האפיק לא היו זמינים, ולכן המזהים R1–R5 ו-RK1, RK2 מופיעים כפי שהסיפור מציין אותם, בלי הצלבה.
