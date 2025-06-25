#!/usr/bin/env python3
"""
Simple script to start the NBA API server for development.
"""

import os
import sys
import uvicorn

# Add the parent directory to the path so we can import the API
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def start_api():
    """Start the API server"""
    try:
        print("🏀 Starting NBA Play-by-Play API...")
        print("📍 API will be available at: http://localhost:8000")
        print("📖 Documentation available at: http://localhost:8000/docs")
        print("🔧 Interactive API at: http://localhost:8000/redoc")
        print("\n💡 Note: Database connections may fail if not configured")
        print("   Check /health endpoint to verify API status")
        print("\n🛑 Press Ctrl+C to stop the server")
        
        # Start the server using import string to enable reload
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=True  # Enable auto-reload for development
        )
        
    except Exception as e:
        print(f"❌ Failed to start API: {e}")
        print("💡 Make sure you're running from the correct directory")
        print("   and that all dependencies are installed")
        sys.exit(1)

if __name__ == "__main__":
    start_api()