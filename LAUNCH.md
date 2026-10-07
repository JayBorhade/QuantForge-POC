# QuantForge — Launch Today

## Fastest path — no Docker (Windows)

**Requirements:** Python 3.12+ and [Node.js 20+](https://nodejs.org/)

```powershell
cd c:\Users\Jay\Desktop\QuantForge
.\scripts\launch-local.ps1
```

Uses SQLite (no PostgreSQL install). Open **http://localhost:3000**

**Or double-click `START.bat`** in the project folder.

### Two windows (recommended)

1. Run `backend\start-api.bat` — wait for startup
2. Run `frontend\start-ui.bat` — wait for “Ready”
3. Open **http://localhost:3000** — sign up with password like `QuantForge1`

---

## With Docker

**Requirements:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### Windows

```powershell
cd c:\Users\Jay\Desktop\QuantForge
.\scripts\launch.ps1
```

### Mac / Linux

```bash
cd QuantForge
chmod +x scripts/launch.sh
./scripts/launch.sh
```

Then open **http://localhost:3000**

---

## What starts

| Service | URL |
|---------|-----|
| Web app | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/api/docs |

First signup creates your account + paper portfolio ($100k).

**Password rules:** 8+ chars, uppercase, lowercase, number (e.g. `QuantForge1`)

---

## Manual launch (no Docker)

### 1. Database

Use Docker only for DB:

```powershell
docker compose up -d postgres redis
```

### 2. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+asyncpg://quantforge:quantforge_secret@localhost:5432/quantforge"
$env:SECRET_KEY="qf-launch-secret-key-change-before-production-2026!!"
$env:JWT_SECRET_KEY="qf-launch-jwt-secret-key-change-before-production!!"
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

---

## Optional: background jobs

```powershell
docker compose --profile workers up -d
```

---

## Before public production

1. Change `SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD` in `.env`
2. Set `APP_ENV=production`, `DEBUG=false`, `COOKIE_SECURE=true`
3. Add real `STRIPE_*` keys for billing
4. Configure SMTP for emails
5. Use HTTPS + reverse proxy (see `docs/DEPLOYMENT.md`)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 3000/8000 in use | Stop other apps or change ports in `docker-compose.yml` |
| Frontend blank | Wait 1–2 min; `docker compose logs frontend` |
| Login fails | Check `docker compose logs backend` |
| CSRF error after login | Hard refresh; clear cookies for localhost |
| DB connection error | `docker compose restart postgres backend` |

```powershell
docker compose logs -f backend
docker compose down
docker compose up -d --build
```
