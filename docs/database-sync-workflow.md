# Database Sync Workflow Guide

This guide outlines how to work with both local (development) and Neon cloud (production) databases.

## Database Overview

| Database | Purpose | Data | Size | Connection |
|----------|---------|------|------|------------|
| Local PostgreSQL | Development & Raw Data Storage | Complete dataset with raw JSON | 9.2 GB | `postgresql://brendan@localhost:5432/nba_pbp` |
| Neon Cloud | Production API | Analytical tables only | 3.4 GB | See `.env` file |

## Common Development Workflows

### 1. Daily Development

```bash
# Always activate virtual environment first
source venv/bin/activate

# Default uses Neon (production)
python your_script.py

# Use local for development
DATABASE_URL="postgresql://brendan@localhost:5432/nba_pbp" python your_script.py

# Quick alias for local development (add to ~/.zshrc)
alias nba-local='DATABASE_URL="postgresql://brendan@localhost:5432/nba_pbp"'
# Then use: nba-local python your_script.py
```

### 2. Adding New Scraped Games

When scraping new games, update both databases:

```python
# In your scraping script
import os
from src.core.database import create_engine
from sqlalchemy.orm import sessionmaker

# Setup both database connections
local_engine = create_engine("postgresql://brendan@localhost:5432/nba_pbp")
cloud_engine = create_engine(os.getenv("DATABASE_URL"))

LocalSession = sessionmaker(bind=local_engine)
CloudSession = sessionmaker(bind=cloud_engine)

# After scraping a game
def save_game_data(game_data, raw_json):
    # Save to local (including raw JSON)
    with LocalSession() as local_db:
        # Save raw_game_data
        local_db.add(RawGameData(game_id=game_id, raw_json=raw_json))
        # Save analytical data
        local_db.add_all(play_events)
        local_db.commit()
    
    # Save to cloud (analytical data only)
    with CloudSession() as cloud_db:
        # Save analytical data only - NO raw_json
        cloud_db.add_all(play_events)
        cloud_db.commit()
```

### 3. Schema Changes with Alembic

```bash
# 1. Make schema changes in models.py

# 2. Generate migration
alembic revision --autogenerate -m "Add new column to play_events"

# 3. Test migration locally
alembic upgrade head

# 4. Apply to cloud
DATABASE_URL="$NEON_URL" alembic upgrade head

# 5. Rollback if needed
DATABASE_URL="$NEON_URL" alembic downgrade -1
```

### 4. Syncing Data Updates

If you reprocess data locally and need to update cloud:

```bash
# Option 1: Sync specific table
pg_dump -h localhost -U brendan -t play_events --data-only nba_pbp | \
  psql "$NEON_URL"

# Option 2: Sync with conditions
pg_dump -h localhost -U brendan -t play_events \
  --data-only \
  --where="game_date >= '2024-01-01'" \
  nba_pbp | psql "$NEON_URL"

# Option 3: Use Python script for complex updates
python scripts/sync_to_cloud.py --table play_events --since 2024-01-01
```

### 5. Database Statistics Comparison

```bash
# Create a comparison script
cat > check_databases.sh << 'EOF'
#!/bin/bash
echo "=== LOCAL DATABASE ==="
python src/database/database_stats.py

echo -e "\n=== CLOUD DATABASE ==="
DATABASE_URL="$NEON_URL" python src/database/database_stats.py
EOF

chmod +x check_databases.sh
./check_databases.sh
```

### 6. Testing with Neon Branches

Neon's branching feature is perfect for testing:

```bash
# Create a test branch
neon branches create --name test-new-feature

# Get the branch connection string
neon connection-string test-new-feature

# Test your changes
DATABASE_URL="branch-connection-string" python your_test.py

# Delete branch when done
neon branches delete test-new-feature
```

## Best Practices

### DO:
- ✅ Always test schema changes locally first
- ✅ Keep raw_game_data in local only
- ✅ Use transactions for data sync operations
- ✅ Monitor Neon storage usage (10 GB limit)
- ✅ Document any manual data fixes

### DON'T:
- ❌ Don't sync raw_game_data to cloud
- ❌ Don't run heavy analytical queries on production during peak hours
- ❌ Don't forget to activate venv before running scripts
- ❌ Don't commit .env file with credentials

## Emergency Procedures

### If Cloud Database is Down:
```bash
# Switch all operations to local
export DATABASE_URL="postgresql://brendan@localhost:5432/nba_pbp"
# Run your API/scripts as normal
```

### If Local Database is Corrupted:
```bash
# You still have cloud data for analytical tables
# Restore from backup
pg_restore -d nba_pbp latest_backup.dump
```

### Full Sync from Local to Cloud:
```bash
# Use the migration script (excludes raw_game_data)
./scripts/migrate_to_cloud.sh --exclude-raw-data
```

## Monitoring

### Check Storage Usage:
```python
# monitor_storage.py
import psycopg2
import os

def check_storage():
    # Check Neon storage
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_database_size(current_database()) / 1024 / 1024 / 1024.0 as gb_used
    """)
    gb_used = cur.fetchone()[0]
    print(f"Neon Storage: {gb_used:.2f} GB / 10 GB ({gb_used/10*100:.1f}%)")
    
    if gb_used > 9:
        print("⚠️  WARNING: Approaching storage limit!")
```

## Quick Reference

```bash
# Environment Variables
NEON_URL="postgresql://nba_pbp_owner:npg_3wBZK4JXYVIR@ep-nameless-morning-a88pbjet-pooler.eastus2.azure.neon.tech/nba_pbp?sslmode=require"
LOCAL_URL="postgresql://brendan@localhost:5432/nba_pbp"

# Common Commands
psql $LOCAL_URL                    # Connect to local
psql $NEON_URL                     # Connect to cloud
pg_dump $LOCAL_URL > backup.sql    # Backup local
psql $NEON_URL < changes.sql       # Apply changes to cloud

# Python Usage
DATABASE_URL=$LOCAL_URL python script.py  # Run on local
DATABASE_URL=$NEON_URL python script.py   # Run on cloud
```