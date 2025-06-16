# Scripts Module

This module contains executable Python scripts for managing NBA game scraping operations, from URL queue building to monitoring and testing.

## Files

### build_game_url_queue.py

**Purpose**: Main script to discover and populate NBA game URLs for systematic scraping. Builds a comprehensive queue of all NBA games from 1996-2025.

**Command Line Arguments**:
- `--seasons` (list): Specific seasons to process
- `--dates` (list): Specific dates to process (supports YYYY-MM-DD, YYYYMMDD, or MM/DD/YYYY formats)
- `--validate` (flag): Validate URLs after generation
- `--validate-only` (flag): Only validate existing URLs in the queue
- `--stats-only` (flag): Show queue statistics without building
- `--limit` (int): Limit number of URLs to validate
- `--status` (str): Status of URLs to validate (default: pending, auto-converts invalid to pending)

**Usage**:
```bash
# Build full queue for all seasons (1996-2025)
python src/scripts/build_game_url_queue.py

# Build queue for specific seasons with validation
python src/scripts/build_game_url_queue.py --seasons 2023-24 2024-25 --validate

# Build queue for specific dates (useful for fixing missing dates)
python src/scripts/build_game_url_queue.py --dates 2024-12-25 2024-12-26 --validate

# Build queue for specific dates with different formats
python src/scripts/build_game_url_queue.py --dates 2024-12-25 20241226 12/27/2024

# Just show statistics
python src/scripts/build_game_url_queue.py --stats-only

# Validate existing URLs (limited batch) - auto-converts invalid to pending
python src/scripts/build_game_url_queue.py --validate-only --limit 100

# Validate specific status of URLs
python src/scripts/build_game_url_queue.py --validate-only --status invalid --limit 500
```

**What it does**:
- Discovers all games for specified seasons or specific dates
- Populates the `game_url_queue` table in the database
- Validates URLs for accessibility and content using the improved validator
- Automatically converts 'invalid' URLs to 'pending' for revalidation when using `--validate-only`
- Shows comprehensive statistics by season, status, and game type
- Handles multiple date formats for flexible date input

**Key Features**:
- **Date-Specific Processing**: Can process games for specific dates to fix missing or failed URL retrievals
- **Multiple Date Formats**: Supports YYYY-MM-DD, YYYYMMDD, and MM/DD/YYYY date formats
- **Smart Season Detection**: Automatically determines the correct NBA season for each date
- **Smart Revalidation**: When using `--validate-only` with no pending URLs, automatically converts invalid URLs to pending for revalidation with the improved validator
- **Improved Validation**: Uses CSS selector `#__NEXT_DATA__` to properly identify script tags with game data
- **Flexible Status Filtering**: Can validate URLs with different statuses (pending, invalid, etc.)
- **Progress Tracking**: Shows validation results and updated queue status

**Dependencies**: `GameURLGenerator`, `GameURLValidator`, database module

---

### demo_queue_building.py

**Purpose**: Demo script that populates the queue with sample game data for testing queue management operations without full data processing.

**Usage**:
```bash
python src/scripts/demo_queue_building.py
```

**What it does**:
- Inserts 4 sample games into the queue (2 from 2024-25, 2 from 2019-20)
- Shows queue statistics before and after insertion
- Demonstrates status updates (marking games as validated/invalid)
- Useful for testing queue functionality without network calls

**Dependencies**: Database module, `GameURLInfo` model

---

### mass_game_scraper.py

**Purpose**: Main orchestration script for mass NBA game scraping with concurrent workers, rate limiting, and comprehensive error handling.

**Command Line Arguments**:
- `--batch-size` (int, default=100): Batch size for processing
- `--max-workers` (int, default=4): Maximum concurrent workers
- `--max-batches` (int): Maximum batches to process (None for unlimited)
- `--season` (str): Filter by specific season
- `--rate-limit` (float, default=0.5): Requests per second
- `--db-url` (str): Database URL (overrides environment)

**Usage**:
```bash
# Run full scraping with default settings
python src/scripts/mass_game_scraper.py

# Scrape specific season with custom settings
python src/scripts/mass_game_scraper.py --season 2023-24 --batch-size 50 --max-workers 2

# Run limited test scraping
python src/scripts/mass_game_scraper.py --max-batches 5 --rate-limit 1.0
```

**Key Features**:
- Concurrent scraping with thread pool management
- Rate limiting and adaptive backoff strategies
- Graceful shutdown handling (SIGINT/SIGTERM)
- Automatic retry for failed games
- Real-time progress tracking and statistics
- Comprehensive error logging

**Dependencies**: `GameScrapingQueue`, `NBADataExtractor`, `RateLimiter`, database module

---

### monitor_progress.py

**Purpose**: Real-time monitoring and reporting dashboard for scraping progress with beautiful terminal UI using Rich library.

**Usage**:
```bash
python src/scripts/monitor_progress.py
```

**Features**:
- Live updating dashboard with progress bars
- Season-by-season breakdown with completion percentages
- Current scraping rate (games per hour)
- Error summaries and failure analysis
- Generates detailed text reports for offline analysis
- Color-coded status indicators

**Dependencies**: `asyncpg`, `rich` library for terminal UI

---

### run_december_scraping.py

**Purpose**: Specific script to run scraping for December 2024 games that are already queued in the database (test/demo purposes).

**Usage**:
```bash
python src/scripts/run_december_scraping.py
```

**What it does**:
- Skips URL collection phase (assumes games already in database)
- Executes scraping on queued December 2024 games
- Generates comprehensive summary report
- Saves detailed report to `december_2024_test_report.md`
- Provides test metrics and validation results

**Dependencies**: `December2024TestScraper` module

---

### run_systematic_scraping.py

**Purpose**: Main entry point for systematic NBA scraping with multiple operation modes and database initialization.

**Command Line Arguments**:
- First positional argument (command): `populate`, `monitor`, `report`, `reset`, or `scrape`
- For `populate`: optional season argument

**Usage**:
```bash
# Run full systematic scraping (prompts for confirmation)
python src/scripts/run_systematic_scraping.py

# Populate queue for specific season
python src/scripts/run_systematic_scraping.py populate 2023-24

# Run monitoring dashboard
python src/scripts/run_systematic_scraping.py monitor

# Generate comprehensive report
python src/scripts/run_systematic_scraping.py report

# Reset stale games in queue
python src/scripts/run_systematic_scraping.py reset
```

**Environment Variables**:
- `DATABASE_URL`: PostgreSQL connection string
- `SCRAPING_RATE_LIMIT`: Requests per second (default: 1.0)
- `BATCH_SIZE`: Processing batch size (default: 20)
- `MAX_WORKERS`: Concurrent workers (default: 3)
- `START_SEASON`: Starting season (default: "1996-97")

**Key Features**:
- Database schema initialization and validation
- Multiple operation modes for different tasks
- Configuration via environment variables
- Comprehensive logging and error handling

**Dependencies**: `SystematicScraper`, `QueueManager`, `ScrapingMonitor`, database schema

---

### scraping_monitor.py

**Purpose**: Standalone monitoring script with enhanced features for tracking mass scraping progress, providing both live dashboard and report export capabilities.

**Command Line Arguments**:
- `--refresh` (int, default=30): Refresh interval in seconds
- `--once` (flag): Show dashboard once and exit
- `--export` (str): Export report to JSON file
- `--db-url` (str): Database URL (overrides environment)

**Usage**:
```bash
# Live monitoring with 30-second refresh
python src/scripts/scraping_monitor.py

# Show dashboard once and exit
python src/scripts/scraping_monitor.py --once

# Export report to JSON file
python src/scripts/scraping_monitor.py --export scraping_report.json

# Custom refresh rate (10 seconds)
python src/scripts/scraping_monitor.py --refresh 10
```

**Dashboard Information**:
- Queue status (completed, pending, in progress, failed, invalid)
- Performance metrics (completion rate, current speed)
- Season progress (top 5 seasons by activity)
- Error analysis and failure patterns
- Recent failures with error details

**Dependencies**: `GameScrapingQueue`, database module

---

### test_mass_scraper.py

**Purpose**: Comprehensive test suite for the mass scraping system, testing all components individually and in integration.

**Usage**:
```bash
python src/scripts/test_mass_scraper.py
```

**Tests Performed**:
1. **Queue Operations** - Database queue management functionality
2. **Data Extractor** - NBA.com data extraction capabilities
3. **Rate Limiter** - Rate limiting behavior and backoff
4. **Integration** - All components working together

**Test Details**:
- Tests queue statistics and batch retrieval operations
- Validates data extraction from real NBA URLs
- Tests rate limiting behavior under various conditions
- Runs integration test with actual game scraping
- Provides comprehensive test summary with pass/fail status

**Dependencies**: All scraping modules (`GameScrapingQueue`, `NBADataExtractor`, `RateLimiter`)

---

### test_queue_offline.py

**Purpose**: Offline test suite that validates queue building functionality without making any network calls.

**Usage**:
```bash
python src/scripts/test_queue_offline.py
```

**Tests Performed**:
1. **Team Mapping** - NBA team abbreviations and historical changes
2. **GameURLInfo Structure** - Data model validation
3. **URL Generation** - URL format testing and validation
4. **Database Schema** - Table existence and structure validation

**Key Features**:
- No network calls required (fully offline)
- Tests core business logic and data structures
- Validates database schema consistency
- Returns proper exit codes (0 for success, 1 for failure)
- Fast execution for CI/CD pipelines

**Dependencies**: Team mapping, URL generator, database modules (no network dependencies)

---

### test_url_queue_build.py

**Purpose**: Test script specifically for URL queue building process with real network validation and NBA.com interaction.

**Usage**:
```bash
python src/scripts/test_url_queue_build.py
```

**Tests Performed**:
1. **Team Mapping** - Validates all 30 current NBA teams
2. **Single Season URL Generation** - Tests 2024-25 season discovery
3. **URL Validation** - Tests known good and bad NBA.com URLs

**Test Details**:
- Discovers games for current season with real NBA.com data
- Tests queue population with sample games
- Validates actual NBA.com URLs for accessibility and content
- Shows detailed results for each test phase
- Provides comprehensive error reporting

**Dependencies**: `GameURLGenerator`, `GameURLValidator`, team mapping, database

## Usage Patterns

### Initial Setup and Testing:
```bash
# 1. Run offline tests first
python src/scripts/test_queue_offline.py

# 2. Test URL generation with current season
python src/scripts/test_url_queue_build.py

# 3. Run demo to populate sample data
python src/scripts/demo_queue_building.py

# 4. Test mass scraper components
python src/scripts/test_mass_scraper.py
```

### Production Workflow:
```bash
# 1. Build the full game URL queue
python src/scripts/build_game_url_queue.py

# 2. Check queue statistics
python src/scripts/build_game_url_queue.py --stats-only

# 3. Start mass scraping
python src/scripts/mass_game_scraper.py --season 2023-24

# 4. Monitor progress in another terminal
python src/scripts/scraping_monitor.py

# 5. Generate and export report
python src/scripts/scraping_monitor.py --export report.json
```

### Maintenance Operations:
```bash
# Reset stale games that are stuck in "in_progress" status
python src/scripts/run_systematic_scraping.py reset

# Validate URLs currently in queue
python src/scripts/build_game_url_queue.py --validate-only --limit 1000

# Export current system status
python src/scripts/scraping_monitor.py --once --export status.json
```

## Common Features

All scripts follow consistent patterns:
- **Async Operations**: Use asyncio for efficient concurrent processing
- **Comprehensive Logging**: Detailed logging with multiple severity levels
- **Error Handling**: Robust error handling with graceful degradation
- **Progress Tracking**: Real-time progress updates and statistics
- **Configuration**: Environment variable and command-line configuration
- **Database Integration**: Proper database connection management and cleanup

The scripts are designed to work together as components of the larger NBA play-by-play data scraping and management system, each handling specific aspects of the overall workflow.