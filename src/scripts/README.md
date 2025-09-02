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

## Game Table Population

The `populate_game_tables.py` script transforms raw scraped WNBA game data into normalized database tables. It reads JSON data from the `raw_game_data` table and populates 8 normalized tables for analytics and querying.

### Prerequisites

Ensure you have scraped game data available in the database:

```bash
source venv/bin/activate
python -m src.database.database  # Setup database and run migrations
# First scrape some games (see Scraper Manager section above)
```

### Basic Usage

```bash
python -m src.scripts.populate_game_tables [MODE] [OPTIONS]
```

### Population Modes

#### Process All Games
```bash
# Populate all games from raw_game_data table
python -m src.scripts.populate_game_tables --all

# Limit number of games processed
python -m src.scripts.populate_game_tables --all --limit 100

# Resume from a specific game ID (useful for large datasets)
python -m src.scripts.populate_game_tables --all --resume-from 1022400150
```

#### Process Specific Games
```bash
# Process specific game IDs
python -m src.scripts.populate_game_tables --games 1022400001 1022400002 1022400003

# Process a single game
python -m src.scripts.populate_game_tables --games 1022400001
```

#### Process by Season
```bash
# Process all games from specific seasons
python -m src.scripts.populate_game_tables --seasons 2024

# Process multiple seasons
python -m src.scripts.populate_game_tables --seasons 2023 2024

# Limit games per season
python -m src.scripts.populate_game_tables --seasons 2024 --limit 50
```

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--all` | Process all games in raw_game_data table | `--all` |
| `--games ID [ID...]` | Process specific game IDs | `--games 1022400001 1022400002` |
| `--seasons YEAR [YEAR...]` | Process games from specific seasons | `--seasons 2024` |
| `--limit N` | Limit number of games to process | `--limit 100` |
| `--resume-from ID` | Resume processing from game ID (--all only) | `--resume-from 1022400150` |
| `--validate` | Validate foreign key integrity after population | `--validate` |
| `--dry-run` | Show what would be processed without processing | `--dry-run` |
| `--override` | Override existing data - clear and repopulate games that already exist | `--override` |

### Examples

#### Production Population
```bash
# Populate all available games
python -m src.scripts.populate_game_tables --all --validate

# Populate 2024 season with validation
python -m src.scripts.populate_game_tables --seasons 2024 --validate

# Populate specific games that failed previously
python -m src.scripts.populate_game_tables --games 1022400001 1022400005 1022400010

# Re-populate games with updated extractors (override existing data)
python -m src.scripts.populate_game_tables --games 1022400001 --override
```

#### Development/Testing
```bash
# Test with limited games
python -m src.scripts.populate_game_tables --all --limit 10 --dry-run
python -m src.scripts.populate_game_tables --seasons 2024 --limit 5

# Resume large population job
python -m src.scripts.populate_game_tables --all --resume-from 1022400500 --validate

# Test with override flag to fix data quality issues
python -m src.scripts.populate_game_tables --seasons 2024 --limit 5 --override
```

### Database Tables Populated

The script populates these 8 normalized tables:

1. **Arena** - Venue information
2. **Team** - WNBA team details
3. **Person** - Players and officials
4. **Game** - Game metadata and results
5. **TeamGame** - Team-game relationships
6. **PersonGame** - Person-game relationships
7. **Play** - Play-by-play data
8. **Boxscore** - Player and team statistics

### Features

- **Transaction Management**: Each game processed in its own transaction
- **Error Recovery**: Failed games don't stop processing of remaining games
- **Progress Tracking**: Real-time updates every 10 games
- **Resume Capability**: Resume large jobs from specific game ID
- **Override Mode**: Clear and repopulate games when data issues occur
- **Foreign Key Validation**: Built-in integrity checking
- **Conflict Resolution**: Handles duplicate data gracefully
- **Comprehensive Logging**: Detailed logs with statistics

#### When to Use --override Flag

Use the `--override` flag in these scenarios:
- **Data Quality Issues**: Fix problems like invalid person IDs or team data
- **Extractor Updates**: Repopulate with improved JSON extraction logic
- **Schema Changes**: Update data after model or processing changes
- **Corruption Recovery**: Clean up games with inconsistent data

⚠️ **Warning**: Override clears ALL existing data for specified games before repopulation

### Output

The script provides detailed statistics after each run:

```
Population Results:
  Total games: 240
  Successful: 235 
  Failed: 5
  Duration: 0:15:30

Records inserted by table:
  arenas: 15
  teams: 12
  persons: 1,247
  games: 235
  team_games: 470
  person_games: 12,450
  plays: 89,670
  boxscores: 3,340
```

## Data Validation

The `validate_populated_data.py` script performs comprehensive validation of populated game table data, checking for data integrity, foreign key violations, and data quality issues.

### Prerequisites

Ensure you have populated game tables:

```bash
source venv/bin/activate
# First populate some tables (see Game Table Population section above)
```

### Basic Usage

```bash
python -m src.scripts.validate_populated_data [OPTIONS]
```

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--output FILE, -o FILE` | Output validation report to file | `--output validation_report.txt` |
| `--json` | Output results as JSON format | `--json` |

### Examples

#### Basic Validation
```bash
# Run complete validation (console output)
python -m src.scripts.validate_populated_data

# Save validation report to file
python -m src.scripts.validate_populated_data --output validation_report.txt

# Save results as JSON
python -m src.scripts.validate_populated_data --output results.json --json
```

### Validation Checks

#### Foreign Key Integrity
- **Game → Arena**: Games referencing valid arenas
- **TeamGame → Game/Team**: Team-game relationships integrity
- **PersonGame → Game/Person**: Person-game relationships integrity
- **Play → Game/Person/Team**: Play-by-play data integrity
- **Boxscore → Game/Person/Team**: Boxscore data integrity

#### Data Quality Checks
- **Missing Required Data**: Games without arena/team information
- **Invalid Values**: Negative statistics, invalid percentages
- **Data Consistency**: Home/away team indicators, box types
- **Completeness**: Persons without names, plays without action types

#### Statistical Analysis
- **Game Statistics**: Total games, unique arenas/teams, date ranges
- **Play Statistics**: Total plays, unique action types, average points
- **Boxscore Statistics**: Player averages, maximum values
- **Person Statistics**: Name coverage, total persons

### Features

- **Comprehensive Checks**: Foreign keys, data quality, statistics
- **Detailed Reporting**: Clear categorization of issues by severity
- **Export Options**: Text reports or JSON for integration
- **Error Classification**: Errors vs warnings for prioritization
- **Performance Optimized**: Efficient SQL queries for large datasets

### Output

The validator provides detailed results:

```
DATA VALIDATION SUMMARY
============================================

Table Record Counts:
  arena: 15
  team: 12
  person: 1,247
  game: 235
  team_game: 470
  person_game: 12,450
  play: 89,670
  boxscore: 3,340

✓ No foreign key violations found
✓ No data quality issues found

Statistical Summary:
  Total games: 235
  Total plays: 89,670
  Total boxscore entries: 3,340

🎉 VALIDATION PASSED - All checks successful!
```

### Integration

Both scripts integrate with:
- `population_services`: Core population logic
- `database.models`: SQLAlchemy ORM models
- `database.database`: Database connection management
- `json_extractors`: Data transformation utilities