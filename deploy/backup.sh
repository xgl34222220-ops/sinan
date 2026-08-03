#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/opt/tianji"
DATA_DIR="$INSTALL_DIR/data"
BACKUP_DIR="$INSTALL_DIR/backups"
DB_FILE="$DATA_DIR/tianji.db"

[[ -f "$DB_FILE" ]] || exit 0
mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$BACKUP_DIR/tianji-$TIMESTAMP.db"

# Use Python's SQLite backup API so WAL-mode databases are copied consistently.
docker compose -f "$INSTALL_DIR/docker-compose.yml" --env-file "$INSTALL_DIR/.env" exec -T api \
  python - "$TARGET" <<'PY'
import os
import sqlite3
import sys

source = "/app/data/tianji.db"
host_target = sys.argv[1]
container_target = "/app/data/.backup.tmp"
with sqlite3.connect(source) as src, sqlite3.connect(container_target) as dst:
    src.backup(dst)
print(container_target)
PY

mv "$DATA_DIR/.backup.tmp" "$TARGET"
gzip -f "$TARGET"
find "$BACKUP_DIR" -type f -name 'tianji-*.db.gz' -mtime +14 -delete
