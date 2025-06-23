"""Offline test for queue building functionality (no network calls)."""

import unittest
import logging
import sys
from datetime import date
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from scrapers.team_mapping import NBA_TEAMS
from scrapers.game_url_generator import GameURLInfo, GameURLGenerator
from core.database import SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestTeamMapping(unittest.TestCase):
    """Test team mapping functionality."""
    
    def test_current_team_count(self):
        """Test that current season has 30 teams."""
        current_teams = NBA_TEAMS.get_all_teams_for_season("2024-25")
        self.assertEqual(len(current_teams), 30, "Current season should have 30 teams")
    
    def test_historical_teams(self):
        """Test historical team lookups."""
        # Test specific historical lookups
        test_cases = [
            ("BOS", "2024-25", True),   # Current team
            ("LAL", "2024-25", True),   # Current team
            ("SEA", "2007-08", True),   # Seattle before relocation
            ("OKC", "2024-25", True),   # OKC after relocation
            ("VAN", "1997-98", True),   # Vancouver Grizzlies
            ("XYZ", "2024-25", False),  # Invalid team
        ]
        
        for tricode, season, should_exist in test_cases:
            with self.subTest(tricode=tricode, season=season):
                team_info = NBA_TEAMS.get_team_for_season(tricode, season)
                exists = team_info is not None
                
                self.assertEqual(exists, should_exist, 
                               f"Team {tricode} in {season}: expected {should_exist}, got {exists}")
                
                if exists:
                    self.assertIn('name', team_info)
                    self.assertIsInstance(team_info['name'], str)


class TestGameURLInfo(unittest.TestCase):
    """Test GameURLInfo data structure."""
    
    def test_game_url_info_structure(self):
        """Test GameURLInfo structure and conversion."""
        game_info = GameURLInfo(
            game_id="0022400306",
            season="2024-25",
            game_date=date(2024, 12, 1),
            home_team="MEM",
            away_team="IND",
            game_url="https://www.nba.com/game/ind-vs-mem-0022400306",
            game_type="regular",
            priority=100
        )
        
        # Test conversion to dict
        game_dict = game_info.to_dict()
        
        required_fields = ['game_id', 'season', 'game_date', 'home_team', 'away_team', 'game_url', 'game_type', 'priority']
        
        for field in required_fields:
            self.assertIn(field, game_dict, f"Missing field in game dict: {field}")
        
        # Test field values
        self.assertEqual(game_dict['game_id'], "0022400306")
        self.assertEqual(game_dict['season'], "2024-25")
        self.assertEqual(game_dict['home_team'], "MEM")
        self.assertEqual(game_dict['away_team'], "IND")


class TestURLGeneration(unittest.TestCase):
    """Test URL generation algorithm."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = GameURLGenerator()
    
    def test_url_generation(self):
        """Test URL generation for different team combinations."""
        test_cases = [
            ("IND", "MEM", "0022400306", "https://www.nba.com/game/ind-vs-mem-0022400306"),
            ("LAL", "BOS", "0012345678", "https://www.nba.com/game/lal-vs-bos-0012345678"),
        ]
        
        for away, home, game_id, expected_url in test_cases:
            with self.subTest(away=away, home=home, game_id=game_id):
                generated_url = self.generator.generate_game_url(away, home, game_id)
                self.assertEqual(generated_url, expected_url, 
                               f"URL generation failed for {away} @ {home}")


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema exists and is properly structured."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.session = SessionLocal()
    
    def tearDown(self):
        """Clean up after tests."""
        self.session.close()
    
    def test_game_url_queue_table_exists(self):
        """Test that game_url_queue table exists."""
        result = self.session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'game_url_queue'
            );
        """))
        
        exists = result.scalar()
        self.assertTrue(exists, "game_url_queue table should exist")
    
    def test_game_url_queue_schema(self):
        """Test game_url_queue table structure."""
        result = self.session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'game_url_queue'
            ORDER BY ordinal_position;
        """))
        
        columns = result.fetchall()
        required_columns = ['id', 'game_id', 'season', 'game_date', 'home_team', 'away_team', 'game_url']
        
        column_names = [col.column_name for col in columns]
        
        for req_col in required_columns:
            self.assertIn(req_col, column_names, f"Missing required column: {req_col}")
    
    def test_raw_game_data_table_exists(self):
        """Test that raw_game_data table exists."""
        result = self.session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'raw_game_data'
            );
        """))
        
        exists = result.scalar()
        self.assertTrue(exists, "raw_game_data table should exist")


class TestOfflineIntegration(unittest.TestCase):
    """Integration tests that don't require network calls."""
    
    def test_full_offline_workflow(self):
        """Test complete offline workflow."""
        # Test team mapping works
        teams = NBA_TEAMS.get_all_teams_for_season("2024-25")
        self.assertEqual(len(teams), 30)
        
        # Test URL generation works
        generator = GameURLGenerator()
        url = generator.generate_game_url("LAL", "BOS", "0022400001")
        self.assertIn("nba.com/game", url)
        
        # Test GameURLInfo structure works
        game_info = GameURLInfo(
            game_id="0022400001",
            season="2024-25",
            game_date=date(2024, 10, 1),
            home_team="BOS",
            away_team="LAL",
            game_url=url,
            game_type="regular",
            priority=100
        )
        
        game_dict = game_info.to_dict()
        self.assertIn('game_id', game_dict)
        self.assertIn('game_url', game_dict)


def run_interactive_tests():
    """Run interactive tests with detailed output."""
    logger.info("Starting offline tests...")
    
    # Test team mapping
    logger.info("\n=== Team Mapping ===")
    current_teams = NBA_TEAMS.get_all_teams_for_season("2024-25")
    logger.info(f"Current teams (2024-25): {len(current_teams)} teams")
    
    # Test historical lookups
    test_cases = [
        ("BOS", "2024-25", True),
        ("SEA", "2007-08", True),
        ("VAN", "1997-98", True),
    ]
    
    for tricode, season, should_exist in test_cases:
        team_info = NBA_TEAMS.get_team_for_season(tricode, season)
        exists = team_info is not None
        if exists:
            logger.info(f"✓ {tricode} in {season}: {team_info['name']}")
        else:
            logger.info(f"✓ {tricode} in {season}: Not found")
    
    # Test URL generation
    logger.info("\n=== URL Generation ===")
    generator = GameURLGenerator()
    test_urls = [
        ("IND", "MEM", "0022400306"),
        ("LAL", "BOS", "0012345678"),
    ]
    
    for away, home, game_id in test_urls:
        url = generator.generate_game_url(away, home, game_id)
        logger.info(f"✓ {away} @ {home} -> {url}")


if __name__ == "__main__":
    # Run interactive tests if called directly
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        run_interactive_tests()
    else:
        unittest.main()