# NBA Play-by-Play Data API

Date: 2025-06-20
Author: Brendan Keane  
Purpose: Comprehensive NBA play-by-play data API with scraping, storage, and query capabilities.

## Project Overview

This project scrapes NBA play-by-play data from the official NBA website, stores it in PostgreSQL, and provides both REST API and MCP server interfaces for querying the data. The system handles all NBA games from the 1996-97 season through 2024-25.

### 🏀 **NEW: MCP Server for AI Integration**
The project now includes a Model Context Protocol (MCP) server that enables Large Language Models like Claude to query NBA data using natural language. See the [MCP Server Quick Start Guide](docs/mcp-quick-start.md) for setup instructions.

## Current Status & Commands
As of June 20th, 2025, we are scraping NBA play-by-play data from the official NBA website and storing the raw JSON data in the `raw_game_data` table. We have also created a game URL queue system that contains all games from the 1996-97 season through 2024-25. We are periodically populating the other database tables with the parsed data from the raw JSON data. Here are the commands to run:

```bash
# Build game URL queue
python -m src.scripts.build_game_url_queue

# Mass scrape games from URL queue (10 workers, 1.0 req/sec, 100 games per batch, 10 batches)
python -m src.scripts.mass_game_scraper --max-workers 10 --rate-limit 1.0 --batch-size 100 --max-batches 10

# Populate enhanced schema from raw game data (all games)
python -m src.scripts.populate_enhanced_schema

# Backfill analytics data (lineup tracking) for all games
python -m src.scripts.populate_enhanced_schema --backfill

# Or backfill limited number of games for testing
python -m src.scripts.populate_enhanced_schema --backfill --limit 100

# View database statistics (recommended for monitoring progress)
python -m src.database.database_stats

# RECOMMENDED: Selective database synchronization (efficient, safe)
python -m src.database.selective_sync --analyze --ignore-size    # Check differences
python -m src.database.selective_sync --sync --dry-run --ignore-size  # Preview sync
python -m src.database.selective_sync --sync --ignore-size       # Auto-sync all changes

# Compare local and cloud databases for differences
python -m src.database.database_comparison

# Full database synchronization (for major schema changes only)
python -m src.database.synchronise_databases --dry-run  # Preview changes first
python -m src.database.synchronise_databases            # Full sync (with confirmation)

# Add missing games manually to fill gaps (example: 2006-07 missing games)
python src/scripts/manual_queue_manager.py 0020600151 0020600157 --reference 0020600158

# Then immediately scrape the newly added games
python -m src.scripts.mass_game_scraper --max-workers 3 --rate-limit 2.0 --batch-size 7

# MCP SERVER COMMANDS (NEW)
# Start the MCP server for AI integration
python src/mcp/start_mcp_server.py

# Test MCP server components
pytest src/mcp/tests/ -v

# Test natural language processing
python -c "
import asyncio
from src.mcp.query_translator import NaturalLanguageQueryTranslator
async def test():
    t = NaturalLanguageQueryTranslator()
    c = await t.translate_query('LeBron James career stats')
    print(f'✅ Query understood with {c.confidence:.2f} confidence')
asyncio.run(test())
"
```

### Status Report (2025-06-20)
```
================================================================================
NBA PLAY-BY-PLAY DATABASE REPORT
================================================================================

DATABASE OVERVIEW
   Database: nba_pbp
   Total Size: 7865 MB
   Active Connections: 1

TABLES SUMMARY (21 tables)
--------------------------------------------------------------------------------
Table Name           Size         Rows            Key Insights
--------------------------------------------------------------------------------
play_events          4335 MB      17,398,392      
raw_game_data        1918 MB      36,304          36304 games, 325.93 KB avg
lineup_states        956 MB       3,285,602       
substitution_events  358 MB       1,495,452       
player_game_stats    237 MB       987,675         
team_game_stats      21 MB        72,426          
game_url_queue       20 MB        36,685          98.96% scraped
enhanced_games       9200 kB      36,214          
players              680 kB       3,787           
scraping_queue       168 kB       32              
scrape_queue         96 kB        30              
games                96 kB        30              
teams                88 kB        30              
arenas               64 kB        99              
scraping_errors      64 kB        71              
scraping_sessions    48 kB        61              61 sessions
alembic_version      24 kB        1               
game_periods         16 kB        0               
officials            8192 bytes   0               
game_officials       8192 bytes   0               
season_progress      8192 bytes   0               

KEY METRICS
   Total Games in Queue: 36,685
   Games Completed: 36,304
   Completion Rate: 98.96%
   Games Ready to Scrape: 0
   JSON Data Stored: 11555.26 MB
   Average Game Size: 325.93 KB
================================================================================
```

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
  - `selective_sync.py`: **NEW** - Efficient table-by-table database synchronization
  - `synchronise_databases.py`: Full database replacement synchronization
  - `database_comparison.py`: Comprehensive database difference analysis

- **src/scripts/**: Execution scripts and utilities
  - `build_game_url_queue.py`: Main script for URL queue generation
  - `mass_game_scraper.py`: Concurrent mass scraping with worker threads
  - `test_queue_offline.py`: Comprehensive testing framework

- **src/api/**: RESTful API endpoints (planned)
- **src/analytics/**: Data analysis and insights (planned)

## Documentation

### Comprehensive Guides
- **[Database Management Guide](docs/database-management.md)** - Complete documentation for database synchronization tools
  - Selective sync tool usage and best practices
  - Full synchronization workflows
  - Safety procedures and troubleshooting
  - Development workflows and automation

### API Documentation
- **[API Health Check Guide](instructions/API-health-check.md)** - Comprehensive API testing procedures
- API endpoints documentation (available at `/docs` when running)

### Development Guides
- **[CLAUDE.md](CLAUDE.md)** - Complete project guidance for AI assistants
- Individual instruction files in `instructions/` directory

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
- [x] **Analyze JSON data and design comprehensive database schema (Plan 09)**
- [x] **Implement complete database schema for parsed data (Plan 10)**

### In Progress 🔄
- [ ] Execute mass game scraping from populated URL queue (Plan 08)
- [ ] Use JSON data to populate normalized database tables (Plan 11)

### Planned 📋
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

### 3. Data Analysis & Schema Design (Phase 3 - Completed ✅)
- **JSON Analysis**: Examine structure across different seasons
- **Schema Design**: Create normalized tables for play-by-play, box scores, metadata
- **Data Validation**: Ensure completeness and accuracy

### 4. Database Population (Phase 4 - In Progress 🔄)
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

### Enhanced Schema Population

After scraping games into the `raw_game_data` table, populate the enhanced normalized schema:

```bash
# Populate all unprocessed games from raw_game_data to enhanced schema
python -m src.scripts.populate_enhanced_schema

# Process specific game by ID
python -m src.scripts.populate_enhanced_schema --game-id 0022200650

# Process limited number of games (useful for testing)
python -m src.scripts.populate_enhanced_schema --limit 100

# Dry run to see what would be processed without making changes
python -m src.scripts.populate_enhanced_schema --dry-run --limit 10

# Backfill all analytics-derived data (clears and repopulates lineup tracking tables)
python -m src.scripts.populate_enhanced_schema --backfill

# Backfill limited number of games (useful for testing)
python -m src.scripts.populate_enhanced_schema --backfill --limit 100

# Dry run backfill to see what would be done
python -m src.scripts.populate_enhanced_schema --backfill --dry-run --limit 10
```

The enhanced schema population features:
- **Data Extraction**: Parses JSON from `raw_game_data.raw_json` into normalized tables
- **Smart Filtering**: Automatically skips invalid games (schedule pages, incomplete data)
- **Idempotent**: Can safely rerun without creating duplicates
- **Comprehensive Data**: Populates `enhanced_games`, `play_events`, `player_game_stats`, `team_game_stats`, `arenas`
- **Player Management**: Automatically creates missing players from game data
- **NBA Team ID Support**: Handles official NBA.com team IDs (1610612xxx format)
- **Error Handling**: Individual game failures don't stop the entire process
- **Progress Tracking**: Real-time status updates and summary statistics
- **Analytics Integration**: Includes lineup tracking and substitution event extraction
- **Backfill Support**: `--backfill` flag clears and repopulates analytics tables with latest algorithms

#### Enhanced Schema Tables:
- **`enhanced_games`**: Core game information (teams, scores, dates, arenas)
- **`play_events`**: Complete play-by-play events with detailed metadata
- **`player_game_stats`**: Individual player statistics per game
- **`team_game_stats`**: Team-level statistics per game
- **`arenas`**: Venue information with capacity and location data
- **`officials`**: Game officials and referee assignments
- **`game_periods`**: Period-by-period scoring breakdown
- **`lineup_states`**: On-court player lineups at each moment of the game
- **`substitution_events`**: Detailed substitution tracking with timing and player info

### Manual Queue Management

Add specific games or fill gaps in the scraping queue using the manual queue manager:

```bash
# Add a single game (uses reference game for metadata)
python src/scripts/manual_queue_manager.py 0040800306 0040800306 --reference 0040800305

# Add a range of consecutive games (fill sequence gaps)
python src/scripts/manual_queue_manager.py 0029700001 0029700014 --reference 0029700015

# Preview what would be added without inserting (dry run)
python src/scripts/manual_queue_manager.py 0021400765 0021400773 --reference 0021400774 --dry-run

# Add games with URL validation (currently disabled due to import issues)
python src/scripts/manual_queue_manager.py 0041300215 0041300225 --reference 0041300214 --validate
```

#### Manual Queue Manager Features:
- **Gap Filling**: Add missing games identified in sequence analysis
- **Reference Metadata**: Copies season, date, type, and priority from existing games
- **Ready for Scraping**: Games added with `validated` status for immediate processing
- **Conflict Handling**: Automatically skips games that already exist in queue
- **Dry Run Mode**: Preview changes before execution
- **Flexible Input**: Handles single games, consecutive ranges, or non-consecutive lists

#### Common Use Cases:
```bash
# Fill identified gaps from database analysis
python src/scripts/manual_queue_manager.py 0020600151 0020600157 --reference 0020600158

# Add playoff games that were missed
python src/scripts/manual_queue_manager.py 0040900105 0040900105 --reference 0040900104
python src/scripts/manual_queue_manager.py 0040900135 0040900135 --reference 0040900134

# After adding games, immediately scrape them
python -m src.scripts.mass_game_scraper --max-workers 3 --rate-limit 2.0 --batch-size 10
```

#### Finding Missing Games:
Use database statistics to identify gaps:
```bash
# View games by season and type to spot missing counts
python src/database/database_stats.py --by-season

# Get detailed queue insights
python src/database/database_stats.py --table game_url_queue
```

### Database Management and Monitoring

#### Database Statistics

Get comprehensive database insights and progress tracking:

```bash
# View complete database report (recommended)
python -m src.database.database_stats

# View games by season and type breakdown
python -m src.database.database_stats --by-season

# Get full JSON report for detailed analysis
python -m src.database.database_stats --json

# Get insights for specific table
python -m src.database.database_stats --table game_url_queue

# Compare specific databases (local vs cloud)
python -m src.database.database_stats --local    # Use local PostgreSQL
python -m src.database.database_stats --neon     # Use Neon cloud database
```

#### Database Comparison

Compare schemas and data between local and cloud databases:

```bash
# Compare local and Neon databases (shows differences)
python -m src.database.database_comparison

# Get detailed JSON comparison report
python -m src.database.database_comparison --json

# Use custom database URLs
python -m src.database.database_comparison --local-url "postgresql://user@host/db" --neon-url "postgresql://user@host/db2"
```

The comparison tool provides:
- **Schema Differences**: Missing tables, column mismatches, index differences
- **Row Count Differences**: Data synchronization status between databases
- **Summary Report**: Quick overview of database consistency

#### Database Synchronization

Synchronize local development changes to cloud database:

```bash
# ALWAYS run dry-run first to preview changes
python -m src.database.synchronise_databases --dry-run

# Full synchronization (WARNING: Overwrites all Neon data with local data)
python -m src.database.synchronise_databases

# Sync only specific tables
python -m src.database.synchronise_databases --tables raw_game_data player_game_stats

# Get JSON output for automation
python -m src.database.synchronise_databases --json

# Use custom database URLs
python -m src.database.synchronise_databases --local-url "postgresql://user@host/local" --neon-url "postgresql://user@host/cloud"
```

**⚠️ WARNING**: Synchronization completely replaces cloud data with local data. Features include:
- **Alembic Migrations**: Automatically runs schema migrations on target database
- **Full Data Replacement**: Truncates and repopulates all tables
- **Batch Processing**: Efficient handling of millions of rows
- **Sequence Updates**: Maintains proper auto-increment values
- **Safety Features**: Dry-run mode, confirmation prompts, error handling

**Development Workflow**:
1. Develop and test locally with full dataset
2. Run comparison to see differences: `python -m src.database.database_comparison`
3. Preview sync changes: `python -m src.database.synchronise_databases --dry-run`
4. Deploy to cloud: `python -m src.database.synchronise_databases`

The database statistics script provides:
- **Database Overview**: Total size, connections, and health metrics
- **Table Analysis**: Row counts, storage sizes, and meaningful insights for each table
- **Progress Tracking**: Scraping completion rates, validation status, and queue metrics
- **Performance Metrics**: JSON data sizes, response times, and efficiency indicators
- **Error Analysis**: Failed games, error patterns, and troubleshooting data

Use these scripts regularly during development and deployment to monitor progress and maintain database consistency.



## Database
We will use a PostgreSQL database to store the scraped data locally. Once we scrape all games from 1996 to 2025, we will have a complete dataset of NBA play-by-play data. We will then upload this database to the cloud and make it accessible via our API.

## API
The API will be used to query the database for specific play-by-play data. The goal is that we can query the API for plays by team, player, game, game time, date, shot clock, score difference, score totals, etc. All of this data is present in the JSON at `#__NEXT_DATA__` and more specifically play-by-play events.

## API Testing & Usage

### Starting the API Server

Before testing the API, start the server from the project root:

```bash
# Activate virtual environment first
source venv/bin/activate

# Start the API server with correct Python path
PYTHONPATH=/Users/brendan/nba-pbp-api python src/api/start_api.py
```

The API will be available at:
- **Main API**: http://localhost:8000
- **Interactive Documentation**: http://localhost:8000/docs  
- **Alternative Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Working Endpoints

#### 1. Health Check
```bash
curl http://localhost:8000/health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-24T04:23:14.982451",
  "service": "NBA Play-by-Play API", 
  "version": "1.0.0"
}
```

#### 2. System Metrics
```bash
curl http://localhost:8000/metrics
```
**Response:**
```json
{
  "status": "operational",
  "timestamp": "2025-06-24T04:23:24.281649",
  "placeholder": "Metrics will be implemented with Redis/Prometheus"
}
```

#### 3. Available API Endpoints
The API provides these endpoints (from OpenAPI schema):
- `GET /health` - Health check
- `GET /metrics` - System metrics
- `GET /api/v1/players/search` - Player search
- `GET /api/v1/teams/search` - Team search  
- `POST /api/v1/player-stats` - Advanced player statistics
- `GET /api/v1/players/{player_id}/stats` - Individual player stats
- `POST /api/v1/team-stats` - Advanced team statistics
- `GET /api/v1/teams/{team_id}/stats` - Individual team stats
- `GET /api/v1/teams/{team_id}/head-to-head/{opponent_team_id}` - Team comparisons
- `POST /api/v1/lineup-stats` - Lineup analysis
- `GET /api/v1/lineups/common/{team_id}` - Common lineups
- `GET /api/v1/lineups/player-combinations` - Player combination analysis

### Current Database Schema

The database contains these key tables with the following structure:

#### Players Table
- `id` (integer) - Primary key
- `nba_id` (varchar) - NBA official player ID
- `player_name` (varchar) - Full player name
- `first_name`, `last_name` (varchar) - Name components
- `position` (varchar) - Playing position
- `jersey_number` (varchar) - Jersey number
- `team_id` (integer) - Current team ID

#### Teams Table  
- `id` (integer) - Primary key
- `tricode` (varchar) - Team abbreviation (e.g., 'LAL', 'BOS')
- `full_name` (varchar) - Full team name
- `nba_team_id` (varchar) - NBA official team ID
- `conference`, `division` (varchar) - League organization
- `arena` (varchar) - Home arena name

#### Player Game Stats Table
Key statistical columns:
- `player_id`, `game_id`, `team_id` - Identifiers
- `points`, `assists`, `rebounds_total` - Basic stats
- `field_goals_made/attempted`, `three_pointers_made/attempted` - Shooting
- `free_throws_made/attempted` - Free throws
- `steals`, `blocks`, `turnovers`, `fouls_personal` - Other stats
- `minutes_played`, `plus_minus` - Advanced metrics

### Sample Data Queries

#### Database Statistics
Current database contains:
- **1,000,298 player game stat records**
- **3,787 unique players**
- **36,304 games with JSON data**
- **17,398,392 play-by-play events**

#### Sample Player Data
```bash
# Query database directly to see sample data
PYTHONPATH=/Users/brendan/nba-pbp-api python -c "
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://localhost:5432/nba_pbp'))
cur = conn.cursor()

# Get high-scoring games
cur.execute('SELECT p.player_name, pgs.points, pgs.assists, pgs.rebounds_total, pgs.game_id FROM player_game_stats pgs JOIN players p ON p.id = pgs.player_id WHERE pgs.points >= 40 ORDER BY pgs.points DESC LIMIT 5')
for row in cur.fetchall():
    print(f'{row[0]}: {row[1]} pts, {row[2]} ast, {row[3]} reb (Game {row[4]})')
conn.close()
"
```

### Known Issues (Development Status)

⚠️ **Current API Issues:**
1. **Player/Team Search Endpoints**: Database schema mismatch - looking for columns that don't exist
2. **Statistics Endpoints**: SQL query errors due to incorrect table aliases
3. **Column Name Mismatches**: API expects different column names than database schema

**Error Examples:**
```bash
# These currently return errors:
curl "http://localhost:8000/api/v1/players/search?query=LeBron"
# Error: column "player_id" does not exist

curl -X POST "http://localhost:8000/api/v1/player-stats" \
  -H "Content-Type: application/json" \
  -d '{"season": "latest", "limit": 5}'
# Error: column p.player_id does not exist
```

### Manual Database Testing

While the API endpoints are being fixed, you can query the database directly:

```bash
# Activate environment and test database queries
source venv/bin/activate
PYTHONPATH=/Users/brendan/nba-pbp-api python -c "
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Find top scorers
print('Top single-game performances:')
cur.execute('''
    SELECT p.player_name, pgs.points, pgs.game_id 
    FROM player_game_stats pgs 
    JOIN players p ON p.id = pgs.player_id 
    WHERE pgs.points >= 50 
    ORDER BY pgs.points DESC 
    LIMIT 10
''')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]} points (Game {row[2]})')

conn.close()
"
```

### Development Roadmap

1. **Fix API Schema Issues** - Update SQL queries to match actual database schema
2. **Implement Search Functionality** - Fix player/team search endpoints  
3. **Add Advanced Filtering** - Enable complex statistical queries
4. **Performance Optimization** - Add database indexing for common queries
5. **Authentication & Rate Limiting** - Secure the API for production use

### Interactive API Documentation

Once the API issues are resolved, use the interactive documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide a web interface to test all endpoints with real-time validation and examples.

## MCP
In addition to the API, we will also create a MCP server to serve users play-by-play data when they are working with a LLM. The MCP server will take in natural language queries and return play-by-play data in a format that is easy for the LLM to understand.
