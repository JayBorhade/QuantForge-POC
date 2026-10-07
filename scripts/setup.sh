#!/bin/bash
set -e

echo "=== QuantForge Setup ==="

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — update secrets before production."
fi

echo "Starting infrastructure..."
docker compose up -d postgres redis

echo "Waiting for PostgreSQL..."
sleep 5

echo "Installing backend dependencies..."
cd backend
python -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head 2>/dev/null || echo "Run migrations after DB is ready: alembic upgrade head"
cd ..

echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo "=== Setup complete ==="
echo "Run: docker compose up"
echo "Frontend: http://localhost:3000"
echo "API docs: http://localhost:8000/api/docs"
