#!/usr/bin/env python3
"""
Simple queue builder that directly runs the queue building process.
"""

import psycopg2
import asyncio
import aiohttp
import os
import logging
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_queue_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database connection
def get_db_connection():
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/nba_pbp')
    return psycopg2.connect(db_url)

# NBA team mapping (simplified)
NBA_TEAMS = {
    'ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
    'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
    'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
}

# Season configurations
SEASONS = {
    '1999-00': ('1999-11-02', '2000-04-19'),
    '2000-01': ('2000-10-31', '2001-04-18'),
    '2001-02': ('2001-10-30', '2002-04-17'),
    '2002-03': ('2002-10-29', '2003-04-16'),
    '2003-04': ('2003-10-28', '2004-04-14'),
    '2004-05': ('2004-11-02', '2005-04-20'),
    '2005-06': ('2005-11-01', '2006-04-19'),
    '2006-07': ('2006-10-31', '2007-04-18'),
    '2007-08': ('2007-10-30', '2008-04-16'),
    '2008-09': ('2008-10-28', '2009-04-15'),
    '2009-10': ('2009-10-27', '2010-04-14'),
    '2010-11': ('2010-10-26', '2011-04-13'),
    '2011-12': ('2011-12-25', '2012-04-26'),  # Lockout shortened season
    '2012-13': ('2012-10-30', '2013-04-17'),
    '2013-14': ('2013-10-29', '2014-04-16'),
    '2014-15': ('2014-10-28', '2015-04-15'),
    '2015-16': ('2015-10-27', '2016-04-13'),
    '2016-17': ('2016-10-25', '2017-04-12'),
    '2017-18': ('2017-10-17', '2018-04-11'),
    '2018-19': ('2018-10-16', '2019-04-10'),
    '2020-21': ('2020-12-22', '2021-05-16'),  # Pandemic shortened season
    '2021-22': ('2021-10-19', '2022-04-10'),
    '2022-23': ('2022-10-18', '2023-04-09'),
    '2023-24': ('2023-10-17', '2024-04-14'),
}

class SimpleQueueBuilder:
    def __init__(self):
        self.session = None
        self.discovered_games = set()
        
    async def initialize(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
    
    async def get_games_for_date(self, game_date: date, season: str) -> List[Dict]:
        """Get games for a specific date."""
        url = f"https://www.nba.com/games?date={game_date.strftime('%Y-%m-%d')}"
        games = []
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for game links
                    game_links = soup.find_all('a', href=re.compile(r'/game/[a-z]{3}-vs-[a-z]{3}-\d+'))
                    
                    for link in game_links:
                        href = link.get('href', '')
                        match = re.search(r'/game/([a-z]{3})-vs-([a-z]{3})-(\d+)', href)
                        if match:
                            away_team = match.group(1).upper()
                            home_team = match.group(2).upper()
                            game_id = match.group(3)
                            
                            # Basic team validation
                            if away_team in NBA_TEAMS and home_team in NBA_TEAMS:
                                if game_id not in self.discovered_games:
                                    game_url = f"https://www.nba.com{href}"
                                    games.append({
                                        'game_id': game_id,
                                        'season': season,
                                        'game_date': game_date,
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'game_url': game_url,
                                        'game_type': 'regular',
                                        'priority': 100
                                    })
                                    self.discovered_games.add(game_id)
                            else:
                                logger.warning(f"Invalid teams: {away_team} vs {home_team}")
                    
                    if games:
                        logger.info(f"Found {len(games)} games for {game_date}")
                        
                elif response.status == 503:
                    logger.warning(f"Service unavailable for {game_date}")
                else:
                    logger.warning(f"HTTP {response.status} for {game_date}")
                    
        except Exception as e:
            logger.error(f"Error fetching {game_date}: {e}")
            
        return games
    
    async def discover_season(self, season: str) -> List[Dict]:
        """Discover all games for a season."""
        if season not in SEASONS:
            logger.error(f"Season {season} not configured")
            return []
            
        start_date_str, end_date_str = SEASONS[season]
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        logger.info(f"Discovering games for {season} ({start_date} to {end_date})")
        
        all_games = []
        current_date = start_date
        
        while current_date <= end_date:
            games = await self.get_games_for_date(current_date, season)
            all_games.extend(games)
            
            # Small delay to be respectful
            await asyncio.sleep(0.5)
            current_date += timedelta(days=1)
            
        logger.info(f"Season {season}: Found {len(all_games)} games")
        return all_games
    
    def insert_games(self, games: List[Dict]) -> int:
        """Insert games into database."""
        if not games:
            return 0
            
        conn = get_db_connection()
        cursor = conn.cursor()
        inserted = 0
        
        try:
            for game in games:
                try:
                    cursor.execute("""
                        INSERT INTO game_url_queue 
                        (game_id, season, game_date, home_team, away_team, game_url, game_type, priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (game_id) DO NOTHING
                    """, (
                        game['game_id'],
                        game['season'],
                        game['game_date'],
                        game['home_team'],
                        game['away_team'],
                        game['game_url'],
                        game['game_type'],
                        game['priority']
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting game {game['game_id']}: {e}")
                    
            conn.commit()
            logger.info(f"Inserted {inserted} new games")
            
        finally:
            cursor.close()
            conn.close()
            
        return inserted

async def build_missing_seasons():
    """Build missing seasons."""
    # Get current seasons
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT season FROM game_url_queue")
    existing_seasons = {row[0] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    
    # Missing seasons (most important ones)
    missing_seasons = [
        '2020-21', '2021-22', '2022-23', '2023-24',  # Recent seasons
        '2015-16', '2016-17', '2017-18', '2018-19',  # Modern era
        '2010-11', '2011-12', '2012-13', '2013-14', '2014-15',  # 2010s
        '2005-06', '2006-07', '2007-08', '2008-09', '2009-10',  # 2000s
        '1999-00', '2000-01', '2001-02', '2002-03', '2003-04', '2004-05'  # Early 2000s
    ]
    
    builder = SimpleQueueBuilder()
    
    try:
        await builder.initialize()
        
        total_inserted = 0
        
        for season in missing_seasons:
            if season not in existing_seasons:
                logger.info(f"Processing missing season: {season}")
                games = await builder.discover_season(season)
                inserted = builder.insert_games(games)
                total_inserted += inserted
                
                # Brief pause between seasons
                await asyncio.sleep(2)
        
        logger.info(f"Completed! Total new games inserted: {total_inserted}")
        
    finally:
        await builder.close()

if __name__ == "__main__":
    asyncio.run(build_missing_seasons())