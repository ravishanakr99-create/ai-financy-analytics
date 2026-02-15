# API Connection Diagnostic Guide

## Step 1: Verify Backend Status

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

**Expected:** `{"status":"healthy"}`

**If it fails:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0
```

---

## Step 2: Frontend baseURL Configuration

| Mode | VITE_API_URL | baseURL | When to use |
|------|--------------|---------|-------------|
| **Proxy (default)** | empty / unset | `/api/v1` | Dev – Vite proxies to backend |
| **Direct** | `http://127.0.0.1:8000/api/v1` | that URL | Dev – if proxy fails; requires CORS |
| **Production** | `https://api.example.com/api/v1` | that URL | Deployed app |

**Correct setup in `frontend/.env`:**
```
# Proxy mode (recommended for dev) – leave empty or omit
# VITE_API_URL=

# Direct mode (if proxy fails)
# VITE_API_URL=http://127.0.0.1:8000/api/v1
```

---

## Step 3: CORS

CORS applies only when the frontend calls the backend directly (VITE_API_URL set).

**Allowed origins:** `localhost` and `127.0.0.1` on ports 5173–5180.

**If your frontend runs on a different port:** Add it to `backend/app/config.py` → `cors_origins`, or set `CORS_ORIGINS` in `backend/.env`.

---

## Step 4: Axios Configuration

The Axios instance in `frontend/src/api/client.js`:

```js
baseURL: import.meta.env.VITE_API_URL || '/api/v1'
```

- No `VITE_API_URL` → relative `/api/v1` (same-origin, Vite proxy)
- With `VITE_API_URL` → full URL (direct backend, CORS)

---

## Step 5: .env-Based Solution (Permanent)

**`frontend/.env` (create if missing):**
```env
# Dev: proxy mode (recommended)
# Leave empty – requests go through Vite proxy

# Dev: direct mode (if proxy fails)
# VITE_API_URL=http://127.0.0.1:8000/api/v1

# Production
# VITE_API_URL=https://your-api.com/api/v1
```

**`frontend/.env.example`** documents these options.

**Important:** Restart the frontend (`npm run dev`) after changing `.env`.

---

## Quick Checklist

| # | Check |
|---|-------|
| 1 | Backend running: `http://127.0.0.1:8000/health` returns OK |
| 2 | Frontend `.env` has no `VITE_API_URL` (or correct direct URL) |
| 3 | Run both: `npm run dev` from project root |
| 4 | Open frontend URL shown in terminal (e.g. http://localhost:5180) |
| 5 | Hard refresh: Ctrl+Shift+R |
