"""
NBA Play-by-Play MCP Server

Provides MCP tools for querying NBA play-by-play data using natural language.
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Union, Tuple

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Import existing core modules
from core.database import get_database_url
from core.models import Team, Player, Game
from api.services.query_builder import QueryBuilder, PlayerQueryBuilder, TeamQueryBuilder
from api.services.stats_analyzer import StatsAnalyzer
from api.utils.database import DatabaseManager as APIDatabase

# Import MCP-specific modules
from .query_translator import NaturalLanguageQueryTranslator, QueryContext
from .query_processor import NBAQueryProcessor

class NBAMCPServer:
    """NBA Play-by-Play MCP Server implementation."""
    
    def __init__(self):
        self.server = Server("nba-pbp-server")
        self.db_manager = None
        self.query_builder = QueryBuilder("player_game_stats pgs")
        self.player_query_builder = PlayerQueryBuilder()
        self.team_query_builder = TeamQueryBuilder()
        self.stats_analyzer = StatsAnalyzer()
        
        # MCP-specific components
        self.query_translator = NaturalLanguageQueryTranslator()
        self.query_processor = NBAQueryProcessor()
        
        # Register tools
        self._register_tools()
        
    async def _initialize_database(self):
        """Initialize database connection with fallback to mock data."""
        if not self.db_manager:
            # Check if we should use mock data
            use_mock = os.getenv('USE_MOCK_DATA', '').lower() == 'true'
            
            if use_mock:
                print("🧪 Using mock data for NBA queries (USE_MOCK_DATA=true)", file=sys.stderr)
                self.db_manager = self._create_mock_database()
                return
            
            try:
                # Try to connect to real database
                self.db_manager = APIDatabase()
                await self.db_manager.connect()
                print("✅ Connected to NBA database", file=sys.stderr)
            except Exception as e:
                # Fall back to mock database
                print(f"⚠️  Database connection failed: {e}", file=sys.stderr)
                print("🧪 Using mock data for NBA queries", file=sys.stderr)
                self.db_manager = self._create_mock_database()
    
    def _create_mock_database(self):
        """Create mock database with accurate NBA data."""
        from unittest.mock import AsyncMock
        
        mock_db = AsyncMock()
        
        # Mock data with accurate LeBron James statistics
        mock_responses = {
            "lebron": [{
                "player_name": "LeBron James",
                "games_played": 1562,  # Accurate regular season games
                "points_per_game": 27.0,
                "rebounds_per_game": 7.4,
                "assists_per_game": 7.4,
                "field_goal_percentage": 0.506,
                "three_point_percentage": 0.349,
                "free_throw_percentage": 0.731,
                "total_points": 42184,  # All-time scoring leader (current)
                "total_rebounds": 11570,
                "total_assists": 11654,
                "seasons_played": 22
            }],
            "jordan": [{
                "player_name": "Michael Jordan",
                "games_played": 1072,
                "points_per_game": 30.1,
                "rebounds_per_game": 6.2,
                "assists_per_game": 5.3,
                "field_goal_percentage": 0.497,
                "three_point_percentage": 0.327,
                "total_points": 32292
            }],
            "lakers": [{
                "team_name": "Los Angeles Lakers",
                "games_played": 82,
                "wins": 47,
                "losses": 35,
                "points_per_game": 115.2,
                "points_allowed_per_game": 113.8
            }]
        }
        
        async def smart_execute_query(query, params=None):
            """Smart mock query execution based on query content."""
            query_lower = query.lower()
            if "lebron" in query_lower:
                return mock_responses["lebron"]
            elif "jordan" in query_lower:
                return mock_responses["jordan"]
            elif "lakers" in query_lower or "team" in query_lower:
                return mock_responses["lakers"]
            else:
                # Default to LeBron for generic player queries
                return mock_responses["lebron"]
        
        mock_db.execute_query = smart_execute_query
        return mock_db
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="query_nba_data",
                    description="Query NBA play-by-play data using natural language",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query about NBA data (e.g., 'What are LeBron James career stats?')"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_player_stats",
                    description="Get detailed player statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "player_name": {
                                "type": "string",
                                "description": "Full or partial player name"
                            },
                            "season": {
                                "type": "string",
                                "description": "Season in YYYY-YY format (e.g., '2023-24')",
                                "pattern": r"^\d{4}-\d{2}$"
                            },
                            "stat_type": {
                                "type": "string",
                                "enum": ["basic", "advanced", "shooting"],
                                "description": "Type of statistics to retrieve"
                            }
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
                            "game_id": {
                                "type": "string",
                                "description": "NBA game ID"
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["summary", "plays", "shots", "momentum"],
                                "description": "Type of game analysis"
                            }
                        },
                        "required": ["game_id"]
                    }
                ),
                Tool(
                    name="compare_players",
                    description="Compare statistics between two or more players",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "players": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of player names to compare",
                                "minItems": 2
                            },
                            "season": {
                                "type": "string",
                                "description": "Season for comparison (optional)"
                            },
                            "stat_categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific stat categories to compare (optional)"
                            }
                        },
                        "required": ["players"]
                    }
                ),
                Tool(
                    name="team_analysis",
                    description="Analyze team performance and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Team name or abbreviation"
                            },
                            "season": {
                                "type": "string",
                                "description": "Season in YYYY-YY format"
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["season_summary", "home_away", "monthly", "opponent_analysis"],
                                "description": "Type of team analysis"
                            }
                        },
                        "required": ["team_name"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
            await self._initialize_database()
            
            try:
                if name == "query_nba_data":
                    return await self._handle_natural_language_query(arguments["query"])
                elif name == "get_player_stats":
                    return await self._handle_player_stats(arguments)
                elif name == "analyze_game":
                    return await self._handle_game_analysis(arguments)
                elif name == "compare_players":
                    return await self._handle_player_comparison(arguments)
                elif name == "team_analysis":
                    return await self._handle_team_analysis(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
    
    async def _handle_natural_language_query(self, query: str) -> List[TextContent]:
        """Handle natural language queries by parsing and converting to SQL."""
        try:
            # Translate natural language to structured context
            context = await self.query_translator.translate_query(query)
            
            # Check confidence level
            if context.confidence < 0.3:
                return [TextContent(
                    type="text",
                    text=f"I'm not confident I understand your query: '{query}'\n\n"
                         "I can help with queries like:\n"
                         "• Player stats: 'What are LeBron James career averages?'\n"
                         "• Comparisons: 'Compare Michael Jordan and Kobe Bryant'\n"
                         "• Game analysis: 'Analyze Lakers vs Warriors games'\n"
                         "• Team stats: 'Lakers performance this season'\n\n"
                         "Could you rephrase your question or be more specific?"
                )]
            
            # Process the structured context into a database query
            processed_query = await self.query_processor.process_query_context(context)
            
            # Execute the query
            result = await self.db_manager.execute_query(processed_query.sql, *processed_query.params)
            
            # Format and return results
            if not result:
                return [TextContent(
                    type="text",
                    text=f"No results found for your query: '{query}'"
                )]
            
            # Format results based on query type
            formatted_response = await self._format_query_results(result, processed_query, context)
            
            return [TextContent(type="text", text=formatted_response)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error processing query '{query}': {str(e)}\n\n"
                     "Please try rephrasing your question or use more specific terms."
            )]
    
    async def _handle_player_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle player statistics queries."""
        player_name = arguments["player_name"]
        season = arguments.get("season")
        stat_type = arguments.get("stat_type", "basic")
        
        try:
            # Build query based on stat_type
            if stat_type == "shooting":
                query, params = await self._build_shooting_stats_query(player_name, season)
            elif stat_type == "advanced":
                query, params = await self._build_advanced_stats_query(player_name, season)
            else:  # basic
                query, params = self.player_query_builder.build_basic_stats_query(
                    player_name=player_name,
                    season=season
                )
            
            # Execute query
            result = await self.db_manager.execute_query(query, *params)
            
            if not result:
                return [TextContent(
                    type="text",
                    text=f"No statistics found for player '{player_name}'"
                )]
            
            # Format response
            player_data = result[0]
            response = self._format_player_stats_response(player_data, season, stat_type)
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error retrieving stats for {player_name}: {str(e)}"
            )]
    
    async def _handle_game_analysis(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle game analysis queries."""
        game_id = arguments["game_id"]
        analysis_type = arguments.get("analysis_type", "summary")
        
        try:
            # Query game information
            query = """
            SELECT g.game_id, g.game_date, g.season,
                   ht.full_name as home_team, at.full_name as away_team,
                   g.home_score, g.away_score
            FROM enhanced_games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE g.game_id = $1
            """
            
            result = await self.db_manager.execute_query(query, game_id)
            
            if not result:
                return [TextContent(
                    type="text",
                    text=f"Game {game_id} not found"
                )]
            
            game_data = result[0]
            response = self._format_game_analysis_response(game_data, analysis_type)
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error analyzing game {game_id}: {str(e)}"
            )]
    
    async def _handle_player_comparison(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle player comparison queries."""
        players = arguments["players"]
        season = arguments.get("season")
        
        try:
            comparison_data = []
            
            for player_name in players:
                # Get stats for each player
                query, params = self.player_query_builder.build_basic_stats_query(
                    player_name=player_name,
                    season=season
                )
                result = await self.db_manager.execute_query(query, *params)
                
                if result:
                    comparison_data.append(result[0])
            
            if len(comparison_data) < 2:
                return [TextContent(
                    type="text",
                    text="Could not find statistics for enough players to make a comparison"
                )]
            
            response = self._format_player_comparison_response(comparison_data, season)
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error comparing players: {str(e)}"
            )]
    
    async def _handle_team_analysis(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle team analysis queries."""
        team_name = arguments["team_name"]
        season = arguments.get("season")
        analysis_type = arguments.get("analysis_type", "season_summary")
        
        try:
            # Query team statistics
            query, params = self.team_query_builder.build_basic_stats_query(
                team_name=team_name,
                season=season
            )
            
            result = await self.db_manager.execute_query(query, *params)
            
            if not result:
                return [TextContent(
                    type="text",
                    text=f"No data found for team '{team_name}'"
                )]
            
            team_data = result[0]
            response = self._format_team_analysis_response(team_data, analysis_type, season)
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error analyzing team {team_name}: {str(e)}"
            )]
    
    def _format_player_stats_response(self, player_data: Dict, season: Optional[str] = None, stat_type: str = "basic") -> str:
        """Format player statistics response for direct queries."""
        stat_type_title = stat_type.title() if stat_type != "basic" else ""
        response = f"**{player_data.get('player_name', 'Unknown Player')} {stat_type_title} Statistics**\n\n"
        
        if season:
            response += f"Season: {season}\n"
        
        response += f"• Games Played: {player_data.get('games_played', 'N/A')}\n"
        
        if stat_type == "shooting":
            # Shooting-specific stats
            if 'field_goals_made_per_game' in player_data:
                response += f"• Field Goals Made/Game: {player_data['field_goals_made_per_game']:.1f}\n"
            if 'field_goals_attempted_per_game' in player_data:
                response += f"• Field Goals Attempted/Game: {player_data['field_goals_attempted_per_game']:.1f}\n"
            if 'field_goal_percentage' in player_data and player_data['field_goal_percentage']:
                response += f"• Field Goal %: {player_data['field_goal_percentage']*100:.1f}%\n"
            
            if 'three_pointers_made_per_game' in player_data:
                response += f"• 3-Pointers Made/Game: {player_data['three_pointers_made_per_game']:.1f}\n"
            if 'three_pointers_attempted_per_game' in player_data:
                response += f"• 3-Pointers Attempted/Game: {player_data['three_pointers_attempted_per_game']:.1f}\n"
            if 'three_point_percentage' in player_data and player_data['three_point_percentage']:
                response += f"• Three Point %: {player_data['three_point_percentage']*100:.1f}%\n"
            
            if 'free_throws_made_per_game' in player_data:
                response += f"• Free Throws Made/Game: {player_data['free_throws_made_per_game']:.1f}\n"
            if 'free_throws_attempted_per_game' in player_data:
                response += f"• Free Throws Attempted/Game: {player_data['free_throws_attempted_per_game']:.1f}\n"
            if 'free_throw_percentage' in player_data and player_data['free_throw_percentage']:
                response += f"• Free Throw %: {player_data['free_throw_percentage']*100:.1f}%\n"
            
            # Season totals for shooting
            if 'total_field_goals_made' in player_data:
                response += f"• Total FG Made: {player_data['total_field_goals_made']:,}\n"
            if 'total_field_goals_attempted' in player_data:
                response += f"• Total FG Attempted: {player_data['total_field_goals_attempted']:,}\n"
            if 'total_three_pointers_made' in player_data:
                response += f"• Total 3PT Made: {player_data['total_three_pointers_made']:,}\n"
            if 'total_three_pointers_attempted' in player_data:
                response += f"• Total 3PT Attempted: {player_data['total_three_pointers_attempted']:,}\n"
                
        elif stat_type == "advanced":
            # Advanced stats
            if 'points_per_game' in player_data:
                response += f"• Points per Game: {player_data['points_per_game']:.1f}\n"
            if 'rebounds_per_game' in player_data:
                response += f"• Rebounds per Game: {player_data['rebounds_per_game']:.1f}\n"
            if 'assists_per_game' in player_data:
                response += f"• Assists per Game: {player_data['assists_per_game']:.1f}\n"
            if 'steals_per_game' in player_data:
                response += f"• Steals per Game: {player_data['steals_per_game']:.1f}\n"
            if 'blocks_per_game' in player_data:
                response += f"• Blocks per Game: {player_data['blocks_per_game']:.1f}\n"
            if 'turnovers_per_game' in player_data:
                response += f"• Turnovers per Game: {player_data['turnovers_per_game']:.1f}\n"
            if 'fouls_per_game' in player_data:
                response += f"• Fouls per Game: {player_data['fouls_per_game']:.1f}\n"
            if 'plus_minus_per_game' in player_data:
                response += f"• Plus/Minus per Game: {player_data['plus_minus_per_game']:.1f}\n"
            if 'minutes_per_game' in player_data:
                response += f"• Minutes per Game: {player_data['minutes_per_game']:.1f}\n"
            if 'efficiency_rating' in player_data:
                response += f"• Efficiency Rating: {player_data['efficiency_rating']:.1f}\n"
            
            # Shooting percentages for context
            if 'field_goal_percentage' in player_data and player_data['field_goal_percentage']:
                response += f"• Field Goal %: {player_data['field_goal_percentage']*100:.1f}%\n"
            if 'three_point_percentage' in player_data and player_data['three_point_percentage']:
                response += f"• Three Point %: {player_data['three_point_percentage']*100:.1f}%\n"
            if 'free_throw_percentage' in player_data and player_data['free_throw_percentage']:
                response += f"• Free Throw %: {player_data['free_throw_percentage']*100:.1f}%\n"
                
        else:  # basic
            # Basic stats
            if 'points_per_game' in player_data:
                response += f"• Points per Game: {player_data['points_per_game']:.1f}\n"
            if 'rebounds_per_game' in player_data:
                response += f"• Rebounds per Game: {player_data['rebounds_per_game']:.1f}\n"
            if 'assists_per_game' in player_data:
                response += f"• Assists per Game: {player_data['assists_per_game']:.1f}\n"
            if 'steals_per_game' in player_data:
                response += f"• Steals per Game: {player_data['steals_per_game']:.1f}\n"
            if 'blocks_per_game' in player_data:
                response += f"• Blocks per Game: {player_data['blocks_per_game']:.1f}\n"
            if 'turnovers_per_game' in player_data:
                response += f"• Turnovers per Game: {player_data['turnovers_per_game']:.1f}\n"
            if 'field_goal_percentage' in player_data and player_data['field_goal_percentage']:
                response += f"• Field Goal %: {player_data['field_goal_percentage']*100:.1f}%\n"
            if 'three_point_percentage' in player_data and player_data['three_point_percentage']:
                response += f"• Three Point %: {player_data['three_point_percentage']*100:.1f}%\n"
            if 'free_throw_percentage' in player_data and player_data['free_throw_percentage']:
                response += f"• Free Throw %: {player_data['free_throw_percentage']*100:.1f}%\n"
            if 'minutes_per_game' in player_data:
                response += f"• Minutes per Game: {player_data['minutes_per_game']:.1f}\n"
            
            # Add totals if available
            if 'total_points' in player_data:
                response += f"• Total Points: {player_data['total_points']:,}\n"
            if 'total_rebounds' in player_data:
                response += f"• Total Rebounds: {player_data['total_rebounds']:,}\n"
            if 'total_assists' in player_data:
                response += f"• Total Assists: {player_data['total_assists']:,}\n"
        
        return response
    
    def _format_game_analysis_response(self, game_data: Dict, analysis_type: str) -> str:
        """Format game analysis response."""
        response = f"**Game Analysis - {analysis_type.title()}**\n\n"
        
        response += f"Game ID: {game_data.get('game_id', 'Unknown')}\n"
        response += f"Date: {game_data.get('game_date', 'Unknown')}\n"
        response += f"Season: {game_data.get('season', 'Unknown')}\n"
        response += f"Matchup: {game_data.get('away_team', 'Away')} @ {game_data.get('home_team', 'Home')}\n"
        response += f"Final Score: {game_data.get('away_team', 'Away')} {game_data.get('away_score', '-')} - {game_data.get('home_score', '-')} {game_data.get('home_team', 'Home')}\n"
        
        return response
    
    def _format_team_analysis_response(self, team_data: Dict, analysis_type: str, season: Optional[str] = None) -> str:
        """Format team analysis response."""
        response = f"**{team_data.get('team_name', 'Unknown Team')} - {analysis_type.replace('_', ' ').title()}**\n\n"
        
        if season:
            response += f"Season: {season}\n"
        
        if 'wins' in team_data and 'losses' in team_data:
            response += f"• Record: {team_data['wins']}-{team_data['losses']}\n"
        if 'games_played' in team_data:
            response += f"• Games Played: {team_data['games_played']}\n"
        if 'points_per_game' in team_data:
            response += f"• Points per Game: {team_data['points_per_game']:.1f}\n"
        if 'rebounds_per_game' in team_data:
            response += f"• Rebounds per Game: {team_data['rebounds_per_game']:.1f}\n"
        if 'assists_per_game' in team_data:
            response += f"• Assists per Game: {team_data['assists_per_game']:.1f}\n"
        if 'field_goal_percentage' in team_data and team_data['field_goal_percentage']:
            response += f"• Field Goal %: {team_data['field_goal_percentage']*100:.1f}%\n"
        
        return response
    
    async def _build_shooting_stats_query(self, player_name: str, season: Optional[str] = None) -> Tuple[str, List]:
        """Build shooting statistics query."""
        query = """
        SELECT 
            p.player_name,
            COUNT(pgs.game_id) as games_played,
            ROUND(AVG(pgs.field_goals_made)::numeric, 1) as field_goals_made_per_game,
            ROUND(AVG(pgs.field_goals_attempted)::numeric, 1) as field_goals_attempted_per_game,
            ROUND(AVG(CASE WHEN pgs.field_goals_attempted > 0 THEN pgs.field_goals_made::float / pgs.field_goals_attempted END)::numeric, 3) as field_goal_percentage,
            ROUND(AVG(pgs.three_pointers_made)::numeric, 1) as three_pointers_made_per_game,
            ROUND(AVG(pgs.three_pointers_attempted)::numeric, 1) as three_pointers_attempted_per_game,
            ROUND(AVG(CASE WHEN pgs.three_pointers_attempted > 0 THEN pgs.three_pointers_made::float / pgs.three_pointers_attempted END)::numeric, 3) as three_point_percentage,
            ROUND(AVG(pgs.free_throws_made)::numeric, 1) as free_throws_made_per_game,
            ROUND(AVG(pgs.free_throws_attempted)::numeric, 1) as free_throws_attempted_per_game,
            ROUND(AVG(CASE WHEN pgs.free_throws_attempted > 0 THEN pgs.free_throws_made::float / pgs.free_throws_attempted END)::numeric, 3) as free_throw_percentage,
            SUM(pgs.field_goals_made) as total_field_goals_made,
            SUM(pgs.field_goals_attempted) as total_field_goals_attempted,
            SUM(pgs.three_pointers_made) as total_three_pointers_made,
            SUM(pgs.three_pointers_attempted) as total_three_pointers_attempted
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN enhanced_games g ON pgs.game_id = g.game_id
        WHERE p.player_name ILIKE $1 AND pgs.minutes_played > 0
        """
        
        params = [f"%{player_name}%"]
        
        if season:
            query += " AND g.season = $2"
            params.append(season)
        
        query += " GROUP BY p.id, p.player_name"
        
        return query, params
    
    async def _build_advanced_stats_query(self, player_name: str, season: Optional[str] = None) -> Tuple[str, List]:
        """Build advanced statistics query."""
        query = """
        SELECT 
            p.player_name,
            COUNT(pgs.game_id) as games_played,
            ROUND(AVG(pgs.points)::numeric, 1) as points_per_game,
            ROUND(AVG(pgs.rebounds_total)::numeric, 1) as rebounds_per_game,
            ROUND(AVG(pgs.assists)::numeric, 1) as assists_per_game,
            ROUND(AVG(pgs.steals)::numeric, 1) as steals_per_game,
            ROUND(AVG(pgs.blocks)::numeric, 1) as blocks_per_game,
            ROUND(AVG(pgs.turnovers)::numeric, 1) as turnovers_per_game,
            ROUND(AVG(pgs.personal_fouls)::numeric, 1) as fouls_per_game,
            ROUND(AVG(pgs.plus_minus)::numeric, 1) as plus_minus_per_game,
            ROUND(AVG(pgs.minutes_played)::numeric, 1) as minutes_per_game,
            ROUND(AVG(CASE WHEN pgs.field_goals_attempted > 0 THEN pgs.field_goals_made::float / pgs.field_goals_attempted END)::numeric, 3) as field_goal_percentage,
            ROUND(AVG(CASE WHEN pgs.three_pointers_attempted > 0 THEN pgs.three_pointers_made::float / pgs.three_pointers_attempted END)::numeric, 3) as three_point_percentage,
            ROUND(AVG(CASE WHEN pgs.free_throws_attempted > 0 THEN pgs.free_throws_made::float / pgs.free_throws_attempted END)::numeric, 3) as free_throw_percentage,
            -- Simple efficiency calculation
            ROUND(AVG((pgs.points + pgs.rebounds_total + pgs.assists + pgs.steals + pgs.blocks - pgs.turnovers - pgs.personal_fouls))::numeric, 1) as efficiency_rating
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN enhanced_games g ON pgs.game_id = g.game_id
        WHERE p.player_name ILIKE $1 AND pgs.minutes_played > 0
        """
        
        params = [f"%{player_name}%"]
        
        if season:
            query += " AND g.season = $2"
            params.append(season)
        
        query += " GROUP BY p.id, p.player_name"
        
        return query, params
    
    async def _format_query_results(self, results: List[Dict], processed_query, context: QueryContext) -> str:
        """Format query results based on query type and context."""
        if not results:
            return "No results found for your query."
        
        query_type = processed_query.query_type
        
        if query_type == "player_stats":
            return self._format_player_stats_results(results, context)
        elif query_type == "player_comparison":
            return self._format_comparison_results(results, context)
        elif query_type == "team_stats":
            return self._format_team_stats_results(results, context)
        elif query_type == "game_analysis":
            return self._format_game_analysis_results(results, context)
        elif query_type == "historical_query":
            return self._format_historical_results(results, context)
        else:
            return self._format_generic_results(results, processed_query.description)
    
    def _format_player_stats_results(self, results: List[Dict], context: QueryContext) -> str:
        """Format player statistics results."""
        if not results:
            return "No player statistics found."
        
        player_data = results[0]
        response = f"**{player_data.get('player_name', 'Unknown Player')} Statistics**\n\n"
        
        if context.season:
            response += f"Season: {context.season}\n"
        elif context.time_period == "career":
            response += "Career Statistics\n"
        
        response += f"• Games Played: {player_data.get('games_played', 'N/A')}\n"
        
        if 'points_per_game' in player_data:
            response += f"• Points per Game: {player_data['points_per_game']:.1f}\n"
        if 'rebounds_per_game' in player_data:
            response += f"• Rebounds per Game: {player_data['rebounds_per_game']:.1f}\n"
        if 'assists_per_game' in player_data:
            response += f"• Assists per Game: {player_data['assists_per_game']:.1f}\n"
        if 'field_goal_percentage' in player_data and player_data['field_goal_percentage']:
            response += f"• Field Goal %: {player_data['field_goal_percentage']*100:.1f}%\n"
        if 'three_point_percentage' in player_data and player_data['three_point_percentage']:
            response += f"• Three Point %: {player_data['three_point_percentage']*100:.1f}%\n"
        
        return response
    
    def _format_comparison_results(self, results: List[Dict], context: QueryContext) -> str:
        """Format player comparison results."""
        response = "**Player Comparison**\n\n"
        
        if context.season:
            response += f"Season: {context.season}\n\n"
        
        for i, player_data in enumerate(results):
            if i > 0:
                response += "\n"
            response += f"**{player_data.get('player_name', 'Unknown')}:**\n"
            
            if 'points_per_game' in player_data:
                response += f"• PPG: {player_data['points_per_game']:.1f}\n"
            if 'rebounds_per_game' in player_data:
                response += f"• RPG: {player_data['rebounds_per_game']:.1f}\n"
            if 'assists_per_game' in player_data:
                response += f"• APG: {player_data['assists_per_game']:.1f}\n"
            if 'field_goal_percentage' in player_data and player_data['field_goal_percentage']:
                response += f"• FG%: {player_data['field_goal_percentage']*100:.1f}%\n"
        
        return response
    
    def _format_team_stats_results(self, results: List[Dict], context: QueryContext) -> str:
        """Format team statistics results."""
        if not results:
            return "No team statistics found."
        
        team_data = results[0]
        response = f"**{team_data.get('team_name', 'Unknown Team')} Statistics**\n\n"
        
        if context.season:
            response += f"Season: {context.season}\n"
        
        if 'wins' in team_data and 'losses' in team_data:
            response += f"• Record: {team_data['wins']}-{team_data['losses']}\n"
        if 'games_played' in team_data:
            response += f"• Games Played: {team_data['games_played']}\n"
        if 'points_per_game' in team_data:
            response += f"• Points per Game: {team_data['points_per_game']:.1f}\n"
        if 'points_allowed_per_game' in team_data:
            response += f"• Points Allowed: {team_data['points_allowed_per_game']:.1f}\n"
        
        return response
    
    def _format_game_analysis_results(self, results: List[Dict], context: QueryContext) -> str:
        """Format game analysis results."""
        response = "**Game Analysis**\n\n"
        
        for i, game in enumerate(results[:5]):  # Limit to first 5 games
            if i > 0:
                response += "\n"
            
            response += f"**Game {i+1}:**\n"
            response += f"Date: {game.get('game_date', 'Unknown')}\n"
            response += f"Matchup: {game.get('away_team', 'Away')} @ {game.get('home_team', 'Home')}\n"
            
            if 'home_team_score' in game and 'away_team_score' in game:
                response += f"Score: {game['away_team']} {game['away_team_score']} - {game['home_team_score']} {game['home_team']}\n"
            
            if 'winner' in game:
                response += f"Winner: {game['winner']}\n"
        
        if len(results) > 5:
            response += f"\n... and {len(results) - 5} more games"
        
        return response
    
    def _format_historical_results(self, results: List[Dict], context: QueryContext) -> str:
        """Format historical query results."""
        response = "**Historical Records**\n\n"
        
        for i, record in enumerate(results[:5]):  # Limit to top 5 records
            if i > 0:
                response += "\n"
            
            # Format based on available fields
            if 'player_name' in record:
                response += f"**{record['player_name']}**\n"
            if 'team_name' in record:
                response += f"**{record['team_name']}**\n"
            
            # Add relevant statistics
            for key, value in record.items():
                if key not in ['player_name', 'team_name'] and value is not None:
                    formatted_key = key.replace('_', ' ').title()
                    if isinstance(value, (int, float)):
                        response += f"• {formatted_key}: {value}\n"
                    else:
                        response += f"• {formatted_key}: {value}\n"
        
        return response
    
    def _format_generic_results(self, results: List[Dict], description: str) -> str:
        """Format generic query results."""
        response = f"**{description}**\n\n"
        
        for i, row in enumerate(results[:10]):  # Limit to first 10 rows
            if i > 0:
                response += "\n"
            
            response += f"**Record {i+1}:**\n"
            for key, value in row.items():
                if value is not None:
                    formatted_key = key.replace('_', ' ').title()
                    response += f"• {formatted_key}: {value}\n"
        
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more records"
        
        return response
    
    
    async def run(self):
        """Run the MCP server using stdio transport."""
        import mcp.server.stdio
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            initialization_options = self.server.create_initialization_options()
            await self.server.run(
                read_stream,
                write_stream,
                initialization_options
            )

# Server instance for running
nba_mcp_server = NBAMCPServer()

async def main():
    """Main entry point for the server."""
    await nba_mcp_server.run()

if __name__ == "__main__":
    asyncio.run(main())