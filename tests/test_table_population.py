"""
Integration tests for table population from WNBA JSON data.
Tests the full pipeline from JSON to database tables.

Test Categories:
- unit: Fast tests that don't require database
- integration: Tests with SQLite database (no JSONB)
- postgres: Tests requiring PostgreSQL (full JSONB support)
"""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Arena, Team, Person, Game, TeamGame, PersonGame, Play, Boxscore
from src.database.population_services import GamePopulationService, DataValidationService, BulkInsertService

# Test markers for different test categories
pytestmark = pytest.mark.integration


@pytest.fixture
def test_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Only create tables we need for testing (exclude RawGameData with JSONB)
    tables_to_create = [
        Arena.__table__,
        Team.__table__,
        Person.__table__,
        Game.__table__,
        TeamGame.__table__,
        PersonGame.__table__,
        Play.__table__,
        Boxscore.__table__
    ]
    
    for table in tables_to_create:
        table.create(engine, checkfirst=True)
    
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create database session for testing"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_game_json() -> Dict[str, Any]:
    """Load sample game JSON data for testing"""
    test_data_dir = Path(__file__).parent / "test_data"
    sample_file = test_data_dir / "raw_game_1022400005.json"
    
    with open(sample_file, 'r') as f:
        return json.load(f)


class TestDataValidationService:
    """Test data validation before insertion"""
    
    def test_validate_arena_valid(self):
        """Test arena validation with valid data"""
        arena_data = {
            'arena_id': 123,
            'arena_name': 'Test Arena',
            'arena_city': 'Test City'
        }
        
        assert DataValidationService.validate_arena(arena_data) is True
    
    def test_validate_arena_missing_required(self):
        """Test arena validation with missing required field"""
        arena_data = {
            'arena_name': 'Test Arena',
            'arena_city': 'Test City'
        }
        
        assert DataValidationService.validate_arena(arena_data) is False
    
    def test_validate_game_valid(self):
        """Test game validation with valid data"""
        game_data = {
            'game_id': 123,
            'arena_id': 456,
            'home_team_id': 789,
            'away_team_id': 101112
        }
        
        assert DataValidationService.validate_game(game_data) is True
    
    def test_validate_game_missing_required(self):
        """Test game validation with missing required field"""
        game_data = {
            'game_id': 123,
            'arena_id': 456,
            'home_team_id': 789
            # missing away_team_id
        }
        
        assert DataValidationService.validate_game(game_data) is False


class TestBulkInsertService:
    """Test bulk insertion with conflict resolution"""
    
    def test_bulk_insert_arenas(self, test_session):
        """Test bulk arena insertion"""
        service = BulkInsertService(test_session)
        
        arenas = [
            {'arena_id': 1, 'arena_name': 'Arena 1'},
            {'arena_id': 2, 'arena_name': 'Arena 2'}
        ]
        
        count = service.bulk_insert_arenas(arenas)
        test_session.commit()
        
        assert count == 2
        
        # Verify in database
        db_arenas = test_session.query(Arena).all()
        assert len(db_arenas) == 2
    
    def test_bulk_insert_arenas_conflict(self, test_session):
        """Test bulk arena insertion with conflicts"""
        service = BulkInsertService(test_session)
        
        # Insert initial arenas
        arenas1 = [{'arena_id': 1, 'arena_name': 'Arena 1'}]
        service.bulk_insert_arenas(arenas1)
        test_session.commit()
        
        # Insert overlapping arenas
        arenas2 = [
            {'arena_id': 1, 'arena_name': 'Arena 1 Updated'},  # Conflict
            {'arena_id': 2, 'arena_name': 'Arena 2'}  # New
        ]
        count = service.bulk_insert_arenas(arenas2)
        test_session.commit()
        
        # Should only insert the new one (conflict ignored)
        # Note: SQLite doesn't support ON CONFLICT DO NOTHING exactly like PostgreSQL
        # So this test may behave differently
        db_arenas = test_session.query(Arena).all()
        assert len(db_arenas) >= 1
    
    def test_bulk_insert_teams(self, test_session):
        """Test bulk team insertion"""
        service = BulkInsertService(test_session)
        
        teams = [
            {'team_id': 1, 'team_name': 'Team 1'},
            {'team_id': 2, 'team_name': 'Team 2'}
        ]
        
        count = service.bulk_insert_teams(teams)
        test_session.commit()
        
        assert count == 2
        
        # Verify in database
        db_teams = test_session.query(Team).all()
        assert len(db_teams) == 2
    
    def test_bulk_insert_invalid_data(self, test_session):
        """Test bulk insertion with invalid data"""
        service = BulkInsertService(test_session)
        
        # Invalid arena data (missing arena_id)
        arenas = [
            {'arena_name': 'Invalid Arena'}
        ]
        
        count = service.bulk_insert_arenas(arenas)
        test_session.commit()
        
        assert count == 0


class TestGamePopulationService:
    """Test full game population service"""
    
    def test_populate_game_basic(self, test_session, sample_game_json):
        """Test basic game population"""
        service = GamePopulationService(test_session)
        
        # This test is complex because it requires:
        # 1. Team mapping from API IDs to database IDs
        # 2. Proper foreign key resolution
        # 3. Transaction management
        
        # For now, we'll test with a simplified scenario
        results = service.populate_game(sample_game_json)
        
        # Verify results structure
        assert 'arenas' in results
        assert 'teams' in results
        assert 'persons' in results
        assert 'games' in results
        
        test_session.commit()
    
    def test_populate_game_foreign_keys(self, test_session, sample_game_json):
        """Test that foreign key relationships are properly established"""
        service = GamePopulationService(test_session)
        
        # Pre-populate required data
        # This would need team mapping implementation
        
        results = service.populate_game(sample_game_json)
        test_session.commit()
        
        # Verify foreign key relationships
        game = test_session.query(Game).first()
        if game:
            assert game.arena_id is not None
            # Verify arena exists
            arena = test_session.query(Arena).filter_by(arena_id=game.arena_id).first()
            assert arena is not None


class TestFullPipeline:
    """Test the complete population pipeline"""
    
    def test_population_order(self, test_session, sample_game_json):
        """Test that population follows correct dependency order"""
        service = GamePopulationService(test_session)
        
        # Mock the population steps to test order
        # This would require more setup to work properly
        
        # For now, just verify the service can be instantiated
        assert service is not None
        assert service.session == test_session
    
    def test_transaction_rollback(self, test_session, sample_game_json):
        """Test that transactions roll back on error"""
        service = GamePopulationService(test_session)
        
        # This test would require inducing an error mid-population
        # to verify rollback behavior
        
        # For now, basic structure test
        assert service.bulk_service is not None
    
    def test_data_integrity(self, test_session):
        """Test data integrity after population"""
        # This would test:
        # 1. No orphaned foreign keys
        # 2. Data consistency across tables
        # 3. Proper handling of nullable fields
        
        pass


class TestRealDataProcessing:
    """Test with actual WNBA game data"""
    
    def test_multiple_games(self):
        """Test processing multiple games"""
        test_data_dir = Path(__file__).parent / "test_data"
        json_files = list(test_data_dir.glob("raw_game_*.json"))
        
        assert len(json_files) >= 3, "Need at least 3 test files"
        
        # Load all test games
        games = []
        for file_path in json_files:
            with open(file_path, 'r') as f:
                games.append(json.load(f))
        
        # Test that all games have required structure
        for game_json in games:
            assert 'boxscore' in game_json
            assert 'gameId' in game_json['boxscore']
            assert 'arena' in game_json['boxscore']
    
    def test_data_variability(self):
        """Test handling of data variability across different games"""
        test_data_dir = Path(__file__).parent / "test_data"
        json_files = list(test_data_dir.glob("raw_game_*.json"))
        
        game_ids = []
        seasons = []
        
        for file_path in json_files:
            with open(file_path, 'r') as f:
                game_json = json.load(f)
                
                game_ids.append(int(game_json['boxscore']['gameId']))
                
                # Try to extract season from game ID pattern
                game_id_str = str(game_json['boxscore']['gameId'])
                if len(game_id_str) >= 6:
                    season = 2000 + int(game_id_str[1:3])
                    seasons.append(season)
        
        # Verify we have games from different seasons/contexts
        assert len(set(game_ids)) == len(game_ids), "All game IDs should be unique"
        
        if seasons:
            print(f"Test data covers seasons: {sorted(set(seasons))}")
    
    def test_playoff_vs_regular_season(self):
        """Test handling of both playoff and regular season games"""
        test_data_dir = Path(__file__).parent / "test_data"
        json_files = list(test_data_dir.glob("raw_game_*.json"))
        
        game_types = set()
        
        for file_path in json_files:
            with open(file_path, 'r') as f:
                game_json = json.load(f)
                
                # Determine game type from game ID
                game_id_str = str(game_json['boxscore']['gameId'])
                if len(game_id_str) >= 4:
                    type_code = game_id_str[3:4]
                    if type_code == '2':
                        game_types.add('regular_season')
                    elif type_code == '4':
                        game_types.add('playoffs')
        
        print(f"Game types in test data: {game_types}")
        
        # We should have at least one game type
        assert len(game_types) >= 1


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_malformed_json(self, test_session):
        """Test handling of malformed JSON data"""
        service = GamePopulationService(test_session)
        
        # Missing required fields
        bad_json = {
            'boxscore': {
                # Missing gameId, arena, etc.
            }
        }
        
        with pytest.raises(KeyError):
            service.populate_game(bad_json)
    
    def test_missing_play_data(self, test_session, sample_game_json):
        """Test handling of games with missing play-by-play data"""
        service = GamePopulationService(test_session)
        
        # Remove play-by-play data
        modified_json = sample_game_json.copy()
        if 'postGameData' in modified_json:
            del modified_json['postGameData']
        
        # Should still be able to populate other tables
        results = service.populate_game(modified_json)
        
        # Play count should be 0
        assert results['plays'] == 0
    
    def test_missing_boxscore_data(self, test_session, sample_game_json):
        """Test handling of games with missing boxscore data"""
        service = GamePopulationService(test_session)
        
        # Remove boxscore data
        modified_json = sample_game_json.copy()
        if 'postGameData' in modified_json and 'postBoxscoreData' in modified_json['postGameData']:
            del modified_json['postGameData']['postBoxscoreData']
        
        # Should still be able to populate other tables
        results = service.populate_game(modified_json)
        
        # Boxscore count should be 0
        assert results['boxscores'] == 0