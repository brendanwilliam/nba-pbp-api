"""
Systematic Scraper for NBA Games
Main execution framework with rate limiting, error handling, and monitoring
"""

import asyncio
import aiohttp
import logging
import time
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import backoff

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.queue_manager import QueueManager, QueueStatus
from scrapers.game_discovery import GameDiscovery

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: float = 1.0, burst: int = 1):
        self.rate = rate  # requests per second
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire permission to make a request"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens < 1:
                sleep_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(sleep_time)
                self.tokens = 1
                
            self.tokens -= 1


class SystematicScraper:
    """Main scraper class for systematic NBA game collection"""
    
    def __init__(self, db_url: str, rate_limit: float = 1.0):
        self.queue_manager = QueueManager(db_url)
        self.game_discovery = GameDiscovery()
        self.rate_limiter = RateLimiter(rate=rate_limit, burst=5)
        self.session = None
        self.stats = {
            'total_scraped': 0,
            'total_failed': 0,
            'total_invalid': 0,
            'start_time': None,
            'session_errors': {}
        }
        
    async def initialize(self):
        """Initialize all components"""
        await self.queue_manager.initialize()
        await self.game_discovery.initialize()
        
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            timeout=aiohttp.ClientTimeout(total=60)
        )
        
        self.stats['start_time'] = datetime.now()
        logger.info("Systematic scraper initialized")
        
    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        await self.game_discovery.close()
        await self.queue_manager.close()
        
    async def populate_queue_for_season(self, season: str) -> int:
        """Discover and add games for a season to the queue"""
        logger.info(f"Discovering games for season {season}")
        
        try:
            games = await self.game_discovery.discover_season_games(season)
            
            if not games:
                logger.warning(f"No games found for season {season}")
                return 0
                
            # Convert to queue items
            from database.queue_manager import GameQueueItem
            queue_items = [
                GameQueueItem(
                    game_id=game.game_id,
                    season=game.season,
                    game_date=game.game_date,
                    home_team=game.home_team,
                    away_team=game.away_team,
                    game_url=game.game_url,
                    priority=self._calculate_priority(game.game_date)
                )
                for game in games
            ]
            
            # Add to queue
            added = await self.queue_manager.add_games_to_queue(queue_items)
            logger.info(f"Added {added} games for season {season} to queue")
            
            return added
            
        except Exception as e:
            logger.error(f"Error populating queue for season {season}: {e}")
            return 0
            
    def _calculate_priority(self, game_date: datetime) -> int:
        """Calculate priority based on game date (recent games higher priority)"""
        days_ago = (datetime.now() - game_date).days
        return max(0, 10000 - days_ago)
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def _scrape_game(self, game_info: Dict) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Scrape a single game with retry logic"""
        game_id = game_info['game_id']
        game_url = game_info['game_url']
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Add jitter to avoid patterns
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        start_time = time.time()
        
        try:
            async with self.session.get(game_url) as response:
                response_time_ms = int((time.time() - start_time) * 1000)
                
                if response.status == 404:
                    return False, None, "Game not found (404)"
                    
                if response.status == 429:
                    # Rate limited - back off significantly
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limited")
                    
                response.raise_for_status()
                
                html = await response.text()
                data_size = len(html.encode('utf-8'))
                
                # Extract JSON data
                game_data = self._extract_game_data(html)
                
                if not game_data:
                    return False, None, "No game data found in page"
                    
                # Validate data
                if not self._validate_game_data(game_data):
                    return False, None, "Invalid game data structure"
                    
                result = {
                    'game_id': game_id,
                    'game_data': game_data,
                    'scraped_at': datetime.now().isoformat(),
                    'response_time_ms': response_time_ms,
                    'data_size_bytes': data_size
                }
                
                return True, result, None
                
        except asyncio.TimeoutError:
            return False, None, "Request timeout"
        except aiohttp.ClientError as e:
            return False, None, f"HTTP error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error scraping {game_id}: {e}")
            return False, None, f"Unexpected error: {str(e)}"
            
    def _extract_game_data(self, html: str) -> Optional[Dict]:
        """Extract JSON data from game page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the __NEXT_DATA__ script tag
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        
        if not script_tag:
            return None
            
        try:
            json_text = script_tag.string
            data = json.loads(json_text)
            return data
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from __NEXT_DATA__")
            return None
            
    def _validate_game_data(self, data: Dict) -> bool:
        """Basic validation of extracted game data"""
        # Check for expected structure
        required_paths = [
            ['props', 'pageProps'],
            ['props', 'pageProps', 'game']
        ]
        
        for path in required_paths:
            current = data
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    return False
                current = current[key]
                
        return True
        
    async def process_queue_batch(self, batch_size: int = 10) -> Dict[str, int]:
        """Process a batch of games from the queue"""
        games = await self.queue_manager.get_next_games(batch_size)
        
        if not games:
            return {'processed': 0, 'success': 0, 'failed': 0, 'invalid': 0}
            
        results = {'processed': 0, 'success': 0, 'failed': 0, 'invalid': 0}
        
        # Process games concurrently with controlled concurrency
        tasks = []
        for game in games:
            task = self._process_single_game(game)
            tasks.append(task)
            
        # Wait for all tasks to complete
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                logger.error(f"Task exception: {outcome}")
                results['failed'] += 1
            elif outcome:
                results[outcome] += 1
            results['processed'] += 1
            
        return results
        
    async def _process_single_game(self, game_info: Dict) -> str:
        """Process a single game and update queue status"""
        game_id = game_info['game_id']
        
        try:
            success, data, error = await self._scrape_game(game_info)
            
            if success and data:
                # Save data to database (implement storage logic)
                await self._save_game_data(data)
                
                # Mark as completed
                await self.queue_manager.mark_game_completed(
                    game_id, 
                    data['response_time_ms'],
                    data['data_size_bytes']
                )
                
                self.stats['total_scraped'] += 1
                return 'success'
                
            elif error and '404' in error:
                # Game doesn't exist
                await self.queue_manager.mark_game_invalid(game_id, error)
                self.stats['total_invalid'] += 1
                return 'invalid'
                
            else:
                # Failed - will retry
                await self.queue_manager.mark_game_failed(game_id, error or "Unknown error")
                self.stats['total_failed'] += 1
                
                # Track error types
                error_type = error.split(':')[0] if error else "Unknown"
                self.stats['session_errors'][error_type] = self.stats['session_errors'].get(error_type, 0) + 1
                
                return 'failed'
                
        except Exception as e:
            logger.error(f"Error processing game {game_id}: {e}")
            await self.queue_manager.mark_game_failed(game_id, str(e))
            return 'failed'
            
    async def _save_game_data(self, data: Dict):
        """Save scraped game data to database"""
        # TODO: Implement actual storage logic
        # For now, just log that we would save it
        game_id = data['game_id']
        logger.debug(f"Would save game data for {game_id}")
        
    async def run_continuous_scraping(self, batch_size: int = 10, max_workers: int = 3):
        """Run continuous scraping with multiple workers"""
        logger.info(f"Starting continuous scraping with {max_workers} workers")
        
        # Reset stale games periodically
        async def reset_stale_periodically():
            while True:
                await asyncio.sleep(1800)  # Every 30 minutes
                await self.queue_manager.reset_stale_games()
                
        # Monitor progress periodically
        async def monitor_progress():
            while True:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._log_progress()
                
        # Create worker tasks
        workers = []
        for i in range(max_workers):
            worker = self._scraping_worker(f"Worker-{i+1}", batch_size)
            workers.append(worker)
            
        # Run all tasks concurrently
        tasks = workers + [reset_stale_periodically(), monitor_progress()]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
            
    async def _scraping_worker(self, worker_name: str, batch_size: int):
        """Individual scraping worker"""
        logger.info(f"{worker_name} started")
        
        consecutive_empty = 0
        
        while True:
            try:
                results = await self.process_queue_batch(batch_size)
                
                if results['processed'] == 0:
                    consecutive_empty += 1
                    if consecutive_empty > 10:
                        logger.info(f"{worker_name}: No more games to process")
                        break
                    await asyncio.sleep(5)
                else:
                    consecutive_empty = 0
                    logger.debug(f"{worker_name} processed batch: {results}")
                    
            except Exception as e:
                logger.error(f"{worker_name} error: {e}")
                await asyncio.sleep(10)
                
    async def _log_progress(self):
        """Log current scraping progress"""
        stats = await self.queue_manager.get_queue_stats()
        runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 3600
        
        logger.info(
            f"Progress - Completed: {stats['completed']}, "
            f"Pending: {stats['pending']}, "
            f"Failed: {stats['failed']}, "
            f"Invalid: {stats['invalid']}, "
            f"Rate: {stats['completed'] / runtime:.1f} games/hour"
        )
        
    async def scrape_all_seasons(self, start_season: Optional[str] = None):
        """Main entry point to scrape all seasons"""
        seasons = list(self.game_discovery.SEASONS.keys())
        
        if start_season:
            start_idx = seasons.index(start_season)
            seasons = seasons[start_idx:]
            
        # Initialize season progress tracking
        estimates = self.game_discovery.estimate_game_counts()
        await self.queue_manager.initialize_season_progress(estimates)
        
        # Process each season
        for season in seasons:
            logger.info(f"Starting season {season}")
            
            # Populate queue for this season
            added = await self.populate_queue_for_season(season)
            
            if added > 0:
                # Process the season
                await self.run_continuous_scraping(batch_size=20, max_workers=3)
                
            # Get season summary
            progress = await self.queue_manager.get_season_progress()
            season_stats = next((s for s in progress if s['season'] == season), None)
            
            if season_stats:
                logger.info(
                    f"Season {season} complete - "
                    f"Scraped: {season_stats['scraped_games']}, "
                    f"Failed: {season_stats['failed_games']}, "
                    f"Invalid: {season_stats['invalid_games']}"
                )
                
            # Delay between seasons
            await asyncio.sleep(10)
            
        logger.info("All seasons completed!")