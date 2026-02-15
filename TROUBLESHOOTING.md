# "Failed to fetch" – Troubleshooting

## Quick start (run both together)

From project root:
```powershell
npm install
npm run dev
```
Then open the frontend URL shown (e.g. http://localhost:5173). Close any other dev servers first.

---

Follow these checks if the frontend still cannot reach the backend:

---

## 1. Network – Is the backend running?

**Check:**
```powershell
# PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Expected: `{"status":"healthy"}`

**If it fails:**
- Start the backend: `cd backend` → `.\.venv\Scripts\Activate.ps1` → `uvicorn app.main:app --reload`
- Ensure nothing else is using port 8000

---

## 2. CORS – Is your frontend origin allowed?

**Check:** What URL is the frontend running on? (e.g. `http://localhost:5175`)

The backend allows: `localhost` and `127.0.0.1` on ports 5173–5178.

**If your port is different:**
- Add it to `backend/app/config.py` → `cors_origins`
- Or set `CORS_ORIGINS` in `backend/.env` (comma-separated)

---

## 3. URL – Is the request going to the right place?

**With Vite proxy (dev):**
- Frontend uses relative URLs: `/api/v1/...`
- Vite proxies `/api` → `http://127.0.0.1:8000`
- Ensure you run the app with `npm run dev` (not a static file server)

**If using `VITE_API_URL`:**
- Set to full backend URL: `http://localhost:8000/api/v1`
- CORS must allow your frontend origin (see #2)

**Check in browser DevTools → Network:**
- Request URL should be either:
  - `http://localhost:517X/api/v1/...` (via Vite proxy), or
  - `http://localhost:8000/api/v1/...` (direct)

---

## Quick fix checklist

| Step | Action |
|------|--------|
| 1 | Restart backend: `uvicorn app.main:app --reload --host 0.0.0.0` |
| 2 | Restart frontend: `npm run dev` |
| 3 | Hard refresh browser (Ctrl+Shift+R) |
| 4 | Ensure both run on the same machine |

---

## Verify backend directly

Open in browser:
- http://localhost:8000/health
- http://localhost:8000/docs

If these work but the frontend still fails, the issue is CORS or the proxy URL.
