#!/usr/bin/env python3
"""
NBA MCP Server Startup Script

This script starts the NBA Play-by-Play MCP server.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.server import NBAMCPServer


async def main():
    """Main entry point for the MCP server."""
    print("🏀 Starting NBA Play-by-Play MCP Server...")
    
    # Initialize and run the server
    server = NBAMCPServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())