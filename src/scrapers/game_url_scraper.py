"""Scraper for discovering NBA game URLs from schedule pages."""

import re
import time
import logging
from datetime import date
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class GameURLScraper:
    """Scrapes NBA.com schedule pages to discover game URLs."""
    
    BASE_URL = "https://www.nba.com"
    SCHEDULE_URL = "https://www.nba.com/games"
    
    def __init__(self, delay: float = 1.0):
        """Initialize scraper with request delay."""
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_games_for_date(self, game_date: date) -> List[Dict[str, str]]:
        """Get all game URLs and basic info for a specific date."""
        url = f"{self.SCHEDULE_URL}?date={game_date.strftime('%Y-%m-%d')}"
        logger.info(f"Scraping games for date: {game_date}")
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            time.sleep(self.delay)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            games = self._extract_games_from_schedule(soup, game_date)
            
            logger.info(f"Found {len(games)} games for {game_date}")
            return games
            
        except requests.RequestException as e:
            logger.error(f"Error fetching schedule for {game_date}: {e}")
            return []
    
    def _extract_games_from_schedule(self, soup: BeautifulSoup, game_date: date) -> List[Dict[str, str]]:
        """Extract game information from schedule page HTML."""
        games = []
        
        # Look for game links - NBA.com uses various selectors for game links
        game_links = soup.find_all('a', href=re.compile(r'/game/[^/]+-vs-[^/]+-\d+'))
        
        for link in game_links:
            href = link.get('href')
            if not href:
                continue
                
            # Extract game ID and team info from URL
            game_info = self._parse_game_url(href, game_date)
            if game_info:
                games.append(game_info)
        
        # Remove duplicates based on game_id
        unique_games = {game['nba_game_id']: game for game in games}
        return list(unique_games.values())
    
    def _parse_game_url(self, url: str, game_date: date) -> Optional[Dict[str, str]]:
        """Parse game URL to extract team codes and game ID."""
        # URL pattern: /game/{away_team}-vs-{home_team}-{game_id}
        pattern = r'/game/([a-z]{3})-vs-([a-z]{3})-(\d+)'
        match = re.search(pattern, url.lower())
        
        if not match:
            return None
        
        away_team, home_team, game_id = match.groups()
        
        return {
            'nba_game_id': game_id,
            'game_url': urljoin(self.BASE_URL, url),
            'away_team_tricode': away_team.upper(),
            'home_team_tricode': home_team.upper(),
            'game_date': game_date.isoformat()
        }
    
    def get_games_for_date_range(self, start_date: date, end_date: date) -> List[Dict[str, str]]:
        """Get all games for a date range."""
        all_games = []
        current_date = start_date
        
        while current_date <= end_date:
            games = self.get_games_for_date(current_date)
            all_games.extend(games)
            current_date = current_date.replace(day=current_date.day + 1)
        
        return all_games