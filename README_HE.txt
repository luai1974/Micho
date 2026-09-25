גרסה 2 — ניהול עובדים ושכר — מוכנה ל-Render

מה נוסף:
- PostgreSQL לפריסה אונליין
- Gunicorn
- CSRF protection
- Cookies מאובטחים בפרודקשן
- סיסמאות Hash
- הרשאות מנהל/עובד
- SECRET_KEY כמשתנה סביבה
- ADMIN_PASSWORD אינו נמצא בקוד
- render.yaml לפריסה
- health endpoint

פריסה:
1. העלה את כל התיקייה ל-GitHub.
2. ב-Render בחר New > Blueprint וחבר את ה-repository.
3. Render יקרא את render.yaml וייצור Web Service + PostgreSQL.
4. כאשר תתבקש להזין ADMIN_PASSWORD, בחר סיסמת מנהל חזקה.
5. לאחר סיום הפריסה פתח את כתובת onrender.com.
6. שם המשתמש למנהל הוא admin (אלא אם שינית ADMIN_USERNAME).

חשוב:
- אין סיסמת מנהל ברירת מחדל בגרסה זו. היא חייבת להיות מוגדרת ב-Render.
- לפרודקשן אמיתי עם נתוני שכר מומלץ להשתמש בתוכנית PostgreSQL עם מדיניות גיבויים מתאימה.
- מחיקת עובד מוחקת גם את רשומות השעות והמפרעות שלו.
