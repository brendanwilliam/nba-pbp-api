#!/usr/bin/env python3
"""
Script to create a comprehensive historical teams table that tracks all NBA team 
relocations, name changes, and active periods. This will properly handle cases like
Seattle SuperSonics → Oklahoma City Thunder.
"""

import asyncio
import asyncpg
import os
from datetime import datetime

# Comprehensive NBA Teams History with relocations and name changes
NBA_TEAMS_HISTORICAL = [
    # Atlanta Hawks lineage
    {
        "team_id": 1610612737, "tricode": "MLH", "full_name": "Milwaukee Hawks", 
        "city": "Milwaukee", "nickname": "Hawks", "conference": "Eastern", "division": "Central",
        "first_season": "1951-52", "last_season": "1954-55", "is_active": False,
        "relocated_to": "St. Louis Hawks"
    },
    {
        "team_id": 1610612737, "tricode": "STL", "full_name": "St. Louis Hawks", 
        "city": "St. Louis", "nickname": "Hawks", "conference": "Western", "division": "Western",
        "first_season": "1955-56", "last_season": "1967-68", "is_active": False,
        "relocated_to": "Atlanta Hawks"
    },
    {
        "team_id": 1610612737, "tricode": "ATL", "full_name": "Atlanta Hawks", 
        "city": "Atlanta", "nickname": "Hawks", "conference": "Eastern", "division": "Southeast",
        "first_season": "1968-69", "last_season": None, "is_active": True,
        "arena": "State Farm Arena", "arena_capacity": 16600, "founded": 1946
    },
    
    # Boston Celtics (no relocations)
    {
        "team_id": 1610612738, "tricode": "BOS", "full_name": "Boston Celtics", 
        "city": "Boston", "nickname": "Celtics", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1946-47", "last_season": None, "is_active": True,
        "arena": "TD Garden", "arena_capacity": 19156, "founded": 1946
    },
    
    # Brooklyn/New Jersey Nets lineage
    {
        "team_id": 1610612751, "tricode": "NYN", "full_name": "New York Nets", 
        "city": "New York", "nickname": "Nets", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1976-77", "last_season": "1976-77", "is_active": False,
        "relocated_to": "New Jersey Nets"
    },
    {
        "team_id": 1610612751, "tricode": "NJN", "full_name": "New Jersey Nets", 
        "city": "East Rutherford", "nickname": "Nets", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1977-78", "last_season": "2011-12", "is_active": False,
        "relocated_to": "Brooklyn Nets"
    },
    {
        "team_id": 1610612751, "tricode": "BKN", "full_name": "Brooklyn Nets", 
        "city": "Brooklyn", "nickname": "Nets", "conference": "Eastern", "division": "Atlantic",
        "first_season": "2012-13", "last_season": None, "is_active": True,
        "arena": "Barclays Center", "arena_capacity": 17732, "founded": 1967
    },
    
    # Charlotte Hornets/Bobcats/New Orleans lineage
    {
        "team_id": 1610612766, "tricode": "CHA", "full_name": "Charlotte Hornets", 
        "city": "Charlotte", "nickname": "Hornets", "conference": "Eastern", "division": "Southeast",
        "first_season": "1988-89", "last_season": "2001-02", "is_active": False,
        "relocated_to": "New Orleans Hornets"
    },
    {
        "team_id": 1610612740, "tricode": "NOH", "full_name": "New Orleans Hornets", 
        "city": "New Orleans", "nickname": "Hornets", "conference": "Western", "division": "Southwest",
        "first_season": "2002-03", "last_season": "2012-13", "is_active": False,
        "name_changed_to": "New Orleans Pelicans"
    },
    {
        "team_id": 1610612740, "tricode": "NOP", "full_name": "New Orleans Pelicans", 
        "city": "New Orleans", "nickname": "Pelicans", "conference": "Western", "division": "Southwest",
        "first_season": "2013-14", "last_season": None, "is_active": True,
        "arena": "Smoothie King Center", "arena_capacity": 16867, "founded": 1988
    },
    {
        "team_id": 1610612766, "tricode": "CHA", "full_name": "Charlotte Bobcats", 
        "city": "Charlotte", "nickname": "Bobcats", "conference": "Eastern", "division": "Southeast",
        "first_season": "2004-05", "last_season": "2013-14", "is_active": False,
        "name_changed_to": "Charlotte Hornets"
    },
    {
        "team_id": 1610612766, "tricode": "CHA", "full_name": "Charlotte Hornets", 
        "city": "Charlotte", "nickname": "Hornets", "conference": "Eastern", "division": "Southeast",
        "first_season": "2014-15", "last_season": None, "is_active": True,
        "arena": "Spectrum Center", "arena_capacity": 19077, "founded": 1988
    },
    
    # Chicago Bulls (no relocations)
    {
        "team_id": 1610612741, "tricode": "CHI", "full_name": "Chicago Bulls", 
        "city": "Chicago", "nickname": "Bulls", "conference": "Eastern", "division": "Central",
        "first_season": "1966-67", "last_season": None, "is_active": True,
        "arena": "United Center", "arena_capacity": 20917, "founded": 1966
    },
    
    # Cleveland Cavaliers (no relocations)
    {
        "team_id": 1610612739, "tricode": "CLE", "full_name": "Cleveland Cavaliers", 
        "city": "Cleveland", "nickname": "Cavaliers", "conference": "Eastern", "division": "Central",
        "first_season": "1970-71", "last_season": None, "is_active": True,
        "arena": "Rocket Mortgage FieldHouse", "arena_capacity": 19432, "founded": 1970
    },
    
    # Dallas Mavericks (no relocations)
    {
        "team_id": 1610612742, "tricode": "DAL", "full_name": "Dallas Mavericks", 
        "city": "Dallas", "nickname": "Mavericks", "conference": "Western", "division": "Southwest",
        "first_season": "1980-81", "last_season": None, "is_active": True,
        "arena": "American Airlines Center", "arena_capacity": 19200, "founded": 1980
    },
    
    # Denver Nuggets (no relocations in NBA)
    {
        "team_id": 1610612743, "tricode": "DEN", "full_name": "Denver Nuggets", 
        "city": "Denver", "nickname": "Nuggets", "conference": "Western", "division": "Northwest",
        "first_season": "1976-77", "last_season": None, "is_active": True,
        "arena": "Ball Arena", "arena_capacity": 19520, "founded": 1967
    },
    
    # Detroit Pistons lineage
    {
        "team_id": 1610612765, "tricode": "FTW", "full_name": "Fort Wayne Pistons", 
        "city": "Fort Wayne", "nickname": "Pistons", "conference": "Western", "division": "Central",
        "first_season": "1949-50", "last_season": "1956-57", "is_active": False,
        "relocated_to": "Detroit Pistons"
    },
    {
        "team_id": 1610612765, "tricode": "DET", "full_name": "Detroit Pistons", 
        "city": "Detroit", "nickname": "Pistons", "conference": "Eastern", "division": "Central",
        "first_season": "1957-58", "last_season": None, "is_active": True,
        "arena": "Little Caesars Arena", "arena_capacity": 20332, "founded": 1941
    },
    
    # Golden State Warriors lineage
    {
        "team_id": 1610612744, "tricode": "PHW", "full_name": "Philadelphia Warriors", 
        "city": "Philadelphia", "nickname": "Warriors", "conference": "Eastern", "division": "Eastern",
        "first_season": "1946-47", "last_season": "1961-62", "is_active": False,
        "relocated_to": "San Francisco Warriors"
    },
    {
        "team_id": 1610612744, "tricode": "SFW", "full_name": "San Francisco Warriors", 
        "city": "San Francisco", "nickname": "Warriors", "conference": "Western", "division": "Western",
        "first_season": "1962-63", "last_season": "1970-71", "is_active": False,
        "name_changed_to": "Golden State Warriors"
    },
    {
        "team_id": 1610612744, "tricode": "GSW", "full_name": "Golden State Warriors", 
        "city": "San Francisco", "nickname": "Warriors", "conference": "Western", "division": "Pacific",
        "first_season": "1971-72", "last_season": None, "is_active": True,
        "arena": "Chase Center", "arena_capacity": 18064, "founded": 1946
    },
    
    # Houston Rockets lineage
    {
        "team_id": 1610612745, "tricode": "SDR", "full_name": "San Diego Rockets", 
        "city": "San Diego", "nickname": "Rockets", "conference": "Western", "division": "Western",
        "first_season": "1967-68", "last_season": "1970-71", "is_active": False,
        "relocated_to": "Houston Rockets"
    },
    {
        "team_id": 1610612745, "tricode": "HOU", "full_name": "Houston Rockets", 
        "city": "Houston", "nickname": "Rockets", "conference": "Western", "division": "Southwest",
        "first_season": "1971-72", "last_season": None, "is_active": True,
        "arena": "Toyota Center", "arena_capacity": 18055, "founded": 1967
    },
    
    # Indiana Pacers (no relocations in NBA)
    {
        "team_id": 1610612754, "tricode": "IND", "full_name": "Indiana Pacers", 
        "city": "Indianapolis", "nickname": "Pacers", "conference": "Eastern", "division": "Central",
        "first_season": "1976-77", "last_season": None, "is_active": True,
        "arena": "Gainbridge Fieldhouse", "arena_capacity": 17274, "founded": 1967
    },
    
    # Los Angeles Clippers lineage
    {
        "team_id": 1610612746, "tricode": "BUF", "full_name": "Buffalo Braves", 
        "city": "Buffalo", "nickname": "Braves", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1970-71", "last_season": "1977-78", "is_active": False,
        "relocated_to": "San Diego Clippers"
    },
    {
        "team_id": 1610612746, "tricode": "SDC", "full_name": "San Diego Clippers", 
        "city": "San Diego", "nickname": "Clippers", "conference": "Western", "division": "Pacific",
        "first_season": "1978-79", "last_season": "1983-84", "is_active": False,
        "relocated_to": "Los Angeles Clippers"
    },
    {
        "team_id": 1610612746, "tricode": "LAC", "full_name": "Los Angeles Clippers", 
        "city": "Los Angeles", "nickname": "Clippers", "conference": "Western", "division": "Pacific",
        "first_season": "1984-85", "last_season": None, "is_active": True,
        "arena": "Crypto.com Arena", "arena_capacity": 20000, "founded": 1970
    },
    
    # Los Angeles Lakers lineage
    {
        "team_id": 1610612747, "tricode": "MNL", "full_name": "Minneapolis Lakers", 
        "city": "Minneapolis", "nickname": "Lakers", "conference": "Western", "division": "Central",
        "first_season": "1949-50", "last_season": "1959-60", "is_active": False,
        "relocated_to": "Los Angeles Lakers"
    },
    {
        "team_id": 1610612747, "tricode": "LAL", "full_name": "Los Angeles Lakers", 
        "city": "Los Angeles", "nickname": "Lakers", "conference": "Western", "division": "Pacific",
        "first_season": "1960-61", "last_season": None, "is_active": True,
        "arena": "Crypto.com Arena", "arena_capacity": 20000, "founded": 1947
    },
    
    # Memphis Grizzlies lineage
    {
        "team_id": 1610612763, "tricode": "VAN", "full_name": "Vancouver Grizzlies", 
        "city": "Vancouver", "nickname": "Grizzlies", "conference": "Western", "division": "Midwest",
        "first_season": "1995-96", "last_season": "2000-01", "is_active": False,
        "relocated_to": "Memphis Grizzlies"
    },
    {
        "team_id": 1610612763, "tricode": "MEM", "full_name": "Memphis Grizzlies", 
        "city": "Memphis", "nickname": "Grizzlies", "conference": "Western", "division": "Southwest",
        "first_season": "2001-02", "last_season": None, "is_active": True,
        "arena": "FedExForum", "arena_capacity": 17794, "founded": 1995
    },
    
    # Miami Heat (no relocations)
    {
        "team_id": 1610612748, "tricode": "MIA", "full_name": "Miami Heat", 
        "city": "Miami", "nickname": "Heat", "conference": "Eastern", "division": "Southeast",
        "first_season": "1988-89", "last_season": None, "is_active": True,
        "arena": "Kaseya Center", "arena_capacity": 19600, "founded": 1988
    },
    
    # Milwaukee Bucks (no relocations)
    {
        "team_id": 1610612749, "tricode": "MIL", "full_name": "Milwaukee Bucks", 
        "city": "Milwaukee", "nickname": "Bucks", "conference": "Eastern", "division": "Central",
        "first_season": "1968-69", "last_season": None, "is_active": True,
        "arena": "Fiserv Forum", "arena_capacity": 17500, "founded": 1968
    },
    
    # Minnesota Timberwolves (no relocations)
    {
        "team_id": 1610612750, "tricode": "MIN", "full_name": "Minnesota Timberwolves", 
        "city": "Minneapolis", "nickname": "Timberwolves", "conference": "Western", "division": "Northwest",
        "first_season": "1989-90", "last_season": None, "is_active": True,
        "arena": "Target Center", "arena_capacity": 19356, "founded": 1989
    },
    
    # New York Knicks (no relocations)
    {
        "team_id": 1610612752, "tricode": "NYK", "full_name": "New York Knicks", 
        "city": "New York", "nickname": "Knicks", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1946-47", "last_season": None, "is_active": True,
        "arena": "Madison Square Garden", "arena_capacity": 20789, "founded": 1946
    },
    
    # Oklahoma City Thunder / Seattle SuperSonics lineage ⭐ THE IMPORTANT ONE ⭐
    {
        "team_id": 1610612760, "tricode": "SEA", "full_name": "Seattle SuperSonics", 
        "city": "Seattle", "nickname": "SuperSonics", "conference": "Western", "division": "Pacific",
        "first_season": "1967-68", "last_season": "2007-08", "is_active": False,
        "relocated_to": "Oklahoma City Thunder",
        "arena": "KeyArena", "arena_capacity": 17072, "founded": 1967
    },
    {
        "team_id": 1610612760, "tricode": "OKC", "full_name": "Oklahoma City Thunder", 
        "city": "Oklahoma City", "nickname": "Thunder", "conference": "Western", "division": "Northwest",
        "first_season": "2008-09", "last_season": None, "is_active": True,
        "arena": "Paycom Center", "arena_capacity": 18203, "founded": 1967
    },
    
    # Orlando Magic (no relocations)
    {
        "team_id": 1610612753, "tricode": "ORL", "full_name": "Orlando Magic", 
        "city": "Orlando", "nickname": "Magic", "conference": "Eastern", "division": "Southeast",
        "first_season": "1989-90", "last_season": None, "is_active": True,
        "arena": "Kia Center", "arena_capacity": 18846, "founded": 1989
    },
    
    # Philadelphia 76ers lineage
    {
        "team_id": 1610612755, "tricode": "SYR", "full_name": "Syracuse Nationals", 
        "city": "Syracuse", "nickname": "Nationals", "conference": "Eastern", "division": "Eastern",
        "first_season": "1949-50", "last_season": "1962-63", "is_active": False,
        "relocated_to": "Philadelphia 76ers"
    },
    {
        "team_id": 1610612755, "tricode": "PHI", "full_name": "Philadelphia 76ers", 
        "city": "Philadelphia", "nickname": "76ers", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1963-64", "last_season": None, "is_active": True,
        "arena": "Wells Fargo Center", "arena_capacity": 20478, "founded": 1946
    },
    
    # Phoenix Suns (no relocations)
    {
        "team_id": 1610612756, "tricode": "PHX", "full_name": "Phoenix Suns", 
        "city": "Phoenix", "nickname": "Suns", "conference": "Western", "division": "Pacific",
        "first_season": "1968-69", "last_season": None, "is_active": True,
        "arena": "Footprint Center", "arena_capacity": 17071, "founded": 1968
    },
    
    # Portland Trail Blazers (no relocations)
    {
        "team_id": 1610612757, "tricode": "POR", "full_name": "Portland Trail Blazers", 
        "city": "Portland", "nickname": "Trail Blazers", "conference": "Western", "division": "Northwest",
        "first_season": "1970-71", "last_season": None, "is_active": True,
        "arena": "Moda Center", "arena_capacity": 19393, "founded": 1970
    },
    
    # Sacramento Kings lineage
    {
        "team_id": 1610612758, "tricode": "ROC", "full_name": "Rochester Royals", 
        "city": "Rochester", "nickname": "Royals", "conference": "Western", "division": "Central",
        "first_season": "1949-50", "last_season": "1956-57", "is_active": False,
        "relocated_to": "Cincinnati Royals"
    },
    {
        "team_id": 1610612758, "tricode": "CIN", "full_name": "Cincinnati Royals", 
        "city": "Cincinnati", "nickname": "Royals", "conference": "Eastern", "division": "Eastern",
        "first_season": "1957-58", "last_season": "1971-72", "is_active": False,
        "relocated_to": "Kansas City-Omaha Kings"
    },
    {
        "team_id": 1610612758, "tricode": "KCO", "full_name": "Kansas City-Omaha Kings", 
        "city": "Kansas City", "nickname": "Kings", "conference": "Western", "division": "Midwest",
        "first_season": "1972-73", "last_season": "1974-75", "is_active": False,
        "name_changed_to": "Kansas City Kings"
    },
    {
        "team_id": 1610612758, "tricode": "KCK", "full_name": "Kansas City Kings", 
        "city": "Kansas City", "nickname": "Kings", "conference": "Western", "division": "Midwest",
        "first_season": "1975-76", "last_season": "1984-85", "is_active": False,
        "relocated_to": "Sacramento Kings"
    },
    {
        "team_id": 1610612758, "tricode": "SAC", "full_name": "Sacramento Kings", 
        "city": "Sacramento", "nickname": "Kings", "conference": "Western", "division": "Pacific",
        "first_season": "1985-86", "last_season": None, "is_active": True,
        "arena": "Golden 1 Center", "arena_capacity": 17608, "founded": 1945
    },
    
    # San Antonio Spurs (no relocations in NBA)
    {
        "team_id": 1610612759, "tricode": "SAS", "full_name": "San Antonio Spurs", 
        "city": "San Antonio", "nickname": "Spurs", "conference": "Western", "division": "Southwest",
        "first_season": "1976-77", "last_season": None, "is_active": True,
        "arena": "Frost Bank Center", "arena_capacity": 18418, "founded": 1967
    },
    
    # Toronto Raptors (no relocations)
    {
        "team_id": 1610612761, "tricode": "TOR", "full_name": "Toronto Raptors", 
        "city": "Toronto", "nickname": "Raptors", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1995-96", "last_season": None, "is_active": True,
        "arena": "Scotiabank Arena", "arena_capacity": 19800, "founded": 1995
    },
    
    # Utah Jazz lineage
    {
        "team_id": 1610612762, "tricode": "NOJ", "full_name": "New Orleans Jazz", 
        "city": "New Orleans", "nickname": "Jazz", "conference": "Eastern", "division": "Central",
        "first_season": "1974-75", "last_season": "1978-79", "is_active": False,
        "relocated_to": "Utah Jazz"
    },
    {
        "team_id": 1610612762, "tricode": "UTA", "full_name": "Utah Jazz", 
        "city": "Salt Lake City", "nickname": "Jazz", "conference": "Western", "division": "Northwest",
        "first_season": "1979-80", "last_season": None, "is_active": True,
        "arena": "Delta Center", "arena_capacity": 18306, "founded": 1974
    },
    
    # Washington Wizards lineage
    {
        "team_id": 1610612764, "tricode": "CHZ", "full_name": "Chicago Zephyrs", 
        "city": "Chicago", "nickname": "Zephyrs", "conference": "Western", "division": "Western",
        "first_season": "1962-63", "last_season": "1962-63", "is_active": False,
        "relocated_to": "Baltimore Bullets"
    },
    {
        "team_id": 1610612764, "tricode": "BAL", "full_name": "Baltimore Bullets", 
        "city": "Baltimore", "nickname": "Bullets", "conference": "Eastern", "division": "Eastern",
        "first_season": "1963-64", "last_season": "1972-73", "is_active": False,
        "relocated_to": "Capital Bullets"
    },
    {
        "team_id": 1610612764, "tricode": "CAP", "full_name": "Capital Bullets", 
        "city": "Landover", "nickname": "Bullets", "conference": "Eastern", "division": "Central",
        "first_season": "1973-74", "last_season": "1973-74", "is_active": False,
        "name_changed_to": "Washington Bullets"
    },
    {
        "team_id": 1610612764, "tricode": "WSB", "full_name": "Washington Bullets", 
        "city": "Washington", "nickname": "Bullets", "conference": "Eastern", "division": "Atlantic",
        "first_season": "1974-75", "last_season": "1996-97", "is_active": False,
        "name_changed_to": "Washington Wizards"
    },
    {
        "team_id": 1610612764, "tricode": "WAS", "full_name": "Washington Wizards", 
        "city": "Washington", "nickname": "Wizards", "conference": "Eastern", "division": "Southeast",
        "first_season": "1997-98", "last_season": None, "is_active": True,
        "arena": "Capital One Arena", "arena_capacity": 20356, "founded": 1961
    }
]

async def create_historical_teams_table():
    """Create comprehensive historical teams table with all relocations and name changes"""
    
    DATABASE_URL = 'postgresql://brendan@localhost:5432/nba_pbp'  # Force local database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🏀 Creating comprehensive historical teams table...")
        
        # Step 1: Create backup of current teams table
        print("📄 Creating backup of current teams table...")
        await conn.execute("CREATE TABLE IF NOT EXISTS teams_backup_historical AS SELECT * FROM teams")
        
        # Step 2: Drop current teams table
        print("🗑️  Dropping current teams table...")
        await conn.execute("DROP TABLE IF EXISTS teams CASCADE")
        
        # Step 3: Create new historical teams table structure
        print("🏗️  Creating historical teams table structure...")
        await conn.execute("""
        CREATE TABLE teams (
            id SERIAL PRIMARY KEY,  -- Unique identifier for each team instance
            team_id INTEGER NOT NULL,  -- NBA team ID (can have multiple entries for relocations)
            tricode VARCHAR(3) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            city VARCHAR(50) NOT NULL,
            nickname VARCHAR(50) NOT NULL,
            conference VARCHAR(10),
            division VARCHAR(15),
            first_season VARCHAR(7) NOT NULL,  -- e.g., "1967-68"
            last_season VARCHAR(7),  -- NULL if still active
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            founded INTEGER,
            arena VARCHAR(100),
            arena_capacity INTEGER,
            relocated_to VARCHAR(100),  -- Name of team they became
            name_changed_to VARCHAR(100),  -- For name changes without relocation
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            
            -- Indexes for efficient querying
            CONSTRAINT unique_team_period UNIQUE (team_id, first_season, last_season)
        )
        """)
        
        # Create indexes for efficient historical lookups
        await conn.execute("CREATE INDEX idx_teams_team_id ON teams(team_id)")
        await conn.execute("CREATE INDEX idx_teams_active ON teams(is_active)")
        await conn.execute("CREATE INDEX idx_teams_tricode ON teams(tricode)")
        await conn.execute("CREATE INDEX idx_teams_seasons ON teams(first_season, last_season)")
        
        # Step 4: Insert all historical team data
        print("📝 Inserting historical teams data...")
        for team_data in NBA_TEAMS_HISTORICAL:
            await conn.execute("""
            INSERT INTO teams (
                team_id, tricode, full_name, city, nickname,
                conference, division, first_season, last_season, is_active,
                founded, arena, arena_capacity, relocated_to, name_changed_to
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """, 
            team_data["team_id"], team_data["tricode"], team_data["full_name"], 
            team_data["city"], team_data["nickname"], team_data.get("conference"), 
            team_data.get("division"), team_data["first_season"], team_data.get("last_season"),
            team_data["is_active"], team_data.get("founded"), team_data.get("arena"), 
            team_data.get("arena_capacity"), team_data.get("relocated_to"), 
            team_data.get("name_changed_to"))
        
        # Step 5: Verify the historical data
        print("✅ Verifying historical teams data...")
        
        # Check Seattle SuperSonics specifically
        seattle_data = await conn.fetch("""
        SELECT id, team_id, tricode, full_name, first_season, last_season, is_active, relocated_to
        FROM teams 
        WHERE team_id = 1610612760
        ORDER BY first_season
        """)
        
        print("   🎯 Seattle SuperSonics / OKC Thunder lineage:")
        for team in seattle_data:
            active_status = "✅ Active" if team['is_active'] else "❌ Inactive"
            relocated = f" → {team['relocated_to']}" if team['relocated_to'] else ""
            print(f"   - {team['tricode']}: {team['full_name']} ({team['first_season']} to {team['last_season'] or 'present'}) {active_status}{relocated}")
        
        # Count total historical entries
        total_entries = await conn.fetchval("SELECT COUNT(*) FROM teams")
        active_teams = await conn.fetchval("SELECT COUNT(*) FROM teams WHERE is_active = true")
        
        print(f"   📊 Total historical entries: {total_entries}")
        print(f"   📊 Currently active teams: {active_teams}")
        
        # Show a few more examples
        print(f"\\n   🔍 Other notable relocations:")
        notable_relocations = await conn.fetch("""
        SELECT tricode, full_name, first_season, last_season, relocated_to
        FROM teams 
        WHERE relocated_to IS NOT NULL
        AND tricode IN ('SEA', 'VAN', 'NOJ', 'SDR')
        ORDER BY first_season
        """)
        
        for team in notable_relocations:
            print(f"   - {team['tricode']}: {team['full_name']} ({team['first_season']}-{team['last_season']}) → {team['relocated_to']}")
        
        print("🎉 Historical teams table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating historical teams table: {e}")
        # Restore from backup if needed
        try:
            await conn.execute("DROP TABLE IF EXISTS teams")
            await conn.execute("CREATE TABLE teams AS SELECT * FROM teams_backup_historical")
            print("📄 Restored teams table from backup")
        except:
            pass
        raise e
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_historical_teams_table())