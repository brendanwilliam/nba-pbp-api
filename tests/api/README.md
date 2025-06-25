# API Endpoint Testing

This directory contains comprehensive tests for the NBA Play-by-Play API endpoints.

## Quick Start

### Automated Testing (Recommended)

```bash
# From project root
cd tests/api

# Run tests with automatic API server management
./run_api_tests.sh

# Run tests against already running server
./run_api_tests.sh --no-start

# Just run tests (no server management)
./run_api_tests.sh --tests-only
```

### Manual Testing

```bash
# 1. Start the API server
cd /path/to/nba-pbp-api
source venv/bin/activate
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 2. In another terminal, run the tests
cd tests/api
python test_api_endpoints.py --verbose
```

## Test Coverage

The test suite validates all major API endpoints:

### Core Endpoints
- ✅ `/health` - Health check
- ✅ `/` - Root endpoint with API info

### Player Statistics
- ✅ `/api/v1/player-stats` - Basic player queries
- ✅ `/api/v1/player-stats` (with filters) - Advanced filtering
- ✅ `/api/v1/players/{id}/stats` - Individual player stats
- ✅ `/api/v1/players/search` - Player search
- ✅ `/api/v1/player-stats/analyze` (POST) - Statistical analysis

### Team Statistics  
- ✅ `/api/v1/team-stats` - Basic team queries
- ✅ `/api/v1/teams/{id}/stats` - Individual team stats
- ✅ `/api/v1/teams/search` - Team search
- ✅ `/api/v1/teams/by-season/{season}` - Teams by season
- ✅ `/api/v1/teams/{id}/head-to-head/{id}` - Head-to-head analysis
- ✅ `/api/v1/team-stats/analyze` (POST) - Statistical analysis

### Lineup Analysis
- ✅ `/api/v1/lineup-stats` - Lineup performance
- ✅ `/api/v1/lineups/common/{team_id}` - Common lineups
- ✅ `/api/v1/lineups/player-combinations` - Player combination analysis
- ✅ **Tatum-Brown Duo Test** - Specific lineup analysis for Jayson Tatum & Jaylen Brown
  - Tests across all seasons (not just latest) for comprehensive historical data
  - **Data coverage analysis** - compares DB totals vs real-world career stats
  - **Season completeness check** - validates which seasons are in the database
  - **Expected real totals**: Tatum 707 games, Brown 738 games, Together 601 games (as of 2025)
  - **Tests both Celtics-only and career-wide statistics**
  - **Data processing validation** - checks if raw_game_data was properly parsed into normalized tables
  - **Season completeness analysis** - identifies missing seasons or incomplete data processing

### Functional Testing
- ✅ **Pagination** - Limit, offset, has_next/has_prev
- ✅ **Filtering** - JSON filters, date ranges, sorting
- ✅ **Error Handling** - Invalid IDs, malformed requests
- ✅ **Data Validation** - Response structure verification

## Test Configuration

### Environment Variables
- `API_PORT` - API server port (default: 8000)
- `API_HOST` - API server host (default: localhost)  
- `TEST_TIMEOUT` - Test timeout in seconds (default: 300)

### Command Line Options
```bash
python test_api_endpoints.py --help

# Options:
--base-url URL    API base URL (default: http://localhost:8000)
--verbose         Enable detailed logging
```

## Expected Results

### Success Criteria
- All endpoints return 200 status codes
- Response structures match expected schemas
- Data validation passes for known values
- Pagination works correctly
- Error handling responds appropriately
- **Tatum-Brown lineup analysis** returns meaningful basketball data

### Sample Output
```
============================================================
NBA Play-by-Play API Endpoint Testing Suite
============================================================
[12:34:56] INFO: Testing health endpoint...
[12:34:56] INFO: GET /health -> 200
[12:34:56] INFO: ✓ Health endpoint - Structure validation passed
[12:34:56] INFO: ✓ Health status is healthy

--- Player Endpoints ---
[12:34:56] INFO: Testing player stats basic endpoint...
[12:34:56] INFO: GET /api/v1/player-stats -> 200
[12:34:56] INFO: ✓ Player stats basic - Structure validation passed

============================================================
Test Results Summary
============================================================
Tests Passed: 25
Tests Failed: 0
Total Duration: 12.34 seconds

🎉 All tests passed!
```

## Troubleshooting

### Common Issues

**0. Low Game Counts / Data Processing Issues**
   ```
   ✓ Individual stats in DB: Tatum 394 games, Brown 381 games  
   ✓ Data coverage: Tatum 55.8% (394/706)
   ```
   - Raw data exists but hasn't been processed into normalized tables
   - Check: `python -m src.database.database_stats --local --table raw_game_data`
   - **Solution**: `python -m src.scripts.populate_enhanced_schema`
   - This processes `raw_game_data` → `player_game_stats`, `team_game_stats`, etc.

1. **Connection Refused**
   ```
   Connection failed to http://localhost:8000
   ```
   - Ensure API server is running: `python -m uvicorn src.api.main:app --port 8000`
   - Check if port 8000 is available: `lsof -i :8000`

2. **Database Errors**
   ```
   Error executing player stats query: connection to server
   ```
   - Verify PostgreSQL is running
   - Check database contains NBA data
   - Validate `DATABASE_URL` environment variable

3. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'src'
   ```
   - Activate virtual environment: `source venv/bin/activate`
   - Run from project root directory
   - Ensure Python path includes src/

### Debug Mode

```bash
# Run with verbose output
python test_api_endpoints.py --verbose

# Test single endpoint manually
curl -X GET "http://localhost:8000/health" -H "accept: application/json"

# Check API logs
python -m uvicorn src.api.main:app --log-level debug
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Test API Endpoints
  run: |
    source venv/bin/activate
    cd tests/api
    timeout 300 ./run_api_tests.sh
```

### Docker Testing
```bash
# Test against containerized API
docker-compose up -d api
./run_api_tests.sh --base-url http://localhost:8000
```

## Development Workflow

1. **Make API Changes** - Modify endpoints in `src/api/`
2. **Update Tests** - Add new test cases if needed
3. **Run Tests** - `./run_api_tests.sh`
4. **Validate Results** - Ensure all tests pass
5. **Deploy** - Confident in API functionality

## Adding New Tests

To add tests for new endpoints:

1. **Add test method** to `APIEndpointTester` class
2. **Follow naming convention**: `test_endpoint_name()`
3. **Use helper methods**: `make_request()`, `assert_response_structure()`
4. **Call from `run_all_tests()`**
5. **Update this documentation**

Example:
```python
def test_new_endpoint(self):
    """Test new endpoint functionality"""
    self.log("Testing new endpoint...")
    
    response = self.make_request("GET", "/api/v1/new-endpoint", {"param": "value"})
    
    if response:
        expected_keys = ["data", "status"]
        self.assert_response_structure(response, expected_keys, "New endpoint")
```