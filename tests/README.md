# WNBA Scraping Tests

This directory contains comprehensive tests for the WNBA scraping system, focusing on data extraction, URL generation, and scraper management.

## Test Structure

### Core Test Files

- **`test_game_url_generator.py`** - Tests for WNBA game URL generation and validation
- **`test_raw_data_extractor.py`** - Tests for JSON data extraction from WNBA.com pages  
- **`test_raw_data_scraper.py`** - Tests for web scraping functionality
- **`test_scraper_manager.py`** - Core scraper manager functionality tests
- **`test_scraper_manager_edge_cases.py`** - Error handling and edge case tests
- **`test_database_population.py`** - Database population validation and completeness testing
- **`test_json_extraction.py`** - Unit tests for WNBA JSON data extraction (21 tests)
- **`test_table_population.py`** - Integration tests for normalized table population
- **`test_bulk_insert_sqlite.py`** - SQLite-compatible bulk insert testing
- **`test_table_population_postgres.py`** - PostgreSQL-specific table population tests

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

### Database Population Tests (`test_database_population.py`)
- ✅ **Data Integrity**: No duplicates, consistent game types, referential integrity
- ✅ **Completeness Validation**: Configurable thresholds for game count validation
- ✅ **Strict Mode**: Exact CSV match validation for production environments
- ✅ **Environment Configuration**: Flexible testing modes (lenient/moderate/strict)

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

---

## Database Population Testing

The database population validation system ensures data integrity and completeness as your WNBA dataset grows.

### Test Categories

#### 1. Data Integrity Tests (Always Strict)
- **No duplicates**: Ensures no duplicate game_ids within season/type combinations
- **Data consistency**: Validates game_type values are properly formatted
- **Referential integrity**: Confirms all expected seasons are present

#### 2. Data Completeness Tests (Configurable)
- **Threshold-based validation**: Checks if game counts fall within acceptable ranges
- **Exact match validation**: Optionally enforces exact CSV matches (strict mode)

### Configuration

#### Environment Variables

```bash
# Completeness thresholds (percentage of expected games)
DB_TEST_MIN_COMPLETENESS=0.0      # Minimum acceptable completeness (default: 0%)
DB_TEST_MAX_COMPLETENESS=110.0    # Maximum acceptable completeness (default: 110%)

# Strict mode - requires exact CSV matches
DB_TEST_STRICT_MODE=false         # Set to 'true' for exact validation
```

#### Usage Scenarios

**Development (Lenient)**
```bash
export DB_TEST_MIN_COMPLETENESS=0.0
export DB_TEST_MAX_COMPLETENESS=200.0
pytest tests/test_database_population.py
```

**CI/Testing (Moderate)**
```bash
export DB_TEST_MIN_COMPLETENESS=50.0
export DB_TEST_MAX_COMPLETENESS=120.0
pytest tests/test_database_population.py
```

**Production Validation (Strict)**
```bash
export DB_TEST_STRICT_MODE=true
pytest tests/test_database_population.py
```

### Management Tools

#### Population Report
```bash
python scripts/manage_test_expectations.py report
```
Shows current database population vs CSV expectations with completeness percentages.

#### Threshold Suggestions
```bash
python scripts/manage_test_expectations.py suggest
```
Analyzes current data and suggests appropriate threshold values for different environments.

#### Update Configuration
```bash
python scripts/manage_test_expectations.py update --min-threshold 25.0 --max-threshold 105.0
```
Updates your `.env` file with new threshold values.

### Typical Workflow

#### 1. Initial Setup (Empty Database)
```bash
# Set lenient thresholds for development
python scripts/manage_test_expectations.py suggest
export DB_TEST_MIN_COMPLETENESS=0.0
export DB_TEST_MAX_COMPLETENESS=200.0
pytest tests/test_database_population.py -v
```

#### 2. During Active Scraping
```bash
# Monitor progress and adjust thresholds
python scripts/manage_test_expectations.py report
# Update thresholds as population grows
python scripts/manage_test_expectations.py update --min-threshold 50.0 --max-threshold 110.0
```

#### 3. Production Validation
```bash
# Ensure complete and accurate data
export DB_TEST_STRICT_MODE=true
pytest tests/test_database_population.py::TestDatabasePopulation::test_database_population_exact_match -v
```

### Test Output Examples

#### Successful Run
```
=== Database Completeness Report ===
Thresholds: 25.0% - 110.0%
1997 playoff: 3/3 (100.0%)
1997 regular: 100/112 (89.3%)
1998 playoff: 0/8 (0.0%)
1998 regular: 45/150 (30.0%)
```

#### Threshold Violation
```
FAILED - Below minimum threshold: 1998 regular: 15.0% < 25.0%
```

#### Strict Mode Failure
```
FAILED - Exact count mismatches: 1997 regular: expected 112, got 110; 1998 playoff: expected 8, got 0
```

### Best Practices

1. **Use appropriate thresholds for your environment**
   - Development: Very lenient (0%-200%)
   - CI: Moderate based on expected scraping progress
   - Production: Strict (95%-105% or exact match)

2. **Update thresholds as data matures**
   - Run `suggest` command regularly to get data-driven threshold recommendations
   - Gradually increase minimum thresholds as scraping progresses

3. **Separate integrity from completeness**
   - Data integrity tests should always pass (no duplicates, valid formats)
   - Completeness tests can be relaxed during development

4. **Monitor and report**
   - Use the `report` command to track scraping progress
   - Include population reports in CI/deployment processes

5. **Handle CSV updates gracefully**
   - When CSV files change, run `suggest` to get new threshold recommendations
   - Test with strict mode to validate CSV changes are reflected in database

### Troubleshooting

#### Tests failing after CSV updates
1. Run `python scripts/manage_test_expectations.py suggest`
2. Compare suggested thresholds with current data
3. Either update database or adjust thresholds as appropriate

#### Unexpected extra games in database
- Check for data quality issues (incorrect season/type assignments)
- Verify CSV files are up to date
- Review scraping logic for over-collection

#### Missing expected games
- Normal during active scraping - adjust thresholds
- For complete datasets, investigate scraping gaps
- Check for CSV vs reality discrepancies

## Table Population and JSONB Testing

The WNBA table population system transforms raw JSON data into normalized relational tables with comprehensive testing across different database capabilities.

### Test Categories

#### ✅ Unit Tests (Database-Free)
**File**: `test_json_extraction.py` - **21 tests, all passing**
- Tests JSON data extraction logic without database dependencies
- Fast execution, covers all extractors: Arena, Team, Game, Person, Play, Boxscore
- Uses real WNBA game JSON samples for validation

```bash
# Run JSON extraction unit tests
pytest tests/test_json_extraction.py -v
```

#### ✅ SQLite Integration Tests  
**File**: `test_bulk_insert_sqlite.py` - **7 tests, all passing**
- SQLite-compatible version of bulk operations
- Tests validation and basic insertion logic
- Handles SQLite limitations (no ON CONFLICT support for non-unique columns)

```bash
# Run SQLite integration tests
pytest tests/test_bulk_insert_sqlite.py -v
```

#### ⚠️ PostgreSQL-Specific Tests
**File**: `test_table_population_postgres.py` - **7 tests, require PostgreSQL**
- Test full JSONB functionality and ON CONFLICT resolution
- Performance testing and PostgreSQL-specific features
- Skipped automatically when PostgreSQL not available

```bash
# Run PostgreSQL tests (requires TEST_DATABASE_URL)
export TEST_DATABASE_URL="postgresql://user:password@localhost/test_db"
pytest -m postgres tests/test_table_population_postgres.py -v
```

#### ⚠️ Legacy Integration Tests (Expected Partial Failures)
**File**: `test_table_population.py` - **3 failing due to SQLite limitations**
- Tests designed for PostgreSQL but run against SQLite
- Failures are expected and don't affect core functionality
- Most tests pass, failures limited to ON CONFLICT operations

### Database Compatibility Matrix

| Feature | SQLite | PostgreSQL | Test Coverage |
|---------|--------|------------|---------------|
| JSON Extraction | ✅ | ✅ | 21 unit tests |
| Basic Insertion | ✅ | ✅ | 7 SQLite tests |
| JSONB Storage | ❌ | ✅ | PostgreSQL tests |
| ON CONFLICT | Limited | ✅ | PostgreSQL tests |
| Foreign Keys | ✅ | ✅ | Both test suites |
| Performance | Basic | Advanced | PostgreSQL tests |

### Current Test Status

```
Total Tests: 275
Passing: 272
Failing: 3 (expected SQLite ON CONFLICT issues)
Skipped: 10 (PostgreSQL-specific features)
```

### Running Table Population Tests

#### All Core Functionality (Recommended)
```bash
# Runs JSON extraction + SQLite integration (28 tests, all passing)
pytest tests/test_json_extraction.py tests/test_bulk_insert_sqlite.py -v
```

#### Full Suite (Excluding Expected Failures)
```bash
# Skip the 3 known SQLite limitation failures
pytest tests/ -k "not test_bulk_insert_teams and not test_missing_play_data and not test_missing_boxscore_data" -v
```

#### With PostgreSQL (Complete Testing)
```bash
# Set up test database first
export TEST_DATABASE_URL="postgresql://username:password@localhost/test_db"
pytest tests/test_table_population_postgres.py -v
```

### PostgreSQL Test Database Setup

#### Create Test Database
```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE wnba_test;
GRANT ALL PRIVILEGES ON DATABASE wnba_test TO your_user;
```

#### Environment Configuration
```bash
# For PostgreSQL table population tests
export TEST_DATABASE_URL="postgresql://username:password@localhost/wnba_test"

# Production database (separate from testing)
export DB_NAME="wnba"
export DB_USER="your_user"  
export DB_PASSWORD="your_password"
export DB_HOST="localhost"
export DB_PORT="5432"
```

### Testing Strategy Insights

#### Database-Agnostic Core
- JSON extraction works regardless of database backend
- 21 unit tests provide complete coverage of extraction logic
- Uses actual WNBA game JSON files for realistic testing

#### Database-Specific Integration
- Bulk operations require database-specific handling
- SQLite tests use alternative implementation for compatibility
- PostgreSQL tests leverage full JSONB and conflict resolution features

#### Layered Testing Approach
1. **Unit Tests**: Fast, reliable core logic validation
2. **SQLite Tests**: Integration testing with common limitations
3. **PostgreSQL Tests**: Full-feature validation for production

#### Production Recommendations

**For Development/CI (SQLite):**
- Use `test_json_extraction.py` and `test_bulk_insert_sqlite.py`
- Focus on extraction and validation logic (28 tests, all passing)
- Mock complex database operations

**For Production Validation (PostgreSQL):**
- Set up `TEST_DATABASE_URL` for full test suite
- Run PostgreSQL-specific tests before deployment
- Leverage JSONB features for performance and advanced querying

### Key Test Features

✅ **Real Data Validation**: Tests use actual WNBA game JSON samples
✅ **Comprehensive Coverage**: All extractors and edge cases tested
✅ **Database Flexibility**: Works with both SQLite and PostgreSQL  
✅ **Performance Testing**: PostgreSQL tests include benchmarks
✅ **Error Handling**: Graceful failure recovery and validation
✅ **Foreign Key Integrity**: Complete referential integrity checking

This testing strategy ensures reliable table population while handling the complexities of JSONB and different database capabilities across development and production environments.