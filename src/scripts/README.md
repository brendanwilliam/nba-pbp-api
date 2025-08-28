# Scripts Directory

This directory contains executable scripts for WNBA data scraping and management operations.

## Scraper Manager

The `scraper_manager.py` module provides a comprehensive CLI interface for scraping WNBA game data from the official WNBA website.

### Prerequisites

Ensure you have activated the virtual environment and set up the database:

```bash
source venv/bin/activate
python -m src.database.database  # Setup database and run migrations
```

### Basic Usage

```bash
python -m src.scripts.scraper_manager COMMAND [OPTIONS]
```

### Available Commands

#### Single Season Scraping
```bash
# Scrape entire 2024 regular season
python -m src.scripts.scraper_manager scrape-season --season 2024 --game-type regular

# Scrape 2024 playoff games
python -m src.scripts.scraper_manager scrape-season --season 2024 --game-type playoff

# Test with limited games (recommended for first run)
python -m src.scripts.scraper_manager scrape-season --season 2024 --max-games 10 --verbose
```

#### Bulk Season Scraping
```bash
# Scrape ALL regular season games (1997-2025)
python -m src.scripts.scraper_manager scrape-all-regular

# Scrape ALL playoff games (1997-2025) 
python -m src.scripts.scraper_manager scrape-all-playoff

# Scrape ALL games (both regular and playoff for all seasons)
python -m src.scripts.scraper_manager scrape-all-games

# Test bulk scraping with limited total games
python -m src.scripts.scraper_manager scrape-all-regular --max-games 50 --verbose
python -m src.scripts.scraper_manager scrape-all-games --max-games 100 --verbose
```

#### Test Single Game
```bash
# Test scraping a specific game
python -m src.scripts.scraper_manager test-single --game-id 1022400001 --season 2024
```

#### Session Management
```bash
# List all active scraping sessions
python -m src.scripts.scraper_manager list-sessions
```

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--season YEAR` | WNBA season year (required for most commands) | `--season 2024` |
| `--game-type TYPE` | Game type: `regular` or `playoff` (default: regular) | `--game-type playoff` |
| `--max-games N` | Limit scraping to N games per season OR total games for bulk commands | `--max-games 5` |
| `--game-id ID` | Specific game ID (for test-single) | `--game-id 1022400001` |
| `--verbose, -v` | Enable verbose logging | `--verbose` |

### Examples

#### Production Scraping
```bash
# Single season scraping
python -m src.scripts.scraper_manager scrape-season --season 2024
python -m src.scripts.scraper_manager scrape-season --season 2023 --game-type playoff

# Bulk scraping (all seasons)
python -m src.scripts.scraper_manager scrape-all-regular    # All regular seasons (1997-2025)
python -m src.scripts.scraper_manager scrape-all-playoff    # All playoff seasons (1997-2025)
python -m src.scripts.scraper_manager scrape-all-games      # EVERYTHING (regular + playoff)
```

#### Development/Testing
```bash
# Single season testing
python -m src.scripts.scraper_manager scrape-season --season 2024 --max-games 5 --verbose

# Bulk scraping testing (limit total games across all seasons)
python -m src.scripts.scraper_manager scrape-all-regular --max-games 10 --verbose   # 10 total games max
python -m src.scripts.scraper_manager scrape-all-games --max-games 20 --verbose     # 20 total games max

# Test single game extraction
python -m src.scripts.scraper_manager test-single --game-id 1022400001 --season 2024 --verbose
```

### Features

- **Session Tracking**: All scraping operations are tracked in the `scraping_sessions` database table
- **Progress Monitoring**: Real-time progress updates every 10 games
- **Duplicate Detection**: Automatically skips games that already exist in the database
- **Error Handling**: Robust error handling with detailed logging
- **Rate Limiting**: Built-in delays to be respectful to the WNBA website
- **Logging**: Comprehensive logging to both console and `scraper_manager.log` file

### Output

The scraper provides detailed statistics after each run:

```
Scraping Results for 2024 regular season:
  Total games: 240
  Successfully scraped: 235
  Failed: 2
  Skipped (already exist): 3
```

### Monitoring

- Check active sessions: Use `list-sessions` command
- View logs: Check `scraper_manager.log` file
- Database status: Use `python -m src.database.database_stats --local`

### Troubleshooting

1. **Import Errors**: Ensure virtual environment is activated
2. **Database Errors**: Run database setup: `python -m src.database.database`
3. **Network Issues**: Check internet connection and try with `--verbose` flag
4. **Rate Limiting**: The scraper includes automatic delays, but you can restart if needed

### Integration

The scraper manager integrates with:
- `game_url_generator`: For systematic URL generation across seasons
- `raw_data_extractor`: For extracting JSON data from WNBA.com pages  
- `database.services`: For session tracking and data storage
- Database models: `raw_game_data` and `scraping_sessions` tables