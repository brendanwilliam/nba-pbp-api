"""
Integration tests for the NBA MCP Server
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.mcp.server import NBAMCPServer
from mcp.types import TextContent


class TestNBAMCPServer:
    """Integration tests for the MCP server."""
    
    @pytest.fixture
    def server(self):
        """Create a server instance for testing."""
        return NBAMCPServer()
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_db = AsyncMock()
        mock_db.execute_query = AsyncMock()
        return mock_db
    
    @pytest.mark.asyncio
    async def test_natural_language_query_processing(self, server, mock_db_manager):
        """Test natural language query processing."""
        # Mock database response
        mock_db_manager.execute_query.return_value = [
            {
                "player_name": "LeBron James",
                "games_played": 82,
                "points_per_game": 25.3,
                "rebounds_per_game": 7.4,
                "assists_per_game": 8.2,
                "field_goal_percentage": 0.525,
                "three_point_percentage": 0.356
            }
        ]
        
        # Patch the database manager
        server.db_manager = mock_db_manager
        
        # Test query
        query = "What are LeBron James career averages?"
        result = await server._handle_natural_language_query(query)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        assert "LeBron James" in result[0].text
        assert "25.3" in result[0].text  # Points per game
    
    @pytest.mark.asyncio
    async def test_player_stats_tool(self, server, mock_db_manager):
        """Test the get_player_stats tool."""
        # Mock database response
        mock_db_manager.execute_query.return_value = [
            {
                "player_name": "Stephen Curry",
                "games_played": 77,
                "points_per_game": 29.5,
                "rebounds_per_game": 5.2,
                "assists_per_game": 6.1,
                "field_goal_percentage": 0.493,
                "three_point_percentage": 0.427
            }
        ]
        
        server.db_manager = mock_db_manager
        
        # Test arguments
        arguments = {
            "player_name": "Stephen Curry",
            "season": "2023-24",
            "stat_type": "basic"
        }
        
        result = await server._handle_player_stats(arguments)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        assert "Stephen Curry" in result[0].text
        assert "29.5" in result[0].text
    
    @pytest.mark.asyncio
    async def test_player_comparison_tool(self, server, mock_db_manager):
        """Test the compare_players tool."""
        # Mock database response
        mock_db_manager.execute_query.return_value = [
            {
                "player_name": "Michael Jordan",
                "games_played": 82,
                "points_per_game": 30.1,
                "rebounds_per_game": 6.2,
                "assists_per_game": 5.3,
                "field_goal_percentage": 0.497
            },
            {
                "player_name": "LeBron James",
                "games_played": 82,
                "points_per_game": 27.1,
                "rebounds_per_game": 7.4,
                "assists_per_game": 7.4,
                "field_goal_percentage": 0.505
            }
        ]
        
        server.db_manager = mock_db_manager
        
        # Test arguments
        arguments = {
            "players": ["Michael Jordan", "LeBron James"],
            "season": "career"
        }
        
        result = await server._handle_player_comparison(arguments)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        assert "Michael Jordan" in result[0].text
        assert "LeBron James" in result[0].text
        assert "30.1" in result[0].text  # Jordan's PPG
        assert "27.1" in result[0].text  # LeBron's PPG
    
    @pytest.mark.asyncio
    async def test_team_analysis_tool(self, server, mock_db_manager):
        """Test the team_analysis tool."""
        # Mock database response
        mock_db_manager.execute_query.return_value = [
            {
                "team_name": "Los Angeles Lakers",
                "games_played": 82,
                "wins": 47,
                "losses": 35,
                "points_per_game": 115.2,
                "points_allowed_per_game": 113.8
            }
        ]
        
        server.db_manager = mock_db_manager
        
        # Test arguments
        arguments = {
            "team_name": "Lakers",
            "season": "2023-24",
            "analysis_type": "season_summary"
        }
        
        result = await server._handle_team_analysis(arguments)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        assert "Lakers" in result[0].text
        assert "47-35" in result[0].text  # Record
        assert "115.2" in result[0].text  # PPG
    
    @pytest.mark.asyncio
    async def test_game_analysis_tool(self, server, mock_db_manager):
        """Test the analyze_game tool."""
        # Mock database response
        mock_db_manager.execute_query.return_value = [
            {
                "game_id": "0022300150",
                "game_date": "2024-01-15",
                "season": "2023-24",
                "home_team": "Los Angeles Lakers",
                "away_team": "Golden State Warriors",
                "home_team_score": 115,
                "away_team_score": 112
            }
        ]
        
        server.db_manager = mock_db_manager
        
        # Test arguments
        arguments = {
            "game_id": "0022300150",
            "analysis_type": "summary"
        }
        
        result = await server._handle_game_analysis(arguments)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        assert "0022300150" in result[0].text
        assert "Lakers" in result[0].text
        assert "Warriors" in result[0].text
        assert "115" in result[0].text
        assert "112" in result[0].text
    
    @pytest.mark.asyncio
    async def test_low_confidence_query_handling(self, server, mock_db_manager):
        """Test handling of low confidence queries."""
        server.db_manager = mock_db_manager
        
        # Test with unclear query
        query = "what is the meaning of life?"
        result = await server._handle_natural_language_query(query)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        # Should contain helpful suggestions
        assert "rephrase" in result[0].text.lower() or "specific" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, server, mock_db_manager):
        """Test error handling in various scenarios."""
        # Mock database to raise an exception
        mock_db_manager.execute_query.side_effect = Exception("Database connection error")
        server.db_manager = mock_db_manager
        
        arguments = {"player_name": "Test Player"}
        result = await server._handle_player_stats(arguments)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        assert "error" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_no_results_handling(self, server, mock_db_manager):
        """Test handling when no results are found."""
        # Mock empty database response
        mock_db_manager.execute_query.return_value = []
        server.db_manager = mock_db_manager
        
        arguments = {"player_name": "Nonexistent Player"}
        result = await server._handle_player_stats(arguments)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], TextContent)
        assert "no" in result[0].text.lower() and "found" in result[0].text.lower()
    
    @pytest.mark.asyncio  
    async def test_database_initialization(self, server):
        """Test database initialization."""
        # Should not raise an exception
        await server._initialize_database()
        
        # Database manager should be set
        assert server.db_manager is not None