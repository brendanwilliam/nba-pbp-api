"""
SQLite-specific tests for bulk insert functionality.
These tests handle SQLite limitations around ON CONFLICT.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.database.models import Arena, Team, Person, Game, TeamGame, PersonGame, Play, Boxscore
from src.database.population_services import DataValidationService


class SqliteBulkInsertService:
    """SQLite-compatible bulk insert service for testing"""
    
    def __init__(self, session):
        self.session = session
    
    def bulk_insert_arenas_sqlite(self, arenas):
        """SQLite-compatible arena insertion"""
        if not arenas:
            return 0
        
        valid_arenas = [
            arena for arena in arenas 
            if DataValidationService.validate_arena(arena)
        ]
        
        count = 0
        for arena_data in valid_arenas:
            # Check if exists first
            existing = self.session.query(Arena).filter_by(
                arena_id=arena_data['arena_id']
            ).first()
            
            if not existing:
                arena = Arena(**arena_data)
                self.session.add(arena)
                count += 1
        
        return count
    
    def bulk_insert_teams_sqlite(self, teams):
        """SQLite-compatible team insertion"""
        if not teams:
            return 0
        
        valid_teams = [
            team for team in teams 
            if DataValidationService.validate_team(team)
        ]
        
        count = 0
        for team_data in valid_teams:
            # Check if exists first (using team_id field)
            existing = self.session.query(Team).filter_by(
                team_id=team_data['team_id']
            ).first()
            
            if not existing:
                team = Team(**team_data)
                self.session.add(team)
                count += 1
        
        return count


@pytest.fixture
def sqlite_engine():
    """Create SQLite test engine with proper schema"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create only the tables we need without JSONB
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
def sqlite_session(sqlite_engine):
    """Create SQLite session"""
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


class TestSqliteBulkInsert:
    """Test bulk inserts with SQLite compatibility"""
    
    def test_sqlite_arena_insert(self, sqlite_session):
        """Test SQLite-compatible arena insertion"""
        service = SqliteBulkInsertService(sqlite_session)
        
        arenas = [
            {'arena_id': 1, 'arena_name': 'Arena 1'},
            {'arena_id': 2, 'arena_name': 'Arena 2'}
        ]
        
        count = service.bulk_insert_arenas_sqlite(arenas)
        sqlite_session.commit()
        
        assert count == 2
        
        # Verify in database
        db_arenas = sqlite_session.query(Arena).all()
        assert len(db_arenas) == 2
    
    def test_sqlite_arena_conflict(self, sqlite_session):
        """Test SQLite conflict handling for arenas"""
        service = SqliteBulkInsertService(sqlite_session)
        
        # Insert first batch
        arenas1 = [{'arena_id': 1, 'arena_name': 'Arena 1'}]
        count1 = service.bulk_insert_arenas_sqlite(arenas1)
        sqlite_session.commit()
        
        assert count1 == 1
        
        # Insert overlapping batch
        arenas2 = [
            {'arena_id': 1, 'arena_name': 'Arena 1 Updated'},  # Conflict
            {'arena_id': 2, 'arena_name': 'Arena 2'}  # New
        ]
        count2 = service.bulk_insert_arenas_sqlite(arenas2)
        sqlite_session.commit()
        
        # Should only insert the new one
        assert count2 == 1
        
        # Verify total count
        db_arenas = sqlite_session.query(Arena).all()
        assert len(db_arenas) == 2
        
        # Verify original name wasn't changed
        arena1 = sqlite_session.query(Arena).filter_by(arena_id=1).first()
        assert arena1.arena_name == 'Arena 1'  # Not updated
    
    def test_sqlite_team_insert(self, sqlite_session):
        """Test SQLite-compatible team insertion"""
        service = SqliteBulkInsertService(sqlite_session)
        
        teams = [
            {'team_id': 1, 'team_name': 'Team 1'},
            {'team_id': 2, 'team_name': 'Team 2'}
        ]
        
        count = service.bulk_insert_teams_sqlite(teams)
        sqlite_session.commit()
        
        assert count == 2
        
        # Verify in database
        db_teams = sqlite_session.query(Team).all()
        assert len(db_teams) == 2
    
    def test_sqlite_team_conflict(self, sqlite_session):
        """Test SQLite conflict handling for teams"""
        service = SqliteBulkInsertService(sqlite_session)
        
        # Insert first team
        teams1 = [{'team_id': 1, 'team_name': 'Team 1'}]
        count1 = service.bulk_insert_teams_sqlite(teams1)
        sqlite_session.commit()
        
        assert count1 == 1
        
        # Try to insert same team_id again
        teams2 = [
            {'team_id': 1, 'team_name': 'Team 1 Updated'},  # Conflict
            {'team_id': 2, 'team_name': 'Team 2'}  # New
        ]
        count2 = service.bulk_insert_teams_sqlite(teams2)
        sqlite_session.commit()
        
        # Should only insert the new one
        assert count2 == 1
        
        # Verify total count
        db_teams = sqlite_session.query(Team).all()
        assert len(db_teams) == 2


class TestDataValidationOnly:
    """Test data validation without database operations"""
    
    def test_arena_validation(self):
        """Test arena validation logic"""
        valid_arena = {'arena_id': 123, 'arena_name': 'Test Arena'}
        assert DataValidationService.validate_arena(valid_arena) is True
        
        invalid_arena = {'arena_name': 'Test Arena'}  # Missing arena_id
        assert DataValidationService.validate_arena(invalid_arena) is False
    
    def test_team_validation(self):
        """Test team validation logic"""
        valid_team = {'team_id': 123, 'team_name': 'Test Team'}
        assert DataValidationService.validate_team(valid_team) is True
        
        invalid_team = {'team_name': 'Test Team'}  # Missing team_id
        assert DataValidationService.validate_team(invalid_team) is False
    
    def test_game_validation(self):
        """Test game validation logic"""
        valid_game = {
            'game_id': 123,
            'arena_id': 456,
            'home_team_id': 789,
            'away_team_id': 101112
        }
        assert DataValidationService.validate_game(valid_game) is True
        
        invalid_game = {
            'game_id': 123,
            'arena_id': 456,
            'home_team_id': 789
            # Missing away_team_id
        }
        assert DataValidationService.validate_game(invalid_game) is False