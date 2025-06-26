#!/usr/bin/env python3
"""
Interactive Demo for NBA MCP Server

This script demonstrates the MCP server capabilities interactively.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.query_translator import NaturalLanguageQueryTranslator
from src.mcp.server import NBAMCPServer
from unittest.mock import AsyncMock


async def demo_session():
    """Run an interactive demo session."""
    print("🏀 NBA MCP Server - Interactive Demo")
    print("=" * 50)
    print("This demo shows how your MCP server processes natural language queries.")
    print("All responses use mock data since we're not connected to the real database.")
    print()
    
    # Set up server with mock data
    server = NBAMCPServer()
    mock_db = AsyncMock()
    
    # Rich mock data with accurate NBA statistics
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
        "comparison": [
            {
                "player_name": "Michael Jordan",
                "games_played": 1072,  # Accurate regular season games
                "points_per_game": 30.1,
                "rebounds_per_game": 6.2,
                "assists_per_game": 5.3,
                "field_goal_percentage": 0.497,
                "three_point_percentage": 0.327,
                "total_points": 32292
            },
            {
                "player_name": "LeBron James", 
                "games_played": 1562,  # Accurate regular season games
                "points_per_game": 27.0,
                "rebounds_per_game": 7.4,
                "assists_per_game": 7.4,
                "field_goal_percentage": 0.506,
                "three_point_percentage": 0.349,
                "total_points": 42184  # All-time scoring leader (current)
            }
        ],
        "lakers": [{
            "team_name": "Los Angeles Lakers",
            "games_played": 82,
            "wins": 47,
            "losses": 35,
            "points_per_game": 115.2,
            "points_allowed_per_game": 113.8,
            "home_wins": 27,
            "road_wins": 20
        }]
    }
    
    async def smart_mock_execute(query, params=None):
        query_lower = query.lower()
        if "compare" in query_lower or "array" in query_lower:
            return mock_responses["comparison"]
        elif "lakers" in query_lower or "team" in query_lower:
            return mock_responses["lakers"] 
        else:
            return mock_responses["lebron"]
    
    mock_db.execute_query = smart_mock_execute
    server.db_manager = mock_db
    
    # Demo queries
    demo_queries = [
        "What are LeBron James career statistics?",
        "Compare Michael Jordan and LeBron James shooting percentages", 
        "How did the Lakers perform this season?",
        "Show me Stephen Curry's three-point stats",
        "What are Kobe Bryant's playoff averages?"
    ]
    
    translator = NaturalLanguageQueryTranslator()
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n🎯 Demo Query {i}: '{query}'")
        print("-" * 60)
        
        # Show the translation process
        context = await translator.translate_query(query)
        print(f"📊 Query Analysis:")
        print(f"   • Type: {context.query_type}")
        print(f"   • Confidence: {context.confidence:.2f}")
        print(f"   • Entities found: {len(context.entities)}")
        if context.entities:
            entities_by_type = {}
            for entity in context.entities:
                if entity.entity_type not in entities_by_type:
                    entities_by_type[entity.entity_type] = []
                entities_by_type[entity.entity_type].append(entity.value)
            
            for entity_type, values in entities_by_type.items():
                print(f"   • {entity_type.title()}: {', '.join(values)}")
        
        if context.season:
            print(f"   • Season: {context.season}")
        
        # Show the response
        print(f"\n🤖 MCP Server Response:")
        try:
            result = await server._handle_natural_language_query(query)
            if result and len(result) > 0:
                response_lines = result[0].text.split('\n')
                for line in response_lines[:15]:  # Show first 15 lines
                    print(f"   {line}")
                if len(response_lines) > 15:
                    print(f"   ... ({len(response_lines) - 15} more lines)")
            else:
                print("   ❌ No response generated")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        input("   Press Enter to continue to next demo...")
    
    print("\n🎉 Demo Complete!")
    print("\nWhat you just saw:")
    print("✅ Natural language understanding")
    print("✅ Entity extraction (players, teams, stats)")
    print("✅ Query classification with confidence scoring")
    print("✅ Structured response generation")
    print("✅ Error handling and graceful degradation")
    
    print("\nWith a real database connection, you would get:")
    print("• Actual NBA statistics from 17M+ play-by-play events")
    print("• Historical data from 1996-2025 seasons")
    print("• Advanced analytics and comparisons")
    print("• Game-by-game breakdowns")
    
    print("\n🚀 Ready to integrate with Claude Desktop!")


if __name__ == "__main__":
    asyncio.run(demo_session())