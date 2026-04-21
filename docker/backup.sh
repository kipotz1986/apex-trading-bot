#!/bin/bash
# APEX Trading Bot - Automated Database Backup Script
# Retention: 7 days

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
FILENAME="apex_backup_${TIMESTAMP}.sql.gz"

# Ensure backup directory exists
mkdir -p ${BACKUP_DIR}

echo "Starting database backup at ${TIMESTAMP}..."

# Create compressed backup using pg_dump from the docker container
# Note: POSTGRES_USER and POSTGRES_DB should match your .env
docker exec apex-postgres pg_dump -U apex apex_trading | gzip > "${BACKUP_DIR}/${FILENAME}"

if [ $? -eq 0 ]; then
    echo "✅ Backup completed successfully: ${FILENAME}"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Remove backups older than 7 days
echo "Cleaning up old backups..."
find ${BACKUP_DIR} -name "apex_backup_*.sql.gz" -mtime +7 -exec rm {} \;

echo "Maintenance complete."
