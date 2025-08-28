# WNBA Scraping Tests

This directory contains comprehensive tests for the WNBA scraping system, focusing on data extraction, URL generation, and scraper management.

## Test Structure

### Core Test Files

- **`test_game_url_generator.py`** - Tests for WNBA game URL generation and validation
- **`test_raw_data_extractor.py`** - Tests for JSON data extraction from WNBA.com pages  
- **`test_raw_data_scraper.py`** - Tests for web scraping functionality
- **`test_scraper_manager.py`** - Core scraper manager functionality tests
- **`test_scraper_manager_edge_cases.py`** - Error handling and edge case tests

### Configuration Files

- **`conftest.py`** - Pytest configuration and shared test fixtures
- **`test_runner.py`** - Custom test runner for development workflows
- **`__init__.py`** - Python package marker

## Running Tests

### Quick Development Testing
```bash
# Run essential tests for rapid feedback
python tests/test_runner.py quick
```

### Edge Case Testing  
```bash
# Run error handling and edge case tests
python tests/test_runner.py edge
```

### Full Test Suite
```bash
# Run complete test suite with coverage
python tests/test_runner.py full
```

### Custom Test Runs
```bash
# Run specific test
python tests/test_runner.py custom tests/test_scraper_manager.py::TestScraperManager::test_scrape_season

# Standard pytest commands (remember to activate venv first)
source venv/bin/activate
pytest tests/test_scraper_manager.py -v --no-cov
pytest tests/ -m "not slow" -v  # Skip slow tests
```

## Test Coverage

### Scraper Manager Tests (`test_scraper_manager.py`)
- ✅ **Initialization**: ScraperManager setup and dependency injection
- ✅ **Session Management**: Start, update, and complete scraping sessions
- ✅ **URL Generation**: Season and game type URL generation
- ✅ **Game Scraping**: Single game scraping workflows
- ✅ **Bulk Operations**: Season and multi-season scraping
- ✅ **CLI Interface**: All command-line commands and argument parsing
- ✅ **Integration Testing**: Real component integration with minimal mocking

### Edge Case Tests (`test_scraper_manager_edge_cases.py`)
- ✅ **Error Handling**: Database failures, network timeouts, invalid responses
- ✅ **Boundary Conditions**: Empty seasons, invalid limits, future seasons
- ✅ **Stress Testing**: Large season processing and memory usage (marked as slow)
- ✅ **Race Conditions**: Concurrency and resource management issues

### Data Processing Tests
- ✅ **URL Generation** (`test_game_url_generator.py`): WNBA URL patterns and validation
- ✅ **Data Extraction** (`test_raw_data_extractor.py`): JSON parsing from `#__NEXT_DATA__` scripts
- ✅ **Web Scraping** (`test_raw_data_scraper.py`): HTTP request handling and response processing

## Test Fixtures and Utilities

### Common Fixtures (from `conftest.py`)
```python
# Sample data fixtures
sample_game_urls          # Realistic WNBA game URLs
sample_game_ids           # Valid WNBA game ID patterns
sample_game_data          # Mock game data structures
mock_regular_season_data  # CSV data for regular season games
mock_playoff_data         # CSV data for playoff games

# HTTP mocking
mock_successful_request   # Mock successful HTTP responses
mock_failed_request       # Mock failed HTTP responses
mock_html_response        # Mock WNBA.com HTML with __NEXT_DATA__

# Environment setup
setup_test_environment    # Clean test environment (auto-used)
setup_logging            # Test logging configuration (auto-used)
```

### Mock Strategy
- **External Dependencies**: HTTP requests and database connections are mocked
- **Time Operations**: `time.sleep()` calls are mocked for speed
- **File System**: CSV file reading uses temporary test files
- **Real Components**: URL generation logic, statistics, and parsing remain unmocked

## Development Guidelines

### Adding New Tests

#### Unit Test Pattern
```python
@patch('src.scripts.scraper_manager.DatabaseService')
def test_new_functionality(self, mock_db_service, mock_scraper_manager):
    # Setup mocks
    mock_db_service.return_value.__enter__.return_value.method.return_value = expected
    
    # Execute
    result = mock_scraper_manager.some_method()
    
    # Assert
    assert result == expected_result
    mock_db_service.assert_called_with(expected_args)
```

#### Edge Case Pattern
```python
def test_error_condition(self, mock_scraper_manager):
    with patch.object(mock_scraper_manager, 'method', side_effect=Exception("Error")):
        result = mock_scraper_manager.calling_method()
        # Verify graceful error handling
        assert result is not None
```

### Test Organization
- **Unit Tests**: Individual method testing with comprehensive mocking
- **Integration Tests**: Component interaction testing with minimal mocking
- **CLI Tests**: Command-line interface and argument validation
- **Slow Tests**: Performance tests marked with `@pytest.mark.slow`

### Performance Considerations
- All external dependencies are mocked for speed
- `time.sleep()` calls are patched to avoid delays
- Large datasets are simulated rather than created
- Complete test suite runs in under 10 seconds

## Test Data

### WNBA-Specific Patterns
- **Game IDs**: Follow WNBA format (e.g., `1029700001`, `1032500286`)
- **Season Range**: 1997-2025 (WNBA history)  
- **URL Structure**: `wnba.com/game/{away_team}-vs-{home_team}-{game_id}`
- **Team Codes**: Valid WNBA team abbreviations

### Sample Data Sources
Tests use realistic data patterns matching actual WNBA structures:
- Regular season game counts per year
- Playoff series formats (best-of-3, best-of-5, best-of-7)
- ID prefixes for different seasons
- Realistic game data JSON structures

## Debugging and Troubleshooting

### Common Issues
1. **Import Errors**: `conftest.py` handles Python path setup automatically
2. **Mock Conflicts**: Check mock setup doesn't interfere with real components
3. **Coverage Failures**: Use `--no-cov` during development

### Debugging Commands
```bash
# Run single test with full output
pytest tests/test_scraper_manager.py::test_name -v -s --tb=long

# Run with debugger
pytest tests/test_scraper_manager.py::test_name --pdb

# Show all print statements
pytest tests/test_scraper_manager.py::test_name -s
```

## Continuous Integration

Tests are designed for CI environments with:
- No external dependencies (comprehensive mocking)
- Deterministic results across environments
- Clear failure reporting and error messages
- Minimal resource usage and fast execution
- Proper cleanup and test isolation

Each test is independent with no shared state, ensuring reliable parallel execution and consistent results.