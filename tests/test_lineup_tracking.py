#!/usr/bin/env python3
"""
Simple test for lineup tracking functionality
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analytics.lineup_tracker import LineupTracker
from core.database import SessionLocal
from sqlalchemy import text

def test_lineup_tracking():
    """Test lineup tracking with a real game"""
    db = SessionLocal()
    try:
        # Get a game that should have valid data
        result = db.execute(text("SELECT game_id, raw_json FROM raw_game_data WHERE game_id = '0022200650'"))
        game_data = result.fetchone()
        
        if not game_data:
            print("No game data found")
            return
        
        game_id, raw_json = game_data
        if isinstance(raw_json, str):
            raw_json = json.loads(raw_json)
        
        print(f"Testing lineup tracking for game: {game_id}")
        
        # Test the lineup tracker initialization
        try:
            tracker = LineupTracker(raw_json)
            print("✅ LineupTracker initialized successfully")
        except Exception as e:
            print(f"❌ LineupTracker initialization failed: {e}")
            return
        
        # Test building timeline
        try:
            timeline = tracker.build_lineup_timeline()
            print(f"✅ Timeline built: {len(timeline)} states")
        except Exception as e:
            print(f"❌ Timeline building failed: {e}")
            return
        
        # Test substitution events
        try:
            subs = tracker.parse_substitution_events()
            print(f"✅ Substitutions extracted: {len(subs)} events")
        except Exception as e:
            print(f"❌ Substitution extraction failed: {e}")
            return
        
        # Test getting players at a specific time
        try:
            players = tracker.get_players_on_court(1, "PT12M00.00S")
            print(f"✅ Players on court query successful")
            print(f"   Home players: {len(players['home_players'])}")
            print(f"   Away players: {len(players['away_players'])}")
        except Exception as e:
            print(f"❌ Players on court query failed: {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_lineup_tracking()