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
