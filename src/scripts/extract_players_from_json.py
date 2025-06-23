"""Extract player data from raw JSON game data and populate player_team table."""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

def extract_players_from_raw_json():
    """Extract player data from raw_game_data JSON."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("Extracting player data from raw JSON...")
        
        # Get a sample of raw game data to see the structure
        cur.execute("SELECT game_id, raw_json FROM raw_game_data LIMIT 5")
        sample_games = cur.fetchall()
        
        if not sample_games:
            print("No raw game data found!")
            return
            
        all_players = {}  # person_id -> player_info
        player_teams = defaultdict(set)  # person_id -> set of team_ids
        
        # Process all games to extract player data
        cur.execute("SELECT game_id, raw_json FROM raw_game_data")
        games = cur.fetchall()
        
        print(f"Processing {len(games)} games...")
        
        for i, game in enumerate(games):
            if i % 1000 == 0:
                print(f"  Processed {i}/{len(games)} games...")
                
            try:
                game_data = json.loads(game['raw_json'])
                
                # Navigate through the JSON structure to find player data
                # This might be in different locations depending on the NBA.com structure
                players_data = None
                
                # Try different possible paths for player data
                if 'props' in game_data and 'pageProps' in game_data['props']:
                    page_props = game_data['props']['pageProps']
                    
                    # Look for game data
                    if 'game' in page_props:
                        game_info = page_props['game']
                        
                        # Extract home team players
                        if 'homeTeam' in game_info:
                            home_team = game_info['homeTeam']
                            if 'players' in home_team:
                                extract_team_players(home_team, all_players, player_teams, cur)
                        
                        # Extract away team players  
                        if 'awayTeam' in game_info:
                            away_team = game_info['awayTeam']
                            if 'players' in away_team:
                                extract_team_players(away_team, all_players, player_teams, cur)
                    
                    # Also check for boxscore data
                    if 'boxscore' in page_props:
                        boxscore = page_props['boxscore']
                        if 'homeTeam' in boxscore:
                            home_team = boxscore['homeTeam']
                            if 'players' in home_team:
                                extract_team_players(home_team, all_players, player_teams, cur)
                        if 'awayTeam' in boxscore:
                            away_team = boxscore['awayTeam']
                            if 'players' in away_team:
                                extract_team_players(away_team, all_players, player_teams, cur)
                                
            except (json.JSONDecodeError, KeyError) as e:
                if i < 5:  # Only show errors for first few games
                    print(f"Error processing game {game['game_id']}: {e}")
                continue
        
        print(f"\nFound {len(all_players)} unique players")
        print(f"Found {sum(len(teams) for teams in player_teams.values())} player-team relationships")
        
        if len(all_players) == 0:
            print("No players found in JSON data. Let me examine the structure...")
            examine_json_structure(sample_games[0]['raw_json'])
            return
        
        # Update players table
        print("Updating players table...")
        update_players_table(all_players, cur)
        
        # Update player_team table
        print("Updating player_team table...")
        update_player_team_table(player_teams, cur)
        
        conn.commit()
        
        # Show summary
        show_summary(cur)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def extract_team_players(team_data, all_players, player_teams, cur):
    """Extract players from team data."""
    # Get team ID from database
    team_tricode = team_data.get('teamTricode') or team_data.get('teamCode')
    if not team_tricode:
        return
        
    cur.execute("SELECT id FROM teams WHERE tricode = %s", (team_tricode,))
    team_result = cur.fetchone()
    if not team_result:
        return
    team_id = team_result['id']
    
    players = team_data.get('players', [])
    for player in players:
        person_id = str(player.get('personId') or player.get('playerId', ''))
        if not person_id:
            continue
            
        first_name = player.get('firstName', '').strip()
        last_name = player.get('lastName', '').strip()
        
        if not first_name or not last_name:
            # Try alternative name fields
            full_name = player.get('name', '').strip()
            if full_name and ' ' in full_name:
                name_parts = full_name.split()
                first_name = ' '.join(name_parts[:-1])
                last_name = name_parts[-1]
        
        if first_name and last_name:
            player_name = f"{first_name} {last_name}"
            player_name_i = f"{last_name}, {first_name}"
            
            all_players[person_id] = {
                'person_id': person_id,
                'first_name': first_name,
                'last_name': last_name,
                'player_name': player_name,
                'player_name_i': player_name_i,
                'jersey_number': player.get('jersey', ''),
                'position': player.get('position', '')
            }
            
            player_teams[person_id].add(team_id)


def examine_json_structure(raw_json):
    """Examine the structure of the JSON to find player data."""
    try:
        data = json.loads(raw_json)
        print("\nJSON Structure Analysis:")
        print(f"Top level keys: {list(data.keys())}")
        
        if 'props' in data:
            props = data['props']
            print(f"Props keys: {list(props.keys())}")
            
            if 'pageProps' in props:
                page_props = props['pageProps']
                print(f"PageProps keys: {list(page_props.keys())}")
                
                # Look for any team or player related keys
                for key in page_props:
                    if 'team' in key.lower() or 'player' in key.lower() or 'box' in key.lower():
                        print(f"Found potentially relevant key: {key}")
                        if isinstance(page_props[key], dict):
                            print(f"  {key} sub-keys: {list(page_props[key].keys())}")
                        
    except Exception as e:
        print(f"Error examining JSON: {e}")


def update_players_table(all_players, cur):
    """Update the players table with real data."""
    for person_id, player_data in all_players.items():
        cur.execute("""
            INSERT INTO players (person_id, player_name, player_name_i, first_name, last_name, nba_id)
            VALUES (%(person_id)s, %(player_name)s, %(player_name_i)s, %(first_name)s, %(last_name)s, %(person_id)s)
            ON CONFLICT (nba_id) DO UPDATE SET
                person_id = EXCLUDED.person_id,
                player_name = EXCLUDED.player_name,
                player_name_i = EXCLUDED.player_name_i,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                updated_at = NOW()
        """, player_data)


def update_player_team_table(player_teams, cur):
    """Update the player_team table."""
    # Clear existing data
    cur.execute("DELETE FROM player_team")
    
    for person_id, team_ids in player_teams.items():
        for team_id in team_ids:
            cur.execute("""
                INSERT INTO player_team (person_id, team_id, is_active)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (person_id, team_id, True))


def show_summary(cur):
    """Show summary of the populated data."""
    cur.execute("""
        SELECT COUNT(*) as total_players,
               COUNT(DISTINCT person_id) as unique_person_ids
        FROM players 
        WHERE person_id IS NOT NULL AND person_id != ''
    """)
    player_summary = cur.fetchone()
    
    cur.execute("""
        SELECT COUNT(*) as total_relationships,
               COUNT(DISTINCT person_id) as unique_players,
               COUNT(DISTINCT team_id) as unique_teams
        FROM player_team
    """)
    relationship_summary = cur.fetchone()
    
    print(f"\n✅ Player Data Summary:")
    print(f"Total players: {player_summary['total_players']}")
    print(f"Unique person IDs: {player_summary['unique_person_ids']}")
    
    print(f"\n✅ Player-Team Relationships:")
    print(f"Total relationships: {relationship_summary['total_relationships']}")
    print(f"Unique players: {relationship_summary['unique_players']}")
    print(f"Unique teams: {relationship_summary['unique_teams']}")
    
    # Show some examples
    print("\n📋 Sample player data:")
    cur.execute("""
        SELECT person_id, player_name, player_name_i 
        FROM players 
        WHERE person_id IS NOT NULL AND person_id != ''
        ORDER BY player_name 
        LIMIT 10
    """)
    for player in cur.fetchall():
        print(f"  {player['person_id']}: {player['player_name']} ({player['player_name_i']})")
        
    print("\n🏀 Sample player-team relationships:")
    cur.execute("""
        SELECT pt.person_id, p.player_name, t.tricode, t.full_name
        FROM player_team pt
        JOIN players p ON pt.person_id = p.person_id
        JOIN teams t ON pt.team_id = t.id
        ORDER BY p.player_name
        LIMIT 10
    """)
    for rel in cur.fetchall():
        print(f"  {rel['player_name']} → {rel['tricode']} ({rel['full_name']})")


if __name__ == "__main__":
    extract_players_from_raw_json()