# Database Setup Guide

## For New Developers

To set up the complete database structure for the WNBA scraping project:

### Quick Setup (Recommended)
```bash
# Activate virtual environment
source venv/bin/activate

# Complete database setup with verification
python -m src.database.database setup
```

This command will:
1. ✅ Create the `wnba` database if it doesn't exist
2. ✅ Run all Alembic migrations to latest version
3. ✅ Verify all 12 required tables exist
4. ✅ Check that arena, person, and team tables have proper `id`/`external_id` structure
5. ✅ Test database connection

### Manual Commands

If you need individual steps:

```bash
# Create database only
python -m src.database.database create

# Run migrations only
python -m src.database.database migrate

# Check migration status
python -m src.database.database status

# Verify table structure
python -m src.database.database verify
```

### Required Environment Variables

Make sure your `.env` file has:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wnba
DB_USER=your_username
DB_PASSWORD=your_password
```

### Expected Database Structure

After setup, you should have these tables:
- `raw_game_data` - Scraped JSON data storage
- `scraping_sessions` - Track scraping operations  
- `database_versions` - Schema version tracking
- `arena` - Arena information (id + arena_id structure)
- `person` - Player/official data (id + person_id structure) 
- `team` - Team information (id + team_id structure)
- `game` - Game metadata
- `person_game`, `team_game` - Relationship tables
- `play` - Play-by-play data
- `boxscore` - Statistical data
- `alembic_version` - Migration tracking

### Troubleshooting

If tables are missing after setup:
```bash
# Run the verification
python -m src.database.database verify

# If issues persist, run full setup again
python -m src.database.database setup
```

The setup process is designed to be idempotent - you can run it multiple times safely.