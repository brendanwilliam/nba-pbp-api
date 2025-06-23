"""Simple script to populate player_team table with existing player data."""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

def populate_player_team_simple():
    """Populate player_team table using existing game data relationships."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🏀 Creating player-team relationships from existing game data...")
        
        # Clear existing player_team data
        cur.execute("DELETE FROM player_team")
        print("   Cleared existing player_team relationships")
        
        # Method 1: Use player_game_stats to create relationships
        print("\n📊 Extracting relationships from player_game_stats...")
        cur.execute("""
            SELECT DISTINCT 
                p.person_id,
                pgs.team_id,
                p.jersey_number,
                p.position
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.id
            WHERE p.person_id IS NOT NULL
        """)
        
        game_stats_relationships = cur.fetchall()
        print(f"   Found {len(game_stats_relationships)} relationships from player_game_stats")
        
        # Method 2: Extract from a sample of JSON data for additional players
        print("\n📋 Extracting additional players from JSON sample...")
        cur.execute("""
            SELECT game_id, raw_json 
            FROM raw_game_data 
            WHERE raw_json IS NOT NULL 
            ORDER BY game_id DESC
            LIMIT 1000
        """)
        
        sample_games = cur.fetchall()
        json_players = {}  # person_id -> player_info
        json_player_teams = defaultdict(set)  # person_id -> set of team_ids
        
        for game in sample_games:
            extract_players_from_game(game, json_players, json_player_teams, cur)
        
        print(f"   Found {len(json_players)} additional players from JSON sample")
        
        # Combine both sources
        all_relationships = set()
        
        # Add relationships from player_game_stats
        for rel in game_stats_relationships:
            if rel['person_id']:
                all_relationships.add((rel['person_id'], rel['team_id']))
        
        # Add relationships from JSON data
        for person_id, team_ids in json_player_teams.items():
            for team_id in team_ids:
                all_relationships.add((person_id, team_id))
        
        print(f"\n✅ Total unique player-team relationships: {len(all_relationships)}")
        
        # Insert relationships
        print("📝 Inserting player-team relationships...")
        inserted_count = 0
        
        for person_id, team_id in all_relationships:
            cur.execute("""
                INSERT INTO player_team (person_id, team_id, is_active)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (person_id, team_id, True))
            inserted_count += 1
            
            if inserted_count % 1000 == 0:
                print(f"    Inserted {inserted_count}/{len(all_relationships)} relationships...")
        
        # Update players with better names from JSON where available
        print(f"\n📝 Updating player names from JSON data...")
        updated_names = 0
        
        for person_id, player_data in json_players.items():
            cur.execute("""
                UPDATE players 
                SET person_id = %s,
                    player_name = %s,
                    player_name_i = %s,
                    first_name = %s,
                    last_name = %s,
                    updated_at = NOW()
                WHERE nba_id = %s
            """, (
                person_id,
                player_data['player_name'],
                player_data['player_name_i'],
                player_data['first_name'],
                player_data['last_name'],
                person_id
            ))
            
            if cur.rowcount > 0:
                updated_names += 1
        
        print(f"    Updated {updated_names} player names")
        
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
    """Extract player data from a single game (simplified)."""
    try:
        if isinstance(game['raw_json'], dict):
            game_data = game['raw_json']
        else:
            game_data = json.loads(game['raw_json'])
        
        if 'props' not in game_data or 'pageProps' not in game_data['props']:
            return
            
        page_props = game_data['props']['pageProps']
        if 'game' not in page_props:
            return
            
        game_info = page_props['game']
        
        # Extract from both teams
        for team_key in ['homeTeam', 'awayTeam']:
            if team_key in game_info:
                team_data = game_info[team_key]
                team_tricode = team_data.get('teamTricode')
                
                if team_tricode:
                    # Get team ID
                    cur.execute("SELECT id FROM teams WHERE tricode = %s", (team_tricode,))
                    team_result = cur.fetchone()
                    if not team_result:
                        continue
                    team_id = team_result['id']
                    
                    # Extract players
                    for player_list_key in ['players', 'inactives']:
                        players = team_data.get(player_list_key, [])
                        for player in players:
                            person_id = str(player.get('personId', ''))
                            if not person_id or person_id == 'None':
                                continue
                            
                            first_name = player.get('firstName', '').strip()
                            family_name = player.get('familyName', '').strip()
                            
                            if first_name and family_name:
                                player_name = f"{first_name} {family_name}"
                                player_name_i = f"{family_name}, {first_name}"
                                
                                all_players[person_id] = {
                                    'person_id': person_id,
                                    'first_name': first_name,
                                    'last_name': family_name,
                                    'player_name': player_name,
                                    'player_name_i': player_name_i
                                }
                                
                                player_teams[person_id].add(team_id)
                            
    except (json.JSONDecodeError, KeyError, TypeError):
        pass


def show_summary(cur):
    """Show summary of the populated data."""
    cur.execute("""
        SELECT COUNT(*) as total_relationships,
               COUNT(DISTINCT person_id) as unique_players,
               COUNT(DISTINCT team_id) as unique_teams
        FROM player_team
    """)
    relationship_summary = cur.fetchone()
    
    cur.execute("""
        SELECT COUNT(*) as total_players,
               COUNT(*) FILTER (WHERE person_id IS NOT NULL AND person_id != '') as with_person_id,
               COUNT(*) FILTER (WHERE player_name != ' Player' AND first_name != 'Player') as with_real_names
        FROM players
    """)
    player_summary = cur.fetchone()
    
    print(f"\n🎯 FINAL SUMMARY:")
    print(f"{'='*50}")
    print(f"📊 Player Data:")
    print(f"   Total players in DB: {player_summary['total_players']:,}")
    print(f"   Players with person_id: {player_summary['with_person_id']:,}")
    print(f"   Players with real names: {player_summary['with_real_names']:,}")
    
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
        AND player_name != ' Player' AND first_name != 'Player'
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
        WHERE p.player_name != ' Player' AND p.first_name != 'Player'
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
        LIMIT 10
    """)
    for team in cur.fetchall():
        print(f"   {team['tricode']}: {team['player_count']:,} players")


if __name__ == "__main__":
    populate_player_team_simple()