# NBA Play-by-Play API Health Check Plan

**Purpose**: Comprehensive testing plan to routinely monitor and validate all API endpoints for functionality, performance, and data integrity.

**Created**: 2025-06-24  
**Status**: Active  
**Frequency**: Should be run before any deployment and weekly for monitoring

---

## Overview

This document outlines a systematic approach to testing all endpoints of the NBA Play-by-Play API to ensure:
- ✅ **Functional correctness** - All endpoints return expected responses
- ✅ **Performance standards** - Response times within acceptable limits
- ✅ **Data integrity** - Returned data matches database schema and business logic
- ✅ **Error handling** - Proper error responses for invalid inputs
- ✅ **REST compliance** - Proper HTTP methods and status codes

## Quick Start

```bash
# 1. Ensure API is running
PYTHONPATH=/Users/brendan/nba-pbp-api python src/api/start_api.py

# 2. Run basic health check
curl http://localhost:8000/health

# 3. Execute comprehensive test suite (see sections below)
```

---

## Test Categories

### 1. System Health Tests

#### 1.1 Basic Connectivity
```bash
# Health check endpoint
curl -w "Time: %{time_total}s\n" http://localhost:8000/health

# Expected: HTTP 200, response time < 1s
# Response: {"status": "healthy", "timestamp": "...", "service": "NBA Play-by-Play API", "version": "1.0.0"}
```

#### 1.2 Database Connectivity
```bash
# Metrics endpoint (verifies database connection)
curl -w "Time: %{time_total}s\n" http://localhost:8000/metrics

# Expected: HTTP 200, response time < 2s
```

#### 1.3 API Documentation
```bash
# OpenAPI schema endpoint
curl -s http://localhost:8000/openapi.json | jq '.info.title'

# Interactive docs (manual verification)
# Visit: http://localhost:8000/docs
# Visit: http://localhost:8000/redoc
```

### 2. Search Functionality Tests

#### 2.1 Player Search
```bash
# Basic player search
curl -s "http://localhost:8000/api/v1/players/search?query=James&limit=5" | jq .
curl -s "http://localhost:8000/api/v1/players/search?query=LeBron&limit=5" | jq .
curl -s "http://localhost:8000/api/v1/players/search?query=Tatum&limit=5" | jq .
curl -s "http://localhost:8000/api/v1/players/search?query=Jaylen%20Brown&limit=5" | jq .

# Edge cases
curl -s "http://localhost:8000/api/v1/players/search?query=XYZ&limit=5" | jq .  # No results
curl -s "http://localhost:8000/api/v1/players/search?query=a&limit=100" | jq .  # Single character

# Performance test
curl -w "Time: %{time_total}s\n" -s "http://localhost:8000/api/v1/players/search?query=James" > /dev/null

# Expected: HTTP 200, response time < 3s, proper JSON structure
```

#### 2.2 Team Search
```bash
# Team search by name
curl -s "http://localhost:8000/api/v1/teams/search?query=Lakers&limit=5" | jq .

# Team search by abbreviation
curl -s "http://localhost:8000/api/v1/teams/search?query=LAL&limit=5" | jq .

# Team search by city
curl -s "http://localhost:8000/api/v1/teams/search?query=Los&limit=5" | jq .

# Expected: HTTP 200, consistent response format, proper team data
```

### 3. Statistics Endpoints Tests (GET)

#### 3.1 Player Statistics
```bash
# Basic player stats query
curl -s "http://localhost:8000/api/v1/player-stats?limit=5" | jq .

# Player stats with filters
curl -s "http://localhost:8000/api/v1/player-stats?season=latest&limit=5" | jq .

# Player stats with specific player
curl -s "http://localhost:8000/api/v1/player-stats?player_id=2546&limit=5" | jq .

# Player stats with team filter
curl -s "http://localhost:8000/api/v1/player-stats?team_id=14&limit=5" | jq .

# Player stats with date range
curl -s "http://localhost:8000/api/v1/player-stats?date_from=2023-01-01&date_to=2023-12-31&limit=5" | jq .

# Player stats with statistical summary
curl -s "http://localhost:8000/api/v1/player-stats?include_summary=true&limit=10" | jq .

# Complex filters (URL encoded JSON)
curl -s "http://localhost:8000/api/v1/player-stats?filters=%7B%22points%22%3A%7B%22gte%22%3A20%7D%7D&limit=5" | jq .

# Performance test
curl -w "Time: %{time_total}s\n" -s "http://localhost:8000/api/v1/player-stats?limit=100" > /dev/null

# Expected: HTTP 200, response time < 5s, proper pagination, data integrity
```

#### 3.2 Team Statistics
```bash
# Basic team stats query
curl -s "http://localhost:8000/api/v1/team-stats?limit=5" | jq .

# Team stats with season filter
curl -s "http://localhost:8000/api/v1/team-stats?season=latest&limit=5" | jq .

# Team stats with home/away filter
curl -s "http://localhost:8000/api/v1/team-stats?home_away=home&limit=5" | jq .

# Team stats with win/loss filter
curl -s "http://localhost:8000/api/v1/team-stats?win_loss=win&limit=5" | jq .

# Expected: HTTP 200, proper team data structure, performance < 5s
```

#### 3.3 Individual Player/Team Stats
```bash
# Individual player stats (replace with actual player ID from search)
curl -s "http://localhost:8000/api/v1/players/2546/stats?limit=5" | jq .

# Individual team stats (replace with actual team ID)
curl -s "http://localhost:8000/api/v1/teams/14/stats?limit=5" | jq .

# Head-to-head analysis
curl -s "http://localhost:8000/api/v1/teams/14/head-to-head/15" | jq .

# Expected: HTTP 200, detailed individual statistics
```

#### 3.4 Lineup Statistics
```bash
# Basic lineup stats (requires multiple player IDs)
curl -s "http://localhost:8000/api/v1/lineup-stats?player_ids=2544&player_ids=203076&limit=5" | jq .  # 2 players, Lebron James and Anthony Davis

# Common lineups for a team
curl -s "http://localhost:8000/api/v1/lineups/common/14?season=latest&limit=5" | jq .  # Team ID 14, Lakers

# Player combinations analysis
curl -s "http://localhost:8000/api/v1/lineups/player-combinations?player_ids=2544&player_ids=203076&limit=5" | jq .  # 2 players, Lebron James and Anthony Davis

# Expected: HTTP 200 or 400 (if insufficient player IDs), proper lineup data
```

### 4. Advanced Analysis Tests (POST)

#### 4.1 Player Statistics Analysis
```bash
# Correlation analysis
curl -X POST "http://localhost:8000/api/v1/player-stats/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "season": "latest",
    "correlation": ["points", "assists", "rebounds_total"],
    "limit": 100
  }' | jq .

# Regression analysis
curl -X POST "http://localhost:8000/api/v1/player-stats/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "season": "latest",
    "regression": "{\"dependent\": \"points\", \"independent\": \"assists,rebounds_total\"}",
    "limit": 100
  }' | jq .

# Expected: HTTP 200, statistical analysis results, response time < 10s
```

#### 4.2 Team Statistics Analysis
```bash
# Team correlation analysis
curl -X POST "http://localhost:8000/api/v1/team-stats/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "season": "latest",
    "correlation": ["points", "assists", "rebounds_total"],
    "limit": 50
  }' | jq .

# Expected: HTTP 200, team-level statistical analysis
```

### 5. Error Handling Tests

#### 5.1 Invalid Parameters
```bash
# Invalid player ID
curl -s "http://localhost:8000/api/v1/players/999999/stats" | jq .
# Expected: HTTP 404

# Invalid team ID
curl -s "http://localhost:8000/api/v1/teams/999999/stats" | jq .
# Expected: HTTP 404

# Invalid season format
curl -s "http://localhost:8000/api/v1/player-stats?season=invalid" | jq .
# Expected: HTTP 200 (should handle gracefully) or HTTP 400

# Invalid JSON in filters
curl -s "http://localhost:8000/api/v1/player-stats?filters=invalid_json" | jq .
# Expected: HTTP 400

# Malformed regression JSON
curl -X POST "http://localhost:8000/api/v1/player-stats/analyze" \
  -H "Content-Type: application/json" \
  -d '{"regression": "invalid_json"}' | jq .
# Expected: HTTP 400
```

#### 5.2 Boundary Testing
```bash
# Excessive limit
curl -s "http://localhost:8000/api/v1/player-stats?limit=99999" | jq .
# Expected: HTTP 422 (validation error)

# Negative offset
curl -s "http://localhost:8000/api/v1/player-stats?offset=-1" | jq .
# Expected: HTTP 422

# Empty required parameters for lineup analysis
curl -s "http://localhost:8000/api/v1/lineup-stats" | jq .
# Expected: HTTP 400
```

### 6. Performance Benchmarks

#### 6.1 Response Time Standards
```bash
# Measure all endpoints with timing
for endpoint in "health" "metrics" "api/v1/players/search?query=James" "api/v1/teams/search?query=Lakers" "api/v1/player-stats?limit=10" "api/v1/team-stats?limit=10"; do
  echo "Testing $endpoint:"
  curl -w "  Response time: %{time_total}s\n" -s "http://localhost:8000/$endpoint" > /dev/null
done
```

**Performance Targets:**
- Health check: < 1s
- Search endpoints: < 3s
- Basic statistics: < 5s
- Complex analysis: < 10s

#### 6.2 Load Testing (Optional)
```bash
# Simple concurrent request test
seq 1 10 | xargs -n1 -P10 curl -s "http://localhost:8000/health" > /dev/null
```

### 7. Data Integrity Tests

#### 7.1 Response Structure Validation
```bash
# Verify response contains required fields
curl -s "http://localhost:8000/api/v1/player-stats?limit=1" | jq 'has("data") and has("total_records") and has("query_info")'
# Expected: true

# Verify player data structure
curl -s "http://localhost:8000/api/v1/players/search?query=James&limit=1" | jq '.players[0] | has("player_id") and has("player_name")'
# Expected: true

# Verify pagination metadata
curl -s "http://localhost:8000/api/v1/player-stats?limit=5&offset=10" | jq '.query_info.pagination | has("limit") and has("offset") and has("has_next") and has("has_prev")'
# Expected: true
```

#### 7.2 Database Consistency
```bash
# Cross-reference search results with detailed queries
PLAYER_ID=$(curl -s "http://localhost:8000/api/v1/players/search?query=James&limit=1" | jq -r '.players[0].player_id')
curl -s "http://localhost:8000/api/v1/players/$PLAYER_ID/stats?limit=1" | jq .
# Expected: Valid player stats for the found player
```

---

## Automated Test Script

Create a comprehensive test script to run all checks:

```bash
#!/bin/bash
# File: test_api_health.sh

API_BASE="http://localhost:8000"
PASS=0
FAIL=0

test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="$3"
    local max_time="$4"
    
    echo "Testing: $name"
    
    response=$(curl -s -w "%{http_code},%{time_total}" "$url")
    status_code=$(echo "$response" | tail -c 10 | cut -d',' -f1)
    time_total=$(echo "$response" | tail -c 10 | cut -d',' -f2)
    
    if [ "$status_code" = "$expected_status" ] && [ "$(echo "$time_total < $max_time" | bc)" = "1" ]; then
        echo "  ✅ PASS (${status_code}, ${time_total}s)"
        ((PASS++))
    else
        echo "  ❌ FAIL (${status_code}, ${time_total}s)"
        ((FAIL++))
    fi
}

echo "🏀 NBA Play-by-Play API Health Check"
echo "======================================="

# System health tests
test_endpoint "Health Check" "$API_BASE/health" "200" "1"
test_endpoint "Metrics" "$API_BASE/metrics" "200" "2"

# Search tests
test_endpoint "Player Search" "$API_BASE/api/v1/players/search?query=James&limit=5" "200" "3"
test_endpoint "Team Search" "$API_BASE/api/v1/teams/search?query=Lakers&limit=5" "200" "3"

# Statistics tests
test_endpoint "Player Stats" "$API_BASE/api/v1/player-stats?limit=5" "200" "5"
test_endpoint "Team Stats" "$API_BASE/api/v1/team-stats?limit=5" "200" "5"

# Error handling tests
test_endpoint "Invalid Player ID" "$API_BASE/api/v1/players/999999/stats" "404" "3"
test_endpoint "Invalid Team ID" "$API_BASE/api/v1/teams/999999/stats" "404" "3"

echo "======================================="
echo "Results: $PASS passed, $FAIL failed"

if [ $FAIL -eq 0 ]; then
    echo "🎉 All tests passed!"
    exit 0
else
    echo "⚠️  Some tests failed. Check API health."
    exit 1
fi
```

---

## Monitoring Integration

### 1. Health Check Automation
```bash
# Add to cron for regular monitoring
# 0 */6 * * * /path/to/test_api_health.sh

# Or use with monitoring tools like Nagios, Datadog, etc.
```

### 2. Performance Monitoring
```bash
# Log response times for trending
curl -w "%{time_total}" -s "$API_BASE/api/v1/player-stats?limit=100" >> /var/log/api_performance.log
```

### 3. Database Health Integration
```bash
# Check database statistics as part of health check
PYTHONPATH=/Users/brendan/nba-pbp-api python -m src.database.database_stats --json | jq '.summary.total_records'
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. API Server Not Responding
```bash
# Check if server is running
ps aux | grep start_api.py

# Restart server if needed
PYTHONPATH=/Users/brendan/nba-pbp-api python src/api/start_api.py
```

#### 2. Database Connection Issues
```bash
# Verify database connectivity
PYTHONPATH=/Users/brendan/nba-pbp-api python -c "
from src.core.database import get_database_url
print('Database URL configured:', bool(get_database_url()))
"
```

#### 3. Slow Response Times
- Check database indexes on frequently queried columns
- Monitor database connection pool status
- Consider implementing Redis caching for frequent queries

#### 4. Empty Results
- Verify database has been populated with scraped data
- Check if filters are too restrictive
- Validate season/date ranges against available data

---

## Maintenance Schedule

### Daily
- Run basic health check script
- Monitor error logs

### Weekly
- Full endpoint test suite
- Performance benchmark validation
- Database statistics review

### Monthly
- Load testing
- Schema validation
- Update test cases for new endpoints

---

## Test Environment Setup

### Prerequisites
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install testing dependencies
pip install httpx pytest jq

# Set environment variables if needed
export DATABASE_URL="postgresql://localhost:5432/nba_pbp"
```

### Development vs Production Testing
- **Development**: Test against localhost:8000
- **Staging**: Test against staging environment URL
- **Production**: Test against production URL with read-only operations

---

## Conclusion

This comprehensive health check plan ensures the NBA Play-by-Play API maintains high quality and reliability. Regular execution of these tests will catch issues early and maintain optimal performance standards.

**Next Steps:**
1. Implement automated test script
2. Set up monitoring alerts
3. Integrate with CI/CD pipeline
4. Document any endpoint-specific issues discovered
5. Update tests as new endpoints are added

---

*Last Updated: 2025-06-24*
*Next Review: Weekly during active development*