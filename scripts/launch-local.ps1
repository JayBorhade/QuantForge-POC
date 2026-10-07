# QuantForge — local launch WITHOUT Docker (SQLite + in-process tasks)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QuantForge Local Launch (no Docker)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$VenvPip = Join-Path $BackendDir "venv\Scripts\pip.exe"

# Backend venv
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python venv..." -ForegroundColor Gray
    Set-Location $BackendDir
    python -m venv venv
    Set-Location $Root
}

Write-Host "Installing backend dependencies..." -ForegroundColor Gray
& $VenvPip install -q -r (Join-Path $BackendDir "requirements.txt")

$env:DATABASE_URL = "sqlite+aiosqlite:///$BackendDir/quantforge.db"
$env:SECRET_KEY = "qf-launch-secret-key-change-before-production-2026!!"
$env:JWT_SECRET_KEY = "qf-launch-jwt-secret-key-change-before-production!!"
$env:FRONTEND_URL = "http://localhost:3000"
$env:BACKEND_URL = "http://localhost:8000"
$env:CSRF_ENABLED = "true"
$env:CELERY_ALWAYS_EAGER = "true"
$env:REDIS_URL = "redis://localhost:6379/0"

# Start backend
Write-Host "Starting API on http://localhost:8000 ..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    param($py, $dir)
    Set-Location $dir
    $env:DATABASE_URL = "sqlite+aiosqlite:///$dir/quantforge.db"
    $env:SECRET_KEY = "qf-launch-secret-key-change-before-production-2026!!"
    $env:JWT_SECRET_KEY = "qf-launch-jwt-secret-key-change-before-production!!"
    $env:FRONTEND_URL = "http://localhost:3000"
    $env:CSRF_ENABLED = "true"
    & $py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $VenvPython, $BackendDir

Start-Sleep -Seconds 5
try {
    $h = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "Backend healthy." -ForegroundColor Green
} catch {
    Write-Host "Backend starting (check logs if issues)..." -ForegroundColor Yellow
    Receive-Job $backendJob -Keep | Select-Object -Last 15
}

# Frontend
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Gray
    Set-Location $FrontendDir
    if (-not (Test-Path "node_modules")) { npm install }
    $env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  API:  http://localhost:8000" -ForegroundColor White
    Write-Host "  Docs: http://localhost:8000/api/docs" -ForegroundColor White
    Write-Host "  App:  http://localhost:3000 (starting...)" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop frontend. Backend runs in background job." -ForegroundColor Gray
    Write-Host "Stop backend: Get-Job | Stop-Job; Get-Job | Remove-Job" -ForegroundColor Gray
    Write-Host ""
    npm run dev
} else {
    Write-Host ""
    Write-Host "Node.js/npm not found. Install from https://nodejs.org/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Backend is running:" -ForegroundColor Green
    Write-Host "  http://localhost:8000" -ForegroundColor White
    Write-Host "  http://localhost:8000/api/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "After installing Node, run:" -ForegroundColor Gray
    Write-Host "  cd frontend" -ForegroundColor Gray
    Write-Host "  npm install && npm run dev" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Backend job ID: $($backendJob.Id) — Stop-Job $($backendJob.Id)" -ForegroundColor Gray
}
