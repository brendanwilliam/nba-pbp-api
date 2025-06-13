"""Scraper for extracting play-by-play data from NBA game pages."""

import json
import time
import logging
from typing import Dict, Optional, Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class GameDataScraper:
    """Scrapes NBA.com game pages to extract play-by-play data."""
    
    def __init__(self, delay: float = 2.0):
        """Initialize scraper with request delay."""
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def scrape_game_data(self, game_url: str) -> Optional[Dict[str, Any]]:
        """Scrape play-by-play data from a game URL."""
        logger.info(f"Scraping game data from: {game_url}")
        
        try:
            response = self.session.get(game_url)
            response.raise_for_status()
            time.sleep(self.delay)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            game_data = self._extract_next_data(soup)
            
            if game_data:
                logger.info(f"Successfully scraped game data from: {game_url}")
                return game_data
            else:
                logger.warning(f"No game data found in: {game_url}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching game data from {game_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping {game_url}: {e}")
            return None
    
    def _extract_next_data(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract JSON data from __NEXT_DATA__ script tag."""
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        
        if not script_tag:
            logger.warning("No __NEXT_DATA__ script tag found")
            return None
        
        try:
            json_data = json.loads(script_tag.string)
            return json_data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing __NEXT_DATA__ JSON: {e}")
            return None
    
    def validate_game_data(self, game_data: Dict[str, Any]) -> bool:
        """Validate that the scraped data contains expected game information."""
        if not isinstance(game_data, dict):
            return False
        
        # Check for expected structure in NBA.com game data
        required_paths = [
            ['props', 'pageProps'],
            ['props', 'pageProps', 'game']
        ]
        
        for path in required_paths:
            current = game_data
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    logger.warning(f"Missing expected key path: {' -> '.join(path)}")
                    return False
                current = current[key]
        
        return True
    
    def extract_game_metadata(self, game_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract basic game metadata from scraped data."""
        if not self.validate_game_data(game_data):
            return None
        
        try:
            game_props = game_data['props']['pageProps']['game']
            
            metadata = {
                'gameId': game_props.get('gameId'),
                'gameTimeUTC': game_props.get('gameTimeUTC'),
                'gameStatus': game_props.get('gameStatus'),
                'gameStatusText': game_props.get('gameStatusText'),
                'homeTeam': game_props.get('homeTeam', {}),
                'awayTeam': game_props.get('awayTeam', {}),
                'period': game_props.get('period'),
                'gameClock': game_props.get('gameClock')
            }
            
            return metadata
            
        except (KeyError, TypeError) as e:
            logger.error(f"Error extracting game metadata: {e}")
            return None
    
    def extract_play_by_play(self, game_data: Dict[str, Any]) -> Optional[list]:
        """Extract play-by-play data from scraped data."""
        if not self.validate_game_data(game_data):
            return None
        
        try:
            # NBA.com structure may vary, but typically play-by-play is nested
            page_props = game_data['props']['pageProps']
            
            # Look for play-by-play data in various possible locations
            possible_pbp_keys = ['playByPlay', 'plays', 'gameActions']
            
            for key in possible_pbp_keys:
                if key in page_props:
                    pbp_data = page_props[key]
                    if isinstance(pbp_data, list) and len(pbp_data) > 0:
                        logger.info(f"Found play-by-play data under key: {key}")
                        return pbp_data
            
            logger.warning("No play-by-play data found in expected locations")
            return None
            
        except (KeyError, TypeError) as e:
            logger.error(f"Error extracting play-by-play data: {e}")
            return None