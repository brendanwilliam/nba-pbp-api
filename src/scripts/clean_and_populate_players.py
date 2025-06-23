"""Clean existing players data and populate from JSON."""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

def clean_and_populate_players():
    """Clean existing data and populate from JSON."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🧹 Cleaning existing player data...")
        
        # Clear player_team relationships first (foreign key constraint)
        cur.execute("DELETE FROM player_team")
        print("   Cleared player_team table")
        
        # Clear players table
        cur.execute("DELETE FROM players")
        print("   Cleared players table")
        
        # Reset sequences
        cur.execute("ALTER SEQUENCE players_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE player_team_id_seq RESTART WITH 1")
        print("   Reset sequences")
        
        conn.commit()
        
        print("\n🏀 Extracting player data from raw JSON games...")
        
        # Get sample of games to test
        cur.execute("SELECT COUNT(*) FROM raw_game_data WHERE raw_json IS NOT NULL")
        total_games = cur.fetchone()['count']
        print(f"Processing {total_games} games...")
        
        all_players = {}  # person_id -> player_info
        player_teams = defaultdict(set)  # person_id -> set of team_ids
        
        # Process games in batches
        batch_size = 2000
        for offset in range(0, total_games, batch_size):
            print(f"  Processing batch {offset//batch_size + 1}/{(total_games + batch_size - 1)//batch_size}...")
            
            cur.execute("""
                SELECT game_id, raw_json 
                FROM raw_game_data 
                WHERE raw_json IS NOT NULL 
                ORDER BY game_id 
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            
            games = cur.fetchall()
            
            for game in games:
                extract_players_from_game(game, all_players, player_teams, cur)
        
        print(f"\n✅ Found {len(all_players)} unique players")
        print(f"✅ Found {sum(len(teams) for teams in player_teams.values())} player-team relationships")
        
        if len(all_players) == 0:
            print("❌ No players found!")
            return
        
        # Insert new players
        print("\n📝 Inserting players...")
        insert_players(all_players, cur)
        
        # Insert player_team relationships
        print("📝 Inserting player-team relationships...")
        insert_player_teams(player_teams, cur)
        
        conn.commit()
        
        # Show summary
        show_summary(cur)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def extract_players_from_game(game, all_players, player_teams, cur):
    """Extract player data from a single game."""
    try:
        # Handle both string and dict formats
        if isinstance(game['raw_json'], dict):
            game_data = game['raw_json']
        else:
            game_data = json.loads(game['raw_json'])
        
        # Navigate to game data
        if 'props' not in game_data or 'pageProps' not in game_data['props']:
            return
            
        page_props = game_data['props']['pageProps']
        if 'game' not in page_props:
            return
            
        game_info = page_props['game']
        
        # Extract players from home team
        if 'homeTeam' in game_info:
            home_team = game_info['homeTeam']
            extract_team_players(home_team, all_players, player_teams, cur)
        
        # Extract players from away team
        if 'awayTeam' in game_info:
            away_team = game_info['awayTeam']
            extract_team_players(away_team, all_players, player_teams, cur)
            
    except (json.JSONDecodeError, KeyError, TypeError):
        # Silently skip problematic games
        pass


def extract_team_players(team_data, all_players, player_teams, cur):
    """Extract players from team data."""
    # Get team tricode
    team_tricode = team_data.get('teamTricode')
    if not team_tricode:
        return
    
    # Get team ID from database
    cur.execute("SELECT id FROM teams WHERE tricode = %s", (team_tricode,))
    team_result = cur.fetchone()
    if not team_result:
        return
    team_id = team_result['id']
    
    # Extract from players list
    players = team_data.get('players', [])
    for player in players:
        extract_single_player(player, team_id, all_players, player_teams)
    
    # Extract from inactives list
    inactives = team_data.get('inactives', [])
    for player in inactives:
        extract_single_player(player, team_id, all_players, player_teams)


def extract_single_player(player, team_id, all_players, player_teams):
    """Extract data for a single player."""
    person_id = str(player.get('personId', ''))
    if not person_id or person_id == 'None':
        return
    
    first_name = player.get('firstName', '').strip()
    family_name = player.get('familyName', '').strip()
    
    # Handle cases where names might be missing
    if not first_name or not family_name:
        full_name = player.get('name', '').strip()
        if full_name and ' ' in full_name:
            name_parts = full_name.split()
            first_name = ' '.join(name_parts[:-1])
            family_name = name_parts[-1]
        else:
            return  # Skip if we can't get proper names
    
    player_name = f"{first_name} {family_name}"
    player_name_i = f"{family_name}, {first_name}"
    
    # Store player info (update if we already have this player)
    all_players[person_id] = {
        'person_id': person_id,
        'first_name': first_name,
        'last_name': family_name,  # Use familyName as last_name
        'player_name': player_name,
        'player_name_i': player_name_i,
        'jersey_number': str(player.get('jerseyNum', '')),
        'position': player.get('position', '')
    }
    
    # Add team relationship
    player_teams[person_id].add(team_id)


def insert_players(all_players, cur):
    """Insert players into the database."""
    inserted_count = 0
    
    for person_id, player_data in all_players.items():
        cur.execute("""
            INSERT INTO players (person_id, player_name, player_name_i, first_name, last_name, nba_id, jersey_number, position)
            VALUES (%(person_id)s, %(player_name)s, %(player_name_i)s, %(first_name)s, %(last_name)s, %(person_id)s, %(jersey_number)s, %(position)s)
        """, player_data)
        inserted_count += 1
        
        if inserted_count % 500 == 0:
            print(f"    Inserted {inserted_count}/{len(all_players)} players...")
    
    print(f"    ✅ Inserted {inserted_count} players total")


def insert_player_teams(player_teams, cur):
    """Insert player-team relationships."""
    relationship_count = 0
    
    for person_id, team_ids in player_teams.items():
        for team_id in team_ids:
            cur.execute("""
                INSERT INTO player_team (person_id, team_id, is_active)
                VALUES (%s, %s, %s)
            """, (person_id, team_id, True))
            relationship_count += 1
    
    print(f"    ✅ Created {relationship_count} player-team relationships")


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
    
    print(f"\n🎯 FINAL SUMMARY:")
    print(f"{'='*50}")
    print(f"📊 Player Data:")
    print(f"   Total players: {player_summary['total_players']:,}")
    print(f"   Unique person IDs: {player_summary['unique_person_ids']:,}")
    
    print(f"\n🔗 Player-Team Relationships:")
    print(f"   Total relationships: {relationship_summary['total_relationships']:,}")
    print(f"   Unique players: {relationship_summary['unique_players']:,}")
    print(f"   Unique teams: {relationship_summary['unique_teams']:,}")
    
    # Show some examples
    print(f"\n👤 Sample player data:")
    cur.execute("""
        SELECT person_id, player_name, player_name_i 
        FROM players 
        WHERE person_id IS NOT NULL AND person_id != ''
        ORDER BY player_name 
        LIMIT 10
    """)
    for player in cur.fetchall():
        print(f"   {player['person_id']}: {player['player_name']} ({player['player_name_i']})")
        
    print(f"\n🏀 Sample player-team relationships:")
    cur.execute("""
        SELECT pt.person_id, p.player_name, t.tricode, t.full_name
        FROM player_team pt
        JOIN players p ON pt.person_id = p.person_id
        JOIN teams t ON pt.team_id = t.id
        ORDER BY p.player_name
        LIMIT 10
    """)
    for rel in cur.fetchall():
        print(f"   {rel['player_name']} → {rel['tricode']} ({rel['full_name']})")
    
    # Show team distribution
    print(f"\n📈 Players per team:")
    cur.execute("""
        SELECT t.tricode, t.full_name, COUNT(pt.person_id) as player_count
        FROM teams t
        LEFT JOIN player_team pt ON t.id = pt.team_id
        GROUP BY t.id, t.tricode, t.full_name
        ORDER BY player_count DESC, t.tricode
        LIMIT 15
    """)
    for team in cur.fetchall():
        print(f"   {team['tricode']}: {team['player_count']:,} players")


if __name__ == "__main__":
    clean_and_populate_players()