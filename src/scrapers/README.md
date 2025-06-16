# Scrapers Module

This module contains a comprehensive suite of scraping tools for collecting NBA game data from NBA.com. The scrapers handle URL discovery, validation, data extraction, and queue management with robust error handling and rate limiting.

## Files Overview

The scrapers work together in this workflow:
1. **URL Discovery** → **Validation** → **Queue Management** → **Data Extraction** → **Rate Limiting** → **Orchestration**

## Files

### game_data_scraper.py

**Purpose**: Core scraper for extracting play-by-play data from NBA game pages by parsing JSON data from `__NEXT_DATA__` script tags.

**Key Components**:
- `GameDataScraper` class: Main scraper with configurable delay

**Functions**:
```python
scraper = GameDataScraper(delay=2.0)  # 2-second delay between requests

# Extract raw game data from NBA.com page
game_data = scraper.scrape_game_data(game_url)

# Extract game metadata (teams, scores, etc.)
metadata = scraper.extract_game_metadata(game_data)

# Extract play-by-play information
plays = scraper.extract_play_by_play(game_data)

# Validate scraped data structure
is_valid = scraper.validate_game_data(game_data)
```

**Dependencies**: `requests`, `BeautifulSoup4`, `json`

---

### game_discovery.py

**Purpose**: Discovers NBA games by scraping season schedules from NBA.com (1996-97 to 2024-25) with special handling for lockout seasons and COVID adjustments.

**Key Components**:
- `GameDiscovery` class: Async game discovery system
- `GameInfo` dataclass: Stores discovered game information

**Functions**:
```python
discovery = GameDiscovery()
await discovery.initialize()

# Discover games for a specific season
games = await discovery.discover_season_games("2024-25")

# Discover all games for all seasons
all_games = await discovery.discover_all_seasons()

# Get season definitions
seasons = discovery.get_season_definitions()

await discovery.close()
```

**Features**:
- HTML parsing with multiple fallback strategies
- Season definitions with historical adjustments
- Concurrent processing for efficiency

**Dependencies**: `asyncio`, `aiohttp`, `BeautifulSoup4`

---

### game_url_generator.py

**Purpose**: Comprehensive URL queue generator for all NBA games from 1996-2025 with database integration and priority calculation.

**Key Components**:
- `GameURLGenerator` class: Generates and validates game URLs
- `GameURLInfo` dataclass: Game URL metadata with priority

**Functions**:
```python
generator = GameURLGenerator(db_session)
await generator.initialize()

# Discover games for a season
games = await generator.discover_season_games("2024-25", batch_size=10)

# Populate database queue
stats = await generator.populate_queue(games)

# Get discovery statistics
stats = generator.get_discovery_stats()

await generator.close()
```

**Features**:
- Multiple parsing strategies for different page structures
- **Accurate game type classification**: Uses NBA game ID patterns (3rd digit: 1=preseason, 2=regular, 3=allstar, 4=playoff)
- Priority calculation based on season and game type
- Database integration for queue population
- Comprehensive error handling

**Dependencies**: `asyncio`, `aiohttp`, `sqlalchemy`, `team_mapping`

---

### game_url_scraper.py

**Purpose**: Simple synchronous scraper for discovering game URLs from NBA schedule pages with date-based filtering.

**Key Components**:
- `GameURLScraper` class: Synchronous URL discovery

**Functions**:
```python
scraper = GameURLScraper(delay=1.0)

# Get games for a specific date
games = scraper.get_games_for_date(date(2024, 12, 25))

# Get games for a date range
all_games = scraper.get_games_for_date_range(start_date, end_date)

# Extract URLs from HTML content
urls = scraper.extract_game_urls(html_content)
```

**Features**:
- Pattern matching for NBA.com game URL format
- Date-based game discovery
- Simple rate limiting with delays

**Dependencies**: `requests`, `BeautifulSoup4`

---

### mass_data_extractor.py

**Purpose**: Enhanced data extraction with validation and quality scoring for mass scraping operations, including user agent rotation and comprehensive error handling.

**Key Components**:
- `NBADataExtractor` class: Robust extraction with user agent rotation
- `DataQuality` dataclass: Quality assessment metrics
- `ExtractionMetadata` dataclass: Extraction process metadata
- `ExtractionResult` enum: Success/failure status

**Functions**:
```python
extractor = NBADataExtractor(timeout=30)

# Extract game data with quality assessment
result, json_data, metadata = extractor.extract_game_data(game_url)

if result == ExtractionResult.SUCCESS:
    print(f"Quality score: {metadata.data_quality.completeness_score}")
    print(f"Response time: {metadata.response_time_ms}ms")
```

**Features**:
- Response status handling (429 rate limit, 404 not found, etc.)
- Comprehensive data quality assessment
- User agent rotation for respectful scraping
- Detailed extraction metadata

**Dependencies**: `requests`, `BeautifulSoup4`, `json`

---

### mass_scraping_queue.py

**Purpose**: PostgreSQL-based queue management for mass NBA data collection with atomic operations and session tracking.

**Key Components**:
- `GameScrapingQueue` class: Async queue manager with session tracking
- `GameScrapingTask` dataclass: Represents queued games
- `ScrapingResult` dataclass: Scraping operation results

**Functions**:
```python
queue = GameScrapingQueue(db_url, session_id)
await queue.initialize()

# Get next batch of games to process
tasks = await queue.get_next_batch(batch_size=100)

# Mark game as completed
await queue.mark_completed(game_id, json_data, response_time_ms)

# Mark game as failed
await queue.mark_failed(game_id, error_message, error_code)

# Get queue statistics
stats = await queue.get_queue_statistics()

# Analyze failed games
failed_analysis = await queue.get_failed_games_analysis()

await queue.close()
```

**Features**:
- Atomic queue operations with row-level locking
- Progress tracking and statistics
- Failed game analysis and retry logic
- Session-based tracking

**Dependencies**: `asyncpg`, `asyncio`

---

### rate_limiter.py

**Purpose**: Intelligent rate limiting with adaptive backoff strategies and automatic rate adjustment based on server responses.

**Key Components**:
- `RateLimiter` class: Token bucket rate limiter with backoff
- `GlobalRateLimiter`: Singleton for thread-safe rate limiting
- `RateLimitConfig` dataclass: Configuration settings

**Functions**:
```python
config = RateLimitConfig(requests_per_second=0.5, burst_limit=3)
limiter = RateLimiter(config)

# Wait if rate limit exceeded
wait_time = limiter.wait_if_needed()

# Handle rate limit response from server
limiter.handle_rate_limit_response(429, retry_after=60)

# Handle successful response
limiter.handle_successful_response(200)

# Check current status
can_proceed = limiter.can_make_request()
```

**Features**:
- Multiple backoff strategies (exponential, linear, fixed)
- Automatic rate adjustment based on server responses
- Request history tracking
- Thread-safe operation

**Dependencies**: `threading`, `datetime`

---

### scraping_manager.py

**Purpose**: Main orchestrator for NBA game scraping operations, coordinating URL discovery and data scraping with team management and queue integration.

**Key Components**:
- `ScrapingManager` class: Coordinates URL discovery and data scraping

**Functions**:
```python
manager = ScrapingManager(db_session, url_delay=1.0, data_delay=2.0)

# Discover games for a specific date
games_added = manager.discover_games_for_date(date(2024, 12, 25), "2024-25")

# Scrape pending games
scraped = manager.scrape_pending_games(limit=10)

# Get scraping statistics
stats = manager.get_scraping_stats()

# Team management
team = manager.get_or_create_team("BOS", "Boston Celtics", "Boston")
```

**Features**:
- Team management (get/create operations)
- Queue management integration
- Failed game retry logic
- Progress statistics

**Dependencies**: `sqlalchemy`, `game_url_scraper`, `game_data_scraper`

---

### systematic_scraper.py

**Purpose**: Main execution framework with concurrent scraping, monitoring, and error handling for systematic NBA data collection.

**Key Components**:
- `SystematicScraper` class: Orchestrates mass scraping operations

**Functions**:
```python
scraper = SystematicScraper(db_url, rate_limit=1.0)
await scraper.initialize()

# Populate queue for a season
await scraper.populate_queue_for_season("2024-25")

# Run continuous scraping
await scraper.run_continuous_scraping(batch_size=20, max_workers=3)

# Scrape all seasons
await scraper.scrape_all_seasons(start_season="2020-21")

# Get progress statistics
stats = await scraper.get_progress_stats()

await scraper.close()
```

**Features**:
- Concurrent worker management
- Built-in rate limiting and backoff
- Progress monitoring and statistics
- Automatic retry and error handling
- Graceful shutdown handling

**Dependencies**: `asyncio`, `aiohttp`, `queue_manager`, `game_discovery`

---

### team_mapping.py

**Purpose**: Comprehensive NBA team abbreviation mapping with historical changes handling team relocations and name changes from 1996-2025.

**Key Components**:
- `NBATeamMapping` class: Handles team relocations and name changes
- `NBA_TEAMS` instance: Global team mapping object

**Functions**:
```python
from team_mapping import NBA_TEAMS

# Get team info for a specific season (handles relocations)
team_info = NBA_TEAMS.get_team_for_season("SEA", "2007-08")  # Returns OKC info

# Get all active teams for a season
active_teams = NBA_TEAMS.get_all_teams_for_season("2024-25")

# Validate team code for a season
is_valid = NBA_TEAMS.validate_team_code("BKN", "2011-12")  # False (was NJN)

# Get team history (relocations/name changes)
history = NBA_TEAMS.get_team_history("OKC")  # Shows SEA → OKC transition
```

**Features**:
- Current team definitions (30 teams)
- Historical relocations (SEA→OKC, NJN→BKN, etc.)
- Alternative abbreviation support
- Season-specific team validation

**Dependencies**: None (pure Python)

---

### url_validator.py

**Purpose**: Validates game URL accessibility and content before scraping with concurrent processing and database integration.

**Key Components**:
- `GameURLValidator` class: Async URL validation with concurrency control
- `URLValidationResult` class: Validation result details

**Functions**:
```python
validator = GameURLValidator(db_session, max_concurrent=10)
await validator.initialize()

# Validate single URL
result = await validator.validate_url(game_id, url)

# Validate batch of games
batch_results = await validator.validate_batch(games, batch_size=50)

# Validate queued URLs
stats = await validator.validate_queue_urls(
    status_filter='pending', 
    limit=1000
)

await validator.close()
```

**Features**:
- Content validation (checks for `__NEXT_DATA__` and game data)
- Batch validation with rate limiting
- Database integration for queue validation
- Concurrent processing with controlled parallelism

**Dependencies**: `asyncio`, `aiohttp`, `BeautifulSoup4`

## Integration Workflow

1. **Discovery**: `game_url_generator.py` discovers all game URLs for seasons
2. **Validation**: `url_validator.py` validates URLs are accessible and contain data  
3. **Queue Management**: `mass_scraping_queue.py` manages the scraping queue
4. **Data Extraction**: `mass_data_extractor.py` extracts JSON data from valid URLs
5. **Rate Limiting**: `rate_limiter.py` ensures respectful scraping behavior
6. **Orchestration**: `systematic_scraper.py` coordinates the entire process

## Key Features

- **Resilience**: Multiple retry mechanisms, error handling, and fallback strategies
- **Scalability**: Async/concurrent processing with controlled parallelism  
- **Respectful**: Rate limiting with adaptive backoff to avoid overwhelming servers
- **Comprehensive**: Handles 29 seasons of NBA data (1996-2025) with team changes
- **Quality Control**: Data validation and quality scoring
- **Progress Tracking**: Detailed statistics and monitoring at multiple levels

This scraping system is designed to handle approximately 30,000 NBA games while being respectful to NBA.com servers and resilient to various failure modes.