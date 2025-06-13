#!/usr/bin/env python3
"""Demo script for NBA.com scraping functionality."""

import sys
import logging
from datetime import date, datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scrapers import GameURLScraper, GameDataScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_url_scraping():
    """Demonstrate game URL discovery."""
    logger.info("=== NBA Game URL Scraping Demo ===")
    
    scraper = GameURLScraper(delay=1.0)
    
    # Try to scrape games for a recent date
    test_date = date(2024, 1, 15)
    logger.info(f"Discovering games for {test_date}")
    
    try:
        games = scraper.get_games_for_date(test_date)
        logger.info(f"Found {len(games)} games:")
        
        for game in games[:3]:  # Show first 3 games
            logger.info(f"  - {game['away_team_tricode']} @ {game['home_team_tricode']} "
                       f"(Game ID: {game['nba_game_id']})")
            logger.info(f"    URL: {game['game_url']}")
        
        return games[0] if games else None
        
    except Exception as e:
        logger.error(f"Error scraping game URLs: {e}")
        return None


def demo_game_data_scraping(game_url):
    """Demonstrate game data extraction."""
    logger.info("\n=== NBA Game Data Scraping Demo ===")
    
    scraper = GameDataScraper(delay=2.0)
    
    logger.info(f"Scraping game data from: {game_url}")
    
    try:
        game_data = scraper.scrape_game_data(game_url)
        
        if game_data:
            logger.info("Successfully scraped game data!")
            
            # Validate the data
            if scraper.validate_game_data(game_data):
                logger.info("Game data structure is valid")
                
                # Extract metadata
                metadata = scraper.extract_game_metadata(game_data)
                if metadata:
                    logger.info("Game metadata:")
                    logger.info(f"  - Game ID: {metadata.get('gameId')}")
                    logger.info(f"  - Game Time: {metadata.get('gameTimeUTC')}")
                    logger.info(f"  - Status: {metadata.get('gameStatus')}")
                    logger.info(f"  - Period: {metadata.get('period')}")
                
                # Try to extract play-by-play
                pbp_data = scraper.extract_play_by_play(game_data)
                if pbp_data:
                    logger.info(f"Found {len(pbp_data)} play-by-play entries")
                else:
                    logger.info("No play-by-play data found (this is expected for some games)")
            else:
                logger.warning("Game data structure is invalid")
        else:
            logger.warning("No game data returned")
            
    except Exception as e:
        logger.error(f"Error scraping game data: {e}")


def main():
    """Run the scraping demo."""
    logger.info("NBA.com Scraping Demo Starting...")
    
    # Demo URL scraping
    sample_game = demo_url_scraping()
    
    if sample_game:
        # Demo game data scraping
        demo_game_data_scraping(sample_game['game_url'])
    else:
        logger.warning("No games found for URL scraping demo")
        
        # Use a fallback URL for data scraping demo
        fallback_url = "https://www.nba.com/game/bos-vs-lal-0022400123"
        logger.info(f"Using fallback URL for game data demo: {fallback_url}")
        demo_game_data_scraping(fallback_url)
    
    logger.info("Demo completed!")


if __name__ == "__main__":
    main()