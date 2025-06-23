# 13 - REST API Development

## Objective
Develop a comprehensive REST API that provides access to NBA play-by-play data, statistics, and analytics through well-designed endpoints with proper authentication, rate limiting, and documentation.

## Ideal State
The ultimate goal for this this project is to allow users to create specific and complex queries to retrieve player/team/lineup data. All user queries need to follow the following high-level rules:

1. Is this query about a player/team/lineup? If it is a query about team stats, we should start at the 'team_game_stats' table and make additional queries from there. If it is a query about player performance, we should start at the 'player_game_stats' table and make additional queries from there. Finally if it is about lineups or on/off numbers, we should start at the 'lineup_stats' table and make additional queries from there.
2. Allow for queries to be about the most recent season, a specific season, subsets of seasons, or all seasons.
3. Allow for queries to be about the most recent game, a specific game, subsets of games, or all games.
4. Once we filter based on the following rules, we should return the data that is most relevant to the query. For example if a user is looking for shot charts, we should return the x, y, distance, and if it was made. If the user wants to compare the performance of a player on the court vs off the court, we should return the on/off numbers.

This is an ideal set of principles for the API, but it informs how we approach the API development process. We should start off with queries that are about players, teams, and lineups. Each of these queries should allow for parameters that correspond with the available columns.

Our goal is to use team/player/lineup data to query play-by-play data or full game data. We should use the same logic for both the API and MCP. When run with an AI agent, the MCP will be able to use several queries to analyze the data and then a final query to generate a report or prediction. I'm imagining this might have to use a final query and some analysis with pandas and possibly generating a data frame to generate the report or prediction.

With that being said, the API endpoints should give users the ability to access data in a similar way to a SQL query with filters, sorting, and pagination. We also want users to be able to add a flag titled 'about' that gives them high-level information about the number of observations, range, median, mean, mode, standard deviation, standard error, and number of statistical outliers. 

We should also allow users to add a flag titled 'correlation' that gives them the correlation between the number of observations, range, median, mean, mode, standard deviation, standard error, and number of statistical outliers. 

We should also allow users to add a flag titled 'regression' that gives them the correlation between the number of observations, range, median, mean, mode, standard deviation, standard error, and number of statistical outliers.

## Background
**Current State**: Enhanced database schema designed, data quality framework available, 8,765+ games of data ready for API development. Create a production-ready API that serves NBA data with high performance and reliability.

**Dependencies**: Plans 10 (schema), 11 (ETL), and 12 (cloud migration) completion

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
       description="Comprehensive NBA game data and analytics with advanced querying capabilities",
       version="2.0.0"
   )
   ```

2. **Project structure**
   ```
   src/api/
   ├── main.py                  # FastAPI application
   ├── routers/
   │   ├── player_stats.py      # Player-centric queries
   │   ├── team_stats.py        # Team-centric queries
   │   ├── lineup_stats.py      # Lineup-centric queries
   │   ├── shot_charts.py       # Shot location data
   │   ├── play_by_play.py      # Play-by-play events
   │   └── analytics.py         # Statistical analysis
   ├── models/
   │   ├── query_params.py      # Query parameter models
   │   ├── filters.py           # Filter models
   │   └── responses.py         # Response models
   ├── services/
   │   ├── query_builder.py     # Dynamic SQL query construction
   │   ├── stats_analyzer.py    # Statistical analysis service
   │   └── data_aggregator.py   # Data aggregation logic
   ├── middleware/
   │   ├── auth.py              # Authentication middleware
   │   ├── rate_limit.py        # Rate limiting
   │   └── caching.py           # Response caching
   └── utils/
       ├── database.py          # Database connection
       ├── validators.py        # Input validation
       └── pandas_utils.py      # DataFrame operations
   ```

### Phase 2: Core Query Endpoints

Based on the ideal state specifications, we'll implement three main entry points for queries:

1. **Player Statistics Endpoint**
   ```python
   @app.post("/api/v1/player-stats", response_model=Union[PlayerStatsResponse, StatisticalAnalysis])
   async def query_player_stats(
       # Player filters
       player_id: Optional[Union[int, List[int]]] = Query(None, description="Single player or list of players"),
       player_name: Optional[str] = Query(None, description="Player name (partial match supported)"),
       
       # Time filters
       season: Optional[str] = Query(None, description="'latest', '2023-24', '2022-23,2023-24', or 'all'"),
       game_id: Optional[str] = Query(None, description="'latest', specific game ID, comma-separated list, or 'all'"),
       date_from: Optional[date] = Query(None, description="Start date for filtering"),
       date_to: Optional[date] = Query(None, description="End date for filtering"),
       
       # Game context filters
       home_away: Optional[str] = Query(None, regex="^(home|away|all)$"),
       opponent_team_id: Optional[int] = Query(None),
       game_type: Optional[str] = Query(None, regex="^(regular|playoff|all)$"),
       
       # Statistical filters (JSON object)
       filters: Optional[str] = Query(None, description="JSON object with column filters, e.g., {'points': {'gte': 20}, 'assists': {'gte': 5}}"),
       
       # Output options
       fields: Optional[List[str]] = Query(None, description="Specific fields to return"),
       sort: Optional[str] = Query(None, description="Sort specification, e.g., '-points,assists'"),
       limit: int = Query(100, le=10000),
       offset: int = Query(0, ge=0),
       
       # Analysis flags
       about: bool = Query(False, description="Include statistical summary (mean, median, std dev, etc.)"),
       correlation: Optional[List[str]] = Query(None, description="Fields to calculate correlations for"),
       regression: Optional[Dict[str, str]] = Query(None, description="Regression analysis specification")
   ):
       """
       Query player statistics with advanced filtering and analysis options.
       Starts from player_game_stats table and joins other tables as needed.
       """
   ```

2. **Team Statistics Endpoint**
   ```python
   @app.post("/api/v1/team-stats", response_model=Union[TeamStatsResponse, StatisticalAnalysis])
   async def query_team_stats(
       # Team filters
       team_id: Optional[Union[int, List[int]]] = Query(None, description="Single team or list of teams"),
       team_name: Optional[str] = Query(None, description="Team name or abbreviation"),
       
       # Time filters (same as player endpoint)
       season: Optional[str] = Query(None),
       game_id: Optional[str] = Query(None),
       date_from: Optional[date] = Query(None),
       date_to: Optional[date] = Query(None),
       
       # Game context filters
       home_away: Optional[str] = Query(None, regex="^(home|away|all)$"),
       opponent_team_id: Optional[int] = Query(None),
       game_type: Optional[str] = Query(None, regex="^(regular|playoff|all)$"),
       win_loss: Optional[str] = Query(None, regex="^(win|loss|all)$"),
       
       # Statistical filters
       filters: Optional[str] = Query(None),
       
       # Output and analysis options (same as player endpoint)
       fields: Optional[List[str]] = Query(None),
       sort: Optional[str] = Query(None),
       limit: int = Query(100, le=10000),
       offset: int = Query(0, ge=0),
       about: bool = Query(False),
       correlation: Optional[List[str]] = Query(None),
       regression: Optional[Dict[str, str]] = Query(None)
   ):
       """
       Query team statistics with advanced filtering and analysis options.
       Starts from team_game_stats table and joins other tables as needed.
       """
   ```

3. **Lineup Statistics Endpoint**
   ```python
   @app.post("/api/v1/lineup-stats", response_model=Union[LineupStatsResponse, StatisticalAnalysis])
   async def query_lineup_stats(
       # Lineup composition filters
       player_ids: Optional[List[int]] = Query(None, description="Players that must be in the lineup"),
       exclude_player_ids: Optional[List[int]] = Query(None, description="Players that must NOT be in the lineup"),
       lineup_size: Optional[int] = Query(None, ge=1, le=5, description="Number of players in lineup"),
       
       # Team and time filters
       team_id: Optional[int] = Query(None),
       season: Optional[str] = Query(None),
       game_id: Optional[str] = Query(None),
       date_from: Optional[date] = Query(None),
       date_to: Optional[date] = Query(None),
       
       # Performance filters
       min_minutes: Optional[float] = Query(None, description="Minimum minutes played together"),
       filters: Optional[str] = Query(None),
       
       # On/Off analysis
       compare_mode: Optional[str] = Query(None, regex="^(on|off|both)$", description="Compare when lineup is on vs off court"),
       
       # Output and analysis options
       fields: Optional[List[str]] = Query(None),
       sort: Optional[str] = Query(None),
       limit: int = Query(100, le=10000),
       offset: int = Query(0, ge=0),
       about: bool = Query(False),
       correlation: Optional[List[str]] = Query(None),
       regression: Optional[Dict[str, str]] = Query(None)
   ):
       """
       Query lineup statistics and on/off numbers.
       Starts from lineup_states table and aggregates performance metrics.
       """
   ```

### Phase 3: Specialized Data Endpoints

1. **Shot Chart Endpoint**
   ```python
   @app.get("/api/v1/shot-charts", response_model=ShotChartResponse)
   async def get_shot_chart_data(
       # Entity selection (at least one required)
       player_id: Optional[int] = Query(None),
       team_id: Optional[int] = Query(None),
       game_id: Optional[str] = Query(None),
       
       # Time filters
       season: Optional[str] = Query(None),
       date_from: Optional[date] = Query(None),
       date_to: Optional[date] = Query(None),
       
       # Shot filters
       shot_type: Optional[List[str]] = Query(None, description="2PT, 3PT, etc."),
       shot_zone: Optional[List[str]] = Query(None),
       period: Optional[List[int]] = Query(None),
       time_remaining: Optional[str] = Query(None, description="e.g., '<2:00' for last 2 minutes"),
       
       # Context filters
       clutch_only: bool = Query(False, description="Only clutch situations"),
       made_only: bool = Query(False),
       missed_only: bool = Query(False)
   ):
       """
       Get shot location data with x, y coordinates, distance, and outcome.
       Returns data optimized for visualization.
       """
   ```

2. **Play-by-Play Query Endpoint**
   ```python
   @app.post("/api/v1/play-by-play", response_model=PlayByPlayResponse)
   async def query_play_by_play(
       # Game selection
       game_id: Optional[Union[str, List[str]]] = Query(None),
       
       # Time filters
       season: Optional[str] = Query(None),
       date_from: Optional[date] = Query(None),
       date_to: Optional[date] = Query(None),
       period: Optional[List[int]] = Query(None),
       time_range: Optional[Dict[str, str]] = Query(None, description="{'start': '10:00', 'end': '8:00'}"),
       
       # Event filters
       event_types: Optional[List[str]] = Query(None),
       player_id: Optional[int] = Query(None),
       team_id: Optional[int] = Query(None),
       
       # Situation filters
       score_margin: Optional[Dict[str, int]] = Query(None, description="{'min': -5, 'max': 5} for close games"),
       shot_clock: Optional[Dict[str, int]] = Query(None),
       
       # Output options
       include_lineup: bool = Query(False, description="Include current lineup for each play"),
       fields: Optional[List[str]] = Query(None),
       sort: Optional[str] = Query("-game_date,period,time_elapsed"),
       limit: int = Query(1000, le=50000),
       offset: int = Query(0, ge=0)
   ):
       """
       Query play-by-play events with detailed filtering options.
       Can return raw events or aggregated patterns.
       """
   ```

### Phase 4: Data Models and Statistical Analysis

1. **Query Parameter Models**
   ```python
   class BaseQueryParams(BaseModel):
       season: Optional[str] = Field(None, description="Season filter: 'latest', '2023-24', 'all', or comma-separated list")
       game_id: Optional[str] = Field(None, description="Game filter: 'latest', specific ID, 'all', or comma-separated list")
       date_from: Optional[date] = None
       date_to: Optional[date] = None
       filters: Optional[Dict[str, Any]] = Field(None, description="Dynamic column filters")
       fields: Optional[List[str]] = Field(None, description="Specific fields to return")
       sort: Optional[str] = Field(None, description="Sort specification: 'field1,-field2'")
       limit: int = Field(100, le=10000)
       offset: int = Field(0, ge=0)
       about: bool = Field(False, description="Include statistical summary")
       correlation: Optional[List[str]] = Field(None, description="Fields for correlation analysis")
       regression: Optional[Dict[str, str]] = Field(None, description="Regression specification")

   class PlayerStatsQuery(BaseQueryParams):
       player_id: Optional[Union[int, List[int]]] = None
       player_name: Optional[str] = None
       team_id: Optional[int] = None
       home_away: Optional[Literal["home", "away", "all"]] = None
       opponent_team_id: Optional[int] = None
       game_type: Optional[Literal["regular", "playoff", "all"]] = None

   class TeamStatsQuery(BaseQueryParams):
       team_id: Optional[Union[int, List[int]]] = None
       team_name: Optional[str] = None
       home_away: Optional[Literal["home", "away", "all"]] = None
       opponent_team_id: Optional[int] = None
       win_loss: Optional[Literal["win", "loss", "all"]] = None

   class LineupStatsQuery(BaseQueryParams):
       player_ids: Optional[List[int]] = Field(None, description="Players that must be in lineup")
       exclude_player_ids: Optional[List[int]] = Field(None, description="Players that must NOT be in lineup")
       lineup_size: Optional[int] = Field(None, ge=1, le=5)
       team_id: Optional[int] = None
       min_minutes: Optional[float] = Field(None, description="Minimum minutes played together")
       compare_mode: Optional[Literal["on", "off", "both"]] = None
   ```

2. **Statistical Analysis Models**
   ```python
   class StatisticalSummary(BaseModel):
       field_name: str
       count: int
       mean: Optional[float] = None
       median: Optional[float] = None
       mode: Optional[float] = None
       std_dev: Optional[float] = None
       std_error: Optional[float] = None
       min_value: Optional[float] = None
       max_value: Optional[float] = None
       range_value: Optional[float] = None
       outliers_count: int = 0
       percentile_25: Optional[float] = None
       percentile_75: Optional[float] = None

   class CorrelationAnalysis(BaseModel):
       field_pairs: List[Tuple[str, str]]
       correlation_coefficients: List[float]
       p_values: List[float]
       significant_correlations: List[Dict[str, Any]]

   class RegressionAnalysis(BaseModel):
       dependent_variable: str
       independent_variables: List[str]
       r_squared: float
       adjusted_r_squared: float
       coefficients: Dict[str, float]
       p_values: Dict[str, float]
       significant_predictors: List[str]
       equation: str

   class StatisticalAnalysis(BaseModel):
       data: List[Dict[str, Any]]
       summary_stats: Optional[List[StatisticalSummary]] = None
       correlation_analysis: Optional[CorrelationAnalysis] = None
       regression_analysis: Optional[RegressionAnalysis] = None
       total_records: int
       query_metadata: Dict[str, Any]
   ```

3. **Response Models**
   ```python
   class PlayerStatsResponse(BaseModel):
       data: List[Dict[str, Any]]
       total_records: int
       query_info: Dict[str, Any]
       statistical_analysis: Optional[StatisticalAnalysis] = None

   class TeamStatsResponse(BaseModel):
       data: List[Dict[str, Any]]
       total_records: int
       query_info: Dict[str, Any]
       statistical_analysis: Optional[StatisticalAnalysis] = None

   class LineupStatsResponse(BaseModel):
       data: List[Dict[str, Any]]
       total_records: int
       on_court_stats: Optional[Dict[str, Any]] = None
       off_court_stats: Optional[Dict[str, Any]] = None
       comparison: Optional[Dict[str, Any]] = None
       statistical_analysis: Optional[StatisticalAnalysis] = None

   class ShotChartResponse(BaseModel):
       shots: List[Dict[str, Any]]  # x, y, distance, made, shot_type, etc.
       total_shots: int
       made_shots: int
       shooting_percentage: float
       zones: Dict[str, Dict[str, Any]]  # Shooting stats by zone
       heat_map_data: Optional[List[Dict[str, Any]]] = None

   class PlayByPlayResponse(BaseModel):
       plays: List[Dict[str, Any]]
       total_plays: int
       game_context: Optional[Dict[str, Any]] = None
       lineup_data: Optional[List[Dict[str, Any]]] = None
       statistical_analysis: Optional[StatisticalAnalysis] = None
   ```

### Phase 5: Query Builder and Analysis Service

1. **Dynamic Query Builder**
   ```python
   class QueryBuilder:
       def __init__(self, base_table: str):
           self.base_table = base_table
           self.joins = []
           self.where_conditions = []
           self.parameters = {}

       def add_season_filter(self, season: str):
           if season == "latest":
               # Get most recent season from database
               subquery = "SELECT MAX(season) FROM enhanced_games"
               self.where_conditions.append(f"{self.base_table}.season = ({subquery})")
           elif season == "all":
               pass  # No filter
           elif "," in season:
               seasons = [s.strip() for s in season.split(",")]
               self.where_conditions.append(f"{self.base_table}.season = ANY(%s)")
               self.parameters['seasons'] = seasons
           else:
               self.where_conditions.append(f"{self.base_table}.season = %s")
               self.parameters['season'] = season

       def add_game_filter(self, game_id: str):
           if game_id == "latest":
               # Get most recent game date
               subquery = "SELECT MAX(game_date) FROM enhanced_games"
               self.where_conditions.append(f"{self.base_table}.game_date = ({subquery})")
           elif game_id == "all":
               pass
           elif "," in game_id:
               game_ids = [g.strip() for g in game_id.split(",")]
               self.where_conditions.append(f"{self.base_table}.game_id = ANY(%s)")
               self.parameters['game_ids'] = game_ids
           else:
               self.where_conditions.append(f"{self.base_table}.game_id = %s")
               self.parameters['game_id'] = game_id

       def add_dynamic_filters(self, filters: Dict[str, Any]):
           """Add filters like {'points': {'gte': 20}, 'assists': {'gte': 5}}"""
           for field, conditions in filters.items():
               if isinstance(conditions, dict):
                   for operator, value in conditions.items():
                       sql_op = self._get_sql_operator(operator)
                       param_key = f"{field}_{operator}"
                       self.where_conditions.append(f"{self.base_table}.{field} {sql_op} %s")
                       self.parameters[param_key] = value

       def _get_sql_operator(self, operator: str) -> str:
           mapping = {
               'gte': '>=', 'gt': '>', 'lte': '<=', 'lt': '<', 
               'eq': '=', 'ne': '!=', 'in': 'IN', 'not_in': 'NOT IN'
           }
           return mapping.get(operator, '=')

       def build_query(self, select_fields: List[str] = None) -> Tuple[str, Dict]:
           if not select_fields:
               select_fields = [f"{self.base_table}.*"]
           
           query_parts = [
               f"SELECT {', '.join(select_fields)}",
               f"FROM {self.base_table}"
           ]
           
           if self.joins:
               query_parts.extend(self.joins)
               
           if self.where_conditions:
               query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
               
           return " ".join(query_parts), self.parameters
   ```

2. **Statistical Analysis Service**
   ```python
   class StatsAnalyzer:
       def __init__(self):
           self.df = None

       def analyze_dataframe(self, df: pd.DataFrame, 
                           about_fields: List[str] = None,
                           correlation_fields: List[str] = None,
                           regression_spec: Dict[str, str] = None) -> StatisticalAnalysis:
           
           self.df = df
           analysis = StatisticalAnalysis(
               data=df.to_dict('records'),
               total_records=len(df),
               query_metadata={"generated_at": datetime.now().isoformat()}
           )

           if about_fields:
               analysis.summary_stats = self._calculate_summary_stats(about_fields)
           
           if correlation_fields:
               analysis.correlation_analysis = self._calculate_correlations(correlation_fields)
           
           if regression_spec:
               analysis.regression_analysis = self._perform_regression(regression_spec)

           return analysis

       def _calculate_summary_stats(self, fields: List[str]) -> List[StatisticalSummary]:
           summaries = []
           for field in fields:
               if field in self.df.columns and pd.api.types.is_numeric_dtype(self.df[field]):
                   series = self.df[field].dropna()
                   
                   # Calculate outliers using IQR method
                   q1, q3 = series.quantile([0.25, 0.75])
                   iqr = q3 - q1
                   outliers = series[(series < q1 - 1.5*iqr) | (series > q3 + 1.5*iqr)]
                   
                   summary = StatisticalSummary(
                       field_name=field,
                       count=len(series),
                       mean=float(series.mean()),
                       median=float(series.median()),
                       mode=float(series.mode().iloc[0]) if not series.mode().empty else None,
                       std_dev=float(series.std()),
                       std_error=float(series.std() / np.sqrt(len(series))),
                       min_value=float(series.min()),
                       max_value=float(series.max()),
                       range_value=float(series.max() - series.min()),
                       outliers_count=len(outliers),
                       percentile_25=float(q1),
                       percentile_75=float(q3)
                   )
                   summaries.append(summary)
           
           return summaries

       def _calculate_correlations(self, fields: List[str]) -> CorrelationAnalysis:
           numeric_df = self.df[fields].select_dtypes(include=[np.number])
           corr_matrix = numeric_df.corr()
           
           # Extract unique pairs and their correlations
           field_pairs = []
           correlations = []
           p_values = []
           
           for i, field1 in enumerate(corr_matrix.columns):
               for j, field2 in enumerate(corr_matrix.columns):
                   if i < j:  # Only upper triangle
                       field_pairs.append((field1, field2))
                       corr_val = corr_matrix.loc[field1, field2]
                       correlations.append(float(corr_val))
                       
                       # Calculate p-value
                       from scipy.stats import pearsonr
                       _, p_val = pearsonr(numeric_df[field1].dropna(), numeric_df[field2].dropna())
                       p_values.append(float(p_val))

           # Identify significant correlations (p < 0.05 and |r| > 0.3)
           significant = [
               {"fields": pair, "correlation": corr, "p_value": p_val}
               for pair, corr, p_val in zip(field_pairs, correlations, p_values)
               if p_val < 0.05 and abs(corr) > 0.3
           ]

           return CorrelationAnalysis(
               field_pairs=field_pairs,
               correlation_coefficients=correlations,
               p_values=p_values,
               significant_correlations=significant
           )

       def _perform_regression(self, regression_spec: Dict[str, str]) -> RegressionAnalysis:
           dependent_var = regression_spec.get('dependent')
           independent_vars = regression_spec.get('independent', '').split(',')
           
           if not dependent_var or not independent_vars:
               return None

           # Prepare data for regression
           y = self.df[dependent_var].dropna()
           X = self.df[independent_vars].dropna()
           
           # Align indices
           common_index = y.index.intersection(X.index)
           y = y.loc[common_index]
           X = X.loc[common_index]
           
           # Perform regression
           from sklearn.linear_model import LinearRegression
           from sklearn.metrics import r2_score
           
           model = LinearRegression()
           model.fit(X, y)
           
           y_pred = model.predict(X)
           r2 = r2_score(y, y_pred)
           
           # Calculate adjusted R²
           n = len(y)
           p = len(independent_vars)
           adjusted_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)
           
           # Build equation string
           equation_parts = [f"{dependent_var} = {model.intercept_:.3f}"]
           for var, coef in zip(independent_vars, model.coef_):
               equation_parts.append(f"{coef:+.3f}*{var}")
           equation = " ".join(equation_parts)

           return RegressionAnalysis(
               dependent_variable=dependent_var,
               independent_variables=independent_vars,
               r_squared=float(r2),
               adjusted_r_squared=float(adjusted_r2),
               coefficients=dict(zip(independent_vars, model.coef_)),
               p_values={},  # Would need statsmodels for p-values
               significant_predictors=[],  # Would need p-values to determine
               equation=equation
           )
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

## Usage Examples

### Example 1: Advanced Player Performance Analysis
```bash
# Query LeBron James stats in clutch situations (last 5 minutes) for 2023-24 season
POST /api/v1/player-stats
{
  "player_name": "LeBron James",
  "season": "2023-24",
  "filters": {
    "time_remaining": {"lte": "5:00"},
    "score_margin": {"gte": -5, "lte": 5}
  },
  "fields": ["game_id", "points", "assists", "rebounds", "field_goals_made", "field_goals_attempted"],
  "about": true,
  "correlation": ["points", "assists", "rebounds"]
}

# Response includes statistical summary and correlation analysis
{
  "data": [...],
  "total_records": 45,
  "statistical_analysis": {
    "summary_stats": [
      {
        "field_name": "points",
        "count": 45,
        "mean": 8.2,
        "median": 8.0,
        "std_dev": 4.1,
        "outliers_count": 3
      }
    ],
    "correlation_analysis": {
      "significant_correlations": [
        {"fields": ["points", "assists"], "correlation": 0.67, "p_value": 0.001}
      ]
    }
  }
}
```

### Example 2: Team Performance Comparison
```bash
# Compare Lakers vs Celtics home/away performance
POST /api/v1/team-stats
{
  "team_name": "Lakers,Celtics",
  "season": "2023-24",
  "home_away": "all",
  "fields": ["team_id", "home_away", "points", "rebounds", "assists", "turnovers", "win_loss"],
  "sort": "-points",
  "regression": {
    "dependent": "points",
    "independent": "rebounds,assists,turnovers"
  }
}
```

### Example 3: Lineup Effectiveness Analysis
```bash
# Analyze Warriors "Death Lineup" on/off court performance
POST /api/v1/lineup-stats
{
  "player_ids": [201939, 2544, 201142, 203110, 2738],  # Curry, Green, Thompson, Wiggins, Durant (historical)
  "team_id": 1610612744,  # Warriors
  "season": "2022-23",
  "min_minutes": 10.0,
  "compare_mode": "both",
  "about": true
}

# Response includes on/off court comparison
{
  "data": [...],
  "on_court_stats": {
    "offensive_rating": 118.5,
    "defensive_rating": 102.1,
    "net_rating": 16.4
  },
  "off_court_stats": {
    "offensive_rating": 112.3,
    "defensive_rating": 108.7,
    "net_rating": 3.6
  },
  "comparison": {
    "net_rating_difference": 12.8
  }
}
```

### Example 4: Shot Chart Analysis
```bash
# Get Stephen Curry's shot chart for playoffs
GET /api/v1/shot-charts?player_id=201939&season=2023-24&game_type=playoff&shot_type=3PT

{
  "shots": [
    {"x": 25.1, "y": 5.8, "distance": 26.2, "made": true, "shot_zone": "Above the Break 3"},
    ...
  ],
  "total_shots": 156,
  "made_shots": 68,
  "shooting_percentage": 43.6,
  "zones": {
    "Above the Break 3": {"attempts": 89, "made": 42, "percentage": 47.2},
    "Corner 3": {"attempts": 67, "made": 26, "percentage": 38.8}
  }
}
```

### Example 5: Complex Multi-Filter Query
```bash
# Find all games where a player scored 50+ points in overtime
POST /api/v1/player-stats
{
  "filters": {
    "points": {"gte": 50},
    "overtime": {"eq": true}
  },
  "season": "all",
  "fields": ["player_name", "game_id", "game_date", "points", "minutes", "team_abbreviation"],
  "sort": "-points",
  "limit": 50
}
```

## Integration with MCP Server

The API design directly supports MCP server development by providing:

1. **Structured Queries**: MCP can translate natural language to API parameters
2. **Statistical Analysis**: Built-in analysis reduces need for additional processing
3. **Flexible Filtering**: Supports complex multi-dimensional queries
4. **Pandas Integration**: Results can be easily converted to DataFrames for analysis

### MCP Query Translation Example
```python
# Natural language: "How did LeBron perform in close games this season?"
# MCP translates to:
api_query = {
    "endpoint": "/api/v1/player-stats",
    "params": {
        "player_name": "LeBron James",
        "season": "latest",
        "filters": {"score_margin": {"gte": -5, "lte": 5}},
        "about": True
    }
}
```

## Success Criteria
- All core endpoints operational with <200ms response time
- Support for complex SQL-like queries with multiple filters
- Statistical analysis integration (about, correlation, regression flags)
- Comprehensive API documentation with examples
- 99.9% uptime SLA
- Rate limiting and authentication working
- Comprehensive test coverage (90%+)
- MCP server compatibility for natural language queries

## Timeline
- **Week 1**: Core API framework and query builder infrastructure
- **Week 2**: Statistical analysis service and main endpoints
- **Week 3**: Authentication, rate limiting, caching, and specialized endpoints
- **Week 4**: Testing, documentation, optimization, and deployment

## Dependencies
- Completed cloud database migration (Plan 12)
- Enhanced database schema with lineup_states table
- API key management system
- Redis for caching and rate limiting
- Load balancer and SSL certificates
- Scientific Python libraries (pandas, numpy, scipy, scikit-learn)

## Next Steps
After completion:
1. MCP server development (Plan 14) - leveraging API endpoints
2. API performance optimization and advanced caching
3. User onboarding and comprehensive documentation
4. Advanced analytics endpoints (player tracking, advanced metrics)
5. Marketing and user acquisition