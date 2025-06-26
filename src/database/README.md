# Database Module

This module manages the database schema and queue operations for the NBA scraping system.

## Files

### queue_schema.sql

**Purpose**: Defines the PostgreSQL database schema for managing web scraping queue operations, tracking NBA game scraping with comprehensive status management, error handling, and performance metrics.

**Database Schema**:

#### Tables:

1. **`scraping_queue`** - Main queue table for tracking games to scrape
   - Core fields: `id`, `game_id`, `season`, `game_date`, `home_team`, `away_team`, `game_url`
   - Status tracking: `status` (pending/in_progress/completed/failed/invalid)
   - Retry management: `retry_count`, `max_retries` (default 3)
   - Priority system: `priority` (higher = processed first)
   - Timestamps: `created_at`, `updated_at`, `started_at`, `completed_at`
   - Error tracking: `error_message`, `error_code`
   - Performance metrics: `response_time_ms`, `data_size_bytes`

2. **`scraping_sessions`** - Session tracking and performance statistics
   - Session metadata and aggregate metrics
   - Tracks total/successful/failed games per session
   - Average response time and throughput statistics

3. **`scraping_errors`** - Detailed error logging
   - Links to `game_id` and `session_id`
   - Stores error type, code, message, and stack trace
   - Retry attempt tracking

4. **`season_progress`** - Season-level progress tracking
   - Total games per season
   - Counts of scraped/failed/invalid games
   - Progress percentage calculation

#### Key Features:
- **Indexes**: Optimized for status, season, date, and priority-based queries
- **Views**: `queue_status_summary`, `season_progress_view` for reporting
- **Triggers**: Automatic `updated_at` timestamp management
- **Row-level locking**: Support for concurrent queue processing

### queue_manager.py

**Purpose**: Python async interface for managing the scraping queue database operations with comprehensive status tracking, retry logic, and progress monitoring.

**Classes**:

#### `QueueStatus` (Enum)
Status constants for queue items:
- `PENDING` - Not yet started
- `IN_PROGRESS` - Currently being processed
- `COMPLETED` - Successfully scraped
- `FAILED` - Failed after max retries
- `INVALID` - Permanently invalid URL

#### `GameQueueItem` (Dataclass)
Represents a game in the scraping queue:
```python
GameQueueItem(
    game_id="0021700001",
    season="2017-18",
    game_date=datetime(2017, 10, 17),
    home_team="CLE",
    away_team="BOS",
    game_url="https://nba.com/game/bos-vs-cle-0021700001",
    status=QueueStatus.PENDING,
    retry_count=0,
    priority=0
)
```

#### `QueueManager` (Main Class)

**Initialization**:
```python
queue_manager = QueueManager(db_url="postgresql://user:pass@localhost/nba_db")
await queue_manager.initialize()
```

**Key Methods**:

1. **`add_games_to_queue(games: List[GameQueueItem])`** - Bulk insert games
   ```python
   games = [GameQueueItem(...), GameQueueItem(...)]
   inserted_count = await queue_manager.add_games_to_queue(games)
   ```

2. **`get_next_games(batch_size: int = 10)`** - Fetch games for processing
   ```python
   games_batch = await queue_manager.get_next_games(batch_size=20)
   ```
   - Uses PostgreSQL row-level locking (`FOR UPDATE SKIP LOCKED`)
   - Automatically marks games as "in_progress" 
   - Orders by priority and game date

3. **`mark_game_completed(game_id, response_time_ms, data_size_bytes)`** - Mark successful scrape
   ```python
   await queue_manager.mark_game_completed("0021700001", 1500, 250000)
   ```

4. **`mark_game_failed(game_id, error_message, error_code)`** - Handle failures
   ```python
   await queue_manager.mark_game_failed("0021700001", "Connection timeout", 504)
   ```
   - Automatically increments retry count
   - Moves to "failed" status after max retries

5. **`mark_game_invalid(game_id, reason)`** - Mark permanently invalid URLs
   ```python
   await queue_manager.mark_game_invalid("0021700001", "404 - Game not found")
   ```

6. **`get_queue_stats()`** - Get queue statistics
   ```python
   stats = await queue_manager.get_queue_stats()
   # Returns: {pending: 1000, in_progress: 10, completed: 500, ...}
   ```

7. **`get_season_progress()`** - Get progress by season
   ```python
   progress = await queue_manager.get_season_progress()
   # Returns list of season progress dictionaries
   ```

8. **`reset_stale_games(timeout_minutes)`** - Reset stuck games
   ```python
   await queue_manager.reset_stale_games(timeout_minutes=30)
   ```

9. **`initialize_season_progress(season_game_counts)`** - Set up season tracking
   ```python
   await queue_manager.initialize_season_progress({
       "2023-24": 1230,
       "2022-23": 1230
   })
   ```

**Usage Pattern**:
```python
async def main():
    # Initialize
    manager = QueueManager("postgresql://localhost/nba_db")
    await manager.initialize()
    
    # Add games
    games = [GameQueueItem(...) for _ in range(100)]
    await manager.add_games_to_queue(games)
    
    # Process games
    while True:
        batch = await manager.get_next_games(10)
        if not batch:
            break
            
        for game in batch:
            try:
                # Scrape game...
                await manager.mark_game_completed(game['game_id'], 1000, 200000)
            except Exception as e:
                await manager.mark_game_failed(game['game_id'], str(e))
    
    # Cleanup
    await manager.close()
```

## Features

- **Atomic Operations**: Database operations use transactions and row-level locking
- **Concurrent Processing**: Multiple workers can safely process the queue simultaneously
- **Retry Logic**: Automatic retry handling with configurable limits
- **Progress Tracking**: Comprehensive statistics at queue, session, and season levels
- **Error Management**: Detailed error logging and analysis
- **Performance Monitoring**: Response time and data size tracking

## Complete Database Schema Reference

This section provides comprehensive documentation of all tables and their exact column names for SQL query reference.

### Core Entity Tables

#### `teams`
```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    tricode VARCHAR(3) UNIQUE NOT NULL,           -- "BOS", "LAL", etc.
    name VARCHAR(100) NOT NULL,                   -- "Boston Celtics"
    city VARCHAR(50) NOT NULL,                    -- "Boston"
    team_id INTEGER,                              -- NBA's internal team ID
    team_tricode VARCHAR(3),                      -- duplicate of tricode
    full_name VARCHAR(100),                       -- "Boston Celtics"
    nickname VARCHAR(50),                         -- "Celtics"
    founded INTEGER,                              -- year founded
    arena VARCHAR(100),                           -- arena name
    arena_capacity INTEGER,                       -- capacity
    owner VARCHAR(200),                           -- owner(s)
    general_manager VARCHAR(100),                 -- GM name
    head_coach VARCHAR(100),                      -- coach name
    d_league_affiliate VARCHAR(100),              -- G-League team
    conference VARCHAR(10),                       -- "East"/"West"
    division VARCHAR(20),                         -- "Atlantic", etc.
    wikipedia_url VARCHAR(200),                   -- Wikipedia link
    basketball_ref_url VARCHAR(200),              -- Basketball Reference link
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `players`
```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    nba_id VARCHAR(20) UNIQUE NOT NULL,           -- NBA's player ID
    first_name VARCHAR(50) NOT NULL,              -- "LeBron"
    last_name VARCHAR(50) NOT NULL,               -- "James"
    jersey_number VARCHAR(3),                     -- "23"
    position VARCHAR(10),                         -- "PG", "SG", "SF", "PF", "C"
    team_id INTEGER REFERENCES teams(id),         -- current team
    person_id VARCHAR(20),                        -- same as nba_id
    player_name VARCHAR(100),                     -- "LeBron James"
    player_name_i VARCHAR(100),                   -- "James, LeBron"
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `player_team` (Junction Table)
```sql
CREATE TABLE player_team (
    id INTEGER PRIMARY KEY,
    person_id VARCHAR(20) NOT NULL,               -- player ID
    team_id INTEGER NOT NULL,                     -- team ID
    jersey_number VARCHAR(3),                     -- jersey number with team
    position VARCHAR(10),                         -- position with team
    start_date DATE,                              -- when joined team
    end_date DATE,                                -- when left team
    is_active BOOLEAN DEFAULT TRUE,               -- currently on team
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Game Management Tables

#### `games` (Original)
```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY,
    nba_game_id VARCHAR(20) UNIQUE NOT NULL,      -- "0021700001"
    game_date DATE NOT NULL,                      -- game date
    home_team_id INTEGER REFERENCES teams(id),    -- home team
    away_team_id INTEGER REFERENCES teams(id),    -- away team
    season VARCHAR(10) NOT NULL,                  -- "2024-25"
    game_type VARCHAR(20) NOT NULL,               -- "Regular Season", "Playoffs"
    game_url VARCHAR(500),                        -- NBA.com game URL
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `enhanced_games` (Enhanced)
```sql
CREATE TABLE enhanced_games (
    game_id VARCHAR(20) PRIMARY KEY,              -- "0021700001"
    game_code VARCHAR(50) NOT NULL,               -- internal game code
    game_status INTEGER NOT NULL,                 -- 1=scheduled, 2=live, 3=final
    game_status_text VARCHAR(20),                 -- "Final"
    season VARCHAR(10) NOT NULL,                  -- "2024-25"
    game_date DATE NOT NULL,                      -- game date
    game_time_utc TIMESTAMP,                      -- game time UTC
    game_time_et TIMESTAMP,                       -- game time Eastern
    home_team_id INTEGER NOT NULL,                -- home team ID
    away_team_id INTEGER NOT NULL,                -- away team ID
    home_score INTEGER,                           -- final home score
    away_score INTEGER,                           -- final away score
    period INTEGER,                               -- current/final period
    game_clock VARCHAR(20),                       -- game clock display
    duration VARCHAR(10),                         -- game duration
    attendance INTEGER,                           -- attendance figure
    sellout BOOLEAN DEFAULT FALSE,                -- was it a sellout
    series_game_number VARCHAR(10),               -- "Game 1" for playoffs
    game_label VARCHAR(100),                      -- display label
    game_sub_label VARCHAR(100),                  -- sub label
    series_text VARCHAR(100),                     -- series description
    if_necessary BOOLEAN DEFAULT FALSE,           -- elimination game
    arena_id INTEGER REFERENCES arenas(arena_id), -- arena reference
    is_neutral BOOLEAN DEFAULT FALSE,             -- neutral site game
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Supporting Tables

#### `arenas`
```sql
CREATE TABLE arenas (
    arena_id INTEGER PRIMARY KEY,                 -- NBA arena ID
    arena_name VARCHAR(100) NOT NULL,             -- "TD Garden"
    arena_city VARCHAR(100) NOT NULL,             -- "Boston"
    arena_state VARCHAR(10),                      -- "MA"
    arena_country VARCHAR(3) DEFAULT 'US',        -- country code
    arena_timezone VARCHAR(50),                   -- timezone
    arena_street_address TEXT,                    -- street address
    arena_postal_code VARCHAR(20),                -- zip code
    capacity INTEGER,                             -- seating capacity
    created_at TIMESTAMP
);
```

#### `officials`
```sql
CREATE TABLE officials (
    official_id INTEGER PRIMARY KEY,              -- official ID
    official_name VARCHAR(100) NOT NULL,          -- full name
    name_i VARCHAR(50),                           -- "Last, First"
    first_name VARCHAR(50),                       -- first name
    family_name VARCHAR(50),                      -- last name
    jersey_num VARCHAR(10),                       -- referee number
    created_at TIMESTAMP
);
```

### Game Statistics Tables

#### `team_game_stats`
```sql
CREATE TABLE team_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) REFERENCES enhanced_games(game_id),
    team_id INTEGER NOT NULL,                     -- team ID
    is_home_team BOOLEAN NOT NULL,                -- home/away flag
    stat_type VARCHAR(20) DEFAULT 'team',         -- 'team', 'starters', 'bench'
    wins INTEGER,                                 -- season wins
    losses INTEGER,                               -- season losses
    in_bonus BOOLEAN,                             -- in bonus situation
    timeouts_remaining INTEGER,                   -- timeouts left
    seed INTEGER,                                 -- playoff seed
    
    -- Shooting Statistics
    field_goals_made INTEGER,                     -- FGM
    field_goals_attempted INTEGER,                -- FGA
    field_goals_percentage DECIMAL(5,3),          -- FG%
    three_pointers_made INTEGER,                  -- 3PM
    three_pointers_attempted INTEGER,             -- 3PA
    three_pointers_percentage DECIMAL(5,3),       -- 3P%
    free_throws_made INTEGER,                     -- FTM
    free_throws_attempted INTEGER,                -- FTA
    free_throws_percentage DECIMAL(5,3),          -- FT%
    
    -- Rebounding
    rebounds_offensive INTEGER,                   -- OREB
    rebounds_defensive INTEGER,                   -- DREB
    rebounds_total INTEGER,                       -- REB
    
    -- Other Core Stats
    assists INTEGER,                              -- AST
    steals INTEGER,                               -- STL
    blocks INTEGER,                               -- BLK
    turnovers INTEGER,                            -- TO
    fouls_personal INTEGER,                       -- PF
    points INTEGER,                               -- PTS
    plus_minus_points INTEGER,                    -- +/-
    
    -- Advanced Stats
    points_fast_break INTEGER,                    -- fast break points
    points_in_paint INTEGER,                      -- paint points
    points_second_chance INTEGER,                 -- second chance points
    
    created_at TIMESTAMP
);
```

#### `player_game_stats`
```sql
CREATE TABLE player_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) REFERENCES enhanced_games(game_id),
    player_id INTEGER REFERENCES players(id),
    team_id INTEGER NOT NULL,                     -- team ID
    jersey_number VARCHAR(10),                    -- jersey number
    position VARCHAR(10),                         -- position played
    starter BOOLEAN DEFAULT FALSE,                -- was starter
    active BOOLEAN DEFAULT TRUE,                  -- was active
    dnp_reason VARCHAR(100),                      -- did not play reason
    
    -- Same shooting/rebounding/stats structure as team_game_stats
    field_goals_made INTEGER,
    field_goals_attempted INTEGER,
    field_goals_percentage DECIMAL(5,3),
    three_pointers_made INTEGER,
    three_pointers_attempted INTEGER,
    three_pointers_percentage DECIMAL(5,3),
    free_throws_made INTEGER,
    free_throws_attempted INTEGER,
    free_throws_percentage DECIMAL(5,3),
    rebounds_offensive INTEGER,
    rebounds_defensive INTEGER,
    rebounds_total INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    fouls_personal INTEGER,
    points INTEGER,
    plus_minus INTEGER,                           -- +/- (note: INTEGER not plus_minus_points)
    points_fast_break INTEGER,
    points_in_paint INTEGER,
    points_second_chance INTEGER,
    
    created_at TIMESTAMP
);
```

### Play-by-Play Tables

#### `play_events`
```sql
CREATE TABLE play_events (
    event_id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) REFERENCES enhanced_games(game_id),
    
    -- Timing Information
    period INTEGER,                               -- quarter/overtime number
    time_remaining VARCHAR(20),                   -- clock time remaining
    time_elapsed_seconds INTEGER,                 -- seconds elapsed in period
    
    -- Event Details
    event_type VARCHAR(50),                       -- "Made Shot", "Missed Shot", "Foul"
    event_action_type VARCHAR(100),               -- detailed action type
    event_sub_type VARCHAR(100),                  -- sub-type of event
    description TEXT,                             -- text description
    
    -- Score Information
    home_score INTEGER,                           -- home score after event
    away_score INTEGER,                           -- away score after event
    score_margin INTEGER,                         -- point differential
    
    -- Player/Team Information
    player_id INTEGER,                            -- primary player involved
    team_id INTEGER,                              -- team of primary player
    assist_player_id INTEGER,                     -- assisting player (if applicable)
    
    -- Shot Data (when applicable)
    shot_distance INTEGER,                        -- distance in feet
    shot_made BOOLEAN,                            -- made/missed
    shot_type VARCHAR(50),                        -- "2PT Field Goal", "3PT Field Goal"
    shot_zone VARCHAR(100),                       -- court zone description
    shot_x DECIMAL(8,4),                          -- X coordinate on court
    shot_y DECIMAL(8,4),                          -- Y coordinate on court
    
    -- Other Event Data
    event_order INTEGER,                          -- order within game
    possession_change BOOLEAN,                    -- did possession change
    video_available BOOLEAN,                      -- is video available
    
    created_at TIMESTAMP
);
```

#### `substitution_events`
```sql
CREATE TABLE substitution_events (
    id INTEGER PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,                 -- game reference
    action_number INTEGER,                        -- event sequence number
    period INTEGER,                               -- quarter/overtime
    seconds_elapsed INTEGER,                      -- seconds into period
    clock_time VARCHAR(20),                       -- displayed clock time
    team_id BIGINT,                               -- team making substitution
    player_out_id BIGINT,                         -- player leaving game
    player_in_id BIGINT,                          -- player entering game
    player_out_name VARCHAR(100),                 -- name of player leaving
    player_in_name VARCHAR(100),                  -- name of player entering
    description TEXT,                             -- substitution description
    created_at TIMESTAMP
);
```

#### `lineup_states`
```sql
CREATE TABLE lineup_states (
    id INTEGER PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,                 -- game reference
    period INTEGER,                               -- quarter/overtime
    seconds_elapsed INTEGER,                      -- seconds into period
    clock_time VARCHAR(20),                       -- displayed clock time
    team_id BIGINT,                               -- team lineup
    player_1_id BIGINT,                           -- player 1 on court
    player_2_id BIGINT,                           -- player 2 on court
    player_3_id BIGINT,                           -- player 3 on court
    player_4_id BIGINT,                           -- player 4 on court
    player_5_id BIGINT,                           -- player 5 on court
    lineup_hash VARCHAR(64),                      -- unique lineup identifier
    created_at TIMESTAMP
);
```

### Scraping and Queue Management Tables

#### `raw_game_data`
```sql
CREATE TABLE raw_game_data (
    id INTEGER PRIMARY KEY,
    game_id VARCHAR(20) UNIQUE NOT NULL,          -- NBA game ID
    game_url TEXT NOT NULL,                       -- source URL
    raw_json JSON NOT NULL,                       -- complete NBA.com JSON
    scraped_at TIMESTAMP,                         -- when scraped
    json_size INTEGER,                            -- size in bytes
    processing_status VARCHAR(20) DEFAULT 'raw'   -- 'raw', 'processed', 'failed'
);
```

#### `scrape_queue` (Legacy)
```sql
CREATE TABLE scrape_queue (
    id INTEGER PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),         -- game to scrape
    status VARCHAR(20) DEFAULT 'pending',         -- scraping status
    attempts INTEGER DEFAULT 0,                   -- retry attempts
    last_attempt TIMESTAMP,                       -- last attempt time
    error_message TEXT,                           -- error details
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `scraping_queue` (Enhanced)
```sql
CREATE TABLE scraping_queue (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) UNIQUE NOT NULL,          -- NBA game ID
    season VARCHAR(10),                           -- "2024-25"
    game_date DATE,                               -- game date
    home_team VARCHAR(3),                         -- home team tricode
    away_team VARCHAR(3),                         -- away team tricode
    game_url TEXT,                                -- NBA.com URL
    status VARCHAR(20) DEFAULT 'pending',         -- queue status
    retry_count INTEGER DEFAULT 0,                -- current retry count
    max_retries INTEGER DEFAULT 3,                -- maximum retries
    priority INTEGER DEFAULT 0,                   -- processing priority
    created_at TIMESTAMP,                         -- when queued
    updated_at TIMESTAMP,                         -- last updated
    started_at TIMESTAMP,                         -- when started
    completed_at TIMESTAMP,                       -- when completed
    error_message TEXT,                           -- error details
    error_code INTEGER,                           -- HTTP/error code
    response_time_ms INTEGER,                     -- response time
    data_size_bytes INTEGER                       -- response size
);
```

#### `scraping_sessions`
```sql
CREATE TABLE scraping_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID,                              -- unique session ID
    started_at TIMESTAMP,                         -- session start
    ended_at TIMESTAMP,                           -- session end
    total_games INTEGER,                          -- games attempted
    successful_games INTEGER,                     -- games completed
    failed_games INTEGER,                         -- games failed
    average_response_time_ms INTEGER,             -- avg response time
    total_data_size_mb DECIMAL,                   -- total data size
    error_summary JSONB,                          -- error breakdown
    is_active BOOLEAN DEFAULT TRUE                -- session active
);
```

#### `scraping_errors`
```sql
CREATE TABLE scraping_errors (
    id SERIAL PRIMARY KEY,
    session_id UUID,                              -- session reference
    game_id VARCHAR(20),                          -- game that failed
    error_type VARCHAR(50),                       -- error category
    error_code INTEGER,                           -- HTTP/system error code
    error_message TEXT,                           -- error description
    stack_trace TEXT,                             -- full stack trace
    retry_attempt INTEGER,                        -- which retry attempt
    occurred_at TIMESTAMP                         -- when error occurred
);
```

#### `season_progress`
```sql
CREATE TABLE season_progress (
    id SERIAL PRIMARY KEY,
    season VARCHAR(10) UNIQUE NOT NULL,           -- "2024-25"
    total_games INTEGER NOT NULL,                 -- total games in season
    scraped_games INTEGER DEFAULT 0,              -- successfully scraped
    failed_games INTEGER DEFAULT 0,               -- permanently failed
    invalid_games INTEGER DEFAULT 0,              -- invalid URLs
    progress_percentage DECIMAL(5,2),             -- completion percentage
    last_updated TIMESTAMP                        -- last progress update
);
```

### Additional Support Tables

#### `game_periods`
```sql
CREATE TABLE game_periods (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) REFERENCES enhanced_games(game_id),
    period_number INTEGER,                        -- 1, 2, 3, 4, OT, 2OT, etc.
    period_type VARCHAR(20),                      -- "REGULAR", "OVERTIME"
    home_score INTEGER,                           -- home score for period
    away_score INTEGER,                           -- away score for period
    period_sequence INTEGER                       -- sequence order
);
```

#### `game_officials`
```sql
CREATE TABLE game_officials (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) REFERENCES enhanced_games(game_id),
    official_id INTEGER REFERENCES officials(official_id),
    assignment VARCHAR(20)                        -- "Crew Chief", "Referee", "Umpire"
);
```

### Key Database Views

#### `game_summary`
```sql
-- Provides game overview with team names
CREATE VIEW game_summary AS
SELECT 
    g.game_id,
    g.game_date,
    g.season,
    ht.tricode AS home_team,
    ht.name AS home_team_name,
    at.tricode AS away_team,
    at.name AS away_team_name,
    g.home_score,
    g.away_score,
    g.game_status_text
FROM enhanced_games g
JOIN teams ht ON g.home_team_id = ht.id
JOIN teams at ON g.away_team_id = at.id;
```

#### `player_game_summary`
```sql
-- Player stats with context
CREATE VIEW player_game_summary AS
SELECT 
    pgs.*,
    p.first_name,
    p.last_name,
    t.tricode AS team,
    g.game_date,
    g.season
FROM player_game_stats pgs
JOIN players p ON pgs.player_id = p.id
JOIN teams t ON pgs.team_id = t.id
JOIN enhanced_games g ON pgs.game_id = g.game_id;
```

#### `queue_status_summary`
```sql
-- Queue status overview
CREATE VIEW queue_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM scraping_queue 
GROUP BY status;
```

### Common Query Patterns

#### Game Queries
```sql
-- Get all games for a team in a season
SELECT * FROM game_summary 
WHERE (home_team = 'BOS' OR away_team = 'BOS') 
AND season = '2023-24';

-- Get playoff games
SELECT * FROM enhanced_games 
WHERE series_game_number IS NOT NULL;
```

#### Player Stats Queries
```sql
-- Player averages for a season
SELECT 
    first_name, last_name, team,
    AVG(points) as avg_points,
    AVG(rebounds_total) as avg_rebounds,
    AVG(assists) as avg_assists
FROM player_game_summary 
WHERE season = '2023-24' 
GROUP BY player_id, first_name, last_name, team;
```

#### Play-by-Play Queries
```sql
-- All shots by a player in a game
SELECT * FROM play_events 
WHERE game_id = '0021700001' 
AND player_id = 123 
AND event_type LIKE '%Shot%';

-- Fourth quarter events
SELECT * FROM play_events 
WHERE game_id = '0021700001' 
AND period = 4 
ORDER BY time_elapsed_seconds;
```

This schema supports comprehensive NBA data analysis including player/team statistics, play-by-play analysis, shot charts, lineup analysis, and game management.

## Dependencies

- `asyncpg`: PostgreSQL async driver
- `asyncio`: Async/await support
- `datetime`: Date/time handling
- `uuid`: Session ID generation
- `dataclasses`: Data structure definitions
- `enum`: Status enumeration