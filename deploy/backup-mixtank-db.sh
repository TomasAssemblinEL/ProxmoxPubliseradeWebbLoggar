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
CHECKSUM_PATH="$FINAL_PATH.sha256"

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

if [ ! -s "$FINAL_PATH" ]; then
  echo "Backup verification failed: file is empty ($FINAL_PATH)" >&2
  rm -f "$FINAL_PATH"
  exit 1
fi

# Verify SQLite integrity of the backup copy.
INTEGRITY_RESULT="$($APP_DIR/.venv/bin/python - "$FINAL_PATH" <<'PY'
import sqlite3
import sys

backup_path = sys.argv[1]
conn = sqlite3.connect(backup_path)
result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
conn.close()
print(result)
PY
)"

if [ "$INTEGRITY_RESULT" != "ok" ]; then
  echo "Backup verification failed: integrity_check returned '$INTEGRITY_RESULT'" >&2
  rm -f "$FINAL_PATH"
  exit 1
fi

sha256sum "$FINAL_PATH" > "$CHECKSUM_PATH"
chmod 640 "$CHECKSUM_PATH"

BACKUP_SIZE_BYTES="$(stat -c %s "$FINAL_PATH")"

find "$BACKUP_DIR" -maxdepth 1 -type f -name 'mixtank-*.db' -mtime "+$KEEP_DAYS" -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'mixtank-*.db.sha256' -mtime "+$KEEP_DAYS" -delete

echo "Backup created: $FINAL_PATH"
echo "Backup verified: integrity_check=ok size_bytes=$BACKUP_SIZE_BYTES checksum_file=$CHECKSUM_PATH"
