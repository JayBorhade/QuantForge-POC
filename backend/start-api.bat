@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
set DATABASE_URL=sqlite+aiosqlite:///./quantforge.db
for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set SECRET_KEY=%%i
for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set JWT_SECRET_KEY=%%i
set FRONTEND_URL=http://localhost:3000
set CELERY_ALWAYS_EAGER=true
echo QuantForge API: http://localhost:8000
echo Docs: http://localhost:8000/api/docs
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
