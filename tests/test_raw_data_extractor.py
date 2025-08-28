# tests/test_raw_data_extractor.py
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup

from src.scrapers.raw_data_extractor import (
    RawDataExtractor, 
    ExtractionResult, 
    DataQuality,
    ExtractionMetadata
)


class TestRawDataExtractor:
    """Test cases for RawDataExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a RawDataExtractor instance for testing."""
        return RawDataExtractor(timeout=30)

    @pytest.fixture
    def custom_timeout_extractor(self):
        """Create a RawDataExtractor with custom timeout."""
        return RawDataExtractor(timeout=10)

    def test_init_default_timeout(self):
        """Test RawDataExtractor initialization with default timeout."""
        extractor = RawDataExtractor()
        assert extractor.timeout == 30
        assert "Mozilla/5.0" in extractor.user_agent

    def test_init_custom_timeout(self, custom_timeout_extractor):
        """Test RawDataExtractor initialization with custom timeout."""
        assert custom_timeout_extractor.timeout == 10

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_success(self, mock_get, extractor, mock_html_response):
        """Test successful game data extraction."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.content = mock_html_response.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/1029700001/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        # Verify results
        assert result == ExtractionResult.SUCCESS
        assert data is not None
        assert data["gameId"] == "1029700001"
        assert data["homeTeam"] == "NYL"
        assert data["awayTeam"] == "PHX"
        assert len(data["playByPlay"]) == 1

        # Verify metadata
        assert metadata is not None
        assert isinstance(metadata.extraction_time_ms, int)
        assert metadata.extraction_time_ms >= 0
        assert metadata.response_size_bytes > 0
        assert metadata.json_size_bytes > 0
        assert metadata.data_quality == DataQuality.COMPLETE
        assert metadata.user_agent_used == extractor.user_agent

        # Verify request was made with proper headers
        mock_get.assert_called_once_with(
            game_url,
            timeout=30,
            headers={'User-Agent': extractor.user_agent}
        )

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_no_script_tag(self, mock_get, extractor, mock_html_response_no_script):
        """Test extraction when __NEXT_DATA__ script tag is missing."""
        mock_response = Mock()
        mock_response.text = mock_html_response_no_script
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/invalid/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.NO_DATA
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_empty_pageprops(self, mock_get, extractor):
        """Test extraction when pageProps is empty."""
        html_with_empty_props = '''
        <html>
            <body>
                <script id="__NEXT_DATA__" type="application/json">
                {"props": {"pageProps": {}}}
                </script>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.text = html_with_empty_props
        mock_response.content = html_with_empty_props.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/empty/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        # The implementation treats empty pageProps as NO_DATA
        assert result == ExtractionResult.NO_DATA
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_no_pageprops(self, mock_get, extractor):
        """Test extraction when pageProps key is missing."""
        html_with_no_pageprops = '''
        <html>
            <body>
                <script id="__NEXT_DATA__" type="application/json">
                {"props": {}}
                </script>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.text = html_with_no_pageprops
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/noprops/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.NO_DATA
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_invalid_json(self, mock_get, extractor):
        """Test extraction with invalid JSON in script tag."""
        html_with_invalid_json = '''
        <html>
            <body>
                <script id="__NEXT_DATA__" type="application/json">
                {invalid json content}
                </script>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.text = html_with_invalid_json
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/invalid-json/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.INVALID_JSON
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_timeout(self, mock_get, extractor):
        """Test extraction with timeout error."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        game_url = "https://www.wnba.com/game/timeout/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.TIMEOUT
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_network_error(self, mock_get, extractor):
        """Test extraction with network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        game_url = "https://www.wnba.com/game/network-error/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.NETWORK_ERROR
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_http_error(self, mock_get, extractor):
        """Test extraction with HTTP error (404, 500, etc.)."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/http-error/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.NETWORK_ERROR
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_unexpected_error(self, mock_get, extractor):
        """Test extraction with unexpected error."""
        mock_get.side_effect = ValueError("Unexpected error")

        game_url = "https://www.wnba.com/game/unexpected-error/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.SERVER_ERROR
        assert data is None
        assert metadata is None

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_custom_timeout(self, mock_get, custom_timeout_extractor, mock_html_response):
        """Test that custom timeout is used in requests."""
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.content = mock_html_response.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/custom-timeout/playbyplay"
        custom_timeout_extractor.extract_game_data(game_url)

        # Verify custom timeout was used
        mock_get.assert_called_once_with(
            game_url,
            timeout=10,
            headers={'User-Agent': custom_timeout_extractor.user_agent}
        )

    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extract_game_data_large_response(self, mock_get, extractor):
        """Test extraction with large response containing comprehensive game data."""
        large_game_data = {
            "gameId": "1032500100",
            "homeTeam": "LAS",
            "awayTeam": "SEA",
            "gameDate": "2025-06-15",
            "playByPlay": [{"period": i, "time": f"{10-i%10}:00", "description": f"Play {i}"} for i in range(100)],
            "boxScore": {"home": {"score": 85}, "away": {"score": 78}},
            "teamStats": {"home": {"rebounds": 35}, "away": {"rebounds": 42}}
        }
        
        html_with_large_data = f'''
        <html>
            <body>
                <script id="__NEXT_DATA__" type="application/json">
                {{"props": {{"pageProps": {json.dumps(large_game_data)}}}}}
                </script>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.text = html_with_large_data
        mock_response.content = html_with_large_data.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/large-data/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.SUCCESS
        assert data == large_game_data
        assert len(data["playByPlay"]) == 100
        assert metadata.data_quality == DataQuality.COMPLETE
        assert metadata.json_size_bytes > 1000  # Should be substantial

    @patch('src.scrapers.raw_data_extractor.time.time')
    @patch('src.scrapers.raw_data_extractor.requests.get')
    def test_extraction_timing_metadata(self, mock_get, mock_time, extractor, mock_html_response):
        """Test that extraction timing is correctly calculated."""
        # Mock time.time() to return predictable values
        mock_time.side_effect = [1000.0, 1000.5]  # 500ms difference
        
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.content = mock_html_response.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_url = "https://www.wnba.com/game/timing-test/playbyplay"
        result, data, metadata = extractor.extract_game_data(game_url)

        assert result == ExtractionResult.SUCCESS
        assert metadata.extraction_time_ms == 500


class TestExtractionResultEnum:
    """Test cases for ExtractionResult enum."""

    def test_extraction_result_values(self):
        """Test that ExtractionResult enum has expected values."""
        assert ExtractionResult.SUCCESS.value == "success"
        assert ExtractionResult.NO_DATA.value == "no_data"
        assert ExtractionResult.INVALID_JSON.value == "invalid_json"
        assert ExtractionResult.NETWORK_ERROR.value == "network_error"
        assert ExtractionResult.TIMEOUT.value == "timeout"
        assert ExtractionResult.RATE_LIMITED.value == "rate_limited"
        assert ExtractionResult.SERVER_ERROR.value == "server_error"


class TestDataQualityEnum:
    """Test cases for DataQuality enum."""

    def test_data_quality_values(self):
        """Test that DataQuality enum has expected values."""
        assert DataQuality.COMPLETE.value == "complete"
        assert DataQuality.PARTIAL.value == "partial"
        assert DataQuality.EMPTY.value == "empty"


class TestExtractionMetadata:
    """Test cases for ExtractionMetadata dataclass."""

    def test_extraction_metadata_creation(self):
        """Test creating ExtractionMetadata instance."""
        metadata = ExtractionMetadata(
            extraction_time_ms=150,
            response_size_bytes=1024,
            json_size_bytes=512,
            data_quality=DataQuality.COMPLETE,
            user_agent_used="Mozilla/5.0 Test"
        )

        assert metadata.extraction_time_ms == 150
        assert metadata.response_size_bytes == 1024
        assert metadata.json_size_bytes == 512
        assert metadata.data_quality == DataQuality.COMPLETE
        assert metadata.user_agent_used == "Mozilla/5.0 Test"

    def test_extraction_metadata_fields(self):
        """Test that ExtractionMetadata has all expected fields."""
        metadata = ExtractionMetadata(
            extraction_time_ms=100,
            response_size_bytes=2048,
            json_size_bytes=1024,
            data_quality=DataQuality.PARTIAL,
            user_agent_used="Test Agent"
        )

        # Verify all fields exist
        assert hasattr(metadata, 'extraction_time_ms')
        assert hasattr(metadata, 'response_size_bytes')
        assert hasattr(metadata, 'json_size_bytes')
        assert hasattr(metadata, 'data_quality')
        assert hasattr(metadata, 'user_agent_used')