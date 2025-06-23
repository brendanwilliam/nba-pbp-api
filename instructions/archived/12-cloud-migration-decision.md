# Cloud Migration Decision - Raw Game Data

## Decision Date: 2025-06-23

### Decision: Exclude raw_game_data from Cloud Database

After migrating to Neon cloud database, we've decided to **exclude the raw_game_data table** from the cloud deployment while keeping it in the local database.

### Rationale

1. **Storage Constraints**
   - raw_game_data contains 11 GB of JSON data (36,701 games × 326 KB average)
   - This exceeds Neon Launch plan's 10 GB total storage limit
   - Other tables only use 3.4 GB, fitting comfortably within limits

2. **Data Architecture**
   - Raw JSON data is primarily for backup/reprocessing
   - All analytical data has been extracted into normalized tables:
     - play_events (17.6M rows)
     - player_game_stats (1M rows)
     - team_game_stats (73K rows)
     - lineup_states (3.3M rows)
     - substitution_events (1.5M rows)
   - API queries will use these extracted tables, not raw JSON

3. **Cost Efficiency**
   - Keeping raw data local saves ~$70/month (would require Scale plan)
   - Launch plan ($19/month) is sufficient for production API needs

### Development Workflow

#### Database Architecture
```
Local PostgreSQL (Development)
├── Complete dataset with raw_game_data (9.2 GB)
├── Full historical backup
└── Development and testing environment

Neon Cloud (Production)
├── Analytical tables only (3.4 GB)
├── API-ready data
└── Global accessibility
```

#### Workflow for Schema Changes

1. **Local Development**
   ```bash
   # Work with complete dataset locally
   DATABASE_URL="postgresql://brendan@localhost:5432/nba_pbp" python script.py
   ```

2. **Test Changes Locally**
   - Develop new features/schema changes
   - Test with full dataset including raw JSON
   - Validate data transformations

3. **Apply to Cloud**
   ```bash
   # Generate migration script
   alembic revision --autogenerate -m "description"
   
   # Apply to cloud
   DATABASE_URL="postgresql://nba_pbp_owner:npg_3wBZK4JXYVIR@ep-nameless-morning-a88pbjet-pooler.eastus2.azure.neon.tech/nba_pbp?sslmode=require" alembic upgrade head
   ```

4. **Data Sync Strategy**
   - For new scraped games: Insert into both local and cloud
   - For reprocessing: Process locally, then sync analytical tables
   - For schema changes: Use Alembic migrations

#### Environment Management

**.env file configuration:**
```bash
# Production (Neon) - Default
DATABASE_URL=postgresql://nba_pbp_owner:npg_3wBZK4JXYVIR@ep-nameless-morning-a88pbjet-pooler.eastus2.azure.neon.tech/nba_pbp?sslmode=require

# Local (Development) - Commented out
# DATABASE_URL=postgresql://brendan@localhost:5432/nba_pbp
```

**Quick switching:**
```bash
# Use production (default)
python src/database/database_stats.py

# Use local for development
DATABASE_URL="postgresql://brendan@localhost:5432/nba_pbp" python src/database/database_stats.py
```

### Future Considerations

1. **If raw data access needed in production:**
   - Implement lazy loading from local to cloud
   - Consider object storage (S3/GCS) for JSON blobs
   - Upgrade to Neon Scale plan ($69/month)

2. **Backup Strategy:**
   - Local database: Regular pg_dump backups
   - Cloud database: Neon's automatic backups
   - Consider periodic full backup sync

3. **Monitoring:**
   - Track cloud storage usage
   - Alert before reaching 10 GB limit
   - Plan for data growth

### Benefits of This Approach

1. **Cost Optimization**: Save $50/month by staying on Launch plan
2. **Performance**: Faster queries without massive JSON data
3. **Flexibility**: Full data available locally for analysis
4. **Safety**: Raw data preserved for reprocessing if needed
5. **Simplicity**: Clear separation of concerns

### Commands Reference

```bash
# Check local database stats
python src/database/database_stats.py

# Check cloud database stats  
DATABASE_URL="$NEON_URL" python src/database/database_stats.py

# Sync new analytical data from local to cloud
pg_dump -h localhost -t play_events --data-only | psql "$NEON_URL"

# Create Neon branch for testing
neon branch create --name feature-test
```

This decision aligns with best practices for separating operational data (in cloud) from archival/raw data (local storage).