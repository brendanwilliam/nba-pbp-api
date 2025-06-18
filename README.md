# NBA Play-by-Play Data API

Date: 2025-06-14  
Author: Brendan Keane  
Purpose: Comprehensive NBA play-by-play data API with scraping, storage, and query capabilities.

## Project Overview

This project scrapes NBA play-by-play data from the official NBA website, stores it in PostgreSQL, and provides both REST API and MCP server interfaces for querying the data. The system handles all NBA games from the 1996-97 season through 2024-25.

## Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database

### Development Setup
1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and configuration
   ```
5. Set up your PostgreSQL database and run migrations:
   ```bash
   alembic upgrade head
   ```

## Architecture

The project follows a modular architecture:

- **src/scrapers/**: Web scraping logic for NBA.com game data
  - `team_mapping.py`: NBA team abbreviation mapping with historical changes
  - `game_url_generator.py`: URL discovery and generation system
  - `url_validator.py`: URL accessibility and content validation
  - `mass_data_extractor.py`: Enhanced JSON extraction with quality scoring and validation
  - `mass_scraping_queue.py`: Queue management for mass scraping operations
  - `rate_limiter.py`: Rate limiting and request throttling

- **src/core/**: Core business logic and data models
  - `database.py`: Database connection and session management
  - `models.py`: SQLAlchemy models for all database tables

- **src/database/**: Database schema and queue management
  - `queue_schema.sql`: Enhanced scraping queue structure
  - `queue_manager.py`: Queue operations and status tracking
  - `database_stats.py`: Comprehensive database statistics and monitoring tool

- **src/scripts/**: Execution scripts and utilities
  - `build_game_url_queue.py`: Main script for URL queue generation
  - `mass_game_scraper.py`: Concurrent mass scraping with worker threads
  - `test_queue_offline.py`: Comprehensive testing framework

- **src/api/**: RESTful API endpoints (planned)
- **src/analytics/**: Data analysis and insights (planned)

## Current Status

### Completed Objectives ✅
- [x] Create plans for all objectives
- [x] Start small batch test scraping of NBA.com game pages (December 2024)
- [x] Create systematic plan to scrape all games from 1996-97 to 2024-25 seasons
- [x] **Build comprehensive game URL queue system (~30,000 games)**
- [x] **Implement team mapping with historical changes (relocations, name changes)**
- [x] **Create URL validation and accessibility testing framework**
- [x] **Set up enhanced database schema with proper indexing**
- [x] **Comprehensive gap analysis and coverage verification system**
- [x] **Automated missing game retrieval and queue completion**

### In Progress 🔄
- [ ] Execute mass game scraping from populated URL queue
- [ ] Analyze JSON data and design comprehensive database schema
- [ ] Implement complete database schema for parsed data

### Planned 📋
- [ ] Use JSON data to populate normalized database tables
- [ ] Migrate database to cloud infrastructure
- [ ] Create REST API endpoints for querying data
- [ ] Create MCP server for LLM integration
- [ ] Create documentation and testing interfaces
- [ ] Plan scaling, monetization, and maintenance strategies

## Scraping System

The scraping system operates in multiple phases:

### 1. URL Queue Generation (Phase 1 - Completed ✅)
- **Discovery**: Systematic discovery of all NBA games from 1996-2025
- **URL Generation**: Creates `https://www.nba.com/game/{away}-vs-{home}-{gameId}` patterns
- **Team Mapping**: Handles team relocations (Seattle→OKC, New Jersey→Brooklyn, etc.)
- **Queue Population**: Stores ~30,000 game URLs in `game_url_queue` table with metadata
- **Validation**: URL accessibility and content verification system

### 2. Mass Game Scraping (Phase 2 - Next)
- **Execution**: Process queued URLs to extract `#__NEXT_DATA__` JSON
- **Rate Limiting**: Respectful scraping with 1-2 second delays
- **Progress Tracking**: Real-time monitoring and error handling
- **Data Storage**: Raw JSON preservation in `raw_game_data` table

### 3. Data Analysis & Schema Design (Phase 3)
- **JSON Analysis**: Examine structure across different seasons
- **Schema Design**: Create normalized tables for play-by-play, box scores, metadata
- **Data Validation**: Ensure completeness and accuracy

### 4. Database Population (Phase 4)
- **Data Parsing**: Extract structured data from raw JSON
- **Table Population**: Populate normalized database tables
- **Index Creation**: Optimize for query performance

## Usage

### Build Game URL Queue
```bash
# Build complete queue (all seasons 1996-2025)
python -m src.scripts.build_game_url_queue

# Build specific seasons
python -m src.scripts.build_game_url_queue --seasons 2023-24 2024-25

# Validate existing URLs
python -m src.scripts.build_game_url_queue --validate-only

# View queue statistics
python -m src.scripts.build_game_url_queue --stats-only
```

### Mass Game Scraping

Execute mass scraping of games from the populated URL queue:

```bash
# Start mass scraping with default settings (4 workers, 0.5 req/sec)
python -m src.scripts.mass_game_scraper

# Scrape with custom settings
python -m src.scripts.mass_game_scraper --max-workers 8 --rate-limit 1.0

# Scrape specific season only
python -m src.scripts.mass_game_scraper --season 2023-24

# Process limited number of batches (useful for testing)
python -m src.scripts.mass_game_scraper --max-batches 10 --batch-size 50
```

The mass scraper features:
- **Concurrent Processing**: Multiple workers for efficient scraping
- **Rate Limiting**: Respectful scraping with configurable delays
- **Progress Tracking**: Real-time monitoring and resumable operations
- **Error Handling**: Automatic retries and comprehensive error logging
- **Data Extraction**: Uses `mass_data_extractor.py` to extract JSON from `#__NEXT_DATA__`
- **Quality Assessment**: Validates data completeness and scores extraction quality
- **Data Storage**: Raw JSON storage in `raw_game_data` table with metadata

### Database Statistics and Monitoring

Get comprehensive database insights and progress tracking:

```bash
# View complete database report (recommended)
python src/database/database_stats.py

# Or run as a module
python -m src.database.database_stats

# Get full JSON report for detailed analysis
python src/database/database_stats.py --json

# Get insights for specific table
python src/database/database_stats.py --table game_url_queue
```

The database statistics script provides:
- **Database Overview**: Total size, connections, and health metrics
- **Table Analysis**: Row counts, storage sizes, and meaningful insights for each table
- **Progress Tracking**: Scraping completion rates, validation status, and queue metrics
- **Performance Metrics**: JSON data sizes, response times, and efficiency indicators
- **Error Analysis**: Failed games, error patterns, and troubleshooting data

#### Key Insights Provided:
- **`game_url_queue`**: Status distribution, season coverage, completion rates
- **`raw_game_data`**: JSON storage statistics, scraping timeline, data quality
- **`scraping_sessions`**: Performance metrics, success rates, session history
- **`scraping_errors`**: Error patterns, affected games, troubleshooting data

Use this script regularly during mass scraping operations to monitor progress and identify any issues.



## Database
We will use a PostgreSQL database to store the scraped data locally. Once we scrape all games from 1996 to 2025, we will have a complete dataset of NBA play-by-play data. We will then upload this database to the cloud and make it accessible via our API.

## API
The API will be used to query the database for specific play-by-play data. The goal is that we can query the API for plays by team, player, game, game time, date, shot clock, score difference, score totals, etc. All of this data is present in the JSON at `#__NEXT_DATA__` and more specifically play-by-play events.

## MCP
In addition to the API, we will also create a MCP server to serve users play-by-play data when they are working with a LLM. The MCP server will take in natural language queries and return play-by-play data in a format that is easy for the LLM to understand.
