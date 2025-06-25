#!/usr/bin/env python3
"""
Example usage of the NBA Play-by-Play API.
Demonstrates how to use the various endpoints with sample queries.
"""

import asyncio
import httpx
import json

# API base URL (adjust if running on different host/port)
BASE_URL = "http://localhost:8000"

async def test_health():
    """Test the health endpoint"""
    print("🏥 Testing health endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print(f"✅ Health check passed: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error: {e}")

async def test_player_search():
    """Test player search functionality"""
    print("\n🔍 Testing player search...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/players/search?query=LeBron")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found {data['total_found']} players")
                for player in data['players'][:3]:  # Show first 3
                    print(f"   - {player['player_name']} (ID: {player['player_id']})")
            else:
                print(f"❌ Player search failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Player search error: {e}")

async def test_team_search():
    """Test team search functionality"""
    print("\n🔍 Testing team search...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/teams/search?query=Lakers")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found {data['total_found']} teams")
                for team in data['teams']:
                    print(f"   - {team['team_name']} ({team['team_abbreviation']}) - ID: {team['team_id']}")
            else:
                print(f"❌ Team search failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Team search error: {e}")

async def test_player_stats_query():
    """Test player statistics query with filters"""
    print("\n📊 Testing player stats query...")
    async with httpx.AsyncClient() as client:
        try:
            # Example query: Get player stats with statistical analysis
            query_data = {
                "season": "latest",
                "limit": 10,
                "about": True,
                "sort": "-points"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/player-stats",
                params=query_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Retrieved {data['total_records']} player stat records")
                if 'statistical_analysis' in data and data['statistical_analysis']:
                    print("📈 Statistical analysis included")
                    stats = data['statistical_analysis'].get('summary_stats', [])
                    for stat in stats[:3]:  # Show first 3 stats
                        print(f"   - {stat['field_name']}: mean={stat.get('mean', 'N/A'):.2f}")
            else:
                print(f"❌ Player stats query failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Player stats query error: {e}")

async def test_team_stats_query():
    """Test team statistics query"""
    print("\n🏀 Testing team stats query...")
    async with httpx.AsyncClient() as client:
        try:
            query_data = {
                "season": "latest", 
                "limit": 5,
                "sort": "-points"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/team-stats",
                params=query_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Retrieved {data['total_records']} team stat records")
                if data['data']:
                    print("🎯 Sample team performance:")
                    for game in data['data'][:3]:  # Show first 3 games
                        team = game.get('team_name', 'Unknown')
                        points = game.get('points', 'N/A')
                        print(f"   - {team}: {points} points")
            else:
                print(f"❌ Team stats query failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Team stats query error: {e}")

async def test_lineup_query():
    """Test lineup statistics query"""
    print("\n👥 Testing lineup stats query...")
    async with httpx.AsyncClient() as client:
        try:
            # This will likely fail without specific player IDs, but shows the structure
            query_data = {
                "player_ids": [2544, 201939],  # Example player IDs
                "season": "latest",
                "limit": 5
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/lineup-stats",
                params={"player_ids": query_data["player_ids"], "season": query_data["season"]}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Retrieved {data['total_records']} lineup records")
            else:
                print(f"ℹ️  Lineup query returned {response.status_code} (expected if no data)")
                # This is expected if there's no data in the database yet
        except Exception as e:
            print(f"ℹ️  Lineup query error (expected): {e}")

async def demonstrate_api():
    """Run all API demonstration tests"""
    print("🏀 NBA Play-by-Play API Demo")
    print("=" * 50)
    
    # Test basic connectivity
    await test_health()
    
    # Test search endpoints
    await test_player_search()
    await test_team_search()
    
    # Test stats queries
    await test_player_stats_query()
    await test_team_stats_query()
    await test_lineup_query()
    
    print("\n" + "=" * 50)
    print("🎯 Demo complete!")
    print("💡 Note: Some queries may fail if the database is not populated with data")
    print("📖 Visit http://localhost:8000/docs for interactive API documentation")

def show_example_queries():
    """Show example API query structures"""
    print("\n📋 Example API Queries:")
    print("-" * 30)
    
    print("\n1. Player Stats Query (POST /api/v1/player-stats):")
    example_player_query = {
        "player_name": "LeBron James",
        "season": "2023-24",
        "filters": '{"points": {"gte": 20}, "assists": {"gte": 5}}',
        "about": True,
        "correlation": ["points", "assists", "rebounds"],
        "sort": "-points",
        "limit": 50
    }
    print(json.dumps(example_player_query, indent=2))
    
    print("\n2. Team Stats Query (POST /api/v1/team-stats):")
    example_team_query = {
        "team_name": "Lakers",
        "season": "2023-24", 
        "home_away": "home",
        "win_loss": "win",
        "about": True,
        "sort": "-points"
    }
    print(json.dumps(example_team_query, indent=2))
    
    print("\n3. Lineup Analysis (POST /api/v1/lineup-stats):")
    example_lineup_query = {
        "player_ids": [2544, 201939, 201142],  # Example: Curry, Green, Thompson
        "team_id": 1610612744,  # Warriors
        "season": "2023-24",
        "compare_mode": "both",
        "min_minutes": 10.0
    }
    print(json.dumps(example_lineup_query, indent=2))

if __name__ == "__main__":
    print("🚀 Starting NBA API examples...")
    
    # Show example query structures
    show_example_queries()
    
    # Run live API tests (requires server to be running)
    print(f"\n🌐 Testing live API at {BASE_URL}")
    print("   (Make sure the API server is running: python src/api/start_api.py)")
    
    try:
        asyncio.run(demonstrate_api())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("💡 Make sure the API server is running on localhost:8000")