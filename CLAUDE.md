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
# Database setup and migrations (recommended approach)
python -m src.database.database            # Create DB, run migrations, test connection
python -m src.database.database migrate    # Create DB and run migrations only
python -m src.database.database status     # Check migration status
python -m src.database.database create     # Create database only

# Direct Alembic commands (advanced usage)
alembic revision --autogenerate -m "description"  # Generate new migration
alembic upgrade head                               # Apply migrations directly

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

- **src/database/**: Database layer with modern ORM architecture
  - `database.py`: Database creation, Alembic migration management, and CLI interface
  - `models.py`: SQLAlchemy ORM models (RawGameData with JSONB, ScrapingSession, DatabaseVersion)  
  - `services.py`: Service layer for clean database operations with context management
  - `queue_manager.py`: Queue operations, status tracking, and progress monitoring
  - `database_stats.py`: Comprehensive database statistics and monitoring tool (CLI + module)
  - `selective_sync.py`: Efficient table-by-table synchronization between databases
  - `synchronise_databases.py`: Full database synchronization from local to cloud with migrations

- **src/analytics/**: Essential basketball analytics and tracking systems

- **src/scripts/**: Execution scripts and utilities

### Focus Areas 🎯

This WNBA scraping project is streamlined to focus on:
- **Data Collection**: Efficient scraping of WNBA.com game data
- **Data Storage**: Normalized PostgreSQL database with comprehensive schema
- **Essential Analytics**: Possession tracking and lineup analysis only
- **Data Quality**: Validation and quality assurance for scraped data

### Database Infrastructure ✅

- **PostgreSQL**: Modern ORM-based schema with SQLAlchemy models
- **Database Name**: `wnba` (local development database)  
- **Core Tables**: `raw_game_data` (JSONB), `scraping_sessions`, `database_versions`
- **Migration System**: Alembic with automated database creation and version management
- **Service Layer**: Context-managed database operations through `services.py`
- **Performance**: JSONB indexing for efficient game data queries

## Database Service Layer Architecture

The project uses a clean service layer pattern for database operations:

### Core Components
- **`DatabaseService`**: Main coordinator with context management
- **`GameDataService`**: Handles raw game data CRUD operations  
- **`ScrapingSessionService`**: Manages scraping session tracking

### Usage Patterns
```python
# Simple operations
from src.database.services import insert_scraped_game
success = insert_scraped_game(game_id, season, game_type, url, data)

# Complex operations with context management
from src.database.services import DatabaseService
with DatabaseService() as db:
    game = db.game_data.get_game_data(game_id)
    session = db.scraping_session.start_session("My Session")
```

### Key Benefits
- **Automatic session management** with context managers
- **Error handling and rollback** built-in
- **Type-safe operations** with proper validation
- **Clean separation** between data access and business logic

## Development Setup

This is a Python project focused on WNBA data scraping. When setting up:

1. Create and activate a virtual environment before any Python operations
2. Database configuration will be needed for PostgreSQL connection (environment variables)
3. The project requires web scraping libraries for WNBA.com data extraction

## Database Management

The project includes comprehensive database management tools for development and deployment:

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

