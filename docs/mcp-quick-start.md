# NBA MCP Server - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Prerequisites Check
```bash
# Verify Python version (3.11+)
python --version

# Check if virtual environment exists
ls venv/

# Verify database connection
echo $DATABASE_URL
```

### 2. Install and Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install MCP dependencies (if not already done)
pip install -r requirements.mcp.txt

# Verify imports work
python -c "from src.mcp.server import NBAMCPServer; print('✅ Ready to go!')"
```

### 3. Start the Server
```bash
# Basic startup (should show: 🏀 Starting NBA Play-by-Play MCP Server...)
python src/mcp/start_mcp_server.py

# With custom database
DATABASE_URL="postgresql://user:pass@host:port/db" python src/mcp/start_mcp_server.py

# With debug logging
LOG_LEVEL=DEBUG python src/mcp/start_mcp_server.py

# Note: Server runs in stdio mode and waits for MCP client connections
# Press Ctrl+C to stop the server
```

## 🧠 Available MCP Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `query_nba_data` | Natural language queries | "What are LeBron James career averages?" |
| `get_player_stats` | Structured player stats | player_name: "Stephen Curry", season: "2023-24" |
| `compare_players` | Player comparisons | players: ["Michael Jordan", "Kobe Bryant"] |
| `analyze_game` | Game analysis | game_id: "0022300150" |
| `team_analysis` | Team performance | team_name: "Lakers", season: "2023-24" |

## 🧪 Local Testing Options

### 1. Super Quick Test (30 seconds) ⭐️
```bash
# Fastest test - verifies everything works with accurate NBA data
python quick_test_mcp.py
```
*Shows LeBron James with correct 1,562 regular season games and other accurate stats*

### 2. Manual Component Test
```bash
# Test all basic components
python src/mcp/tests/manual_test_mcp.py
```

### 3. Comprehensive Test Suite
```bash
# Full automated testing with mock data (2 minutes)
python src/mcp/tests/test_mcp_local.py
```

### 4. Database Connection Test
```bash
# Test with your real NBA database
DATABASE_URL="postgresql://user:pass@host:port/db" python src/mcp/tests/test_database_connection.py

# Test without database (mock data only)
python src/mcp/tests/test_database_connection.py
```

## 🔧 Individual Component Tests

```bash
# Quick verification test (all components)
python -c "
import asyncio
import sys
sys.path.append('.')

async def test_all():
    print('🧪 Testing NBA MCP Server components...')
    
    # Test imports
    from src.mcp.server import NBAMCPServer
    print('✅ Server imports OK')
    
    # Test natural language processing
    from src.mcp.query_translator import NaturalLanguageQueryTranslator
    translator = NaturalLanguageQueryTranslator()
    context = await translator.translate_query('LeBron James career stats')
    print(f'✅ Query processing: {context.confidence:.2f} confidence')
    
    # Test server creation
    server = NBAMCPServer()
    print('✅ Server creation OK')
    
    print('🎉 All components working!')

asyncio.run(test_all())
"

# Test natural language processing
python -c "
import asyncio
from src.mcp.query_translator import NaturalLanguageQueryTranslator

async def test():
    t = NaturalLanguageQueryTranslator()
    c = await t.translate_query('LeBron James career stats')
    print(f'✅ Confidence: {c.confidence:.2f}, Type: {c.query_type}')

asyncio.run(test())
"

# Test database connection
python -c "
import asyncio
from src.api.utils.database import DatabaseManager

async def test():
    db = DatabaseManager()
    await db.initialize()
    result = await db.execute_query('SELECT COUNT(*) as count FROM players')
    print(f'✅ Found {result[0][\"count\"]} players in database')

asyncio.run(test())
"

# Run unit tests
pytest src/mcp/tests/ -v
```

## 🎯 Claude Desktop Integration

1. **Find config file:**
   ```bash
   # macOS
   open ~/Library/Application\ Support/Claude/
   
   # Edit claude_desktop_config.json
   ```

2. **Add configuration:**
   ```json
   {
     "mcpServers": {
       "nba-data": {
         "command": "python",
         "args": ["src/mcp/start_mcp_server.py"],
         "cwd": "/Users/yourname/nba-pbp-api",
         "env": {
           "DATABASE_URL": "postgresql://user:pass@host:port/db"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** and look for NBA tools

## 🐳 Docker Quick Start

```bash
# Build image
docker build -f Dockerfile.mcp -t nba-mcp-server .

# Run container
docker run -d \
  --name nba-mcp \
  -e DATABASE_URL="postgresql://user:pass@host:port/db" \
  nba-mcp-server

# Check logs
docker logs nba-mcp
```

## 🆘 Quick Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| Import errors | `source venv/bin/activate && export PYTHONPATH="$(pwd):$PYTHONPATH"` |
| Database connection | Check `DATABASE_URL` format: `postgresql://user:pass@host:port/db` |
| Low confidence | Set `MIN_CONFIDENCE=0.2` or improve query phrasing |
| Claude not showing tools | Verify absolute paths in config, restart Claude Desktop |
| Server won't start | Check `python -c "import mcp; print('OK')"` |

## 📝 Example Queries to Try

Once connected to Claude Desktop or your MCP client:

- "What are LeBron James career averages?"
- "Compare Michael Jordan and Kobe Bryant shooting percentages"
- "How did the Lakers perform this season?"
- "Show me Stephen Curry's three-point stats in 2023-24"
- "What happened in the Lakers vs Warriors games?"
- "Who has the highest scoring game this season?"

## 📚 More Help

- **Full Documentation**: `docs/mcp-server-guide.md`
- **Database Setup**: `docs/database-management.md`
- **Test Examples**: `src/mcp/tests/`
- **Configuration**: `src/mcp/config.py`

---

*Need more help? Check the comprehensive guide or run the test suite to verify everything is working correctly.*