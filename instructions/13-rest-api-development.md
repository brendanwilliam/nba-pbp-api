# 13 - REST API Development

## Objective
Develop a comprehensive REST API that provides access to NBA play-by-play data, statistics, and analytics through well-designed endpoints with proper authentication, rate limiting, and documentation.

## Background
With the database populated and migrated to the cloud, create a production-ready API that serves the NBA data to developers, analysts, and applications with high performance and reliability.

## Scope
- **API Framework**: FastAPI or Flask-based REST API
- **Endpoints**: Comprehensive data access for games, players, teams, statistics
- **Features**: Authentication, rate limiting, caching, pagination
- **Documentation**: OpenAPI/Swagger documentation

## Implementation Plan

### Phase 1: API Framework Setup
1. **Technology stack selection**
   ```python
   # FastAPI for high performance and automatic documentation
   from fastapi import FastAPI, Depends, HTTPException, Query
   from fastapi.security import HTTPBearer
   from fastapi.middleware.cors import CORSMiddleware
   from fastapi.middleware.gzip import GZipMiddleware
   
   app = FastAPI(
       title="NBA Play-by-Play API",
       description="Comprehensive NBA game data and analytics",
       version="1.0.0"
   )
   ```

2. **Project structure**
   ```
   src/api/
   ├── main.py              # FastAPI application
   ├── routers/
   │   ├── games.py         # Game-related endpoints
   │   ├── players.py       # Player statistics and data
   │   ├── teams.py         # Team information and stats
   │   ├── plays.py         # Play-by-play events
   │   └── analytics.py     # Advanced analytics
   ├── models/
   │   ├── requests.py      # Pydantic request models
   │   └── responses.py     # Pydantic response models
   ├── services/
   │   ├── game_service.py  # Business logic for games
   │   ├── player_service.py
   │   └── analytics_service.py
   ├── middleware/
   │   ├── auth.py          # Authentication middleware
   │   ├── rate_limit.py    # Rate limiting
   │   └── caching.py       # Response caching
   └── utils/
       ├── database.py      # Database connection
       └── validators.py    # Input validation
   ```

### Phase 2: Core API Endpoints
1. **Games endpoints**
   ```python
   @app.get("/games", response_model=List[GameSummary])
   async def get_games(
       date: Optional[str] = Query(None, description="YYYY-MM-DD format"),
       season: Optional[str] = Query(None, description="2023-24 format"),
       team: Optional[str] = Query(None, description="Team abbreviation"),
       limit: int = Query(50, le=100),
       offset: int = Query(0, ge=0)
   ):
       """Get games with optional filtering"""
   
   @app.get("/games/{game_id}", response_model=GameDetail)
   async def get_game_detail(game_id: str):
       """Get detailed information for a specific game"""
   
   @app.get("/games/{game_id}/plays", response_model=List[PlayEvent])
   async def get_game_plays(
       game_id: str,
       period: Optional[int] = Query(None, ge=1, le=10),
       event_type: Optional[str] = Query(None)
   ):
       """Get play-by-play events for a game"""
   ```

2. **Players endpoints**
   ```python
   @app.get("/players", response_model=List[PlayerSummary])
   async def get_players(
       season: Optional[str] = Query(None),
       team: Optional[str] = Query(None),
       active: Optional[bool] = Query(None)
   ):
       """Get player list with optional filtering"""
   
   @app.get("/players/{player_id}/stats", response_model=PlayerStats)
   async def get_player_stats(
       player_id: int,
       season: Optional[str] = Query(None),
       game_type: str = Query("regular", regex="^(regular|playoff|all)$")
   ):
       """Get player statistics"""
   
   @app.get("/players/{player_id}/games", response_model=List[PlayerGameStats])
   async def get_player_games(
       player_id: int,
       season: Optional[str] = Query(None),
       limit: int = Query(50, le=100)
   ):
       """Get player's game-by-game statistics"""
   ```

3. **Teams endpoints**
   ```python
   @app.get("/teams", response_model=List[TeamInfo])
   async def get_teams():
       """Get all NBA teams"""
   
   @app.get("/teams/{team_id}/stats", response_model=TeamStats)
   async def get_team_stats(
       team_id: int,
       season: Optional[str] = Query(None)
   ):
       """Get team statistics for a season"""
   
   @app.get("/teams/{team_id}/roster", response_model=List[PlayerInfo])
   async def get_team_roster(
       team_id: int,
       season: Optional[str] = Query(None)
   ):
       """Get team roster for a season"""
   ```

### Phase 3: Advanced Analytics Endpoints
1. **Shot chart data**
   ```python
   @app.get("/players/{player_id}/shots", response_model=List[ShotEvent])
   async def get_player_shots(
       player_id: int,
       season: Optional[str] = Query(None),
       shot_type: Optional[str] = Query(None),
       game_id: Optional[str] = Query(None)
   ):
       """Get shot chart data for a player"""
   
   @app.get("/games/{game_id}/shots", response_model=List[ShotEvent])
   async def get_game_shots(game_id: str):
       """Get all shots in a game"""
   ```

2. **Advanced statistics**
   ```python
   @app.get("/analytics/efficiency", response_model=List[EfficiencyStats])
   async def get_efficiency_stats(
       season: str,
       min_games: int = Query(10, ge=1),
       position: Optional[str] = Query(None)
   ):
       """Get player efficiency statistics"""
   
   @app.get("/analytics/clutch", response_model=List[ClutchStats])
   async def get_clutch_stats(
       season: str,
       situation: str = Query("last_5_min", regex="^(last_5_min|last_2_min|last_30_sec)$")
   ):
       """Get clutch performance statistics"""
   ```

### Phase 4: Data Models and Validation
1. **Pydantic models**
   ```python
   class GameSummary(BaseModel):
       game_id: str
       game_date: date
       home_team: TeamInfo
       away_team: TeamInfo
       home_score: Optional[int]
       away_score: Optional[int]
       game_status: str
       season: str
   
   class PlayEvent(BaseModel):
       event_id: int
       game_id: str
       period: int
       time_remaining: str
       time_elapsed: int
       event_type: str
       description: str
       player: Optional[PlayerInfo]
       team: Optional[TeamInfo]
       home_score: int
       away_score: int
   
   class PlayerStats(BaseModel):
       player_id: int
       player_name: str
       games_played: int
       minutes_per_game: float
       points_per_game: float
       rebounds_per_game: float
       assists_per_game: float
       field_goal_percentage: float
       three_point_percentage: float
       free_throw_percentage: float
   ```

### Phase 5: Authentication and Security
1. **API key authentication**
   ```python
   class APIKeyAuth:
       def __init__(self, api_key_header: str = "X-API-Key"):
           self.api_key_header = api_key_header
       
       async def __call__(self, request: Request):
           api_key = request.headers.get(self.api_key_header)
           if not api_key:
               raise HTTPException(401, "API key required")
           
           user = await self.validate_api_key(api_key)
           if not user:
               raise HTTPException(401, "Invalid API key")
           
           return user
   ```

2. **Rate limiting**
   ```python
   class RateLimiter:
       def __init__(self, requests_per_minute: int = 100):
           self.requests_per_minute = requests_per_minute
           self.redis = Redis()
       
       async def __call__(self, request: Request, user: User = Depends(auth)):
           key = f"rate_limit:{user.id}"
           current = await self.redis.incr(key)
           
           if current == 1:
               await self.redis.expire(key, 60)
           elif current > self.requests_per_minute:
               raise HTTPException(429, "Rate limit exceeded")
   ```

## Performance Optimization

### Caching Strategy
1. **Response caching**
   ```python
   @lru_cache(maxsize=1000)
   async def get_cached_player_stats(player_id: int, season: str):
       # Cache frequently accessed player stats
       
   class RedisCache:
       def __init__(self):
           self.redis = Redis()
       
       async def get_or_set(self, key: str, factory_func, ttl: int = 300):
           cached = await self.redis.get(key)
           if cached:
               return json.loads(cached)
           
           result = await factory_func()
           await self.redis.setex(key, ttl, json.dumps(result))
           return result
   ```

2. **Database query optimization**
   ```python
   class OptimizedQueries:
       def get_games_with_stats(self, filters):
           # Use joins to minimize database round trips
           query = """
           SELECT g.*, ht.team_name as home_team_name, at.team_name as away_team_name
           FROM games g
           JOIN teams ht ON g.home_team_id = ht.team_id
           JOIN teams at ON g.away_team_id = at.team_id
           WHERE ($1::date IS NULL OR g.game_date = $1)
           AND ($2::text IS NULL OR g.season = $2)
           ORDER BY g.game_date DESC
           LIMIT $3 OFFSET $4
           """
   ```

### Database Connection Management
```python
class DatabaseManager:
    def __init__(self):
        self.pool = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=10,
            max_size=20,
            command_timeout=60
        )
    
    async def get_connection(self):
        return await self.pool.acquire()
    
    async def execute_query(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
```

## API Documentation and Testing

### OpenAPI Documentation
```python
# Comprehensive API documentation
app = FastAPI(
    title="NBA Play-by-Play API",
    description="""
    Comprehensive NBA game data and analytics API providing access to:
    - Historical play-by-play data (1996-present)
    - Player and team statistics
    - Advanced analytics and shot charts
    - Real-time game data
    """,
    version="1.0.0",
    contact={
        "name": "NBA PBP API Support",
        "url": "https://nba-pbp-api.com/support",
        "email": "support@nba-pbp-api.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)
```

### Testing Framework
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_games():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/games?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10

@pytest.mark.asyncio
async def test_get_player_stats():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/players/2544/stats?season=2023-24")
    assert response.status_code == 200
```

## Deployment and Operations

### Docker Configuration
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Health Checks and Monitoring
```python
@app.get("/health")
async def health_check():
    # Check database connectivity
    # Check Redis connectivity
    # Return system status
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/metrics")
async def metrics():
    # Prometheus-compatible metrics
    return {
        "requests_total": request_counter.value,
        "response_time_avg": response_time.mean(),
        "database_connections": db_pool.size()
    }
```

## Success Criteria
- All core endpoints operational with <200ms response time
- Comprehensive API documentation
- 99.9% uptime SLA
- Rate limiting and authentication working
- Comprehensive test coverage (90%+)

## Timeline
- **Week 1**: Core API framework and basic endpoints
- **Week 2**: Advanced endpoints and analytics
- **Week 3**: Authentication, rate limiting, and caching
- **Week 4**: Testing, documentation, and deployment

## Dependencies
- Completed cloud database migration (Plan 12)
- API key management system
- Redis for caching and rate limiting
- Load balancer and SSL certificates

## Next Steps
After completion:
1. MCP server development (Plan 14)
2. API performance optimization
3. User onboarding and documentation
4. Marketing and user acquisition