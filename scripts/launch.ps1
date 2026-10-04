# QuantForge — one-command launch (Windows)
# Requires: Docker Desktop running

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QuantForge Launch" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual launch (no Docker):" -ForegroundColor Yellow
    Write-Host "  1. Start PostgreSQL + Redis locally"
    Write-Host "  2. cd backend; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    Write-Host "  3. uvicorn app.main:app --reload --port 8000"
    Write-Host "  4. cd frontend; npm install; npm run dev"
    exit 1
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Yellow
}

Write-Host "Building and starting services (first run may take 5-10 min)..." -ForegroundColor Green
docker compose down 2>$null
docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker compose failed. Check Docker Desktop is running." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for API health..." -ForegroundColor Gray
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Seconds 3 }
}
if (-not $ready) {
    Write-Host "Backend slow to start. Check: docker compose logs backend" -ForegroundColor Yellow
} else {
    Write-Host "Backend is healthy." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  QuantForge is LIVE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  App:      http://localhost:3000" -ForegroundColor White
Write-Host "  API:      http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""
Write-Host "  1. Open http://localhost:3000" -ForegroundColor Gray
Write-Host "  2. Sign up (password needs upper, lower, number)" -ForegroundColor Gray
Write-Host "  3. Explore dashboard" -ForegroundColor Gray
Write-Host ""
Write-Host "  Logs:    docker compose logs -f" -ForegroundColor Gray
Write-Host "  Stop:    docker compose down" -ForegroundColor Gray
Write-Host "  Celery:  docker compose --profile workers up -d" -ForegroundColor Gray
Write-Host ""
