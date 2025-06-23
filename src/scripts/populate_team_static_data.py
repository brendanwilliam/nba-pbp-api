"""Populate team data with static NBA information."""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

# Complete NBA team data
NBA_TEAM_DATA = {
    'ATL': {
        'full_name': 'Atlanta Hawks',
        'founded': 1946,
        'arena': 'State Farm Arena',
        'arena_capacity': 18118,
        'owner': 'Tony Ressler',
        'general_manager': 'Landry Fields',
        'head_coach': 'Quin Snyder',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Atlanta_Hawks',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/ATL/'
    },
    'BOS': {
        'full_name': 'Boston Celtics',
        'founded': 1946,
        'arena': 'TD Garden',
        'arena_capacity': 19156,
        'owner': 'Wyc Grousbeck',
        'general_manager': 'Brad Stevens',
        'head_coach': 'Joe Mazzulla',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Boston_Celtics',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/BOS/'
    },
    'BKN': {
        'full_name': 'Brooklyn Nets',
        'founded': 1967,
        'arena': 'Barclays Center',
        'arena_capacity': 17732,
        'owner': 'Joe Tsai',
        'general_manager': 'Sean Marks',
        'head_coach': 'Jordi Fernandez',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Brooklyn_Nets',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/BRK/'
    },
    'CHA': {
        'full_name': 'Charlotte Hornets',
        'founded': 1988,
        'arena': 'Spectrum Center',
        'arena_capacity': 19077,
        'owner': 'Michael Jordan',
        'general_manager': 'Mitch Kupchak',
        'head_coach': 'Charles Lee',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Charlotte_Hornets',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/CHO/'
    },
    'CHI': {
        'full_name': 'Chicago Bulls',
        'founded': 1966,
        'arena': 'United Center',
        'arena_capacity': 20917,
        'owner': 'Jerry Reinsdorf',
        'general_manager': 'Arturas Karnisovas',
        'head_coach': 'Billy Donovan',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Chicago_Bulls',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/CHI/'
    },
    'CLE': {
        'full_name': 'Cleveland Cavaliers',
        'founded': 1970,
        'arena': 'Rocket Mortgage FieldHouse',
        'arena_capacity': 19432,
        'owner': 'Dan Gilbert',
        'general_manager': 'Koby Altman',
        'head_coach': 'Kenny Atkinson',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Cleveland_Cavaliers',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/CLE/'
    },
    'DAL': {
        'full_name': 'Dallas Mavericks',
        'founded': 1980,
        'arena': 'American Airlines Center',
        'arena_capacity': 19200,
        'owner': 'Mark Cuban',
        'general_manager': 'Nico Harrison',
        'head_coach': 'Jason Kidd',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Dallas_Mavericks',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/DAL/'
    },
    'DEN': {
        'full_name': 'Denver Nuggets',
        'founded': 1967,
        'arena': 'Ball Arena',
        'arena_capacity': 19520,
        'owner': 'Stan Kroenke',
        'general_manager': 'Calvin Booth',
        'head_coach': 'Michael Malone',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Denver_Nuggets',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/DEN/'
    },
    'DET': {
        'full_name': 'Detroit Pistons',
        'founded': 1941,
        'arena': 'Little Caesars Arena',
        'arena_capacity': 20332,
        'owner': 'Tom Gores',
        'general_manager': 'Troy Weaver',
        'head_coach': 'J.B. Bickerstaff',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Detroit_Pistons',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/DET/'
    },
    'GSW': {
        'full_name': 'Golden State Warriors',
        'founded': 1946,
        'arena': 'Chase Center',
        'arena_capacity': 18064,
        'owner': 'Joe Lacob',
        'general_manager': 'Mike Dunleavy Jr.',
        'head_coach': 'Steve Kerr',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Golden_State_Warriors',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/GSW/'
    },
    'HOU': {
        'full_name': 'Houston Rockets',
        'founded': 1967,
        'arena': 'Toyota Center',
        'arena_capacity': 18055,
        'owner': 'Tilman Fertitta',
        'general_manager': 'Rafael Stone',
        'head_coach': 'Ime Udoka',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Houston_Rockets',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/HOU/'
    },
    'IND': {
        'full_name': 'Indiana Pacers',
        'founded': 1967,
        'arena': 'Gainbridge Fieldhouse',
        'arena_capacity': 17923,
        'owner': 'Herb Simon',
        'general_manager': 'Chad Buchanan',
        'head_coach': 'Rick Carlisle',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Indiana_Pacers',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/IND/'
    },
    'LAC': {
        'full_name': 'Los Angeles Clippers',
        'founded': 1970,
        'arena': 'Crypto.com Arena',
        'arena_capacity': 19060,
        'owner': 'Steve Ballmer',
        'general_manager': 'Lawrence Frank',
        'head_coach': 'Tyronn Lue',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Los_Angeles_Clippers',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/LAC/'
    },
    'LAL': {
        'full_name': 'Los Angeles Lakers',
        'founded': 1947,
        'arena': 'Crypto.com Arena',
        'arena_capacity': 18997,
        'owner': 'Jeanie Buss',
        'general_manager': 'Rob Pelinka',
        'head_coach': 'JJ Redick',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Los_Angeles_Lakers',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/LAL/'
    },
    'MEM': {
        'full_name': 'Memphis Grizzlies',
        'founded': 1995,
        'arena': 'FedExForum',
        'arena_capacity': 18119,
        'owner': 'Robert Pera',
        'general_manager': 'Zach Kleiman',
        'head_coach': 'Taylor Jenkins',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Memphis_Grizzlies',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/MEM/'
    },
    'MIA': {
        'full_name': 'Miami Heat',
        'founded': 1988,
        'arena': 'Kaseya Center',
        'arena_capacity': 19600,
        'owner': 'Micky Arison',
        'general_manager': 'Pat Riley',
        'head_coach': 'Erik Spoelstra',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Miami_Heat',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/MIA/'
    },
    'MIL': {
        'full_name': 'Milwaukee Bucks',
        'founded': 1968,
        'arena': 'Fiserv Forum',
        'arena_capacity': 17500,
        'owner': 'Marc Lasry',
        'general_manager': 'Jon Horst',
        'head_coach': 'Doc Rivers',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Milwaukee_Bucks',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/MIL/'
    },
    'MIN': {
        'full_name': 'Minnesota Timberwolves',
        'founded': 1989,
        'arena': 'Target Center',
        'arena_capacity': 19356,
        'owner': 'Glen Taylor',
        'general_manager': 'Tim Connelly',
        'head_coach': 'Chris Finch',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Minnesota_Timberwolves',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/MIN/'
    },
    'NOP': {
        'full_name': 'New Orleans Pelicans',
        'founded': 1988,
        'arena': 'Smoothie King Center',
        'arena_capacity': 16867,
        'owner': 'Gayle Benson',
        'general_manager': 'Trajan Langdon',
        'head_coach': 'Willie Green',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/New_Orleans_Pelicans',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/NOP/'
    },
    'NYK': {
        'full_name': 'New York Knicks',
        'founded': 1946,
        'arena': 'Madison Square Garden',
        'arena_capacity': 20789,
        'owner': 'James Dolan',
        'general_manager': 'Leon Rose',
        'head_coach': 'Tom Thibodeau',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/New_York_Knicks',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/NYK/'
    },
    'OKC': {
        'full_name': 'Oklahoma City Thunder',
        'founded': 1967,
        'arena': 'Paycom Center',
        'arena_capacity': 18203,
        'owner': 'Clay Bennett',
        'general_manager': 'Sam Presti',
        'head_coach': 'Mark Daigneault',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Oklahoma_City_Thunder',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/OKC/'
    },
    'ORL': {
        'full_name': 'Orlando Magic',
        'founded': 1989,
        'arena': 'Kia Center',
        'arena_capacity': 18846,
        'owner': 'Dan DeVos',
        'general_manager': 'John Hammond',
        'head_coach': 'Jamahl Mosley',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Orlando_Magic',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/ORL/'
    },
    'PHI': {
        'full_name': 'Philadelphia 76ers',
        'founded': 1949,
        'arena': 'Wells Fargo Center',
        'arena_capacity': 20318,
        'owner': 'Josh Harris',
        'general_manager': 'Daryl Morey',
        'head_coach': 'Nick Nurse',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Philadelphia_76ers',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/PHI/'
    },
    'PHX': {
        'full_name': 'Phoenix Suns',
        'founded': 1968,
        'arena': 'Footprint Center',
        'arena_capacity': 17071,
        'owner': 'Mat Ishbia',
        'general_manager': 'James Jones',
        'head_coach': 'Mike Budenholzer',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Phoenix_Suns',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/PHO/'
    },
    'POR': {
        'full_name': 'Portland Trail Blazers',
        'founded': 1970,
        'arena': 'Moda Center',
        'arena_capacity': 19393,
        'owner': 'Jody Allen',
        'general_manager': 'Joe Cronin',
        'head_coach': 'Chauncey Billups',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Portland_Trail_Blazers',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/POR/'
    },
    'SAC': {
        'full_name': 'Sacramento Kings',
        'founded': 1945,
        'arena': 'Golden 1 Center',
        'arena_capacity': 17608,
        'owner': 'Vivek Ranadive',
        'general_manager': 'Monte McNair',
        'head_coach': 'Mike Brown',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Sacramento_Kings',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/SAC/'
    },
    'SAS': {
        'full_name': 'San Antonio Spurs',
        'founded': 1967,
        'arena': 'Frost Bank Center',
        'arena_capacity': 18354,
        'owner': 'Peter Holt',
        'general_manager': 'Brian Wright',
        'head_coach': 'Gregg Popovich',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/San_Antonio_Spurs',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/SAS/'
    },
    'TOR': {
        'full_name': 'Toronto Raptors',
        'founded': 1995,
        'arena': 'Scotiabank Arena',
        'arena_capacity': 19800,
        'owner': 'Larry Tanenbaum',
        'general_manager': 'Masai Ujiri',
        'head_coach': 'Darko Rajakovic',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Toronto_Raptors',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/TOR/'
    },
    'UTA': {
        'full_name': 'Utah Jazz',
        'founded': 1974,
        'arena': 'Delta Center',
        'arena_capacity': 18306,
        'owner': 'Ryan Smith',
        'general_manager': 'Justin Zanik',
        'head_coach': 'Will Hardy',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Utah_Jazz',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/UTA/'
    },
    'WAS': {
        'full_name': 'Washington Wizards',
        'founded': 1961,
        'arena': 'Capital One Arena',
        'arena_capacity': 20356,
        'owner': 'Ted Leonsis',
        'general_manager': 'Will Dawkins',
        'head_coach': 'Brian Keefe',
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Washington_Wizards',
        'basketball_ref_url': 'https://www.basketball-reference.com/teams/WAS/'
    }
}

def populate_complete_team_data():
    """Populate teams with complete static data."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        for tricode, data in NBA_TEAM_DATA.items():
            print(f"Updating {tricode} - {data['full_name']}...")
            
            cur.execute("""
                UPDATE teams 
                SET full_name = %(full_name)s,
                    founded = %(founded)s,
                    arena = %(arena)s,
                    arena_capacity = %(arena_capacity)s,
                    owner = %(owner)s,
                    general_manager = %(general_manager)s,
                    head_coach = %(head_coach)s,
                    wikipedia_url = %(wikipedia_url)s,
                    basketball_ref_url = %(basketball_ref_url)s,
                    updated_at = NOW()
                WHERE tricode = %(tricode)s
            """, {**data, 'tricode': tricode})
        
        conn.commit()
        print("\nTeam data population complete!")
        
        # Show summary
        cur.execute("""
            SELECT COUNT(*) as total,
                   COUNT(founded) as with_founded,
                   COUNT(arena) as with_arena,
                   COUNT(owner) as with_owner,
                   COUNT(head_coach) as with_coach
            FROM teams
        """)
        summary = cur.fetchone()
        print(f"\nSummary:")
        print(f"Total teams: {summary['total']}")
        print(f"Teams with founded year: {summary['with_founded']}")
        print(f"Teams with arena: {summary['with_arena']}")
        print(f"Teams with owner: {summary['with_owner']}")
        print(f"Teams with head coach: {summary['with_coach']}")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    populate_complete_team_data()