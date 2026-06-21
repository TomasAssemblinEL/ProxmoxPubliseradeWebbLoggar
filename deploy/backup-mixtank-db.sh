#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/logweb"
DB_PATH="${LOGWEB_DB_PATH:-$APP_DIR/data/mixtank.db}"
BACKUP_DIR="${LOGWEB_DB_BACKUP_DIR:-/mnt/systembackup/logweb-db}"
KEEP_DAYS="${LOGWEB_DB_BACKUP_KEEP_DAYS:-30}"

if [ ! -f "$DB_PATH" ]; then
  echo "Database file not found: $DB_PATH" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
FINAL_PATH="$BACKUP_DIR/mixtank-$STAMP.db"
TMP_PATH="$FINAL_PATH.tmp"

# Use SQLite backup API for consistent backups while app is running.
"$APP_DIR/.venv/bin/python" - "$DB_PATH" "$TMP_PATH" <<'PY'
import sqlite3
import sys

source_path = sys.argv[1]
target_path = sys.argv[2]

source_conn = sqlite3.connect(source_path)
target_conn = sqlite3.connect(target_path)

with target_conn:
    source_conn.backup(target_conn)

source_conn.close()
target_conn.close()
PY

mv "$TMP_PATH" "$FINAL_PATH"
chmod 640 "$FINAL_PATH"

find "$BACKUP_DIR" -maxdepth 1 -type f -name 'mixtank-*.db' -mtime "+$KEEP_DAYS" -delete

echo "Backup created: $FINAL_PATH"
