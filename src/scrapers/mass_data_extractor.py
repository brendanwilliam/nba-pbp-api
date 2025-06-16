"""
Enhanced NBA Data Extractor for Mass Scraping Operations
Implements robust JSON extraction with validation and quality scoring
"""

import json
import time
import logging
from typing import Dict, Optional, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ExtractionResult(str, Enum):
    SUCCESS = "success"
    NO_DATA = "no_data"
    INVALID_JSON = "invalid_json"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"


@dataclass
class DataQuality:
    """Data quality assessment"""
    completeness_score: float  # 0.0 to 1.0
    has_play_by_play: bool
    has_box_score: bool
    has_game_metadata: bool
    total_plays: int
    missing_fields: List[str]
    

@dataclass
class ExtractionMetadata:
    """Metadata about the extraction process"""
    extraction_time_ms: int
    response_size_bytes: int
    json_size_bytes: int
    data_quality: DataQuality
    user_agent_used: str
    

class NBADataExtractor:
    """Enhanced NBA.com data extractor with comprehensive validation"""
    
    # User agents to rotate through
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
    ]
    
    def __init__(self, timeout: int = 30, user_agent_index: int = 0):
        """Initialize extractor with configuration"""
        self.timeout = timeout
        self.current_user_agent_index = user_agent_index % len(self.USER_AGENTS)
        
        # Create session with configuration
        self.session = requests.Session()
        self._update_session_headers()
        
        # Request configuration
        self.session.timeout = timeout
        
    def _update_session_headers(self):
        """Update session headers with current user agent"""
        self.session.headers.update({
            'User-Agent': self.USER_AGENTS[self.current_user_agent_index],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def rotate_user_agent(self):
        """Rotate to next user agent"""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.USER_AGENTS)
        self._update_session_headers()
        logger.debug(f"Rotated to user agent: {self.USER_AGENTS[self.current_user_agent_index]}")
        
    def extract_game_data(self, game_url: str) -> Tuple[ExtractionResult, Optional[Dict[str, Any]], Optional[ExtractionMetadata]]:
        """
        Extract game data from NBA.com URL
        
        Returns:
            (result_status, json_data, metadata)
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Extracting data from: {game_url}")
            
            # Make request
            response = self.session.get(game_url)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Handle different response codes
            if response.status_code == 429:
                logger.warning(f"Rate limited for URL: {game_url}")
                return ExtractionResult.RATE_LIMITED, None, None
                
            elif response.status_code == 404:
                logger.warning(f"Game not found (404): {game_url}")
                return ExtractionResult.NO_DATA, None, None
                
            elif response.status_code >= 500:
                logger.error(f"Server error ({response.status_code}): {game_url}")
                return ExtractionResult.SERVER_ERROR, None, None
                
            elif response.status_code != 200:
                logger.error(f"Unexpected status code {response.status_code}: {game_url}")
                return ExtractionResult.NETWORK_ERROR, None, None
            
            # Parse HTML and extract JSON
            soup = BeautifulSoup(response.content, 'html.parser')
            json_data = self._extract_next_data(soup)
            
            if not json_data:
                logger.warning(f"No __NEXT_DATA__ found in: {game_url}")
                return ExtractionResult.NO_DATA, None, None
            
            # Validate and assess data quality
            quality = self._assess_data_quality(json_data)
            
            # Create metadata
            json_str = json.dumps(json_data)
            metadata = ExtractionMetadata(
                extraction_time_ms=response_time_ms,
                response_size_bytes=len(response.content),
                json_size_bytes=len(json_str.encode('utf-8')),
                data_quality=quality,
                user_agent_used=self.USER_AGENTS[self.current_user_agent_index]
            )
            
            logger.info(f"Successfully extracted data from {game_url} "
                       f"(quality: {quality.completeness_score:.2f}, "
                       f"size: {metadata.json_size_bytes} bytes)")
            
            return ExtractionResult.SUCCESS, json_data, metadata
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout extracting data from: {game_url}")
            return ExtractionResult.TIMEOUT, None, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error extracting data from {game_url}: {e}")
            return ExtractionResult.NETWORK_ERROR, None, None
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {game_url}: {e}")
            return ExtractionResult.INVALID_JSON, None, None
            
        except Exception as e:
            logger.error(f"Unexpected error extracting data from {game_url}: {e}")
            return ExtractionResult.NETWORK_ERROR, None, None
    
    def _extract_next_data(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract JSON data from __NEXT_DATA__ script tag"""
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        
        if not script_tag or not script_tag.string:
            return None
        
        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse __NEXT_DATA__ JSON: {e}")
            return None
    
    def _assess_data_quality(self, json_data: Dict[str, Any]) -> DataQuality:
        """Assess the quality and completeness of extracted game data"""
        missing_fields = []
        
        # Check basic structure
        has_props = self._check_path(json_data, ['props'], missing_fields)
        has_page_props = self._check_path(json_data, ['props', 'pageProps'], missing_fields)
        
        # Check game data
        has_game = self._check_path(json_data, ['props', 'pageProps', 'game'], missing_fields)
        has_game_metadata = False
        if has_game:
            game_data = json_data['props']['pageProps']['game']
            has_game_metadata = all(key in game_data for key in ['gameId', 'gameTimeUTC', 'homeTeam', 'awayTeam'])
            if not has_game_metadata:
                missing_fields.extend(['game.gameId', 'game.gameTimeUTC', 'game.homeTeam', 'game.awayTeam'])
        
        # Check for play-by-play data
        has_play_by_play = False
        total_plays = 0
        
        if has_page_props:
            page_props = json_data['props']['pageProps']
            
            # Check various possible locations for play-by-play data
            pbp_keys = ['playByPlay', 'plays', 'gameActions', 'actions']
            for key in pbp_keys:
                if key in page_props and isinstance(page_props[key], list):
                    has_play_by_play = True
                    total_plays = len(page_props[key])
                    break
                    
            # Also check nested in game object
            if not has_play_by_play and has_game:
                game_data = page_props['game']
                for key in pbp_keys:
                    if key in game_data and isinstance(game_data[key], list):
                        has_play_by_play = True
                        total_plays = len(game_data[key])
                        break
        
        if not has_play_by_play:
            missing_fields.append('playByPlay')
        
        # Check for box score data
        has_box_score = False
        if has_page_props:
            page_props = json_data['props']['pageProps']
            box_score_keys = ['boxScore', 'gameStats', 'playerStats', 'teamStats']
            
            for key in box_score_keys:
                if key in page_props:
                    has_box_score = True
                    break
                    
            # Also check in game object
            if not has_box_score and has_game:
                game_data = page_props['game']
                for key in box_score_keys:
                    if key in game_data:
                        has_box_score = True
                        break
        
        if not has_box_score:
            missing_fields.append('boxScore')
        
        # Calculate completeness score
        total_components = 4  # props, game metadata, play-by-play, box score
        present_components = sum([
            has_props and has_page_props,
            has_game_metadata,
            has_play_by_play,
            has_box_score
        ])
        
        completeness_score = present_components / total_components
        
        # Bonus for having actual play data
        if total_plays > 50:  # Reasonable minimum for a full game
            completeness_score = min(1.0, completeness_score + 0.1)
        
        return DataQuality(
            completeness_score=completeness_score,
            has_play_by_play=has_play_by_play,
            has_box_score=has_box_score,
            has_game_metadata=has_game_metadata,
            total_plays=total_plays,
            missing_fields=missing_fields
        )
    
    def _check_path(self, data: Dict[str, Any], path: List[str], missing_fields: List[str]) -> bool:
        """Check if a nested path exists in the data"""
        current = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                missing_fields.append('.'.join(path))
                return False
            current = current[key]
        return True
    
    def validate_json_structure(self, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that JSON has expected NBA.com structure"""
        issues = []
        
        if not isinstance(json_data, dict):
            issues.append("Root is not a dictionary")
            return False, issues
        
        # Check for required top-level structure
        if 'props' not in json_data:
            issues.append("Missing 'props' key")
        elif not isinstance(json_data['props'], dict):
            issues.append("'props' is not a dictionary")
        else:
            props = json_data['props']
            
            if 'pageProps' not in props:
                issues.append("Missing 'props.pageProps' key")
            elif not isinstance(props['pageProps'], dict):
                issues.append("'props.pageProps' is not a dictionary")
        
        # Check for buildId (indicates this is Next.js data)
        if 'buildId' not in json_data:
            issues.append("Missing 'buildId' (may not be Next.js data)")
        
        return len(issues) == 0, issues
    
    def calculate_completeness_score(self, json_data: Dict[str, Any]) -> float:
        """Calculate a completeness score for the JSON data"""
        quality = self._assess_data_quality(json_data)
        return quality.completeness_score