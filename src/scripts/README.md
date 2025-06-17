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

# 2. Test mass scraper components
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

---

## Coverage Analysis Scripts

### comprehensive_coverage_report.py

**Purpose**: Comprehensive gap analysis across all NBA game types and eras to identify missing games and coverage issues.

**Usage**:
```bash
python src/scripts/comprehensive_coverage_report.py
```

**What it does**:
- Analyzes regular season game ID sequences for completeness (1996-2024)
- Validates early playoff numbering (1996-2000) with sparse sequential IDs
- Checks modern playoff structure (2001+) using round/series/game format
- Identifies missing games, extra games, and structural issues
- Provides prioritized recommendations for gap filling

**Key Features**:
- Handles different game ID patterns by era
- Distinguishes between acceptable gaps (early playoffs) and actual missing games
- Shows critical gaps requiring immediate attention (10+ missing games)
- Generates actionable reports for data retrieval

---

### verify_game_id_sequences.py

**Purpose**: Verifies regular season game ID sequence coverage by analyzing sequence gaps within each season.

**Usage**:
```bash
python src/scripts/verify_game_id_sequences.py
```

**What it does**:
- Extracts sequence numbers from regular season game IDs (last 4 digits)
- Compares actual sequences against expected counts per season
- Identifies specific missing sequence ranges
- Shows which games exist vs expected total

**Key Features**:
- Handles variable season lengths (lockout seasons, COVID season)
- Identifies exact missing sequences for targeted retrieval
- Validates sequence continuity and completeness

---

### verify_playoff_sequences.py

**Purpose**: Analyzes playoff game ID structure and validates tournament bracket completeness.

**Usage**:
```bash
python src/scripts/verify_playoff_sequences.py
```

**What it does**:
- Parses modern playoff IDs: `004{YY}00{round}{series}{game}`
- Validates tournament structure (8→4→2→1 series progression)
- Checks for missing series and games within existing series
- Identifies structural anomalies in playoff data

**Key Features**:
- Understands NBA playoff tournament structure
- Detects missing entire series vs missing games within series
- Generates specific missing game IDs for retrieval

---

### retrieve_identified_gaps.py

**Purpose**: Actively retrieves missing games identified through sequence analysis by discovering team matchups.

**Usage**:
```bash
python src/scripts/retrieve_identified_gaps.py
```

**What it does**:
- Takes specific missing game sequences from gap analysis
- Uses team discovery to find valid NBA.com URLs for missing games
- Estimates game dates based on sequence position in season
- Adds discovered games to the queue database

**Key Features**:
- Intelligent team combination discovery (tries common matchups first)
- Automatic game date estimation based on sequence
- Rate limiting and error handling for NBA.com requests
- Progress tracking and success reporting

## Coverage Analysis Workflow

**Complete Coverage Analysis Process**:
```bash
# 1. Run comprehensive analysis to identify all gaps
python src/scripts/comprehensive_coverage_report.py

# 2. Verify specific regular season sequences 
python src/scripts/verify_game_id_sequences.py

# 3. Check playoff tournament structure
python src/scripts/verify_playoff_sequences.py

# 4. Retrieve missing games identified in analysis
python src/scripts/retrieve_identified_gaps.py

# 5. Re-run analysis to verify improvements
python src/scripts/comprehensive_coverage_report.py
```

These coverage analysis scripts work together to achieve near-perfect NBA game coverage by systematically identifying and filling gaps in the historical game database.