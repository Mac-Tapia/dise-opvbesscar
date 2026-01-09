#!/bin/bash
# MongoDB Restore Script for Iquitos EV Infrastructure

set -e

# Configuration
BACKUP_DIR="/backups"

# MongoDB connection
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_USER="${MONGO_USER:-admin}"
MONGO_PASS="${MONGO_PASSWORD:-}"
MONGO_DB="${MONGO_DB:-iquitos_ev_db}"

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}"/*.tar.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
        BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
    else
        echo "Error: Backup file not found: ${BACKUP_FILE}"
        exit 1
    fi
fi

echo "=== MongoDB Restore Started ==="
echo "Date: $(date)"
echo "Backup file: ${BACKUP_FILE}"
echo "Target database: ${MONGO_DB}"
echo ""
read -p "WARNING: This will overwrite the existing database. Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Extract backup
TEMP_DIR=$(mktemp -d)
echo "Extracting backup to ${TEMP_DIR}..."
tar -xzvf "${BACKUP_FILE}" -C "${TEMP_DIR}"

# Find the backup directory
BACKUP_PATH=$(find "${TEMP_DIR}" -type d -name "${MONGO_DB}" | head -1)
if [ -z "${BACKUP_PATH}" ]; then
    BACKUP_PATH=$(find "${TEMP_DIR}" -type d -mindepth 1 -maxdepth 2 | head -1)
fi

echo "Restoring from: ${BACKUP_PATH}"

# Perform restore
if [ -n "${MONGO_PASS}" ]; then
    mongorestore \
        --host="${MONGO_HOST}" \
        --port="${MONGO_PORT}" \
        --username="${MONGO_USER}" \
        --password="${MONGO_PASS}" \
        --authenticationDatabase=admin \
        --db="${MONGO_DB}" \
        --drop \
        "${BACKUP_PATH}/${MONGO_DB}"
else
    mongorestore \
        --host="${MONGO_HOST}" \
        --port="${MONGO_PORT}" \
        --db="${MONGO_DB}" \
        --drop \
        "${BACKUP_PATH}/${MONGO_DB}"
fi

# Cleanup
rm -rf "${TEMP_DIR}"

echo "=== Restore Completed ==="
echo "Database ${MONGO_DB} has been restored from ${BACKUP_FILE}"
