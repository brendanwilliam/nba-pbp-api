"""
Build Game URL Queue Script
Main script to discover and populate NBA game URLs for systematic scraping.
"""

import asyncio
import logging
import argparse
from datetime import datetime, date
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
    
    async def build_queue_for_dates(self, dates: List[str], validate: bool = True) -> dict:
        """Build queue for specific dates."""
        logger.info(f"Building queue for specific dates: {dates}")
        
        total_stats = {
            'dates_processed': 0,
            'total_games': 0,
            'total_inserted': 0,
            'total_duplicates': 0,
            'total_errors': 0,
            'validation_stats': None,
            'processed_dates': []
        }
        
        # Parse and validate dates
        parsed_dates = []
        for date_str in dates:
            try:
                # Try different date formats
                if len(date_str) == 10 and '-' in date_str:
                    # Format: YYYY-MM-DD
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                elif len(date_str) == 8:
                    # Format: YYYYMMDD
                    parsed_date = datetime.strptime(date_str, '%Y%m%d').date()
                elif '/' in date_str:
                    # Format: MM/DD/YYYY or M/D/YYYY
                    parsed_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                else:
                    raise ValueError(f"Unsupported date format: {date_str}")
                
                parsed_dates.append(parsed_date)
                logger.info(f"Parsed date: {date_str} -> {parsed_date}")
                
            except ValueError as e:
                logger.error(f"Invalid date format '{date_str}': {e}")
                total_stats['total_errors'] += 1
                continue
        
        if not parsed_dates:
            logger.error("No valid dates to process")
            return total_stats
        
        # Determine season for each date to use appropriate discovery logic
        season_dates = {}
        for parsed_date in parsed_dates:
            season = self._determine_season_for_date(parsed_date)
            if season not in season_dates:
                season_dates[season] = []
            season_dates[season].append(parsed_date)
        
        logger.info(f"Dates grouped by season: {season_dates}")
        
        # Process each season's dates
        for season, season_date_list in season_dates.items():
            logger.info(f"Processing {len(season_date_list)} dates for season {season}")
            
            try:
                # Discover games for the specific dates
                games = await self.generator.discover_games_for_dates(season_date_list, season)
                
                if games:
                    # Populate queue
                    stats = await self.generator.populate_queue(games)
                    
                    # Update totals
                    total_stats['dates_processed'] += len(season_date_list)
                    total_stats['total_games'] += stats['total']
                    total_stats['total_inserted'] += stats['inserted']
                    total_stats['total_duplicates'] += stats['duplicates']
                    total_stats['total_errors'] += stats['errors']
                    total_stats['processed_dates'].extend([d.isoformat() for d in season_date_list])
                    
                    logger.info(f"Season {season} dates completed: {stats}")
                else:
                    logger.warning(f"No games found for season {season} dates: {season_date_list}")
                
            except Exception as e:
                logger.error(f"Error processing season {season} dates: {e}")
                total_stats['total_errors'] += 1
        
        # Validate URLs if requested
        if validate and total_stats['total_inserted'] > 0:
            logger.info("Starting URL validation...")
            validation_stats = await self.validator.validate_queue_urls(
                status_filter='pending',
                limit=total_stats['total_inserted']  # Validate all newly inserted
            )
            total_stats['validation_stats'] = validation_stats
            logger.info(f"Validation completed: {validation_stats}")
        
        return total_stats
    
    def _determine_season_for_date(self, game_date: date) -> str:
        """Determine NBA season for a given date."""
        year = game_date.year
        month = game_date.month
        
        # NBA season typically runs October to June
        # Games from Oct-Dec belong to season starting that year
        # Games from Jan-Jun belong to season that started the previous year
        if month >= 10:  # October, November, December
            season_start_year = year
        else:  # January through September
            season_start_year = year - 1
        
        return f"{season_start_year}-{str(season_start_year + 1)[2:]}"
    
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
    
    async def validate_existing_queue(self, limit: Optional[int] = None, status_filter: str = 'pending') -> dict:
        """Validate existing URLs in the queue."""
        logger.info(f"Validating existing URLs in queue with status '{status_filter}'")
        
        try:
            # Check how many URLs have the requested status
            from sqlalchemy import text
            count_result = self.db_session.execute(
                text("SELECT COUNT(*) FROM game_url_queue WHERE status = :status"),
                {"status": status_filter}
            ).scalar()
            
            if count_result == 0:
                logger.info(f"No URLs with status '{status_filter}' found.")
                
                # If no pending URLs, check for invalid URLs
                if status_filter == 'pending':
                    invalid_count = self.db_session.execute(
                        text("SELECT COUNT(*) FROM game_url_queue WHERE status = 'invalid'")
                    ).scalar()
                    
                    if invalid_count > 0:
                        logger.info(f"Found {invalid_count:,} invalid URLs. Converting some to pending for revalidation...")
                        
                        # Convert some invalid URLs to pending for revalidation
                        convert_limit = limit if limit else min(1000, invalid_count)
                        updated = self.db_session.execute(text("""
                            UPDATE game_url_queue
                            SET status = 'pending'
                            WHERE game_id IN (
                                SELECT game_id 
                                FROM game_url_queue 
                                WHERE status = 'invalid'
                                ORDER BY season DESC, game_date DESC
                                LIMIT :limit
                            )
                        """), {"limit": convert_limit})
                        self.db_session.commit()
                        
                        converted_count = updated.rowcount
                        logger.info(f"Converted {converted_count} invalid URLs to pending for revalidation")
                        
                        if converted_count == 0:
                            return {'total': 0, 'valid': 0, 'invalid': 0, 'errors': 0, 'message': 'No URLs to validate'}
                    else:
                        return {'total': 0, 'valid': 0, 'invalid': 0, 'errors': 0, 'message': 'No URLs to validate'}
            
            # Now validate the URLs
            stats = await self.validator.validate_queue_urls(
                status_filter='pending',  # Always validate pending after conversion
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
    parser.add_argument('--dates', nargs='+', help='Specific dates to process (e.g., 2024-12-25 2024-12-26). Supports YYYY-MM-DD, YYYYMMDD, or MM/DD/YYYY formats')
    parser.add_argument('--validate', action='store_true', help='Validate URLs after generation')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing URLs')
    parser.add_argument('--stats-only', action='store_true', help='Only show queue statistics')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to validate')
    parser.add_argument('--status', default='pending', help='Status of URLs to validate (default: pending, auto-converts invalid to pending)')
    
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
            stats = await builder.validate_existing_queue(limit=args.limit, status_filter=args.status)
            print(f"\n=== VALIDATION RESULTS ===")
            print(f"Status filter: {args.status}")
            print(f"Limit: {args.limit if args.limit else 'No limit'}")
            print(f"Validation stats: {stats}")
            
            # Show current queue status after validation
            current_stats = builder.get_queue_stats()
            print(f"\n=== CURRENT QUEUE STATUS ===")
            print(f"By Status: {current_stats.get('by_status', {})}")
            
        elif args.dates:
            # Process specific dates
            stats = await builder.build_queue_for_dates(args.dates, validate=args.validate)
            print(f"\n=== DATE PROCESSING RESULTS ===")
            print(f"Processing stats: {stats}")
            print(f"Processed dates: {stats.get('processed_dates', [])}")
            
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