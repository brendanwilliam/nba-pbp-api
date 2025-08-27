# tests/conftest.py
import sys
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import date

# Add the src directory to Python path so imports work
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Markers are now configured in pytest.ini

# Sample data fixtures for GameURLGenerator
@pytest.fixture
def mock_regular_season_data():
    """Mock data for regular season CSV."""
    return pd.DataFrame({
        'season': [1997, 1998, 2020, 2025],
        'total_regular_games': [115, 120, 72, 286],
        'id_prefix': [10297, 10298, 10320, 10325]
    })

@pytest.fixture 
def mock_playoff_data():
    """Mock data for playoff CSV."""
    return pd.DataFrame({
        'season': [1997, 1998, 2001, 2002, 2025],
        'best_of': ["3", "3", "5", "3,5,7", "3,5,7"],
        'id_prefix': [10297, 10298, 10301, 10302, 10325],
        'total_games': [3, 6, 15, None, None],
        'num_series': [None, None, None, "4,2,1", "4,2,1"]
    })

@pytest.fixture
def sample_game_urls():
    """Sample game URLs for testing."""
    return [
        "https://www.wnba.com/game/1029700001/playbyplay",
        "https://www.wnba.com/game/1029700050/playbyplay", 
        "https://www.wnba.com/game/1032500100/playbyplay"
    ]

@pytest.fixture
def sample_game_ids():
    """Sample game IDs for testing."""
    return ["1029700001", "1029700050", "1032500100", "1032500286"]

@pytest.fixture
def mock_html_response():
    """Mock HTML response with __NEXT_DATA__ script."""
    return '''
    <html>
        <head><title>WNBA Game</title></head>
        <body>
            <script id="__NEXT_DATA__" type="application/json">
            {
                "props": {
                    "pageProps": {
                        "gameId": "1029700001",
                        "homeTeam": "NYL",
                        "awayTeam": "PHX",
                        "gameDate": "1997-06-21",
                        "playByPlay": [
                            {"period": 1, "time": "10:00", "description": "Game Start"}
                        ]
                    }
                }
            }
            </script>
        </body>
    </html>
    '''

@pytest.fixture
def mock_html_response_no_script():
    """Mock HTML response without __NEXT_DATA__ script."""
    return '''
    <html>
        <head><title>WNBA Game</title></head>
        <body>
            <p>Game not found or no play-by-play data available</p>
        </body>
    </html>
    '''

@pytest.fixture
def sample_game_data():
    """Sample game data that would be extracted from __NEXT_DATA__."""
    return {
        "gameId": "1029700001",
        "homeTeam": "NYL", 
        "awayTeam": "PHX",
        "gameDate": "1997-06-21",
        "playByPlay": [
            {"period": 1, "time": "10:00", "description": "Game Start"},
            {"period": 1, "time": "9:45", "description": "Jump ball"},
            {"period": 1, "time": "9:30", "description": "Made shot"}
        ]
    }

@pytest.fixture
def temp_csv_files(tmp_path):
    """Create temporary CSV files for testing."""
    regular_season_csv = tmp_path / "wnba-games-regular.csv"
    playoff_csv = tmp_path / "wnba-games-playoff.csv"
    
    # Create regular season CSV
    regular_df = pd.DataFrame({
        'season': [1997, 2025],
        'total_regular_games': [115, 286], 
        'id_prefix': [10297, 10325]
    })
    regular_df.to_csv(regular_season_csv, index=False)
    
    # Create playoff CSV
    playoff_df = pd.DataFrame({
        'season': [1997, 2025],
        'best_of': ["3", "3,5,7"],
        'id_prefix': [10297, 10325],
        'total_games': [3, None],
        'num_series': [None, "4,2,1"]
    })
    playoff_df.to_csv(playoff_csv, index=False)
    
    return {
        'regular': regular_season_csv,
        'playoff': playoff_csv
    }

# Auto-use fixtures for common setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically run before each test to set up clean environment."""
    # You can set environment variables here if needed
    import os
    original_env = os.environ.copy()
    
    # Set any test-specific environment variables
    os.environ['TESTING'] = 'true'
    
    yield  # This is where the test runs
    
    # Cleanup after test
    os.environ.clear()
    os.environ.update(original_env)

# Helper functions that can be used across tests
@pytest.fixture
def mock_successful_request():
    """Mock a successful HTTP request."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    return mock_response

@pytest.fixture 
def mock_failed_request():
    """Mock a failed HTTP request."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 404")
    mock_response.status_code = 404
    return mock_response

# Database-related fixtures (if you need them for other tests)
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    return session

# Set up logging for tests
@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    # Suppress some noisy loggers during testing
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)