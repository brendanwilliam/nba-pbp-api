#!/usr/bin/env python3
"""
Script to fix teams table with 100% accurate NBA team ID mappings.
Based on official NBA.com team IDs and verified against actual game data.
"""

import asyncio
import asyncpg
import os

# CORRECT NBA Team ID mappings (verified against NBA.com and game data)
NBA_TEAMS_CORRECT = {
    1610612737: {
        "tricode": "ATL", "full_name": "Atlanta Hawks", "city": "Atlanta", "nickname": "Hawks",
        "conference": "Eastern", "division": "Southeast", "founded": 1946,
        "arena": "State Farm Arena", "arena_capacity": 16600
    },
    1610612738: {
        "tricode": "BOS", "full_name": "Boston Celtics", "city": "Boston", "nickname": "Celtics",
        "conference": "Eastern", "division": "Atlantic", "founded": 1946,
        "arena": "TD Garden", "arena_capacity": 19156
    },
    1610612751: {
        "tricode": "BKN", "full_name": "Brooklyn Nets", "city": "Brooklyn", "nickname": "Nets",
        "conference": "Eastern", "division": "Atlantic", "founded": 1967,
        "arena": "Barclays Center", "arena_capacity": 17732
    },
    1610612766: {
        "tricode": "CHA", "full_name": "Charlotte Hornets", "city": "Charlotte", "nickname": "Hornets",
        "conference": "Eastern", "division": "Southeast", "founded": 1988,
        "arena": "Spectrum Center", "arena_capacity": 19077
    },
    1610612741: {
        "tricode": "CHI", "full_name": "Chicago Bulls", "city": "Chicago", "nickname": "Bulls",
        "conference": "Eastern", "division": "Central", "founded": 1966,
        "arena": "United Center", "arena_capacity": 20917
    },
    1610612739: {
        "tricode": "CLE", "full_name": "Cleveland Cavaliers", "city": "Cleveland", "nickname": "Cavaliers",
        "conference": "Eastern", "division": "Central", "founded": 1970,
        "arena": "Rocket Mortgage FieldHouse", "arena_capacity": 19432
    },
    1610612742: {
        "tricode": "DAL", "full_name": "Dallas Mavericks", "city": "Dallas", "nickname": "Mavericks",
        "conference": "Western", "division": "Southwest", "founded": 1980,
        "arena": "American Airlines Center", "arena_capacity": 19200
    },
    1610612743: {
        "tricode": "DEN", "full_name": "Denver Nuggets", "city": "Denver", "nickname": "Nuggets",
        "conference": "Western", "division": "Northwest", "founded": 1967,
        "arena": "Ball Arena", "arena_capacity": 19520
    },
    1610612765: {
        "tricode": "DET", "full_name": "Detroit Pistons", "city": "Detroit", "nickname": "Pistons",
        "conference": "Eastern", "division": "Central", "founded": 1941,
        "arena": "Little Caesars Arena", "arena_capacity": 20332
    },
    1610612744: {
        "tricode": "GSW", "full_name": "Golden State Warriors", "city": "San Francisco", "nickname": "Warriors",
        "conference": "Western", "division": "Pacific", "founded": 1946,
        "arena": "Chase Center", "arena_capacity": 18064
    },
    1610612745: {
        "tricode": "HOU", "full_name": "Houston Rockets", "city": "Houston", "nickname": "Rockets",
        "conference": "Western", "division": "Southwest", "founded": 1967,
        "arena": "Toyota Center", "arena_capacity": 18055
    },
    1610612754: {
        "tricode": "IND", "full_name": "Indiana Pacers", "city": "Indianapolis", "nickname": "Pacers",
        "conference": "Eastern", "division": "Central", "founded": 1967,
        "arena": "Gainbridge Fieldhouse", "arena_capacity": 17274
    },
    1610612746: {
        "tricode": "LAC", "full_name": "Los Angeles Clippers", "city": "Los Angeles", "nickname": "Clippers",
        "conference": "Western", "division": "Pacific", "founded": 1970,
        "arena": "Crypto.com Arena", "arena_capacity": 20000
    },
    1610612747: {
        "tricode": "LAL", "full_name": "Los Angeles Lakers", "city": "Los Angeles", "nickname": "Lakers",
        "conference": "Western", "division": "Pacific", "founded": 1947,
        "arena": "Crypto.com Arena", "arena_capacity": 20000
    },
    1610612763: {
        "tricode": "MEM", "full_name": "Memphis Grizzlies", "city": "Memphis", "nickname": "Grizzlies",
        "conference": "Western", "division": "Southwest", "founded": 1995,
        "arena": "FedExForum", "arena_capacity": 17794
    },
    1610612748: {
        "tricode": "MIA", "full_name": "Miami Heat", "city": "Miami", "nickname": "Heat",
        "conference": "Eastern", "division": "Southeast", "founded": 1988,
        "arena": "Kaseya Center", "arena_capacity": 19600
    },
    1610612749: {
        "tricode": "MIL", "full_name": "Milwaukee Bucks", "city": "Milwaukee", "nickname": "Bucks",
        "conference": "Eastern", "division": "Central", "founded": 1968,
        "arena": "Fiserv Forum", "arena_capacity": 17500
    },
    1610612750: {
        "tricode": "MIN", "full_name": "Minnesota Timberwolves", "city": "Minneapolis", "nickname": "Timberwolves",
        "conference": "Western", "division": "Northwest", "founded": 1989,
        "arena": "Target Center", "arena_capacity": 19356
    },
    1610612740: {
        "tricode": "NOP", "full_name": "New Orleans Pelicans", "city": "New Orleans", "nickname": "Pelicans",
        "conference": "Western", "division": "Southwest", "founded": 1988,
        "arena": "Smoothie King Center", "arena_capacity": 16867
    },
    1610612752: {
        "tricode": "NYK", "full_name": "New York Knicks", "city": "New York", "nickname": "Knicks",
        "conference": "Eastern", "division": "Atlantic", "founded": 1946,
        "arena": "Madison Square Garden", "arena_capacity": 20789
    },
    1610612760: {
        "tricode": "OKC", "full_name": "Oklahoma City Thunder", "city": "Oklahoma City", "nickname": "Thunder",
        "conference": "Western", "division": "Northwest", "founded": 1967,
        "arena": "Paycom Center", "arena_capacity": 18203
    },
    1610612753: {
        "tricode": "ORL", "full_name": "Orlando Magic", "city": "Orlando", "nickname": "Magic",
        "conference": "Eastern", "division": "Southeast", "founded": 1989,
        "arena": "Kia Center", "arena_capacity": 18846
    },
    1610612755: {
        "tricode": "PHI", "full_name": "Philadelphia 76ers", "city": "Philadelphia", "nickname": "76ers",
        "conference": "Eastern", "division": "Atlantic", "founded": 1946,
        "arena": "Wells Fargo Center", "arena_capacity": 20478
    },
    1610612756: {  # CORRECTED: This is Phoenix Suns, NOT Seattle SuperSonics
        "tricode": "PHX", "full_name": "Phoenix Suns", "city": "Phoenix", "nickname": "Suns",
        "conference": "Western", "division": "Pacific", "founded": 1968,
        "arena": "Footprint Center", "arena_capacity": 17071
    },
    1610612757: {
        "tricode": "POR", "full_name": "Portland Trail Blazers", "city": "Portland", "nickname": "Trail Blazers",
        "conference": "Western", "division": "Northwest", "founded": 1970,
        "arena": "Moda Center", "arena_capacity": 19393
    },
    1610612758: {
        "tricode": "SAC", "full_name": "Sacramento Kings", "city": "Sacramento", "nickname": "Kings",
        "conference": "Western", "division": "Pacific", "founded": 1945,
        "arena": "Golden 1 Center", "arena_capacity": 17608
    },
    1610612759: {
        "tricode": "SAS", "full_name": "San Antonio Spurs", "city": "San Antonio", "nickname": "Spurs",
        "conference": "Western", "division": "Southwest", "founded": 1967,
        "arena": "Frost Bank Center", "arena_capacity": 18418
    },
    1610612761: {
        "tricode": "TOR", "full_name": "Toronto Raptors", "city": "Toronto", "nickname": "Raptors",
        "conference": "Eastern", "division": "Atlantic", "founded": 1995,
        "arena": "Scotiabank Arena", "arena_capacity": 19800
    },
    1610612762: {
        "tricode": "UTA", "full_name": "Utah Jazz", "city": "Salt Lake City", "nickname": "Jazz",
        "conference": "Western", "division": "Northwest", "founded": 1974,
        "arena": "Delta Center", "arena_capacity": 18306
    },
    1610612764: {
        "tricode": "WAS", "full_name": "Washington Wizards", "city": "Washington", "nickname": "Wizards",
        "conference": "Eastern", "division": "Southeast", "founded": 1961,
        "arena": "Capital One Arena", "arena_capacity": 20356
    }
}

async def fix_teams_table_accurate():
    """Fix teams table with 100% accurate NBA team mappings"""
    
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/nba_pbp')
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🏀 Fixing teams table with accurate NBA team mappings...")
        
        # Clear current teams table
        print("🗑️  Clearing current teams table...")
        await conn.execute("DELETE FROM teams")
        
        # Insert correct team mappings
        print("📝 Inserting correct NBA teams...")
        for team_id, team_data in NBA_TEAMS_CORRECT.items():
            await conn.execute("""
            INSERT INTO teams (
                team_id, tricode, full_name, city, nickname,
                conference, division, founded, arena, arena_capacity, active_years
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, team_id, team_data["tricode"], team_data["full_name"], team_data["city"],
            team_data["nickname"], team_data.get("conference"), team_data.get("division"),
            team_data.get("founded"), team_data.get("arena"), team_data.get("arena_capacity"),
            "current")
        
        # Verify the corrections
        print("✅ Verifying corrections...")
        key_teams = await conn.fetch("""
        SELECT team_id, tricode, full_name 
        FROM teams 
        WHERE team_id IN (1610612756, 1610612747, 1610612738)
        ORDER BY team_id
        """)
        
        print("   Key team verifications:")
        for team in key_teams:
            print(f"   - {team['team_id']}: {team['tricode']} = {team['full_name']}")
        
        # Count total teams
        total_teams = await conn.fetchval("SELECT COUNT(*) FROM teams")
        print(f"   Total teams: {total_teams}")
        
        print("🎉 Teams table fixed with accurate mappings!")
        
    except Exception as e:
        print(f"❌ Error fixing teams table: {e}")
        raise e
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_teams_table_accurate())