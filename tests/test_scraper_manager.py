"""
Tests for the scraper manager module.

This module tests the ScraperManager class and its CLI interface,
including URL generation, session management, and bulk scraping operations.
"""

import pytest
import sys
import json
import argparse
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from io import StringIO

from src.scripts.scraper_manager import ScraperManager, main, setup_logging
from src.scrapers.game_url_generator import GameURLInfo
from src.scrapers.raw_data_extractor import ExtractionResult, ExtractionMetadata, DataQuality


@pytest.fixture
def mock_scraper_manager():
    """Create a ScraperManager with mocked dependencies."""
    with patch('src.scripts.scraper_manager.GameURLGenerator') as mock_gen, \
         patch('src.scripts.scraper_manager.RawDataExtractor') as mock_ext, \
         patch('src.scripts.scraper_manager.DatabaseService'):
        
        manager = ScraperManager()
        manager.url_generator = mock_gen.return_value
        manager.data_extractor = mock_ext.return_value
        return manager


@pytest.fixture
def sample_game_url_infos():
    """Sample GameURLInfo objects for testing."""
    return [
        GameURLInfo(
            game_id="1029700001",
            season="1997",
            game_url="https://www.wnba.com/game/1029700001/playbyplay",
            game_type="regular"
        ),
        GameURLInfo(
            game_id="1029700002",
            season="1997", 
            game_url="https://www.wnba.com/game/1029700002/playbyplay",
            game_type="regular"
        ),
        GameURLInfo(
            game_id="1029700051",
            season="1997",
            game_url="https://www.wnba.com/game/1029700051/playbyplay", 
            game_type="playoff"
        )
    ]


@pytest.fixture
def mock_extraction_metadata():
    """Mock extraction metadata."""
    return ExtractionMetadata(
        extraction_time_ms=150,
        response_size_bytes=34000,
        json_size_bytes=12000,
        data_quality=DataQuality.COMPLETE,
        user_agent_used="test-agent"
    )


@pytest.fixture
def sample_game_data():
    """Sample game data that would be extracted."""
    return {
        "gameId": "1029700001",
        "homeTeam": "NYL",
        "awayTeam": "PHX", 
        "gameDate": "1997-06-21",
        "playByPlay": [
            {"period": 1, "time": "10:00", "description": "Game Start"}
        ]
    }


class TestScraperManager:
    """Test the ScraperManager class."""

    def test_scraper_manager_initialization(self):
        """Test that ScraperManager initializes correctly."""
        with patch('src.scripts.scraper_manager.GameURLGenerator') as mock_gen, \
             patch('src.scripts.scraper_manager.RawDataExtractor') as mock_ext:
            
            manager = ScraperManager()
            
            mock_gen.assert_called_once()
            mock_ext.assert_called_once()
            assert manager.current_session_id is None

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_start_scraping_session_success(self, mock_db_service):
        """Test successfully starting a scraping session."""
        # Setup mocks
        mock_session = Mock()
        mock_session.id = 123
        mock_db_service.return_value.__enter__.return_value.scraping_session.start_session.return_value = mock_session
        
        manager = ScraperManager()
        session_id = manager.start_scraping_session("test_session")
        
        assert session_id == 123
        assert manager.current_session_id == 123

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_start_scraping_session_failure(self, mock_db_service):
        """Test handling failure when starting scraping session."""
        mock_db_service.return_value.__enter__.return_value.scraping_session.start_session.return_value = None
        
        manager = ScraperManager()
        session_id = manager.start_scraping_session("test_session")
        
        assert session_id is None
        assert manager.current_session_id is None

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_update_session_progress(self, mock_db_service):
        """Test updating session progress."""
        manager = ScraperManager()
        manager.current_session_id = 123
        
        manager.update_session_progress(10, 2)
        
        mock_db_service.return_value.__enter__.return_value.scraping_session.update_session.assert_called_with(
            123, games_scraped=10, errors_count=2
        )

    @patch('src.scripts.scraper_manager.DatabaseService') 
    def test_update_session_progress_no_active_session(self, mock_db_service):
        """Test updating progress with no active session."""
        manager = ScraperManager()
        manager.current_session_id = None
        
        # Should not raise exception, just log warning
        manager.update_session_progress(10, 2)
        
        mock_db_service.return_value.__enter__.return_value.scraping_session.update_session.assert_not_called()

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_complete_session(self, mock_db_service):
        """Test completing a scraping session."""
        manager = ScraperManager()
        manager.current_session_id = 123
        
        manager.complete_session('completed')
        
        mock_db_service.return_value.__enter__.return_value.scraping_session.update_session.assert_called_with(
            123, status='completed'
        )

    def test_generate_urls_for_season_regular(self, mock_scraper_manager, sample_game_url_infos):
        """Test generating URLs for a regular season."""
        mock_scraper_manager.url_generator.generate_regular_season_ids.return_value = ["1029700001", "1029700002"]
        mock_scraper_manager.url_generator.generate_game_url.side_effect = lambda x: f"https://www.wnba.com/game/{x}/playbyplay"
        
        urls = mock_scraper_manager.generate_urls_for_season(1997, 'regular')
        
        assert len(urls) == 2
        assert urls[0].game_id == "1029700001"
        assert urls[0].season == "1997"
        assert urls[0].game_type == "regular"
        assert "1029700001" in urls[0].game_url

    def test_generate_urls_for_season_playoff(self, mock_scraper_manager):
        """Test generating URLs for playoffs."""
        mock_scraper_manager.url_generator.generate_playoff_ids.return_value = ["1029700051"]
        mock_scraper_manager.url_generator.generate_game_url.side_effect = lambda x: f"https://www.wnba.com/game/{x}/playbyplay"
        
        urls = mock_scraper_manager.generate_urls_for_season(1997, 'playoff')
        
        assert len(urls) == 1
        assert urls[0].game_type == "playoff"

    def test_generate_urls_for_season_invalid_type(self, mock_scraper_manager):
        """Test generating URLs with invalid game type."""
        urls = mock_scraper_manager.generate_urls_for_season(1997, 'invalid')
        
        assert urls == []

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_success(self, mock_db_service, mock_scraper_manager, 
                                       sample_game_url_infos, sample_game_data, mock_extraction_metadata):
        """Test successfully scraping a single game."""
        game_url_info = sample_game_url_infos[0]
        
        # Mock database checks
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        mock_db_service.return_value.__enter__.return_value.game_data.insert_game_data.return_value = Mock()
        
        # Mock data extraction
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.SUCCESS, sample_game_data, mock_extraction_metadata
        )
        
        result = mock_scraper_manager.scrape_single_game(game_url_info)
        
        assert result is True
        mock_db_service.return_value.__enter__.return_value.game_data.insert_game_data.assert_called_once()

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_already_exists(self, mock_db_service, mock_scraper_manager, sample_game_url_infos):
        """Test scraping a game that already exists."""
        game_url_info = sample_game_url_infos[0]
        
        # Mock that game already exists
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = True
        
        result = mock_scraper_manager.scrape_single_game(game_url_info)
        
        assert result is True
        mock_scraper_manager.data_extractor.extract_game_data.assert_not_called()

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_extraction_failure(self, mock_db_service, mock_scraper_manager, sample_game_url_infos):
        """Test scraping when data extraction fails."""
        game_url_info = sample_game_url_infos[0]
        
        # Mock database checks
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        
        # Mock extraction failure
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.NETWORK_ERROR, None, None
        )
        
        result = mock_scraper_manager.scrape_single_game(game_url_info)
        
        assert result is False

    @patch('src.scripts.scraper_manager.time.sleep')  # Speed up tests
    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_season(self, mock_db_service, mock_sleep, mock_scraper_manager, sample_game_url_infos):
        """Test scraping a full season."""
        # Mock session creation
        mock_session = Mock()
        mock_session.id = 123
        mock_db_service.return_value.__enter__.return_value.scraping_session.start_session.return_value = mock_session
        
        # Mock URL generation using patch.object
        with patch.object(mock_scraper_manager, 'generate_urls_for_season', return_value=sample_game_url_infos[:2]) as mock_gen_urls:
            # Mock that games don't exist and scraping succeeds
            mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
            
            with patch.object(mock_scraper_manager, 'scrape_single_game', return_value=True) as mock_scrape:
                stats = mock_scraper_manager.scrape_season(1997, 'regular', max_games=2)
            
            assert stats['total'] == 2
            assert stats['success'] == 2
            assert stats['failed'] == 0
            assert stats['skipped'] == 0
        assert mock_scrape.call_count == 2

    @patch('pandas.DataFrame')
    @patch('src.scripts.scraper_manager.time.sleep')  # Speed up tests
    def test_scrape_all_seasons_regular(self, mock_sleep, mock_df, mock_scraper_manager, sample_game_url_infos):
        """Test scraping all regular seasons."""
        # Mock DataFrame with seasons - need to support df['season']
        mock_season_column = Mock()
        mock_season_column.unique.return_value.tolist.return_value = [1997, 1998]
        
        mock_dataframe = Mock()
        mock_dataframe.__getitem__ = Mock(return_value=mock_season_column)
        mock_scraper_manager.url_generator.regular_season_df = mock_dataframe
        
        # Mock session creation
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'generate_urls_for_season') as mock_gen_urls, \
             patch.object(mock_scraper_manager, 'scrape_single_game', return_value=True) as mock_scrape, \
             patch('src.scripts.scraper_manager.DatabaseService') as mock_db:
            
            mock_gen_urls.return_value = [sample_game_url_infos[0]]  # 1 game per season
            mock_db.return_value.__enter__.return_value.game_data.game_exists.return_value = False
            
            stats = mock_scraper_manager.scrape_all_seasons('regular', max_games_total=2)
        
        assert stats['seasons_processed'] == 2
        assert stats['total_success'] == 2
        assert mock_scrape.call_count == 2

    def test_scrape_all_seasons_with_limit(self, mock_scraper_manager, sample_game_url_infos):
        """Test scraping all seasons with a total game limit."""
        # Mock DataFrame with multiple seasons - need to make it subscriptable
        mock_season_column = Mock()
        mock_season_column.unique.return_value.tolist.return_value = [1997, 1998, 1999]
        
        mock_df = Mock()
        mock_df.__getitem__ = Mock(return_value=mock_season_column)  # Support df['season']
        mock_scraper_manager.url_generator.regular_season_df = mock_df
        
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'generate_urls_for_season', return_value=sample_game_url_infos), \
             patch.object(mock_scraper_manager, 'scrape_single_game', return_value=True) as mock_scrape, \
             patch('src.scripts.scraper_manager.DatabaseService') as mock_db, \
             patch('src.scripts.scraper_manager.time.sleep'):
            
            mock_db.return_value.__enter__.return_value.game_data.game_exists.return_value = False
            
            # Limit to 2 total games
            stats = mock_scraper_manager.scrape_all_seasons('regular', max_games_total=2)
        
        # Should stop after 2 games, not process all seasons
        assert stats['total_success'] == 2
        assert mock_scrape.call_count == 2

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_list_active_sessions(self, mock_db_service, mock_scraper_manager, capsys):
        """Test listing active scraping sessions."""
        # Mock active sessions
        mock_session1 = Mock()
        mock_session1.id = 1
        mock_session1.session_name = "session_1"
        mock_session1.start_time = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_session2 = Mock()
        mock_session2.id = 2
        mock_session2.session_name = "session_2"  
        mock_session2.start_time = datetime(2024, 1, 1, 13, 0, 0)
        
        mock_db_service.return_value.__enter__.return_value.scraping_session.get_active_sessions.return_value = [
            mock_session1, mock_session2
        ]
        
        mock_scraper_manager.list_active_sessions()
        
        captured = capsys.readouterr()
        assert "Active scraping sessions:" in captured.out
        assert "session_1" in captured.out
        assert "session_2" in captured.out

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_list_active_sessions_empty(self, mock_db_service, mock_scraper_manager, capsys):
        """Test listing active sessions when none exist."""
        mock_db_service.return_value.__enter__.return_value.scraping_session.get_active_sessions.return_value = []
        
        mock_scraper_manager.list_active_sessions()
        
        captured = capsys.readouterr()
        assert "No active scraping sessions found." in captured.out


class TestScraperManagerCLI:
    """Test the CLI interface of scraper manager."""

    @patch('src.scripts.scraper_manager.ScraperManager')
    @patch('src.scripts.scraper_manager.setup_logging')
    @patch('sys.argv', ['scraper_manager.py', 'scrape-season', '--season', '2024'])
    def test_main_scrape_season(self, mock_setup_logging, mock_manager_class):
        """Test CLI scrape-season command."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.scrape_season.return_value = {
            'total': 10, 'success': 8, 'failed': 1, 'skipped': 1
        }
        
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            main()
        
        mock_manager.scrape_season.assert_called_with(2024, 'regular', None)
        output = fake_stdout.getvalue()
        assert "Total games: 10" in output
        assert "Successfully scraped: 8" in output

    @patch('src.scripts.scraper_manager.ScraperManager')
    @patch('src.scripts.scraper_manager.setup_logging')
    @patch('sys.argv', ['scraper_manager.py', 'scrape-all-regular', '--max-games', '5'])
    def test_main_scrape_all_regular(self, mock_setup_logging, mock_manager_class):
        """Test CLI scrape-all-regular command."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.scrape_all_seasons.return_value = {
            'seasons_processed': 3,
            'total_games': 5,
            'total_success': 4,
            'total_failed': 1,
            'total_skipped': 0,
            'season_results': [
                {'season': 1997, 'stats': {'success': 2, 'failed': 0, 'skipped': 0}},
                {'season': 1998, 'stats': {'success': 2, 'failed': 1, 'skipped': 0}}
            ]
        }
        
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            main()
        
        mock_manager.scrape_all_seasons.assert_called_with('regular', 5)
        output = fake_stdout.getvalue()
        assert "All Regular Season Scraping Results:" in output
        assert "Seasons processed: 3" in output

    @patch('src.scripts.scraper_manager.ScraperManager')
    @patch('src.scripts.scraper_manager.setup_logging')
    @patch('sys.argv', ['scraper_manager.py', 'scrape-all-games', '--max-games', '10'])
    def test_main_scrape_all_games(self, mock_setup_logging, mock_manager_class):
        """Test CLI scrape-all-games command."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.scrape_all_games.return_value = {
            'regular_stats': {
                'seasons_processed': 2,
                'total_games': 6,
                'total_success': 5,
                'total_failed': 1,
                'total_skipped': 0
            },
            'playoff_stats': {
                'seasons_processed': 2,
                'total_games': 4, 
                'total_success': 4,
                'total_failed': 0,
                'total_skipped': 0
            },
            'combined_stats': {
                'total_games': 10,
                'total_success': 9,
                'total_failed': 1,
                'total_skipped': 0
            }
        }
        
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            main()
        
        mock_manager.scrape_all_games.assert_called_with(10)
        output = fake_stdout.getvalue()
        assert "ALL GAMES SCRAPING RESULTS:" in output
        assert "Total games processed: 10" in output

    @patch('src.scripts.scraper_manager.ScraperManager')
    @patch('src.scripts.scraper_manager.setup_logging')
    @patch('sys.argv', ['scraper_manager.py', 'test-single', '--game-id', '1029700001', '--season', '1997'])
    def test_main_test_single(self, mock_setup_logging, mock_manager_class):
        """Test CLI test-single command."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.url_generator.generate_game_url.return_value = "https://www.wnba.com/game/1029700001/playbyplay"
        mock_manager.scrape_single_game.return_value = True
        
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            main()
        
        mock_manager.start_scraping_session.assert_called()
        mock_manager.scrape_single_game.assert_called()
        mock_manager.complete_session.assert_called_with('completed')
        output = fake_stdout.getvalue()
        assert "Successfully scraped game 1029700001" in output

    @patch('src.scripts.scraper_manager.ScraperManager')
    @patch('src.scripts.scraper_manager.setup_logging') 
    @patch('sys.argv', ['scraper_manager.py', 'list-sessions'])
    def test_main_list_sessions(self, mock_setup_logging, mock_manager_class):
        """Test CLI list-sessions command."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        main()
        
        mock_manager.list_active_sessions.assert_called_once()

    @patch('src.scripts.scraper_manager.ScraperManager')
    @patch('src.scripts.scraper_manager.setup_logging')
    @patch('sys.argv', ['scraper_manager.py', 'scrape-season'])
    def test_main_missing_season_argument(self, mock_setup_logging, mock_manager_class):
        """Test CLI with missing required season argument."""
        with pytest.raises(SystemExit):
            main()

    @patch('src.scripts.scraper_manager.ScraperManager') 
    @patch('src.scripts.scraper_manager.setup_logging')
    @patch('sys.argv', ['scraper_manager.py', 'test-single', '--game-id', '1029700001'])
    def test_main_missing_season_for_test_single(self, mock_setup_logging, mock_manager_class):
        """Test CLI test-single with missing season argument.""" 
        with pytest.raises(SystemExit):
            main()


class TestLoggingSetup:
    """Test logging configuration."""
    
    @patch('src.scripts.scraper_manager.logging.basicConfig')
    def test_setup_logging_default(self, mock_basic_config):
        """Test default logging setup."""
        setup_logging()
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 20  # INFO level
        
    @patch('src.scripts.scraper_manager.logging.basicConfig')
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test verbose logging setup."""
        setup_logging(verbose=True)
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 10  # DEBUG level


class TestScraperManagerIntegration:
    """Integration tests using real components with minimal mocking."""
    
    @patch('src.scripts.scraper_manager.DatabaseService')
    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_integration_scrape_single_game(self, mock_requests, mock_db_service, mock_html_response, sample_game_data):
        """Integration test for scraping a single game with real URL generator."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = mock_html_response
        mock_response.content = mock_html_response.encode()
        mock_requests.return_value = mock_response
        
        # Mock database operations
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        mock_db_service.return_value.__enter__.return_value.game_data.insert_game_data.return_value = Mock()
        
        # Create manager with real components (but mocked external calls)
        with patch('src.scrapers.game_url_generator.pd.read_csv') as mock_csv:
            mock_csv.side_effect = [
                # Mock regular season CSV
                Mock(spec=['__getitem__'], **{'__getitem__': lambda self, key: [1997] if key == 'season' else [112] if key == 'total_regular_games' else [10297]}),
                # Mock playoff CSV  
                Mock(spec=['__getitem__'], **{'__getitem__': lambda self, key: [1997] if key == 'season' else ["3"] if key == 'best_of' else [10297] if key == 'id_prefix' else [3] if key == 'total_games' else [None]})
            ]
            
            manager = ScraperManager()
            
            game_url_info = GameURLInfo(
                game_id="1029700001",
                season="1997",
                game_url="https://www.wnba.com/game/1029700001/playbyplay",
                game_type="regular"
            )
            
            result = manager.scrape_single_game(game_url_info)
            
            assert result is True
            mock_requests.assert_called_once()
            mock_db_service.return_value.__enter__.return_value.game_data.insert_game_data.assert_called_once()


@pytest.mark.slow
class TestScraperManagerSlow:
    """Slower integration tests that can be skipped during rapid development."""
    
    @patch('src.scripts.scraper_manager.DatabaseService')
    @patch('src.scripts.scraper_manager.time.sleep')
    def test_full_season_scraping_workflow(self, mock_sleep, mock_db_service, mock_scraper_manager, sample_game_url_infos):
        """Test the full workflow of scraping a season."""
        # Mock successful session creation
        mock_session = Mock()
        mock_session.id = 123
        mock_db_service.return_value.__enter__.return_value.scraping_session.start_session.return_value = mock_session
        
        # Mock URL generation for full season using patch.object
        with patch.object(mock_scraper_manager, 'generate_urls_for_season', return_value=sample_game_url_infos) as mock_gen_urls:
            # Mock that no games exist initially
            mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
            
            # Mock successful scraping
            with patch.object(mock_scraper_manager, 'scrape_single_game', return_value=True) as mock_scrape:
                stats = mock_scraper_manager.scrape_season(1997, 'regular')
            
            # Verify session management
            mock_db_service.return_value.__enter__.return_value.scraping_session.start_session.assert_called()
            
            # Verify all games were processed
            assert stats['total'] == len(sample_game_url_infos)
            assert stats['success'] == len(sample_game_url_infos)
            assert stats['failed'] == 0
        assert stats['skipped'] == 0


# Pytest markers for test organization
pytestmark = [
    pytest.mark.scraper_manager,
    pytest.mark.unit
]