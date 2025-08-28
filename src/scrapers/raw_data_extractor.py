"""
Extracts raw game data from a game URL.
"""

import requests
from bs4 import BeautifulSoup
import json
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult(str, Enum):
    """Result of the extraction process"""
    SUCCESS = "success"
    NO_DATA = "no_data"
    INVALID_JSON = "invalid_json"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"

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

    def extract_game_data(self, game_url: str) -> Tuple[ExtractionResult, Optional[Dict[str, Any]], Optional[ExtractionMetadata]]:
        """Extract game data from a game URL."""
        try:
            response = requests.get(game_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            data = soup.find('script', {'id': '__NEXT_DATA__'})
            game_json = json.loads(data.text)
            game_data = game_json['props']['pageProps']

            metadata = ExtractionMetadata(
                extraction_time_ms=int((time.time() - start_time) * 1000),
                response_size_bytes=len(response.content),
                json_size_bytes=len(json.dumps(game_data).encode('utf-8')),
                data_quality=DataQuality.COMPLETE,
                user_agent_used=self.USER_AGENTS[self.current_user_agent_index]
            )

            return ExtractionResult.SUCCESS, game_data, metadata
        except requests.exceptions.RequestException as e:
            logger.error(f"Error extracting game data from {game_url}: {e}")
            return ExtractionResult.NETWORK_ERROR, None, None