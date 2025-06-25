# Selective Sync Quick Reference

Quick reference for the NBA Play-by-Play API selective database synchronization tool.

## Common Commands

### Daily Routine
```bash
# Check what needs updating
python -m src.database.selective_sync --analyze --ignore-size

# Preview and apply updates
python -m src.database.selective_sync --sync --dry-run --ignore-size
python -m src.database.selective_sync --sync --ignore-size
```

### Specific Table Sync
```bash
# Sync new scraping data
python -m src.database.selective_sync --sync raw_game_data scraping_sessions

# Sync team data after historical updates
python -m src.database.selective_sync --sync teams

# Force sync large table
python -m src.database.selective_sync --sync play_events --force --verbose
```

### Analysis and Troubleshooting
```bash
# Check specific tables
python -m src.database.selective_sync --analyze --tables teams players games

# Schema-only updates
python -m src.database.selective_sync --sync teams --schema-only

# Data-only updates
python -m src.database.selective_sync --sync raw_game_data --data-only
```

## Quick Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `--analyze` | Check differences only | `--analyze --ignore-size` |
| `--sync` | Sync tables | `--sync teams players` |
| `--dry-run` | Preview changes | `--sync --dry-run` |
| `--ignore-size` | Skip size-only diffs | `--analyze --ignore-size` |
| `--force` | Allow large table sync | `--sync play_events --force` |
| `--verbose` | Show progress | `--sync --verbose` |
| `--tables` | Filter to specific tables | `--analyze --tables teams` |
| `--schema-only` | Structure changes only | `--sync teams --schema-only` |
| `--data-only` | Data changes only | `--sync --data-only` |

## Common Workflows

### New Development Data
1. `--analyze --ignore-size` (check changes)
2. `--sync raw_game_data scraping_sessions` (sync new data)

### Team/Schema Updates
1. `--analyze --tables teams` (check team changes)
2. `--sync teams --schema-only` (update structure)
3. `--sync teams --data-only` (update data)

### Large Table Updates
1. `--analyze --tables play_events` (check size)
2. `--sync play_events --force --verbose` (sync with progress)

### Safety First
1. Always use `--dry-run` first for major changes
2. Use `--ignore-size` to focus on important differences
3. Sync specific tables rather than all tables when possible

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Table >1M rows" | Add `--force` flag |
| "Schema differences" | Use `--schema-only` first |
| "Permission denied" | Check DATABASE_URL environment variable |
| Slow performance | Use `--verbose` to monitor progress |

## Safety Features

✅ **Automatic backups** for schema changes  
✅ **Batch processing** for large tables  
✅ **Dry-run mode** for safe previewing  
✅ **System table exclusion** automatically  
✅ **Error handling** with rollback capability  

For complete documentation, see [Database Management Guide](database-management.md)