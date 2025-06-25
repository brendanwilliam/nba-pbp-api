# Database Management Tools

This document provides comprehensive documentation for the NBA Play-by-Play API database management tools.

## Overview

The project includes sophisticated database management tools for development and deployment workflows, supporting both local PostgreSQL and cloud Neon databases.

## Architecture

```
Local Development Database (PostgreSQL)
    ↓ Synchronization Tools
Cloud Production Database (Neon)
    ↓ API Access
REST API Endpoints
```

## Available Tools

### 1. Selective Sync Tool (`src/database/selective_sync.py`)

**Purpose**: Efficient table-by-table synchronization for routine updates

**When to use**: Daily development workflow, syncing new data, targeted updates

#### Features

- **Smart Difference Detection**
  - Schema differences (missing/extra/different columns)
  - Row count differences  
  - Significant size differences (>50% + >1MB threshold)
  - Option to ignore minor size differences with `--ignore-size`

- **Flexible Sync Modes**
  - **Auto-sync**: Automatically detect and sync all different tables
  - **Manual sync**: Specify exact tables to synchronize
  - **Analysis only**: Check differences without making changes
  - **Dry-run**: Preview all changes before execution

- **Advanced Controls**
  - Large table protection (>1M rows require `--force`)
  - Schema-only sync (`--schema-only`)
  - Data-only sync (`--data-only`)
  - Verbose progress reporting (`--verbose`)
  - Table filtering (`--tables`)

- **Safety Features**
  - Automatic timestamped backups for schema changes
  - Batch processing (10K rows per batch) for large tables
  - System/backup tables automatically excluded
  - Comprehensive error handling and rollback

#### Usage Examples

```bash
# Daily routine check - see what needs updating
python -m src.database.selective_sync --analyze --ignore-size

# Preview changes before applying
python -m src.database.selective_sync --sync --dry-run --ignore-size

# Sync specific tables
python -m src.database.selective_sync --sync raw_game_data teams players

# Auto-sync all different tables (recommended for routine updates)
python -m src.database.selective_sync --sync --ignore-size

# Force sync large table with progress tracking
python -m src.database.selective_sync --sync play_events --force --verbose

# Check specific tables only
python -m src.database.selective_sync --analyze --tables teams players games

# Schema-only update (for structure changes)
python -m src.database.selective_sync --sync teams --schema-only

# Data-only update (preserve schema)
python -m src.database.selective_sync --sync raw_game_data --data-only
```

#### Command Line Options

| Option | Description |
|--------|-------------|
| `--analyze` | Analyze differences between databases |
| `--sync [TABLES...]` | Sync tables (auto-detect if no tables specified) |
| `--tables TABLE [TABLE...]` | Specific tables to analyze or sync |
| `--dry-run` | Preview changes without making them |
| `--verbose, -v` | Detailed progress output |
| `--force` | Force sync of large tables (>1M rows) |
| `--schema-only` | Only sync schema, not data |
| `--data-only` | Only sync data, not schema |
| `--ignore-size` | Ignore size-only differences |

#### Sample Output

```
================================================================================
DATABASE DIFFERENCE ANALYSIS REPORT
================================================================================

📊 SUMMARY:
   Common tables analyzed: 21
   Tables needing sync: 2
   Tables only in LOCAL: 0
   Tables only in NEON: 0

⚠️  TABLES REQUIRING SYNCHRONIZATION:
--------------------------------------------------

📋 raw_game_data:
   Rows: Local=36,701, Neon=0 (diff: +36,701)
   📊 Row count difference: +36,701
   💾 Size difference: +1909.5 MB

📋 player_team:
   Rows: Local=8,759, Neon=8,759 (diff: +0)
   ⚠️  Schema differences:
      Different definitions: ['is_active']

💡 USAGE EXAMPLES:
   # Sync specific table:
   python -m src.database.selective_sync --sync raw_game_data
   
   # Auto-sync all differences:
   python -m src.database.selective_sync --sync --ignore-size
   
   # Dry run first:
   python -m src.database.selective_sync --sync --dry-run --ignore-size
================================================================================
```

### 2. Full Sync Tool (`src/database/synchronise_databases.py`)

**Purpose**: Complete database replacement for major schema changes

**When to use**: Major updates, schema migrations, initial deployment

#### Features

- Complete database replacement
- Alembic schema migrations
- Handles 23.6M+ rows efficiently
- Sequence updates and foreign key constraints
- Error handling and rollback capabilities

#### Usage

```bash
# Preview full synchronization
python -m src.database.synchronise_databases --dry-run

# Execute full synchronization
python -m src.database.synchronise_databases
```

### 3. Database Comparison Tool (`src/database/database_comparison.py`)

**Purpose**: Comprehensive analysis of differences between databases

**When to use**: Before major updates, troubleshooting, compliance checking

#### Usage

```bash
# Compare all aspects of local and Neon databases
python -m src.database.database_comparison
```

#### Sample Output

```
================================================================================
DATABASE COMPARISON REPORT
================================================================================

DATABASE OVERVIEW
   LOCAL:  nba_pbp (9217 MB, 23 tables)
   NEON:   nba_pbp (3424 MB, 25 tables)

⚠️  DATABASES HAVE DIFFERENCES
   Schema differences: 1
   Row count differences: 5
   Missing tables: 2

SCHEMA DIFFERENCES
--------------------------------------------------
   player_team:
     Columns only in LOCAL: ['updated_field']
     Columns only in NEON: ['legacy_field']

ROW COUNT DIFFERENCES
--------------------------------------------------
Table                Local Rows   Neon Rows    Difference
--------------------------------------------------
raw_game_data        36,701       0            +36,701
scraping_sessions    82           0            +82
================================================================================
```

### 4. Database Statistics Tool (`src/database/database_stats.py`)

**Purpose**: Monitor database health and progress

**When to use**: Regular monitoring, performance analysis, progress tracking

#### Usage

```bash
# Local database statistics
python -m src.database.database_stats --local

# Cloud database statistics  
python -m src.database.database_stats --neon

# JSON output for automation
python -m src.database.database_stats --neon --json
```

## Development Workflows

### Daily Development Routine

```bash
# 1. Check what needs to be updated
python -m src.database.selective_sync --analyze --ignore-size

# 2. Preview changes
python -m src.database.selective_sync --sync --dry-run --ignore-size

# 3. Apply updates
python -m src.database.selective_sync --sync --ignore-size
```

### New Data Deployment

```bash
# 1. Sync new scraping data
python -m src.database.selective_sync --sync raw_game_data scraping_sessions

# 2. Verify deployment
python -m src.database.selective_sync --analyze --tables raw_game_data
```

### Schema Changes

```bash
# 1. Compare full databases first
python -m src.database.database_comparison

# 2. For minor schema changes
python -m src.database.selective_sync --sync teams --schema-only

# 3. For major schema changes
python -m src.database.synchronise_databases --dry-run
python -m src.database.synchronise_databases
```

### Large Table Updates

```bash
# 1. Check table size and differences
python -m src.database.selective_sync --analyze --tables play_events

# 2. Force sync with progress tracking
python -m src.database.selective_sync --sync play_events --force --verbose

# 3. Verify completion
python -m src.database.database_stats --neon
```

## Safety and Best Practices

### Before Any Sync
1. **Always run analysis first**: `--analyze` to understand changes
2. **Use dry-run mode**: `--dry-run` to preview changes
3. **Check database backups**: Ensure recent backups exist
4. **Verify local data**: Confirm local database has correct data

### For Production Deployments
1. **Test on staging first**: Use a staging Neon database
2. **Schedule during low usage**: Minimize impact on API users
3. **Monitor after deployment**: Check API functionality post-sync
4. **Have rollback plan**: Keep previous backup accessible

### Performance Considerations
1. **Use selective sync for routine updates**: Much faster than full sync
2. **Use `--ignore-size` flag**: Avoid syncing tables with only storage differences
3. **Sync large tables individually**: Use `--force` and `--verbose` for monitoring
4. **Batch operations during off-peak hours**: Minimize database load

## Troubleshooting

### Common Issues

#### "Table does not exist" Error
```bash
# Check if table exists in both databases
python -m src.database.selective_sync --analyze --tables problematic_table
```

#### "Permission denied" Error
```bash
# Verify database connection strings and credentials
python -m src.database.database_stats --neon
```

#### Sync appears to hang
```bash
# Use verbose mode to see progress
python -m src.database.selective_sync --sync large_table --verbose --force
```

#### Schema differences detected
```bash
# Use schema-only sync to update structure first
python -m src.database.selective_sync --sync table_name --schema-only
```

### Recovery Procedures

#### Restore from backup (schema changes)
```sql
-- Automatic backups are created with timestamps
DROP TABLE current_table;
ALTER TABLE table_backup_20241225_143022 RENAME TO current_table;
```

#### Rollback failed sync
```bash
# Re-run full comparison to assess state
python -m src.database.database_comparison

# Restore specific table from local
python -m src.database.selective_sync --sync problematic_table --force
```

## Monitoring and Maintenance

### Regular Checks (Recommended Weekly)
```bash
# 1. Overall database health
python -m src.database.database_stats --neon

# 2. Sync status
python -m src.database.selective_sync --analyze --ignore-size

# 3. Performance metrics
python -m src.database.database_comparison
```

### Automated Monitoring Setup
```bash
# Add to cron for daily checks
0 6 * * * cd /path/to/nba-pbp-api && python -m src.database.selective_sync --analyze --ignore-size > /var/log/db-sync-check.log
```

## Environment Variables

Ensure these environment variables are properly configured:

```bash
# Required for Neon cloud database access
DATABASE_URL="postgresql://user:pass@host:port/database"

# Optional for custom local database
LOCAL_DATABASE_URL="postgresql://localhost:5432/nba_pbp"
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Check Database Sync Status
  run: |
    python -m src.database.selective_sync --analyze --ignore-size
    
- name: Deploy Database Changes
  run: |
    python -m src.database.selective_sync --sync --ignore-size
  if: github.ref == 'refs/heads/main'
```

This comprehensive database management system ensures reliable, efficient, and safe synchronization between development and production environments while providing detailed monitoring and troubleshooting capabilities.