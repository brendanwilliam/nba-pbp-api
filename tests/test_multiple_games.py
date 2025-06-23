"""Test JSON parsing on multiple games to validate schema consistency."""

import unittest
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add tests and src to path  
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.database import SessionLocal
from sqlalchemy import text
from json_parser import JSONGameParser


class TestMultipleGames(unittest.TestCase):
    """Test JSON parsing consistency across multiple games."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = JSONGameParser()
        self.session = SessionLocal()
    
    def tearDown(self):
        """Clean up after tests."""
        self.parser.close()
        self.session.close()
    
    def test_parsing_consistency_five_games(self):
        """Test parsing consistency across 5 games."""
        self._test_multiple_games(5)
    
    def test_parsing_consistency_ten_games(self):
        """Test parsing consistency across 10 games."""
        self._test_multiple_games(10)
    
    def _test_multiple_games(self, limit: int):
        """Test JSON parsing on multiple games."""
        # Get multiple games
        query = text(f"SELECT game_id, LENGTH(raw_json::text) as json_size FROM raw_game_data LIMIT {limit}")
        results = self.session.execute(query).fetchall()
        
        self.assertGreater(len(results), 0, "No games found in database")
        
        successful_parses = 0
        
        for game_id, json_size in results:
            with self.subTest(game_id=game_id):
                try:
                    # Get and parse game data
                    _, raw_json = self.parser.get_sample_game(game_id)
                    game_data = raw_json
                    
                    # Test parsing methods
                    basic_info = self.parser.parse_game_basic_info(game_data)
                    home_team, away_team = self.parser.parse_teams(game_data)
                    arena_info = self.parser.parse_arena(game_data)
                    periods = self.parser.parse_periods(game_data)
                    home_players, away_players = self.parser.count_player_stats(game_data)
                    event_count = self.parser.count_play_events(game_data)
                    
                    # Validate data types
                    self.assertIsInstance(basic_info, dict)
                    self.assertIsInstance(home_team, dict)
                    self.assertIsInstance(away_team, dict)
                    self.assertIsInstance(arena_info, dict)
                    self.assertIsInstance(periods, list)
                    self.assertIsInstance(home_players, int)
                    self.assertIsInstance(away_players, int)
                    self.assertIsInstance(event_count, int)
                    
                    # Validate essential fields exist
                    self.assertIn('game_id', basic_info)
                    self.assertIn('team_id', home_team)
                    self.assertIn('team_id', away_team)
                    
                    # Validate data ranges
                    self.assertGreaterEqual(home_players, 0)
                    self.assertGreaterEqual(away_players, 0)
                    self.assertGreaterEqual(event_count, 0)
                    
                    successful_parses += 1
                    
                except Exception as e:
                    self.fail(f"Failed to parse game {game_id}: {e}")
        
        # Ensure all games parsed successfully
        self.assertEqual(successful_parses, len(results), 
                        f"Only {successful_parses}/{len(results)} games parsed successfully")
    
    def test_data_quality_validation(self):
        """Test data quality across multiple games."""
        query = text("SELECT game_id FROM raw_game_data LIMIT 3")
        game_ids = [row[0] for row in self.session.execute(query).fetchall()]
        
        for game_id in game_ids:
            with self.subTest(game_id=game_id):
                _, raw_json = self.parser.get_sample_game(game_id)
                
                # Test basic info quality
                basic_info = self.parser.parse_game_basic_info(raw_json)
                if basic_info.get('game_id'):
                    self.assertEqual(basic_info['game_id'], game_id)
                
                # Test team data quality
                home_team, away_team = self.parser.parse_teams(raw_json)
                if home_team.get('team_id') and away_team.get('team_id'):
                    self.assertNotEqual(home_team['team_id'], away_team['team_id'],
                                      "Home and away teams should be different")
                
                # Test arena data exists
                arena_info = self.parser.parse_arena(raw_json)
                self.assertIsNotNone(arena_info.get('arena_name'))


def run_interactive_test(limit: int = 5):
    """Run interactive test showing parsing results."""
    parser = JSONGameParser()
    session = SessionLocal()
    
    try:
        print(f"🏀 Testing JSON Parser on {limit} Games")
        print("=" * 60)
        
        # Get multiple games
        query = text(f"SELECT game_id, LENGTH(raw_json::text) as json_size FROM raw_game_data LIMIT {limit}")
        results = session.execute(query).fetchall()
        
        for i, (game_id, json_size) in enumerate(results, 1):
            print(f"\n📊 Game {i}/{limit}: {game_id} ({json_size:,} bytes)")
            
            try:
                # Get and parse game data
                _, raw_json = parser.get_sample_game(game_id)
                game_data = raw_json
                
                # Test parsing methods
                basic_info = parser.parse_game_basic_info(game_data)
                home_team, away_team = parser.parse_teams(game_data)
                arena_info = parser.parse_arena(game_data)
                periods = parser.parse_periods(game_data)
                home_players, away_players = parser.count_player_stats(game_data)
                event_count = parser.count_play_events(game_data)
                
                print(f"   ✅ Basic Info: {basic_info.get('game_status_text', 'N/A')} - {basic_info.get('game_code', 'N/A')}")
                print(f"   ✅ Teams: {home_team.get('team_tricode', 'N/A')} vs {away_team.get('team_tricode', 'N/A')}")
                print(f"   ✅ Arena: {arena_info.get('arena_name', 'N/A')}")
                print(f"   ✅ Periods: {len(periods)} periods found")
                print(f"   ✅ Players: {home_players} home, {away_players} away")
                print(f"   ✅ Events: {event_count} play-by-play events")
                
            except Exception as e:
                print(f"   ❌ Error parsing {game_id}: {e}")
                
        print(f"\n✅ Testing completed on {limit} games!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        parser.close()
        session.close()


if __name__ == "__main__":
    # Run interactive test if called directly
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        run_interactive_test(limit)
    else:
        unittest.main()