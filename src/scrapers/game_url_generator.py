"""
NBA Game URL Generator
Generates comprehensive queue of all NBA game URLs from 1996-2025
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import json

from .team_mapping import NBA_TEAMS
from ..core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class GameURLInfo:
    """Information about a game URL for the queue."""
    game_id: str
    season: str
    game_date: date
    home_team: str
    away_team: str
    game_url: str
    game_type: str = 'regular'
    priority: int = 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database insertion."""
        data = asdict(self)
        data['game_date'] = self.game_date.isoformat()
        return data


class GameURLGenerator:
    """Generates NBA game URLs for systematic scraping."""
    
    BASE_URL = "https://www.nba.com"
    SCHEDULE_URL = "https://www.nba.com/games"
    
    # Season date ranges with special handling for shortened seasons
    SEASONS = {
        "1996-97": ("1996-11-01", "1997-06-15"),
        "1997-98": ("1997-11-01", "1998-06-15"),
        "1998-99": ("1999-02-05", "1999-06-25"),  # Lockout shortened
        "1999-00": ("1999-11-02", "2000-06-19"),
        "2000-01": ("2000-10-31", "2001-06-15"),
        "2001-02": ("2001-10-30", "2002-06-12"),
        "2002-03": ("2002-10-29", "2003-06-15"),
        "2003-04": ("2003-10-28", "2004-06-15"),
        "2004-05": ("2004-11-02", "2005-06-23"),
        "2005-06": ("2005-11-01", "2006-06-20"),
        "2006-07": ("2006-10-31", "2007-06-14"),
        "2007-08": ("2007-10-30", "2008-06-17"),
        "2008-09": ("2008-10-28", "2009-06-14"),
        "2009-10": ("2009-10-27", "2010-06-17"),
        "2010-11": ("2010-10-26", "2011-06-12"),
        "2011-12": ("2011-12-25", "2012-06-21"),  # Lockout shortened
        "2012-13": ("2012-10-30", "2013-06-20"),
        "2013-14": ("2013-10-29", "2014-06-15"),
        "2014-15": ("2014-10-28", "2015-06-16"),
        "2015-16": ("2015-10-27", "2016-06-19"),
        "2016-17": ("2016-10-25", "2017-06-12"),
        "2017-18": ("2017-10-17", "2018-06-08"),
        "2018-19": ("2018-10-16", "2019-06-13"),
        "2019-20": ("2019-10-22", "2020-10-11"),  # COVID extended
        "2020-21": ("2020-12-22", "2021-07-20"),  # COVID adjusted
        "2021-22": ("2021-10-19", "2022-06-16"),
        "2022-23": ("2022-10-18", "2023-06-12"),
        "2023-24": ("2023-10-17", "2024-06-17"),
        "2024-25": ("2024-10-22", "2025-06-15"), # TODO: Update end date once season ends
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize generator with database session."""
        self.db_session = db_session
        self.session = None
        self.discovered_games: Set[str] = set()
        
    async def initialize(self):
        """Initialize aiohttp session."""
        connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification for testing
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            
    def generate_game_url(self, away_team: str, home_team: str, game_id: str) -> str:
        """Generate NBA.com game URL from team codes and game ID."""
        return f"{self.BASE_URL}/game/{away_team.lower()}-vs-{home_team.lower()}-{game_id}"
    
    async def discover_season_games(self, season: str, batch_size: int = 10) -> List[GameURLInfo]:
        """Discover all games for a specific season."""
        if season not in self.SEASONS:
            raise ValueError(f"Unknown season: {season}")
            
        logger.info(f"Discovering games for season {season}")
        
        start_date_str, end_date_str = self.SEASONS[season]
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        all_games = []
        current_date = start_date
        
        # Process dates in batches to avoid overwhelming the server
        dates_batch = []
        
        while current_date <= end_date:
            dates_batch.append(current_date)
            
            if len(dates_batch) >= batch_size:
                # Process this batch
                batch_games = await self._process_date_batch(dates_batch, season)
                all_games.extend(batch_games)
                dates_batch = []
                
                # Rate limiting between batches
                await asyncio.sleep(2)
            
            current_date += timedelta(days=1)
        
        # Process remaining dates
        if dates_batch:
            batch_games = await self._process_date_batch(dates_batch, season)
            all_games.extend(batch_games)
        
        logger.info(f"Season {season}: discovered {len(all_games)} games")
        return all_games
    
    async def _process_date_batch(self, dates: List[date], season: str) -> List[GameURLInfo]:
        """Process a batch of dates concurrently."""
        tasks = []
        for game_date in dates:
            task = self._discover_games_for_date(game_date, season)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_games = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Error in batch processing: {result}")
                continue
            all_games.extend(result)
        
        return all_games
    
    async def _discover_games_for_date(self, game_date: date, season: str) -> List[GameURLInfo]:
        """Discover games for a specific date."""
        date_str = game_date.strftime("%Y-%m-%d")
        url = f"{self.SCHEDULE_URL}?date={date_str}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 404:
                    return []  # No games on this date
                    
                response.raise_for_status()
                html = await response.text()
                
                games = self._parse_games_from_html(html, game_date, season)
                return games
                
        except aiohttp.ClientError as e:
            logger.warning(f"Error fetching games for {date_str}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error for {date_str}: {e}")
            return []
    
    def _parse_games_from_html(self, html: str, game_date: date, season: str) -> List[GameURLInfo]:
        """Parse game information from NBA.com schedule page."""
        soup = BeautifulSoup(html, 'html.parser')
        games = []
        
        # Try multiple parsing strategies for different page structures
        
        # Strategy 1: Modern NBA.com structure
        game_links = soup.find_all('a', href=re.compile(r'/game/[a-z]{3}-vs-[a-z]{3}-\d+'))
        for link in game_links:
            game_info = self._extract_game_from_link(link, game_date, season)
            if game_info and game_info.game_id not in self.discovered_games:
                games.append(game_info)
                self.discovered_games.add(game_info.game_id)
        
        # Strategy 2: __NEXT_DATA__ JSON extraction
        if not games:
            games.extend(self._extract_from_next_data(html, game_date, season))
        
        # Strategy 3: Alternative selectors
        if not games:
            games.extend(self._extract_from_alternative_selectors(soup, game_date, season))
        
        return games
    
    def _extract_game_from_link(self, link, game_date: date, season: str) -> Optional[GameURLInfo]:
        """Extract game info from a game link element."""
        href = link.get('href', '')
        
        # Parse URL pattern: /game/away-vs-home-gameid
        match = re.search(r'/game/([a-z]{3})-vs-([a-z]{3})-(\d+)', href)
        if not match:
            return None
        
        away_team = match.group(1).upper()
        home_team = match.group(2).upper()
        game_id = match.group(3)
        
        # Validate team codes for the season
        if not (NBA_TEAMS.validate_team_code(away_team, season) and 
                NBA_TEAMS.validate_team_code(home_team, season)):
            logger.warning(f"Invalid team codes for {season}: {away_team} vs {home_team}")
            return None
        
        # Determine game type
        game_type = self._determine_game_type(game_date, season, game_id)
        
        # Calculate priority (higher for recent seasons and playoffs)
        priority = self._calculate_priority(season, game_type)
        
        game_url = f"{self.BASE_URL}{href}" if href.startswith('/') else href
        
        return GameURLInfo(
            game_id=game_id,
            season=season,
            game_date=game_date,
            home_team=home_team,
            away_team=away_team,
            game_url=game_url,
            game_type=game_type,
            priority=priority
        )
    
    def _extract_from_next_data(self, html: str, game_date: date, season: str) -> List[GameURLInfo]:
        """Extract games from __NEXT_DATA__ JSON if available."""
        games = []
        
        # Find __NEXT_DATA__ script
        script_pattern = re.compile(r'__NEXT_DATA__["\']?\s*=\s*({.*?})\s*(?:</script>|;)', re.DOTALL)
        match = script_pattern.search(html)
        
        if not match:
            return games
        
        try:
            data = json.loads(match.group(1))
            # Navigate the JSON structure to find games
            # This structure varies, so we need to be flexible
            
            # Common paths where games might be found
            possible_paths = [
                ['props', 'pageProps', 'games'],
                ['props', 'pageProps', 'schedule', 'games'],
                ['props', 'initialData', 'games'],
            ]
            
            for path in possible_paths:
                games_data = data
                try:
                    for key in path:
                        games_data = games_data[key]
                    
                    if isinstance(games_data, list):
                        for game_data in games_data:
                            game_info = self._parse_game_from_json(game_data, game_date, season)
                            if game_info:
                                games.append(game_info)
                        break
                        
                except (KeyError, TypeError):
                    continue
                    
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse __NEXT_DATA__ for {game_date}")
        
        return games
    
    def _parse_game_from_json(self, game_data: Dict, game_date: date, season: str) -> Optional[GameURLInfo]:
        """Parse game info from JSON data structure."""
        try:
            # Extract game ID
            game_id = str(game_data.get('gameId', ''))
            if not game_id:
                return None
            
            # Extract teams
            home_team = game_data.get('homeTeam', {}).get('teamTricode', '').upper()
            away_team = game_data.get('awayTeam', {}).get('teamTricode', '').upper()
            
            if not (home_team and away_team):
                return None
            
            # Validate teams
            if not (NBA_TEAMS.validate_team_code(away_team, season) and 
                    NBA_TEAMS.validate_team_code(home_team, season)):
                return None
            
            # Generate URL
            game_url = self.generate_game_url(away_team, home_team, game_id)
            
            # Determine game type
            game_type = self._determine_game_type(game_date, season, game_id)
            priority = self._calculate_priority(season, game_type)
            
            return GameURLInfo(
                game_id=game_id,
                season=season,
                game_date=game_date,
                home_team=home_team,
                away_team=away_team,
                game_url=game_url,
                game_type=game_type,
                priority=priority
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Error parsing game JSON: {e}")
            return None
    
    def _extract_from_alternative_selectors(self, soup: BeautifulSoup, game_date: date, season: str) -> List[GameURLInfo]:
        """Try alternative selectors for older page structures."""
        games = []
        
        # Alternative selectors to try
        selectors = [
            {'selector': '[data-game-id]', 'attr': 'data-game-id'},
            {'selector': '.game-card a', 'attr': 'href'},
            {'selector': '.nba-game-card a', 'attr': 'href'},
        ]
        
        for selector_info in selectors:
            elements = soup.select(selector_info['selector'])
            for element in elements:
                game_info = self._extract_from_alternative_element(
                    element, selector_info['attr'], game_date, season
                )
                if game_info and game_info.game_id not in self.discovered_games:
                    games.append(game_info)
                    self.discovered_games.add(game_info.game_id)
        
        return games
    
    def _extract_from_alternative_element(self, element, attr: str, game_date: date, season: str) -> Optional[GameURLInfo]:
        """Extract game info from alternative element structures."""
        if attr == 'data-game-id':
            game_id = element.get('data-game-id')
            if not game_id:
                return None
            
            # Try to extract teams from text content
            text = element.get_text().strip()
            teams = self._extract_teams_from_text(text)
            if not teams:
                return None
            
            away_team, home_team = teams
            game_url = self.generate_game_url(away_team, home_team, game_id)
            
        elif attr == 'href':
            href = element.get('href', '')
            game_info = self._extract_game_from_link(element, game_date, season)
            return game_info
        
        else:
            return None
        
        # Validate and create game info
        if NBA_TEAMS.validate_team_code(away_team, season) and NBA_TEAMS.validate_team_code(home_team, season):
            game_type = self._determine_game_type(game_date, season, game_id)
            priority = self._calculate_priority(season, game_type)
            
            return GameURLInfo(
                game_id=game_id,
                season=season,
                game_date=game_date,
                home_team=home_team,
                away_team=away_team,
                game_url=game_url,
                game_type=game_type,
                priority=priority
            )
        
        return None
    
    def _extract_teams_from_text(self, text: str) -> Optional[Tuple[str, str]]:
        """Extract team abbreviations from text content."""
        # Common patterns
        patterns = [
            r'([A-Z]{3})\s*@\s*([A-Z]{3})',
            r'([A-Z]{3})\s*vs\.?\s*([A-Z]{3})',
            r'([A-Z]{3})\s*-\s*([A-Z]{3})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1), match.group(2)
        
        return None
    
    def _determine_game_type(self, game_date: date, season: str, game_id: str) -> str:
        """Determine if game is regular season, playoff, etc."""
        # Basic heuristics - can be improved with more data
        
        # Playoff games typically start in April
        if game_date.month >= 4:
            # Check if it's after regular season (very rough estimate)
            if game_date.month >= 5 or (game_date.month == 4 and game_date.day > 15):
                return 'playoff'
        
        # All-Star games (mid-February)
        if game_date.month == 2 and 12 <= game_date.day <= 20:
            return 'allstar'
        
        # Preseason (October before regular season starts)
        season_start = datetime.strptime(self.SEASONS[season][0], "%Y-%m-%d").date()
        if game_date < season_start:
            return 'preseason'
        
        return 'regular'
    
    def _calculate_priority(self, season: str, game_type: str) -> int:
        """Calculate priority for game scraping (lower = higher priority)."""
        base_priority = 100
        
        # Recent seasons get higher priority
        season_year = int(season.split('-')[0])
        if season_year >= 2020:
            base_priority -= 30
        elif season_year >= 2015:
            base_priority -= 20
        elif season_year >= 2010:
            base_priority -= 10
        
        # Playoff games get higher priority
        if game_type == 'playoff':
            base_priority -= 20
        elif game_type == 'allstar':
            base_priority -= 10
        
        return max(base_priority, 1)  # Minimum priority of 1
    
    async def populate_queue(self, games: List[GameURLInfo], batch_size: int = 1000) -> Dict[str, int]:
        """Populate the database queue with discovered games."""
        if not self.db_session:
            raise ValueError("Database session required for queue population")
        
        stats = {
            'total': len(games),
            'inserted': 0,
            'duplicates': 0,
            'errors': 0
        }
        
        # Process in batches
        for i in range(0, len(games), batch_size):
            batch = games[i:i + batch_size]
            batch_stats = await self._insert_batch(batch)
            
            stats['inserted'] += batch_stats['inserted']
            stats['duplicates'] += batch_stats['duplicates']
            stats['errors'] += batch_stats['errors']
        
        return stats
    
    async def _insert_batch(self, games: List[GameURLInfo]) -> Dict[str, int]:
        """Insert a batch of games into the database."""
        stats = {'inserted': 0, 'duplicates': 0, 'errors': 0}
        
        for game in games:
            try:
                # Convert to dict for insertion
                game_data = game.to_dict()
                
                # Use INSERT ... ON CONFLICT DO NOTHING for PostgreSQL
                insert_query = text("""
                    INSERT INTO game_url_queue 
                    (game_id, season, game_date, home_team, away_team, game_url, game_type, priority)
                    VALUES (:game_id, :season, :game_date, :home_team, :away_team, :game_url, :game_type, :priority)
                    ON CONFLICT (game_id) DO NOTHING
                """)
                
                result = self.db_session.execute(insert_query, game_data)
                
                if result.rowcount > 0:
                    stats['inserted'] += 1
                else:
                    stats['duplicates'] += 1
                    
            except Exception as e:
                logger.error(f"Error inserting game {game.game_id}: {e}")
                stats['errors'] += 1
        
        # Commit the batch
        try:
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error committing batch: {e}")
            stats['errors'] += len(games)
            stats['inserted'] = 0
            stats['duplicates'] = 0
        
        return stats
    
    async def generate_all_seasons(self, seasons: Optional[List[str]] = None) -> Dict[str, Dict[str, int]]:
        """Generate URLs for all seasons and populate the queue."""
        if seasons is None:
            seasons = list(self.SEASONS.keys())
        
        all_stats = {}
        
        for season in seasons:
            logger.info(f"Processing season {season}")
            
            try:
                # Discover games for the season
                games = await self.discover_season_games(season)
                
                # Populate queue
                stats = await self.populate_queue(games)
                all_stats[season] = stats
                
                logger.info(f"Season {season}: {stats}")
                
                # Longer pause between seasons
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error processing season {season}: {e}")
                all_stats[season] = {'error': str(e)}
        
        return all_stats


async def main():
    """Example usage of the GameURLGenerator."""
    generator = GameURLGenerator()
    
    try:
        await generator.initialize()
        
        # Test with a single season first
        games = await generator.discover_season_games("2024-25")
        
        logger.info(f"Discovered {len(games)} games for 2024-25 season")
        for game in games[:5]:  # Show first 5
            logger.info(f"Game: {game}")
            
    finally:
        await generator.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())