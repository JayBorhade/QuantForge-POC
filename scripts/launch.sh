#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "========================================"
echo "  QuantForge Launch"
echo "========================================"
echo ""

if ! command -v docker &>/dev/null; then
  echo "Docker not found. Install Docker first."
  exit 1
fi

[ -f .env ] || cp .env.example .env

# The template contains placeholders only. Generate fresh local secrets before
# Compose reads the file; hex values are URL-safe for database/Redis URLs.
if ! command -v python3 &>/dev/null; then
  echo "python3 is required to generate safe local secrets."
  exit 1
fi
python3 - <<'PY'
from pathlib import Path
import secrets

path = Path(".env")
lines = path.read_text().splitlines()
values = {}
for line in lines:
    if line and not line.lstrip().startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values[key] = value

def fresh(name):
    current = values.get(name, "")
    if not current or current.startswith(("change-me", "quantforge_secret", "replace-me", "your-")) or current in {"sk_test_...", "whsec_...", "price_..."}:
        values[name] = secrets.token_hex(32)

for name in ("SECRET_KEY", "JWT_SECRET_KEY", "POSTGRES_PASSWORD", "REDIS_PASSWORD", "ENCRYPTION_KEY"):
    fresh(name)

user = values.get("POSTGRES_USER", "quantforge")
password = values["POSTGRES_PASSWORD"]
database = values.get("POSTGRES_DB", "quantforge")
values["DATABASE_URL"] = f"postgresql+asyncpg://{user}:{password}@localhost:5432/{database}"
redis_password = values["REDIS_PASSWORD"]
values["REDIS_URL"] = f"redis://:{redis_password}@localhost:6379/0"
values["CELERY_BROKER_URL"] = f"redis://:{redis_password}@localhost:6379/1"
values["CELERY_RESULT_BACKEND"] = f"redis://:{redis_password}@localhost:6379/2"
path.write_text("\n".join(f"{key}={value}" if not key.startswith("#") and "=" in key else key for key in lines) + "\n")
# Rewrite every configured key once, preserving comments and ordering.
lines = path.read_text().splitlines()
written = set()
out = []
for line in lines:
    if line and not line.lstrip().startswith("#") and "=" in line:
        key = line.split("=", 1)[0]
        if key in values:
            out.append(f"{key}={values[key]}")
            written.add(key)
        else:
            out.append(line)
    else:
        out.append(line)
for key, value in values.items():
    if key not in written:
        out.append(f"{key}={value}")
path.write_text("\n".join(out) + "\n")
PY

echo "Building and starting..."
docker compose down 2>/dev/null || true
docker compose up -d --build

echo "Waiting for API..."
for i in $(seq 1 40); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo "Backend healthy."
    break
  fi
  sleep 3
done

echo ""
echo "========================================"
echo "  QuantForge is LIVE"
echo "========================================"
echo ""
echo "  App:      http://localhost:3000"
echo "  API Docs: http://localhost:8000/api/docs"
echo ""
