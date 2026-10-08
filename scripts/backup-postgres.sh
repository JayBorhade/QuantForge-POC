#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-./backups}"
mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$OUT_DIR/quantforge-postgres-$STAMP.sql.gz"

docker compose -f docker-compose.production.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER:?POSTGRES_USER is required}" "${POSTGRES_DB:?POSTGRES_DB is required}" \
  | gzip > "$FILE"

echo "PostgreSQL backup written to $FILE"
