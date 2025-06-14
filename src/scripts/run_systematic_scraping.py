"""
Main script to run systematic NBA game scraping
Scrapes all games from 1996-97 to 2024-25
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from scrapers.systematic_scraper import SystematicScraper
from database.queue_manager import QueueManager
from scripts.monitor_progress import ScrapingMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scraping_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def initialize_database(db_url: str):
    """Initialize database schema"""
    import asyncpg
    
    logger.info("Initializing database schema...")
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'queue_schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        await conn.execute(schema_sql)
        logger.info("Database schema initialized successfully")
        
    finally:
        await conn.close()


async def main():
    """Main execution function"""
    load_dotenv()
    
    # Configuration
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/nba_pbp')
    rate_limit = float(os.getenv('SCRAPING_RATE_LIMIT', '1.0'))  # requests per second
    batch_size = int(os.getenv('BATCH_SIZE', '20'))
    max_workers = int(os.getenv('MAX_WORKERS', '3'))
    start_season = os.getenv('START_SEASON', '1996-97')
    
    logger.info(f"Starting systematic NBA scraping")
    logger.info(f"Database: {db_url}")
    logger.info(f"Rate limit: {rate_limit} req/s")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Workers: {max_workers}")
    logger.info(f"Starting from season: {start_season}")
    
    # Initialize database
    await initialize_database(db_url)
    
    # Create scraper
    scraper = SystematicScraper(db_url, rate_limit=rate_limit)
    
    try:
        await scraper.initialize()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == 'populate':
                # Just populate the queue for a specific season
                season = sys.argv[2] if len(sys.argv) > 2 else start_season
                logger.info(f"Populating queue for season {season}")
                count = await scraper.populate_queue_for_season(season)
                logger.info(f"Added {count} games to queue")
                
            elif command == 'monitor':
                # Run monitoring dashboard
                monitor = ScrapingMonitor(db_url)
                await monitor.initialize()
                await monitor.display_live_dashboard()
                
            elif command == 'report':
                # Generate report
                monitor = ScrapingMonitor(db_url)
                await monitor.initialize()
                await monitor.generate_report()
                
            elif command == 'reset':
                # Reset stale games
                queue_manager = QueueManager(db_url)
                await queue_manager.initialize()
                await queue_manager.reset_stale_games()
                await queue_manager.close()
                
            else:
                logger.error(f"Unknown command: {command}")
                print("Usage: python run_systematic_scraping.py [populate|monitor|report|reset|scrape]")
                
        else:
            # Default: run full scraping
            logger.info("Starting full systematic scraping")
            
            # Ask for confirmation
            print("\n" + "="*60)
            print("SYSTEMATIC NBA SCRAPING")
            print("="*60)
            print(f"This will scrape approximately 30,000 NBA games")
            print(f"Starting from season: {start_season}")
            print(f"Estimated time: Several days to weeks")
            print("="*60)
            
            response = input("\nDo you want to continue? (yes/no): ")
            
            if response.lower() == 'yes':
                await scraper.scrape_all_seasons(start_season=start_season)
            else:
                logger.info("Scraping cancelled by user")
                
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        
    finally:
        await scraper.close()
        logger.info("Scraping session ended")


if __name__ == "__main__":
    asyncio.run(main())