"""
Build Game URL Queue Script
Main script to discover and populate NBA game URLs for systematic scraping.
"""

import asyncio
import logging
import argparse
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from ..core.database import get_db
from ..scrapers.game_url_generator import GameURLGenerator
from ..scrapers.url_validator import GameURLValidator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_url_queue.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class GameURLQueueBuilder:
    """Main class for building the game URL queue."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.generator = GameURLGenerator(db_session)
        self.validator = GameURLValidator(db_session)
        
    async def initialize(self):
        """Initialize async components."""
        await self.generator.initialize()
        await self.validator.initialize()
        
    async def close(self):
        """Close async components."""
        await self.generator.close()
        await self.validator.close()
        
    async def build_queue_for_seasons(self, seasons: List[str], validate: bool = True) -> dict:
        """Build queue for specified seasons."""
        logger.info(f"Building queue for seasons: {seasons}")
        
        total_stats = {
            'seasons_processed': 0,
            'total_games': 0,
            'total_inserted': 0,
            'total_duplicates': 0,
            'total_errors': 0,
            'validation_stats': None
        }
        
        # Generate URLs for all seasons
        for season in seasons:
            logger.info(f"Processing season {season}")
            
            try:
                # Discover games for the season
                games = await self.generator.discover_season_games(season)
                
                # Populate queue
                stats = await self.generator.populate_queue(games)
                
                # Update totals
                total_stats['seasons_processed'] += 1
                total_stats['total_games'] += stats['total']
                total_stats['total_inserted'] += stats['inserted']
                total_stats['total_duplicates'] += stats['duplicates']
                total_stats['total_errors'] += stats['errors']
                
                logger.info(f"Season {season} completed: {stats}")
                
            except Exception as e:
                logger.error(f"Error processing season {season}: {e}")
                total_stats['total_errors'] += 1
        
        # Validate URLs if requested
        if validate and total_stats['total_inserted'] > 0:
            logger.info("Starting URL validation...")
            validation_stats = await self.validator.validate_queue_urls(
                status_filter='pending',
                limit=1000  # Validate first 1000 for testing
            )
            total_stats['validation_stats'] = validation_stats
            logger.info(f"Validation completed: {validation_stats}")
        
        return total_stats
    
    async def build_full_queue(self, validate_sample: bool = True) -> dict:
        """Build the complete queue for all seasons 1996-2025."""
        logger.info("Building complete NBA game URL queue (1996-2025)")
        
        # All seasons
        all_seasons = [
            "1996-97", "1997-98", "1998-99", "1999-00", "2000-01",
            "2001-02", "2002-03", "2003-04", "2004-05", "2005-06",
            "2006-07", "2007-08", "2008-09", "2009-10", "2010-11",
            "2011-12", "2012-13", "2013-14", "2014-15", "2015-16",
            "2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
            "2021-22", "2022-23", "2023-24", "2024-25"
        ]
        
        start_time = datetime.now()
        
        try:
            # Build queue (without full validation to save time)
            stats = await self.build_queue_for_seasons(all_seasons, validate=False)
            
            # Validate a sample for quality check
            if validate_sample and stats['total_inserted'] > 0:
                logger.info("Validating sample URLs for quality check...")
                sample_stats = await self.validator.validate_sample(sample_size=50)
                stats['sample_validation'] = sample_stats
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            stats['duration_minutes'] = duration.total_seconds() / 60
            stats['start_time'] = start_time.isoformat()
            stats['end_time'] = end_time.isoformat()
            
            logger.info(f"Queue building completed in {stats['duration_minutes']:.1f} minutes")
            logger.info(f"Final stats: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error building full queue: {e}")
            raise
    
    async def validate_existing_queue(self, limit: Optional[int] = None) -> dict:
        """Validate existing URLs in the queue."""
        logger.info("Validating existing URLs in queue")
        
        try:
            stats = await self.validator.validate_queue_urls(
                status_filter='pending',
                limit=limit
            )
            
            logger.info(f"Validation completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error validating queue: {e}")
            raise
    
    def get_queue_stats(self) -> dict:
        """Get current queue statistics."""
        from sqlalchemy import text
        
        stats = {}
        
        try:
            # Total count by status
            result = self.db_session.execute(text("""
                SELECT status, COUNT(*) as count
                FROM game_url_queue
                GROUP BY status
                ORDER BY status
            """))
            
            stats['by_status'] = {row.status: row.count for row in result.fetchall()}
            
            # Count by season
            result = self.db_session.execute(text("""
                SELECT season, COUNT(*) as count
                FROM game_url_queue
                GROUP BY season
                ORDER BY season
            """))
            
            stats['by_season'] = {row.season: row.count for row in result.fetchall()}
            
            # Count by game type
            result = self.db_session.execute(text("""
                SELECT game_type, COUNT(*) as count
                FROM game_url_queue
                GROUP BY game_type
                ORDER BY game_type
            """))
            
            stats['by_game_type'] = {row.game_type: row.count for row in result.fetchall()}
            
            # Overall stats
            result = self.db_session.execute(text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN url_validated = true THEN 1 END) as validated_games,
                    MIN(game_date) as earliest_game,
                    MAX(game_date) as latest_game
                FROM game_url_queue
            """))
            
            row = result.fetchone()
            stats['overall'] = {
                'total_games': row.total_games,
                'validated_games': row.validated_games,
                'earliest_game': row.earliest_game.isoformat() if row.earliest_game else None,
                'latest_game': row.latest_game.isoformat() if row.latest_game else None
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {'error': str(e)}


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Build NBA Game URL Queue')
    parser.add_argument('--seasons', nargs='+', help='Specific seasons to process (e.g., 2023-24 2024-25)')
    parser.add_argument('--validate', action='store_true', help='Validate URLs after generation')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing URLs')
    parser.add_argument('--stats-only', action='store_true', help='Only show queue statistics')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to validate')
    
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    
    # Create queue builder
    builder = GameURLQueueBuilder(db)
    
    try:
        await builder.initialize()
        
        if args.stats_only:
            # Just show statistics
            stats = builder.get_queue_stats()
            print("\n=== QUEUE STATISTICS ===")
            print(f"Overall: {stats.get('overall', {})}")
            print(f"By Status: {stats.get('by_status', {})}")
            print(f"By Season: {stats.get('by_season', {})}")
            print(f"By Game Type: {stats.get('by_game_type', {})}")
            
        elif args.validate_only:
            # Only validate existing URLs
            stats = await builder.validate_existing_queue(limit=args.limit)
            print(f"\n=== VALIDATION RESULTS ===")
            print(f"Validation stats: {stats}")
            
        elif args.seasons:
            # Process specific seasons
            stats = await builder.build_queue_for_seasons(args.seasons, validate=args.validate)
            print(f"\n=== GENERATION RESULTS ===")
            print(f"Processing stats: {stats}")
            
        else:
            # Build full queue
            stats = await builder.build_full_queue(validate_sample=True)
            print(f"\n=== FULL QUEUE BUILD RESULTS ===")
            print(f"Final stats: {stats}")
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Process failed: {e}")
        raise
    finally:
        await builder.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())