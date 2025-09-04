#!/usr/bin/env python3
"""
Tests for src.database.services module.

This module tests the database service layer including DatabaseService,
GameDataService, and ScrapingSessionService classes.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Import the services under test
from src.database.services import (
    DatabaseConnection,
    GameDataService,
    ScrapingSessionService,
    DatabaseService,
    insert_scraped_game,
    get_games_for_analysis,
    delete_single_game,
    delete_season_games,
    delete_games_by_pattern,
    update_single_game,
    upsert_single_game,
    refresh_game_data,
    update_multiple_games,
    with_database
)
from src.database.models import Base, RawGameData, ScrapingSession, DatabaseVersion


class TestDatabaseConnection:
    """Test DatabaseConnection class."""
    
    @patch.dict(os.environ, {
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_wnba'
    })
    @patch('src.database.services.create_engine')
    @patch('src.database.services.sessionmaker')
    def test_database_connection_initialization(self, mock_sessionmaker, mock_create_engine):
        """Test DatabaseConnection initialization."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_session_local = Mock()
        mock_sessionmaker.return_value = mock_session_local
        
        db_conn = DatabaseConnection()
        
        expected_url = "postgresql://test_user:test_pass@localhost:5432/test_wnba"
        mock_create_engine.assert_called_once_with(expected_url)
        mock_sessionmaker.assert_called_once_with(bind=mock_engine)
        assert db_conn.engine == mock_engine
        assert db_conn.SessionLocal == mock_session_local
    
    @patch.dict(os.environ, {
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_wnba'
    })
    @patch('src.database.services.create_engine')
    @patch('src.database.services.sessionmaker')
    def test_get_session(self, mock_sessionmaker, mock_create_engine):
        """Test getting a new database session."""
        mock_session_instance = Mock()
        mock_session_local = Mock()
        mock_session_local.return_value = mock_session_instance
        mock_sessionmaker.return_value = mock_session_local
        
        db_conn = DatabaseConnection()
        session = db_conn.get_session()
        
        assert session == mock_session_instance
        mock_session_local.assert_called_once()
    
    @patch.dict(os.environ, {
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_wnba'
    })
    @patch('src.database.services.create_engine')
    @patch('src.database.services.sessionmaker')
    def test_get_engine(self, mock_sessionmaker, mock_create_engine):
        """Test getting the database engine."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        db_conn = DatabaseConnection()
        engine = db_conn.get_engine()
        
        assert engine == mock_engine


class TestGameDataService:
    """Test GameDataService class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock()
        return session
    
    @pytest.fixture
    def game_data_service(self, mock_session):
        """Create GameDataService with mock session."""
        return GameDataService(mock_session)
    
    @pytest.fixture
    def sample_game_data(self):
        """Sample game data for testing."""
        return {
            "gameId": "1029700001",
            "homeTeam": "NYL",
            "awayTeam": "PHX",
            "gameDate": "1997-06-21",
            "playByPlay": [
                {"period": 1, "time": "10:00", "description": "Game Start"}
            ]
        }
    
    def test_insert_game_data_success(self, game_data_service, mock_session, sample_game_data):
        """Test successful game data insertion."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Execute
        result = game_data_service.insert_game_data(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=sample_game_data
        )
        
        # Assert
        assert result is not None
        assert isinstance(result, RawGameData)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_insert_game_data_duplicate_game_id(self, game_data_service, mock_session, sample_game_data):
        """Test inserting game with duplicate game_id."""
        # Setup mocks - game already exists
        existing_game = Mock(spec=RawGameData)
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_game
        
        # Execute
        result = game_data_service.insert_game_data(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=sample_game_data
        )
        
        # Assert - should return existing game, not add new one
        assert result == existing_game
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
    
    def test_insert_game_data_database_error(self, game_data_service, mock_session, sample_game_data):
        """Test handling of database errors during insertion."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        # Execute
        result = game_data_service.insert_game_data(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=sample_game_data
        )
        
        # Assert
        assert result is None
        mock_session.rollback.assert_called_once()
    
    def test_update_game_data_success(self, game_data_service, mock_session, sample_game_data):
        """Test successful game data update."""
        # Setup mocks
        existing_game = Mock(spec=RawGameData)
        existing_game.game_url = "old_url"
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_game
        
        # Execute
        result = game_data_service.update_game_data(
            game_id=1029700001,
            game_data=sample_game_data,
            game_url="new_url"
        )
        
        # Assert
        assert result == existing_game
        assert existing_game.game_data == sample_game_data
        assert existing_game.game_url == "new_url"
        mock_session.commit.assert_called_once()
    
    def test_update_game_data_game_not_found(self, game_data_service, mock_session, sample_game_data):
        """Test updating non-existent game."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Execute
        result = game_data_service.update_game_data(
            game_id=1029700001,
            game_data=sample_game_data
        )
        
        # Assert
        assert result is None
        mock_session.commit.assert_not_called()
    
    def test_upsert_game_data_update_existing(self, game_data_service, mock_session, sample_game_data):
        """Test upsert when game exists (update path)."""
        # Setup mocks
        existing_game = Mock(spec=RawGameData)
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_game
        
        # Execute
        result = game_data_service.upsert_game_data(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=sample_game_data
        )
        
        # Assert - should update existing
        assert result == existing_game
        assert existing_game.game_data == sample_game_data
        assert existing_game.game_url == "https://example.com/game"
        mock_session.commit.assert_called_once()
        mock_session.add.assert_not_called()
    
    def test_upsert_game_data_insert_new(self, game_data_service, mock_session, sample_game_data):
        """Test upsert when game doesn't exist (insert path)."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Execute
        result = game_data_service.upsert_game_data(
            game_id=1029700001,
            season=1997,
            game_type="regular",
            game_url="https://example.com/game",
            game_data=sample_game_data
        )
        
        # Assert - should create new
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_get_game_data_success(self, game_data_service, mock_session):
        """Test successful game data retrieval."""
        # Setup mocks
        expected_game = Mock(spec=RawGameData)
        mock_session.query.return_value.filter_by.return_value.first.return_value = expected_game
        
        # Execute
        result = game_data_service.get_game_data(1029700001)
        
        # Assert
        assert result == expected_game
        mock_session.query.assert_called_with(RawGameData)
    
    def test_get_games_by_season_regular(self, game_data_service, mock_session):
        """Test getting games by season (regular season)."""
        # Setup mocks
        expected_games = [Mock(spec=RawGameData), Mock(spec=RawGameData)]
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.filter_by.return_value.all.return_value = expected_games
        
        # Execute
        result = game_data_service.get_games_by_season(1997, "regular")
        
        # Assert
        assert result == expected_games
        mock_session.query.assert_called_with(RawGameData)
    
    def test_get_games_by_season_no_game_type(self, game_data_service, mock_session):
        """Test getting games by season without game type filter."""
        # Setup mocks
        expected_games = [Mock(spec=RawGameData)]
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.all.return_value = expected_games
        
        # Execute
        result = game_data_service.get_games_by_season(1997)
        
        # Assert
        assert result == expected_games
    
    def test_game_exists_true(self, game_data_service, mock_session):
        """Test game_exists when game exists."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = Mock()
        
        # Execute
        result = game_data_service.game_exists(1029700001)
        
        # Assert
        assert result is True
    
    def test_game_exists_false(self, game_data_service, mock_session):
        """Test game_exists when game doesn't exist."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Execute
        result = game_data_service.game_exists(1029700001)
        
        # Assert
        assert result is False
    
    def test_delete_game_data_success(self, game_data_service, mock_session):
        """Test successful game deletion."""
        # Setup mocks
        existing_game = Mock(spec=RawGameData)
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_game
        
        # Execute
        result = game_data_service.delete_game_data(1029700001)
        
        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(existing_game)
        mock_session.commit.assert_called_once()
    
    def test_delete_game_data_not_found(self, game_data_service, mock_session):
        """Test deleting non-existent game."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Execute
        result = game_data_service.delete_game_data(1029700001)
        
        # Assert
        assert result is False
        mock_session.delete.assert_not_called()
    
    def test_delete_games_by_season_dry_run(self, game_data_service, mock_session):
        """Test deleting games by season (dry run)."""
        # Setup mocks - need to mock the full query chain
        mock_games = [Mock(spec=RawGameData), Mock(spec=RawGameData)]
        mock_query_base = mock_session.query.return_value
        mock_query_season = mock_query_base.filter_by.return_value
        mock_query_final = mock_query_season.filter_by.return_value
        mock_query_final.all.return_value = mock_games
        
        # Set up the query chain for when game_type is provided
        mock_query_season.filter_by.return_value = mock_query_final
        
        # Execute
        result = game_data_service.delete_games_by_season(1997, "regular", dry_run=True)
        
        # Assert
        assert result == {'would_delete': 2, 'deleted': 0}
        mock_query_final.delete.assert_not_called()
    
    def test_delete_games_by_season_actual_deletion(self, game_data_service, mock_session):
        """Test actual deletion of games by season."""
        # Setup mocks - same pattern as dry run test
        mock_games = [Mock(spec=RawGameData), Mock(spec=RawGameData)]
        mock_query_base = mock_session.query.return_value
        mock_query_season = mock_query_base.filter_by.return_value
        mock_query_final = mock_query_season.filter_by.return_value
        mock_query_final.all.return_value = mock_games
        mock_query_final.delete.return_value = 2
        
        # Set up the query chain for when game_type is provided
        mock_query_season.filter_by.return_value = mock_query_final
        
        # Execute
        result = game_data_service.delete_games_by_season(1997, "regular", dry_run=False)
        
        # Assert
        assert result == {'would_delete': 2, 'deleted': 2}
        mock_query_final.delete.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_update_multiple_games_success(self, game_data_service, mock_session, sample_game_data):
        """Test updating multiple games successfully."""
        # Setup mocks
        existing_game1 = Mock(spec=RawGameData)
        existing_game2 = Mock(spec=RawGameData)
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            existing_game1, existing_game2
        ]
        
        updates = [
            {'game_id': 1029700001, 'game_data': sample_game_data},
            {'game_id': 1029700002, 'game_data': sample_game_data}
        ]
        
        # Execute
        result = game_data_service.update_multiple_games(updates)
        
        # Assert
        assert result['total'] == 2
        assert result['updated'] == 2
        assert result['not_found'] == 0
        assert result['failed'] == 0
    
    def test_refresh_game_from_url_success(self, game_data_service, mock_session, sample_game_data):
        """Test successful game data refresh from URL."""
        # Setup mocks
        existing_game = Mock(spec=RawGameData)
        existing_game.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)  # Old enough to refresh
        existing_game.game_url = "https://example.com/game"
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_game
        
        # The method tries to import RawDataExtractor dynamically
        # We'll test both success and ImportError scenarios
        
        # First test: successful import and extraction
        with patch('builtins.__import__') as mock_import:
            # Mock the RawDataExtractor import
            mock_extractor_module = Mock()
            mock_extractor_class = Mock()
            mock_extractor_module.RawDataExtractor = mock_extractor_class
            mock_extractor_module.ExtractionResult = Mock()
            mock_extractor_module.ExtractionResult.SUCCESS = 'SUCCESS'
            
            # Set up import to return our mocked module
            def side_effect(name, *args, **kwargs):
                if 'raw_data_extractor' in name:
                    return mock_extractor_module
                else:
                    # Let other imports work normally
                    return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = side_effect
            
            # Mock the extractor instance
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.extract_game_data.return_value = ('SUCCESS', sample_game_data, {})
            
            # Execute
            result = game_data_service.refresh_game_from_url(1029700001, force_refresh=True)
            
            # Assert
            assert result == existing_game
            assert existing_game.game_data == sample_game_data
            mock_session.commit.assert_called_once()
    
    def test_refresh_game_from_url_import_error(self, game_data_service, mock_session):
        """Test refresh_game_from_url when RawDataExtractor import fails."""
        # Setup mocks
        existing_game = Mock(spec=RawGameData)
        existing_game.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        existing_game.game_url = "https://example.com/game"
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_game
        
        # Mock the import to raise ImportError
        with patch('builtins.__import__') as mock_import:
            mock_import.side_effect = ImportError("No module named 'scrapers.raw_data_extractor'")
            
            # Execute
            result = game_data_service.refresh_game_from_url(1029700001, force_refresh=True)
            
            # Assert - should return None due to ImportError
            assert result is None
            mock_session.commit.assert_not_called()


class TestScrapingSessionService:
    """Test ScrapingSessionService class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def scraping_session_service(self, mock_session):
        """Create ScrapingSessionService with mock session."""
        return ScrapingSessionService(mock_session)
    
    def test_start_session_success(self, scraping_session_service, mock_session):
        """Test successful scraping session start."""
        # Execute
        result = scraping_session_service.start_session("Test Session")
        
        # Assert
        assert result is not None
        assert isinstance(result, ScrapingSession)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_start_session_database_error(self, scraping_session_service, mock_session):
        """Test handling database error during session start."""
        # Setup mocks
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        # Execute
        result = scraping_session_service.start_session("Test Session")
        
        # Assert
        assert result is None
        mock_session.rollback.assert_called_once()
    
    def test_update_session_success(self, scraping_session_service, mock_session):
        """Test successful session update."""
        # Setup mocks
        existing_session = Mock(spec=ScrapingSession)
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_session
        
        # Execute
        result = scraping_session_service.update_session(
            session_id=1,
            games_scraped=10,
            errors_count=2,
            status="completed"
        )
        
        # Assert
        assert result == existing_session
        assert existing_session.games_scraped == 10
        assert existing_session.errors_count == 2
        assert existing_session.status == "completed"
        assert existing_session.end_time is not None
        mock_session.commit.assert_called_once()
    
    def test_update_session_not_found(self, scraping_session_service, mock_session):
        """Test updating non-existent session."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Execute
        result = scraping_session_service.update_session(session_id=1, games_scraped=10)
        
        # Assert
        assert result is None
        mock_session.commit.assert_not_called()
    
    def test_get_active_sessions(self, scraping_session_service, mock_session):
        """Test getting active sessions."""
        # Setup mocks
        expected_sessions = [Mock(spec=ScrapingSession), Mock(spec=ScrapingSession)]
        mock_session.query.return_value.filter_by.return_value.all.return_value = expected_sessions
        
        # Execute
        result = scraping_session_service.get_active_sessions()
        
        # Assert
        assert result == expected_sessions
        mock_session.query.assert_called_with(ScrapingSession)


class TestDatabaseService:
    """Test DatabaseService context manager."""
    
    @patch('src.database.services.DatabaseConnection')
    def test_database_service_context_manager_success(self, mock_db_connection_class):
        """Test successful context manager usage."""
        # Setup mocks
        mock_connection = Mock()
        mock_session = Mock()
        mock_db_connection_class.return_value = mock_connection
        mock_connection.get_session.return_value = mock_session
        
        # Execute
        with DatabaseService() as db:
            assert db.game_data is not None
            assert db.scraping_session is not None
            assert isinstance(db.game_data, GameDataService)
            assert isinstance(db.scraping_session, ScrapingSessionService)
        
        # Assert cleanup
        mock_session.close.assert_called_once()
    
    @patch('src.database.services.DatabaseConnection')
    def test_database_service_context_manager_exception(self, mock_db_connection_class):
        """Test context manager with exception handling."""
        # Setup mocks
        mock_connection = Mock()
        mock_session = Mock()
        mock_db_connection_class.return_value = mock_connection
        mock_connection.get_session.return_value = mock_session
        
        # Execute with exception
        with pytest.raises(ValueError):
            with DatabaseService() as db:
                raise ValueError("Test exception")
        
        # Assert rollback and cleanup
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
    
    @patch('src.database.services.DatabaseConnection')
    def test_get_session(self, mock_db_connection_class):
        """Test getting the current session."""
        # Setup mocks
        mock_connection = Mock()
        mock_session = Mock()
        mock_db_connection_class.return_value = mock_connection
        mock_connection.get_session.return_value = mock_session
        
        # Execute
        with DatabaseService() as db:
            session = db.get_session()
            assert session == mock_session


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('src.database.services.DatabaseService')
    def test_insert_scraped_game_success(self, mock_db_service_class):
        """Test insert_scraped_game convenience function."""
        # Setup mocks
        mock_db_service = Mock()
        mock_db_service_class.return_value.__enter__.return_value = mock_db_service
        mock_db_service.game_data.insert_game_data.return_value = Mock(spec=RawGameData)
        
        # Execute
        result = insert_scraped_game(1029700001, 1997, "regular", "https://example.com", {})
        
        # Assert
        assert result is True
        mock_db_service.game_data.insert_game_data.assert_called_once()
    
    @patch('src.database.services.DatabaseService')
    def test_insert_scraped_game_failure(self, mock_db_service_class):
        """Test insert_scraped_game when insertion fails."""
        # Setup mocks
        mock_db_service = Mock()
        mock_db_service_class.return_value.__enter__.return_value = mock_db_service
        mock_db_service.game_data.insert_game_data.return_value = None
        
        # Execute
        result = insert_scraped_game(1029700001, 1997, "regular", "https://example.com", {})
        
        # Assert
        assert result is False
    
    @patch('src.database.services.DatabaseService')
    def test_get_games_for_analysis(self, mock_db_service_class):
        """Test get_games_for_analysis convenience function."""
        # Setup mocks
        mock_db_service = Mock()
        mock_db_service_class.return_value.__enter__.return_value = mock_db_service
        expected_games = [Mock(spec=RawGameData)]
        mock_db_service.game_data.get_games_by_season.return_value = expected_games
        
        # Execute
        result = get_games_for_analysis(1997, "regular")
        
        # Assert
        assert result == expected_games
        mock_db_service.game_data.get_games_by_season.assert_called_once_with(1997, "regular")
    
    @patch('src.database.services.DatabaseService')
    def test_delete_single_game(self, mock_db_service_class):
        """Test delete_single_game convenience function."""
        # Setup mocks
        mock_db_service = Mock()
        mock_db_service_class.return_value.__enter__.return_value = mock_db_service
        mock_db_service.game_data.delete_game_data.return_value = True
        
        # Execute
        result = delete_single_game(1029700001)
        
        # Assert
        assert result is True
        mock_db_service.game_data.delete_game_data.assert_called_once_with(1029700001)
    
    @patch('src.database.services.DatabaseService')
    def test_delete_season_games(self, mock_db_service_class):
        """Test delete_season_games convenience function."""
        # Setup mocks
        mock_db_service = Mock()
        mock_db_service_class.return_value.__enter__.return_value = mock_db_service
        expected_stats = {'would_delete': 5, 'deleted': 0}
        mock_db_service.game_data.delete_games_by_season.return_value = expected_stats
        
        # Execute
        result = delete_season_games(1997, "regular", dry_run=True)
        
        # Assert
        assert result == expected_stats
        mock_db_service.game_data.delete_games_by_season.assert_called_once_with(1997, "regular", True)
    
    @patch('src.database.services.DatabaseService')
    def test_with_database_decorator(self, mock_db_service_class):
        """Test with_database decorator."""
        # Setup mocks
        mock_db_service = Mock()
        mock_db_service_class.return_value.__enter__.return_value = mock_db_service
        
        # Define test function with decorator
        @with_database
        def test_function(db, arg1, arg2, kwarg1=None):
            assert db == mock_db_service
            return f"result_{arg1}_{arg2}_{kwarg1}"
        
        # Execute
        result = test_function("a", "b", kwarg1="c")
        
        # Assert
        assert result == "result_a_b_c"


class TestErrorHandling:
    """Test error handling across all services."""
    
    @pytest.fixture
    def mock_session_with_error(self):
        """Create a mock session that raises errors."""
        session = Mock()
        session.commit.side_effect = SQLAlchemyError("Database connection lost")
        return session
    
    def test_game_data_service_error_handling(self, mock_session_with_error):
        """Test GameDataService error handling."""
        service = GameDataService(mock_session_with_error)
        
        # Mock the query to return None for insert (so it attempts to create new record)
        mock_session_with_error.query.return_value.filter_by.return_value.first.return_value = None
        
        # Test various operations with error
        result = service.insert_game_data(1, 1997, "regular", "url", {})
        assert result is None
        
        result = service.update_game_data(1, {})
        assert result is None
        
        result = service.upsert_game_data(1, 1997, "regular", "url", {})
        assert result is None
    
    def test_scraping_session_service_error_handling(self, mock_session_with_error):
        """Test ScrapingSessionService error handling."""
        service = ScrapingSessionService(mock_session_with_error)
        
        # Test session start with error
        result = service.start_session("Test Session")
        assert result is None
        mock_session_with_error.rollback.assert_called()


# Performance and stress tests (marked as slow)
@pytest.mark.slow
class TestServicePerformance:
    """Test service layer performance with larger datasets."""
    
    @patch('src.database.services.DatabaseService')
    def test_bulk_game_operations_performance(self, mock_db_service_class):
        """Test performance of bulk game operations."""
        # Setup mocks
        mock_db_service = Mock()
        mock_db_service_class.return_value.__enter__.return_value = mock_db_service
        
        # Mock bulk update operation
        mock_db_service.game_data.update_multiple_games.return_value = {
            'total': 100, 'updated': 95, 'not_found': 3, 'failed': 2
        }
        
        # Create large update list
        updates = [
            {'game_id': 1029700000 + i, 'game_data': {'test': f'data_{i}'}}
            for i in range(100)
        ]
        
        # Execute
        result = update_multiple_games(updates)
        
        # Assert
        assert result['total'] == 100
        assert result['updated'] == 95
        mock_db_service.game_data.update_multiple_games.assert_called_once_with(updates)