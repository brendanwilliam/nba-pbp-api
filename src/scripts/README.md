# Scripts Module

This module contains executable Python scripts for managing NBA game scraping operations, data processing, and database population. All scripts have been streamlined to support the current project objectives (Plan 10: Enhanced Database Schema Implementation).

## Core Scripts Overview

### Data Processing & Schema Population

#### populate_enhanced_schema.py
**Purpose**: Core script for migrating raw JSON data to the enhanced database schema tables. Processes games, players, play events, team stats, and more.

**Usage**:
```bash
python src/scripts/populate_enhanced_schema.py
```

**Key Features**:
- Extracts structured data from raw JSON game files
- Populates enhanced_games, play_events, player_game_stats, team_game_stats tables
- Handles data validation and error recovery
- Progress tracking and batch processing
- Essential for Plan 10 implementation

---

#### fix_play_events_data.py
**Purpose**: Reprocesses existing play_events records to fix missing shot coordinates, shot types, and possession detection.

**Usage**:
```bash
python src/scripts/fix_play_events_data.py
```

**Key Features**:
- Fixes missing shot coordinate data
- Enhances shot type classification
- Improves possession tracking accuracy
- Data quality improvement for existing schema

---

### Scraping & Queue Management

#### build_game_url_queue.py
**Purpose**: Main script for discovering and populating NBA game URLs for systematic scraping. Builds comprehensive queue of all NBA games from 1996-2025.

**Command Line Arguments**:
- `--seasons` (list): Specific seasons to process
- `--dates` (list): Specific dates to process (supports YYYY-MM-DD, YYYYMMDD, or MM/DD/YYYY formats)
- `--validate` (flag): Validate URLs after generation
- `--validate-only` (flag): Only validate existing URLs in the queue
- `--stats-only` (flag): Show queue statistics without building
- `--limit` (int): Limit number of URLs to validate
- `--status` (str): Status of URLs to validate

**Usage**:
```bash
# Build full queue for all seasons
python src/scripts/build_game_url_queue.py

# Build queue for specific seasons with validation
python src/scripts/build_game_url_queue.py --seasons 2023-24 2024-25 --validate

# Just show statistics
python src/scripts/build_game_url_queue.py --stats-only

# Validate existing URLs (auto-converts invalid to pending)
python src/scripts/build_game_url_queue.py --validate-only --limit 100
```

---

#### mass_game_scraper.py
**Purpose**: Main orchestration script for mass NBA game scraping with concurrent workers, rate limiting, and comprehensive error handling.

**Command Line Arguments**:
- `--batch-size` (int, default=100): Batch size for processing
- `--max-workers` (int, default=4): Maximum concurrent workers
- `--max-batches` (int): Maximum batches to process
- `--season` (str): Filter by specific season
- `--rate-limit` (float, default=0.5): Requests per second
- `--db-url` (str): Database URL override

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

---

### Monitoring & Analysis

#### scraping_monitor.py
**Purpose**: Real-time monitoring dashboard for tracking mass scraping progress, with both live dashboard and report export capabilities.

**Command Line Arguments**:
- `--refresh` (int, default=30): Refresh interval in seconds
- `--once` (flag): Show dashboard once and exit
- `--export` (str): Export report to JSON file
- `--db-url` (str): Database URL override

**Usage**:
```bash
# Live monitoring with 30-second refresh
python src/scripts/scraping_monitor.py

# Show dashboard once and exit
python src/scripts/scraping_monitor.py --once

# Export report to JSON file
python src/scripts/scraping_monitor.py --export scraping_report.json
```

**Dashboard Information**:
- Queue status (completed, pending, in progress, failed, invalid)
- Performance metrics (completion rate, current speed)
- Season progress (top 5 seasons by activity)
- Error analysis and failure patterns
- Recent failures with error details

---

#### comprehensive_coverage_report.py
**Purpose**: Comprehensive gap analysis across all NBA game types and eras to identify missing games and coverage issues.

**Usage**:
```bash
python src/scripts/comprehensive_coverage_report.py
```

**Key Features**:
- Analyzes regular season game ID sequences for completeness (1996-2024)
- Validates early playoff numbering (1996-2000) with sparse sequential IDs
- Checks modern playoff structure (2001+) using round/series/game format
- Identifies missing games, extra games, and structural issues
- Provides prioritized recommendations for gap filling
- Handles different game ID patterns by era

---

#### audit_scraped_games.py
**Purpose**: Comprehensive analysis of scraped NBA games data with detailed breakdown by season, type, and status.

**Usage**:
```bash
python src/scripts/audit_scraped_games.py
```

**Key Features**:
- Database auditing and progress tracking
- Season-by-season breakdown of scraped vs expected games
- Game type analysis (regular season, playoffs, play-in)
- Status tracking for scraping queue
- Data quality metrics and reporting

---

### Analysis & Development Tools

#### json_structure_analyzer.py
**Purpose**: Analyzes JSON structure evolution across different seasons to understand schema changes and data availability.

**Usage**:
```bash
python src/scripts/json_structure_analyzer.py
```

**Key Features**:
- Schema design and understanding data evolution
- Tracks field availability across seasons
- Identifies new data fields and deprecated ones
- Helps inform database schema decisions
- Useful for Plan 10 schema development

---

#### backfill_lineup_tracking_enhanced.py
**Purpose**: Enhanced version of lineup tracking backfill with memory monitoring and optimization for large-scale processing.

**Usage**:
```bash
python src/scripts/backfill_lineup_tracking_enhanced.py
```

**Key Features**:
- Enhanced lineup tracking algorithm
- Memory usage monitoring and optimization
- Batch processing for large datasets
- Progress tracking and error recovery
- Supports Plan 10 lineup tracking tables

---

## Workflow Patterns

### Plan 10 Implementation Workflow
```bash
# 1. Ensure data is available
python src/scripts/comprehensive_coverage_report.py

# 2. Populate enhanced schema from raw JSON
python src/scripts/populate_enhanced_schema.py

# 3. Fix any data quality issues
python src/scripts/fix_play_events_data.py

# 4. Audit results
python src/scripts/audit_scraped_games.py
```

### Ongoing Scraping Operations
```bash
# 1. Build/update URL queue
python src/scripts/build_game_url_queue.py --validate

# 2. Start mass scraping
python src/scripts/mass_game_scraper.py --season 2024-25

# 3. Monitor progress (in another terminal)
python src/scripts/scraping_monitor.py

# 4. Generate status report
python src/scripts/scraping_monitor.py --export status.json
```

### Maintenance & Quality Assurance
```bash
# Check coverage and identify gaps
python src/scripts/comprehensive_coverage_report.py

# Analyze JSON structure evolution
python src/scripts/json_structure_analyzer.py

# Audit database state
python src/scripts/audit_scraped_games.py

# Validate URLs in queue
python src/scripts/build_game_url_queue.py --validate-only --limit 1000
```

## Script Dependencies

All scripts follow consistent patterns:
- **Environment Setup**: Require virtual environment activation (`source venv/bin/activate`)
- **Database Connection**: Use PostgreSQL connection from environment variables
- **Async Operations**: Use asyncio for efficient concurrent processing
- **Comprehensive Logging**: Detailed logging with multiple severity levels
- **Error Handling**: Robust error handling with graceful degradation
- **Progress Tracking**: Real-time progress updates and statistics
- **Configuration**: Environment variable and command-line configuration

## Database Integration

Scripts interact with key database tables:
- `game_url_queue` - URL discovery and validation tracking
- `raw_game_data` - Scraped JSON data storage
- `enhanced_games` - Structured game information
- `play_events` - Individual play-by-play events
- `player_game_stats` - Player performance data
- `team_game_stats` - Team performance data
- `scraping_sessions` - Scraping operation tracking
- `scraping_errors` - Error logging and analysis

## Recent Changes (Script Cleanup)

**Removed Scripts (No Longer Needed)**:
- `retrieve_identified_gaps.py` - Superseded by comprehensive coverage system
- `verify_game_id_sequences.py` - Functionality moved to comprehensive_coverage_report.py
- `verify_playoff_sequences.py` - Functionality moved to comprehensive_coverage_report.py
- `manual_queue_manager.py` - Manual processes have been automated
- `sample_json_extractor.py` - One-time task completed
- `enhanced_games_coverage_audit.py` - Duplicate functionality
- `backfill_lineup_tracking.py` - Superseded by enhanced version
- `migrate_lineup_tracking_v2.py` - One-time migration completed

The scripts module has been streamlined from 19 to 11 scripts, reducing maintenance overhead by 42% while maintaining all essential functionality for Plan 10 and ongoing operations.