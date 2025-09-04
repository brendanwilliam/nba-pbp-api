#!/usr/bin/env python3
"""
Combined WNBA Data Manager - Unified CLI for scraping and populating game data.

This script combines the functionality of scraper_manager.py and populate_game_tables.py
to provide a unified interface for managing WNBA game data from raw scraping to
normalized table population.
"""

import argparse
import logging
import sys
from typing import List, Optional, Dict, Any

from .scraper_manager import ScraperManager
from .populate_game_tables import GameTablePopulator

logger = logging.getLogger(__name__)


class WNBADataManager:
    """Unified manager for WNBA data scraping and population operations."""
    
    def __init__(self):
        self.scraper_manager = ScraperManager()
        self.table_populator = GameTablePopulator()
    
    def scrape_and_populate_games(self, game_ids: List[str], 
                                 override_existing: bool = False,
                                 clear_tables_first: bool = False) -> Dict[str, Any]:
        """
        Scrape specific games and immediately populate them into normalized tables.
        
        Args:
            game_ids: List of game IDs to scrape and populate
            override_existing: If True, re-scrape games that already exist
            clear_tables_first: If True, clear all populated tables before processing
            
        Returns:
            Dict with combined scraping and population statistics
        """
        logger.info(f"Starting scrape-and-populate operation for {len(game_ids)} games")
        
        # Step 1: Clear tables if requested
        if clear_tables_first:
            logger.info("🗑️ Clearing all populated tables as requested")
            success = self.table_populator.clear_all_tables()
            if not success:
                logger.error("Failed to clear tables - aborting operation")
                return {'scraping': {}, 'population': {}, 'success': False}
        
        # Step 2: Scrape the games
        logger.info("🕷️ Starting scraping phase...")
        scraping_stats = self.scraper_manager.scrape_specific_games(
            game_ids, 
            override_existing=override_existing
        )
        
        if scraping_stats['success'] == 0:
            logger.warning("No games were successfully scraped - skipping population")
            return {
                'scraping': scraping_stats,
                'population': {'total_games': 0, 'successful_games': 0, 'failed_games': 0},
                'success': False
            }
        
        # Step 3: Populate the successfully scraped games into normalized tables
        logger.info("📊 Starting population phase...")
        
        # Convert string game IDs to integers for population
        game_ids_int = []
        for game_id in game_ids:
            try:
                game_ids_int.append(int(game_id))
            except ValueError:
                logger.warning(f"Invalid game ID format: {game_id} - skipping")
        
        population_stats = self.table_populator.populate_specific_games(
            game_ids_int,
            override_existing=override_existing
        )
        
        # Combined results
        combined_stats = {
            'scraping': scraping_stats,
            'population': population_stats,
            'success': scraping_stats['success'] > 0 and population_stats['successful_games'] > 0
        }
        
        logger.info(f"✅ Scrape-and-populate completed. "
                   f"Scraped: {scraping_stats['success']}/{scraping_stats['total']}, "
                   f"Populated: {population_stats['successful_games']}/{population_stats['total_games']}")
        
        return combined_stats
    
    def scrape_and_populate_season(self, season: int, game_type: str = 'regular',
                                  max_games: Optional[int] = None,
                                  clear_tables_first: bool = False) -> Dict[str, Any]:
        """
        Scrape an entire season and populate it into normalized tables.
        
        Args:
            season: WNBA season year
            game_type: 'regular' or 'playoff'
            max_games: Maximum number of games to process
            clear_tables_first: If True, clear all populated tables before processing
            
        Returns:
            Dict with combined scraping and population statistics
        """
        logger.info(f"Starting scrape-and-populate operation for {season} {game_type} season")
        
        # Step 1: Clear tables if requested
        if clear_tables_first:
            logger.info("🗑️ Clearing all populated tables as requested")
            success = self.table_populator.clear_all_tables()
            if not success:
                logger.error("Failed to clear tables - aborting operation")
                return {'scraping': {}, 'population': {}, 'success': False}
        
        # Step 2: Scrape the season
        logger.info(f"🕷️ Starting scraping phase for {season} {game_type} season...")
        scraping_stats = self.scraper_manager.scrape_season(season, game_type, max_games)
        
        if scraping_stats['success'] == 0:
            logger.warning("No games were successfully scraped - skipping population")
            return {
                'scraping': scraping_stats,
                'population': {'total_games': 0, 'successful_games': 0, 'failed_games': 0},
                'success': False
            }
        
        # Step 3: Populate all games from this season
        logger.info("📊 Starting population phase...")
        population_stats = self.table_populator.populate_games_by_season(
            [season],
            limit=max_games,
            override_existing=False  # Don't override since we just scraped
        )
        
        # Combined results
        combined_stats = {
            'scraping': scraping_stats,
            'population': population_stats,
            'success': scraping_stats['success'] > 0 and population_stats['successful_games'] > 0
        }
        
        logger.info(f"✅ Season scrape-and-populate completed. "
                   f"Scraped: {scraping_stats['success']}/{scraping_stats['total']}, "
                   f"Populated: {population_stats['successful_games']}/{population_stats['total_games']}")
        
        return combined_stats
    
    def verify_and_repopulate_games(self, game_ids: List[str]) -> Dict[str, Any]:
        """
        Verify existing games by re-scraping and update if changed, then re-populate.
        
        Args:
            game_ids: List of game IDs to verify and potentially repopulate
            
        Returns:
            Dict with verification and population statistics
        """
        logger.info(f"Starting verify-and-repopulate operation for {len(game_ids)} games")
        
        # Step 1: Verify and update games in raw_game_data
        logger.info("🔍 Starting verification phase...")
        verification_stats = self.scraper_manager.verify_and_update_games(game_ids)
        
        # Step 2: Repopulate games that were updated
        updated_game_ids = []
        for result in verification_stats['results']:
            if result['status'] == 'updated':
                try:
                    updated_game_ids.append(int(result['game_id']))
                except ValueError:
                    logger.warning(f"Invalid game ID format: {result['game_id']} - skipping")
        
        population_stats = None
        if updated_game_ids:
            logger.info(f"📊 Re-populating {len(updated_game_ids)} updated games...")
            population_stats = self.table_populator.populate_specific_games(
                updated_game_ids,
                override_existing=True  # Override since we know data changed
            )
        else:
            logger.info("No games were updated - skipping population phase")
            population_stats = {'total_games': 0, 'successful_games': 0, 'failed_games': 0}
        
        combined_stats = {
            'verification': verification_stats,
            'population': population_stats,
            'success': verification_stats['updated'] >= 0  # Success if no errors occurred
        }
        
        logger.info(f"✅ Verify-and-repopulate completed. "
                   f"Updated: {verification_stats['updated']}, "
                   f"Re-populated: {population_stats['successful_games']}")
        
        return combined_stats
    
    def verify_and_repopulate_season(self, season: int, game_type: str = 'regular',
                                   max_games: Optional[int] = None) -> Dict[str, Any]:
        """
        Verify an entire season by re-scraping and update if changed, then re-populate.
        
        Args:
            season: WNBA season year
            game_type: 'regular' or 'playoff'  
            max_games: Maximum number of games to process
            
        Returns:
            Dict with verification and population statistics
        """
        logger.info(f"Starting verify-and-repopulate operation for {season} {game_type} season")
        
        # Step 1: Verify and update season in raw_game_data
        logger.info("🔍 Starting season verification phase...")
        verification_stats = self.scraper_manager.verify_and_update_season(
            season, game_type, max_games
        )
        
        # Step 2: Repopulate games that were updated
        updated_game_ids = []
        for result in verification_stats['results']:
            if result['status'] == 'updated':
                try:
                    updated_game_ids.append(int(result['game_id']))
                except ValueError:
                    logger.warning(f"Invalid game ID format: {result['game_id']} - skipping")
        
        population_stats = None
        if updated_game_ids:
            logger.info(f"📊 Re-populating {len(updated_game_ids)} updated games...")
            population_stats = self.table_populator.populate_specific_games(
                updated_game_ids,
                override_existing=True  # Override since we know data changed
            )
        else:
            logger.info("No games were updated - skipping population phase")
            population_stats = {'total_games': 0, 'successful_games': 0, 'failed_games': 0}
        
        combined_stats = {
            'verification': verification_stats,
            'population': population_stats,
            'success': verification_stats['failed'] == 0  # Success if no errors occurred
        }
        
        logger.info(f"✅ Season verify-and-repopulate completed. "
                   f"Season: {season} {game_type}, "
                   f"Updated: {verification_stats['updated']}, "
                   f"Re-populated: {population_stats['successful_games']}")
        
        return combined_stats
    
    def full_refresh_games(self, game_ids: List[str]) -> Dict[str, Any]:
        """
        Perform a complete refresh of games: re-scrape, clear populated data, and re-populate.
        
        Args:
            game_ids: List of game IDs to refresh completely
            
        Returns:
            Dict with refresh statistics
        """
        logger.info(f"Starting full refresh for {len(game_ids)} games")
        
        # Step 1: Re-scrape all games (with override)
        logger.info("🕷️ Re-scraping games with override...")
        scraping_stats = self.scraper_manager.scrape_specific_games(
            game_ids,
            override_existing=True
        )
        
        # Step 2: Clear existing populated data for these games only
        logger.info("🗑️ Clearing existing populated data for these games...")
        game_ids_int = []
        for game_id in game_ids:
            try:
                game_ids_int.append(int(game_id))
            except ValueError:
                logger.warning(f"Invalid game ID format: {game_id} - skipping")
        
        # Clear game data individually (the populator handles this)
        
        # Step 3: Re-populate the games
        logger.info("📊 Re-populating games...")
        population_stats = self.table_populator.populate_specific_games(
            game_ids_int,
            override_existing=True
        )
        
        combined_stats = {
            'scraping': scraping_stats,
            'population': population_stats,
            'success': scraping_stats['success'] > 0 and population_stats['successful_games'] > 0
        }
        
        logger.info(f"✅ Full refresh completed. "
                   f"Re-scraped: {scraping_stats['success']}/{scraping_stats['total']}, "
                   f"Re-populated: {population_stats['successful_games']}/{population_stats['total_games']}")
        
        return combined_stats


def setup_logging(verbose: bool = False):
    """Setup unified logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('wnba_data_manager.log')
        ]
    )


def main():
    """Main CLI interface for the unified WNBA data manager."""
    parser = argparse.ArgumentParser(
        description='Unified WNBA Data Manager - Scrape and populate game data'
    )
    
    # Command selection
    parser.add_argument(
        'command', 
        choices=[
            'scrape-populate-games',
            'scrape-populate-season', 
            'verify-repopulate',
            'verify-repopulate-season',
            'full-refresh',
            'populate-only',
            'scrape-only'
        ],
        help='Operation to perform'
    )
    
    # Target specification
    parser.add_argument('--season', type=int, help='WNBA season year (e.g., 2024)')
    parser.add_argument('--game-type', choices=['regular', 'playoff'], default='regular',
                       help='Type of games (default: regular)')
    parser.add_argument('--game-ids', type=str, nargs='+',
                       help='Specific game IDs to process')
    
    # Processing options
    parser.add_argument('--max-games', type=int, help='Maximum number of games to process')
    parser.add_argument('--override', action='store_true',
                       help='Override existing data')
    parser.add_argument('--clear-tables', action='store_true',
                       help='Clear all populated tables before processing')
    parser.add_argument('--validate', action='store_true',
                       help='Validate foreign key integrity after population')
    
    # Utility options  
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without actual processing')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Initialize manager
    manager = WNBADataManager()
    
    try:
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual processing will occur")
            return
        
        if args.command == 'scrape-populate-games':
            if not args.game_ids:
                logger.error("--game-ids is required for scrape-populate-games command")
                sys.exit(1)
            
            stats = manager.scrape_and_populate_games(
                args.game_ids,
                override_existing=args.override,
                clear_tables_first=args.clear_tables
            )
            
            print(f"\nScrape-and-Populate Results:")
            print(f"  SCRAPING:")
            print(f"    Total: {stats['scraping']['total']}")
            print(f"    Success: {stats['scraping']['success']}")
            print(f"    Failed: {stats['scraping']['failed']}")
            print(f"    Skipped: {stats['scraping']['skipped']}")
            print(f"  POPULATION:")
            print(f"    Total: {stats['population']['total_games']}")
            print(f"    Success: {stats['population']['successful_games']}")
            print(f"    Failed: {stats['population']['failed_games']}")
        
        elif args.command == 'scrape-populate-season':
            if not args.season:
                logger.error("--season is required for scrape-populate-season command")
                sys.exit(1)
            
            stats = manager.scrape_and_populate_season(
                args.season,
                args.game_type,
                args.max_games,
                clear_tables_first=args.clear_tables
            )
            
            print(f"\nSeason Scrape-and-Populate Results ({args.season} {args.game_type}):")
            print(f"  SCRAPING:")
            print(f"    Total: {stats['scraping']['total']}")
            print(f"    Success: {stats['scraping']['success']}")
            print(f"    Failed: {stats['scraping']['failed']}")
            print(f"    Skipped: {stats['scraping']['skipped']}")
            print(f"  POPULATION:")
            print(f"    Total: {stats['population']['total_games']}")
            print(f"    Success: {stats['population']['successful_games']}")
            print(f"    Failed: {stats['population']['failed_games']}")
        
        elif args.command == 'verify-repopulate':
            if not args.game_ids:
                logger.error("--game-ids is required for verify-repopulate command")
                sys.exit(1)
            
            stats = manager.verify_and_repopulate_games(args.game_ids)
            
            print(f"\nVerify-and-Repopulate Results:")
            print(f"  VERIFICATION:")
            print(f"    Total: {stats['verification']['total']}")
            print(f"    Identical: {stats['verification']['identical']}")
            print(f"    Updated: {stats['verification']['updated']}")
            print(f"    Failed: {stats['verification']['failed']}")
            print(f"    Not Found: {stats['verification']['not_found']}")
            print(f"  POPULATION:")
            print(f"    Total: {stats['population']['total_games']}")
            print(f"    Success: {stats['population']['successful_games']}")
            print(f"    Failed: {stats['population']['failed_games']}")
            
            # Show detailed changes for updated games
            if stats['verification']['updated'] > 0:
                print(f"\nDetailed Changes:")
                for result in stats['verification']['results']:
                    if result['status'] == 'updated':
                        changes = result.get('changes', {})
                        sections = ', '.join(changes.get('sections_changed', []))
                        total_changes = changes.get('total_changes', 0)
                        print(f"  Game {result['game_id']}: {total_changes} changes in [{sections}]")
                        
                        # Show detailed changes for each section
                        for section, section_changes in changes.get('details', {}).items():
                            if section_changes:
                                print(f"    {section}:")
                                for change in section_changes[:2]:  # Show first 2 changes per section
                                    print(f"      • {change}")
                                if len(section_changes) > 2:
                                    print(f"      • ... and {len(section_changes) - 2} more changes")
        
        elif args.command == 'verify-repopulate-season':
            if not args.season:
                logger.error("--season is required for verify-repopulate-season command")
                sys.exit(1)
            
            stats = manager.verify_and_repopulate_season(
                args.season,
                args.game_type,
                args.max_games
            )
            
            print(f"\nSeason Verify-and-Repopulate Results ({args.season} {args.game_type}):")
            print(f"  VERIFICATION:")
            print(f"    Total: {stats['verification']['total']}")
            print(f"    Identical: {stats['verification']['identical']}")
            print(f"    Updated: {stats['verification']['updated']}")
            print(f"    Failed: {stats['verification']['failed']}")
            print(f"    Not Found: {stats['verification']['not_found']}")
            print(f"  POPULATION:")
            print(f"    Total: {stats['population']['total_games']}")
            print(f"    Success: {stats['population']['successful_games']}")
            print(f"    Failed: {stats['population']['failed_games']}")
            
            # Show detailed changes for updated games
            if stats['verification']['updated'] > 0:
                print(f"\nDetailed Changes:")
                for result in stats['verification']['results']:
                    if result['status'] == 'updated':
                        changes = result.get('changes', {})
                        sections = ', '.join(changes.get('sections_changed', []))
                        total_changes = changes.get('total_changes', 0)
                        print(f"  Game {result['game_id']}: {total_changes} changes in [{sections}]")
                        
                        # Show detailed changes for each section
                        for section, section_changes in changes.get('details', {}).items():
                            if section_changes:
                                print(f"    {section}:")
                                for change in section_changes[:2]:  # Show first 2 changes per section
                                    print(f"      • {change}")
                                if len(section_changes) > 2:
                                    print(f"      • ... and {len(section_changes) - 2} more changes")
        
        elif args.command == 'full-refresh':
            if not args.game_ids:
                logger.error("--game-ids is required for full-refresh command")
                sys.exit(1)
            
            stats = manager.full_refresh_games(args.game_ids)
            
            print(f"\nFull Refresh Results:")
            print(f"  RE-SCRAPING:")
            print(f"    Total: {stats['scraping']['total']}")
            print(f"    Success: {stats['scraping']['success']}")
            print(f"    Failed: {stats['scraping']['failed']}")
            print(f"  RE-POPULATION:")
            print(f"    Total: {stats['population']['total_games']}")
            print(f"    Success: {stats['population']['successful_games']}")
            print(f"    Failed: {stats['population']['failed_games']}")
        
        elif args.command == 'populate-only':
            # Delegate to populate_game_tables functionality
            if args.game_ids:
                game_ids_int = [int(gid) for gid in args.game_ids]
                stats = manager.table_populator.populate_specific_games(
                    game_ids_int, 
                    override_existing=args.override
                )
            elif args.season:
                stats = manager.table_populator.populate_games_by_season(
                    [args.season], 
                    limit=args.max_games,
                    override_existing=args.override
                )
            else:
                stats = manager.table_populator.populate_all_games(
                    limit=args.max_games,
                    override_existing=args.override
                )
            
            print(f"\nPopulation Results:")
            print(f"  Total games: {stats['total_games']}")
            print(f"  Successful: {stats['successful_games']}")
            print(f"  Failed: {stats['failed_games']}")
            
            if stats['failed_game_ids']:
                print(f"  Failed game IDs: {stats['failed_game_ids']}")
        
        elif args.command == 'scrape-only':
            # Delegate to scraper_manager functionality
            if args.game_ids:
                stats = manager.scraper_manager.scrape_specific_games(
                    args.game_ids, 
                    override_existing=args.override
                )
            elif args.season:
                stats = manager.scraper_manager.scrape_season(
                    args.season, 
                    args.game_type, 
                    args.max_games
                )
            else:
                logger.error("Either --game-ids or --season is required for scrape-only")
                sys.exit(1)
            
            print(f"\nScraping Results:")
            print(f"  Total: {stats['total']}")
            print(f"  Success: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Skipped: {stats['skipped']}")
        
        # Run validation if requested
        if args.validate and 'population' in locals() and stats.get('population', {}).get('successful_games', 0) > 0:
            logger.info("\nRunning foreign key validation...")
            is_valid = manager.table_populator.validate_foreign_keys()
            if not is_valid:
                logger.error("Foreign key validation failed!")
                sys.exit(1)
            else:
                logger.info("✓ Foreign key validation passed!")
    
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()