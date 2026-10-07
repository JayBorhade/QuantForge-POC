# QuantForge Windows Setup Script
$ErrorActionPreference = "Stop"

Write-Host "=== QuantForge Setup ===" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

Write-Host "Starting PostgreSQL and Redis..."
docker compose up -d postgres redis

Start-Sleep -Seconds 8

Write-Host "Installing backend dependencies..."
Set-Location backend
python -m venv venv
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Set-Location ..

Write-Host "Installing frontend dependencies..."
Set-Location frontend
npm install
Set-Location ..

Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host "Start all services: docker compose up"
Write-Host "Frontend: http://localhost:3000"
Write-Host "API docs: http://localhost:8000/api/docs"
