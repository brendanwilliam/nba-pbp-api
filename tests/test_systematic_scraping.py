"""
Test script for systematic scraping system
Tests with a small batch before full execution
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from scrapers.systematic_scraper import SystematicScraper
from scrapers.game_discovery import GameDiscovery
from database.queue_manager import QueueManager, GameQueueItem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_game_discovery():
    """Test game discovery for a specific date"""
    logger.info("Testing game discovery...")
    
    discovery = GameDiscovery()
    await discovery.initialize()
    
    try:
        # Test with a known date that has games
        test_date = datetime(2024, 12, 25)  # Christmas Day - always has games
        games = await discovery._discover_games_for_date(test_date, "2024-25")
        
        logger.info(f"Found {len(games)} games on {test_date.date()}")
        
        for game in games[:3]:  # Show first 3
            logger.info(f"  {game.away_team} @ {game.home_team} - {game.game_url}")
            
        return len(games) > 0
        
    finally:
        await discovery.close()


async def test_queue_operations():
    """Test queue management operations"""
    logger.info("Testing queue operations...")
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/nba_pbp')
    queue_manager = QueueManager(db_url)
    
    try:
        await queue_manager.initialize()
        
        # Create test games
        test_games = [
            GameQueueItem(
                game_id="test_001",
                season="2024-25",
                game_date=datetime(2024, 12, 25),
                home_team="LAL",
                away_team="GSW",
                game_url="https://www.nba.com/game/gsw-vs-lal-test001"
            ),
            GameQueueItem(
                game_id="test_002", 
                season="2024-25",
                game_date=datetime(2024, 12, 25),
                home_team="BOS",
                away_team="MIA",
                game_url="https://www.nba.com/game/mia-vs-bos-test002"
            )
        ]
        
        # Add to queue
        added = await queue_manager.add_games_to_queue(test_games)
        logger.info(f"Added {added} test games to queue")
        
        # Get queue stats
        stats = await queue_manager.get_queue_stats()
        logger.info(f"Queue stats: {stats}")
        
        # Get next games
        next_games = await queue_manager.get_next_games(2)
        logger.info(f"Got {len(next_games)} games from queue")
        
        # Clean up test data
        import asyncpg
        conn = await asyncpg.connect(db_url)
        await conn.execute("DELETE FROM scraping_queue WHERE game_id LIKE 'test_%'")
        await conn.close()
        
        logger.info("Queue operations test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Queue test failed: {e}")
        return False
        
    finally:
        await queue_manager.close()


async def test_small_batch_scraping():
    """Test scraping with a very small batch"""
    logger.info("Testing small batch scraping...")
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/nba_pbp')
    scraper = SystematicScraper(db_url, rate_limit=2.0)  # Faster for testing
    
    try:
        await scraper.initialize()
        
        # Populate queue with just a few games from recent date
        test_date = datetime(2024, 12, 25)
        discovery = GameDiscovery()
        await discovery.initialize()
        
        games = await discovery._discover_games_for_date(test_date, "2024-25")
        
        if games:
            # Limit to first 2 games for testing
            test_games = games[:2]
            
            queue_items = [
                GameQueueItem(
                    game_id=game.game_id,
                    season=game.season,
                    game_date=game.game_date,
                    home_team=game.home_team,
                    away_team=game.away_team,
                    game_url=game.game_url
                )
                for game in test_games
            ]
            
            # Add to queue
            added = await scraper.queue_manager.add_games_to_queue(queue_items)
            logger.info(f"Added {added} games for testing")
            
            # Process the batch
            results = await scraper.process_queue_batch(batch_size=5)
            logger.info(f"Batch results: {results}")
            
            # Get final stats
            stats = await scraper.queue_manager.get_queue_stats()
            logger.info(f"Final stats: {stats}")
            
            success = results['success'] > 0 or results['invalid'] > 0
            logger.info(f"Small batch test {'PASSED' if success else 'FAILED'}")
            return success
            
        else:
            logger.warning("No games found for test date")
            return False
            
        await discovery.close()
        
    except Exception as e:
        logger.error(f"Small batch test failed: {e}")
        return False
        
    finally:
        await scraper.close()


async def main():
    """Run all tests"""
    load_dotenv()
    
    logger.info("Starting systematic scraping tests...")
    
    # Initialize database first
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/nba_pbp')
    
    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'database', 'queue_schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        await conn.execute(schema_sql)
        await conn.close()
        
        logger.info("Database schema initialized")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return
    
    # Run tests
    tests = [
        ("Game Discovery", test_game_discovery),
        ("Queue Operations", test_queue_operations), 
        ("Small Batch Scraping", test_small_batch_scraping)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results[test_name] = result
            logger.info(f"{test_name}: {'PASS' if result else 'FAIL'}")
            
        except Exception as e:
            logger.error(f"{test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System ready for systematic scraping.")
    else:
        logger.warning("⚠️  Some tests failed. Please fix issues before running full scraping.")


if __name__ == "__main__":
    asyncio.run(main())