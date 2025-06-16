#!/usr/bin/env python3
"""
Wrapper script to run queue building with proper imports.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now run the main script
if __name__ == "__main__":
    # Import after path is set
    from scripts.build_game_url_queue import main
    import asyncio
    
    # Pass through command line arguments
    original_argv = sys.argv
    sys.argv = ['build_game_url_queue.py'] + sys.argv[1:]
    
    asyncio.run(main())