"""Test JSON parsing for enhanced database schema implementation."""

import unittest
import sys
from pathlib import Path

# Add tests and src to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from json_parser import JSONGameParser
from core.database import SessionLocal
from sqlalchemy import text


class TestJSONParser(unittest.TestCase):
    """Test cases for JSON game parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = JSONGameParser()
    
    def tearDown(self):
        """Clean up after tests."""
        self.parser.close()
    
    def test_get_sample_game(self):
        """Test getting a sample game from database."""
        game_id, raw_json = self.parser.get_sample_game()
        
        self.assertIsInstance(game_id, str)
        self.assertIsInstance(raw_json, dict)
        self.assertTrue(len(game_id) > 0)
    
    def test_parse_game_basic_info(self):
        """Test parsing basic game information."""
        game_id, raw_json = self.parser.get_sample_game()
        basic_info = self.parser.parse_game_basic_info(raw_json)
        
        self.assertIsInstance(basic_info, dict)
        self.assertIn('game_id', basic_info)
        self.assertIn('game_status', basic_info)
        self.assertIn('game_status_text', basic_info)
    
    def test_parse_teams(self):
        """Test parsing team information."""
        game_id, raw_json = self.parser.get_sample_game()
        home_team, away_team = self.parser.parse_teams(raw_json)
        
        self.assertIsInstance(home_team, dict)
        self.assertIsInstance(away_team, dict)
        
        # Check required fields
        for team in [home_team, away_team]:
            self.assertIn('team_id', team)
            self.assertIn('team_tricode', team)
            self.assertIn('team_name', team)
    
    def test_parse_arena(self):
        """Test parsing arena information."""
        game_id, raw_json = self.parser.get_sample_game()
        arena_info = self.parser.parse_arena(raw_json)
        
        self.assertIsInstance(arena_info, dict)
        self.assertIn('arena_name', arena_info)
        self.assertIn('arena_city', arena_info)
    
    def test_parse_periods(self):
        """Test parsing period scores."""
        game_id, raw_json = self.parser.get_sample_game()
        periods = self.parser.parse_periods(raw_json)
        
        self.assertIsInstance(periods, list)
        if periods:  # If periods exist
            for period in periods:
                self.assertIn('period_number', period)
                self.assertIn('period_type', period)
    
    def test_count_player_stats(self):
        """Test counting player statistics."""
        game_id, raw_json = self.parser.get_sample_game()
        home_players, away_players = self.parser.count_player_stats(raw_json)
        
        self.assertIsInstance(home_players, int)
        self.assertIsInstance(away_players, int)
        self.assertGreaterEqual(home_players, 0)
        self.assertGreaterEqual(away_players, 0)
    
    def test_count_play_events(self):
        """Test counting play-by-play events."""
        game_id, raw_json = self.parser.get_sample_game()
        event_count = self.parser.count_play_events(raw_json)
        
        self.assertIsInstance(event_count, int)
        self.assertGreaterEqual(event_count, 0)
    
    def test_multiple_games_consistency(self):
        """Test parsing consistency across multiple games."""
        session = SessionLocal()
        query = text("SELECT game_id FROM raw_game_data LIMIT 3")
        game_ids = [row[0] for row in session.execute(query).fetchall()]
        session.close()
        
        for game_id in game_ids:
            with self.subTest(game_id=game_id):
                _, raw_json = self.parser.get_sample_game(game_id)
                
                # Test that all parsing methods work without errors
                basic_info = self.parser.parse_game_basic_info(raw_json)
                home_team, away_team = self.parser.parse_teams(raw_json)
                arena_info = self.parser.parse_arena(raw_json)
                periods = self.parser.parse_periods(raw_json)
                home_players, away_players = self.parser.count_player_stats(raw_json)
                event_count = self.parser.count_play_events(raw_json)
                
                # Basic validation
                self.assertIsInstance(basic_info, dict)
                self.assertIsInstance(home_team, dict)
                self.assertIsInstance(away_team, dict)
                self.assertIsInstance(arena_info, dict)
                self.assertIsInstance(periods, list)


if __name__ == '__main__':
    unittest.main()