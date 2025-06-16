"""
Enhanced Game Scraping Queue for Mass NBA Data Collection
Implements the queue management system from Plan 08
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from uuid import uuid4
import asyncpg
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ScrapingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    INVALID = "invalid"


@dataclass
class GameScrapingTask:
    """Represents a game to be scraped"""
    game_id: str
    season: str
    game_date: datetime
    home_team: str
    away_team: str
    game_url: str
    status: ScrapingStatus = ScrapingStatus.PENDING
    retry_count: int = 0
    priority: int = 0
    queue_id: int = None


@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    game_id: str
    success: bool
    raw_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    json_size_bytes: Optional[int] = None


class GameScrapingQueue:
    """Enhanced queue manager for mass game scraping operations"""
    
    def __init__(self, db_url: str, session_id: Optional[str] = None):
        self.db_url = db_url
        self.pool = None
        self.session_id = session_id or str(uuid4())
        
    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.db_url, 
            min_size=5, 
            max_size=20,
            command_timeout=60
        )
        logger.info(f"GameScrapingQueue initialized with session {self.session_id}")
        
        # Create session record
        await self._create_session_record()
        
    async def close(self):
        """Close database connections and finalize session"""
        if self.pool:
            await self._finalize_session_record()
            await self.pool.close()
            
    async def _create_session_record(self):
        """Create a new scraping session record"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO scraping_sessions (session_id, started_at, is_active)
                VALUES ($1, NOW(), TRUE)
                ON CONFLICT (session_id) DO NOTHING
            """, self.session_id)
            
    async def _finalize_session_record(self):
        """Finalize the scraping session record"""
        async with self.pool.acquire() as conn:
            # Calculate session stats
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'completed') as successful,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    AVG(response_time_ms) as avg_response_time,
                    SUM(data_size_bytes) / 1024.0 / 1024.0 as total_data_mb
                FROM scraping_queue
                WHERE updated_at >= (
                    SELECT started_at FROM scraping_sessions 
                    WHERE session_id = $1
                )
            """, self.session_id)
            
            # Update session record
            await conn.execute("""
                UPDATE scraping_sessions
                SET ended_at = NOW(),
                    is_active = FALSE,
                    successful_games = $2,
                    failed_games = $3,
                    average_response_time_ms = $4,
                    total_data_size_mb = $5
                WHERE session_id = $1
            """, self.session_id, stats['successful'], stats['failed'], 
                stats['avg_response_time'], stats['total_data_mb'])
            
    async def get_next_batch(self, batch_size: int = 100) -> List[GameScrapingTask]:
        """Get next batch of games to scrape with atomic locking"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Select and lock games for processing
                games = await conn.fetch("""
                    SELECT id, game_id, season, game_date, home_team, away_team, 
                           game_url, retry_count, priority
                    FROM scraping_queue
                    WHERE status = 'pending' 
                    AND retry_count < max_retries
                    ORDER BY priority DESC, game_date ASC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                """, batch_size)
                
                if not games:
                    return []
                
                # Mark as in progress
                game_ids = [g['game_id'] for g in games]
                await conn.execute("""
                    UPDATE scraping_queue
                    SET status = 'in_progress',
                        started_at = NOW(),
                        updated_at = NOW()
                    WHERE game_id = ANY($1::text[])
                """, game_ids)
                
                # Convert to GameScrapingTask objects
                tasks = []
                for game in games:
                    tasks.append(GameScrapingTask(
                        game_id=game['game_id'],
                        season=game['season'],
                        game_date=game['game_date'],
                        home_team=game['home_team'],
                        away_team=game['away_team'],
                        game_url=game['game_url'],
                        status=ScrapingStatus.IN_PROGRESS,
                        retry_count=game['retry_count'],
                        priority=game['priority'],
                        queue_id=game['id']
                    ))
                
                logger.info(f"Retrieved batch of {len(tasks)} games for scraping")
                return tasks
                
    async def mark_completed(self, game_id: str, json_data: Dict[str, Any], 
                           response_time_ms: int) -> bool:
        """Mark game as successfully scraped and store JSON data"""
        json_size = len(json.dumps(json_data).encode('utf-8'))
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Update queue status
                await conn.execute("""
                    UPDATE scraping_queue
                    SET status = 'completed',
                        completed_at = NOW(),
                        updated_at = NOW(),
                        response_time_ms = $2,
                        data_size_bytes = $3,
                        error_message = NULL,
                        error_code = NULL
                    WHERE game_id = $1
                """, game_id, response_time_ms, json_size)
                
                # Store raw JSON data
                await conn.execute("""
                    INSERT INTO raw_game_data 
                    (game_id, game_url, raw_json, json_size, processing_status)
                    VALUES ($1, $2, $3, $4, 'raw')
                    ON CONFLICT (game_id) 
                    DO UPDATE SET 
                        raw_json = $3,
                        json_size = $4,
                        scraped_at = NOW()
                """, game_id, 
                    await self._get_game_url(conn, game_id),
                    json.dumps(json_data), 
                    json_size)
                
                # Update season progress
                await self._update_season_progress(conn, game_id, 'completed')
                
        logger.info(f"Marked game {game_id} as completed ({json_size} bytes)")
        return True
        
    async def mark_failed(self, game_id: str, error_message: str, 
                         error_code: Optional[int] = None, 
                         should_retry: bool = True) -> bool:
        """Mark game as failed and handle retry logic"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Get current retry count
                current = await conn.fetchrow("""
                    SELECT retry_count, max_retries 
                    FROM scraping_queue 
                    WHERE game_id = $1
                """, game_id)
                
                if not current:
                    logger.error(f"Game {game_id} not found in queue")
                    return False
                
                new_retry_count = current['retry_count'] + 1
                max_retries = current['max_retries']
                
                # Determine final status
                if not should_retry or new_retry_count >= max_retries:
                    final_status = 'failed'
                    started_at = None
                else:
                    final_status = 'pending'  # Will be retried
                    started_at = None
                
                # Update queue record
                await conn.execute("""
                    UPDATE scraping_queue
                    SET status = $2,
                        retry_count = $3,
                        error_message = $4,
                        error_code = $5,
                        updated_at = NOW(),
                        started_at = $6
                    WHERE game_id = $1
                """, game_id, final_status, new_retry_count, 
                    error_message, error_code, started_at)
                
                # Log detailed error
                await conn.execute("""
                    INSERT INTO scraping_errors 
                    (game_id, session_id, error_type, error_code, error_message, retry_number)
                    VALUES ($1, $2, 'scraping_failure', $3, $4, $5)
                """, game_id, self.session_id, error_code, error_message, new_retry_count)
                
                # Update season progress if permanently failed
                if final_status == 'failed':
                    await self._update_season_progress(conn, game_id, 'failed')
                
        logger.warning(f"Marked game {game_id} as {final_status} (attempt {new_retry_count})")
        return final_status == 'failed'  # Return True if permanently failed
        
    async def mark_invalid(self, game_id: str, reason: str) -> bool:
        """Mark game URL as invalid (404, malformed, etc.)"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    UPDATE scraping_queue
                    SET status = 'invalid',
                        error_message = $2,
                        updated_at = NOW(),
                        started_at = NULL
                    WHERE game_id = $1
                """, game_id, reason)
                
                # Log error
                await conn.execute("""
                    INSERT INTO scraping_errors
                    (game_id, session_id, error_type, error_message, retry_number)
                    VALUES ($1, $2, 'invalid_url', $3, 0)
                """, game_id, self.session_id, reason)
                
                await self._update_season_progress(conn, game_id, 'invalid')
                
        logger.warning(f"Marked game {game_id} as invalid: {reason}")
        return True
        
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        async with self.pool.acquire() as conn:
            # Basic counts
            basic_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'invalid') as invalid,
                    COUNT(*) as total
                FROM scraping_queue
            """)
            
            # Performance metrics
            perf_stats = await conn.fetchrow("""
                SELECT 
                    AVG(response_time_ms) as avg_response_time_ms,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_ms) as median_response_time_ms,
                    SUM(data_size_bytes) / 1024.0 / 1024.0 as total_data_mb,
                    AVG(data_size_bytes) / 1024.0 as avg_data_kb
                FROM scraping_queue
                WHERE status = 'completed'
            """)
            
            # Progress rate
            rate_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE completed_at > NOW() - INTERVAL '1 hour') as completed_last_hour,
                    COUNT(*) FILTER (WHERE completed_at > NOW() - INTERVAL '1 day') as completed_last_day
                FROM scraping_queue
                WHERE status = 'completed'
            """)
            
            return {
                'queue_counts': dict(basic_stats),
                'performance': dict(perf_stats) if perf_stats else {},
                'rate': dict(rate_stats),
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat()
            }
            
    async def get_season_progress(self) -> List[Dict[str, Any]]:
        """Get detailed progress by season"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    season,
                    COUNT(*) as total_games,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'invalid') as invalid,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    ROUND(
                        COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / COUNT(*), 2
                    ) as completion_percentage,
                    MIN(game_date) as season_start,
                    MAX(game_date) as season_end
                FROM scraping_queue
                GROUP BY season
                ORDER BY season
            """)
            
            return [dict(r) for r in results]
            
    async def reset_stale_games(self, timeout_minutes: int = 30) -> int:
        """Reset games stuck in 'in_progress' status"""
        async with self.pool.acquire() as conn:
            cutoff = datetime.now() - timedelta(minutes=timeout_minutes)
            
            result = await conn.execute("""
                UPDATE scraping_queue
                SET status = 'pending',
                    started_at = NULL,
                    updated_at = NOW()
                WHERE status = 'in_progress'
                AND started_at < $1
            """, cutoff)
            
            count = int(result.split()[-1])
            if count > 0:
                logger.warning(f"Reset {count} stale games to pending status")
                
            return count
            
    async def get_failed_games_analysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Analyze failed games for patterns"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    sq.game_id,
                    sq.season,
                    sq.game_date,
                    sq.home_team,
                    sq.away_team,
                    sq.game_url,
                    sq.retry_count,
                    sq.error_message,
                    sq.error_code,
                    COUNT(se.id) as error_count,
                    ARRAY_AGG(DISTINCT se.error_type) as error_types
                FROM scraping_queue sq
                LEFT JOIN scraping_errors se ON sq.game_id = se.game_id
                WHERE sq.status = 'failed'
                GROUP BY sq.game_id, sq.season, sq.game_date, sq.home_team, 
                         sq.away_team, sq.game_url, sq.retry_count, 
                         sq.error_message, sq.error_code, sq.updated_at
                ORDER BY sq.updated_at DESC
                LIMIT $1
            """, limit)
            
            return [dict(r) for r in results]
            
    async def _get_game_url(self, conn, game_id: str) -> str:
        """Get game URL from queue"""
        result = await conn.fetchval("""
            SELECT game_url FROM scraping_queue WHERE game_id = $1
        """, game_id)
        return result or ""
        
    async def _update_season_progress(self, conn, game_id: str, result_type: str):
        """Update season progress tracking"""
        season = await conn.fetchval("""
            SELECT season FROM scraping_queue WHERE game_id = $1
        """, game_id)
        
        if not season:
            return
            
        # This will be handled by the season_progress_view automatically
        # since it's calculated from scraping_queue status counts
        pass