# Database Backup Strategy

This guide covers how to backup your NBA play-by-play database to an external drive for disaster recovery.

## Overview

Your local database contains the complete dataset including 11 GB of raw JSON data that isn't stored in the cloud. Regular backups to an external drive ensure you never lose this valuable data.

## Backup Methods

### Method 1: Full Database Backup (Recommended)

This creates a complete, compressed backup of your entire database.

```bash
# 1. Connect your external drive (e.g., /Volumes/MyBackupDrive)

# 2. Create a backup directory with date
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_DIR="/Volumes/MyBackupDrive/nba-pbp-backups/$BACKUP_DATE"
mkdir -p "$BACKUP_DIR"

# 3. Create compressed backup (will take 10-20 minutes for 9.2 GB)
pg_dump -h localhost -U brendan -Fc -b -v \
  -f "$BACKUP_DIR/nba_pbp_complete_$BACKUP_DATE.dump" \
  nba_pbp

# 4. Verify backup
ls -lh "$BACKUP_DIR/nba_pbp_complete_$BACKUP_DATE.dump"
```

**Expected size**: ~2-3 GB compressed (from 9.2 GB original)

### Method 2: Separate Table Backups

Backup critical tables separately for more flexibility:

```bash
# Create backup directory
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_DIR="/Volumes/MyBackupDrive/nba-pbp-backups/$BACKUP_DATE"
mkdir -p "$BACKUP_DIR"

# Backup raw JSON data (most important - not in cloud)
pg_dump -h localhost -U brendan -Fc -t raw_game_data \
  -f "$BACKUP_DIR/raw_game_data_$BACKUP_DATE.dump" nba_pbp

# Backup analytical tables
pg_dump -h localhost -U brendan -Fc \
  -t play_events -t player_game_stats -t team_game_stats \
  -t lineup_states -t substitution_events \
  -f "$BACKUP_DIR/analytical_tables_$BACKUP_DATE.dump" nba_pbp

# Backup metadata tables
pg_dump -h localhost -U brendan -Fc \
  -t teams -t players -t games -t game_url_queue \
  -f "$BACKUP_DIR/metadata_tables_$BACKUP_DATE.dump" nba_pbp
```

### Method 3: Automated Backup Script

Create a script for regular backups:

```bash
# Save as: scripts/backup_to_external.sh
#!/bin/bash

# Configuration
EXTERNAL_DRIVE="/Volumes/MyBackupDrive"  # Change to your drive name
BACKUP_ROOT="$EXTERNAL_DRIVE/nba-pbp-backups"
RETENTION_DAYS=30  # Keep backups for 30 days

# Check if external drive is mounted
if [ ! -d "$EXTERNAL_DRIVE" ]; then
    echo "❌ External drive not found at $EXTERNAL_DRIVE"
    echo "Please connect your external drive and try again."
    exit 1
fi

# Create backup directory
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$BACKUP_DATE"
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting backup to $BACKUP_DIR"

# Backup database
echo "📦 Creating database backup..."
pg_dump -h localhost -U brendan -Fc -b \
  -f "$BACKUP_DIR/nba_pbp_complete.dump" \
  nba_pbp

# Backup .env file (without sensitive data)
echo "📄 Backing up configuration..."
grep -v PASSWORD .env > "$BACKUP_DIR/env_backup"

# Create backup manifest
echo "📝 Creating manifest..."
cat > "$BACKUP_DIR/manifest.txt" << EOF
NBA PBP Database Backup
Date: $(date)
Database Size: $(psql -h localhost -U brendan -t -c "SELECT pg_size_pretty(pg_database_size('nba_pbp'))" nba_pbp)
Tables Backed Up: All
Backup Method: pg_dump compressed format
EOF

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "✅ Backup complete! Size: $BACKUP_SIZE"

# Clean old backups
echo "🧹 Cleaning old backups..."
find "$BACKUP_ROOT" -name "*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null

# List recent backups
echo -e "\n📊 Recent backups:"
ls -lt "$BACKUP_ROOT" | head -5
```

Make it executable:
```bash
chmod +x scripts/backup_to_external.sh
```

## Restore Procedures

### Restore Full Backup

```bash
# 1. Create new database (if needed)
createdb -h localhost -U brendan nba_pbp_restored

# 2. Restore from backup
pg_restore -h localhost -U brendan -d nba_pbp_restored -v \
  "/Volumes/MyBackupDrive/nba-pbp-backups/20240623/nba_pbp_complete_20240623.dump"

# 3. Verify restoration
psql -h localhost -U brendan -d nba_pbp_restored -c \
  "SELECT COUNT(*) FROM raw_game_data"
```

### Restore Specific Tables

```bash
# Restore just raw_game_data
pg_restore -h localhost -U brendan -d nba_pbp -t raw_game_data -v \
  --clean --if-exists \
  "/Volumes/MyBackupDrive/nba-pbp-backups/20240623/raw_game_data_20240623.dump"
```

## Backup Schedule Recommendations

### Weekly Full Backup
Run every Sunday night:
```bash
# Add to crontab (crontab -e)
0 2 * * 0 /Users/brendan/nba-pbp-api/scripts/backup_to_external.sh
```

### Daily Incremental Backup
Backup only recent changes:
```bash
# Backup games added in last 7 days
pg_dump -h localhost -U brendan -Fc \
  -t raw_game_data \
  --where="scraped_at > CURRENT_DATE - INTERVAL '7 days'" \
  -f "$BACKUP_DIR/incremental_$(date +%Y%m%d).dump" \
  nba_pbp
```

## External Drive Organization

Recommended structure:
```
/Volumes/MyBackupDrive/
└── nba-pbp-backups/
    ├── 20240623_020000/
    │   ├── nba_pbp_complete.dump
    │   ├── env_backup
    │   └── manifest.txt
    ├── 20240616_020000/
    │   └── ...
    └── README.txt
```

## Important Backup Tips

### 1. Verify Backups Regularly
```bash
# Test restore to temporary database monthly
createdb nba_pbp_test
pg_restore -d nba_pbp_test your_backup.dump
psql -d nba_pbp_test -c "SELECT COUNT(*) FROM play_events"
dropdb nba_pbp_test
```

### 2. Multiple Backup Locations
- Keep at least 2 external drives
- Rotate them weekly
- Store one offsite if possible

### 3. Cloud Backup Option
For additional safety, consider cloud storage:
```bash
# After local backup, sync to cloud storage
aws s3 sync "$BACKUP_DIR" s3://your-bucket/nba-pbp-backups/
# or
rsync -avz "$BACKUP_DIR" your-cloud-server:/backups/nba-pbp/
```

### 4. Document Your Backups
Create a backup log:
```bash
echo "$(date): Backup completed to $BACKUP_DIR - Size: $BACKUP_SIZE" >> ~/nba-backups.log
```

## Recovery Time Estimates

| Scenario | Backup Size | Restore Time |
|----------|------------|--------------|
| Full restore | ~3 GB | 20-30 minutes |
| Raw data only | ~2 GB | 15-20 minutes |
| Analytical tables | ~1 GB | 5-10 minutes |

## Emergency Recovery Checklist

If your computer fails:

1. **Get new computer with PostgreSQL installed**
2. **Connect external backup drive**
3. **Create new database**: `createdb nba_pbp`
4. **Restore latest backup**: `pg_restore -d nba_pbp /path/to/backup.dump`
5. **Verify data integrity**: Run database stats script
6. **Update .env file** with connection strings
7. **Test application** functionality

## Quick Backup Command

Add to your ~/.zshrc for easy access:
```bash
alias nba-backup='cd ~/nba-pbp-api && ./scripts/backup_to_external.sh'
```

Then just run:
```bash
nba-backup
```

Remember: Your raw_game_data is irreplaceable and represents hours of scraping work. Regular backups to an external drive ensure you'll never lose this valuable dataset!