"""Fix team data with actual NBA team information."""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

# Actual NBA team data
NBA_TEAMS = {
    'ATL': {'city': 'Atlanta', 'name': 'Hawks', 'conference': 'Eastern', 'division': 'Southeast'},
    'BOS': {'city': 'Boston', 'name': 'Celtics', 'conference': 'Eastern', 'division': 'Atlantic'},
    'BKN': {'city': 'Brooklyn', 'name': 'Nets', 'conference': 'Eastern', 'division': 'Atlantic'},
    'CHA': {'city': 'Charlotte', 'name': 'Hornets', 'conference': 'Eastern', 'division': 'Southeast'},
    'CHI': {'city': 'Chicago', 'name': 'Bulls', 'conference': 'Eastern', 'division': 'Central'},
    'CLE': {'city': 'Cleveland', 'name': 'Cavaliers', 'conference': 'Eastern', 'division': 'Central'},
    'DAL': {'city': 'Dallas', 'name': 'Mavericks', 'conference': 'Western', 'division': 'Southwest'},
    'DEN': {'city': 'Denver', 'name': 'Nuggets', 'conference': 'Western', 'division': 'Northwest'},
    'DET': {'city': 'Detroit', 'name': 'Pistons', 'conference': 'Eastern', 'division': 'Central'},
    'GSW': {'city': 'Golden State', 'name': 'Warriors', 'conference': 'Western', 'division': 'Pacific'},
    'HOU': {'city': 'Houston', 'name': 'Rockets', 'conference': 'Western', 'division': 'Southwest'},
    'IND': {'city': 'Indiana', 'name': 'Pacers', 'conference': 'Eastern', 'division': 'Central'},
    'LAC': {'city': 'Los Angeles', 'name': 'Clippers', 'conference': 'Western', 'division': 'Pacific'},
    'LAL': {'city': 'Los Angeles', 'name': 'Lakers', 'conference': 'Western', 'division': 'Pacific'},
    'MEM': {'city': 'Memphis', 'name': 'Grizzlies', 'conference': 'Western', 'division': 'Southwest'},
    'MIA': {'city': 'Miami', 'name': 'Heat', 'conference': 'Eastern', 'division': 'Southeast'},
    'MIL': {'city': 'Milwaukee', 'name': 'Bucks', 'conference': 'Eastern', 'division': 'Central'},
    'MIN': {'city': 'Minnesota', 'name': 'Timberwolves', 'conference': 'Western', 'division': 'Northwest'},
    'NOP': {'city': 'New Orleans', 'name': 'Pelicans', 'conference': 'Western', 'division': 'Southwest'},
    'NYK': {'city': 'New York', 'name': 'Knicks', 'conference': 'Eastern', 'division': 'Atlantic'},
    'OKC': {'city': 'Oklahoma City', 'name': 'Thunder', 'conference': 'Western', 'division': 'Northwest'},
    'ORL': {'city': 'Orlando', 'name': 'Magic', 'conference': 'Eastern', 'division': 'Southeast'},
    'PHI': {'city': 'Philadelphia', 'name': '76ers', 'conference': 'Eastern', 'division': 'Atlantic'},
    'PHX': {'city': 'Phoenix', 'name': 'Suns', 'conference': 'Western', 'division': 'Pacific'},
    'POR': {'city': 'Portland', 'name': 'Trail Blazers', 'conference': 'Western', 'division': 'Northwest'},
    'SAC': {'city': 'Sacramento', 'name': 'Kings', 'conference': 'Western', 'division': 'Pacific'},
    'SAS': {'city': 'San Antonio', 'name': 'Spurs', 'conference': 'Western', 'division': 'Southwest'},
    'TOR': {'city': 'Toronto', 'name': 'Raptors', 'conference': 'Eastern', 'division': 'Atlantic'},
    'UTA': {'city': 'Utah', 'name': 'Jazz', 'conference': 'Western', 'division': 'Northwest'},
    'WAS': {'city': 'Washington', 'name': 'Wizards', 'conference': 'Eastern', 'division': 'Southeast'}
}

def fix_team_data():
    """Update teams with correct NBA data."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # First update basic team info
        for tricode, info in NBA_TEAMS.items():
            print(f"Updating {tricode}...")
            
            cur.execute("""
                UPDATE teams 
                SET city = %(city)s,
                    name = %(name)s,
                    nickname = %(name)s,
                    full_name = %(full_name)s,
                    conference = %(conference)s,
                    division = %(division)s,
                    updated_at = NOW()
                WHERE tricode = %(tricode)s
            """, {
                'city': info['city'],
                'name': info['name'],
                'full_name': f"{info['city']} {info['name']}",
                'conference': info['conference'],
                'division': info['division'],
                'tricode': tricode
            })
        
        conn.commit()
        print("Team data fixed!")
        
        # Show updated data
        cur.execute("""
            SELECT tricode, city, name, full_name, conference, division 
            FROM teams 
            ORDER BY conference, division, tricode
        """)
        
        print("\nUpdated teams:")
        for team in cur.fetchall():
            print(f"{team['tricode']}: {team['full_name']} ({team['conference']} - {team['division']})")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    fix_team_data()