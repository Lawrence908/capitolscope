#!/bin/bash
# Database Backup Script
# Creates daily backups of PostgreSQL database and critical application data

BACKUP_DIR="/opt/capitolscope/backups"
LOG_FILE="/var/log/capitolscope/backup.log"
DB_NAME="capitolscope"
RETENTION_DAYS=30

echo "$(date): Starting backup process..." >> $LOG_FILE

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/capitolscope_backup_$TIMESTAMP.sql.gz"
CONFIG_BACKUP="$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz"

# Database backup
echo "$(date): Creating database backup..." >> $LOG_FILE
if sudo -u postgres pg_dump $DB_NAME | gzip > $BACKUP_FILE; then
    echo "$(date): Database backup created successfully: $BACKUP_FILE" >> $LOG_FILE
    
    # Verify backup integrity
    if gzip -t $BACKUP_FILE; then
        echo "$(date): Backup integrity verified" >> $LOG_FILE
    else
        echo "$(date): ERROR - Backup integrity check failed" >> $LOG_FILE
        exit 1
    fi
else
    echo "$(date): ERROR - Database backup failed" >> $LOG_FILE
    exit 1
fi

# Configuration and critical files backup
echo "$(date): Creating configuration backup..." >> $LOG_FILE
tar -czf $CONFIG_BACKUP \
    /opt/capitolscope/app/src/core/config.py \
    /opt/capitolscope/.env \
    /etc/systemd/system/capitolscope-*.service \
    /etc/cron.d/capitolscope-tasks \
    /var/log/capitolscope/*.log \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo "$(date): Configuration backup created: $CONFIG_BACKUP" >> $LOG_FILE
else
    echo "$(date): WARNING - Some configuration files could not be backed up" >> $LOG_FILE
fi

# Clean up old backups
echo "$(date): Cleaning up old backups (older than $RETENTION_DAYS days)..." >> $LOG_FILE
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Log backup size and completion
BACKUP_SIZE=$(du -sh $BACKUP_FILE | cut -f1)
echo "$(date): Backup completed successfully. Size: $BACKUP_SIZE" >> $LOG_FILE

# Optional: Upload to cloud storage (uncomment and configure as needed)
# echo "$(date): Uploading backup to cloud storage..." >> $LOG_FILE
# aws s3 cp $BACKUP_FILE s3://your-backup-bucket/capitolscope/daily/ >> $LOG_FILE 2>&1

echo "$(date): Backup process completed" >> $LOG_FILE



