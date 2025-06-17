# Core Module

This module contains the foundational database infrastructure for the NBA Play-by-Play API project.

## Files

### database.py

**Purpose**: Sets up the database connection infrastructure using SQLAlchemy, providing the foundation for all database operations.

**Functions**:

1. **`get_db()`** - Database Session Generator
   - Creates and manages database sessions with proper cleanup
   - Used as a dependency injection in FastAPI or as a context manager
   - Returns: Yields a database session that automatically closes after use
   ```python
   # Usage example
   for db in get_db():
       # Use db session here
       pass
   ```

2. **`get_database_url()`** - Database URL Accessor
   - Returns the database URL string for async connections
   - Used for creating async database connections or passing URL to other components
   - Returns: String containing the PostgreSQL connection URL

**Configuration**:
- `DATABASE_URL`: Retrieved from environment variable, defaults to `"postgresql://localhost:5432/nba_pbp"`
- `engine`: SQLAlchemy engine instance for database connections
- `SessionLocal`: Session factory for creating database sessions
- `Base`: Declarative base class for all database models

### models.py

**Purpose**: Defines the database schema using SQLAlchemy ORM models representing NBA data including teams, players, games, and scraping management.

**Models**:

1. **`Team`** - NBA Team Information
   - Table: `teams`
   - Key Fields: `id`, `tricode` (3-letter code), `name`, `city`
   - Usage:
     ```python
     team = Team(tricode="BOS", name="Boston Celtics", city="Boston")
     ```

2. **`Player`** - NBA Player Information
   - Table: `players`
   - Key Fields: `id`, `nba_id`, `first_name`, `last_name`, `jersey_number`, `position`, `team_id`
   - Usage:
     ```python
     player = Player(
         nba_id="123456",
         first_name="Jayson",
         last_name="Tatum",
         jersey_number="0",
         position="F",
         team_id=team.id
     )
     ```

3. **`Game`** - NBA Game Information
   - Table: `games`
   - Key Fields: `id`, `nba_game_id`, `game_date`, `home_team_id`, `away_team_id`, `season`, `game_type`, `game_url`
   - Usage:
     ```python
     game = Game(
         nba_game_id="0022400123",
         game_date=date(2024, 12, 25),
         home_team_id=1,
         away_team_id=2,
         season="2024-25",
         game_type="Regular Season"
     )
     ```

4. **`ScrapeQueue`** - Scraping Status Tracking
   - Table: `scrape_queue`
   - Key Fields: `id`, `game_id`, `status`, `attempts`, `last_attempt`, `error_message`
   - Status values: "pending", "in_progress", "completed", "failed"
   - Usage:
     ```python
     queue_item = ScrapeQueue(game_id=game.id, status="pending", attempts=0)
     ```

5. **`RawGameData`** - Raw Scraped JSON Storage
   - Table: `raw_game_data`
   - Key Fields: `id`, `game_id`, `game_url`, `raw_json`, `scraped_at`, `json_size`, `processing_status`
   - Processing status: "raw", "processed", "failed"
   - Usage:
     ```python
     raw_data = RawGameData(
         game_id="0022400123",
         game_url="https://nba.com/game/...",
         raw_json={"game_data": {...}},
         json_size=len(json_string)
     )
     ```

**Key Features**:
- All models include automatic timestamp tracking (`created_at`, `updated_at`)
- Proper indexing on frequently queried fields for performance
- Foreign key relationships maintain data integrity
- JSON column type for storing raw scraped data
- Status tracking for queue management and processing workflows

**Common Query Patterns**:
```python
# Find a team by tricode
team = db.query(Team).filter(Team.tricode == "BOS").first()

# Get all games for a season
games = db.query(Game).filter(Game.season == "2024-25").all()

# Get games with pending scrape status
pending_games = db.query(Game).join(ScrapeQueue).filter(
    ScrapeQueue.status == "pending"
).all()

# Get player with team information
player = db.query(Player).join(Team).filter(
    Player.last_name == "Tatum"
).first()
```

## Dependencies

- `sqlalchemy`: Core ORM library
- `python-dotenv`: Environment variable management
- `psycopg2-binary`: PostgreSQL adapter