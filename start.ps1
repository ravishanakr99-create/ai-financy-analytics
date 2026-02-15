# One-click start - Run from project root
# Close other terminals using ports 8000/5173 first if you get "port in use"

Write-Host "Starting backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\.venv\Scripts\Activate.ps1; Write-Host 'Backend starting...' -ForegroundColor Green; uvicorn app.main:app --reload --host 0.0.0.0" -PassThru

Start-Sleep -Seconds 4

Write-Host "Starting frontend..." -ForegroundColor Cyan
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; Write-Host 'Frontend starting...' -ForegroundColor Green; npm run dev" -PassThru

Write-Host "`nDone. Two windows opened." -ForegroundColor Green
Write-Host "  Backend:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3000 (or next port if 3000 is in use)" -ForegroundColor White
Write-Host "`nFrontend uses DIRECT backend URL: http://127.0.0.1:8000" -ForegroundColor Gray
