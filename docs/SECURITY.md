# QuantForge Security Hardening Checklist

## Authentication
- [x] bcrypt password hashing
- [x] JWT access tokens (short-lived)
- [x] Rotating refresh tokens with JTI tracking
- [x] httpOnly secure cookies
- [x] 2FA (TOTP) support
- [x] Session/device tracking
- [ ] Enforce email verification before live trading

## API Security
- [x] Rate limiting (SlowAPI)
- [x] Input sanitization (bleach)
- [x] Pydantic validation on all endpoints
- [x] SQLAlchemy ORM (SQL injection protection)
- [x] Security response headers
- [x] CORS restricted to frontend origin
- [x] CSRF double-submit cookie on mutating API requests

## Infrastructure
- [x] Environment variables for secrets
- [x] .env excluded from git
- [x] NGINX rate limiting
- [x] Audit logging
- [x] RBAC (user/admin/superadmin)
- [ ] TLS/HTTPS via Let's Encrypt on VPS
- [ ] Secrets manager (AWS SM / Vault) for production

## Data
- [x] Broker API secrets encrypted at rest (Fernet)
- [x] Password reset token expiry
- [ ] Database encryption at rest
- [ ] Regular automated backups

## Deployment
- [ ] Change all default secrets in `.env`
- [ ] Set `APP_ENV=production`, `DEBUG=false`
- [ ] Enable `COOKIE_SECURE=true`
- [ ] Firewall: only 80/443/22 open
- [ ] Disable debug endpoints
- [ ] Configure fail2ban for SSH

## Monitoring
- [ ] Centralized logging (ELK / Loki)
- [ ] Alerting on failed logins
- [ ] API usage monitoring for admin panel
