"""
Game Discovery Module for NBA Games (1996-97 to 2024-25)
Discovers and generates URLs for all NBA games across seasons
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GameInfo:
    game_id: str
    season: str
    game_date: datetime
    home_team: str
    away_team: str
    game_url: str
    

class GameDiscovery:
    """Discovers NBA games by scraping season schedules"""
    
    # NBA season definitions
    SEASONS = {
        "1996-97": ("1996-10-01", "1997-06-30"),
        "1997-98": ("1997-10-01", "1998-06-30"),
        "1998-99": ("1999-02-01", "1999-06-30"),  # Lockout shortened
        "1999-00": ("1999-10-01", "2000-06-30"),
        "2000-01": ("2000-10-01", "2001-06-30"),
        "2001-02": ("2001-10-01", "2002-06-30"),
        "2002-03": ("2002-10-01", "2003-06-30"),
        "2003-04": ("2003-10-01", "2004-06-30"),
        "2004-05": ("2004-10-01", "2005-06-30"),
        "2005-06": ("2005-10-01", "2006-06-30"),
        "2006-07": ("2006-10-01", "2007-06-30"),
        "2007-08": ("2007-10-01", "2008-06-30"),
        "2008-09": ("2008-10-01", "2009-06-30"),
        "2009-10": ("2009-10-01", "2010-06-30"),
        "2010-11": ("2010-10-01", "2011-06-30"),
        "2011-12": ("2011-12-01", "2012-06-30"),  # Lockout shortened
        "2012-13": ("2012-10-01", "2013-06-30"),
        "2013-14": ("2013-10-01", "2014-06-30"),
        "2014-15": ("2014-10-01", "2015-06-30"),
        "2015-16": ("2015-10-01", "2016-06-30"),
        "2016-17": ("2016-10-01", "2017-06-30"),
        "2017-18": ("2017-10-01", "2018-06-30"),
        "2018-19": ("2018-10-01", "2019-06-30"),
        "2019-20": ("2019-10-01", "2020-10-15"),  # COVID extended
        "2020-21": ("2020-12-01", "2021-07-30"),  # COVID adjusted
        "2021-22": ("2021-10-01", "2022-06-30"),
        "2022-23": ("2022-10-01", "2023-06-30"),
        "2023-24": ("2023-10-01", "2024-06-30"),
        "2024-25": ("2024-10-01", "2025-06-30"),
    }
    
    def __init__(self):
        self.session = None
        self.base_url = "https://www.nba.com"
        
    async def initialize(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            
    async def discover_season_games(self, season: str) -> List[GameInfo]:
        """Discover all games for a specific season"""
        if season not in self.SEASONS:
            raise ValueError(f"Unknown season: {season}")
            
        start_date_str, end_date_str = self.SEASONS[season]
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        all_games = []
        current_date = start_date
        
        # Process dates in batches
        while current_date <= end_date:
            # Scrape games for this date
            games = await self._discover_games_for_date(current_date, season)
            all_games.extend(games)
            
            # Move to next date
            current_date += timedelta(days=1)
            
            # Rate limiting
            await asyncio.sleep(0.5)
            
        logger.info(f"Discovered {len(all_games)} games for season {season}")
        return all_games
        
    async def _discover_games_for_date(self, date: datetime, season: str) -> List[GameInfo]:
        """Discover games for a specific date"""
        date_str = date.strftime("%Y-%m-%d")
        url = f"{self.base_url}/games?date={date_str}"
        
        try:
            async with self.session.get(url, timeout=30) as response:
                if response.status == 404:
                    return []  # No games on this date
                    
                response.raise_for_status()
                html = await response.text()
                
                # Parse games from the page
                games = self._parse_games_from_html(html, date, season)
                return games
                
        except aiohttp.ClientError as e:
            logger.warning(f"Error fetching games for {date_str}: {e}")
            return []
            
    def _parse_games_from_html(self, html: str, date: datetime, season: str) -> List[GameInfo]:
        """Parse game information from NBA.com games page"""
        soup = BeautifulSoup(html, 'html.parser')
        games = []
        
        # Look for game cards/links (structure may vary by season)
        # Modern structure
        game_links = soup.find_all('a', href=re.compile(r'/game/[a-z]{3}-vs-[a-z]{3}-\d+'))
        
        # Fallback: older structure
        if not game_links:
            game_links = soup.find_all('a', {'data-game-id': True})
            
        for link in game_links:
            game_info = self._extract_game_info(link, date, season)
            if game_info:
                games.append(game_info)
                
        return games
        
    def _extract_game_info(self, link_element, date: datetime, season: str) -> Optional[GameInfo]:
        """Extract game information from a link element"""
        href = link_element.get('href', '')
        
        # Pattern: /game/away-vs-home-gameid
        match = re.search(r'/game/([a-z]{3})-vs-([a-z]{3})-(\d+)', href)
        if match:
            away_team = match.group(1).upper()
            home_team = match.group(2).upper()
            game_id = match.group(3)
            
            # Construct full URL
            game_url = f"{self.base_url}{href}" if href.startswith('/') else href
            
            return GameInfo(
                game_id=game_id,
                season=season,
                game_date=date,
                home_team=home_team,
                away_team=away_team,
                game_url=game_url
            )
            
        # Try alternative patterns for older seasons
        game_id = link_element.get('data-game-id')
        if game_id:
            # Extract teams from text or other attributes
            teams = self._extract_teams_from_element(link_element)
            if teams:
                away_team, home_team = teams
                game_url = f"{self.base_url}/game/{away_team.lower()}-vs-{home_team.lower()}-{game_id}"
                
                return GameInfo(
                    game_id=game_id,
                    season=season,
                    game_date=date,
                    home_team=home_team,
                    away_team=away_team,
                    game_url=game_url
                )
                
        return None
        
    def _extract_teams_from_element(self, element) -> Optional[Tuple[str, str]]:
        """Extract team abbreviations from element text or attributes"""
        text = element.get_text()
        
        # Common patterns: "LAL @ BOS", "Lakers vs Celtics", etc
        patterns = [
            r'([A-Z]{3})\s*@\s*([A-Z]{3})',
            r'([A-Z]{3})\s*vs\.?\s*([A-Z]{3})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1), match.group(2)
                
        return None
        
    async def discover_all_seasons(self, seasons: Optional[List[str]] = None) -> Dict[str, List[GameInfo]]:
        """Discover games for multiple seasons"""
        if seasons is None:
            seasons = list(self.SEASONS.keys())
            
        all_games = {}
        
        for season in seasons:
            logger.info(f"Discovering games for season {season}")
            games = await self.discover_season_games(season)
            all_games[season] = games
            
            # Longer delay between seasons
            await asyncio.sleep(2)
            
        return all_games
        
    def estimate_game_counts(self) -> Dict[str, int]:
        """Estimate game counts per season (for progress tracking)"""
        estimates = {
            "1996-97": 1189,
            "1997-98": 1189,
            "1998-99": 725,   # Lockout
            "1999-00": 1189,
            "2000-01": 1189,
            "2001-02": 1189,
            "2002-03": 1189,
            "2003-04": 1189,
            "2004-05": 1230,
            "2005-06": 1230,
            "2006-07": 1230,
            "2007-08": 1230,
            "2008-09": 1230,
            "2009-10": 1230,
            "2010-11": 1230,
            "2011-12": 990,   # Lockout
            "2012-13": 1230,
            "2013-14": 1230,
            "2014-15": 1230,
            "2015-16": 1230,
            "2016-17": 1230,
            "2017-18": 1230,
            "2018-19": 1230,
            "2019-20": 1059,  # COVID
            "2020-21": 1080,  # COVID
            "2021-22": 1230,
            "2022-23": 1230,
            "2023-24": 1230,
            "2024-25": 1230,  # Estimate
        }
        
        return estimates