#!/usr/bin/env bash
# GO OIL DMS — Backup script.
# Dumps the Mongo database + backend .env to a tarball named by timestamp.
#
# Usage:  ./scripts/backup.sh [output-dir]
#
set -euo pipefail

OUT_DIR="${1:-./backups}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
NAME="gooil-dms-backup-${STAMP}"
TMP="$(mktemp -d)"

echo "→ Backing up to ${OUT_DIR}/${NAME}.tar.gz"
mkdir -p "$OUT_DIR"

# Mongo dump
DB_NAME_LOCAL="${DB_NAME:-go_oil_dms}"
MONGO_URL_LOCAL="${MONGO_URL:-mongodb://localhost:27017}"
mongodump --uri "$MONGO_URL_LOCAL" --db "$DB_NAME_LOCAL" --out "$TMP/mongo" --quiet

# Config
mkdir -p "$TMP/config"
[[ -f backend/.env ]] && cp backend/.env "$TMP/config/backend.env"
[[ -f frontend/.env ]] && cp frontend/.env "$TMP/config/frontend.env"

# Archive
tar -czf "$OUT_DIR/${NAME}.tar.gz" -C "$TMP" .
rm -rf "$TMP"
echo "✓ Backup complete: $OUT_DIR/${NAME}.tar.gz"
