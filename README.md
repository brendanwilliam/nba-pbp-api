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
  - `game_data_scraper.py`: JSON data extraction from game pages
  - `scraping_manager.py`: Coordinated scraping operations

- **src/core/**: Core business logic and data models
  - `database.py`: Database connection and session management
  - `models.py`: SQLAlchemy models for all database tables

- **src/database/**: Database schema and queue management
  - `queue_schema.sql`: Enhanced scraping queue structure
  - `queue_manager.py`: Queue operations and status tracking

- **src/scripts/**: Execution scripts and utilities
  - `build_game_url_queue.py`: Main script for URL queue generation
  - `test_queue_offline.py`: Comprehensive testing framework
  - `demo_queue_building.py`: Working demonstration

- **src/api/**: RESTful API endpoints (planned)
- **src/analytics/**: Data analysis and insights (planned)

## Current Status

### Completed Objectives ✅
- [x] Create plans for all objectives
- [x] Start small batch test scraping of NBA.com game pages (December 2024)
- [x] Create systematic plan to scrape all games from 1996-97 to 2024-25 seasons
- [x] **Build comprehensive game URL queue system (30,000+ games)**
- [x] **Implement team mapping with historical changes (relocations, name changes)**
- [x] **Create URL validation and accessibility testing**
- [x] **Set up enhanced database schema with proper indexing**

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

### Run Tests
```bash
# Offline functionality tests
python -m src.scripts.test_queue_offline

# Demo with sample data
python -m src.scripts.demo_queue_building
```


## Database
We will use a PostgreSQL database to store the scraped data locally. Once we scrape all games from 1996 to 2025, we will have a complete dataset of NBA play-by-play data. We will then upload this database to the cloud and make it accessible via our API.

## API
The API will be used to query the database for specific play-by-play data. The goal is that we can query the API for plays by team, player, game, game time, date, shot clock, score difference, score totals, etc. All of this data is present in the JSON at `#__NEXT_DATA__` and more specifically play-by-play events.

## MCP
In addition to the API, we will also create a MCP server to serve users play-by-play data when they are working with a LLM. The MCP server will take in natural language queries and return play-by-play data in a format that is easy for the LLM to understand.
