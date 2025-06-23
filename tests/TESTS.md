# Test Suite Documentation

This document provides comprehensive documentation for the NBA Play-by-Play API test suite.

## Overview

The test suite validates all core functionality of the NBA data scraping and processing system, including JSON parsing, database operations, queue management, and mass scraping capabilities.

## Test Structure

```
tests/
├── TESTS.md                    # This documentation
├── json_parser.py             # Shared JSON parsing utilities
├── test_json_parser.py        # JSON parsing validation tests
├── test_multiple_games.py     # Multi-game consistency tests
├── test_queue_offline.py      # Queue operations tests (no network)
├── test_mass_scraper.py       # Mass scraper system tests
├── test_december_2024.py      # Legacy December 2024 tests
├── test_scrapers.py           # Legacy scraper tests
├── test_systematic_scraping.py # Legacy systematic scraping tests
├── data/                      # Test data files (58 NBA game JSON files)
└── reports/                   # Test reports and documentation
```

## Test Modules

### 1. JSON Parser Tests (`test_json_parser.py`)

**Purpose**: Validates JSON parsing for enhanced database schema implementation.

**Key Test Cases**:
- `test_get_sample_game()` - Database connection and game retrieval
- `test_parse_game_basic_info()` - Basic game information extraction
- `test_parse_teams()` - Team data parsing and validation
- `test_parse_arena()` - Arena information extraction
- `test_parse_periods()` - Period scores and game flow data
- `test_count_player_stats()` - Player statistics counting
- `test_count_play_events()` - Play-by-play event enumeration
- `test_multiple_games_consistency()` - Cross-game parsing consistency

**Usage**:
```bash
# Run all JSON parser tests
python -m pytest tests/test_json_parser.py -v

# Run specific test
python -m pytest tests/test_json_parser.py::TestJSONParser::test_parse_teams -v
```

### 2. Multiple Games Tests (`test_multiple_games.py`)

**Purpose**: Validates parsing consistency across multiple games and seasons.

**Key Test Cases**:
- `test_parsing_consistency_five_games()` - 5-game batch consistency
- `test_parsing_consistency_ten_games()` - 10-game batch consistency
- `test_data_quality_validation()` - Data quality and integrity checks

**Interactive Mode**:
```bash
# Test with interactive output
cd tests && python test_multiple_games.py --interactive 5

# Test specific number of games
cd tests && python test_multiple_games.py --interactive 10
```

**Usage**:
```bash
# Run all multiple games tests
python -m pytest tests/test_multiple_games.py -v

# Run with specific batch size validation
python -m pytest tests/test_multiple_games.py::TestMultipleGames::test_parsing_consistency_five_games -v
```

### 3. Queue Offline Tests (`test_queue_offline.py`)

**Purpose**: Tests queue building and management functionality without network calls.

**Test Categories**:

#### Team Mapping Tests
- `test_current_team_count()` - Validates 30 current NBA teams
- `test_historical_teams()` - Tests historical team lookups (relocations, name changes)

#### URL Generation Tests  
- `test_game_url_info_structure()` - GameURLInfo data structure validation
- `test_url_generation()` - URL generation algorithm testing

#### Database Schema Tests
- `test_game_url_queue_table_exists()` - Queue table existence validation
- `test_game_url_queue_schema()` - Queue table structure validation
- `test_raw_game_data_table_exists()` - Raw data table validation

#### Integration Tests
- `test_full_offline_workflow()` - End-to-end offline workflow validation

**Interactive Mode**:
```bash
# Run with detailed output
cd tests && python test_queue_offline.py --interactive
```

**Usage**:
```bash
# Run all queue tests
python -m pytest tests/test_queue_offline.py -v

# Run specific category
python -m pytest tests/test_queue_offline.py::TestTeamMapping -v
```

### 4. Mass Scraper Tests (`test_mass_scraper.py`)

**Purpose**: Validates the mass scraping system components.

**Test Categories**:

#### Queue Operations Tests
- Async queue initialization and statistics
- Batch retrieval and status updates
- Game completion and failure handling

#### Data Extractor Tests
- URL validation and format checking
- Extraction result enumeration
- Basic extractor functionality

#### Rate Limiter Tests
- Request timing and throttling
- Burst limit enforcement
- Rate limit response handling
- Statistics collection

#### Integration Tests
- Component integration testing
- End-to-end workflow validation
- Error handling and recovery

**Interactive Mode**:
```bash
# Run with detailed async output
cd tests && python test_mass_scraper.py --interactive
```

**Usage**:
```bash
# Run basic import tests
python -m pytest tests/test_mass_scraper.py::TestMassScraperSuite::test_all_imports_successful -v

# Run specific component tests
python -m pytest tests/test_mass_scraper.py::TestRateLimiter -v
```

## Shared Utilities

### JSON Parser Module (`json_parser.py`)

**Purpose**: Provides shared JSON parsing functionality for test modules.

**Key Classes**:
- `JSONGameParser` - Main parser class with database connectivity

**Key Methods**:
- `get_sample_game(game_id=None)` - Retrieve game data from database
- `parse_game_basic_info(game_data)` - Extract basic game information
- `parse_teams(game_data)` - Extract home/away team data
- `parse_periods(game_data)` - Extract period scores
- `parse_arena(game_data)` - Extract arena information
- `count_play_events(game_data)` - Count play-by-play events
- `count_player_stats(game_data)` - Count player statistics
- `close()` - Clean up database session

## Test Data

### Database Requirements

Tests require a PostgreSQL database with the following tables:
- `raw_game_data` - Contains scraped JSON game data
- `game_url_queue` - Contains game URLs for scraping
- Other schema tables as defined in `src/database/enhanced_schema.sql`

### Sample Data (`tests/data/`)

Contains 58 NBA game JSON files spanning multiple seasons (1996-2024):
- Regular season games (`*_reg_*`)
- Playoff games (`*_pla_*`)
- Multiple eras and team configurations
- Various game states and data completeness levels

## Running Tests

### Prerequisites

1. **Virtual Environment**: Activate the project virtual environment
2. **Database**: PostgreSQL instance with scraped game data
3. **Dependencies**: Install test dependencies via `requirements.txt`

### Basic Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run all moved test modules
python -m pytest tests/test_json_parser.py tests/test_multiple_games.py tests/test_queue_offline.py -v

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_json_parser.py -v

# Run specific test method
python -m pytest tests/test_json_parser.py::TestJSONParser::test_parse_teams -v
```

### Interactive Testing

Some tests support interactive mode for detailed output:

```bash
# JSON parsing with detailed output
cd tests && python test_multiple_games.py --interactive 5

# Queue operations with detailed output  
cd tests && python test_queue_offline.py --interactive

# Mass scraper with detailed async output
cd tests && python test_mass_scraper.py --interactive
```

### Continuous Integration

For CI/CD pipelines:

```bash
# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run tests with XML output
python -m pytest tests/ --junitxml=test-results.xml

# Run only fast tests (exclude network-dependent)
python -m pytest tests/test_json_parser.py tests/test_queue_offline.py -v
```

## Test Categories

### Unit Tests
- Individual function and method validation
- Database schema validation
- Data structure testing
- Algorithm correctness

### Integration Tests  
- Multi-component workflows
- Database connectivity
- Queue operations
- Parsing consistency

### System Tests
- End-to-end functionality
- Performance validation
- Error handling
- Data quality assurance

## Expected Test Results

### Success Criteria
- **JSON Parser**: 8/8 tests passing
- **Multiple Games**: 3/3 tests passing  
- **Queue Offline**: 8/8 tests passing
- **Mass Scraper**: Variable (depends on async components)

### Performance Benchmarks
- JSON parsing: <1s per game
- Database queries: <100ms per query
- Batch operations: <5s for 10 games
- Queue operations: <50ms per operation

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check `DATABASE_URL` in `.env`
   - Ensure database contains required tables

2. **Import Errors**
   - Verify virtual environment is activated
   - Check Python path includes `src/` directory
   - Ensure all dependencies are installed

3. **Test Data Issues**
   - Verify `raw_game_data` table has content
   - Check game data format matches expected structure
   - Ensure test database is populated

4. **Async Test Failures**
   - Mass scraper tests may fail without proper async setup
   - Use pytest-asyncio for async test support
   - Check network connectivity for integration tests

### Debug Mode

```bash
# Run tests with verbose output
python -m pytest tests/ -v -s

# Run tests with detailed logging
python -m pytest tests/ -v --log-cli-level=DEBUG

# Run single test with debugging
python -m pytest tests/test_json_parser.py::TestJSONParser::test_parse_teams -v -s --pdb
```

## Contributing

### Adding New Tests

1. **Create test file** in `tests/` directory
2. **Follow naming convention**: `test_*.py`
3. **Import required modules**: Use proper path handling
4. **Inherit from unittest.TestCase**: Standard test structure
5. **Add documentation**: Include docstrings and comments
6. **Update this file**: Add documentation for new tests

### Test Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Use setUp/tearDown for resource management
3. **Assertions**: Use descriptive assertion messages
4. **Data**: Use test data that won't change
5. **Coverage**: Aim for high code coverage
6. **Performance**: Keep tests fast and efficient

## Future Enhancements

### Planned Additions
- Performance benchmarking tests
- Load testing for mass operations
- API endpoint testing (when implemented)
- Database migration testing
- Data validation stress tests
- Network resilience testing

### Test Infrastructure
- Automated test data generation
- Test database seeding scripts
- CI/CD pipeline integration
- Test result reporting dashboard
- Performance regression detection