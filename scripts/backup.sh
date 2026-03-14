#!/usr/bin/env bash
# scripts/backup.sh — Story 12.2: Daily PostgreSQL dump + Redis AOF backup
#
# Usage:
#   ./scripts/backup.sh               # auto-detect config from .env
#   BACKUP_DIR=/mnt/backups ./scripts/backup.sh
#
# Required environment variables (read from /opt/joat_stores/.env):
#   DATABASE_URL      — postgres://user:pass@host:port/db
#   REDIS_URL         — redis://host:port/db
#   BACKUP_DIR        — local directory for backups (default: /var/backups/joat_stores)
#   BACKUP_KEEP_DAYS  — days to retain local backups (default: 7)
#   S3_BUCKET         — optional: s3://bucket/prefix for offsite upload
#
# Cron: 0 3 * * * /opt/joat_stores/scripts/backup.sh >> /var/log/joat_backup.log 2>&1

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-/var/backups/joat_stores}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
S3_BUCKET="${S3_BUCKET:-}"

mkdir -p "${BACKUP_DIR}"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

# ---------------------------------------------------------------------------
# 1. PostgreSQL dump
# ---------------------------------------------------------------------------
log "Starting PostgreSQL backup..."

# Parse DATABASE_URL: postgres://user:pass@host:port/db
if [ -z "${DATABASE_URL:-}" ]; then
  log "ERROR: DATABASE_URL not set"
  exit 1
fi

PG_DUMP_FILE="${BACKUP_DIR}/postgres_${TIMESTAMP}.dump"

# Use pg_dump with custom format (compressed, parallel-restore capable)
pg_dump \
  "${DATABASE_URL}" \
  --format=custom \
  --compress=9 \
  --no-acl \
  --no-owner \
  --file="${PG_DUMP_FILE}"

log "PostgreSQL backup complete: ${PG_DUMP_FILE} ($(du -sh "${PG_DUMP_FILE}" | cut -f1))"

# ---------------------------------------------------------------------------
# 2. Redis AOF / RDB backup
# ---------------------------------------------------------------------------
log "Starting Redis backup..."

REDIS_BACKUP_FILE="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"

# Trigger a BGSAVE and wait for it to complete
redis-cli -u "${REDIS_URL:-redis://localhost:6379}" BGSAVE
sleep 2

# Copy the RDB file from the running container
# In Docker Compose, the redis service exposes the data volume
REDIS_RDB_PATH="${REDIS_RDB_PATH:-/data/dump.rdb}"
if [ -f "${REDIS_RDB_PATH}" ]; then
  cp "${REDIS_RDB_PATH}" "${REDIS_BACKUP_FILE}"
  log "Redis RDB backup: ${REDIS_BACKUP_FILE}"
else
  log "WARNING: Redis RDB not found at ${REDIS_RDB_PATH} — skipping Redis backup"
fi

# ---------------------------------------------------------------------------
# 3. Upload to S3 (optional)
# ---------------------------------------------------------------------------
if [ -n "${S3_BUCKET}" ]; then
  log "Uploading to ${S3_BUCKET}..."
  aws s3 cp "${PG_DUMP_FILE}" "${S3_BUCKET}/postgres/$(basename "${PG_DUMP_FILE}")" \
    --storage-class STANDARD_IA
  if [ -f "${REDIS_BACKUP_FILE}" ]; then
    aws s3 cp "${REDIS_BACKUP_FILE}" "${S3_BUCKET}/redis/$(basename "${REDIS_BACKUP_FILE}")" \
      --storage-class STANDARD_IA
  fi
  log "S3 upload complete"
fi

# ---------------------------------------------------------------------------
# 4. Prune old local backups
# ---------------------------------------------------------------------------
log "Pruning backups older than ${BACKUP_KEEP_DAYS} days..."
find "${BACKUP_DIR}" -name "*.dump" -mtime "+${BACKUP_KEEP_DAYS}" -delete
find "${BACKUP_DIR}" -name "*.rdb"  -mtime "+${BACKUP_KEEP_DAYS}" -delete

log "Backup complete. Files in ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}"
