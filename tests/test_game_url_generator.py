import pytest
import pandas as pd
import json
from unittest.mock import Mock, patch, mock_open, MagicMock
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

from src.scrapers.game_url_generator import GameURLGenerator, GameURLInfo


class TestGameURLInfo:
    """Tests for GameURLInfo dataclass."""
    
    def test_game_url_info_creation(self):
        """Test creating GameURLInfo instance."""
        info = GameURLInfo(
            game_id="1029700001",
            season="1997",
            game_url="https://www.wnba.com/game/1029700001/playbyplay"
        )
        assert info.game_id == "1029700001"
        assert info.season == "1997"
        assert info.game_url == "https://www.wnba.com/game/1029700001/playbyplay"
        assert info.game_type == "regular"  # default value

    def test_game_url_info_to_dict(self):
        """Test converting GameURLInfo to dictionary."""
        info = GameURLInfo(
            game_id="1029700001",
            season="1997",
            game_url="https://www.wnba.com/game/1029700001/playbyplay",
            game_type="playoff"
        )
        result = info.to_dict()
        
        assert result['game_id'] == "1029700001"
        assert result['season'] == "1997"
        assert result['game_url'] == "https://www.wnba.com/game/1029700001/playbyplay"
        assert result['game_type'] == "playoff"


class TestGameURLGenerator:
    """Tests for GameURLGenerator class."""
    
    @pytest.fixture
    def mock_regular_season_df(self):
        """Mock regular season DataFrame."""
        return pd.DataFrame({
            'season': [1997, 2020, 2025],
            'total_regular_games': [115, 72, 286],
            'id_prefix': [10297, 10320, 10325]
        }).astype({'season': 'int64', 'total_regular_games': 'int64', 'id_prefix': 'int64'})

    @pytest.fixture
    def mock_playoff_df(self):
        """Mock playoff DataFrame."""
        df = pd.DataFrame({
            'season': [1997, 2001, 2002, 2025],
            'best_of': ["3", "5", "3,5,7", "3,5,7"],
            'id_prefix': [10297, 10301, 10302, 10325],
            'total_games': [3, 15, None, None],
            'num_series': [None, None, "4,2,1", "4,2,1"]
        })
        df = df.astype({'season': 'int64', 'id_prefix': 'int64'})
        # Convert total_games to nullable integer type to handle None values properly
        df['total_games'] = df['total_games'].astype('Int64')
        return df

    @pytest.fixture
    def generator(self, mock_regular_season_df, mock_playoff_df):
        """Create GameURLGenerator instance with mocked DataFrames."""
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.side_effect = [mock_regular_season_df, mock_playoff_df]
            with patch.object(GameURLGenerator, 'GAMES_REGULAR_FP', 'mocked_regular.csv'), \
                 patch.object(GameURLGenerator, 'GAMES_PLAYOFF_FP', 'mocked_playoff.csv'):
                return GameURLGenerator()

    # Basic URL Generation Tests
    def test_generate_game_url(self, generator):
        """Test basic game URL generation."""
        game_url = generator.generate_game_url("1029700001")
        assert game_url == "https://www.wnba.com/game/1029700001/playbyplay"

    @pytest.mark.parametrize("game_id,expected_url", [
        ("1029700001", "https://www.wnba.com/game/1029700001/playbyplay"),
        ("1032500150", "https://www.wnba.com/game/1032500150/playbyplay"),
        ("1030200075", "https://www.wnba.com/game/1030200075/playbyplay"),
    ])
    def test_generate_game_url_multiple_ids(self, generator, game_id, expected_url):
        """Test URL generation with multiple game IDs."""
        result = generator.generate_game_url(game_id)
        assert result == expected_url

    # Game ID Generation Tests
    def test_generate_game_ids_regular(self, generator):
        """Test generating regular season game IDs."""
        game_ids = generator.generate_game_ids("regular", 1997)
        assert len(game_ids) == 115
        assert game_ids[0] == "1029700001"
        assert game_ids[-1] == "1029700115"  # Last game

    def test_generate_game_ids_playoff(self, generator):
        """Test generating playoff game IDs."""
        game_ids = generator.generate_game_ids("playoff", 1997)
        assert len(game_ids) == 3
        assert all(game_id.startswith("10297") for game_id in game_ids)

    def test_generate_game_ids_invalid_type(self, generator):
        """Test generating game IDs with invalid type."""
        result = generator.generate_game_ids("invalid", 1997)
        assert result == []

    # Regular Season ID Generation Tests
    def test_generate_regular_season_ids_1997(self, generator):
        """Test regular season ID generation for 1997."""
        game_ids = generator.generate_regular_season_ids(1997)
        assert len(game_ids) == 115
        assert game_ids[0] == "1029700001"
        assert game_ids[-1] == "1029700115"  # prefix + zfill(5) of 115
        assert all(len(game_id) == 10 for game_id in game_ids)

    def test_generate_regular_season_ids_2020(self, generator):
        """Test regular season ID generation for 2020 (special case)."""
        game_ids = generator.generate_regular_season_ids(2020)
        assert len(game_ids) == 72
        assert game_ids[0] == "1032010001"  # Special format for 2020
        assert game_ids[-1] == "1032010072"
        assert all(len(game_id) == 10 for game_id in game_ids)

    def test_generate_regular_season_ids_2025(self, generator):
        """Test regular season ID generation for 2025."""
        game_ids = generator.generate_regular_season_ids(2025)
        assert len(game_ids) == 286
        assert game_ids[0] == "1032500001"
        assert game_ids[-1] == "1032500286"  # prefix + zfill(5) of 286

    # Playoff ID Generation Tests
    def test_generate_playoff_ids_pre_2002(self, generator):
        """Test playoff ID generation for seasons before 2002."""
        game_ids = generator.generate_playoff_ids(1997)
        assert len(game_ids) == 3
        assert all(game_id.startswith("10297") for game_id in game_ids)
        assert all(len(game_id) == 10 for game_id in game_ids)

    def test_generate_playoff_ids_post_2002(self, generator):
        """Test playoff ID generation for seasons 2002 and later."""
        game_ids = generator.generate_playoff_ids(2002)
        # Based on "3,5,7" best_of and "4,2,1" num_series
        # Round 1: 4 series × 3 games = 12 IDs
        # Round 2: 2 series × 5 games = 10 IDs
        # Round 3: 1 series × 7 games = 7 IDs
        # Total: 29 IDs
        assert len(game_ids) == 29
        assert game_ids[0] == "1030200101"  # Round 1, Series 0, Game 1
        assert game_ids[11] == "1030200133"  # Round 1, Series 3, Game 3

    # URL Generation for Multiple Seasons Tests
    def test_generate_regular_season_game_urls_single_season(self, generator):
        """Test generating URLs for a single regular season."""
        urls = generator.generate_regular_season_game_urls(1997)
        assert len(urls) == 115
        assert urls[0] == "https://www.wnba.com/game/1029700001/playbyplay"
        assert urls[-1] == "https://www.wnba.com/game/1029700115/playbyplay"

    def test_generate_regular_season_game_urls_all_seasons(self, generator):
        """Test generating URLs for all regular seasons."""
        urls = generator.generate_regular_season_game_urls()
        # 115 + 72 + 286 = 473 total games across all seasons
        assert len(urls) == 473

    def test_generate_playoff_game_urls_single_season(self, generator):
        """Test generating URLs for a single playoff season."""
        urls = generator.generate_playoff_game_urls(1997)
        assert len(urls) == 3
        assert all(url.startswith("https://www.wnba.com/game/10297") for url in urls)

    def test_generate_playoff_game_urls_all_seasons(self, generator):
        """Test generating URLs for all playoff seasons."""
        urls = generator.generate_playoff_game_urls()
        # Calculate expected based on our mock data:
        # 1997: 3 games, 2001: 15 games, 2002: 29 games, 2025: 29 games = 76 total
        assert len(urls) == 76

    def test_generate_all_urls(self, generator):
        """Test generating all URLs (regular + playoff)."""
        urls = generator.generate_all_urls()
        # 473 regular (115+72+286) + 76 playoff (3+15+29+29) = 549 total
        assert len(urls) == 549

    def test_generate_all_ids(self, generator):
        """Test generating all IDs (regular + playoff)."""
        # Based on our mock data: 
        # Regular season: 1997(115) + 2020(72) + 2025(286) = 473
        # Playoff: 1997(3) + 2001(15) + 2002(29) + 2025(29) = 76
        # Total: 473 + 76 = 549
        ids = generator.generate_all_ids()
        assert len(ids) == 549
        # Verify we have IDs from different seasons
        assert any(id.startswith("10297") for id in ids)  # 1997
        assert any(id.startswith("10320") for id in ids)  # 2020  
        assert any(id.startswith("10325") for id in ids)  # 2025

    # Validation Tests
    @patch('requests.get')
    def test_validate_game_url_success(self, mock_get, generator):
        """Test successful game URL validation."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = generator.validate_game_url("https://www.wnba.com/game/1029700001/playbyplay")
        assert result is True
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_validate_game_url_failure(self, mock_get, generator):
        """Test failed game URL validation."""
        mock_get.side_effect = RequestException("Network error")

        result = generator.validate_game_url("https://www.wnba.com/game/invalid/playbyplay")
        assert result is False

    @patch('requests.get')
    def test_validate_play_by_play_success(self, mock_get, generator):
        """Test successful play-by-play validation."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = '<html><script id="__NEXT_DATA__">{"data": "test"}</script></html>'
        mock_get.return_value = mock_response
        
        result = generator.validate_play_by_play("https://www.wnba.com/game/1029700001/playbyplay")
        assert result is True

    @patch('requests.get')
    def test_validate_play_by_play_no_script(self, mock_get, generator):
        """Test play-by-play validation when __NEXT_DATA__ script is missing."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = '<html><p>No script here</p></html>'
        mock_get.return_value = mock_response
        
        result = generator.validate_play_by_play("https://www.wnba.com/game/1029700001/playbyplay")
        assert result is False

    @patch('requests.get')
    def test_validate_play_by_play_request_error(self, mock_get, generator):
        """Test play-by-play validation with request error."""
        mock_get.side_effect = RequestException("Connection error")
        
        result = generator.validate_play_by_play("https://www.wnba.com/game/invalid/playbyplay")
        assert result is False

    # Game Data Extraction Tests
    @patch('requests.get')
    def test_get_game_data(self, mock_get, generator):
        """Test getting game data from URL."""
        test_data = {"props": {"pageProps": {"gameId": "1029700001", "teams": ["NYL", "PHX"]}}}
        html_content = f'<html><script id="__NEXT_DATA__">{json.dumps(test_data)}</script></html>'
        
        mock_response = Mock()
        mock_response.text = html_content
        mock_get.return_value = mock_response
        
        result = generator.get_game_data("https://www.wnba.com/game/1029700001/playbyplay")
        
        assert result == test_data["props"]["pageProps"]
        assert result["gameId"] == "1029700001"

    @patch('builtins.open', new_callable=mock_open)
    @patch.object(GameURLGenerator, 'get_game_data')
    def test_save_game_data(self, mock_get_game_data, mock_file, generator):
        """Test saving game data to file."""
        test_data = {"gameId": "1029700001", "teams": ["NYL", "PHX"]}
        mock_get_game_data.return_value = test_data
        
        generator.save_game_data("https://www.wnba.com/game/1029700001/playbyplay", "test.json")
        
        mock_file.assert_called_once_with("test.json", "w")
        mock_file().write.assert_called()
        # Verify JSON was written (json.dump calls write multiple times)
        written_content = ''.join(call[0][0] for call in mock_file().write.call_args_list)
        assert "1029700001" in written_content

    # Edge Cases and Error Handling
    def test_generate_regular_season_ids_nonexistent_season(self, generator):
        """Test generating IDs for a season not in the DataFrame."""
        with pytest.raises(IndexError):
            generator.generate_regular_season_ids(1990)

    def test_generate_playoff_ids_nonexistent_season(self, generator):
        """Test generating playoff IDs for a season not in the DataFrame."""
        with pytest.raises(IndexError):
            generator.generate_playoff_ids(1990)

    def test_base_url_constant(self, generator):
        """Test that BASE_URL constant is correct."""
        assert generator.BASE_URL == "https://www.wnba.com"

    def test_csv_file_constants(self, generator):
        """Test CSV file path constants."""
        # The file paths are now absolute paths, so check they end with the expected filenames
        assert generator.GAMES_REGULAR_FP.endswith("wnba-games-regular.csv")
        assert generator.GAMES_PLAYOFF_FP.endswith("wnba-games-playoff.csv")

    # Integration Tests
    def test_id_format_consistency(self, generator):
        """Test that generated IDs have consistent format."""
        regular_ids = generator.generate_regular_season_ids(1997)
        playoff_ids = generator.generate_playoff_ids(1997)
        
        # All IDs should be strings
        assert all(isinstance(game_id, str) for game_id in regular_ids)
        assert all(isinstance(game_id, str) for game_id in playoff_ids)
        
        # All IDs should start with the same prefix for the same season
        assert all(game_id.startswith("10297") for game_id in regular_ids)
        assert all(game_id.startswith("10297") for game_id in playoff_ids)

    def test_generated_urls_format(self, generator):
        """Test that all generated URLs have correct format."""
        urls = generator.generate_regular_season_game_urls(1997)
        
        for url in urls[:5]:  # Test first 5 URLs
            assert url.startswith("https://www.wnba.com/game/")
            assert url.endswith("/playbyplay")
            assert len(url.split('/')) == 6  # Expected URL structure

    @pytest.mark.parametrize("season,expected_prefix", [
        (1997, "10297"),
        (2020, "10320"), 
        (2025, "10325")
    ])
    def test_id_prefix_by_season(self, generator, season, expected_prefix):
        """Test that correct ID prefixes are used for different seasons."""
        game_ids = generator.generate_regular_season_ids(season)
        assert all(game_id.startswith(expected_prefix) for game_id in game_ids)


# Performance and Integration Tests (marked as slow)
class TestGameURLGeneratorPerformance:
    """Performance tests for GameURLGenerator."""

    @pytest.fixture
    def generator(self):
        """Create real generator instance for performance tests."""
        # Note: These tests would require actual CSV files
        # In practice, you'd mock or provide test CSV files
        with patch('pandas.read_csv') as mock_read_csv:
            # Mock with minimal data for performance tests
            mock_regular_df = pd.DataFrame({
                'season': [2025], 'total_regular_games': [286], 'id_prefix': [10325]
            })
            mock_playoff_df = pd.DataFrame({
                'season': [2025], 'best_of': ["3,5,7"], 'id_prefix': [10325],
                'total_games': [None], 'num_series': ["4,2,1"]
            })
            mock_read_csv.side_effect = [mock_regular_df, mock_playoff_df]
            with patch.object(GameURLGenerator, 'GAMES_REGULAR_FP', 'mocked_regular.csv'), \
                 patch.object(GameURLGenerator, 'GAMES_PLAYOFF_FP', 'mocked_playoff.csv'):
                return GameURLGenerator()

    @pytest.mark.slow
    def test_large_season_generation_performance(self, generator):
        """Test performance with large seasons."""
        import time
        start = time.time()

        # This would test against real data
        # game_ids = generator.generate_regular_season_ids(2025)

        end = time.time()
        # assert end - start < 1.0  # Should complete quickly
        # assert len(game_ids) > 0

    @pytest.mark.integration 
    def test_csv_files_exist(self):
        """Integration test to verify CSV files exist."""
        import os
        # CSV files are in the src/scrapers directory
        assert os.path.exists("src/scrapers/wnba-games-regular.csv")
        assert os.path.exists("src/scrapers/wnba-games-playoff.csv")