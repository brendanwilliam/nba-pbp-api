"""Main orchestrator for NBA game scraping operations."""

import logging
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.database import get_db
from core.models import Game, Team, ScrapeQueue, RawGameData
from scrapers.game_url_scraper import GameURLScraper
from scrapers.game_data_scraper import GameDataScraper

logger = logging.getLogger(__name__)


class ScrapingManager:
    """Manages the complete NBA game scraping process."""
    
    def __init__(self, db: Session, url_scraper_delay: float = 1.0, data_scraper_delay: float = 2.0):
        """Initialize scraping manager with database session."""
        self.db = db
        self.url_scraper = GameURLScraper(delay=url_scraper_delay)
        self.data_scraper = GameDataScraper(delay=data_scraper_delay)
    
    def discover_games_for_date(self, game_date: date, season: str) -> int:
        """Discover and queue games for a specific date."""
        logger.info(f"Discovering games for {game_date}")
        
        # Get game URLs from NBA.com
        game_info_list = self.url_scraper.get_games_for_date(game_date)
        
        games_added = 0
        for game_info in game_info_list:
            if self._create_game_record(game_info, season):
                games_added += 1
        
        self.db.commit()
        logger.info(f"Added {games_added} new games for {game_date}")
        return games_added
    
    def _create_game_record(self, game_info: dict, season: str) -> bool:
        """Create game record and add to scraping queue."""
        # Check if game already exists
        existing_game = self.db.query(Game).filter_by(
            nba_game_id=game_info['nba_game_id']
        ).first()
        
        if existing_game:
            logger.debug(f"Game {game_info['nba_game_id']} already exists")
            return False
        
        # Get or create teams
        home_team = self._get_or_create_team(game_info['home_team_tricode'])
        away_team = self._get_or_create_team(game_info['away_team_tricode'])
        
        if not home_team or not away_team:
            logger.error(f"Failed to get teams for game {game_info['nba_game_id']}")
            return False
        
        # Create game record
        game = Game(
            nba_game_id=game_info['nba_game_id'],
            game_date=datetime.fromisoformat(game_info['game_date']).date(),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            season=season,
            game_type="Regular Season",  # Default, can be updated later
            game_url=game_info['game_url']
        )
        
        self.db.add(game)
        self.db.flush()  # Get the game ID
        
        # Add to scraping queue
        scrape_entry = ScrapeQueue(
            game_id=game.id,
            status="pending"
        )
        self.db.add(scrape_entry)
        
        logger.debug(f"Created game record for {game_info['nba_game_id']}")
        return True
    
    def _get_or_create_team(self, tricode: str) -> Optional[Team]:
        """Get existing team or create new one."""
        team = self.db.query(Team).filter_by(tricode=tricode).first()
        
        if not team:
            # Create new team with basic info
            team = Team(
                tricode=tricode,
                name=f"{tricode} Team",  # Placeholder, should be updated with real data
                city=tricode  # Placeholder
            )
            self.db.add(team)
            self.db.flush()
            logger.info(f"Created new team: {tricode}")
        
        return team
    
    def scrape_pending_games(self, limit: int = 10) -> int:
        """Scrape data for pending games in the queue."""
        pending_games = self.db.query(ScrapeQueue).join(Game).filter(
            ScrapeQueue.status == "pending"
        ).limit(limit).all()
        
        if not pending_games:
            logger.info("No pending games to scrape")
            return 0
        
        logger.info(f"Scraping {len(pending_games)} pending games")
        scraped_count = 0
        
        for scrape_entry in pending_games:
            if self._scrape_single_game(scrape_entry):
                scraped_count += 1
        
        self.db.commit()
        logger.info(f"Successfully scraped {scraped_count}/{len(pending_games)} games")
        return scraped_count
    
    def _scrape_single_game(self, scrape_entry: ScrapeQueue) -> bool:
        """Scrape data for a single game."""
        game = scrape_entry.game
        logger.info(f"Scraping game {game.nba_game_id}")
        
        # Update status to in_progress
        scrape_entry.status = "in_progress"
        scrape_entry.attempts += 1
        scrape_entry.last_attempt = datetime.utcnow()
        self.db.flush()
        
        try:
            # Scrape the game data
            raw_data = self.data_scraper.scrape_game_data(game.game_url)
            
            if raw_data:
                # Validate the data
                if self.data_scraper.validate_game_data(raw_data):
                    # Store raw data
                    raw_game_data = RawGameData(
                        game_id=game.id,
                        raw_json=raw_data
                    )
                    self.db.add(raw_game_data)
                    
                    # Mark as completed
                    scrape_entry.status = "completed"
                    scrape_entry.error_message = None
                    
                    logger.info(f"Successfully scraped game {game.nba_game_id}")
                    return True
                else:
                    scrape_entry.status = "failed"
                    scrape_entry.error_message = "Invalid game data structure"
            else:
                scrape_entry.status = "failed"
                scrape_entry.error_message = "No data returned from scraper"
        
        except Exception as e:
            logger.error(f"Error scraping game {game.nba_game_id}: {e}")
            scrape_entry.status = "failed"
            scrape_entry.error_message = str(e)
        
        return False
    
    def get_scraping_stats(self) -> dict:
        """Get statistics about scraping progress."""
        stats = {}
        
        for status in ["pending", "in_progress", "completed", "failed"]:
            count = self.db.query(ScrapeQueue).filter_by(status=status).count()
            stats[status] = count
        
        total_games = self.db.query(Game).count()
        stats["total_games"] = total_games
        
        return stats
    
    def retry_failed_games(self, max_attempts: int = 3) -> int:
        """Retry scraping failed games that haven't exceeded max attempts."""
        failed_games = self.db.query(ScrapeQueue).filter(
            and_(
                ScrapeQueue.status == "failed",
                ScrapeQueue.attempts < max_attempts
            )
        ).all()
        
        logger.info(f"Retrying {len(failed_games)} failed games")
        
        for scrape_entry in failed_games:
            scrape_entry.status = "pending"
            scrape_entry.error_message = None
        
        self.db.commit()
        
        # Now scrape the retried games
        return self.scrape_pending_games(limit=len(failed_games))