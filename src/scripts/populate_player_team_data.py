"""Populate player and player_team data from existing game data."""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

def extract_players_from_games():
    """Extract player data from play_events and populate player_team relationships."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("Extracting unique player-team combinations from play_events...")
        
        # Get unique player-team combinations from play_events
        cur.execute("""
            SELECT DISTINCT 
                p.nba_id as person_id,
                p.first_name || ' ' || p.last_name as player_name,
                t.tricode,
                t.id as team_id,
                t.team_id as nba_team_id
            FROM play_events pe
            JOIN players p ON pe.player_id = p.id
            JOIN teams t ON pe.team_id = t.id
            WHERE pe.player_id IS NOT NULL 
            AND p.first_name IS NOT NULL
            AND p.last_name IS NOT NULL
            ORDER BY p.first_name || ' ' || p.last_name
        """)
        
        player_teams = cur.fetchall()
        print(f"Found {len(player_teams)} unique player-team combinations")
        
        # Update players table with real names
        player_updates = {}
        for pt in player_teams:
            person_id = pt['person_id']
            if person_id not in player_updates:
                # Create player name variations
                name_parts = pt['player_name'].strip().split()
                if len(name_parts) >= 2:
                    first_name = ' '.join(name_parts[:-1])
                    last_name = name_parts[-1]
                    player_name = pt['player_name']
                    player_name_i = f"{last_name}, {first_name}"
                else:
                    first_name = pt['player_name']
                    last_name = ''
                    player_name = pt['player_name']
                    player_name_i = pt['player_name']
                
                player_updates[person_id] = {
                    'person_id': person_id,
                    'player_name': player_name,
                    'player_name_i': player_name_i,
                    'first_name': first_name,
                    'last_name': last_name
                }
        
        print(f"Updating {len(player_updates)} unique players...")
        
        # Insert or update players
        for person_id, data in player_updates.items():
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
            """, data)
        
        # Clear existing player_team relationships
        cur.execute("DELETE FROM player_team")
        
        # Insert player_team relationships
        print("Creating player-team relationships...")
        relationships_added = 0
        
        for pt in player_teams:
            # Get the internal player ID
            cur.execute("SELECT id FROM players WHERE person_id = %s", (pt['person_id'],))
            player_result = cur.fetchone()
            
            if player_result:
                cur.execute("""
                    INSERT INTO player_team (person_id, team_id, is_active)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (pt['person_id'], pt['team_id'], True))
                relationships_added += 1
        
        conn.commit()
        
        # Show summary
        cur.execute("""
            SELECT COUNT(*) as total_players,
                   COUNT(DISTINCT person_id) as unique_person_ids
            FROM players 
            WHERE person_id IS NOT NULL
        """)
        player_summary = cur.fetchone()
        
        cur.execute("""
            SELECT COUNT(*) as total_relationships,
                   COUNT(DISTINCT person_id) as unique_players,
                   COUNT(DISTINCT team_id) as unique_teams
            FROM player_team
        """)
        relationship_summary = cur.fetchone()
        
        print(f"\nPlayer Data Summary:")
        print(f"Total players: {player_summary['total_players']}")
        print(f"Unique person IDs: {player_summary['unique_person_ids']}")
        
        print(f"\nPlayer-Team Relationships:")
        print(f"Total relationships: {relationship_summary['total_relationships']}")
        print(f"Unique players: {relationship_summary['unique_players']}")
        print(f"Unique teams: {relationship_summary['unique_teams']}")
        
        # Show some examples
        print("\nSample player data:")
        cur.execute("""
            SELECT person_id, player_name, player_name_i 
            FROM players 
            WHERE person_id IS NOT NULL 
            ORDER BY player_name 
            LIMIT 10
        """)
        for player in cur.fetchall():
            print(f"  {player['person_id']}: {player['player_name']} ({player['player_name_i']})")
            
        print("\nSample player-team relationships:")
        cur.execute("""
            SELECT pt.person_id, p.player_name, t.tricode, t.full_name
            FROM player_team pt
            JOIN players p ON pt.person_id = p.person_id
            JOIN teams t ON pt.team_id = t.id
            ORDER BY p.player_name
            LIMIT 10
        """)
        for rel in cur.fetchall():
            print(f"  {rel['player_name']} -> {rel['tricode']} ({rel['full_name']})")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    extract_players_from_games()