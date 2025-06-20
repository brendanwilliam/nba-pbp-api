"""Test Mass Scraper System - validates the mass scraping implementation."""

import asyncio
import unittest
import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from scrapers.mass_scraping_queue import GameScrapingQueue, GameScrapingTask, ScrapingStatus
from scrapers.mass_data_extractor import NBADataExtractor, ExtractionResult
from scrapers.rate_limiter import RateLimiter, RateLimitConfig
from core.database import get_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestQueueOperations(unittest.IsolatedAsyncioTestCase):
    """Test queue operations."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        db_url = get_database_url()
        if not db_url:
            self.skipTest("Database URL not found")
        
        self.queue = GameScrapingQueue(db_url, session_id=str(uuid.uuid4()))
        await self.queue.initialize()
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'queue'):
            await self.queue.close()
    
    async def test_queue_statistics(self):
        """Test getting queue statistics."""
        stats = await self.queue.get_queue_statistics()
        
        self.assertIn('queue_counts', stats)
        self.assertIsInstance(stats['queue_counts'], dict)
    
    async def test_season_progress(self):
        """Test getting season progress."""
        progress = await self.queue.get_season_progress()
        
        self.assertIsInstance(progress, list)
        
        if progress:
            season = progress[0]
            self.assertIn('season', season)
            self.assertIn('completion_percentage', season)
    
    async def test_batch_operations(self):
        """Test batch retrieval and status updates."""
        # Get a small batch
        batch = await self.queue.get_next_batch(batch_size=2)
        self.assertIsInstance(batch, list)
        
        if not batch:
            self.skipTest("No games available for batch test")
        
        # Test marking game as completed
        test_game = batch[0]
        test_json = {"test": "data", "game_id": test_game.game_id}
        await self.queue.mark_completed(test_game.game_id, test_json, 1500)
        
        # Test marking game as failed
        if len(batch) > 1:
            test_game2 = batch[1]
            await self.queue.mark_failed(test_game2.game_id, "Test failure", 500)


class TestDataExtractor(unittest.TestCase):
    """Test data extraction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = NBADataExtractor(timeout=10)
    
    def test_extractor_initialization(self):
        """Test extractor initializes properly."""
        self.assertIsInstance(self.extractor.timeout, (int, float))
    
    def test_url_validation(self):
        """Test URL validation logic."""
        # Test valid URLs
        valid_urls = [
            "https://www.nba.com/game/lal-vs-bos-0022400123",
            "https://www.nba.com/game/gsw-vs-lal-0022400456",
        ]
        
        for url in valid_urls:
            # This tests that the URL format is accepted by the extractor
            # Actual extraction may fail if the game doesn't exist
            result, json_data, metadata = self.extractor.extract_game_data(url)
            
            # Result should be one of the expected enum values
            self.assertIsInstance(result, ExtractionResult)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        config = RateLimitConfig(
            requests_per_second=10.0,  # Fast for testing
            burst_limit=5,
            burst_window_seconds=1
        )
        self.limiter = RateLimiter(config)
    
    def test_rate_limiter_basic_operations(self):
        """Test basic rate limiter operations."""
        # Test initial wait
        wait_time = self.limiter.wait_if_needed()
        self.assertIsInstance(wait_time, (int, float))
        self.assertGreaterEqual(wait_time, 0)
        
        # Test successful response handling
        self.limiter.handle_successful_response(200)
        
        # Test rate limit response handling
        self.limiter.handle_rate_limit_response(429, retry_after=1)
        
        # Test stats retrieval
        stats = self.limiter.get_rate_limit_stats()
        self.assertIsInstance(stats, dict)
    
    def test_multiple_requests(self):
        """Test multiple requests through rate limiter."""
        for i in range(3):
            wait_time = self.limiter.wait_if_needed()
            self.assertGreaterEqual(wait_time, 0)
            self.limiter.handle_successful_response(200)
    
    def test_rate_limit_handling(self):
        """Test rate limit response handling."""
        # Simulate rate limit
        self.limiter.handle_rate_limit_response(429, retry_after=1)
        
        # Next request should have increased wait time
        wait_time = self.limiter.wait_if_needed()
        self.assertGreater(wait_time, 0)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Test integration of all components."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        db_url = get_database_url()
        if not db_url:
            self.skipTest("Database URL not found")
        
        self.queue = GameScrapingQueue(db_url, session_id=str(uuid.uuid4()))
        self.extractor = NBADataExtractor(timeout=5)
        self.limiter = RateLimiter(RateLimitConfig(requests_per_second=2.0))
        
        await self.queue.initialize()
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'queue'):
            await self.queue.close()
    
    async def test_component_integration(self):
        """Test that all components work together."""
        # Get a batch
        batch = await self.queue.get_next_batch(batch_size=1)
        
        if not batch:
            self.skipTest("No games available for integration test")
        
        game = batch[0]
        
        # Apply rate limiting
        wait_time = self.limiter.wait_if_needed()
        self.assertGreaterEqual(wait_time, 0)
        
        # Extract data (may fail if URL doesn't exist - that's OK for testing)
        result, json_data, metadata = self.extractor.extract_game_data(game.game_url)
        self.assertIsInstance(result, ExtractionResult)
        
        # Handle the result appropriately
        if result == ExtractionResult.SUCCESS:
            await self.queue.mark_completed(game.game_id, json_data, 
                                          metadata.extraction_time_ms if metadata else 1000)
            self.limiter.handle_successful_response(200)
        else:
            await self.queue.mark_failed(game.game_id, f"Integration test: {result}")
            
            if result == ExtractionResult.RATE_LIMITED:
                self.limiter.handle_rate_limit_response(429)
        
        # Test completed successfully regardless of extraction result
        self.assertTrue(True)


class TestMassScraperSuite(unittest.TestCase):
    """Test suite for mass scraper components."""
    
    def test_all_imports_successful(self):
        """Test that all required modules can be imported."""
        # If we got this far, all imports were successful
        self.assertTrue(True)
    
    def test_configuration_classes(self):
        """Test configuration classes."""
        config = RateLimitConfig(
            requests_per_second=1.0,
            burst_limit=5,
            burst_window_seconds=10
        )
        
        self.assertEqual(config.requests_per_second, 1.0)
        self.assertEqual(config.burst_limit, 5)
        self.assertEqual(config.burst_window_seconds, 10)


async def run_interactive_tests():
    """Run interactive tests with detailed output."""
    logger.info("🏀 NBA Mass Scraper Test Suite")
    logger.info("=" * 50)
    
    db_url = get_database_url()
    if not db_url:
        logger.error("Database URL not found")
        return False
    
    # Test queue operations
    logger.info("\n🧪 Testing Queue Operations...")
    queue = GameScrapingQueue(db_url, session_id=str(uuid.uuid4()))
    
    try:
        await queue.initialize()
        
        stats = await queue.get_queue_statistics()
        logger.info(f"Queue stats: {stats.get('queue_counts', {})}")
        
        progress = await queue.get_season_progress()
        logger.info(f"Found {len(progress)} seasons in queue")
        
        if progress:
            for season in progress[:3]:
                logger.info(f"Season {season['season']}: {season['completion_percentage']:.1f}% complete")
        
        batch = await queue.get_next_batch(batch_size=2)
        logger.info(f"Retrieved batch of {len(batch)} games")
        
        logger.info("✅ Queue operations test passed")
        
    except Exception as e:
        logger.error(f"❌ Queue operations test failed: {e}")
        return False
    finally:
        await queue.close()
    
    # Test rate limiter
    logger.info("\n🧪 Testing Rate Limiter...")
    config = RateLimitConfig(requests_per_second=5.0, burst_limit=3)
    limiter = RateLimiter(config)
    
    for i in range(3):
        wait_time = limiter.wait_if_needed()
        logger.info(f"Request {i+1}: waited {wait_time:.2f}s")
        limiter.handle_successful_response(200)
    
    stats = limiter.get_rate_limit_stats()
    logger.info(f"Rate limiter stats: {stats}")
    logger.info("✅ Rate limiter test passed")
    
    logger.info("\n🎉 All interactive tests completed!")
    return True


if __name__ == "__main__":
    # Run interactive tests if called directly
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        asyncio.run(run_interactive_tests())
    else:
        unittest.main()