@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
set DATABASE_URL=sqlite+aiosqlite:///./quantforge.db
set SECRET_KEY=qf-launch-secret-key-change-before-production-2026!!
set JWT_SECRET_KEY=qf-launch-jwt-secret-key-change-before-production!!
set FRONTEND_URL=http://localhost:3000
set CELERY_ALWAYS_EAGER=true
echo QuantForge API: http://localhost:8000
echo Docs: http://localhost:8000/api/docs
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
