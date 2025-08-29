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

# Additional markers for table population tests
def pytest_configure(config):
    """Configure pytest with custom markers for table population"""
    config.addinivalue_line("markers", "postgres: Tests requiring PostgreSQL database")

# Sample data fixtures for GameURLGenerator
@pytest.fixture
def mock_regular_season_data():
    """Mock data for regular season CSV."""
    return pd.DataFrame({
        'season': [1997, 1998, 2020, 2025],
        'total_regular_games': [115, 120, 132, 286],
        'id_prefix': [10297, 10298, 10220, 10225]
    })

@pytest.fixture 
def mock_playoff_data():
    """Mock data for playoff CSV."""
    return pd.DataFrame({
        'season': [1997, 1998, 2001, 2002, 2025],
        'best_of': ["3", "3", "5", "3,5,7", "3,5,7"],
        'id_prefix': [10297, 10298, 10301, 10302, 10225],
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
        'id_prefix': [10297, 10225]
    })
    regular_df.to_csv(regular_season_csv, index=False)
    
    # Create playoff CSV
    playoff_df = pd.DataFrame({
        'season': [1997, 2025],
        'best_of': ["3", "3,5,7"],
        'id_prefix': [10297, 10225],
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

# Database-related fixtures for database module tests
@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    from unittest.mock import Mock
    connection = Mock()
    connection.get_session.return_value = Mock()
    connection.get_engine.return_value = Mock()
    return connection

@pytest.fixture
def mock_database_service():
    """Mock DatabaseService for testing."""
    from unittest.mock import Mock
    service = Mock()
    service.game_data = Mock()
    service.scraping_session = Mock()
    return service

@pytest.fixture
def sample_raw_game_data():
    """Sample RawGameData model instance for testing."""
    from src.database.models import RawGameData
    return RawGameData(
        game_id=1029700001,
        season=1997,
        game_type="regular",
        game_url="https://www.wnba.com/game/phx-vs-nyl-1029700001",
        game_data={
            "gameId": "1029700001",
            "homeTeam": "NYL",
            "awayTeam": "PHX",
            "gameDate": "1997-06-21",
            "playByPlay": [
                {"period": 1, "time": "10:00", "description": "Game Start"}
            ]
        }
    )

@pytest.fixture
def sample_scraping_session():
    """Sample ScrapingSession model instance for testing."""
    from src.database.models import ScrapingSession
    return ScrapingSession(
        session_name="Test Scraping Session",
        status="running",
        games_scraped=5,
        errors_count=1
    )

@pytest.fixture
def sample_database_version():
    """Sample DatabaseVersion model instance for testing."""
    from src.database.models import DatabaseVersion
    return DatabaseVersion(
        version="1.0.0",
        description="Initial database schema"
    )

@pytest.fixture
def in_memory_database():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from tests.test_models_sqlite import SqliteTestBase
    
    # Use SQLite with JSON support (not JSONB)
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Create tables with SQLite-compatible schema
    SqliteTestBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()

@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for database testing."""
    import os
    return {
        'DB_NAME': 'test_wnba',
        'DB_USER': 'test_user', 
        'DB_PASSWORD': 'test_password',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432'
    }

# Set up logging for tests
@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    # Suppress some noisy loggers during testing
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('alembic').setLevel(logging.WARNING)


# PostgreSQL test fixtures for table population
@pytest.fixture
def postgresql_url():
    """Get PostgreSQL URL from environment or skip tests"""
    import os
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip("PostgreSQL tests require TEST_DATABASE_URL environment variable")
    return url


@pytest.fixture
def postgresql_engine(postgresql_url):
    """Create PostgreSQL engine for testing"""
    from sqlalchemy import create_engine
    from src.database.models import Base
    
    engine = create_engine(postgresql_url, echo=False)
    
    # Create all tables including JSONB ones
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Clean up - drop all tables
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def postgresql_session(postgresql_engine):
    """Create PostgreSQL session for testing"""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=postgresql_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def sample_game_json():
    """Load sample game JSON data (session-scoped for performance)"""
    import json
    from pathlib import Path
    
    test_data_dir = Path(__file__).parent / "test_data"
    sample_file = test_data_dir / "raw_game_1022400005.json"
    
    with open(sample_file, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def all_sample_games():
    """Load all sample game files"""
    import json
    from pathlib import Path
    
    test_data_dir = Path(__file__).parent / "test_data"
    games = []
    
    for json_file in test_data_dir.glob("raw_game_*.json"):
        with open(json_file, 'r') as f:
            games.append(json.load(f))
    
    return games