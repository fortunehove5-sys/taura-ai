#!/usr/bin/env bash
# Application-level backup for Taura AI, complementing (not replacing) a
# whole-VM Xen Orchestra snapshot.
#
# Xen Orchestra snapshots (Console -> select VM -> Snapshots -> Create) are
# the right tool for whole-VM disaster recovery / rollback and are managed
# entirely outside this script -- see deploy/zchpc/README.md "Backup &
# recovery". This script instead backs up just the application-level state
# (the audit log, and later a session-store database dump once one exists)
# to a separate location, so you have finer-grained restore points than a
# full VM snapshot and can retain them off-VM.
#
# Usage: run manually, or via cron, e.g. daily at 02:00:
#   0 2 * * * /opt/taura-ai/app/deploy/zchpc/backup.sh >> /var/log/taura-backup.log 2>&1
set -euo pipefail

APP_DIR="/opt/taura-ai/app"
BACKUP_DIR="/opt/taura-ai/backups"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RETAIN_DAYS=30

mkdir -p "$BACKUP_DIR"

# --- Audit log ---------------------------------------------------------
if [ -f "$APP_DIR/logs/audit.log" ]; then
  gzip -c "$APP_DIR/logs/audit.log" > "$BACKUP_DIR/audit-${TIMESTAMP}.log.gz"
  echo "Backed up audit.log -> $BACKUP_DIR/audit-${TIMESTAMP}.log.gz"
else
  echo "No audit.log found at $APP_DIR/logs/audit.log -- skipping (nothing logged yet?)"
fi

# --- Session-store database (placeholder) -------------------------------
# Once the session store moves off in-memory/JSONL to a real database (see
# docs/ARCHITECTURE.md's "Session Store & Audit Log" row), add the
# equivalent of a `pg_dump` here, e.g.:
#
#   docker compose exec -T db pg_dump -U taura taura > "$BACKUP_DIR/db-${TIMESTAMP}.sql"
#   gzip "$BACKUP_DIR/db-${TIMESTAMP}.sql"

# --- Retention -----------------------------------------------------------
find "$BACKUP_DIR" -name "*.gz" -mtime "+${RETAIN_DAYS}" -delete
echo "Pruned backups older than ${RETAIN_DAYS} days from $BACKUP_DIR"
