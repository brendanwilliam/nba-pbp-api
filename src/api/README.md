# NBA Play-by-Play API

A comprehensive REST API for querying NBA play-by-play data, player statistics, team performance, and lineup analysis with advanced filtering and statistical analysis capabilities.

## Table of Contents
- [Quick Start](#quick-start)
- [API Overview](#api-overview)
- [Local Development](#local-development)
- [Endpoint Reference](#endpoint-reference)
- [Query Examples](#query-examples)
- [Statistical Analysis](#statistical-analysis)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Configuration](#configuration)

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database (local or cloud)
- Virtual environment activated

### 1. Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate

# Install required packages
pip install fastapi uvicorn pandas numpy scipy scikit-learn httpx asyncpg
```

### 2. Start the API Server
```bash
# From the project root directory
python src/api/start_api.py

# Or manually with uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access the API
- **API Base URL**: `http://localhost:8000`
- **Interactive Documentation**: `http://localhost:8000/docs`
- **Alternative Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

## API Overview

### Core Features
- **Advanced Querying**: Complex filtering with JSON-based parameters
- **Statistical Analysis**: Built-in correlations, regression, and summary statistics
- **Flexible Filtering**: Season, date, team, player, game type filters
- **Pagination**: Efficient handling of large datasets
- **Search Capabilities**: Player and team search functionality
- **Type Safety**: Full type validation with Pydantic models

### Response Format
All endpoints return JSON with consistent structure:
```json
{
  "data": [...],           // Query results
  "total_records": 1500,   // Total matching records
  "query_info": {...},     // Applied filters and pagination
  "statistical_analysis": {...}  // Optional statistical analysis
}
```

## Local Development

### Project Structure
```
src/api/
├── main.py                 # FastAPI application entry point
├── models/                 # Data models and validation
│   ├── query_params.py     # Request parameter models
│   └── responses.py        # Response data models
├── routers/                # API endpoint routers
│   ├── player_stats.py     # Player statistics endpoints
│   ├── team_stats.py       # Team statistics endpoints
│   └── lineup_stats.py     # Lineup analysis endpoints
├── services/               # Business logic services
│   ├── query_builder.py    # Dynamic SQL query construction
│   └── stats_analyzer.py   # Statistical analysis service
├── utils/                  # Utilities and database connection
│   └── database.py         # Database manager and query executor
├── examples.py             # Usage examples and demos
├── test_api.py            # Basic API tests
└── start_api.py           # Development server startup script
```

### Environment Configuration
Set database connection via environment variables:
```bash
# Database connection options (use one)
export DATABASE_URL="postgresql://user:password@localhost:5432/nba_pbp"
export NEON_DATABASE_URL="postgresql://user:password@host:5432/nba_pbp"

# Or individual components
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="nba_pbp"
export DB_USER="postgres"
export DB_PASSWORD="your_password"
```

### Running Tests
```bash
# Run basic API tests
python src/api/test_api.py

# Run example demonstrations
python src/api/examples.py

# With pytest (if installed)
pytest src/api/test_api.py -v
```

## Endpoint Reference

### System Endpoints

#### Health Check
```http
GET /health
```
Returns API health status and connectivity information.

#### Metrics
```http
GET /metrics
```
Returns basic system metrics and operational status.

### Search Endpoints

#### Player Search
```http
GET /api/v1/players/search?query={search_term}&limit={number}
```
Search for players by name (partial matches supported).

**Parameters:**
- `query` (required): Player name search term
- `limit` (optional): Maximum results (default: 20, max: 100)

#### Team Search
```http
GET /api/v1/teams/search?query={search_term}&limit={number}
```
Search for teams by name or abbreviation.

**Parameters:**
- `query` (required): Team name or abbreviation
- `limit` (optional): Maximum results (default: 30, max: 50)

### Player Statistics

#### Advanced Player Query
```http
POST /api/v1/player-stats
```
Complex player statistics queries with filtering and analysis.

**Query Parameters:**
- `player_id` (int or list): Player ID(s) to filter
- `player_name` (string): Player name (partial match)
- `season` (string): Season filter (`latest`, `2023-24`, `all`, or comma-separated)
- `game_id` (string): Game filter (`latest`, specific ID, `all`, or comma-separated)
- `date_from` / `date_to` (date): Date range filters
- `team_id` (int): Team filter
- `home_away` (string): `home`, `away`, or `all`
- `opponent_team_id` (int): Opponent team filter
- `game_type` (string): `regular`, `playoff`, or `all`
- `filters` (JSON string): Dynamic column filters
- `fields` (list): Specific fields to return
- `sort` (string): Sort specification (e.g., `-points,assists`)
- `limit` / `offset` (int): Pagination
- `about` (boolean): Include statistical summary
- `correlation` (list): Fields for correlation analysis
- `regression` (JSON string): Regression specification

#### Individual Player Stats
```http
GET /api/v1/players/{player_id}/stats
```
Get statistics for a specific player.

**Parameters:**
- `season` (string): Season filter (default: `latest`)
- `game_type` (string): Game type filter (default: `all`)
- `limit` / `offset` (int): Pagination

### Team Statistics

#### Advanced Team Query
```http
POST /api/v1/team-stats
```
Complex team statistics queries with win/loss analysis.

**Query Parameters:** (Similar to player stats with team-specific additions)
- `team_id` (int or list): Team ID(s) to filter
- `team_name` (string): Team name or abbreviation
- `win_loss` (string): `win`, `loss`, or `all`
- (Plus all common parameters from player stats)

#### Individual Team Stats
```http
GET /api/v1/teams/{team_id}/stats
```
Get statistics for a specific team including season averages.

#### Head-to-Head Analysis
```http
GET /api/v1/teams/{team_id}/head-to-head/{opponent_team_id}
```
Compare performance between two teams.

**Parameters:**
- `season` (string): Season filter (default: `all`)
- `game_type` (string): Game type filter (default: `all`)

### Lineup Analysis

#### Advanced Lineup Query
```http
POST /api/v1/lineup-stats
```
Analyze player combinations and lineup performance.

**Query Parameters:**
- `player_ids` (list): Players that must be in lineup
- `exclude_player_ids` (list): Players that must NOT be in lineup
- `lineup_size` (int): Number of players in lineup (1-5)
- `team_id` (int): Team filter
- `min_minutes` (float): Minimum minutes played together
- `compare_mode` (string): `on`, `off`, or `both` for on/off analysis
- (Plus common filtering parameters)

#### Common Lineups
```http
GET /api/v1/lineups/common/{team_id}
```
Get most frequently used lineups for a team.

**Parameters:**
- `season` (string): Season filter (default: `latest`)
- `min_games` (int): Minimum games played together (default: 5)
- `lineup_size` (int): Number of players (default: 5)
- `limit` (int): Maximum results (default: 20)

#### Player Combinations
```http
GET /api/v1/lineups/player-combinations
```
Analyze how specific players perform together.

**Parameters:**
- `player_ids` (list, required): Player IDs to analyze
- `team_id` (int): Team filter
- `season` (string): Season filter
- `min_minutes` (float): Minimum minutes threshold

## Query Examples

### Basic Player Query
```bash
curl -X POST "http://localhost:8000/api/v1/player-stats" \
  -H "Content-Type: application/json" \
  -d '{
    "player_name": "LeBron James",
    "season": "2023-24",
    "limit": 10,
    "sort": "-points"
  }'
```

### Advanced Filtering with Statistics
```bash
curl -X POST "http://localhost:8000/api/v1/player-stats" \
  -H "Content-Type: application/json" \
  -d '{
    "season": "latest",
    "filters": "{\"points\": {\"gte\": 25}, \"assists\": {\"gte\": 7}}",
    "about": true,
    "correlation": ["points", "assists", "rebounds"],
    "sort": "-points",
    "limit": 50
  }'
```

### Team Performance Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/team-stats" \
  -H "Content-Type: application/json" \
  -d '{
    "team_name": "Lakers",
    "season": "2023-24",
    "home_away": "home",
    "win_loss": "win",
    "about": true
  }'
```

### Lineup Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/lineup-stats" \
  -H "Content-Type: application/json" \
  -d '{
    "player_ids": [2544, 201939, 201142],
    "team_id": 1610612744,
    "season": "2023-24",
    "compare_mode": "both",
    "min_minutes": 10.0
  }'
```

## Statistical Analysis

### Summary Statistics (`about: true`)
When enabled, provides comprehensive statistical summaries:
- Count, mean, median, mode
- Standard deviation and standard error
- Min, max, range values
- Outlier detection (IQR method)
- 25th and 75th percentiles

### Correlation Analysis (`correlation: [fields]`)
Calculates Pearson correlations between specified fields:
- Correlation coefficients and p-values
- Significance testing (p < 0.05, |r| > 0.3)
- Correlation strength interpretation

### Regression Analysis (`regression: JSON`)
Performs linear regression analysis:
```json
{
  "regression": "{\"dependent\": \"points\", \"independent\": \"rebounds,assists,steals\"}"
}
```
Returns R², adjusted R², coefficients, and regression equation.

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (player/team/game not found)
- `422` - Validation Error (parameter format issues)
- `500` - Internal Server Error

### Error Response Format
```json
{
  "error": "Error description",
  "detail": "Additional error details",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Common Issues
1. **Database Connection**: Check environment variables and database accessibility
2. **Invalid JSON**: Ensure proper JSON formatting in `filters` and `regression` parameters
3. **Player/Team Not Found**: Verify IDs exist using search endpoints first
4. **Parameter Validation**: Check parameter types and value ranges

## Testing

### Run Example Tests
```bash
# Basic API functionality test
python src/api/test_api.py

# Interactive API demonstration
python src/api/examples.py
```

### Manual Testing with curl
```bash
# Health check
curl http://localhost:8000/health

# Player search
curl "http://localhost:8000/api/v1/players/search?query=LeBron"

# Basic player stats
curl -X POST "http://localhost:8000/api/v1/player-stats" \
  -H "Content-Type: application/json" \
  -d '{"season": "latest", "limit": 5}'
```

### Testing with Python
```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        # Health check
        response = await client.get("http://localhost:8000/health")
        print(response.json())
        
        # Player search
        response = await client.get(
            "http://localhost:8000/api/v1/players/search?query=Jordan"
        )
        print(response.json())

asyncio.run(test_api())
```

## Configuration

### Database Configuration
The API supports multiple database connection methods:

1. **Single URL** (recommended):
   ```bash
   export DATABASE_URL="postgresql://user:password@host:port/database"
   ```

2. **Component-based**:
   ```bash
   export DB_HOST="localhost"
   export DB_PORT="5432"
   export DB_NAME="nba_pbp"
   export DB_USER="postgres"
   export DB_PASSWORD="password"
   ```

3. **Cloud providers**:
   ```bash
   export NEON_DATABASE_URL="postgresql://..."  # Neon
   export POSTGRES_URL="postgresql://..."       # Generic
   ```

### Connection Pool Settings
Default connection pool configuration:
- Minimum connections: 5
- Maximum connections: 20
- Command timeout: 60 seconds
- Connection timeout: 30 seconds

### Performance Settings
- **Pagination**: Default limit 100, maximum 10,000
- **Search limits**: Player search max 100, team search max 50
- **Query timeout**: 60 seconds
- **Response compression**: GZip enabled for responses > 1KB

## Development Notes

### Adding New Endpoints
1. Create route functions in appropriate router file
2. Define request/response models in `models/`
3. Add business logic to `services/`
4. Update this README with documentation

### Database Schema Requirements
The API expects these database tables:
- `enhanced_games` - Game information
- `players` - Player roster data
- `teams` - Team information
- `player_game_stats` - Player performance by game
- `team_game_stats` - Team performance by game
- `lineup_stats` - Lineup performance data
- `play_events` - Individual play-by-play events

### Contributing
1. Follow existing code structure and patterns
2. Add type hints for all functions
3. Include docstrings for public methods
4. Update tests and documentation
5. Ensure database queries are parameterized for security

## Support

### Troubleshooting
- Check `/health` endpoint for database connectivity
- Verify environment variables are set correctly
- Review logs for detailed error messages
- Use `/docs` for interactive testing

### Documentation
- Interactive API docs: `/docs`
- Alternative format: `/redoc`
- OpenAPI schema: `/openapi.json`

---

**Note**: This API requires an active NBA database with populated game data. Some endpoints may return empty results if the database is not fully populated with scraped NBA data.