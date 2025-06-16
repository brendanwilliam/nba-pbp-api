#!/usr/bin/env python3
"""
Standalone script to build the complete NBA game URL queue.
"""

import sys
import os
import asyncio
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import everything we need
from core.database import get_db
from scrapers.game_url_generator import GameURLGenerator
from scrapers.url_validator import GameURLValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_queue_build.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def build_full_queue():
    """Build the complete queue for all seasons."""
    logger.info("Starting full NBA game URL queue build (1996-2025)")
    
    # All seasons
    all_seasons = [
        "1996-97", "1997-98", "1998-99", "1999-00", "2000-01",
        "2001-02", "2002-03", "2003-04", "2004-05", "2005-06",
        "2006-07", "2007-08", "2008-09", "2009-10", "2010-11",
        "2011-12", "2012-13", "2013-14", "2014-15", "2015-16",
        "2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
        "2021-22", "2022-23", "2023-24", "2024-25"
    ]
    
    db = next(get_db())
    generator = GameURLGenerator(db)
    
    try:
        await generator.initialize()
        
        total_stats = {
            'seasons_processed': 0,
            'total_games': 0,
            'total_inserted': 0,
            'total_duplicates': 0,
            'total_errors': 0
        }
        
        for season in all_seasons:
            logger.info(f"Processing season {season}")
            
            try:
                # Discover games for the season
                games = await generator.discover_season_games(season)
                logger.info(f"Found {len(games)} games for {season}")
                
                # Populate queue
                if games:
                    stats = await generator.populate_queue(games)
                    logger.info(f"Season {season} stats: {stats}")
                    
                    # Update totals
                    total_stats['seasons_processed'] += 1
                    total_stats['total_games'] += stats['total']
                    total_stats['total_inserted'] += stats['inserted']
                    total_stats['total_duplicates'] += stats['duplicates']
                    total_stats['total_errors'] += stats['errors']
                else:
                    logger.warning(f"No games found for season {season}")
                
            except Exception as e:
                logger.error(f"Error processing season {season}: {e}")
                total_stats['total_errors'] += 1
        
        logger.info(f"Final stats: {total_stats}")
        return total_stats
        
    finally:
        await generator.close()
        db.close()

if __name__ == "__main__":
    asyncio.run(build_full_queue())