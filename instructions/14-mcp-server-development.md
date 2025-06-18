# 14 - MCP Server Development

## Objective
Develop a Model Context Protocol (MCP) server that enables Large Language Models to query NBA play-by-play data using natural language, providing seamless integration for AI applications and chatbots.

## Background
**Current State**: Enhanced database schema designed with comprehensive NBA data structure. The MCP server will translate natural language queries into structured database queries, allowing LLMs like Claude, GPT, and others to access NBA data through conversational interfaces.

**Dependencies**: Plans 10 (schema), 11 (ETL), 12 (cloud), and 13 (REST API) completion

## Scope
- **MCP Implementation**: Standards-compliant MCP server
- **Natural Language Processing**: Query interpretation and SQL generation
- **LLM Integration**: Support for multiple AI models
- **Query Optimization**: Efficient database access patterns

## Implementation Plan

### Phase 1: MCP Server Framework
1. **MCP server setup**
   ```python
   from mcp import Server
   from mcp.types import Tool, TextContent
   
   class NBAMCPServer(Server):
       def __init__(self):
           super().__init__("nba-pbp-server", "1.0.0")
           self.db_manager = DatabaseManager()
           self.query_translator = NaturalLanguageQueryTranslator()
           
       async def list_tools(self):
           return [
               Tool(
                   name="query_nba_data",
                   description="Query NBA play-by-play data using natural language",
                   inputSchema={
                       "type": "object",
                       "properties": {
                           "query": {"type": "string", "description": "Natural language query about NBA data"}
                       },
                       "required": ["query"]
                   }
               ),
               Tool(
                   name="get_player_stats",
                   description="Get specific player statistics",
                   inputSchema={
                       "type": "object",
                       "properties": {
                           "player_name": {"type": "string"},
                           "season": {"type": "string", "pattern": "^\\d{4}-\\d{2}$"},
                           "stat_type": {"type": "string", "enum": ["basic", "advanced", "shooting"]}
                       },
                       "required": ["player_name"]
                   }
               ),
               Tool(
                   name="analyze_game",
                   description="Get detailed analysis of a specific game",
                   inputSchema={
                       "type": "object",
                       "properties": {
                           "game_id": {"type": "string"},
                           "analysis_type": {"type": "string", "enum": ["summary", "plays", "shots", "momentum"]}
                       },
                       "required": ["game_id"]
                   }
               )
           ]
   ```

2. **Natural language query processor**
   ```python
   class NaturalLanguageQueryTranslator:
       def __init__(self):
           self.query_patterns = self._load_query_patterns()
           self.entity_extractor = EntityExtractor()
       
       async def translate_query(self, natural_query: str):
           # Extract entities (players, teams, dates, stats)
           entities = await self.entity_extractor.extract(natural_query)
           
           # Determine query type and intent
           query_type = self._classify_query_type(natural_query)
           
           # Generate SQL based on entities and intent
           sql_query = await self._generate_sql(query_type, entities)
           
           return {
               "sql": sql_query,
               "entities": entities,
               "query_type": query_type
           }
   ```

### Phase 2: Query Understanding and Processing
1. **Entity extraction**
   ```python
   class EntityExtractor:
       def __init__(self):
           self.player_names = self._load_player_names()
           self.team_names = self._load_team_names()
           self.date_parser = DateParser()
       
       async def extract(self, query: str):
           entities = {
               "players": self._extract_players(query),
               "teams": self._extract_teams(query),
               "dates": self._extract_dates(query),
               "stats": self._extract_statistics(query),
               "game_situations": self._extract_situations(query)
           }
           return entities
       
       def _extract_players(self, query: str):
           # Match player names using fuzzy matching
           # Handle nicknames and variations
           # Return player IDs and confidence scores
           
       def _extract_teams(self, query: str):
           # Match team names, cities, abbreviations
           # Handle historical team names
           
       def _extract_dates(self, query: str):
           # Parse various date formats
           # Handle relative dates ("last week", "this season")
           # Season extraction ("2023-24 season")
   ```

2. **Query classification**
   ```python
   class QueryClassifier:
       QUERY_TYPES = {
           "player_stats": ["average", "per game", "career", "season stats"],
           "game_analysis": ["game", "match", "vs", "against"],
           "team_performance": ["team", "franchise", "record"],
           "historical_comparison": ["compare", "versus", "better than"],
           "shot_analysis": ["shooting", "shot chart", "field goal"],
           "play_by_play": ["play by play", "what happened", "sequence"]
       }
       
       def classify(self, query: str):
           # Use keyword matching and ML classification
           # Return query type with confidence score
   ```

### Phase 3: SQL Generation Engine
1. **Query builders**
   ```python
   class SQLQueryBuilder:
       def __init__(self):
           self.templates = self._load_query_templates()
       
       def build_player_stats_query(self, entities):
           player_id = entities["players"][0]["id"]
           season = entities.get("dates", {}).get("season")
           
           query = """
           SELECT p.player_name, 
                  AVG(pgs.points) as avg_points,
                  AVG(pgs.rebounds) as avg_rebounds,
                  AVG(pgs.assists) as avg_assists,
                  COUNT(*) as games_played
           FROM player_game_stats pgs
           JOIN players p ON pgs.player_id = p.player_id
           JOIN games g ON pgs.game_id = g.game_id
           WHERE pgs.player_id = $1
           """
           
           params = [player_id]
           
           if season:
               query += " AND g.season = $2"
               params.append(season)
           
           query += " GROUP BY p.player_id, p.player_name"
           
           return query, params
       
       def build_game_analysis_query(self, entities):
           # Generate complex queries for game analysis
           # Include play-by-play events, key moments, statistics
   ```

2. **Query optimization**
   ```python
   class QueryOptimizer:
       def optimize_query(self, sql_query: str, entities: dict):
           # Add appropriate indexes hints
           # Optimize joins and subqueries
           # Add result limits for performance
           
       def validate_query(self, sql_query: str):
           # Ensure query is safe (no writes, no dangerous operations)
           # Validate against allowed operations
           # Check for potential performance issues
   ```

### Phase 4: Response Formatting and Context
1. **Response formatter**
   ```python
   class ResponseFormatter:
       def format_player_stats(self, data, context):
           if not data:
               return "No statistics found for the specified criteria."
           
           player_data = data[0]
           response = f"""
           {player_data['player_name']} Statistics:
           • Games Played: {player_data['games_played']}
           • Average Points: {player_data['avg_points']:.1f}
           • Average Rebounds: {player_data['avg_rebounds']:.1f}
           • Average Assists: {player_data['avg_assists']:.1f}
           """
           
           if context.get("season"):
               response += f"\n(Season: {context['season']})"
           
           return response
       
       def format_game_analysis(self, data, context):
           # Format complex game analysis with key events
           # Include momentum shifts, key plays, statistics
   ```

2. **Context management**
   ```python
   class ConversationContext:
       def __init__(self):
           self.session_data = {}
       
       def update_context(self, session_id: str, entities: dict, query_result: dict):
           # Store recent queries and entities for follow-up questions
           # Track conversation flow and references
           
       def resolve_references(self, query: str, session_id: str):
           # Handle pronouns and references to previous queries
           # "his stats last season" -> resolve "his" to previously mentioned player
   ```

### Phase 5: Advanced Query Capabilities
1. **Complex analytics queries**
   ```python
   class AdvancedQueryHandlers:
       async def handle_comparison_query(self, entities):
           # "Compare LeBron James and Michael Jordan"
           # Generate side-by-side statistics
           
       async def handle_trend_analysis(self, entities):
           # "Show Stephen Curry's three-point shooting over time"
           # Generate time-series data
           
       async def handle_situational_analysis(self, entities):
           # "How does team X perform in clutch time?"
           # Filter for specific game situations
   ```

2. **Real-time data integration**
   ```python
   class RealTimeDataHandler:
       async def get_live_game_data(self, game_id: str):
           # Interface with live NBA data feeds
           # Provide real-time play-by-play updates
           
       async def get_current_season_stats(self):
           # Automatically detect current season
           # Provide up-to-date statistics
   ```

## Integration and Deployment

### MCP Server Configuration
```python
# Server configuration
server_config = {
    "name": "nba-pbp-server",
    "version": "1.0.0",
    "description": "NBA Play-by-Play Data MCP Server",
    "tools": [
        "query_nba_data",
        "get_player_stats", 
        "analyze_game",
        "compare_players",
        "team_analysis"
    ],
    "capabilities": {
        "natural_language_query": True,
        "historical_data": True,
        "real_time_data": False,  # Future enhancement
        "advanced_analytics": True
    }
}
```

### Client Integration Examples
1. **Claude integration**
   ```python
   # Example usage with Claude
   mcp_tools = [
       {
           "name": "query_nba_data",
           "description": "Query NBA statistics and play-by-play data",
           "input_schema": {
               "type": "object",
               "properties": {
                   "query": {"type": "string"}
               }
           }
       }
   ]
   ```

2. **Custom application integration**
   ```python
   import asyncio
   from mcp.client import MCPClient
   
   async def query_nba_data(question: str):
       async with MCPClient("nba-pbp-server") as client:
           response = await client.call_tool(
               "query_nba_data",
               {"query": question}
           )
           return response.content
   ```

## Testing and Validation

### Test Scenarios
```python
test_queries = [
    "What are LeBron James' career averages?",
    "How did the Lakers perform against the Celtics in 2023?",
    "Show me Stephen Curry's three-point stats this season",
    "What happened in the fourth quarter of game 7 of the 2016 Finals?",
    "Compare Michael Jordan and Kobe Bryant's playoff performance",
    "Which team has the best home record this season?",
    "Show me the play-by-play for the last 2 minutes of Lakers vs Warriors on March 15, 2024"
]

async def test_query_processing():
    for query in test_queries:
        result = await mcp_server.process_query(query)
        assert result is not None
        assert len(result) > 0
```

### Performance Benchmarks
- Query processing time: <500ms for simple queries
- Complex analytics: <2 seconds
- Natural language accuracy: 90%+ intent recognition
- SQL generation success rate: 95%+

## Documentation and Examples

### API Documentation
```markdown
## NBA MCP Server Tools

### query_nba_data
Query NBA data using natural language.

**Input:**
- `query` (string): Natural language question about NBA data

**Examples:**
- "What are LeBron James' stats this season?"
- "How many points did Kobe score in his final game?"
- "Which team has won the most championships?"

### get_player_stats
Get specific player statistics with structured parameters.

**Input:**
- `player_name` (string): Full or partial player name
- `season` (string, optional): Season in YYYY-YY format
- `stat_type` (string, optional): "basic", "advanced", or "shooting"
```

## Success Criteria
- Natural language queries processed with 90%+ accuracy
- Sub-second response times for common queries
- Integration with major LLM platforms
- Comprehensive coverage of NBA data queries
- Robust error handling and graceful degradation

## Timeline
- **Week 1**: MCP server framework and basic query processing
- **Week 2**: Advanced query understanding and SQL generation
- **Week 3**: Response formatting and context management
- **Week 4**: Testing, optimization, and documentation

## Dependencies
- Completed REST API development (Plan 13)
- MCP protocol libraries and tools
- Natural language processing capabilities
- Database query optimization

## Next Steps
After completion:
1. Integration testing with LLM platforms
2. Performance optimization and caching
3. Advanced analytics features
4. Real-time data integration planning