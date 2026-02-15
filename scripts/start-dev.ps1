# Start backend and frontend for development
# Run from project root: .\scripts\start-dev.ps1

$ErrorActionPreference = "Stop"
$BackendPath = Join-Path $PSScriptRoot "..\backend"
$FrontendPath = Join-Path $PSScriptRoot "..\frontend"

Write-Host "Starting backend (http://127.0.0.1:8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BackendPath'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 0.0.0.0"

Start-Sleep -Seconds 3

Write-Host "Starting frontend (Vite dev server)..." -ForegroundColor Cyan  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FrontendPath'; npm run dev"

Write-Host "`nBoth servers starting. Check the new windows for URLs." -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "Frontend: http://localhost:5173 (or next available port)" -ForegroundColor Yellow
