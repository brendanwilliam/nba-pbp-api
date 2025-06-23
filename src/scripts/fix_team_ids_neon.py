"""Fix team_id values in teams table to match NBA team IDs from player_game_stats."""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

# NBA team ID mapping (tricode -> NBA team ID)
NBA_TEAM_IDS = {
    'ATL': 1610612737,
    'BOS': 1610612738,
    'BKN': 1610612751,
    'CHA': 1610612766,
    'CHI': 1610612741,
    'CLE': 1610612739,
    'DAL': 1610612742,
    'DEN': 1610612743,
    'DET': 1610612765,
    'GSW': 1610612744,
    'HOU': 1610612745,
    'IND': 1610612754,
    'LAC': 1610612746,
    'LAL': 1610612747,
    'MEM': 1610612763,
    'MIA': 1610612748,
    'MIL': 1610612749,
    'MIN': 1610612750,
    'NOP': 1610612740,
    'NYK': 1610612752,
    'OKC': 1610612760,
    'ORL': 1610612753,
    'PHI': 1610612755,
    'PHX': 1610612756,
    'POR': 1610612757,
    'SAC': 1610612758,
    'SAS': 1610612759,
    'TOR': 1610612761,
    'UTA': 1610612762,
    'WAS': 1610612764
}

def fix_team_ids():
    """Update team_id column with correct NBA team IDs."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🔧 Fixing team_id values in teams table...")
        
        updated_count = 0
        for tricode, nba_team_id in NBA_TEAM_IDS.items():
            cur.execute("""
                UPDATE teams 
                SET team_id = %s 
                WHERE tricode = %s
            """, (nba_team_id, tricode))
            
            if cur.rowcount > 0:
                updated_count += 1
                print(f"   Updated {tricode}: team_id = {nba_team_id}")
        
        conn.commit()
        print(f"\n✅ Successfully updated {updated_count} teams")
        
        # Verify the update
        print("\n📊 Verification:")
        cur.execute("SELECT tricode, team_id FROM teams ORDER BY tricode")
        for team in cur.fetchall():
            print(f"   {team['tricode']}: {team['team_id']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    fix_team_ids()