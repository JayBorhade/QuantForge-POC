# QuantForge Linux VPS Deployment Guide

## Requirements
- Ubuntu 22.04+ LTS
- Docker & Docker Compose
- 4GB+ RAM recommended
- Domain with DNS A record

## 1. Server Setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git nginx certbot
sudo usermod -aG docker $USER
```

## 2. Clone & Configure

```bash
git clone <your-repo> /opt/quantforge
cd /opt/quantforge
cp .env.example .env
nano .env  # Set production secrets
```

Required production values:
- `APP_ENV=production`
- `DEBUG=false`
- `SECRET_KEY` — 64+ char random string
- `JWT_SECRET_KEY` — 64+ char random string
- `COOKIE_SECURE=true`
- `FRONTEND_URL=https://yourdomain.com`
- Strong `POSTGRES_PASSWORD`

## 3. SSL with Certbot

```bash
sudo certbot certonly --standalone -d yourdomain.com
```

Mount certs in NGINX config for HTTPS.

## 4. Deploy

```bash
docker compose -f docker-compose.yml up -d --build
docker compose exec backend alembic upgrade head
```

## 5. Verify

- https://yourdomain.com — Frontend
- https://yourdomain.com/api/docs — API documentation
- `docker compose ps` — All services healthy

## 6. Maintenance

```bash
# View logs
docker compose logs -f backend

# Restart services
docker compose restart

# Backup database
docker compose exec postgres pg_dump -U quantforge quantforge > backup.sql
```
