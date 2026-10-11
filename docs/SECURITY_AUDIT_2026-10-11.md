# QuantForge Security Audit — 2026-10-11

## Scope and method

This is a source-level review of the QuantForge repository and the proposed security-hardening changes in PR #54. It is not a live penetration test, a deployed-site scan, or a security certification. No production credentials, live broker orders, or production provider operations were used. Findings below distinguish code controls from items that still need route-by-route, staging, or deployment verification.

Reviewed areas include FastAPI middleware and auth dependencies, token/password/CSRF helpers, the user model, billing/webhook handlers, Docker Compose, Next.js configuration, dependency manifests, the security checklist, and the proposed PR #54 diff.

## Executive result

**Release status: NOT READY FOR PRODUCTION until the blockers below are resolved and verified.**

PR #54 contains substantial hardening changes, but it remains unmerged. The current main branch still has older code in some of the reviewed areas (including permissive CORS methods/headers, the older JWT/password stack, and default local Compose credentials/host bindings). Do not assume PR #54 protections are present in a deployed build until the PR is reviewed, merged, deployed, and re-tested.

Highest-priority remaining gates:
1. PostgreSQL row-level security is not implemented; enabling it safely requires a reviewed request/worker/webhook context design and PostgreSQL isolation tests.
2. The existing main branch stores TOTP/MFA seeds in plaintext. PR #54 now includes an encryption helper and Alembic data migration; this proposed migration must pass CI and be applied with the correct ENCRYPTION_KEY in staging before the risk can be considered closed.
3. Route-by-route IDOR/BOLA adversarial tests are not complete.
4. Stripe signature/replay/idempotency, Redis-backed rate limits, cookie/proxy/TLS, SMTP, and broker flows require staging validation.
5. Earlier commits passed backend/frontend CI, the PostgreSQL migration baseline, CodeQL for Python and JavaScript/TypeScript, and dependency audit. The current candidate additionally adds hashed/expiring password-reset and email-verification tokens, a token migration, refresh-session row locking/account-state checks, TOTP replay-step tracking and single-use recovery codes, enumeration-safe signup, and cookie-authenticated WebSockets with origin and per-user connection limits. CI and migration workflows have been queued for the latest candidate and must finish successfully before merge. Full npm audit has a documented development-tooling residual.

## 20-check assessment

| # | Check | Source-review result | Status / required action |
|---:|---|---|---|
| 1 | SQL injection | SQLAlchemy ORM/bound parameters are the standard pattern in sampled data-access code; no confirmed user-controlled SQL interpolation was established in this bounded review. | **Partially verified** — search all raw SQL/text() uses and test any dynamic identifiers/filters. |
| 2 | Cross-site scripting (XSS) | React's normal text rendering escapes values; source search in the PR notes did not identify dangerouslySetInnerHTML. | **Baseline present; runtime test needed** — exercise strategy names, logs, notifications, errors, and all user-controlled text in a browser. |
| 3 | CSRF | PR #54 introduces a signed double-submit token, constant-time comparison, and exact-path exemptions. The latest branch removes cookie-authenticated `/auth/refresh` from the exemption list and adds a regression test. The unauthenticated `/auth/resend-verification` endpoint remains exempt because it does not rely on a logged-in browser session. Main has an older unsigned equality-only implementation. | **Fix proposed, not on main** — verify login/refresh/logout and all cookie-authenticated mutations behind the real proxy. |
| 4 | Insecure file uploads | No application upload endpoint was identified in the reviewed route surface. | **Not applicable to current feature surface** — do not add uploads without strict size/type/content validation, random names, isolated storage, and scanning appropriate to the file type. |
| 5 | IDOR / broken object-level authorization | The app uses authenticated-user dependencies and ownership checks in sampled routes. | **Open release gate** — add adversarial two-user tests for every resource ID and verify read, update, delete, export, websocket, and nested-resource paths. |
| 6 | Missing rate limiting | Global SlowAPI limiting exists; PR #54 adds tighter IP limits and this candidate adds distributed Redis-backed per-account limits for signup, login, reset, and verification actions outside local/test. Refresh tokens are row-locked during rotation; reset/verification tokens are hashed at rest, verification tokens expire after 24 hours, and TOTP steps are recorded to prevent code replay. WebSockets now use the HttpOnly access cookie, exact configured-origin checks, an active server-side session, and a per-user connection cap. | **Fix proposed, runtime validation needed** — account and IP limits fail closed when Redis is unavailable outside local/test; test 429 behavior across replicas and verify Redis availability in staging. |
| 7 | Insecure JWT secrets/algorithm | Main accepts configured algorithm and contains development defaults; PR #54 constrains JWT to HS256 and validates distinct high-entropy non-placeholder production secrets. | **Fix proposed, not on main** — rotate any exposed secrets and verify production config fails closed. |
| 8 | Exposed API secrets | .env is ignored and examples use placeholders; PR #54 adds randomized local launcher secrets and removes raw provider error responses. | **Partial** — scan all history and artifacts for credentials; rotate anything ever committed. Inject production secrets via a secret manager/environment and never expose them to frontend variables. |
| 9 | Weak password hashing | Main uses direct bcrypt; PR #54 uses SHA-256 pre-hashing plus bcrypt to avoid 72-byte truncation and upgrades legacy bcrypt hashes after successful login. | **Fix proposed, not on main** — validate migration/rehash behavior and password-reset/session-revocation tests. |
| 10 | Missing MFA | TOTP support exists; PR #54 requires MFA for admin routes. This branch adds version-marked encryption for TOTP seeds, a data migration for existing values, per-account replay-step tracking, and hashed single-use recovery codes. | **Partial** — admin enforcement is proposed; ordinary-user MFA is opt-in. Validate the migration with the deployment encryption key and test existing MFA accounts in staging. |
| 11 | Overly permissive CORS | Main allows all methods and headers. PR #54 uses explicit method/header allowlists and configured origins. | **Confirmed on main; fix proposed** — verify exact deployed origin list and ensure credentials are never combined with wildcard origins. |
| 12 | Auth tokens in local storage | The reviewed frontend API uses credentialed cookies and reads only the CSRF cookie; PR #54 removes access tokens from JSON responses, refreshes only from HttpOnly cookies, and the WebSocket client no longer places access tokens in query strings. | **Fix proposed / verify whole frontend** — search all frontend storage and network paths for access/refresh tokens, and confirm cookies are Secure in production. |
| 13 | Client-side-only permission enforcement | Backend auth/verified-user/admin dependencies exist; PR #54 adds admin MFA enforcement. | **Baseline present; route coverage open** — test protected APIs directly without the UI, including WebSockets and all admin/financial actions. |
| 14 | Missing row-level security (RLS) | No PostgreSQL RLS policies or tenant session-context design are present. | **Confirmed blocker** — implement and test policies covering API requests, background workers, and admin/migration flows before marking complete. Application-level ownership checks alone are not RLS. |
| 15 | Unverified webhook signatures | Stripe webhook handler calls a provider signature-verification helper before processing and records event IDs for idempotency in the proposed code. | **Fix proposed / staging required** — test missing/invalid signatures, replayed IDs, retries, out-of-order events, and secret rotation in Stripe test mode. |
| 16 | SSRF | No arbitrary user-supplied URL-fetch route was identified in the sampled paths; PR #54 removes unrestricted Next.js remote image host configuration. | **Baseline only** — review every URL-fetching integration and enforce host allowlists, DNS/IP checks, redirect controls, and private/link-local address blocking where applicable. |
| 17 | Exposed source maps | PR #54 explicitly disables production browser source maps. | **Fix proposed / artifact verification required** — inspect production build and CDN for .map files before release. |
| 18 | Default credentials | Main Compose defaults to quantforge_secret and binds PostgreSQL/Redis to all interfaces. PR #54 binds local ports to loopback and adds production configuration checks. | **Confirmed on main; fix proposed** — production must reject default credentials and keep DB/Redis private. Rotate reused credentials. |
| 19 | Sensitive data in logs | PR #54 sanitizes request IDs and avoids returning raw upstream exception details; request logs omit request bodies/tokens in reviewed middleware. | **Partial** — inspect all application/provider/audit logs for tokens, passwords, TOTP seeds, broker credentials, PII, and webhook payloads; set retention/access controls. |
| 20 | Vulnerable dependencies | PR #54 adds CodeQL, Dependabot, pip-audit, and npm audit checks and reports passing Python/production npm audits. Full npm audit has a documented development-tooling residual. | **Reported by PR, not independently re-run here** — rerun all dependency checks on the final commit and track/mitigate the remaining advisory. |

## Required closure evidence

- [ ] Merge/review the proposed security changes only after the open release gates are addressed or explicitly risk-accepted.
- [ ] Add PostgreSQL RLS migration(s), tenant context management, and tests for API/background/admin contexts.
- [ ] Verify the TOTP encryption and one-time-token migrations in CI/staging using the deployment encryption key; confirm rollback/recovery and existing MFA-account login.
- [ ] Validate refresh-token row-lock/reuse behavior against PostgreSQL, MFA recovery-code consumption, and cookie-authenticated WebSockets behind the real proxy.
- [ ] Add comprehensive two-user authorization tests; MFA recovery codes are implemented but still need end-to-end UI/API tests.
- [ ] Complete two-user IDOR/BOLA regression coverage for every sensitive resource and WebSocket.
- [ ] Run backend tests, frontend lint/typecheck/build, Docker production build, CodeQL, pip-audit, and npm audit on the final candidate commit.
- [ ] Validate Stripe webhook signatures/idempotency and Redis rate limiting in staging.
- [ ] Validate deployed HTTPS, Secure/HttpOnly cookie attributes, CORS allowlist, secret configuration, source-map absence, and log redaction.
- [ ] Run a safe authenticated staging DAST scan with explicit authorization and without live-money trading.

## Safety boundary

No live trading, real-money orders, production payment operations, or destructive production tests were performed. Passing static checks is not proof of exploit resistance; unresolved items remain release gates until the evidence above exists.
