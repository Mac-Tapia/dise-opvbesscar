#!/bin/bash
# MongoDB Backup Script for Iquitos EV Infrastructure

set -e

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="iquitos_ev_db_${DATE}"
RETENTION_DAYS=7

# MongoDB connection
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_USER="${MONGO_USER:-admin}"
MONGO_PASS="${MONGO_PASSWORD:-}"
MONGO_DB="${MONGO_DB:-iquitos_ev_db}"

echo "=== MongoDB Backup Started ==="
echo "Date: $(date)"
echo "Database: ${MONGO_DB}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Perform backup
if [ -n "${MONGO_PASS}" ]; then
    mongodump \
        --host="${MONGO_HOST}" \
        --port="${MONGO_PORT}" \
        --username="${MONGO_USER}" \
        --password="${MONGO_PASS}" \
        --authenticationDatabase=admin \
        --db="${MONGO_DB}" \
        --out="${BACKUP_DIR}/${BACKUP_NAME}"
else
    mongodump \
        --host="${MONGO_HOST}" \
        --port="${MONGO_PORT}" \
        --db="${MONGO_DB}" \
        --out="${BACKUP_DIR}/${BACKUP_NAME}"
fi

# Compress backup
cd "${BACKUP_DIR}"
tar -czvf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

echo "Backup created: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Size: $(du -h ${BACKUP_NAME}.tar.gz | cut -f1)"

# Remove old backups
echo "Removing backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "iquitos_ev_db_*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# List remaining backups
echo "=== Available Backups ==="
ls -lh "${BACKUP_DIR}"/*.tar.gz 2>/dev/null || echo "No backups found"

echo "=== Backup Completed ==="
