"""
Manages the scraping of raw game data for WNBA games and populating the database.

This manager coordinates URL generation, raw data scraping, and session management
to provide a comprehensive scraping solution for WNBA game data.
"""

import argparse
import logging
import sys
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..scrapers.game_url_generator import GameURLGenerator, GameURLInfo
from ..scrapers.raw_data_extractor import RawDataExtractor, ExtractionResult
from ..database.services import DatabaseService

logger = logging.getLogger(__name__)


class ScraperManager:
    """Coordinates WNBA game data scraping operations."""
    
    def __init__(self):
        self.url_generator = GameURLGenerator()
        self.data_extractor = RawDataExtractor()
        self.current_session_id = None
    
    def start_scraping_session(self, session_name: str) -> Optional[int]:
        """Start a new scraping session and return session ID."""
        with DatabaseService() as db:
            session = db.scraping_session.start_session(session_name)
            if session:
                self.current_session_id = session.id
                logger.info(f"Started scraping session '{session_name}' with ID {session.id}")
                return session.id
            return None
    
    def update_session_progress(self, games_scraped: int, errors_count: int = 0):
        """Update current session progress."""
        if not self.current_session_id:
            logger.warning("No active session to update")
            return
        
        with DatabaseService() as db:
            db.scraping_session.update_session(
                self.current_session_id, 
                games_scraped=games_scraped,
                errors_count=errors_count
            )
    
    def complete_session(self, status: str = 'completed'):
        """Complete the current scraping session."""
        if not self.current_session_id:
            logger.warning("No active session to complete")
            return
        
        with DatabaseService() as db:
            db.scraping_session.update_session(self.current_session_id, status=status)
            logger.info(f"Completed scraping session {self.current_session_id} with status: {status}")
    
    def generate_urls_for_season(self, season: int, game_type: str = 'regular') -> List[GameURLInfo]:
        """Generate game URLs for a specific season and game type."""
        game_urls = []
        
        if game_type == 'regular':
            game_ids = self.url_generator.generate_regular_season_ids(season)
        elif game_type == 'playoff':
            game_ids = self.url_generator.generate_playoff_ids(season)
        else:
            logger.error(f"Invalid game_type: {game_type}. Must be 'regular' or 'playoff'")
            return []
        
        for game_id in game_ids:
            game_url = self.url_generator.generate_game_url(game_id)
            game_urls.append(GameURLInfo(
                game_id=game_id,
                season=str(season),
                game_url=game_url,
                game_type=game_type
            ))
        
        logger.info(f"Generated {len(game_urls)} URLs for {season} {game_type} season")
        return game_urls
    
    def scrape_single_game(self, game_url_info: GameURLInfo) -> bool:
        """Scrape a single game and save to database."""
        try:
            # Check if game already exists
            with DatabaseService() as db:
                if db.game_data.game_exists(int(game_url_info.game_id)):
                    logger.info(f"Game {game_url_info.game_id} already exists, skipping")
                    return True
            
            # Extract game data
            result, game_data, metadata = self.data_extractor.extract_game_data(game_url_info.game_url)
            
            if result != ExtractionResult.SUCCESS or not game_data:
                logger.warning(f"Failed to extract data for game {game_url_info.game_id}: {result}")
                return False
            
            # Save to database
            with DatabaseService() as db:
                success = db.game_data.insert_game_data(
                    game_id=int(game_url_info.game_id),
                    season=int(game_url_info.season),
                    game_type=game_url_info.game_type,
                    game_url=game_url_info.game_url,
                    game_data=game_data
                )
                
                if success:
                    logger.info(f"Successfully scraped game {game_url_info.game_id}")
                    return True
                else:
                    logger.error(f"Failed to save game {game_url_info.game_id} to database")
                    return False
        
        except Exception as e:
            logger.error(f"Error scraping game {game_url_info.game_id}: {e}")
            return False
    
    def scrape_season(self, season: int, game_type: str = 'regular', max_games: Optional[int] = None) -> Dict[str, int]:
        """
        Scrape all games for a season.
        
        Args:
            season: WNBA season year
            game_type: 'regular' or 'playoff'
            max_games: Maximum number of games to scrape (for testing)
            
        Returns:
            Dict with scraping statistics
        """
        session_name = f"{season}_{game_type}_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start scraping session")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
        
        # Generate URLs
        game_urls = self.generate_urls_for_season(season, game_type)
        
        if max_games:
            game_urls = game_urls[:max_games]
            logger.info(f"Limited to first {max_games} games for testing")
        
        # Scraping statistics
        stats = {'total': len(game_urls), 'success': 0, 'failed': 0, 'skipped': 0}
        
        logger.info(f"Starting to scrape {stats['total']} games for {season} {game_type} season")
        
        for i, game_url_info in enumerate(game_urls, 1):
            logger.info(f"Scraping game {i}/{stats['total']}: {game_url_info.game_id}")
            
            # Check if already exists
            with DatabaseService() as db:
                if db.game_data.game_exists(int(game_url_info.game_id)):
                    stats['skipped'] += 1
                    logger.info(f"Game {game_url_info.game_id} already exists, skipping")
                    continue
            
            success = self.scrape_single_game(game_url_info)
            
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            
            # Update session progress every 10 games
            if i % 10 == 0:
                self.update_session_progress(stats['success'], stats['failed'])
            
            # Small delay to be respectful to the server
            time.sleep(1)
        
        # Final session update
        self.update_session_progress(stats['success'], stats['failed'])
        
        # Complete session
        session_status = 'completed' if stats['failed'] == 0 else 'completed_with_errors'
        self.complete_session(session_status)
        
        logger.info(f"Scraping completed. Success: {stats['success']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
        return stats
    
    def scrape_all_seasons(self, game_type: str = 'regular', max_games_total: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape all available seasons for a specific game type.
        
        Args:
            game_type: 'regular' or 'playoff'
            max_games_total: Maximum total games across ALL seasons (for testing)
            
        Returns:
            Dict with overall scraping statistics
        """
        session_name = f"all_seasons_{game_type}_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start bulk scraping session")
            return {'seasons_processed': 0, 'total_games': 0, 'total_success': 0, 'total_failed': 0, 'total_skipped': 0}
        
        # Get available seasons from the generator
        if game_type == 'regular':
            seasons = self.url_generator.regular_season_df['season'].unique().tolist()
        else:
            seasons = self.url_generator.playoff_df['season'].unique().tolist()
        
        seasons = sorted(seasons)
        logger.info(f"Starting bulk scraping for {len(seasons)} seasons ({game_type} games)")
        if max_games_total:
            logger.info(f"Limited to maximum {max_games_total} total games across all seasons")
        
        overall_stats = {
            'seasons_processed': 0,
            'total_games': 0,
            'total_success': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'season_results': []
        }
        
        games_scraped = 0
        
        for season in seasons:
            # Check if we've hit the total game limit
            if max_games_total and games_scraped >= max_games_total:
                logger.info(f"Reached maximum total games limit ({max_games_total}), stopping")
                break
                
            logger.info(f"Processing season {season} ({game_type})...")
            
            try:
                # Calculate remaining games for this season
                remaining_games = max_games_total - games_scraped if max_games_total else None
                
                # Generate URLs for this season
                game_urls = self.generate_urls_for_season(season, game_type)
                
                if remaining_games:
                    game_urls = game_urls[:remaining_games]
                
                if not game_urls:
                    logger.info(f"No games to scrape for season {season}")
                    overall_stats['season_results'].append({
                        'season': season,
                        'stats': {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
                    })
                    continue
                
                # Process this season's games
                season_stats = {'total': len(game_urls), 'success': 0, 'failed': 0, 'skipped': 0}
                
                for i, game_url_info in enumerate(game_urls, 1):
                    logger.info(f"Season {season} - Game {i}/{len(game_urls)}: {game_url_info.game_id}")
                    
                    # Check if already exists
                    with DatabaseService() as db:
                        if db.game_data.game_exists(int(game_url_info.game_id)):
                            season_stats['skipped'] += 1
                            logger.info(f"Game {game_url_info.game_id} already exists, skipping")
                            continue
                    
                    success = self.scrape_single_game(game_url_info)
                    
                    if success:
                        season_stats['success'] += 1
                        games_scraped += 1
                    else:
                        season_stats['failed'] += 1
                    
                    # Update progress every 10 games
                    if (season_stats['success'] + season_stats['failed']) % 10 == 0:
                        self.update_session_progress(
                            overall_stats['total_success'] + season_stats['success'], 
                            overall_stats['total_failed'] + season_stats['failed']
                        )
                    
                    # Small delay to be respectful
                    time.sleep(1)
                    
                    # Check total limit again
                    if max_games_total and games_scraped >= max_games_total:
                        logger.info(f"Reached maximum total games limit ({max_games_total})")
                        break
                
                # Update overall stats
                overall_stats['seasons_processed'] += 1
                overall_stats['total_games'] += season_stats['total']
                overall_stats['total_success'] += season_stats['success']
                overall_stats['total_failed'] += season_stats['failed']
                overall_stats['total_skipped'] += season_stats['skipped']
                
                overall_stats['season_results'].append({
                    'season': season,
                    'stats': season_stats
                })
                
                logger.info(f"Completed season {season}: {season_stats['success']} success, "
                           f"{season_stats['failed']} failed, {season_stats['skipped']} skipped")
                
            except Exception as e:
                logger.error(f"Error processing season {season}: {e}")
                overall_stats['season_results'].append({
                    'season': season,
                    'error': str(e)
                })
        
        # Update session with final stats
        self.update_session_progress(overall_stats['total_success'], overall_stats['total_failed'])
        self.complete_session('completed' if overall_stats['total_failed'] == 0 else 'completed_with_errors')
        
        logger.info(f"Bulk scraping completed. Seasons: {overall_stats['seasons_processed']}, "
                   f"Total games: {overall_stats['total_games']}, "
                   f"Success: {overall_stats['total_success']}, "
                   f"Failed: {overall_stats['total_failed']}, "
                   f"Skipped: {overall_stats['total_skipped']}")
        
        return overall_stats
    
    def scrape_all_games(self, max_games_per_season: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape all regular and playoff games for all seasons.
        
        Args:
            max_games_per_season: Maximum games per season (for testing)
            
        Returns:
            Dict with overall scraping statistics
        """
        session_name = f"all_games_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start all-games scraping session")
            return {'regular_stats': {}, 'playoff_stats': {}, 'combined_stats': {}}
        
        logger.info("Starting comprehensive scraping of ALL WNBA games (regular + playoff)")
        
        # Scrape all regular season games
        logger.info("=== SCRAPING ALL REGULAR SEASON GAMES ===")
        regular_stats = self.scrape_all_seasons('regular', max_games_per_season)
        
        # Scrape all playoff games  
        logger.info("=== SCRAPING ALL PLAYOFF GAMES ===")
        playoff_stats = self.scrape_all_seasons('playoff', max_games_per_season)
        
        # Combined statistics
        combined_stats = {
            'total_seasons': regular_stats['seasons_processed'] + playoff_stats['seasons_processed'],
            'total_games': regular_stats['total_games'] + playoff_stats['total_games'],
            'total_success': regular_stats['total_success'] + playoff_stats['total_success'],
            'total_failed': regular_stats['total_failed'] + playoff_stats['total_failed'],
            'total_skipped': regular_stats['total_skipped'] + playoff_stats['total_skipped']
        }
        
        # Update session with combined stats
        self.update_session_progress(combined_stats['total_success'], combined_stats['total_failed'])
        self.complete_session('completed' if combined_stats['total_failed'] == 0 else 'completed_with_errors')
        
        logger.info(f"ALL-GAMES SCRAPING COMPLETED!")
        logger.info(f"Regular seasons: {regular_stats['seasons_processed']}, "
                   f"Playoff seasons: {playoff_stats['seasons_processed']}")
        logger.info(f"Total games processed: {combined_stats['total_games']}")
        logger.info(f"Success: {combined_stats['total_success']}, "
                   f"Failed: {combined_stats['total_failed']}, "
                   f"Skipped: {combined_stats['total_skipped']}")
        
        return {
            'regular_stats': regular_stats,
            'playoff_stats': playoff_stats,
            'combined_stats': combined_stats
        }
    
    def list_active_sessions(self):
        """List all currently active scraping sessions."""
        with DatabaseService() as db:
            sessions = db.scraping_session.get_active_sessions()
            if sessions:
                print("\nActive scraping sessions:")
                for session in sessions:
                    print(f"  ID: {session.id}, Name: {session.session_name}, Started: {session.start_time}")
            else:
                print("No active scraping sessions found.")


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('scraper_manager.log')
        ]
    )


def main():
    """Main CLI interface for the scraper manager."""
    parser = argparse.ArgumentParser(description='WNBA Game Data Scraper Manager')
    
    parser.add_argument('command', choices=['scrape-season', 'scrape-all-regular', 'scrape-all-playoff', 'scrape-all-games', 'test-single', 'list-sessions'],
                       help='Command to execute')
    
    parser.add_argument('--season', type=int, required=False,
                       help='WNBA season year (e.g., 2024)')
    
    parser.add_argument('--game-type', choices=['regular', 'playoff'], default='regular',
                       help='Type of games to scrape (default: regular)')
    
    parser.add_argument('--max-games', type=int, default=None,
                       help='Maximum number of games to scrape (for testing)')
    
    parser.add_argument('--game-id', type=str, default=None,
                       help='Specific game ID to scrape (for test-single command)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Initialize scraper manager
    manager = ScraperManager()
    
    try:
        if args.command == 'scrape-season':
            if not args.season:
                logger.error("--season is required for scrape-season command")
                sys.exit(1)
            
            stats = manager.scrape_season(args.season, args.game_type, args.max_games)
            
            print(f"\nScraping Results for {args.season} {args.game_type} season:")
            print(f"  Total games: {stats['total']}")
            print(f"  Successfully scraped: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Skipped (already exist): {stats['skipped']}")
            
        elif args.command == 'test-single':
            if not args.game_id or not args.season:
                logger.error("--game-id and --season are required for test-single command")
                sys.exit(1)
            
            # Create test game URL info
            game_url = manager.url_generator.generate_game_url(args.game_id)
            game_url_info = GameURLInfo(
                game_id=args.game_id,
                season=str(args.season),
                game_url=game_url,
                game_type=args.game_type
            )
            
            session_name = f"test_single_{args.game_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            manager.start_scraping_session(session_name)
            
            success = manager.scrape_single_game(game_url_info)
            
            if success:
                print(f"Successfully scraped game {args.game_id}")
                manager.complete_session('completed')
            else:
                print(f"Failed to scrape game {args.game_id}")
                manager.complete_session('failed')
                
        elif args.command == 'scrape-all-regular':
            stats = manager.scrape_all_seasons('regular', args.max_games)
            
            print(f"\nAll Regular Season Scraping Results:")
            print(f"  Seasons processed: {stats['seasons_processed']}")
            print(f"  Total games: {stats['total_games']}")
            print(f"  Successfully scraped: {stats['total_success']}")
            print(f"  Failed: {stats['total_failed']}")
            print(f"  Skipped (already exist): {stats['total_skipped']}")
            
            print(f"\nSeason-by-season breakdown:")
            for result in stats['season_results']:
                if 'error' in result:
                    print(f"  {result['season']}: ERROR - {result['error']}")
                else:
                    s = result['stats']
                    print(f"  {result['season']}: {s['success']} success, {s['failed']} failed, {s['skipped']} skipped")
        
        elif args.command == 'scrape-all-playoff':
            stats = manager.scrape_all_seasons('playoff', args.max_games)
            
            print(f"\nAll Playoff Scraping Results:")
            print(f"  Seasons processed: {stats['seasons_processed']}")
            print(f"  Total games: {stats['total_games']}")
            print(f"  Successfully scraped: {stats['total_success']}")
            print(f"  Failed: {stats['total_failed']}")
            print(f"  Skipped (already exist): {stats['total_skipped']}")
            
            print(f"\nSeason-by-season breakdown:")
            for result in stats['season_results']:
                if 'error' in result:
                    print(f"  {result['season']}: ERROR - {result['error']}")
                else:
                    s = result['stats']
                    print(f"  {result['season']}: {s['success']} success, {s['failed']} failed, {s['skipped']} skipped")
        
        elif args.command == 'scrape-all-games':
            results = manager.scrape_all_games(args.max_games)
            
            print(f"\nALL GAMES SCRAPING RESULTS:")
            print(f"="*50)
            
            combined = results['combined_stats']
            print(f"COMBINED TOTALS:")
            print(f"  Total games processed: {combined['total_games']}")
            print(f"  Successfully scraped: {combined['total_success']}")
            print(f"  Failed: {combined['total_failed']}")
            print(f"  Skipped (already exist): {combined['total_skipped']}")
            
            regular = results['regular_stats']
            playoff = results['playoff_stats']
            
            print(f"\nREGULAR SEASON SUMMARY:")
            print(f"  Seasons: {regular['seasons_processed']}")
            print(f"  Games: {regular['total_games']} (Success: {regular['total_success']}, Failed: {regular['total_failed']}, Skipped: {regular['total_skipped']})")
            
            print(f"\nPLAYOFF SUMMARY:")
            print(f"  Seasons: {playoff['seasons_processed']}")
            print(f"  Games: {playoff['total_games']} (Success: {playoff['total_success']}, Failed: {playoff['total_failed']}, Skipped: {playoff['total_skipped']})")
            
        elif args.command == 'list-sessions':
            manager.list_active_sessions()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        if manager.current_session_id:
            manager.complete_session('failed')
        sys.exit(1)


if __name__ == "__main__":
    main()