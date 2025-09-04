"""
Extracts raw game data from a game URL.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExtractionResult(Enum):
    """Result of the extraction process"""
    SUCCESS = "success"
    NO_DATA = "no_data"
    INVALID_JSON = "invalid_json"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"


class DataQuality(Enum):
    """Data quality indicators"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"


@dataclass
class ExtractionMetadata:
    """Metadata about the extraction process"""
    extraction_time_ms: int
    response_size_bytes: int
    json_size_bytes: int
    data_quality: DataQuality
    user_agent_used: str


class RawDataExtractor:
    """Extracts raw game data from a game URL."""

    def __init__(self, timeout: int = 30):
        """Initialize extractor with configuration"""
        self.timeout = timeout
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def extract_game_data(self, game_url: str) -> Tuple[ExtractionResult, Optional[Dict[str, Any]], Optional[ExtractionMetadata]]:
        """Extract game data from a game URL."""
        start_time = time.time()
        
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(game_url, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            data_script = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not data_script:
                logger.warning(f"No __NEXT_DATA__ script found in {game_url}")
                return ExtractionResult.NO_DATA, None, None
            
            try:
                game_json = json.loads(data_script.text)
                game_data = game_json.get('props', {}).get('pageProps', {})
                
                if not game_data:
                    logger.warning(f"No pageProps data found in {game_url}")
                    return ExtractionResult.NO_DATA, None, None
                
                # Determine data quality
                data_quality = DataQuality.COMPLETE if game_data else DataQuality.EMPTY
                
                metadata = ExtractionMetadata(
                    extraction_time_ms=int((time.time() - start_time) * 1000),
                    response_size_bytes=len(response.content),
                    json_size_bytes=len(json.dumps(game_data).encode('utf-8')),
                    data_quality=data_quality,
                    user_agent_used=self.user_agent
                )

                return ExtractionResult.SUCCESS, game_data, metadata
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for {game_url}: {e}")
                return ExtractionResult.INVALID_JSON, None, None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout error extracting game data from {game_url}")
            return ExtractionResult.TIMEOUT, None, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error extracting game data from {game_url}: {e}")
            return ExtractionResult.NETWORK_ERROR, None, None
        except Exception as e:
            logger.error(f"Unexpected error extracting game data from {game_url}: {e}")
            return ExtractionResult.SERVER_ERROR, None, None