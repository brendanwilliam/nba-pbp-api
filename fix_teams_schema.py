#!/usr/bin/env python3
"""
Script to fix the teams table structure and populate with proper NBA team data.
This will:
1. Use team_id as the primary key (using NBA team IDs)
2. Add proper team names and information
3. Include historical teams like Seattle SuperSonics
4. Remove the auto-increment id column and nba_team_id column
"""

import asyncio
import asyncpg
import os
from datetime import datetime

# NBA Teams mapping with historical data
NBA_TEAMS = {
    # Current Teams
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
    1610612756: {
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
    },
    
    # Historical Teams (for historical data)
    1610612756: {  # Note: Phoenix Suns ID, but this will be for Seattle
        "tricode": "SEA", "full_name": "Seattle SuperSonics", "city": "Seattle", "nickname": "SuperSonics",
        "conference": "Western", "division": "Northwest", "founded": 1967,
        "arena": "KeyArena", "arena_capacity": 17072,
        "active_years": "1967-2008"
    }
}

async def restructure_teams_table():
    """Restructure the teams table with proper NBA team IDs as primary keys"""
    
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/nba_pbp')
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🏀 Starting teams table restructuring...")
        
        # Step 1: Create backup of current teams table
        print("📄 Creating backup of current teams table...")
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS teams_backup AS 
        SELECT * FROM teams
        """)
        
        # Step 2: Drop current teams table
        print("🗑️  Dropping current teams table...")
        await conn.execute("DROP TABLE IF EXISTS teams CASCADE")
        
        # Step 3: Create new teams table with proper structure
        print("🏗️  Creating new teams table structure...")
        await conn.execute("""
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,  -- NBA team ID as primary key
            tricode VARCHAR(3) NOT NULL UNIQUE,
            full_name VARCHAR(100) NOT NULL,
            city VARCHAR(50) NOT NULL,
            nickname VARCHAR(50) NOT NULL,
            conference VARCHAR(10),
            division VARCHAR(15),
            founded INTEGER,
            arena VARCHAR(100),
            arena_capacity INTEGER,
            active_years VARCHAR(20) DEFAULT 'current',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Step 4: Insert current NBA teams
        print("📝 Inserting current NBA teams...")
        for team_id, team_data in NBA_TEAMS.items():
            if team_data.get("active_years") != "current" and "active_years" not in team_data:
                team_data["active_years"] = "current"
                
            await conn.execute("""
            INSERT INTO teams (
                team_id, tricode, full_name, city, nickname,
                conference, division, founded, arena, arena_capacity, active_years
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (team_id) DO UPDATE SET
                tricode = EXCLUDED.tricode,
                full_name = EXCLUDED.full_name,
                city = EXCLUDED.city,
                nickname = EXCLUDED.nickname,
                conference = EXCLUDED.conference,
                division = EXCLUDED.division,
                founded = EXCLUDED.founded,
                arena = EXCLUDED.arena,
                arena_capacity = EXCLUDED.arena_capacity,
                active_years = EXCLUDED.active_years,
                updated_at = CURRENT_TIMESTAMP
            """, team_id, team_data["tricode"], team_data["full_name"], team_data["city"],
            team_data["nickname"], team_data.get("conference"), team_data.get("division"),
            team_data.get("founded"), team_data.get("arena"), team_data.get("arena_capacity"),
            team_data.get("active_years", "current"))
        
        # Step 5: Add historical teams (Seattle SuperSonics, etc.)
        print("📚 Adding historical teams...")
        historical_teams = [
            (1610612757, "SEA", "Seattle SuperSonics", "Seattle", "SuperSonics", 
             "Western", "Northwest", 1967, "KeyArena", 17072, "1967-2008")
        ]
        
        for team_data in historical_teams:
            await conn.execute("""
            INSERT INTO teams (
                team_id, tricode, full_name, city, nickname,
                conference, division, founded, arena, arena_capacity, active_years
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (team_id) DO NOTHING
            """, *team_data)
        
        # Step 6: Verify the new structure
        print("✅ Verifying new teams table...")
        teams_count = await conn.fetchval("SELECT COUNT(*) FROM teams")
        print(f"   Total teams in new table: {teams_count}")
        
        # Show sample of new data
        sample_teams = await conn.fetch("""
        SELECT team_id, tricode, full_name, city, active_years 
        FROM teams 
        ORDER BY tricode 
        LIMIT 5
        """)
        
        print("   Sample teams:")
        for team in sample_teams:
            print(f"   - {team['tricode']}: {team['full_name']} (ID: {team['team_id']})")
        
        print("🎉 Teams table restructuring completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during teams table restructuring: {e}")
        # Restore from backup if needed
        try:
            await conn.execute("DROP TABLE IF EXISTS teams")
            await conn.execute("CREATE TABLE teams AS SELECT * FROM teams_backup")
            print("📄 Restored teams table from backup")
        except:
            pass
        raise e
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(restructure_teams_table())