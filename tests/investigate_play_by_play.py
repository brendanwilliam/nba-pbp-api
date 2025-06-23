"""Investigate why play-by-play data is not being extracted."""

import json
import sys
from pathlib import Path
from pprint import pprint

# Add tests and src to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.database import SessionLocal
from sqlalchemy import text
from json_parser import JSONGameParser


def investigate_json_structure(game_id: str):
    """Deep dive into JSON structure to find play-by-play data."""
    parser = JSONGameParser()
    
    try:
        # Get raw JSON data
        _, raw_json = parser.get_sample_game(game_id)
        
        print(f"🔍 Investigating JSON structure for game: {game_id}")
        print("=" * 60)
        
        # Explore top-level structure
        print("\n📋 Top-level JSON keys:")
        if isinstance(raw_json, dict):
            for key in raw_json.keys():
                print(f"  - {key}")
        
        # Navigate to props -> pageProps -> game
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        print(f"\n🎮 Game object keys:")
        if isinstance(game, dict):
            for key in sorted(game.keys()):
                value = game[key]
                if isinstance(value, list):
                    print(f"  - {key}: list with {len(value)} items")
                elif isinstance(value, dict):
                    print(f"  - {key}: dict with {len(value)} keys")
                else:
                    print(f"  - {key}: {type(value).__name__}")
        
        # Look specifically for actions/events
        actions = game.get('actions', [])
        print(f"\n🎬 Actions array: {len(actions)} items")
        
        if actions and len(actions) > 0:
            print("First action sample:")
            pprint(actions[0], depth=2)
        
        # Look for other potential play-by-play locations
        potential_pbp_keys = ['events', 'plays', 'playByPlay', 'gameEvents', 'timeline']
        
        print(f"\n🔎 Searching for play-by-play data...")
        
        def search_nested(obj, path=""):
            """Recursively search for play-by-play data."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if this key might contain play-by-play
                    if any(pbp_key.lower() in key.lower() for pbp_key in potential_pbp_keys):
                        if isinstance(value, list) and len(value) > 0:
                            print(f"  🎯 Found potential PBP: {current_path} (list with {len(value)} items)")
                            if len(value) > 0:
                                print(f"      Sample item keys: {list(value[0].keys()) if isinstance(value[0], dict) else type(value[0])}")
                        elif isinstance(value, dict) and len(value) > 0:
                            print(f"  🎯 Found potential PBP: {current_path} (dict with {len(value)} keys)")
                    
                    # Continue searching if reasonable depth
                    if len(path.split('.')) < 4:  # Limit depth to avoid infinite recursion
                        search_nested(value, current_path)
            
            elif isinstance(obj, list) and len(obj) > 0:
                # Check if this is a list of events/actions
                if isinstance(obj[0], dict):
                    sample_keys = list(obj[0].keys())
                    event_indicators = ['action', 'event', 'play', 'time', 'period', 'description']
                    if any(indicator in str(sample_keys).lower() for indicator in event_indicators):
                        print(f"  🎯 Found potential PBP list at {path}: {len(obj)} items")
                        print(f"      Sample keys: {sample_keys}")
        
        search_nested(raw_json)
        
        # Check specific known locations
        print(f"\n🔍 Checking specific locations:")
        
        # Check if actions are nested differently
        if 'actions' in game:
            actions_data = game['actions']
            print(f"  game.actions: {type(actions_data)} with {len(actions_data) if isinstance(actions_data, (list, dict)) else 'N/A'} items")
        
        # Check if there's a different structure for live vs final games
        game_status = game.get('gameStatus', 'unknown')
        game_status_text = game.get('gameStatusText', 'unknown')
        print(f"  Game status: {game_status} ({game_status_text})")
        
        # Look in team data for plays
        home_team = game.get('homeTeam', {})
        away_team = game.get('awayTeam', {})
        
        print(f"\n👥 Team data structure:")
        print(f"  Home team keys: {list(home_team.keys()) if isinstance(home_team, dict) else 'N/A'}")
        print(f"  Away team keys: {list(away_team.keys()) if isinstance(away_team, dict) else 'N/A'}")
        
        # Check for periods/quarters data
        periods = game.get('period')
        if isinstance(periods, int):
            print(f"\n⏱️ Current period: {periods}")
            # Look for period-specific data
            for i in range(1, periods + 1):
                period_key = f"period{i}"
                if period_key in game:
                    print(f"  Found {period_key}: {type(game[period_key])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error investigating JSON: {e}")
        return False
        
    finally:
        parser.close()


def compare_multiple_games():
    """Compare JSON structure across multiple games to find patterns."""
    parser = JSONGameParser()
    session = SessionLocal()
    
    try:
        # Get multiple games
        result = session.execute(text("SELECT game_id FROM raw_game_data LIMIT 5"))
        game_ids = [row[0] for row in result.fetchall()]
        
        print(f"🔍 Comparing {len(game_ids)} games for play-by-play patterns")
        print("=" * 70)
        
        for i, game_id in enumerate(game_ids, 1):
            print(f"\n{i}. Game {game_id}:")
            
            try:
                _, raw_json = parser.get_sample_game(game_id)
                
                props = raw_json.get('props', {})
                page_props = props.get('pageProps', {})
                game = page_props.get('game', {})
                
                # Quick stats
                actions = game.get('actions', [])
                game_status = game.get('gameStatusText', 'Unknown')
                
                print(f"   Status: {game_status}")
                print(f"   Actions: {len(actions)} items")
                
                # Look for any arrays that might be play-by-play
                for key, value in game.items():
                    if isinstance(value, list) and len(value) > 10:  # Likely to be events
                        print(f"   Large array '{key}': {len(value)} items")
                        if len(value) > 0 and isinstance(value[0], dict):
                            sample_keys = list(value[0].keys())
                            print(f"      Sample keys: {sample_keys[:5]}...")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error comparing games: {e}")
        
    finally:
        parser.close()


def check_test_data_files():
    """Check the test data files to see if they have play-by-play data."""
    test_data_dir = Path(__file__).parent / "data"
    
    if not test_data_dir.exists():
        print("❌ Test data directory not found")
        return
    
    json_files = list(test_data_dir.glob("*.json"))
    
    if not json_files:
        print("❌ No JSON test files found")
        return
    
    print(f"🔍 Checking {len(json_files)} test data files for play-by-play")
    print("=" * 60)
    
    for json_file in json_files[:3]:  # Check first 3 files
        print(f"\n📄 File: {json_file.name}")
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Navigate to game data
            props = data.get('props', {})
            page_props = props.get('pageProps', {})
            game = page_props.get('game', {})
            
            actions = game.get('actions', [])
            print(f"   Actions: {len(actions)} items")
            
            if actions and len(actions) > 0:
                print("   Sample action:")
                pprint(actions[0], depth=1, width=60)
            
            # Look for other potential arrays
            for key, value in game.items():
                if isinstance(value, list) and len(value) > 5:
                    print(f"   Array '{key}': {len(value)} items")
            
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")


def main():
    """Main investigation function."""
    print("🏀 Play-by-Play Data Investigation")
    print("=" * 50)
    
    # Get a sample game from database
    session = SessionLocal()
    result = session.execute(text("SELECT game_id FROM raw_game_data LIMIT 1"))
    sample_game = result.fetchone()
    session.close()
    
    if sample_game:
        game_id = sample_game[0]
        
        print("\n1️⃣ Deep JSON Structure Investigation")
        investigate_json_structure(game_id)
        
        print("\n2️⃣ Multiple Games Comparison")
        compare_multiple_games()
    
    print("\n3️⃣ Test Data Files Investigation")
    check_test_data_files()


if __name__ == "__main__":
    main()