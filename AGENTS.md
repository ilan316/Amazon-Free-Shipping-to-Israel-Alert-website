# AMZ Free Ship Alert — Website (www.amzfreeil.com)

> ⚠️ קובץ זה זהה ל-`CLAUDE.md` / `AGENTS.md` באותה תיקייה. כל עדכון חייב להיכתב **בשני הקבצים**.

## תיאור
האתר השיווקי + הבלוג של השירות שמנטר מוצרי Amazon ומתריע במייל על משלוח חינם לישראל.
**השירות web-only** — אין אפליקציית Windows (הוסרה). `web-guide.html` הוא המדריך היחיד.
הדשבורד והבאקאנד יושבים בפרויקט נפרד (`Amazon Free Shipping to Israel Alert SaaS` → `app.amzfreeil.com`).

## Tech Stack
- **Frontend:** HTML/CSS/JS סטטי, RTL
- **Serverless:** Vercel Functions (`api/`)
- **Analytics:** Vercel Insights + Speed Insights
- **Deploy:** Vercel (CLI מחובר ישירות)

## מבנה קבצים
| נתיב | תפקיד |
|---|---|
| `index.html`, `about.html`, `prices.html`, `search.html`, `free-products.html` | דפי הליבה |
| `blog/` | ~200 פוסטים וסקירות |
| `tools/build-internal-links.js` | **מייצר** את בלוקי הקישורים הפנימיים וה-PICKS בתוך ה-HTML |
| `generate-sitemap.js` | מייצר את `sitemap.xml` |
| `.github/workflows/` | Action שמריץ את שני הגנרטורים בכל פרסום דראפט |
| `vercel.json` | headers + redirects + קאשינג |
| `llms.txt`, `llms-full.txt`, `robots.txt` | הזנת מנועי AI |

## ⚠️ ה-HTML נוצר אוטומטית
בלוקי הקישורים הפנימיים, ה-PICKS וה-sitemap נכתבים ע"י `build-internal-links.js` ו-`generate-sitemap.js`, שרצים ב-GitHub Action בכל פרסום דראפט.
**עריכה ידנית של הבלוקים האלה מתבטלת בריצה הבאה — לתקן את הגנרטור.**
ה-sitemap מתעדכן ב-repo הזה, לא בבאקאנד.

## מלכודות ב-`vercel.json`
- **בלוק `routes` מבטל בשקט את `headers` ואת `redirects`.** הוא נמחק ב-26/07 (`69edb08`) ואסור להחזיר. ה-CSP חי — כל origin חיצוני חדש מחייב עדכון CSP.
- **קאשינג:** `css`/`js` = `must-revalidate`. תמונות ופונטים = `immutable` לשנה **עם שמות לא-hashed** — זו מלכודת: שינוי תמונה בלי שינוי שם לא יגיע למשתמשים.

## Git ו-Deploy
- **Remote:** https://github.com/ilan316/Amazon-Free-Shipping-to-Israel-Alert-website.git · branch `main`
- `git push origin main` → Vercel פורסת אוטומטית
- **זו תיקיית העבודה היחידה של האתר.** ב-07/09/2026 אוחדו שני עותקי עבודה: העותק שהיה תקוע ב-30/08 נמחק, והעותק החי (`amzfreeil-www/`) שונה לשם הזה. אין יותר תיקייה כפולה.

## ריצה מקומית
```bash
npx vercel dev       # כולל api/
npx serve .          # frontend בלבד
```

## כתיבת פוסטי בלוג
- עברית פשוטה לקהל רחב — בלי ז'רגון לועזי לא-מוכר.
- **אסור לכתוב מחירים או נתונים לא מאומתים** — רק "בדוק מחיר נוכחי ←".
- מוצרי חשמל/אלקטרוניקה — **חובה** אזהרת מתח/תקע 110V מול 230V בישראל.
- ביטויים באנגלית בכותרות RTL — לעטוף ב-`<bdi>`.
- **מיסים:** סף הפטור הוא **$75** (לא $130). עד $75 פטור מלא ממכס+מע"מ. **אין לציין אחוזים** (המע"מ משתנה). סף משלוח חינם = $49.

## שפה מועדפת
עברית — כל התגובות והמסמכים בעברית.

## כללי עבודה
1. תמיד להיכנס ל-**Plan Mode** לפני שינויים
2. לבדוק מקומית לפני push
3. אחרי כל שינוי: `git status` → `git add` → `git commit` → `git push`
4. אחרי deploy — לבדוק לוגים ב-Vercel
5. אין `force push` ל-`main`

## ⛔ אסור בלי אישור מפורש
- **אין לגעת ב-`vercel.json` בלי אישור** — במיוחד לא להחזיר `routes` ולא לשנות קאשינג.
- **אין לגעת בצבע המותג.** ניגודיות של טקסט קטן תוקנה (`d6ddd06`); כותרות הירו, מספרים גדולים ו-hover **נפסלו לצמיתות**.
- **backlinks ופנייה לתקשורת נפסלו לצמיתות (17/08/26)** — לא להעלות שוב. הצמיחה היא בפייסבוק/טלגרם.
- **אין לשנות SEO בדפי הסקירה.** נסגר 28/07/26: noindex, הסרת בלוקים, סף תוכן וחיבור בולטים — כולם נפסלו או נמדדו ככישלון. **לא להעלות שוב.**
- **BOM באמצע קובץ CSS שובר את `:root{}` בשקט** — כל המשתנים נופלים. לשמור UTF-8 בלי BOM.
- **ציון Performance במובייל רועד 61/72/88 בין הרצות ללא שינוי קוד** — לדווח רק על חציון של 3 הרצות ודלתא ≥15 נקודות. לא להמציא אבחנות לרעש.
