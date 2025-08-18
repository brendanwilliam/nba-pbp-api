# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WNBA play-by-play data scraping and analytics project that extracts game data from the official WNBA website, stores it in PostgreSQL, and provides essential basketball analytics including possession and lineup tracking. The project focuses specifically on WNBA data collection and processing, without API or MCP server components.

## Common Development Commands

### Environment Setup
```bash
# Always activate virtual environment first
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_queue_offline.py

# Run tests with verbose output
pytest -v tests/
```

### Database Management
```bash
# Check database status (local WNBA database)
python -m src.database.database_stats --local

# Run Alembic migrations
alembic upgrade head

# Generate new migration
alembic revision --autogenerate -m "description"

# Database synchronization commands (see Database Management section below)
python -m src.database.selective_sync --analyze
```

### WNBA Data Scraping
```bash
# Build game URL queue for WNBA seasons
python -m src.scripts.build_game_url_queue

# Test scraping system offline
python -m tests.test_queue_offline

# Run mass scraping (use with caution)
python -m src.scripts.mass_game_scraper
```

## Claude Code Guidelines
- Before writing code, write your plan to `instructions/` as a markdown file. After writing the plan, write your code to a branch that has the same name as the plan.
- After writing your code, write a summary of what you did to `instructions/` as a markdown file.
- After writing your code, push your code to GitHub and create a pull request to the main branch.
- After the pull request is merged, delete the branch.
- Once the branch is deleted, move the instructions to `instructions/archived/`.

## Architecture

The project follows a modular architecture with completed and planned components:

### Completed Components ✅

- **src/scrapers/**: Web scraping logic for WNBA.com game data
  - `team_mapping.py`: WNBA team abbreviation mapping with historical changes (relocations, name changes)
  - `game_url_generator.py`: URL discovery and generation system for WNBA seasons
  - `url_validator.py`: URL accessibility and content validation with concurrent processing
  - `mass_data_extractor.py`: JSON data extraction from `#__NEXT_DATA__` script tags
  - `mass_scraping_queue.py`: Coordinated scraping operations with queue management

- **src/core/**: Core business logic and data models
  - `database.py`: Unified database connection and session management (sync/async support)
  - `models.py`: SQLAlchemy models for teams, games, players, queue management
  - `query_builder.py`: Consolidated query builder system with statistical analysis
  - `config.py`: Centralized configuration management

- **src/database/**: Database schema and queue management
  - `queue_schema.sql`: Enhanced scraping queue structure with comprehensive indexing
  - `enhanced_schema.sql`: Comprehensive normalized database schema for WNBA game data
  - `queue_manager.py`: Queue operations, status tracking, and progress monitoring
  - `database_stats.py`: Comprehensive database statistics and monitoring tool (CLI + module)
  - `selective_sync.py`: Efficient table-by-table synchronization between databases
  - `synchronise_databases.py`: Full database synchronization from local to cloud with migrations

- **src/data_quality/**: Data validation and quality assurance
  - `validation_framework.py`: Comprehensive validation framework for WNBA JSON data

- **src/analytics/**: Essential basketball analytics and tracking systems
  - `possession_tracking.py`: Complete possession-by-possession analysis system
  - `lineup_tracking.py`: Real-time player on/off tracking for any game moment

- **src/scripts/**: Execution scripts and utilities (continued)
  - `json_structure_analyzer.py`: JSON structure analysis across all seasons

- **src/scripts/**: Execution scripts and utilities
  - `build_game_url_queue.py`: Main script for URL queue generation and management
  - `test_queue_offline.py`: Comprehensive testing framework for all components
  - `comprehensive_coverage_report.py`: Gap analysis across all game types and eras
  - `verify_game_id_sequences.py`: Regular season sequence coverage verification
  - `verify_playoff_sequences.py`: Playoff tournament structure validation
  - `retrieve_identified_gaps.py`: Active retrieval of missing games from gap analysis
  - `mass_game_scraper.py`: Concurrent mass scraping with worker threads and rate limiting

### Focus Areas 🎯

This WNBA scraping project is streamlined to focus on:
- **Data Collection**: Efficient scraping of WNBA.com game data
- **Data Storage**: Normalized PostgreSQL database with comprehensive schema
- **Essential Analytics**: Possession tracking and lineup analysis only
- **Data Quality**: Validation and quality assurance for scraped data

### Database Infrastructure ✅

- **PostgreSQL**: Enhanced normalized schema with 16 tables for comprehensive WNBA data storage
- **Database Name**: `wnba_pbp` (local development database)
- **Performance**: Optimized with strategic indexing for basketball analytics
- **Migration System**: Alembic-based schema versioning with selective sync tools
- **Schema Documentation**: Complete table and column reference available in `src/database/README.md`

## Development Setup

This is a Python project focused on WNBA data scraping. When setting up:

1. Create and activate a virtual environment before any Python operations
2. Database configuration will be needed for PostgreSQL connection (`wnba_pbp` database)
3. The project requires web scraping libraries for WNBA.com data extraction

## Database Management

The project includes comprehensive database management tools for development and deployment:

### Key Commands
```bash
# Monitor database statistics and progress  
python -m src.database.database_stats --local   # Local WNBA database

# Selective synchronization (recommended for routine updates)
python -m src.database.selective_sync --analyze --ignore-size    # Check differences
python -m src.database.selective_sync --sync --dry-run --ignore-size  # Preview sync
python -m src.database.selective_sync --sync raw_game_data       # Sync specific table

# Full synchronization (for major updates)  
python -m src.database.synchronise_databases --dry-run  # Preview first
python -m src.database.synchronise_databases            # Full deployment
```

### Development Workflow

#### For Routine Updates (Recommended)
1. **Develop locally** with WNBA dataset in PostgreSQL (`wnba_pbp` database)
2. **Analyze differences** to see what changes need deployment:
   ```bash
   python -m src.database.selective_sync --analyze --ignore-size
   ```
3. **Preview selective sync** with dry-run to validate changes:
   ```bash
   python -m src.database.selective_sync --sync --dry-run --ignore-size
   ```
4. **Deploy specific changes** table by table:
   ```bash
   python -m src.database.selective_sync --sync raw_game_data teams
   ```

#### For Major Updates (Schema Changes)
1. **Preview full synchronization** with dry-run:
   ```bash
   python -m src.database.synchronise_databases --dry-run
   ```
2. **Deploy to target database** with full data and schema synchronization:
   ```bash
   python -m src.database.synchronise_databases
   ```

### Database Synchronization Tools

#### Selective Sync Tool (src/database/selective_sync.py)
**Recommended for routine updates** - Efficient table-by-table synchronization

**Key Features:**
- Smart difference detection (schema, row count, significant size changes)
- Auto-sync mode: Finds and syncs all different tables automatically
- Manual sync: Sync specific tables only
- Large table protection: Tables >1M rows require `--force` flag
- Schema-only or data-only sync options
- Comprehensive safety features with automatic backups

**Common Usage Patterns:**
```bash
# Daily routine check
python -m src.database.selective_sync --analyze --ignore-size

# Sync new scraping data
python -m src.database.selective_sync --sync raw_game_data scraping_sessions

# Auto-sync all differences (safe for routine updates)
python -m src.database.selective_sync --sync --ignore-size

# Force sync large table with verbose progress
python -m src.database.selective_sync --sync play_events --force --verbose

# Preview before major sync
python -m src.database.selective_sync --sync --dry-run
```

**Safety Features:**
- Automatic backups for schema changes (timestamped)
- Batch processing for large tables (10K rows per batch)
- Excluded system/backup tables automatically
- Comprehensive error handling and rollback capabilities

#### Full Sync Tool (src/database/synchronise_databases.py)
**For major schema changes** - Complete database replacement

The full synchronization tool handles:
- Alembic schema migrations
- Complete data replacement with WNBA dataset
- Sequence updates and foreign key constraints
- Batch processing for large datasets
- Error handling and rollback capabilities

## Key Implementation Details

- The WNBA.com game pages contain play-by-play data in a `#__NEXT_DATA__` script tag as JSON (same structure as NBA)
- Game URLs follow the pattern: `wnba.com/game/{away_team}-vs-{home_team}-{game_id}`
- The scraper uses a queue system to track scraping status and manage WNBA games across seasons
- Essential analytics focus on possession tracking and lineup analysis only

## Database Schema Reference

**IMPORTANT**: When writing SQL queries or working with the database, always reference the complete database schema documentation in `src/database/README.md`. This file contains:

- **Exact table names and column names** for all database tables
- **Data types and constraints** for each column  
- **Relationships and foreign keys** between tables
- **Common query patterns** and example SQL queries for WNBA analytics
- **Database views** available for simplified queries

This prevents hallucination of non-existent tables or columns and ensures accurate SQL query generation.

## Current Status
Please use this section to keep track of high-level objectives and their status. Copy the contents over to `README.md` whenever you update this section.

### Objectives

#### Completed Objectives ✅

**Infrastructure & Data Foundation (Plans 01-08)**
- [x] **Plan 01**: Virtual environment setup with all dependencies
- [x] **Plan 02**: PostgreSQL database setup with Alembic migrations
- [x] **Plan 03**: NBA.com scraping implementation with JSON extraction
- [x] **Plan 04**: Comprehensive project planning (Plans 05-21 created)
- [x] **Plan 05**: Test scraping December 2024 (30 games, 100% success rate)
- [x] **Plan 06**: Systematic scraping infrastructure with queue management
- [x] **Plan 07**: Game URL queue building (~30,000 games)
- [x] **Plan 08**: Mass game scraping (8,765+ games successfully processed)

**Data Processing & Schema (Plans 09-12)**
- [x] **Plan 09**: JSON analysis and comprehensive 16-table schema design
- [x] **Plan 10**: Enhanced database schema implementation with optimization
- [x] **Plan 11**: Database population with ETL pipeline for normalized tables
- [x] **Plan 12**: Cloud database migration to Neon with sync tools

**Advanced Features & Infrastructure**
- [x] **On/Off Player Tracking System**: Real-time lineup tracking for any game moment
- [x] **Possession Tracking Implementation**: Complete possession-by-possession analysis
- [x] **Code Audit & Refactoring**: Unified database layer, consolidated query builder
- [x] **Dockerization Strategy**: Multi-service architecture with deployment automation
- [x] **Gap Analysis & Data Quality**: Comprehensive coverage analysis and validation

#### In Progress 🔄
- [ ] **Plan 1-1**: WNBA PBP Database Initialization (Current focus: WNBA data collection and analytics)

#### Future Opportunities 📋
- [ ] **Enhanced Analytics**: Advanced WNBA-specific basketball metrics and insights
- [ ] **Data Export**: Tools for exporting WNBA data in various formats
- [ ] **Visualization**: Dashboard and reporting tools for WNBA analytics
- [ ] **Historical Coverage**: Complete historical WNBA game data collection

