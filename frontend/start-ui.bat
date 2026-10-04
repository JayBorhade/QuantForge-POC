@echo off
cd /d "%~dp0"
set NEXT_PUBLIC_API_URL=http://localhost:8000
if not exist node_modules npm install
echo QuantForge UI: http://localhost:3000
npm run dev
pause
