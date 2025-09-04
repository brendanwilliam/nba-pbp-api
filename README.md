# WNBA Play-by-Play Data Scraping Project

This project extracts WNBA game data from the official WNBA website, stores it in PostgreSQL, and provides essential basketball analytics including possession and lineup tracking.

## Project Overview

The WNBA scraping project focuses on:
- **Data Collection**: Efficient scraping of WNBA.com game data from 1997-2025
- **Data Storage**: Normalized PostgreSQL database with comprehensive schema
- **Essential Analytics**: Possession tracking and lineup analysis
- **Data Quality**: Validation and quality assurance for scraped data

## Development Philosophy

This project follows a **WNBA-first development approach**:

### 🏀 **Why WNBA First?**
- **Manageable Scale**: WNBA has ~240 regular season games vs NBA's ~1,230, making it ideal for testing and iteration
- **Lower Complexity**: Fewer total games and plays allow for faster development cycles and easier debugging
- **Proven Foundation**: WNBA success validates our architecture before scaling to NBA's larger dataset
- **Quality Focus**: Smaller dataset enables thorough testing of data quality, analytics, and performance

### 🚀 **Development Roadmap**
1. **Phase 1** (Current): Complete WNBA implementation with full feature set
2. **Phase 2**: Add NBA support using proven WNBA architecture 
3. **Phase 3**: Cross-league analytics and comparative features

### 📊 **Scale Comparison**
| League | Regular Season Games | Total Games (1997-2025) | Plays per Game |
|--------|---------------------|--------------------------|----------------|
| WNBA   | ~240/season         | ~6,600                   | ~400-500       |
| NBA    | ~1,230/season       | ~35,000                  | ~400-500       |

**Result**: WNBA provides the perfect testing environment at ~15% of NBA's scale, enabling rapid development and validation before enterprise-scale deployment.

## Environment Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Virtual environment (recommended)

### Initial Setup

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/nba-pbp-api
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Testing

This project uses pytest for testing with comprehensive coverage of the WNBA scraping functionality.

### Test Configuration

The project includes:
- **pytest.ini**: Test configuration with coverage reporting
- **conftest.py**: Shared fixtures and test setup
- **Test markers**: `unit`, `integration`, `slow` for organizing tests

### Running Tests

#### Basic Test Commands

```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests
pytest

# Run all tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_game_url_generator.py

# Run specific test function
pytest tests/test_game_url_generator.py::TestGameURLGenerator::test_generate_game_url

# Run specific test class
pytest tests/test_game_url_generator.py::TestGameURLGenerator
```

#### Test Filtering by Markers

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests (recommended for development)
pytest -m "not slow"

# Run only slow performance tests
pytest -m slow

# Combine markers
pytest -m "unit and not slow"
```

#### Advanced Test Options

```bash
# Run tests in parallel (if pytest-xdist is installed)
pytest -n auto

# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l

# Run tests that failed in the last run
pytest --lf

# Run tests that failed in the last run, then all others
pytest --ff

# Show the slowest 10 tests
pytest --durations=10

# Generate XML report for CI/CD
pytest --junitxml=test-results.xml
```

### Test Coverage

```bash
# Generate HTML coverage report (opens in browser)
pytest --cov=src --cov-report=html
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux

# Generate terminal coverage report
pytest --cov=src --cov-report=term

# Generate coverage report with missing lines
pytest --cov=src --cov-report=term-missing

# Set minimum coverage threshold (fail if below 80%)
pytest --cov=src --cov-fail-under=80
```

### Test Structure

#### Core Test Files

- **`tests/conftest.py`**: Shared fixtures, markers, and test configuration
- **`tests/test_game_url_generator.py`**: Comprehensive tests for WNBA URL generation
- **`pytest.ini`**: Project-wide pytest configuration

#### Test Categories

1. **Unit Tests** (`-m unit`):
   - Fast, isolated component tests
   - Mock external dependencies
   - Test individual functions and classes

2. **Integration Tests** (`-m integration`):
   - Test component interactions
   - Verify CSV file accessibility
   - Database connection tests

3. **Performance Tests** (`-m slow`):
   - Large dataset processing
   - Memory and speed benchmarks
   - Concurrent operation testing

#### Key Test Classes

**`TestGameURLInfo`**:
- Data class creation and validation
- Dictionary conversion functionality

**`TestGameURLGenerator`**:
- URL generation for regular season and playoffs
- Game ID generation algorithms
- Season-specific logic (1997-2025)
- CSV data processing
- URL validation and content checking
- Data extraction from WNBA.com

**`TestGameURLGeneratorPerformance`**:
- Large-scale URL generation benchmarks
- File system integration tests

### Test Data

The tests use mocked CSV data to avoid dependencies on actual files:
- Regular season data: seasons 1997, 1998, 2020, 2025
- Playoff data: various tournament formats across WNBA history
- Sample game URLs and IDs for validation testing

### Debugging Tests

```bash
# Run with Python debugger on failures
pytest --pdb

# Run with detailed output for debugging
pytest -vvv --tb=long

# Show print statements in test output
pytest -s

# Run specific test with debugging
pytest -vvv -s tests/test_game_url_generator.py::TestGameURLGenerator::test_generate_game_url
```

### Continuous Integration

For CI/CD pipelines, use:
```bash
# CI-friendly test run with XML output
pytest --junitxml=test-results.xml --cov=src --cov-report=xml

# Quiet mode for CI logs
pytest -q --cov=src --cov-report=term
```

## Development Commands

### Database Management
```bash
# Check database status
python -m src.database.database_stats --local

# Run database migrations
alembic upgrade head

# Sync database changes
python -m src.database.selective_sync --analyze --ignore-size
```

### WNBA Data Scraping
```bash
# Build game URL queue
python -m src.scripts.build_game_url_queue

# Test scraping offline
pytest tests/test_queue_offline.py

# Run mass scraping (use with caution)
python -m src.scripts.mass_game_scraper
```

## Troubleshooting Tests

### Common Issues

1. **Import Errors:**
   - Ensure virtual environment is activated
   - Check that `src/` directory is in Python path
   - Verify all dependencies are installed

2. **Database Connection Errors:**
   - Check PostgreSQL is running
   - Verify database configuration
   - Ensure `wnba_pbp` database exists

3. **CSV File Errors:**
   - Integration tests require CSV files in `src/scrapers/`
   - Unit tests use mocked data and should not fail on missing files

4. **Slow Test Performance:**
   - Skip slow tests during development: `pytest -m "not slow"`
   - Use parallel execution: `pytest -n auto`

### Getting Help

- Check test output for detailed error messages
- Use `-vvv` flag for maximum verbosity
- Review `conftest.py` for fixture setup
- Examine `pytest.ini` for configuration options

## Project Architecture

### Completed Components ✅
- **Web Scrapers**: WNBA.com data extraction
- **Database Schema**: Normalized PostgreSQL storage
- **Analytics**: Possession and lineup tracking
- **Data Quality**: Validation framework
- **Queue Management**: Systematic scraping coordination

### Key Directories
- **`src/scrapers/`**: Web scraping logic
- **`src/database/`**: Database schema and management
- **`src/analytics/`**: Basketball analytics
- **`src/scripts/`**: Execution scripts
- **`tests/`**: Comprehensive test suite

For more detailed information about the project structure and development guidelines, see `CLAUDE.md`.