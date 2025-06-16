"""
NBA Game URL Validator
Validates accessibility and content of discovered game URLs
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import re
from bs4 import BeautifulSoup
import json
import time

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class URLValidationResult:
    """Result of URL validation."""
    
    def __init__(self, game_id: str, url: str):
        self.game_id = game_id
        self.url = url
        self.is_accessible = False
        self.has_next_data = False
        self.has_game_data = False
        self.response_status = None
        self.response_time_ms = None
        self.error_message = None
        self.validation_timestamp = datetime.now()
    
    def is_valid(self) -> bool:
        """Check if URL is considered valid for scraping."""
        return self.is_accessible and self.has_next_data and self.has_game_data
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage."""
        return {
            'game_id': self.game_id,
            'url': self.url,
            'is_accessible': self.is_accessible,
            'has_next_data': self.has_next_data,
            'has_game_data': self.has_game_data,
            'response_status': self.response_status,
            'response_time_ms': self.response_time_ms,
            'error_message': self.error_message,
            'validation_timestamp': self.validation_timestamp
        }


class GameURLValidator:
    """Validates NBA game URLs for accessibility and content."""
    
    def __init__(self, db_session: Optional[Session] = None, max_concurrent: int = 10):
        """Initialize validator with database session and concurrency limit."""
        self.db_session = db_session
        self.max_concurrent = max_concurrent
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Rate limiting
        self.requests_per_second = 2
        self.last_request_time = 0
        
    async def initialize(self):
        """Initialize aiohttp session with appropriate settings."""
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=5,
            keepalive_timeout=30,
            ssl=False  # Disable SSL verification for testing
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            timeout=aiohttp.ClientTimeout(total=30, connect=10)
        )
        
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            
    async def _rate_limit(self):
        """Implement rate limiting to avoid overwhelming the server."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def validate_url(self, game_id: str, url: str) -> URLValidationResult:
        """Validate a single game URL."""
        result = URLValidationResult(game_id, url)
        
        async with self.semaphore:
            await self._rate_limit()
            
            try:
                start_time = time.time()
                
                async with self.session.get(url) as response:
                    end_time = time.time()
                    result.response_time_ms = int((end_time - start_time) * 1000)
                    result.response_status = response.status
                    
                    if response.status == 200:
                        result.is_accessible = True
                        
                        # Get content for analysis
                        content = await response.text()
                        
                        # Check for __NEXT_DATA__
                        result.has_next_data = self._check_next_data(content)
                        
                        # Check for actual game data
                        if result.has_next_data:
                            result.has_game_data = self._check_game_data(content)
                            
                    elif response.status == 404:
                        result.error_message = "Page not found"
                    elif response.status == 403:
                        result.error_message = "Access forbidden"
                    elif response.status >= 500:
                        result.error_message = f"Server error: {response.status}"
                    else:
                        result.error_message = f"HTTP {response.status}"
                        
            except aiohttp.ClientTimeout:
                result.error_message = "Request timeout"
            except aiohttp.ClientError as e:
                result.error_message = f"Client error: {str(e)}"
            except Exception as e:
                result.error_message = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error validating {url}: {e}")
        
        return result
    
    def _check_next_data(self, content: str) -> bool:
        """Check if page contains __NEXT_DATA__ script."""
        # Check for script tag with id="__NEXT_DATA__"
        return 'id="__NEXT_DATA__"' in content or "id='__NEXT_DATA__'" in content
    
    def _check_game_data(self, content: str) -> bool:
        """Check if __NEXT_DATA__ contains actual game data."""
        try:
            # Parse HTML to find the script tag
            soup = BeautifulSoup(content, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not script_tag or not script_tag.string:
                # Fallback to regex pattern
                script_pattern = re.compile(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>([^<]+)</script>', re.DOTALL)
                match = script_pattern.search(content)
                if not match:
                    return False
                json_str = match.group(1)
            else:
                json_str = script_tag.string
            
            # Parse the JSON data
            data = json.loads(json_str)
            
            # Look for common game data indicators
            game_indicators = [
                'game',
                'homeTeam',
                'awayTeam',
                'actions',
                'plays',
                'boxScore',
                'gameId'
            ]
            
            # Check if any game indicators are present in the JSON
            json_str = json.dumps(data).lower()
            return any(indicator in json_str for indicator in game_indicators)
            
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error checking game data: {e}")
            return False
    
    async def validate_batch(self, games: List[Tuple[str, str]], batch_size: int = 50) -> List[URLValidationResult]:
        """Validate a batch of URLs concurrently."""
        results = []
        
        # Process in smaller batches to manage memory and connections
        for i in range(0, len(games), batch_size):
            batch = games[i:i + batch_size]
            
            # Create validation tasks for this batch
            tasks = []
            for game_id, url in batch:
                task = self.validate_url(game_id, url)
                tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions and add results
            for result in batch_results:
                if isinstance(result, BaseException):
                    logger.error(f"Validation task failed: {result}")
                    continue
                results.append(result)
            
            # Pause between batches
            if i + batch_size < len(games):
                await asyncio.sleep(2)
        
        return results
    
    async def validate_queue_urls(self, status_filter: str = 'pending', limit: Optional[int] = None) -> Dict[str, int]:
        """Validate URLs from the database queue."""
        if not self.db_session:
            raise ValueError("Database session required for queue validation")
        
        # Get URLs to validate
        query = text("""
            SELECT game_id, game_url 
            FROM game_url_queue 
            WHERE status = :status
            ORDER BY priority ASC, game_date DESC
        """)
        
        if limit:
            query = text(str(query) + f" LIMIT {limit}")
        
        result = self.db_session.execute(query, {'status': status_filter})
        games = [(row.game_id, row.game_url) for row in result.fetchall()]
        
        if not games:
            logger.info(f"No games found with status '{status_filter}'")
            return {'total': 0, 'valid': 0, 'invalid': 0, 'errors': 0}
        
        logger.info(f"Validating {len(games)} URLs...")
        
        # Validate all URLs
        validation_results = await self.validate_batch(games)
        
        # Update database with results
        stats = await self._update_validation_results(validation_results)
        
        return stats
    
    async def _update_validation_results(self, results: List[URLValidationResult]) -> Dict[str, int]:
        """Update database with validation results."""
        stats = {'total': len(results), 'valid': 0, 'invalid': 0, 'errors': 0}
        
        for result in results:
            try:
                if result.is_valid():
                    new_status = 'validated'
                    stats['valid'] += 1
                elif result.is_accessible:
                    new_status = 'invalid'  # Accessible but no game data
                    stats['invalid'] += 1
                else:
                    new_status = 'invalid'  # Not accessible
                    stats['invalid'] += 1
                
                # Update queue status
                update_query = text("""
                    UPDATE game_url_queue 
                    SET status = :status, 
                        url_validated = :validated,
                        updated_at = NOW()
                    WHERE game_id = :game_id
                """)
                
                self.db_session.execute(update_query, {
                    'status': new_status,
                    'validated': result.is_valid(),
                    'game_id': result.game_id
                })
                
            except Exception as e:
                logger.error(f"Error updating validation result for {result.game_id}: {e}")
                stats['errors'] += 1
        
        # Commit all updates
        try:
            self.db_session.commit()
            logger.info(f"Updated {len(results)} validation results")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error committing validation results: {e}")
            raise
        
        return stats
    
    async def validate_sample(self, season: Optional[str] = None, sample_size: int = 10) -> Dict[str, int]:
        """Validate a sample of URLs for testing purposes."""
        if not self.db_session:
            raise ValueError("Database session required")
        
        # Get sample URLs
        query = text("""
            SELECT game_id, game_url 
            FROM game_url_queue 
            WHERE status = 'pending'
        """)
        
        if season:
            query = text(str(query) + " AND season = :season")
            result = self.db_session.execute(query, {'season': season})
        else:
            result = self.db_session.execute(query)
        
        all_games = [(row.game_id, row.game_url) for row in result.fetchall()]
        
        if not all_games:
            return {'total': 0, 'valid': 0, 'invalid': 0, 'errors': 0}
        
        # Take sample
        import random
        sample_games = random.sample(all_games, min(sample_size, len(all_games)))
        
        logger.info(f"Validating sample of {len(sample_games)} URLs...")
        
        # Validate sample
        results = await self.validate_batch(sample_games)
        
        # Calculate stats without updating database
        stats = {'total': len(results), 'valid': 0, 'invalid': 0, 'errors': 0}
        
        for result in results:
            if result.is_valid():
                stats['valid'] += 1
            elif result.error_message:
                stats['errors'] += 1
            else:
                stats['invalid'] += 1
        
        # Log sample results
        logger.info(f"Sample validation results: {stats}")
        
        for result in results[:5]:  # Show first 5 detailed results
            logger.info(f"URL: {result.url}")
            logger.info(f"  Valid: {result.is_valid()}")
            logger.info(f"  Accessible: {result.is_accessible}")
            logger.info(f"  Has Next Data: {result.has_next_data}")
            logger.info(f"  Has Game Data: {result.has_game_data}")
            logger.info(f"  Response Time: {result.response_time_ms}ms")
            if result.error_message:
                logger.info(f"  Error: {result.error_message}")
        
        return stats


async def main():
    """Example usage of the URL validator."""
    validator = GameURLValidator()
    
    try:
        await validator.initialize()
        
        # Test with a few URLs
        test_urls = [
            ("test1", "https://www.nba.com/game/ind-vs-mem-0022400306"),
            ("test2", "https://www.nba.com/game/nop-vs-nyk-0022400308"),
        ]
        
        results = await validator.validate_batch(test_urls)
        
        for result in results:
            logger.info(f"URL: {result.url}")
            logger.info(f"Valid: {result.is_valid()}")
            logger.info(f"Accessible: {result.is_accessible}")
            logger.info(f"Next Data: {result.has_next_data}")
            logger.info(f"Game Data: {result.has_game_data}")
            logger.info(f"Response Time: {result.response_time_ms}ms")
            if result.error_message:
                logger.info(f"Error: {result.error_message}")
            logger.info("---")
            
    finally:
        await validator.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())