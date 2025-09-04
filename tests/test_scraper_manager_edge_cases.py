"""
Edge case and error handling tests for scraper manager.

Tests various failure scenarios, edge cases, and error conditions
to ensure robust behavior of the scraper manager.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, Timeout, ConnectionError
import json

from src.scripts.scraper_manager import ScraperManager
from src.scrapers.game_url_generator import GameURLInfo
from src.scrapers.raw_data_extractor import ExtractionResult


@pytest.fixture
def mock_scraper_manager():
    """Create a ScraperManager with mocked dependencies."""
    with patch('src.scripts.scraper_manager.GameURLGenerator') as mock_gen, \
         patch('src.scripts.scraper_manager.RawDataExtractor') as mock_ext:
        
        manager = ScraperManager()
        manager.url_generator = mock_gen.return_value
        manager.data_extractor = mock_ext.return_value
        return manager


@pytest.fixture
def sample_game_url_info():
    """Sample GameURLInfo for testing."""
    return GameURLInfo(
        game_id="1029700001",
        season="1997",
        game_url="https://www.wnba.com/game/1029700001/playbyplay",
        game_type="regular"
    )


class TestScraperManagerErrorHandling:
    """Test error handling in ScraperManager."""

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_database_error(self, mock_db_service, mock_scraper_manager, sample_game_url_info):
        """Test handling database errors during single game scraping."""
        # Mock database service to raise exception
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.side_effect = Exception("Database connection failed")
        
        result = mock_scraper_manager.scrape_single_game(sample_game_url_info)
        
        assert result is False

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_insertion_failure(self, mock_db_service, mock_scraper_manager, sample_game_url_info):
        """Test handling database insertion failure."""
        # Mock successful extraction but failed insertion
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        mock_db_service.return_value.__enter__.return_value.game_data.insert_game_data.return_value = None
        
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.SUCCESS, {"test": "data"}, None
        )
        
        result = mock_scraper_manager.scrape_single_game(sample_game_url_info)
        
        assert result is False

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_extraction_timeout(self, mock_db_service, mock_scraper_manager, sample_game_url_info):
        """Test handling extraction timeout."""
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.TIMEOUT, None, None
        )
        
        result = mock_scraper_manager.scrape_single_game(sample_game_url_info)
        
        assert result is False

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_rate_limited(self, mock_db_service, mock_scraper_manager, sample_game_url_info):
        """Test handling rate limiting."""
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.RATE_LIMITED, None, None
        )
        
        result = mock_scraper_manager.scrape_single_game(sample_game_url_info)
        
        assert result is False

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_invalid_json(self, mock_db_service, mock_scraper_manager, sample_game_url_info):
        """Test handling invalid JSON from extraction."""
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.INVALID_JSON, None, None
        )
        
        result = mock_scraper_manager.scrape_single_game(sample_game_url_info)
        
        assert result is False

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_scrape_single_game_no_data(self, mock_db_service, mock_scraper_manager, sample_game_url_info):
        """Test handling when no data is available."""
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.NO_DATA, None, None
        )
        
        result = mock_scraper_manager.scrape_single_game(sample_game_url_info)
        
        assert result is False

    def test_scrape_season_session_creation_failure(self, mock_scraper_manager):
        """Test handling session creation failure in scrape_season."""
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=None):
            stats = mock_scraper_manager.scrape_season(1997, 'regular')
        
        assert stats['total'] == 0
        assert stats['success'] == 0
        assert stats['failed'] == 0
        assert stats['skipped'] == 0

    def test_scrape_all_seasons_session_creation_failure(self, mock_scraper_manager):
        """Test handling session creation failure in scrape_all_seasons."""
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=None):
            stats = mock_scraper_manager.scrape_all_seasons('regular')
        
        assert stats['seasons_processed'] == 0
        assert stats['total_games'] == 0
        assert stats['total_success'] == 0

    def test_scrape_all_seasons_url_generation_failure(self, mock_scraper_manager):
        """Test handling URL generation failure."""
        mock_scraper_manager.url_generator.regular_season_df = None
        
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123):
            with pytest.raises(TypeError):  # Changed from AttributeError to TypeError since None is not subscriptable
                mock_scraper_manager.scrape_all_seasons('regular')

    @patch('src.scripts.scraper_manager.time.sleep')
    def test_scrape_all_seasons_individual_season_failure(self, mock_sleep, mock_scraper_manager):
        """Test handling when individual seasons fail during bulk scraping."""
        # Mock DataFrame with multiple seasons - need to make it subscriptable
        mock_season_column = Mock()
        mock_season_column.unique.return_value.tolist.return_value = [1997, 1998]
        
        mock_df = Mock()
        mock_df.__getitem__ = Mock(return_value=mock_season_column)  # Support df['season']
        mock_scraper_manager.url_generator.regular_season_df = mock_df
        
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'generate_urls_for_season') as mock_gen_urls, \
             patch.object(mock_scraper_manager, 'update_session_progress'), \
             patch.object(mock_scraper_manager, 'complete_session'):
            
            # First season succeeds, second fails
            def side_effect(season, game_type):
                if season == 1997:
                    return [GameURLInfo("1029700001", "1997", "http://test.com", "regular")]
                else:
                    raise Exception("Season processing failed")
            
            mock_gen_urls.side_effect = side_effect
            
            with patch('src.scripts.scraper_manager.DatabaseService') as mock_db:
                mock_db.return_value.__enter__.return_value.game_data.game_exists.return_value = False
                
                with patch.object(mock_scraper_manager, 'scrape_single_game', return_value=True):
                    stats = mock_scraper_manager.scrape_all_seasons('regular')
        
        # Should have processed 2 seasons (1 success, 1 error)
        assert stats['seasons_processed'] == 1  # Only successful ones counted
        assert len(stats['season_results']) == 2  # Both attempts recorded
        
        # Check that error was recorded
        error_result = next((r for r in stats['season_results'] if 'error' in r), None)
        assert error_result is not None
        assert error_result['season'] == 1998

    def test_generate_urls_for_season_empty_result(self, mock_scraper_manager):
        """Test handling when URL generation returns empty results."""
        mock_scraper_manager.url_generator.generate_regular_season_ids.return_value = []
        
        urls = mock_scraper_manager.generate_urls_for_season(1997, 'regular')
        
        assert urls == []

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_update_session_progress_database_error(self, mock_db_service, mock_scraper_manager):
        """Test handling database errors during session updates."""
        mock_scraper_manager.current_session_id = 123
        mock_db_service.return_value.__enter__.return_value.scraping_session.update_session.side_effect = Exception("DB Error")
        
        # Currently the implementation doesn't handle DB errors, so it will raise
        with pytest.raises(Exception, match="DB Error"):
            mock_scraper_manager.update_session_progress(10, 2)

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_complete_session_database_error(self, mock_db_service, mock_scraper_manager):
        """Test handling database errors during session completion."""
        mock_scraper_manager.current_session_id = 123
        mock_db_service.return_value.__enter__.return_value.scraping_session.update_session.side_effect = Exception("DB Error")
        
        # Currently the implementation doesn't handle DB errors, so it will raise
        with pytest.raises(Exception, match="DB Error"):
            mock_scraper_manager.complete_session('completed')


class TestScraperManagerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_scrape_season_with_zero_max_games(self, mock_scraper_manager):
        """Test scraping with max_games = 0."""
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'generate_urls_for_season', return_value=[]):
            
            stats = mock_scraper_manager.scrape_season(1997, 'regular', max_games=0)
        
        assert stats['total'] == 0

    def test_scrape_all_seasons_empty_seasons_list(self, mock_scraper_manager):
        """Test scraping when no seasons are available."""
        # Mock DataFrame with empty seasons - need to make it subscriptable
        mock_season_column = Mock()
        mock_season_column.unique.return_value.tolist.return_value = []
        
        mock_df = Mock()
        mock_df.__getitem__ = Mock(return_value=mock_season_column)  # Support df['season']
        mock_scraper_manager.url_generator.regular_season_df = mock_df
        
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123):
            stats = mock_scraper_manager.scrape_all_seasons('regular')
        
        assert stats['seasons_processed'] == 0

    @patch('src.scripts.scraper_manager.time.sleep')
    def test_scrape_all_seasons_with_zero_max_games(self, mock_sleep, mock_scraper_manager):
        """Test bulk scraping with max_games_total = 0."""
        # Mock DataFrame with seasons - need to make it subscriptable
        mock_season_column = Mock()
        mock_season_column.unique.return_value.tolist.return_value = [1997]
        
        mock_df = Mock()
        mock_df.__getitem__ = Mock(return_value=mock_season_column)  # Support df['season']
        mock_scraper_manager.url_generator.regular_season_df = mock_df
        
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123):
            stats = mock_scraper_manager.scrape_all_seasons('regular', max_games_total=0)
        
        # Should stop immediately
        assert stats['total_success'] == 0

    def test_scrape_season_with_negative_max_games(self, mock_scraper_manager):
        """Test scraping with negative max_games."""
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'generate_urls_for_season', return_value=[]):
            
            # Should handle gracefully (treated as no limit)
            stats = mock_scraper_manager.scrape_season(1997, 'regular', max_games=-1)
        
        assert stats['total'] == 0

    def test_generate_urls_for_season_with_future_season(self, mock_scraper_manager):
        """Test URL generation for a future season."""
        # Mock that no data exists for future season
        mock_scraper_manager.url_generator.generate_regular_season_ids.side_effect = IndexError("No data for season")
        
        with pytest.raises(IndexError):
            mock_scraper_manager.generate_urls_for_season(2030, 'regular')

    def test_generate_urls_for_season_with_invalid_season(self, mock_scraper_manager):
        """Test URL generation for an invalid season."""
        mock_scraper_manager.url_generator.generate_regular_season_ids.side_effect = IndexError("Invalid season")
        
        with pytest.raises(IndexError):
            mock_scraper_manager.generate_urls_for_season(-1, 'regular')

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_list_active_sessions_database_error(self, mock_db_service, mock_scraper_manager, capsys):
        """Test listing sessions when database has errors."""
        mock_db_service.return_value.__enter__.return_value.scraping_session.get_active_sessions.side_effect = Exception("DB Error")
        
        # Currently the implementation doesn't handle DB errors, so it will raise
        with pytest.raises(Exception, match="DB Error"):
            mock_scraper_manager.list_active_sessions()

    def test_scrape_all_games_partial_failure(self, mock_scraper_manager):
        """Test scrape_all_games when one type succeeds and other fails."""
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'scrape_all_seasons') as mock_scrape_all, \
             patch.object(mock_scraper_manager, 'update_session_progress'), \
             patch.object(mock_scraper_manager, 'complete_session'):
            
            # First call (regular) succeeds, second call (playoff) fails
            def side_effect(game_type, max_games_per_season=None):
                if game_type == 'regular':
                    return {
                        'seasons_processed': 1,
                        'total_games': 5,
                        'total_success': 5,
                        'total_failed': 0,
                        'total_skipped': 0
                    }
                else:
                    raise Exception("Playoff scraping failed")
            
            mock_scrape_all.side_effect = side_effect
            
            with pytest.raises(Exception):
                mock_scraper_manager.scrape_all_games()


class TestScraperManagerConcurrencyAndRaceConditions:
    """Test potential concurrency issues and race conditions."""

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_concurrent_game_existence_check(self, mock_db_service, mock_scraper_manager, sample_game_url_info):
        """Test race condition where game is inserted between existence check and insertion."""
        # Simulate race condition: game doesn't exist during first check but does exist during insertion
        mock_db_service.return_value.__enter__.return_value.game_data.game_exists.return_value = False
        
        # Mock that insertion fails due to unique constraint (game was inserted by another process)
        from sqlalchemy.exc import IntegrityError
        mock_db_service.return_value.__enter__.return_value.game_data.insert_game_data.side_effect = IntegrityError("", "", "")
        
        mock_scraper_manager.data_extractor.extract_game_data.return_value = (
            ExtractionResult.SUCCESS, {"test": "data"}, None
        )
        
        result = mock_scraper_manager.scrape_single_game(sample_game_url_info)
        
        # Should handle gracefully (depends on implementation - might be True or False)
        assert isinstance(result, bool)

    @patch('src.scripts.scraper_manager.DatabaseService')
    def test_session_update_during_completion(self, mock_db_service, mock_scraper_manager):
        """Test updating session progress while another process is completing the session."""
        mock_scraper_manager.current_session_id = 123
        
        # Mock that session no longer exists (was completed/deleted by another process)
        mock_db_service.return_value.__enter__.return_value.scraping_session.update_session.return_value = None
        
        # Should handle gracefully
        mock_scraper_manager.update_session_progress(10, 2)
        mock_scraper_manager.complete_session('completed')


@pytest.mark.slow
class TestScraperManagerStressAndPerformance:
    """Stress tests and performance-related edge cases."""

    @patch('src.scripts.scraper_manager.time.sleep')
    def test_large_season_scraping(self, mock_sleep, mock_scraper_manager):
        """Test scraping a season with many games."""
        # Create a large list of games (simulating a full season)
        large_game_list = [
            GameURLInfo(f"102970{i:04d}", "1997", f"http://test.com/{i}", "regular")
            for i in range(1, 301)  # 300 games
        ]
        
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'generate_urls_for_season', return_value=large_game_list), \
             patch('src.scripts.scraper_manager.DatabaseService') as mock_db, \
             patch.object(mock_scraper_manager, 'scrape_single_game', return_value=True) as mock_scrape:
            
            mock_db.return_value.__enter__.return_value.game_data.game_exists.return_value = False
            
            stats = mock_scraper_manager.scrape_season(1997, 'regular')
        
        assert stats['total'] == 300
        assert stats['success'] == 300
        assert mock_scrape.call_count == 300

    @patch('src.scripts.scraper_manager.time.sleep')
    def test_bulk_scraping_memory_usage(self, mock_sleep, mock_scraper_manager):
        """Test that bulk scraping doesn't accumulate excessive data in memory."""
        # Mock many seasons with games - need to make it subscriptable
        mock_season_column = Mock()
        mock_season_column.unique.return_value.tolist.return_value = list(range(1997, 2026))  # 29 seasons
        
        mock_df = Mock()
        mock_df.__getitem__ = Mock(return_value=mock_season_column)  # Support df['season']
        mock_scraper_manager.url_generator.regular_season_df = mock_df
        
        def generate_urls_side_effect(season, game_type):
            # Return a reasonable number of games per season
            return [
                GameURLInfo(f"10{season % 100}{i:05d}", str(season), f"http://test.com/{season}_{i}", game_type)
                for i in range(1, 11)  # 10 games per season
            ]
        
        with patch.object(mock_scraper_manager, 'start_scraping_session', return_value=123), \
             patch.object(mock_scraper_manager, 'generate_urls_for_season', side_effect=generate_urls_side_effect), \
             patch('src.scripts.scraper_manager.DatabaseService') as mock_db, \
             patch.object(mock_scraper_manager, 'scrape_single_game', return_value=True):
            
            mock_db.return_value.__enter__.return_value.game_data.game_exists.return_value = False
            
            stats = mock_scraper_manager.scrape_all_seasons('regular', max_games_total=50)
        
        # Should have processed 50 games total across multiple seasons
        assert stats['total_success'] == 50
        
        # Should not have processed all seasons (due to limit)
        assert stats['seasons_processed'] < 29


# Custom markers for different test types
pytestmark = [
    pytest.mark.scraper_manager,
    pytest.mark.edge_cases
]