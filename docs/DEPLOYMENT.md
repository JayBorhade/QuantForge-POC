# QuantForge Production Deployment

## Architecture

Production runs PostgreSQL 16, Redis 7, FastAPI, a standalone Next.js frontend, a Celery worker, Celery Beat, and NGINX. Only NGINX is exposed publicly by the production Compose stack.

## 1. Server prerequisites

- Ubuntu 22.04/24.04 LTS
- 4+ GB RAM
- Docker Engine + Compose plugin
- DNS A/AAAA record for the production domain
- Firewall allowing only SSH and HTTP/HTTPS

## 2. Configure secrets

```bash
git clone <your-repo> /opt/quantforge
cd /opt/quantforge
cp .env.example .env
chmod 600 .env
```

Set at minimum: `APP_ENV=production`, `DEBUG=false`, unique `SECRET_KEY`, `JWT_SECRET_KEY`, and `ENCRYPTION_KEY`, `COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax`, production `FRONTEND_URL`/`BACKEND_URL`, a strong `POSTGRES_PASSWORD`, and trusted `CORS_ORIGINS`.

Never commit `.env` or broker credentials.

## 3. Start the production stack

```bash
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml ps
```

The backend applies Alembic migrations before starting. Worker and Beat wait for backend readiness.

## 4. Verify health

```bash
curl -f http://127.0.0.1/health
curl -f http://127.0.0.1/health/ready
docker compose -f docker-compose.production.yml logs --tail=100 backend
docker compose -f docker-compose.production.yml logs --tail=100 celery-worker
```

Readiness checks PostgreSQL and Redis and returns HTTP 503 if either dependency is unavailable.

## 5. HTTPS

The repository NGINX config is HTTP-only so TLS termination can be deployed with your preferred certificate manager or edge proxy. For a direct VPS deployment, terminate TLS at NGINX or an external load balancer and forward traffic to the Compose NGINX service. Do not expose ports 3000, 8000, 5432, or 6379 publicly.

## 6. Backups

Run `chmod +x scripts/backup-postgres.sh` followed by `./scripts/backup-postgres.sh ./backups`. Keep backups off-host as well as locally and test restoration regularly.

Recommended policy: daily full PostgreSQL backup, encrypted off-site copy, appropriate retention, and periodic restore drills.

## 7. Logs and incident debugging

Every API request receives an `X-Request-ID`. Backend logs include request method, path, status, duration, and failures; audit records capture security-sensitive actions.

```bash
docker compose -f docker-compose.production.yml logs -f backend
docker compose -f docker-compose.production.yml logs -f celery-worker celery-beat
```

Forward container stdout/stderr to centralized logging (Loki, ELK, CloudWatch, etc.) and alert on readiness failures, worker crashes, broker reconciliation failures, authentication failures, and database errors.

## 8. Trading safety

Live execution remains gated by verification, 2FA, and the risk engine. Deployment success is not proof that a broker account is ready for live trading.

Before enabling live execution operationally: verify broker credentials and quote connectivity, reconciliation/fill handling, risk limits and kill switch, paper-trading soak tests, monitoring/rollback, and minimal initial notional.

## 9. Upgrade / rollback

```bash
git fetch --all
git checkout <release-tag>
docker compose -f docker-compose.production.yml up -d --build
```

Take a database backup before destructive schema changes. Never manually edit production migration history.

## 10. Security checklist

- [ ] TLS certificate installed and auto-renewal tested
- [ ] Firewall configured
- [ ] SSH key-only access / fail2ban configured
- [ ] Production secrets generated and stored securely
- [ ] Database backups verified by restore
- [ ] Centralized logs and alerts connected
- [ ] Broker credentials validated
- [ ] Paper-trading soak test completed
- [ ] Live trading approval explicitly granted
