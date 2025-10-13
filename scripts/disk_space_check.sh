#!/bin/bash
# Disk Space Monitoring Script
# Checks disk usage and alerts when thresholds are exceeded

LOG_FILE="/var/log/capitolscope/disk_check.log"
WARNING_THRESHOLD=80
CRITICAL_THRESHOLD=90

# Function to check disk space for a given path
check_disk_space() {
    local path=$1
    local name=$2
    
    if [ ! -d "$path" ]; then
        echo "$(date): WARNING - Directory $path does not exist" >> $LOG_FILE
        return
    fi
    
    local usage=$(df "$path" | awk 'NR==2 {print $5}' | sed 's/%//')
    local available=$(df -h "$path" | awk 'NR==2 {print $4}')
    
    if [ "$usage" -gt $CRITICAL_THRESHOLD ]; then
        echo "$(date): CRITICAL - $name disk usage is ${usage}% (available: $available)" >> $LOG_FILE
        # Send alert email if configured
        echo "$name disk usage critical: ${usage}% used, $available available" | \
            mail -s "CRITICAL: CapitolScope Disk Space Alert" admin@capitolscope.chrislawrence.ca 2>/dev/null || true
        return 2
    elif [ "$usage" -gt $WARNING_THRESHOLD ]; then
        echo "$(date): WARNING - $name disk usage is ${usage}% (available: $available)" >> $LOG_FILE
        return 1
    else
        echo "$(date): OK - $name disk usage is ${usage}% (available: $available)" >> $LOG_FILE
        return 0
    fi
}

echo "$(date): Starting disk space check..." >> $LOG_FILE

# Check root filesystem
check_disk_space "/" "Root filesystem"
ROOT_STATUS=$?

# Check log directory
check_disk_space "/var/log" "Log directory"
LOG_STATUS=$?

# Check application directory
check_disk_space "/opt/capitolscope" "Application directory"
APP_STATUS=$?

# Check database directory (if separate)
if [ -d "/var/lib/postgresql" ]; then
    check_disk_space "/var/lib/postgresql" "Database directory"
    DB_STATUS=$?
fi

# Check temp directory
check_disk_space "/tmp" "Temp directory"
TMP_STATUS=$?

# Overall status
if [ $ROOT_STATUS -eq 2 ] || [ $LOG_STATUS -eq 2 ] || [ $APP_STATUS -eq 2 ] || [ $DB_STATUS -eq 2 ] || [ $TMP_STATUS -eq 2 ]; then
    echo "$(date): CRITICAL - One or more filesystems are critically low on space" >> $LOG_FILE
    exit 2
elif [ $ROOT_STATUS -eq 1 ] || [ $LOG_STATUS -eq 1 ] || [ $APP_STATUS -eq 1 ] || [ $DB_STATUS -eq 1 ] || [ $TMP_STATUS -eq 1 ]; then
    echo "$(date): WARNING - One or more filesystems are running low on space" >> $LOG_FILE
    exit 1
else
    echo "$(date): All filesystems have adequate space" >> $LOG_FILE
    exit 0
fi



