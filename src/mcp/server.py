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

# Import unified database layer
from core.database import get_async_db_manager

# Import MCP-specific modules
from .query_translator import NaturalLanguageQueryTranslator, QueryContext
from .play_query_processor import PlayQueryProcessor

class NBAMCPServer:
    """NBA Play-by-Play MCP Server implementation."""
    
    def __init__(self):
        self.server = Server("nba-pbp-server")
        self.db_manager = None
        
        # New unified play-by-play processor
        self.play_processor = PlayQueryProcessor()
        
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
                # Try to connect to real database using unified database layer
                self.db_manager = await get_async_db_manager()
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
        
        # Add the same methods as UnifiedDatabaseManager for compatibility
        mock_db.execute_async_query = smart_execute_query
        mock_db.execute_query = smart_execute_query
        return mock_db
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="query_plays",
                    description="Query NBA play-by-play data using natural language - supports shot charts, player plays, clutch moments, comprehensive game analysis, and event filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query about NBA play-by-play data. Examples:\n" +
                                "• 'Show me all LeBron James 3-pointers in the 4th quarter vs Warriors in 2023-24'\n" +
                                "• 'What shots did Curry make from beyond 30 feet this season with coordinates?'\n" +
                                "• 'Get all blocks by Giannis in crunch time when score was within 5'\n" +
                                "• 'Show me Tatum's shot chart in playoffs with x and y coordinates'\n" +
                                "• 'What assists did CP3 have in the final 2 minutes of close games?'\n" +
                                "• 'All plays by Lakers in overtime games this season'\n" +
                                "• 'Clutch shots made in the paint during 2024 playoffs'\n" +
                                "• 'LeBron James dunks vs Warriors 2023-24'\n" +
                                "• 'Show me all free throws by Curry in the 1st quarter'\n" +
                                "• 'Bad pass turnovers by Russell Westbrook this season'\n" +
                                "• 'All layups and driving layups by Ja Morant'\n" +
                                "• 'Personal fouls committed by Draymond Green in playoffs'\n" +
                                "• 'Alley oop dunks in Lakers games this season'"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
            await self._initialize_database()
            
            try:
                if name == "query_plays":
                    # Use the new unified play query processor
                    response_text = await self.play_processor.process_play_query(
                        arguments["query"], 
                        self.db_manager
                    )
                    return [TextContent(type="text", text=response_text)]
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}. Only 'query_plays' is supported.")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
    
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