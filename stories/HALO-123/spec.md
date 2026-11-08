# טיוטת כרטיס — HALO-123 (בהמתנה לתשובות)

### OPS — מופעי מפתחי Halo מורשים לערוך את Jira ומסומנים כמופעים שאינם של הראל

| שדה | ערך |
| --- | --- |
| סיפור משתמש | בתור מפתחי הסיפור "התחלה בלחיצה אחת ב-Jira למפתחי Halo", אנחנו רוצים שכל פריסה תאמר אם היא מופע הראל, ושלחשבון השירות של Jira במופעי מפתחי Halo יהיו הרשאות עריכה, כדי שהכפתור יעבוד שם והקישור יוצג בהראל. |
| הקשר ותיאור | בתוך הסיפור: הגדרה בכל פריסה שאומרת אם היא מופע הראל, ובמופעי מפתחי Halo הרשאה לחשבון השירות של Jira לערוך תוויות, לשנות אחראי ולהעביר סיפורים ל-In Progress. מחוץ לסיפור: הרשאות עריכה במופע של הראל. |
| עוקב אחר | FR-12, FR-13 |
| עדיפות | Should |
| גודל | S (כ-2 נקודות) |
| חוסמים | אין |
| תלוי ב- | — |

קריטריוני קבלה

1. תרחיש 1: מסלול תקין — ההגדרה קיימת בכל פריסה. **בהינתן** כל פריסה פעילה של Halo, **כאשר** בודקים את ההגדרות שלה, **אז** יש בה הגדרה שאומרת במפורש אם זה מופע הראל, **וגם** במופע של הראל היא אומרת "כן" ובמופעי מפתחי Halo "לא".
2. תרחיש 2: מסלול תקין — הרשאות העריכה במופעי מפתחי Halo. **בהינתן** חשבון השירות של Jira במופע של מפתחי Halo, **כאשר** בודקים את הרשאותיו בפרויקט ה-Jira שלו, **אז** הוא יכול להוסיף תווית לסיפור, לשנות את האחראי ולהעביר סיפור ל-In Progress.
3. תרחיש 3: גבול התחום — מופע הראל לא משתנה. **בהינתן** המופע של הראל, **כאשר** בודקים את חשבון השירות של Jira שלו, **אז** הרשאותיו זהות להרשאות שלפני הסיפור, **וגם** הוא עדיין קורא תוויות, סטטוס ואחראי של סיפורים.

## Open points before this becomes a spec
- AC1: the list of active deployments and the value each must carry; whether a missing value stops the deployment.
- AC2: what the repository delivers (runbook, read-only permission check, or both) and who grants the permissions in which Jira site/project.
- AC3: the observable baseline for "identical permissions" on Harel.
- Target repository (single-repo rule) and the split with HALO-126 for backend read / API exposure of the setting.
