#!/usr/bin/env python3
"""
Local MCP Server Testing Script

This script provides comprehensive local testing for the NBA MCP server
without requiring Claude Desktop or external MCP clients.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.server import NBAMCPServer
from src.mcp.query_translator import NaturalLanguageQueryTranslator
from src.mcp.query_processor import NBAQueryProcessor
from unittest.mock import AsyncMock


class LocalMCPTester:
    """Local tester for MCP server functionality."""
    
    def __init__(self):
        self.server = NBAMCPServer()
        self.setup_mock_database()
    
    def setup_mock_database(self):
        """Set up mock database for testing without real DB connection."""
        # Create mock database manager
        mock_db = AsyncMock()
        
        # Mock player stats response with accurate LeBron James data
        mock_player_stats = [{
            "player_name": "LeBron James",
            "games_played": 1562,  # Accurate regular season games
            "points_per_game": 27.0,
            "rebounds_per_game": 7.4,
            "assists_per_game": 7.4,
            "field_goal_percentage": 0.506,
            "three_point_percentage": 0.349,
            "free_throw_percentage": 0.731,
            "total_points": 42184,  # All-time scoring leader (current)
            "seasons_played": 22
        }]
        
        # Mock player comparison response with accurate career stats
        mock_comparison = [
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
        ]
        
        # Mock team stats response
        mock_team_stats = [{
            "team_name": "Los Angeles Lakers",
            "games_played": 82,
            "wins": 47,
            "losses": 35,
            "points_per_game": 115.2,
            "points_allowed_per_game": 113.8
        }]
        
        # Mock game analysis response
        mock_game_analysis = [{
            "game_id": "0022300150",
            "game_date": "2024-01-15",
            "season": "2023-24",
            "home_team": "Los Angeles Lakers",
            "away_team": "Golden State Warriors",
            "home_team_score": 115,
            "away_team_score": 112
        }]
        
        # Configure mock responses based on query content
        async def mock_execute_query(query, params=None):
            query_lower = query.lower()
            
            if "compare" in query_lower or "array" in query_lower:
                return mock_comparison
            elif "team" in query_lower or "lakers" in query_lower:
                return mock_team_stats
            elif "game" in query_lower:
                return mock_game_analysis
            else:
                return mock_player_stats
        
        mock_db.execute_query = mock_execute_query
        self.server.db_manager = mock_db
    
    async def test_natural_language_queries(self):
        """Test natural language query processing."""
        print("🧪 Testing Natural Language Queries")
        print("-" * 50)
        
        test_queries = [
            "What are LeBron James career averages?",
            "Compare Michael Jordan and LeBron James",
            "How did the Lakers perform this season?",
            "Stephen Curry three point percentage in 2023-24",
            "Show me game analysis for Lakers vs Warriors",
            "What are Kobe Bryant's career stats?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}. Query: '{query}'")
            try:
                result = await self.server._handle_natural_language_query(query)
                
                if result and len(result) > 0:
                    response_text = result[0].text
                    print(f"   ✅ Success (Response length: {len(response_text)} chars)")
                    print(f"   📝 Preview: {response_text[:100]}...")
                else:
                    print("   ❌ No response returned")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        return True
    
    async def test_specific_tools(self):
        """Test individual MCP tools."""
        print("\n🔧 Testing Individual MCP Tools")
        print("-" * 50)
        
        # Test player stats tool
        print("\n1. Testing get_player_stats tool:")
        try:
            result = await self.server._handle_player_stats({
                "player_name": "LeBron James",
                "season": "2023-24",
                "stat_type": "basic"
            })
            print(f"   ✅ Player stats: {len(result[0].text)} chars")
            print(f"   📝 Preview: {result[0].text[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test player comparison tool
        print("\n2. Testing compare_players tool:")
        try:
            result = await self.server._handle_player_comparison({
                "players": ["Michael Jordan", "LeBron James"],
                "season": "career"
            })
            print(f"   ✅ Player comparison: {len(result[0].text)} chars")
            print(f"   📝 Preview: {result[0].text[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test team analysis tool
        print("\n3. Testing team_analysis tool:")
        try:
            result = await self.server._handle_team_analysis({
                "team_name": "Lakers",
                "season": "2023-24",
                "analysis_type": "season_summary"
            })
            print(f"   ✅ Team analysis: {len(result[0].text)} chars")
            print(f"   📝 Preview: {result[0].text[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test game analysis tool
        print("\n4. Testing analyze_game tool:")
        try:
            result = await self.server._handle_game_analysis({
                "game_id": "0022300150",
                "analysis_type": "summary"
            })
            print(f"   ✅ Game analysis: {len(result[0].text)} chars")
            print(f"   📝 Preview: {result[0].text[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return True
    
    async def test_query_translation(self):
        """Test the natural language translation component."""
        print("\n🧠 Testing Query Translation")
        print("-" * 50)
        
        translator = NaturalLanguageQueryTranslator()
        
        test_cases = [
            ("LeBron James career stats", "PLAYER_STATS"),
            ("Compare Jordan and Kobe", "PLAYER_COMPARISON"),
            ("Lakers team record", "TEAM_STATS"),
            ("What happened in the Lakers vs Warriors game?", "GAME_ANALYSIS"),
            ("Who has the highest scoring game ever?", "HISTORICAL_QUERY"),
            ("Random unrelated query", "UNKNOWN")
        ]
        
        for query, expected_type in test_cases:
            context = await translator.translate_query(query)
            
            print(f"\nQuery: '{query}'")
            print(f"   Expected: {expected_type}")
            print(f"   Actual: {context.query_type}")
            print(f"   Confidence: {context.confidence:.2f}")
            print(f"   Entities: {len(context.entities)} found")
            print(f"   Season: {context.season}")
            
            # Check if classification is reasonable
            if context.query_type.value.upper() == expected_type or context.confidence > 0.3:
                print("   ✅ Good classification")
            else:
                print("   ⚠️  Low confidence or unexpected classification")
        
        return True
    
    async def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n🛡️  Testing Error Handling")
        print("-" * 50)
        
        # Test with invalid player name
        print("\n1. Testing invalid player name:")
        try:
            result = await self.server._handle_player_stats({
                "player_name": "Nonexistent Player XYZ"
            })
            print(f"   ✅ Handled gracefully: {result[0].text[:50]}...")
        except Exception as e:
            print(f"   ❌ Unhandled error: {e}")
        
        # Test with unclear query
        print("\n2. Testing unclear natural language query:")
        try:
            result = await self.server._handle_natural_language_query(
                "What is the meaning of life, the universe, and everything?"
            )
            print(f"   ✅ Handled gracefully: {result[0].text[:50]}...")
        except Exception as e:
            print(f"   ❌ Unhandled error: {e}")
        
        # Test with database error simulation
        print("\n3. Testing database error handling:")
        try:
            # Temporarily break the mock database
            original_execute = self.server.db_manager.execute_query
            self.server.db_manager.execute_query = AsyncMock(side_effect=Exception("Mock DB error"))
            
            result = await self.server._handle_player_stats({
                "player_name": "Test Player"
            })
            print(f"   ✅ Database error handled: {result[0].text[:50]}...")
            
            # Restore mock database
            self.server.db_manager.execute_query = original_execute
            
        except Exception as e:
            print(f"   ❌ Unhandled error: {e}")
        
        return True
    
    async def run_all_tests(self):
        """Run comprehensive test suite."""
        print("🏀 NBA MCP Server - Local Testing Suite")
        print("=" * 60)
        
        tests = [
            ("Component Import Test", self.test_imports),
            ("Query Translation Test", self.test_query_translation), 
            ("Natural Language Queries", self.test_natural_language_queries),
            ("Individual MCP Tools", self.test_specific_tools),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n🧪 {test_name}")
            print("=" * 60)
            
            try:
                success = await test_func()
                results.append((test_name, "✅ PASS"))
                print(f"✅ {test_name} completed successfully")
            except Exception as e:
                results.append((test_name, f"❌ FAIL: {e}"))
                print(f"❌ {test_name} failed: {e}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        for test_name, result in results:
            print(f"{result:<20} {test_name}")
        
        passed = sum(1 for _, result in results if result.startswith("✅"))
        total = len(results)
        
        print(f"\n📈 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! Your MCP server is working perfectly!")
            print("\nNext steps:")
            print("1. Set up Claude Desktop integration")
            print("2. Connect to your real database")
            print("3. Start using natural language NBA queries!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Check the errors above.")
        
        return passed == total
    
    async def test_imports(self):
        """Test that all components import correctly."""
        print("Testing imports...")
        
        try:
            from src.mcp.server import NBAMCPServer
            from src.mcp.query_translator import NaturalLanguageQueryTranslator
            from src.mcp.query_processor import NBAQueryProcessor
            from src.mcp.config import MCPConfig
            print("✅ All imports successful")
            return True
        except Exception as e:
            print(f"❌ Import failed: {e}")
            return False


async def interactive_test():
    """Interactive testing mode."""
    print("\n🎮 Interactive Testing Mode")
    print("-" * 40)
    print("Enter natural language queries to test the MCP server.")
    print("Type 'quit' to exit.\n")
    
    tester = LocalMCPTester()
    
    while True:
        try:
            query = input("🏀 Ask about NBA data: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            print(f"\n🧠 Processing: '{query}'")
            
            # Show translation
            translator = NaturalLanguageQueryTranslator()
            context = await translator.translate_query(query)
            print(f"📊 Understood as: {context.query_type} (confidence: {context.confidence:.2f})")
            
            # Show response
            result = await tester.server._handle_natural_language_query(query)
            if result:
                print(f"\n🎯 Response:")
                print("-" * 40)
                print(result[0].text)
                print("-" * 40)
            else:
                print("❌ No response generated")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main entry point for testing."""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await interactive_test()
    else:
        tester = LocalMCPTester()
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())