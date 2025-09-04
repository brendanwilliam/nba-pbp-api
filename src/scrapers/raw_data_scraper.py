"""
Scrapes raw game data for WNBA games.

This scraper uses the game_url_generator to generate game URLs and the raw_data_extractor to extract raw game data.

The scraper will generate a queue of game URLs and extract raw game data for each game and save it to a database.
"""

import os
import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from .game_url_generator import GameURLGenerator, GameURLInfo
from .raw_data_extractor import RawDataExtractor, ExtractionMetadata

logger = logging.getLogger(__name__)


@dataclass
class RawDataScraper:
    """Scrapes raw game data for WNBA games."""
    game_url_generator: GameURLGenerator
    raw_data_extractor: RawDataExtractor
    db_session: Session

    def __init__(self, game_url_generator: GameURLGenerator, raw_data_extractor: RawDataExtractor, db_session: Session):
        self.game_url_generator = game_url_generator
        self.raw_data_extractor = raw_data_extractor
        self.db_session = db_session

    def scrape_game_data(self, game_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[ExtractionMetadata]]:
        """Scrapes raw game data for a single game."""
        try:
            game_data, metadata = self.raw_data_extractor.extract_game_data(game_url)
            return game_data, metadata
        except Exception as e:
            logger.error(f"Error scraping game data from {game_url}: {e}")
            return None, None

    def add_game_data_to_db(self, game_data: Dict[str, Any], metadata: Optional[ExtractionMetadata] = None) -> None:
        """Adds game data to the database in the raw_game_data table."""
        try:
            self.db_session.add(game_data)
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Error adding game data to database: {e}")

    def scrape_game_data_queue(self, game_url_queue: List[str]) -> Tuple[Optional[Dict[str, Any]], Optional[ExtractionMetadata]]:
        """Scrapes raw game data for a queue of games."""
        try:
            game_data = []
            for game_url in game_url_queue:

                # Extract game data
                game_data, metadata = self.raw_data_extractor.extract_game_data(game_url)

                # Save game data to database
                self.add_game_data_to_db(game_data, metadata)

        except Exception as e:
            logger.error(f"Error scraping game data from {game_url_queue}: {e}")
            return None, None



