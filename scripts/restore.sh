#!/usr/bin/env bash
# GO OIL DMS — Restore script.
# Restores a tarball produced by backup.sh into the local Mongo instance.
#
# Usage:  ./scripts/restore.sh <path-to-backup.tar.gz>
#
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup.tar.gz>"
  exit 1
fi

BACKUP="$1"
[[ -f "$BACKUP" ]] || { echo "File not found: $BACKUP"; exit 2; }

TMP="$(mktemp -d)"
tar -xzf "$BACKUP" -C "$TMP"

DB_NAME_LOCAL="${DB_NAME:-go_oil_dms}"
MONGO_URL_LOCAL="${MONGO_URL:-mongodb://localhost:27017}"

echo "→ Restoring into $DB_NAME_LOCAL"
mongorestore --uri "$MONGO_URL_LOCAL" --db "$DB_NAME_LOCAL" \
             --drop --quiet "$TMP/mongo/$DB_NAME_LOCAL"

rm -rf "$TMP"
echo "✓ Restore complete."
