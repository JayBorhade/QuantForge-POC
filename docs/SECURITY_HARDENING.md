# QuantForge Security Hardening Status

This document records source-level controls added during the security-hardening batch. It is not a penetration-test certificate; deployment, provider, and database behavior still require staging validation.

## Controls

| Area | Current control | Status / remaining validation |
|---|---|---|
| SQL injection | SQLAlchemy ORM and bound parameters are the standard data-access path. | Static review did not find user-controlled SQL interpolation in the sampled paths; keep query review in CI/reviews. |
| XSS | React text rendering escapes values; no dangerouslySetInnerHTML or upload surface was found in the source search. Browser testing is still required. | Implemented baseline; test user-controlled strategy names, logs, and notifications in staging. |
| CSRF | Signed double-submit token, constant-time comparison, and exact-path exemptions. | Implemented; validate cookie/domain behavior behind the production proxy. |
| File uploads | No application upload endpoint currently exists. | Not applicable to current routes; any future upload must enforce size/type limits, random names, storage isolation, and malware scanning where appropriate. |
| IDOR/BOLA | User-owned resource queries should include the authenticated owner; admin APIs use server-side dependencies. | Route-by-route cross-user tests remain required; do not rely on UI visibility. |
| Rate limiting | Global limits plus tighter limits on signup/login/refresh/password recovery/email verification/2FA; Redis-backed storage outside local/test. | Implemented in source; verify Redis reachability and limits across multiple replicas in staging. |
| JWT secrets | HS256 is the only accepted algorithm; production/staging require distinct, high-entropy, non-placeholder secrets. | Implemented; rotate any real secrets ever committed or shared. |
| Exposed API secrets | Local launch scripts generate fresh local secrets; committed examples contain placeholders only. | No provider credentials should be committed; use secret-manager/environment injection. |
| Password hashing | New passwords use SHA-256 pre-hashing plus salted bcrypt to avoid bcrypt's 72-byte truncation; legacy bcrypt hashes are verified and upgraded on successful login. | Implemented with regression tests. |
| MFA | TOTP is available; admin access now requires MFA. | Implemented for admins; ordinary users can enable MFA. TOTP seed is currently stored in plaintext in the database; encrypt it with a schema migration before production. Test recovery and account-support procedures. |
| CORS | Exact configured origins, explicit methods/headers; non-local environments require HTTPS origins. | Implemented; verify the real production origin list. |
| Auth token storage | Access/refresh tokens use HttpOnly cookies; API responses no longer return the access token; refresh reads only the HttpOnly cookie. | Implemented; browser storage should contain no auth tokens. |
| Client-side authorization | Backend dependencies enforce authentication, verified-email requirements, role checks, and admin MFA. | Server is authoritative; continue testing every sensitive route directly. |
| Database row-level security | The application currently uses application-layer ownership checks; PostgreSQL RLS policies are not configured. | NOT IMPLEMENTED. RLS requires a deliberate tenant/session-context design covering API requests, Celery tasks, migrations, and admin workflows before enabling it safely. |
| Webhook signatures | Stripe events are passed through the provider signature verifier before processing, with event idempotency. | Implemented in source; test replay, invalid signatures, and secret rotation in Stripe test mode. |
| SSRF | No user-controlled arbitrary-URL fetch endpoint was identified in the reviewed paths; Next image optimization no longer allows every HTTPS hostname. | Implemented baseline; review any future URL-fetching integrations and broker/provider allowlists. |
| Source maps | Next production browser source maps are explicitly disabled. | Implemented; inspect deployed artifacts/CDN after build. |
| Default credentials | Local Compose service ports bind to loopback; production Compose requires explicit database credentials. Local launchers generate random secrets. | Implemented baseline; change any reused credentials and keep production services private. |
| Sensitive logs | Billing failures return generic client errors rather than raw provider exception text; request logs avoid bodies and tokens. | Implemented baseline; inspect provider logs and audit-log retention in staging. |
| Vulnerable dependencies | Replaced python-jose 3.3.0 with PyJWT 2.15.1; raised Next.js/React minimum versions to patched security releases; updated aiohttp. CodeQL, Dependabot, pip-audit, and npm audit are configured. | Audit jobs must pass and dependency update PRs must be reviewed before release. |

## Release gates

- Keep .env, broker API keys, Stripe secrets, database credentials, and encryption keys out of Git.
- Use HTTPS, trusted proxy configuration, secure cookies, and an exact production CORS allowlist.
- Validate CSRF, MFA, cross-user object access, webhook replay/signature handling, and rate limits in an isolated staging environment.
- Confirm backups, key rotation, incident response, and audit-log access policy.
- Do not enable real-money trading until broker credentials, risk limits, order reconciliation, and kill-switch behavior have been independently tested.