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

## Dependencies

- `asyncpg`: PostgreSQL async driver
- `asyncio`: Async/await support
- `datetime`: Date/time handling
- `uuid`: Session ID generation
- `dataclasses`: Data structure definitions
- `enum`: Status enumeration