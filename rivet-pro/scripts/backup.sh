#!/bin/bash
#############################################################
# RIVET Pro MVP - Database Backup Script
#
# This script backs up your Neon PostgreSQL database
# to a timestamped SQL dump file.
#
# Usage: ./backup.sh
# Schedule with cron: 0 2 * * * /path/to/backup.sh
#############################################################

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-../backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}RIVET Pro - Database Backup${NC}"
echo ""

# Load environment
if [ ! -f "../.env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    exit 1
fi

source ../.env

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ DATABASE_URL not set in .env${NC}"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/rivetpro_backup_$TIMESTAMP.sql"

echo "  → Creating backup..."
echo "  → File: $BACKUP_FILE"

# Perform backup
pg_dump "$DATABASE_URL" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Get file size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup complete ($SIZE)${NC}"

    # Compress backup
    echo "  → Compressing..."
    gzip "$BACKUP_FILE"
    COMPRESSED_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
    echo -e "${GREEN}✓ Compressed to $COMPRESSED_SIZE${NC}"

    # Clean up old backups
    echo "  → Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
    find "$BACKUP_DIR" -name "rivetpro_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

    echo ""
    echo -e "${GREEN}Backup saved: $BACKUP_FILE.gz${NC}"
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# List recent backups
echo ""
echo "Recent backups:"
ls -lh "$BACKUP_DIR" | tail -n 5
