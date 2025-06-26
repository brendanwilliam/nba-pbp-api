# NBA Play-by-Play MCP Server - Complete Setup and Usage Guide

This guide provides step-by-step instructions for setting up, running, and using the NBA Play-by-Play Model Context Protocol (MCP) server.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Database Setup](#database-setup)
4. [Running the MCP Server](#running-the-mcp-server)
5. [Integration with AI Clients](#integration-with-ai-clients)
6. [Testing and Validation](#testing-and-validation)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

## Prerequisites

### System Requirements
- Python 3.11 or higher
- PostgreSQL database with NBA data
- Virtual environment (recommended)
- Git (for cloning the repository)

### Environment Setup
```bash
# 1. Clone the repository (if not already done)
git clone <repository-url>
cd nba-pbp-api

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements.mcp.txt
```

## Quick Start

### 1. Environment Configuration

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/nba_pbp

# MCP Server Configuration (optional)
MCP_SERVER_NAME=nba-pbp-server
MCP_SERVER_VERSION=1.0.0
LOG_LEVEL=INFO
MIN_CONFIDENCE=0.3
MAX_QUERY_TIMEOUT=30
```

### 2. Verify Database Connection

```bash
# Test database connectivity
python -c "
import asyncio
from src.api.utils.database import DatabaseManager

async def test_db():
    db = DatabaseManager()
    await db.initialize()
    print('✅ Database connection successful!')
    
asyncio.run(test_db())
"
```

### 3. Start the MCP Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start the MCP server
python src/mcp/start_mcp_server.py
```

You should see:
```
🏀 Starting NBA Play-by-Play MCP Server...
Server running on stdio transport...
```

## Database Setup

### Option 1: Using Existing Database

If you already have the NBA database populated:

```bash
# Verify your database has the required tables
python -c "
import asyncio
from src.api.utils.database import DatabaseManager

async def check_tables():
    db = DatabaseManager()
    await db.initialize()
    
    # Check for key tables
    tables = ['players', 'teams', 'games', 'player_game_stats']
    for table in tables:
        result = await db.execute_query(f'SELECT COUNT(*) FROM {table} LIMIT 1')
        print(f'✅ {table}: {result[0][\"count\"]} records')

asyncio.run(check_tables())
"
```

### Option 2: Fresh Database Setup

If you need to set up the database from scratch, refer to the existing database documentation:

```bash
# See comprehensive database setup instructions
cat docs/database-management.md

# Quick setup commands (adjust DATABASE_URL as needed)
python -m src.database.database_stats --local
```

## Running the MCP Server

### Development Mode

```bash
# Standard development run
source venv/bin/activate
python src/mcp/start_mcp_server.py
```

### With Custom Configuration

```bash
# Set environment variables for custom config
export DATABASE_URL="postgresql://user:pass@host:port/db"
export LOG_LEVEL="DEBUG"
export MIN_CONFIDENCE="0.2"

# Start server
python src/mcp/start_mcp_server.py
```

### Docker Mode

```bash
# Build the MCP server image
docker build -f Dockerfile.mcp -t nba-mcp-server .

# Run with environment variables
docker run -d \
  --name nba-mcp \
  -e DATABASE_URL="postgresql://user:pass@host:port/db" \
  -p 8080:8080 \
  nba-mcp-server

# Check logs
docker logs nba-mcp
```

## Integration with AI Clients

### Claude Desktop Integration

1. **Locate Claude Desktop MCP Configuration**
   ```bash
   # macOS
   ~/Library/Application Support/Claude/claude_desktop_config.json
   
   # Windows
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Add NBA MCP Server Configuration**
   ```json
   {
     "mcpServers": {
       "nba-data": {
         "command": "python",
         "args": ["src/mcp/start_mcp_server.py"],
         "cwd": "/absolute/path/to/nba-pbp-api",
         "env": {
           "DATABASE_URL": "postgresql://user:pass@host:port/db"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**
   - Close Claude Desktop completely
   - Restart the application
   - Look for the NBA data tools in the tool panel

### Custom MCP Client

```python
# Example Python client
import asyncio
from mcp.client import MCPClient

async def query_nba_data():
    async with MCPClient("nba-pbp-server") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        # Query player stats
        response = await client.call_tool(
            "query_nba_data",
            {"query": "What are LeBron James career averages?"}
        )
        print(response.content[0].text)

# Run the client
asyncio.run(query_nba_data())
```

### HTTP Mode (Advanced)

For remote access, you can modify the server to run in HTTP mode:

```python
# In src/mcp/start_mcp_server.py, modify the run method
# Add HTTP transport support (requires additional MCP configuration)
```

## Testing and Validation

### 1. Unit Tests

```bash
# Run the full test suite
source venv/bin/activate
pytest src/mcp/tests/ -v

# Run specific test modules
pytest src/mcp/tests/test_query_translator.py -v
pytest src/mcp/tests/test_mcp_server.py -v

# Run with coverage
pytest --cov=src.mcp src/mcp/tests/
```

### 2. Manual Testing

```bash
# Test natural language processing
python -c "
import asyncio
from src.mcp.query_translator import NaturalLanguageQueryTranslator

async def test_queries():
    translator = NaturalLanguageQueryTranslator()
    
    queries = [
        'What are LeBron James career stats?',
        'Compare Michael Jordan and Kobe Bryant',
        'Lakers vs Warriors games this season',
        'Stephen Curry three point percentage'
    ]
    
    for query in queries:
        context = await translator.translate_query(query)
        print(f'✅ \"{query}\" → {context.query_type} (confidence: {context.confidence:.2f})')

asyncio.run(test_queries())
"
```

### 3. Integration Testing

```bash
# Test with mock database (safe testing)
python -c "
import asyncio
from unittest.mock import AsyncMock
from src.mcp.server import NBAMCPServer

async def test_integration():
    server = NBAMCPServer()
    
    # Mock database for testing
    server.db_manager = AsyncMock()
    server.db_manager.execute_query.return_value = [
        {
            'player_name': 'LeBron James',
            'points_per_game': 25.3,
            'rebounds_per_game': 7.4,
            'assists_per_game': 8.2
        }
    ]
    
    # Test natural language query
    result = await server._handle_natural_language_query('LeBron James stats')
    print('✅ Integration test passed')
    print(f'Response: {result[0].text[:100]}...')

asyncio.run(test_integration())
"
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Error: Cannot import module
# Solution: Check Python path and virtual environment
source venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"
python src/mcp/start_mcp_server.py
```

#### 2. Database Connection Issues
```bash
# Error: Database connection failed
# Solution: Verify DATABASE_URL and database status

# Check database URL format
echo $DATABASE_URL
# Should be: postgresql://user:password@host:port/database

# Test database connectivity
python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

#### 3. MCP Server Not Starting
```bash
# Error: Server fails to start
# Solution: Check dependencies and configuration

# Verify MCP library installation
python -c "import mcp; print('✅ MCP library available')"

# Check for conflicting processes
ps aux | grep python | grep mcp

# Detailed error logging
LOG_LEVEL=DEBUG python src/mcp/start_mcp_server.py
```

#### 4. Claude Desktop Integration Issues
```bash
# Error: Tools not appearing in Claude Desktop
# Solutions:

# 1. Verify configuration file location and syntax
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool

# 2. Check absolute paths
pwd  # Use this path in your config

# 3. Verify server starts independently
cd /absolute/path/to/nba-pbp-api
source venv/bin/activate
python src/mcp/start_mcp_server.py

# 4. Check Claude Desktop logs (if available)
# Look for MCP-related error messages
```

#### 5. Low Query Confidence
```bash
# Issue: Queries not being understood
# Solution: Adjust confidence threshold or improve query phrasing

# Lower confidence threshold temporarily
export MIN_CONFIDENCE=0.2

# Test specific query patterns
python -c "
import asyncio
from src.mcp.query_translator import NaturalLanguageQueryTranslator

async def debug_query():
    translator = NaturalLanguageQueryTranslator()
    query = 'your problematic query here'
    context = await translator.translate_query(query)
    
    print(f'Query: {query}')
    print(f'Type: {context.query_type}')
    print(f'Confidence: {context.confidence}')
    print(f'Entities: {[e.value for e in context.entities]}')

asyncio.run(debug_query())
"
```

### Debugging Tools

#### 1. Enable Verbose Logging
```bash
# Set debug logging
export LOG_LEVEL=DEBUG

# Enable query logging
export ENABLE_QUERY_LOGGING=true

# Start server with verbose output
python src/mcp/start_mcp_server.py
```

#### 2. Database Query Debugging
```bash
# Test direct database queries
python -c "
import asyncio
from src.api.utils.database import DatabaseManager

async def debug_db():
    db = DatabaseManager()
    await db.initialize()
    
    # Test simple query
    result = await db.execute_query('SELECT COUNT(*) as count FROM players')
    print(f'Players count: {result[0][\"count\"]}')
    
    # Test complex query (as used by MCP server)
    query = '''
    SELECT p.player_name, COUNT(*) as games 
    FROM players p 
    JOIN player_game_stats pgs ON p.player_id = pgs.player_id 
    WHERE LOWER(p.player_name) LIKE LOWER($1) 
    GROUP BY p.player_name 
    LIMIT 5
    '''
    result = await db.execute_query(query, ['%lebron%'])
    print(f'LeBron results: {result}')

asyncio.run(debug_db())
"
```

#### 3. Component Testing
```bash
# Test individual components
python -c "
# Test query translation
import asyncio
from src.mcp.query_translator import NaturalLanguageQueryTranslator

async def test_component():
    translator = NaturalLanguageQueryTranslator()
    context = await translator.translate_query('LeBron James stats')
    print(f'Translation working: {context.confidence > 0.5}')

asyncio.run(test_component())
"
```

## Production Deployment

### Docker Deployment
```bash
# 1. Build production image
docker build -f Dockerfile.mcp -t nba-mcp-server:latest .

# 2. Run with production configuration
docker run -d \
  --name nba-mcp-production \
  --restart unless-stopped \
  -e DATABASE_URL="$PRODUCTION_DATABASE_URL" \
  -e LOG_LEVEL="INFO" \
  -e MAX_DB_CONNECTIONS="50" \
  -e MIN_CONFIDENCE="0.3" \
  nba-mcp-server:latest

# 3. Health check
docker exec nba-mcp-production python -c "
from src.mcp.server import NBAMCPServer
print('✅ Production server healthy')
"
```

### Cloud Deployment (AWS/GCP/Azure)
```bash
# Example for AWS ECS
# 1. Push image to ECR
docker tag nba-mcp-server:latest $AWS_ACCOUNT.dkr.ecr.region.amazonaws.com/nba-mcp:latest
docker push $AWS_ACCOUNT.dkr.ecr.region.amazonaws.com/nba-mcp:latest

# 2. Create ECS task definition with environment variables
# 3. Deploy to ECS service with load balancer if needed
```

### Environment Variables for Production
```bash
# Required
DATABASE_URL=postgresql://user:pass@production-host:5432/nba_pbp

# Performance tuning
MAX_DB_CONNECTIONS=50
MIN_DB_CONNECTIONS=10
MAX_QUERY_TIMEOUT=60
DEFAULT_RESULT_LIMIT=100

# Security
LOG_LEVEL=INFO
ENABLE_QUERY_LOGGING=false

# Monitoring
ENABLE_HEALTH_CHECK=true
METRICS_ENDPOINT=true
```

### Monitoring and Maintenance
```bash
# Health check endpoint (if enabled)
curl http://localhost:8080/health

# Monitor database connections
python -c "
from src.api.utils.database import DatabaseManager
import asyncio

async def monitor():
    db = DatabaseManager()
    await db.initialize()
    print('✅ Database connectivity check passed')

asyncio.run(monitor())
"

# Log monitoring
tail -f /var/log/nba-mcp-server.log
```

This comprehensive guide should get you up and running with the NBA MCP server in any environment. For additional support, refer to the test files in `src/mcp/tests/` for working examples of all functionality.