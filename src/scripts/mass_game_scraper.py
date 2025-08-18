#!/usr/bin/env python3
"""
Mass WNBA Game Scraper - Main orchestration script
Implements the systematic scraping system for WNBA data
"""

import asyncio
import logging
import sys
import os
import time
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scrapers.mass_scraping_queue import GameScrapingQueue, GameScrapingTask, ScrapingResult
from scrapers.mass_data_extractor import NBADataExtractor, ExtractionResult
from scrapers.rate_limiter import RateLimiter, RateLimitConfig, GlobalRateLimiter
from core.database import get_database_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mass_scraping.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MassGameScraper:
    """Main orchestrator for mass NBA game scraping"""
    
    def __init__(self, 
                 db_url: str,
                 batch_size: int = 100,
                 max_workers: int = 4,
                 rate_limit_rps: float = 0.5):
        
        self.db_url = db_url
        self.batch_size = batch_size
        self.max_workers = max_workers
        
        # Initialize components
        self.queue_manager = GameScrapingQueue(db_url)
        
        # Configure rate limiter
        rate_config = RateLimitConfig(
            requests_per_second=rate_limit_rps,
            burst_limit=3,
            burst_window_seconds=10
        )
        self.rate_limiter = GlobalRateLimiter(rate_config)
        
        # Create data extractors for each worker
        self.extractors = [
            NBADataExtractor(timeout=30, user_agent_index=i) 
            for i in range(max_workers)
        ]
        
        # Control flags
        self.should_stop = False
        self.paused = False
        
        # Statistics
        self.session_stats = {
            'started_at': None,
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'invalid': 0,
            'rate_limited': 0,
            'avg_response_time': 0.0
        }
        
    async def initialize(self):
        """Initialize the scraper components"""
        logger.info("Initializing mass game scraper...")
        await self.queue_manager.initialize()
        
        # Reset any stale games
        stale_count = await self.queue_manager.reset_stale_games(timeout_minutes=30)
        if stale_count > 0:
            logger.info(f"Reset {stale_count} stale games to pending")
            
        self.session_stats['started_at'] = datetime.now()
        logger.info("Mass game scraper initialized successfully")
        
    async def close(self):
        """Close the scraper and cleanup resources"""
        logger.info("Closing mass game scraper...")
        await self.queue_manager.close()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.should_stop = True
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    async def run_scraping_session(self, 
                                 max_batches: Optional[int] = None,
                                 season_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a complete scraping session
        
        Args:
            max_batches: Maximum number of batches to process (None for unlimited)
            season_filter: Only process games from this season (e.g., "2023-24")
        """
        logger.info(f"Starting scraping session (max_batches={max_batches}, "
                   f"season_filter={season_filter})")
        
        batch_count = 0
        
        while not self.should_stop:
            # Check if we've hit the batch limit
            if max_batches and batch_count >= max_batches:
                logger.info(f"Reached maximum batch limit ({max_batches})")
                break
                
            # Get next batch of games
            games = await self.queue_manager.get_next_batch(self.batch_size)
            
            if not games:
                logger.info("No more games to process")
                break
                
            # Filter by season if specified
            if season_filter:
                games = [g for g in games if g.season == season_filter]
                if not games:
                    logger.info(f"No games found for season {season_filter} in this batch")
                    continue
            
            logger.info(f"Processing batch {batch_count + 1} with {len(games)} games")
            
            # Process the batch
            batch_results = await self._process_batch(games)
            
            # Update statistics
            self._update_session_stats(batch_results)
            
            # Log progress
            await self._log_progress()
            
            batch_count += 1
            
            # Brief pause between batches
            if not self.should_stop:
                await asyncio.sleep(2)
        
        # Final statistics
        final_stats = await self._get_final_stats()
        logger.info(f"Scraping session completed: {final_stats}")
        
        return final_stats
        
    async def _process_batch(self, games: List[GameScrapingTask]) -> List[ScrapingResult]:
        """Process a batch of games with concurrent workers"""
        logger.info(f"Processing batch of {len(games)} games")
        
        # Create thread pool for concurrent scraping
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all games to thread pool
            future_to_game = {}
            
            for i, game in enumerate(games):
                extractor = self.extractors[i % len(self.extractors)]
                future = executor.submit(self._scrape_single_game, game, extractor)
                future_to_game[future] = game
            
            # Collect results as they complete
            results = []
            for future in as_completed(future_to_game):
                if self.should_stop:
                    logger.info("Stopping batch processing due to shutdown signal")
                    break
                    
                game = future_to_game[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update queue based on result
                    await self._update_queue_from_result(result)
                    
                except Exception as e:
                    logger.error(f"Error processing game {game.game_id}: {e}")
                    # Mark as failed in queue
                    await self.queue_manager.mark_failed(
                        game.game_id, 
                        f"Processing error: {str(e)}"
                    )
        
        return results
        
    def _scrape_single_game(self, game: GameScrapingTask, extractor: NBADataExtractor) -> ScrapingResult:
        """Scrape a single game (runs in thread pool)"""
        logger.debug(f"Scraping game {game.game_id}: {game.game_url}")
        
        # Apply rate limiting
        wait_time = self.rate_limiter.wait_if_needed()
        
        # Extract data
        start_time = time.time()
        result_status, json_data, metadata = extractor.extract_game_data(game.game_url)
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Handle rate limiting
        if result_status == ExtractionResult.RATE_LIMITED:
            self.rate_limiter.handle_rate_limit_response(429)
            # Rotate user agent for this extractor
            extractor.rotate_user_agent()
            
            return ScrapingResult(
                game_id=game.game_id,
                success=False,
                error_message="Rate limited",
                error_code=429,
                response_time_ms=response_time_ms
            )
        elif result_status == ExtractionResult.SUCCESS:
            self.rate_limiter.handle_successful_response(200)
            
            return ScrapingResult(
                game_id=game.game_id,
                success=True,
                raw_json=json_data,
                response_time_ms=response_time_ms,
                json_size_bytes=metadata.json_size_bytes if metadata else None
            )
        else:
            # Handle other errors
            error_codes = {
                ExtractionResult.NO_DATA: 404,
                ExtractionResult.INVALID_JSON: 422,
                ExtractionResult.NETWORK_ERROR: 500,
                ExtractionResult.TIMEOUT: 408,
                ExtractionResult.SERVER_ERROR: 500
            }
            
            error_code = error_codes.get(result_status, 500)
            
            return ScrapingResult(
                game_id=game.game_id,
                success=False,
                error_message=result_status.value,
                error_code=error_code,
                response_time_ms=response_time_ms
            )
            
    async def _update_queue_from_result(self, result: ScrapingResult):
        """Update the queue based on scraping result"""
        if result.success:
            await self.queue_manager.mark_completed(
                result.game_id,
                result.raw_json,
                result.response_time_ms
            )
        elif result.error_code == 404:
            await self.queue_manager.mark_invalid(
                result.game_id,
                result.error_message
            )
        elif result.error_code == 429:
            # Rate limited - will be retried
            await self.queue_manager.mark_failed(
                result.game_id,
                result.error_message,
                result.error_code,
                should_retry=True
            )
        else:
            # Other failures
            await self.queue_manager.mark_failed(
                result.game_id,
                result.error_message,
                result.error_code,
                should_retry=True
            )
            
    def _update_session_stats(self, results: List[ScrapingResult]):
        """Update session statistics"""
        self.session_stats['total_processed'] += len(results)
        
        for result in results:
            if result.success:
                self.session_stats['successful'] += 1
            elif result.error_code == 404:
                self.session_stats['invalid'] += 1
            elif result.error_code == 429:
                self.session_stats['rate_limited'] += 1
            else:
                self.session_stats['failed'] += 1
                
        # Update average response time
        response_times = [r.response_time_ms for r in results if r.response_time_ms]
        if response_times:
            total_time = sum(response_times)
            total_count = self.session_stats['total_processed']
            self.session_stats['avg_response_time'] = (
                (self.session_stats['avg_response_time'] * (total_count - len(response_times)) + total_time) 
                / total_count
            )
            
    async def _log_progress(self):
        """Log current progress and statistics"""
        queue_stats = await self.queue_manager.get_queue_statistics()
        rate_stats = self.rate_limiter.get_rate_limit_stats()
        
        elapsed = datetime.now() - self.session_stats['started_at']
        rate_per_hour = (self.session_stats['total_processed'] / max(elapsed.total_seconds() / 3600, 0.01))
        
        logger.info(
            f"Progress: {self.session_stats['total_processed']} processed "
            f"({self.session_stats['successful']} success, "
            f"{self.session_stats['failed']} failed, "
            f"{self.session_stats['invalid']} invalid, "
            f"{self.session_stats['rate_limited']} rate limited) | "
            f"Rate: {rate_per_hour:.1f}/hour | "
            f"Queue: {queue_stats['queue_counts']['pending']} pending, "
            f"{queue_stats['queue_counts']['completed']} completed"
        )
        
        if rate_stats['in_backoff']:
            logger.info(f"Rate limiter: In backoff until {rate_stats['backoff_until']}")
            
    async def _get_final_stats(self) -> Dict[str, Any]:
        """Get final session statistics"""
        queue_stats = await self.queue_manager.get_queue_statistics()
        season_progress = await self.queue_manager.get_season_progress()
        
        elapsed = datetime.now() - self.session_stats['started_at']
        
        return {
            'session_stats': self.session_stats,
            'elapsed_time': str(elapsed),
            'queue_stats': queue_stats,
            'season_progress': season_progress,
            'rate_limiter_stats': self.rate_limiter.get_rate_limit_stats()
        }


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NBA Mass Game Scraper')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximum concurrent workers')
    parser.add_argument('--max-batches', type=int, help='Maximum batches to process')
    parser.add_argument('--season', type=str, help='Filter by specific season (e.g., 2023-24)')
    parser.add_argument('--rate-limit', type=float, default=0.5, help='Requests per second')
    parser.add_argument('--db-url', type=str, help='Database URL (overrides environment)')
    
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or get_database_url()
    if not db_url:
        logger.error("Database URL not provided and not found in environment")
        sys.exit(1)
    
    # Create and initialize scraper
    scraper = MassGameScraper(
        db_url=db_url,
        batch_size=args.batch_size,
        max_workers=args.max_workers,
        rate_limit_rps=args.rate_limit
    )
    
    try:
        # Setup signal handlers for graceful shutdown
        scraper.setup_signal_handlers()
        
        # Initialize
        await scraper.initialize()
        
        # Run scraping session
        final_stats = await scraper.run_scraping_session(
            max_batches=args.max_batches,
            season_filter=args.season
        )
        
        logger.info("Scraping session completed successfully")
        logger.info(f"Final statistics: {final_stats}")
        
    except Exception as e:
        logger.error(f"Error during scraping session: {e}")
        sys.exit(1)
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())