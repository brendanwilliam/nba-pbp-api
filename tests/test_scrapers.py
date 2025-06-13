"""Tests for NBA.com scraping functionality."""

import json
import csv
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from pathlib import Path
from bs4 import BeautifulSoup

from src.scrapers.game_url_scraper import GameURLScraper
from src.scrapers.game_data_scraper import GameDataScraper


class TestGameURLScraper:
    """Tests for GameURLScraper."""
    
    def setup_method(self):
        """Set up test instance."""
        self.scraper = GameURLScraper(delay=0.1)
    
    @patch('src.scrapers.game_url_scraper.time.sleep')
    @patch('src.scrapers.game_url_scraper.requests.Session.get')
    def test_get_games_for_date_success(self, mock_get, mock_sleep):
        """Test successful game URL scraping."""
        # Mock response
        mock_response = Mock()
        mock_response.content = """
        <html>
            <body>
                <a href="/game/bos-vs-lal-0022400123">BOS vs LAL</a>
                <a href="/game/gsw-vs-mia-0022400124">GSW vs MIA</a>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test
        test_date = date(2024, 1, 15)
        games = self.scraper.get_games_for_date(test_date)
        
        # Assertions
        assert len(games) == 2
        assert games[0]['nba_game_id'] == '0022400123'
        assert games[0]['away_team_tricode'] == 'BOS'
        assert games[0]['home_team_tricode'] == 'LAL'
        assert games[1]['nba_game_id'] == '0022400124'
        assert games[1]['away_team_tricode'] == 'GSW'
        assert games[1]['home_team_tricode'] == 'MIA'
    
    def test_parse_game_url_valid(self):
        """Test parsing valid game URL."""
        test_date = date(2024, 1, 15)
        url = "/game/bos-vs-lal-0022400123"
        
        result = self.scraper._parse_game_url(url, test_date)
        
        assert result is not None
        assert result['nba_game_id'] == '0022400123'
        assert result['away_team_tricode'] == 'BOS'
        assert result['home_team_tricode'] == 'LAL'
        assert result['game_date'] == '2024-01-15'
        assert 'nba.com/game/bos-vs-lal-0022400123' in result['game_url']
    
    def test_parse_game_url_invalid(self):
        """Test parsing invalid game URL."""
        test_date = date(2024, 1, 15)
        url = "/invalid-url"
        
        result = self.scraper._parse_game_url(url, test_date)
        
        assert result is None
    
    @patch('src.scrapers.game_url_scraper.requests.Session.get')
    def test_get_games_for_date_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        test_date = date(2024, 1, 15)
        games = self.scraper.get_games_for_date(test_date)
        
        assert games == []


class TestGameDataScraper:
    """Tests for GameDataScraper."""
    
    def setup_method(self):
        """Set up test instance."""
        self.scraper = GameDataScraper(delay=0.1)
    
    def test_extract_next_data_success(self):
        """Test successful extraction of __NEXT_DATA__."""
        html_content = """
        <html>
            <head>
                <script id="__NEXT_DATA__">{"props": {"pageProps": {"game": {"gameId": "123"}}}}</script>
            </head>
        </html>
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = self.scraper._extract_next_data(soup)
        
        assert result is not None
        assert result['props']['pageProps']['game']['gameId'] == '123'
    
    def test_extract_next_data_missing_script(self):
        """Test extraction when __NEXT_DATA__ script is missing."""
        html_content = "<html><head></head></html>"
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = self.scraper._extract_next_data(soup)
        
        assert result is None
    
    def test_extract_next_data_invalid_json(self):
        """Test extraction with invalid JSON."""
        html_content = """
        <html>
            <head>
                <script id="__NEXT_DATA__">invalid json</script>
            </head>
        </html>
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = self.scraper._extract_next_data(soup)
        
        assert result is None
    
    def test_validate_game_data_valid(self):
        """Test validation of valid game data."""
        game_data = {
            'props': {
                'pageProps': {
                    'game': {
                        'gameId': '123',
                        'homeTeam': {'tricode': 'LAL'},
                        'awayTeam': {'tricode': 'BOS'}
                    }
                }
            }
        }
        
        result = self.scraper.validate_game_data(game_data)
        
        assert result is True
    
    def test_validate_game_data_invalid(self):
        """Test validation of invalid game data."""
        game_data = {'invalid': 'structure'}
        
        result = self.scraper.validate_game_data(game_data)
        
        assert result is False
    
    def test_extract_game_metadata_success(self):
        """Test successful extraction of game metadata."""
        game_data = {
            'props': {
                'pageProps': {
                    'game': {
                        'gameId': '123',
                        'gameTimeUTC': '2024-01-15T20:00:00Z',
                        'gameStatus': 3,
                        'homeTeam': {'tricode': 'LAL'},
                        'awayTeam': {'tricode': 'BOS'},
                        'period': 4
                    }
                }
            }
        }
        
        result = self.scraper.extract_game_metadata(game_data)
        
        assert result is not None
        assert result['gameId'] == '123'
        assert result['gameTimeUTC'] == '2024-01-15T20:00:00Z'
        assert result['gameStatus'] == 3
        assert result['period'] == 4
    
    @patch('src.scrapers.game_data_scraper.time.sleep')
    @patch('src.scrapers.game_data_scraper.requests.Session.get')
    def test_scrape_game_data_success(self, mock_get, mock_sleep):
        """Test successful game data scraping."""
        # Mock response
        mock_response = Mock()
        mock_response.content = """
        <html>
            <head>
                <script id="__NEXT_DATA__">{"props": {"pageProps": {"game": {"gameId": "123"}}}}</script>
            </head>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test
        result = self.scraper.scrape_game_data("https://nba.com/game/test")
        
        # Assertions
        assert result is not None
        assert result['props']['pageProps']['game']['gameId'] == '123'


class TestScrapingWithRealData:
    """Tests using real NBA game data for validation."""
    
    @classmethod
    def setup_class(cls):
        """Load test data from CSV."""
        test_data_path = Path(__file__).parent / "data" / "gameid_on_days.csv"
        cls.expected_games = {}
        
        with open(test_data_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                test_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                cls.expected_games[test_date] = int(row['num_games'])
    
    def setup_method(self):
        """Set up test instance."""
        self.scraper = GameURLScraper(delay=0.1)
    
    @pytest.mark.parametrize("test_date,expected_count", [
        (date(2025, 6, 11), 1),
        (date(2025, 4, 11), 15),
        (date(2009, 2, 27), 13),
        (date(2009, 2, 28), 7),
        (date(2009, 5, 15), 0),
        (date(1997, 6, 13), 1),
    ])
    def test_game_count_for_known_dates(self, test_date, expected_count):
        """Test that scraper finds expected number of games for known dates."""
        # This test will actually hit NBA.com, so we mark it as integration
        # In practice, you might want to run this sparingly or mock the responses
        pytest.skip("Integration test - requires actual NBA.com access")
        
        games = self.scraper.get_games_for_date(test_date)
        assert len(games) == expected_count, f"Expected {expected_count} games for {test_date}, got {len(games)}"
    
    @patch('src.scrapers.game_url_scraper.time.sleep')
    @patch('src.scrapers.game_url_scraper.requests.Session.get')
    def test_game_count_validation_with_mock(self, mock_get, mock_sleep):
        """Test game count validation using mocked responses that simulate expected counts."""
        
        def create_mock_response(num_games):
            """Create a mock HTML response with specified number of game links."""
            game_links = []
            team_codes = ['bos', 'lal', 'gsw', 'mia', 'nyk', 'chi', 'sas', 'hou', 'dal', 'phi', 'det', 'was', 'orl', 'atl', 'mem']
            
            for i in range(num_games):
                game_id = f"002240{str(i).zfill(4)}"
                away_team = team_codes[i % len(team_codes)]
                home_team = team_codes[(i + 1) % len(team_codes)]
                game_links.append(f'<a href="/game/{away_team}-vs-{home_team}-{game_id}">Game {i}</a>')
            
            html_content = f"""
            <html>
                <body>
                    {''.join(game_links)}
                </body>
            </html>
            """
            
            mock_response = Mock()
            mock_response.content = html_content
            mock_response.raise_for_status.return_value = None
            return mock_response
        
        # Test cases from CSV
        test_cases = [
            (date(2025, 6, 11), 1),
            (date(2025, 4, 11), 15),
            (date(2009, 2, 27), 13),
            (date(2009, 2, 28), 7),
            (date(2009, 5, 15), 0),
            (date(1997, 6, 13), 1),
        ]
        
        for test_date, expected_count in test_cases:
            mock_get.return_value = create_mock_response(expected_count)
            
            games = self.scraper.get_games_for_date(test_date)
            assert len(games) == expected_count, f"Expected {expected_count} games for {test_date}, got {len(games)}"
    
    def test_csv_data_loading(self):
        """Test that CSV test data is loaded correctly."""
        assert len(self.expected_games) == 6
        assert self.expected_games[date(2025, 6, 11)] == 1
        assert self.expected_games[date(2025, 4, 11)] == 15
        assert self.expected_games[date(2009, 2, 27)] == 13
        assert self.expected_games[date(2009, 2, 28)] == 7
        assert self.expected_games[date(2009, 5, 15)] == 0
        assert self.expected_games[date(1997, 6, 13)] == 1