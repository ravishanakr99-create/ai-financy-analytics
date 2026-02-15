# Quick Start – Eligibility Report

## What changed

The frontend is now configured to call the backend **directly** at `http://127.0.0.1:8000`, which avoids Vite proxy issues.

---

## Steps

### 1. Close other dev servers

Close any terminals running:
- Other Vite/React apps (e.g. Freelance Marketplace)
- Other uvicorn/FastAPI apps

They can block ports and cause conflicts.

### 2. Start the app

From the project folder, run:

```powershell
.\start.ps1
```

This opens two terminals (backend and frontend).

### 3. Open the app

Open **http://localhost:3000** in your browser (or the URL shown in the frontend terminal if 3000 is in use).

### 4. Hard refresh

Press **Ctrl+Shift+R** to avoid cached JavaScript.

---

## Manual start (alternative)

**Terminal 1 – backend:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0
```

**Terminal 2 – frontend:**
```powershell
cd frontend
npm run dev
```

---

## Verify

- Backend: http://127.0.0.1:8000/docs
- Frontend: URL shown in the frontend terminal

If the page shows "Backend: ✓ Connected", the connection is working.
