# AMZ Free Ship Alert — Website

## תיאור
אתר שיווקי לאפליקציית Windows שמנטרת מוצרי Amazon ושולחת התראה בדוא"ל כשמוזהה משלוח חינם לישראל.

## Tech Stack
- **Frontend**: HTML, CSS, JavaScript (static site)
- **Backend**: Vercel Serverless Functions (`api/download.js`, `api/download-count.js`)
- **Analytics**: Vercel Insights
- **Deploy**: Vercel

## Git
- **Remote**: https://github.com/ilan316/Amazon-Free-Shipping-to-Israel-Alert-website.git
- **Branch**: `main`

## Deploy
- `git push origin main` → Vercel מ-deploy אוטומטית מ-main
- בדוק לוגים ב-Vercel dashboard לאחר deploy

## שפה מועדפת
עברית — כל תגובות ומסמכים בעברית

## כללי עבודה
1. **תמיד** להיכנס ל-Plan Mode לפני שינויים
2. **בדוק מקומי** לפני push ל-main
3. לאחר push — בדוק לוגים ב-Vercel
4. אין לעשות force push ל-main

## ריצה מקומית
```bash
npx vercel dev       # מריץ את הפרויקט כולל API routes
# או פשוט:
npx serve .          # עבור frontend בלבד
# או:
python -m http.server 3000
```
