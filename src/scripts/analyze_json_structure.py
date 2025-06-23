"""Analyze JSON structure to find player data location."""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

def analyze_json_structure():
    """Analyze the structure of raw JSON to find player data."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get a few recent games to analyze
        cur.execute("""
            SELECT game_id, raw_json 
            FROM raw_game_data 
            WHERE raw_json IS NOT NULL 
            ORDER BY game_id DESC 
            LIMIT 3
        """)
        games = cur.fetchall()
        
        for i, game in enumerate(games):
            print(f"\n{'='*60}")
            print(f"ANALYZING GAME {game['game_id']} (Sample {i+1})")
            print(f"{'='*60}")
            
            try:
                # raw_json might already be parsed as dict
                if isinstance(game['raw_json'], dict):
                    data = game['raw_json']
                else:
                    data = json.loads(game['raw_json'])
                analyze_structure(data, "", 0, max_depth=4)
                
                # Look specifically for player data
                print(f"\n🔍 SEARCHING FOR PLAYER DATA IN GAME {game['game_id']}:")
                find_player_data(data, "")
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error for game {game['game_id']}: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


def analyze_structure(obj, path, depth, max_depth=3):
    """Recursively analyze JSON structure."""
    if depth > max_depth:
        return
        
    indent = "  " * depth
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                print(f"{indent}{key}: dict ({len(value)} keys)")
                if depth < max_depth:
                    analyze_structure(value, key_path, depth + 1, max_depth)
            elif isinstance(value, list):
                print(f"{indent}{key}: list ({len(value)} items)")
                if len(value) > 0 and depth < max_depth:
                    print(f"{indent}  First item type: {type(value[0]).__name__}")
                    if isinstance(value[0], dict):
                        print(f"{indent}  First item keys: {list(value[0].keys())}")
            else:
                value_str = str(value)[:50]
                print(f"{indent}{key}: {type(value).__name__} = {value_str}")
    elif isinstance(obj, list):
        print(f"{indent}List with {len(obj)} items")
        if len(obj) > 0:
            print(f"{indent}First item type: {type(obj[0]).__name__}")


def find_player_data(obj, path):
    """Recursively search for player data."""
    
    if isinstance(obj, dict):
        # Check if this looks like player data
        if has_player_indicators(obj):
            print(f"🏀 FOUND POTENTIAL PLAYER DATA at {path}")
            print(f"   Keys: {list(obj.keys())}")
            
            # Show sample data
            for key, value in obj.items():
                if any(indicator in key.lower() for indicator in ['name', 'person', 'player', 'jersey']):
                    print(f"   {key}: {value}")
            print()
        
        # Check if this looks like team data with players
        if has_team_with_players_indicators(obj):
            print(f"🏆 FOUND POTENTIAL TEAM DATA WITH PLAYERS at {path}")
            print(f"   Keys: {list(obj.keys())}")
            
            # Look for player arrays
            for key, value in obj.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and has_player_indicators(value[0]):
                        print(f"   {key}: list of {len(value)} players")
                        print(f"   Sample player keys: {list(value[0].keys())}")
            print()
        
        # Recurse into nested objects
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            find_player_data(value, new_path)
            
    elif isinstance(obj, list):
        # Check if this is a list of players
        if len(obj) > 0 and isinstance(obj[0], dict) and has_player_indicators(obj[0]):
            print(f"👥 FOUND PLAYER LIST at {path}")
            print(f"   {len(obj)} players")
            print(f"   Sample player keys: {list(obj[0].keys())}")
            
            # Show a few examples
            for i, player in enumerate(obj[:3]):
                name = player.get('name') or f"{player.get('firstName', '')} {player.get('lastName', '')}"
                person_id = player.get('personId') or player.get('playerId')
                print(f"   Player {i+1}: {name} (ID: {person_id})")
            print()
        
        # Recurse into list items
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                find_player_data(item, f"{path}[{i}]")


def has_player_indicators(obj):
    """Check if object has indicators that it contains player data."""
    if not isinstance(obj, dict):
        return False
        
    player_keys = {'personid', 'playerid', 'firstname', 'lastname', 'name', 'jersey', 'position'}
    obj_keys_lower = {key.lower() for key in obj.keys()}
    
    # Must have at least 2 player-related keys
    return len(player_keys.intersection(obj_keys_lower)) >= 2


def has_team_with_players_indicators(obj):
    """Check if object has indicators that it contains team data with players."""
    if not isinstance(obj, dict):
        return False
        
    team_keys = {'teamcode', 'teamtricode', 'teamid'}
    player_list_keys = {'players', 'roster', 'lineup'}
    
    obj_keys_lower = {key.lower() for key in obj.keys()}
    
    has_team_indicator = len(team_keys.intersection(obj_keys_lower)) > 0
    has_player_list = len(player_list_keys.intersection(obj_keys_lower)) > 0
    
    return has_team_indicator and has_player_list


if __name__ == "__main__":
    analyze_json_structure()