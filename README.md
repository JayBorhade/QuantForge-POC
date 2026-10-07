# QuantForge

**Build, Backtest, Automate, Scale**

Production-grade algorithmic trading infrastructure for modern quant teams.

## Launch today

```powershell
.\scripts\launch.ps1
```

Then open **http://localhost:3000** — see [LAUNCH.md](LAUNCH.md) for full instructions.

![QuantForge](https://img.shields.io/badge/Next.js-15-black?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square)

## Features

- **Authentication** — JWT + rotating refresh tokens, 2FA, device tracking, httpOnly cookies
- **5 Trading Strategies** — EMA Crossover, RSI Mean Reversion, VWAP Intraday, Breakout, AI Sentiment
- **Backtesting** — Sharpe ratio, max drawdown, win rate, equity curves, trade history
- **Broker Adapters** — Zerodha Kite, Binance, Angel One (modular)
- **Dashboard** — Portfolio analytics, live trading, risk management, bot deployment
- **Admin Panel** — User management, audit logs, analytics
- **Infrastructure** — Docker Compose, NGINX, Celery, Redis, GitHub Actions CI

## Project Structure

```
QuantForge/
├── frontend/          # Next.js 15 + React + Tailwind + ShadCN
├── backend/           # FastAPI + SQLAlchemy + Celery
│   ├── app/           # API, models, services
│   ├── strategies/    # Trading algorithms
│   └── brokers/       # Broker adapters
├── infra/nginx/       # Reverse proxy config
├── scripts/           # Setup scripts
├── docs/              # Deployment & security guides
└── docker-compose.yml
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (local frontend dev)
- Python 3.12+ (local backend dev)

### 1. Environment

```bash
cp .env.example .env
```

### 2. Docker (recommended)

```bash
docker compose up -d --build
```

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/api/docs

### 3. Local Development

**Windows:**
```powershell
.\scripts\setup.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Celery worker:**
```bash
cd backend
celery -A app.celery_app worker --loglevel=info
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/signup` | Register account |
| `POST /api/v1/auth/login` | Login (sets cookies) |
| `POST /api/v1/auth/refresh` | Rotate tokens |
| `GET /api/v1/dashboard/overview` | Dashboard metrics |
| `GET/POST /api/v1/strategies` | Manage strategies |
| `POST /api/v1/strategies/backtest` | Run backtest |
| `WS /api/v1/ws?token=` | Live WebSocket feed |
| `GET /api/v1/portfolios` | Portfolio list & analytics |
| `POST /api/v1/brokers/connect` | Connect broker API |
| `GET /api/v1/notifications` | User notifications |
| `GET /api/v1/ai/*` | AI market, risk, portfolio insights |
| `GET/POST /api/v1/deployments` | Bot deployment center |
| `GET /api/v1/logs/*` | Strategy, audit, system logs |
| `GET /api/v1/sessions` | Device session management |
| `GET /api/v1/admin/*` | Admin (requires admin role) |

## Strategies

| Strategy | Key Parameters |
|----------|----------------|
| EMA Crossover | fast_ema=20, slow_ema=50, SL/TP % |
| RSI Mean Reversion | oversold=30, overbought=70, trailing stop |
| VWAP Intraday | volume filter, volatility threshold |
| Breakout | lookback=20, ATR stop |
| AI Sentiment | news/reddit/social weights |

## Documentation

- [Linux Deployment Guide](docs/DEPLOYMENT.md)
- [Security Checklist](docs/SECURITY.md)
- API: http://localhost:8000/api/docs

## Tech Stack

**Frontend:** Next.js 15, React, TypeScript, TailwindCSS, ShadCN, Framer Motion, Recharts, Zustand, Axios

**Backend:** FastAPI, PostgreSQL, Redis, SQLAlchemy, Alembic, Celery, JWT, bcrypt

**Trading:** pandas, numpy, ta, yfinance, vectorbt, backtrader

## Stripe setup

1. Create products/prices in [Stripe Dashboard](https://dashboard.stripe.com)
2. Add to `.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_STARTER=price_...
   STRIPE_PRICE_PRO=price_...
   ```
3. Forward webhooks locally: `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`

## Verify integration

With backend running on port 8000:

```bash
pip install httpx
python scripts/verify_integration.py
```

See [docs/INTEGRATION_AUDIT.md](docs/INTEGRATION_AUDIT.md) for full route ↔ frontend mapping.

## Promote user to admin

```bash
cd backend
python scripts/create_admin.py your@email.com
```

## License

Proprietary — QuantForge © 2026
