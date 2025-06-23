"""Test processing a single game with the enhanced database schema."""

import unittest
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, date

# Add tests and src to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.database import SessionLocal
from sqlalchemy import text
from json_parser import JSONGameParser


class GameProcessor:
    """Process NBA game JSON data into normalized database tables."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.parser = JSONGameParser()
    
    def process_game(self, game_id: str) -> Dict[str, Any]:
        """Process a single game into the database."""
        try:
            # Get raw JSON data
            _, raw_json = self.parser.get_sample_game(game_id)
            
            # Parse the data
            basic_info = self.parser.parse_game_basic_info(raw_json)
            home_team, away_team = self.parser.parse_teams(raw_json)
            arena_info = self.parser.parse_arena(raw_json)
            periods = self.parser.parse_periods(raw_json)
            home_players, away_players = self.parser.count_player_stats(raw_json)
            event_count = self.parser.count_play_events(raw_json)
            
            result = {
                'game_id': game_id,
                'parsing_successful': True,
                'basic_info': basic_info,
                'home_team': home_team,
                'away_team': away_team,
                'arena_info': arena_info,
                'periods_count': len(periods),
                'home_players_count': home_players,
                'away_players_count': away_players,
                'events_count': event_count,
                'database_operations': {}
            }
            
            # Check if we can insert team data
            result['database_operations']['teams'] = self._process_teams(home_team, away_team)
            
            # Check if we can insert game data (would require team IDs)
            result['database_operations']['game'] = self._process_game_info(basic_info, home_team, away_team)
            
            return result
            
        except Exception as e:
            return {
                'game_id': game_id,
                'parsing_successful': False,
                'error': str(e),
                'database_operations': {}
            }
    
    def _process_teams(self, home_team: Dict[str, Any], away_team: Dict[str, Any]) -> Dict[str, Any]:
        """Process team data with current schema."""
        teams_processed = []
        
        for team_info in [home_team, away_team]:
            team_tricode = team_info.get('team_tricode')
            team_name = team_info.get('team_name')
            team_city = team_info.get('team_city')
            
            if team_tricode:
                # Check if team exists (current schema uses tricode)
                existing = self.session.execute(text(
                    "SELECT COUNT(*) FROM teams WHERE tricode = :tricode"
                ), {"tricode": team_tricode}).scalar()
                
                if existing == 0:
                    teams_processed.append({
                        'team_tricode': team_tricode,
                        'team_name': team_name,
                        'team_city': team_city,
                        'action': 'would_insert'
                    })
                else:
                    teams_processed.append({
                        'team_tricode': team_tricode,
                        'action': 'exists'
                    })
        
        return {
            'teams_processed': teams_processed,
            'total_teams': len(teams_processed)
        }
    
    def _process_game_info(self, basic_info: Dict[str, Any], home_team: Dict[str, Any], away_team: Dict[str, Any]) -> Dict[str, Any]:
        """Process game information with current schema."""
        game_id = basic_info.get('game_id')
        
        if not game_id:
            return {'error': 'No game_id found'}
        
        # Check if game exists (current schema uses nba_game_id)
        existing = self.session.execute(text(
            "SELECT COUNT(*) FROM games WHERE nba_game_id = :game_id"
        ), {"game_id": game_id}).scalar()
        
        if existing == 0:
            return {
                'game_id': game_id,
                'game_code': basic_info.get('game_code'),
                'game_status': basic_info.get('game_status'),
                'home_team_tricode': home_team.get('team_tricode'),
                'away_team_tricode': away_team.get('team_tricode'),
                'action': 'would_insert'
            }
        else:
            return {
                'game_id': game_id,
                'action': 'exists'
            }
    
    def check_schema_readiness(self) -> Dict[str, Any]:
        """Check if the database schema is ready for processing."""
        required_tables = [
            'teams', 'games', 'players', 'arenas',
            'game_periods', 'team_game_stats', 'player_game_stats', 'play_events'
        ]
        
        table_status = {}
        
        for table in required_tables:
            try:
                result = self.session.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'"
                )).scalar()
                
                table_status[table] = 'exists' if result > 0 else 'missing'
                
                if result > 0:
                    # Get row count
                    count = self.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    table_status[f"{table}_count"] = count
                    
            except Exception as e:
                table_status[table] = f'error: {str(e)}'
        
        return table_status
    
    def close(self):
        """Clean up resources."""
        self.parser.close()
        self.session.close()


class TestSingleGameProcessing(unittest.TestCase):
    """Test processing a single game with enhanced database schema."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = GameProcessor()
    
    def tearDown(self):
        """Clean up after tests."""
        self.processor.close()
    
    def test_schema_readiness(self):
        """Test if database schema is ready for processing."""
        schema_status = self.processor.check_schema_readiness()
        
        # Print detailed schema status
        print("\n🔍 Database Schema Status:")
        print("=" * 50)
        
        for key, value in schema_status.items():
            if not key.endswith('_count'):
                status_emoji = "✅" if value == "exists" else "❌"
                print(f"{status_emoji} {key}: {value}")
                
                # Show count if available
                count_key = f"{key}_count"
                if count_key in schema_status:
                    print(f"   📊 Rows: {schema_status[count_key]:,}")
        
        # At minimum, we need teams and games tables
        required_core_tables = ['teams', 'games']
        
        for table in required_core_tables:
            self.assertEqual(schema_status.get(table), 'exists', 
                           f"Required table '{table}' does not exist")
    
    def test_process_single_game(self):
        """Test processing a single game."""
        # Get a sample game ID
        session = SessionLocal()
        result = session.execute(text("SELECT game_id FROM raw_game_data LIMIT 1"))
        sample_game = result.fetchone()
        session.close()
        
        if not sample_game:
            self.skipTest("No game data available for testing")
        
        game_id = sample_game[0]
        
        # Process the game
        result = self.processor.process_game(game_id)
        
        # Print detailed processing results
        print(f"\n🏀 Processing Results for Game: {game_id}")
        print("=" * 60)
        
        self.assertTrue(result['parsing_successful'], 
                       f"Failed to parse game {game_id}: {result.get('error', 'Unknown error')}")
        
        # Validate parsed data
        self.assertIsInstance(result['basic_info'], dict)
        self.assertIsInstance(result['home_team'], dict)
        self.assertIsInstance(result['away_team'], dict)
        
        # Print game info
        basic_info = result['basic_info']
        home_team = result['home_team']
        away_team = result['away_team']
        
        print(f"📊 Game: {basic_info.get('game_code', 'N/A')}")
        print(f"🏟️ Status: {basic_info.get('game_status_text', 'N/A')}")
        print(f"👥 Teams: {away_team.get('team_tricode', 'N/A')} @ {home_team.get('team_tricode', 'N/A')}")
        print(f"🏟️ Arena: {result['arena_info'].get('arena_name', 'N/A')}")
        print(f"⏱️ Periods: {result['periods_count']}")
        print(f"👨‍💼 Players: {result['home_players_count']} home, {result['away_players_count']} away")
        print(f"🎬 Events: {result['events_count']:,}")
        
        # Print database operations
        print(f"\n🗄️ Database Operations:")
        db_ops = result['database_operations']
        
        if 'teams' in db_ops:
            teams_info = db_ops['teams']
            print(f"   Teams processed: {teams_info['total_teams']}")
            for team in teams_info['teams_processed']:
                action_emoji = "➕" if team['action'] == 'would_insert' else "✅"
                team_id_text = f"(ID: {team.get('team_id', 'N/A')})" if 'team_id' in team else ""
                print(f"   {action_emoji} {team['team_tricode']} {team_id_text} - {team['action']}")
        
        if 'game' in db_ops:
            game_info = db_ops['game']
            if 'error' not in game_info:
                action_emoji = "➕" if game_info['action'] == 'would_insert' else "✅"
                print(f"   {action_emoji} Game {game_info['game_id']} - {game_info['action']}")
            else:
                print(f"   ❌ Game processing error: {game_info['error']}")
        
        # Validate team tricodes exist
        self.assertIsNotNone(home_team.get('team_tricode'), "Home team should have team_tricode")
        self.assertIsNotNone(away_team.get('team_tricode'), "Away team should have team_tricode")
        
        # Validate game has essential data
        self.assertIsNotNone(basic_info.get('game_id'), "Game should have game_id")
        self.assertIsNotNone(basic_info.get('game_status'), "Game should have game_status")
    
    def test_multiple_games_processing(self):
        """Test processing multiple games for consistency."""
        session = SessionLocal()
        result = session.execute(text("SELECT game_id FROM raw_game_data LIMIT 3"))
        game_ids = [row[0] for row in result.fetchall()]
        session.close()
        
        if len(game_ids) < 3:
            self.skipTest("Not enough game data for testing")
        
        print(f"\n🏀 Processing {len(game_ids)} Games:")
        print("=" * 60)
        
        successful_count = 0
        
        for i, game_id in enumerate(game_ids, 1):
            result = self.processor.process_game(game_id)
            
            if result['parsing_successful']:
                successful_count += 1
                basic_info = result['basic_info']
                home_team = result['home_team']
                away_team = result['away_team']
                
                print(f"{i}. ✅ {game_id}")
                print(f"   {basic_info.get('game_code', 'N/A')} - {basic_info.get('game_status_text', 'N/A')}")
                print(f"   {away_team.get('team_tricode', 'N/A')} @ {home_team.get('team_tricode', 'N/A')}")
                print(f"   Events: {result['events_count']:,}, Players: {result['home_players_count']}+{result['away_players_count']}")
            else:
                print(f"{i}. ❌ {game_id}: {result.get('error', 'Unknown error')}")
        
        print(f"\n📊 Summary: {successful_count}/{len(game_ids)} games processed successfully")
        
        # Expect at least 80% success rate
        success_rate = successful_count / len(game_ids)
        self.assertGreaterEqual(success_rate, 0.8, 
                               f"Success rate {success_rate:.1%} is below 80%")


def run_interactive_test():
    """Run interactive test with detailed output."""
    print("🏀 Single Game Processing Test")
    print("=" * 50)
    
    processor = GameProcessor()
    
    try:
        # Check schema readiness
        print("\n🔍 Checking Database Schema...")
        schema_status = processor.check_schema_readiness()
        
        required_tables = ['teams', 'games', 'players']
        schema_ready = all(schema_status.get(table) == 'exists' for table in required_tables)
        
        if schema_ready:
            print("✅ Database schema is ready for processing")
        else:
            print("❌ Database schema is not ready")
            print("Missing tables:")
            for table in required_tables:
                if schema_status.get(table) != 'exists':
                    print(f"  - {table}")
            return False
        
        # Get a sample game
        session = SessionLocal()
        result = session.execute(text("SELECT game_id FROM raw_game_data LIMIT 1"))
        sample_game = result.fetchone()
        session.close()
        
        if not sample_game:
            print("❌ No game data available for testing")
            return False
        
        game_id = sample_game[0]
        
        # Process the game
        print(f"\n🎯 Processing Game: {game_id}")
        result = processor.process_game(game_id)
        
        if result['parsing_successful']:
            print("✅ Game processed successfully!")
            
            # Show summary
            basic_info = result['basic_info']
            home_team = result['home_team']
            away_team = result['away_team']
            
            print(f"\n📊 Game Summary:")
            print(f"   Game: {basic_info.get('game_code', 'N/A')}")
            print(f"   Teams: {away_team.get('team_tricode', 'N/A')} @ {home_team.get('team_tricode', 'N/A')}")
            print(f"   Status: {basic_info.get('game_status_text', 'N/A')}")
            print(f"   Arena: {result['arena_info'].get('arena_name', 'N/A')}")
            print(f"   Players: {result['home_players_count']} + {result['away_players_count']}")
            print(f"   Events: {result['events_count']:,}")
            
            return True
        else:
            print(f"❌ Failed to process game: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        processor.close()


if __name__ == "__main__":
    # Run interactive test if called directly
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        success = run_interactive_test()
        exit(0 if success else 1)
    else:
        unittest.main()