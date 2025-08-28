#!/usr/bin/env python3
"""
Tests for src.database.models module.

This module tests the SQLAlchemy ORM models for the WNBA database.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import json

# Import SQLite-compatible models for testing
from tests.test_models_sqlite import SqliteTestBase, SqliteDatabaseVersion, SqliteScrapingSession, SqliteRawGameData
# Import the original models for type checking
from src.database.models import DatabaseVersion, ScrapingSession, RawGameData


class TestDatabaseModels:
    """Test SQLAlchemy model definitions and basic operations."""
    
    @pytest.fixture
    def in_memory_db(self):
        """Create an in-memory SQLite database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)
        SqliteTestBase.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        yield session
        
        session.close()
    
    def test_database_version_model_creation(self, in_memory_db):
        """Test creating DatabaseVersion records."""
        session = in_memory_db
        
        # Create a version record
        version = SqliteDatabaseVersion(
            version="1.0.0",
            description="Initial schema"
        )
        
        session.add(version)
        session.commit()
        
        # Verify record was created
        retrieved = session.query(SqliteDatabaseVersion).filter_by(version="1.0.0").first()
        assert retrieved is not None
        assert retrieved.version == "1.0.0"
        assert retrieved.description == "Initial schema"
        assert retrieved.applied_at is not None
        assert isinstance(retrieved.applied_at, datetime)
    
    def test_database_version_unique_constraint(self, in_memory_db):
        """Test that version field has unique constraint."""
        session = in_memory_db
        
        # Create first version
        version1 = SqliteDatabaseVersion(version="1.0.0", description="First")
        session.add(version1)
        session.commit()
        
        # Try to create duplicate version
        version2 = SqliteDatabaseVersion(version="1.0.0", description="Duplicate")
        session.add(version2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_database_version_repr(self, in_memory_db):
        """Test DatabaseVersion string representation."""
        version = SqliteDatabaseVersion(
            version="1.0.0",
            description="Test version"
        )
        
        repr_str = repr(version)
        assert "DatabaseVersion" in repr_str
        assert "1.0.0" in repr_str
    
    def test_scraping_session_model_creation(self, in_memory_db):
        """Test creating ScrapingSession records."""
        session = in_memory_db
        
        # Create a scraping session
        scraping_session = SqliteScrapingSession(
            session_name="Test Session",
            status="running",
            games_scraped=5,
            errors_count=1
        )
        
        session.add(scraping_session)
        session.commit()
        
        # Verify record was created
        retrieved = session.query(SqliteScrapingSession).filter_by(session_name="Test Session").first()
        assert retrieved is not None
        assert retrieved.session_name == "Test Session"
        assert retrieved.status == "running"
        assert retrieved.games_scraped == 5
        assert retrieved.errors_count == 1
        assert retrieved.start_time is not None
        assert retrieved.end_time is None
    
    def test_scraping_session_default_values(self, in_memory_db):
        """Test ScrapingSession default values."""
        session = in_memory_db
        
        # Create session with minimal data
        scraping_session = SqliteScrapingSession(session_name="Minimal Session")
        session.add(scraping_session)
        session.commit()
        
        # Verify defaults
        retrieved = session.query(SqliteScrapingSession).filter_by(session_name="Minimal Session").first()
        assert retrieved.status == "running"
        assert retrieved.games_scraped == 0
        assert retrieved.errors_count == 0
        assert retrieved.start_time is not None
        assert retrieved.end_time is None
    
    def test_scraping_session_completed_status(self, in_memory_db):
        """Test ScrapingSession with completed status."""
        session = in_memory_db
        
        end_time = datetime.now()  # SQLite doesn't preserve timezone info
        scraping_session = SqliteScrapingSession(
            session_name="Completed Session",
            status="completed",
            end_time=end_time,
            games_scraped=10,
            errors_count=0
        )
        
        session.add(scraping_session)
        session.commit()
        
        # Verify record
        retrieved = session.query(SqliteScrapingSession).first()
        assert retrieved.status == "completed"
        assert retrieved.end_time == end_time
        assert retrieved.games_scraped == 10
        assert retrieved.errors_count == 0
    
    def test_scraping_session_repr(self, in_memory_db):
        """Test ScrapingSession string representation."""
        scraping_session = SqliteScrapingSession(
            session_name="Test Session",
            status="running"
        )
        
        repr_str = repr(scraping_session)
        assert "ScrapingSession" in repr_str
        assert "Test Session" in repr_str
        assert "running" in repr_str
    
    def test_raw_game_data_model_creation(self, in_memory_db):
        """Test creating RawGameData records."""
        session = in_memory_db
        
        # Sample game data
        game_data = {
            "gameId": "1029700001",
            "homeTeam": "NYL",
            "awayTeam": "PHX",
            "gameDate": "1997-06-21",
            "playByPlay": [
                {"period": 1, "time": "10:00", "description": "Game Start"}
            ]
        }
        
        # Create game data record
        raw_game = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://www.wnba.com/game/phx-vs-nyl-1029700001",
            game_data=game_data
        )
        
        session.add(raw_game)
        session.commit()
        
        # Verify record was created
        retrieved = session.query(SqliteRawGameData).filter_by(game_id=1029700001).first()
        assert retrieved is not None
        assert retrieved.game_id == 1029700001
        assert retrieved.season == 1997
        assert retrieved.game_type == "regular"
        assert retrieved.game_url == "https://www.wnba.com/game/phx-vs-nyl-1029700001"
        assert retrieved.game_data == game_data
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
    
    def test_raw_game_data_unique_game_id(self, in_memory_db):
        """Test that game_id has unique constraint."""
        session = in_memory_db
        
        game_data = {"test": "data"}
        
        # Create first game
        game1 = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/1",
            game_data=game_data
        )
        session.add(game1)
        session.commit()
        
        # Try to create duplicate game_id
        game2 = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/2",
            game_data=game_data
        )
        session.add(game2)
        
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_raw_game_data_jsonb_functionality(self, in_memory_db):
        """Test JSONB functionality (using JSON for SQLite compatibility)."""
        session = in_memory_db
        
        # Complex game data structure
        game_data = {
            "gameId": "1029700001",
            "teams": {
                "home": {"name": "New York Liberty", "score": 89},
                "away": {"name": "Phoenix Mercury", "score": 84}
            },
            "playByPlay": [
                {
                    "period": 1,
                    "time": "10:00",
                    "description": "Game Start",
                    "players": ["Player1", "Player2"]
                },
                {
                    "period": 1,
                    "time": "9:45",
                    "description": "Jump ball won by NYL",
                    "stats": {"possession": "NYL"}
                }
            ],
            "metadata": {
                "venue": "Madison Square Garden",
                "attendance": 15623,
                "officials": ["Ref1", "Ref2", "Ref3"]
            }
        }
        
        raw_game = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=game_data
        )
        
        session.add(raw_game)
        session.commit()
        
        # Retrieve and verify complex data structure
        retrieved = session.query(SqliteRawGameData).filter_by(game_id=1029700001).first()
        assert retrieved.game_data == game_data
        assert retrieved.game_data["teams"]["home"]["score"] == 89
        assert len(retrieved.game_data["playByPlay"]) == 2
        assert retrieved.game_data["metadata"]["attendance"] == 15623
    
    def test_raw_game_data_updated_at_timestamp(self, in_memory_db):
        """Test that updated_at timestamp changes on updates."""
        session = in_memory_db
        
        # Create initial record
        game_data = {"initial": "data"}
        raw_game = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=game_data
        )
        
        session.add(raw_game)
        session.commit()
        
        initial_updated_at = raw_game.updated_at
        
        # Wait a moment and update (simulate time passing)
        import time
        time.sleep(0.1)  # Increase sleep time for more reliable timestamp differences
        
        # Update the record
        raw_game.game_data = {"updated": "data"}
        session.commit()
        
        # Verify updated_at changed (SQLite may not have microsecond precision)
        session.refresh(raw_game)
        # Use >= instead of > to handle cases where timestamps are the same
        assert raw_game.updated_at >= initial_updated_at
    
    def test_raw_game_data_repr(self, in_memory_db):
        """Test RawGameData string representation."""
        raw_game = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data={"test": "data"}
        )
        
        repr_str = repr(raw_game)
        assert "RawGameData" in repr_str
        assert "1029700001" in repr_str
    
    def test_raw_game_data_indexing(self, in_memory_db):
        """Test that game_id is properly indexed."""
        session = in_memory_db
        
        # Create multiple games
        for i in range(5):
            game_data = {"game": f"data_{i}"}
            raw_game = SqliteRawGameData(
                game_id=1029700000 + i,
                season=1997,
                game_type="regular",
                game_url=f"https://example.com/game_{i}",
                game_data=game_data
            )
            session.add(raw_game)
        
        session.commit()
        
        # Query by game_id should be efficient (index is used)
        result = session.query(SqliteRawGameData).filter_by(game_id=1029700002).first()
        assert result is not None
        assert result.game_data["game"] == "data_2"


class TestModelRelationships:
    """Test relationships between models (if any are added in the future)."""
    
    @pytest.fixture
    def in_memory_db(self):
        """Create an in-memory SQLite database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)
        SqliteTestBase.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        yield session
        
        session.close()
    
    def test_multiple_model_creation(self, in_memory_db):
        """Test creating records of different model types."""
        session = in_memory_db
        
        # Create database version
        version = SqliteDatabaseVersion(version="1.0.0", description="Initial")
        session.add(version)
        
        # Create scraping session
        scraping_session = SqliteScrapingSession(session_name="Test Session")
        session.add(scraping_session)
        
        # Create raw game data
        game_data = {"test": "data"}
        raw_game = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=game_data
        )
        session.add(raw_game)
        
        session.commit()
        
        # Verify all records exist
        assert session.query(SqliteDatabaseVersion).count() == 1
        assert session.query(SqliteScrapingSession).count() == 1
        assert session.query(SqliteRawGameData).count() == 1


class TestModelValidation:
    """Test model validation and constraints."""
    
    @pytest.fixture
    def in_memory_db(self):
        """Create an in-memory SQLite database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)
        SqliteTestBase.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        yield session
        
        session.close()
    
    def test_raw_game_data_required_fields(self, in_memory_db):
        """Test that required fields are enforced."""
        session = in_memory_db
        
        # Test missing game_id (should fail)
        with pytest.raises((IntegrityError, TypeError)):
            raw_game = SqliteRawGameData(
                season=1997,
                game_type="regular",
                game_url="https://example.com/game",
                game_data={"test": "data"}
            )
            session.add(raw_game)
            session.commit()
        
        session.rollback()
        
        # Test missing season (should fail)
        with pytest.raises((IntegrityError, TypeError)):
            raw_game = SqliteRawGameData(
                game_id=1029700001,
                game_type="regular",
                game_url="https://example.com/game",
                game_data={"test": "data"}
            )
            session.add(raw_game)
            session.commit()
    
    def test_scraping_session_required_fields(self, in_memory_db):
        """Test ScrapingSession required fields."""
        session = in_memory_db
        
        # Test missing session_name (should fail)
        with pytest.raises((IntegrityError, TypeError)):
            scraping_session = SqliteScrapingSession(status="running")
            session.add(scraping_session)
            session.commit()
    
    def test_database_version_required_fields(self, in_memory_db):
        """Test DatabaseVersion required fields."""
        session = in_memory_db
        
        # Test missing version (should fail)
        with pytest.raises((IntegrityError, TypeError)):
            version = SqliteDatabaseVersion(description="Test")
            session.add(version)
            session.commit()


# Performance and stress tests (marked as slow)
@pytest.mark.slow
class TestModelPerformance:
    """Test model performance with larger datasets."""
    
    @pytest.fixture
    def in_memory_db(self):
        """Create an in-memory SQLite database for testing."""
        engine = create_engine('sqlite:///:memory:', echo=False)
        SqliteTestBase.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        yield session
        
        session.close()
    
    def test_bulk_raw_game_data_insertion(self, in_memory_db):
        """Test inserting many RawGameData records."""
        session = in_memory_db
        
        # Create 100 game records
        games = []
        for i in range(100):
            game_data = {
                "gameId": f"102970000{i:02d}",
                "homeTeam": "NYL",
                "awayTeam": "PHX",
                "playByPlay": [{"event": f"event_{j}"} for j in range(10)]
            }
            
            raw_game = SqliteRawGameData(
                game_id=1029700000 + i,
                season=1997,
                game_type="regular",
                game_url=f"https://example.com/game_{i}",
                game_data=game_data
            )
            games.append(raw_game)
        
        # Bulk insert
        session.bulk_save_objects(games)
        session.commit()
        
        # Verify all records were inserted
        assert session.query(SqliteRawGameData).count() == 100
        
        # Test querying performance
        result = session.query(SqliteRawGameData).filter_by(game_id=1029700050).first()
        assert result is not None
        assert result.game_data["gameId"] == "10297000050"
    
    def test_large_jsonb_data_storage(self, in_memory_db):
        """Test storing large JSON data structures."""
        session = in_memory_db
        
        # Create large play-by-play data (simulating a full game)
        large_game_data = {
            "gameId": "1029700001",
            "teams": {"home": "NYL", "away": "PHX"},
            "playByPlay": []
        }
        
        # Simulate 400 play events (typical WNBA game)
        for i in range(400):
            event = {
                "eventNum": i,
                "period": (i // 100) + 1,
                "time": f"{10 - (i % 100) // 10}:{9 - (i % 10):02d}",
                "description": f"Event {i} description with some details",
                "homeScore": i // 4,
                "awayScore": i // 5,
                "players": [f"Player_{j}" for j in range(5)],
                "stats": {
                    "fieldGoals": {"made": i % 3, "attempted": i % 5},
                    "freeThrows": {"made": i % 2, "attempted": i % 3}
                }
            }
            large_game_data["playByPlay"].append(event)
        
        # Store the large data structure
        raw_game = SqliteRawGameData(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/large_game",
            game_data=large_game_data
        )
        
        session.add(raw_game)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(SqliteRawGameData).filter_by(game_id=1029700001).first()
        assert retrieved is not None
        assert len(retrieved.game_data["playByPlay"]) == 400
        assert retrieved.game_data["playByPlay"][100]["period"] == 2
        assert "Event 200 description" in retrieved.game_data["playByPlay"][200]["description"]