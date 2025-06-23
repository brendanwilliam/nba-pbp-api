"""Populate player_team table for Neon database using existing player_game_stats data."""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

def populate_player_team_neon():
    """Populate player_team table using existing player_game_stats data."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🏀 Creating player-team relationships from player_game_stats...")
        
        # Clear existing player_team data
        cur.execute("DELETE FROM player_team")
        print("   Cleared existing player_team relationships")
        
        # Extract relationships from player_game_stats
        print("\n📊 Extracting relationships from player_game_stats...")
        cur.execute("""
            SELECT DISTINCT 
                p.person_id,
                pgs.team_id as team_table_id,
                pgs.jersey_number,
                pgs.position
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.id
            WHERE p.person_id IS NOT NULL AND p.person_id != ''
        """)
        
        relationships = cur.fetchall()
        print(f"   Found {len(relationships)} unique player-team relationships")
        
        if len(relationships) == 0:
            print("❌ No relationships found! Checking data...")
            # Debug: check what we have
            cur.execute("SELECT COUNT(*) FROM players WHERE person_id IS NOT NULL AND person_id != ''")
            valid_players = cur.fetchone()['count']
            print(f"   Players with person_id: {valid_players}")
            return
        
        # Insert relationships
        print("📝 Inserting player-team relationships...")
        inserted_count = 0
        
        for rel in relationships:
            if rel['person_id']:
                cur.execute("""
                    INSERT INTO player_team (person_id, team_id, is_active)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (rel['person_id'], rel['team_table_id'], True))
                inserted_count += 1
                
                if inserted_count % 1000 == 0:
                    print(f"    Inserted {inserted_count}/{len(relationships)} relationships...")
        
        conn.commit()
        print(f"✅ Successfully inserted {inserted_count} player-team relationships")
        
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
    populate_player_team_neon()