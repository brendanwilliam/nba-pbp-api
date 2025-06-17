# Scrapers Module

This module contains a comprehensive suite of scraping tools for collecting NBA game data from NBA.com. The scrapers handle URL discovery, validation, data extraction, and queue management with robust error handling and rate limiting.

## Architecture Overview

The scrapers work together in this workflow:
1. **URL Discovery** → **Validation** → **Queue Management** → **Data Extraction** → **Rate Limiting**

## Current Files

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

# Discover games for specific dates
games = await generator.discover_games_for_dates(date_list, season)

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
- Date-specific game discovery

**Dependencies**: `asyncio`, `aiohttp`, `sqlalchemy`, `team_mapping`

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

## Key Features

- **Resilience**: Multiple retry mechanisms, error handling, and fallback strategies
- **Scalability**: Async/concurrent processing with controlled parallelism  
- **Respectful**: Rate limiting with adaptive backoff to avoid overwhelming servers
- **Comprehensive**: Handles 29 seasons of NBA data (1996-2025) with team changes
- **Quality Control**: Data validation and quality scoring
- **Progress Tracking**: Detailed statistics and monitoring at multiple levels

This scraping system is designed to handle approximately 30,000 NBA games while being respectful to NBA.com servers and resilient to various failure modes.