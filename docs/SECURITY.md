# QuantForge Security Hardening Checklist

## Authentication
- [x] bcrypt password hashing
- [x] JWT access tokens (short-lived)
- [x] Rotating refresh tokens with JTI tracking
- [x] httpOnly secure cookies
- [x] 2FA (TOTP) support
- [x] Session/device tracking
- [x] Enforce email verification before live trading

## API Security
- [x] Rate limiting (SlowAPI)
- [x] Input sanitization (bleach)
- [x] Pydantic validation on all endpoints
- [x] SQLAlchemy ORM (SQL injection protection)
- [x] Security response headers
- [x] CORS restricted to explicitly configured origins outside local development
- [x] CSRF double-submit cookie on mutating API requests
- [x] Request IDs and structured request timing/failure logs

## Configuration
- [x] Production/staging fail-fast validation for secret, database, encryption, cookie, CORS, CSRF and debug settings
- [x] Development-only defaults remain isolated to local/test environments
- [x] .env excluded from git and documented as local/secret material
- [x] Production Compose forces APP_ENV=production and DEBUG=false
- [ ] External secrets manager (AWS SM / Vault) for production

## Infrastructure
- [x] Environment variables for secrets
- [x] NGINX rate limiting
- [x] Audit logging
- [x] RBAC (user/admin/superadmin)
- [ ] TLS/HTTPS via Let's Encrypt on VPS
- [ ] Firewall: only 80/443/22 open
- [ ] fail2ban for SSH

## Data
- [x] Broker API secrets encrypted at rest (Fernet)
- [x] Password reset token expiry
- [ ] Database encryption at rest
- [x] Automated PostgreSQL backup helper
- [ ] Off-site backup retention and restore drill

## Deployment
- [x] Production frontend image and Compose stack
- [x] PostgreSQL/Redis readiness checks
- [x] Alembic migrations run before backend startup
- [ ] Generate and store real production secrets
- [ ] TLS certificate installed and auto-renewal tested
- [ ] Firewall configured
- [ ] Database backups verified by restore

## Monitoring
- [x] Structured request logging with request IDs
- [ ] Centralized log aggregation
- [ ] Alerting on failed logins/readiness/worker/reconciliation failures
- [ ] API usage monitoring for admin panel

## Trading validation
- [x] Live execution safety gates (verification + 2FA + risk engine)
- [x] Automated broker reconciliation lifecycle
- [ ] Broker credential/market-data validation (requires provider API keys)
- [ ] Paper-trading soak test
- [ ] Explicit live-trading approval

> Provider API integration validation is intentionally deferred until broker/API credentials are available. No live trading is enabled by this repository hardening work.
