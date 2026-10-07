# QuantForge Integration Audit

## API Route Map (prefix: `/api/v1`)

| Frontend `api.ts` | Backend Route | Auth | Status |
|-------------------|---------------|------|--------|
| `POST /auth/signup` | `auth.signup` | No | OK |
| `POST /auth/login` | `auth.login` | No | OK (sets cookies) |
| `POST /auth/refresh` | `auth.refresh` | Cookie | OK |
| `POST /auth/logout` | `auth.logout` | Yes | OK |
| `GET /auth/me` | `auth.get_me` | Yes | OK |
| `POST /auth/forgot-password` | `auth.forgot_password` + SMTP email | No | OK |
| `POST /auth/signup` | + verification email (background) | No | OK |
| `POST /auth/reset-password` | `auth.reset_password` | No | OK |
| `POST /auth/verify-email` | `auth.verify_email` | No | OK |
| `POST /auth/2fa/*` | `auth 2fa routes` | Yes | OK |
| `GET /dashboard/overview` | `dashboard.overview` | Yes | OK |
| `GET /dashboard/recent-trades` | `dashboard.recent_trades` | Yes | OK |
| `GET/POST /strategies` | `strategies CRUD` | Yes | OK |
| `POST /strategies/{id}/start\|stop` | Celery + engine | Yes | OK |
| `POST /strategies/backtest` | Creates `StrategyRun` | Yes | OK |
| `GET /strategies/runs/{id}` | Poll backtest results | Yes | OK |
| `GET/POST /portfolios` | `portfolios.*` | Yes | OK |
| `GET /brokers`, `POST /connect` | `brokers.*` | Yes | OK |
| `GET /notifications` | `notifications.*` | Yes | OK |
| `GET /ai/*` | `ai.*` | Yes | OK |
| `GET/POST /deployments` | `deployments.*` | Yes | OK |
| `GET /logs/*` | `logs.*` | Yes | OK |
| `GET/DELETE /sessions` | `sessions.*` | Yes | OK |
| `GET /admin/*` | `admin.*` | Admin | OK |
| WebSocket `WS /api/v1/ws?token=` | `websocket` | Token query | Wired in UI |

## User Flows

### Registration
`signup` → User + Subscription + Portfolio + Notification → `login` → cookies → `/dashboard`

### Login
`login` → JWT cookies → `GET /auth/me` → dashboard layout `fetchUser`

### Backtest
`POST /strategies/backtest` → `StrategyRun` PENDING → Celery (or sync fallback) → `GET /strategies/runs/{id}` poll → charts

### Live feed
`WS /api/v1/ws?token=` from cookie/header → ping/pong → trade notifications broadcast

## Fixes applied (audit pass)

- `POST /strategies/backtest` registered before `/{id}` paths
- Strategy create audit log after `flush()` (valid UUID)
- Broker import: `brokers.factory` (not `app.brokers`)
- Backtest creates `StrategyRun`, Celery or inline fallback
- Email service with dev console fallback
- WebSocket heartbeat + frontend `useWebSocket` hook
- Next.js middleware for `/dashboard` and `/admin`
- `UserResponse.role` enum serialization
- NGINX WebSocket path: `/api/v1/ws`

## Production features (implemented)
- Fernet encryption for broker credentials (`app/core/encryption.py`)
- Stripe checkout, portal, webhooks (`/api/v1/billing/*`)
- CSRF middleware + `X-CSRF-Token` header from frontend

## Known Limits (optional follow-ups)
