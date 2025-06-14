"""
Queue Manager for Systematic NBA Game Scraping
Handles queue operations, status tracking, and retry logic
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from uuid import uuid4
import asyncpg
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueueStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INVALID = "invalid"


@dataclass
class GameQueueItem:
    game_id: str
    season: str
    game_date: datetime
    home_team: str
    away_team: str
    game_url: str
    status: QueueStatus = QueueStatus.PENDING
    retry_count: int = 0
    priority: int = 0
    

class QueueManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
        self.session_id = str(uuid4())
        
    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(self.db_url, min_size=5, max_size=20)
        logger.info(f"Queue manager initialized with session {self.session_id}")
        
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            
    async def add_games_to_queue(self, games: List[GameQueueItem]) -> int:
        """Add multiple games to the scraping queue"""
        async with self.pool.acquire() as conn:
            # Prepare batch insert
            values = []
            for game in games:
                values.append((
                    game.game_id,
                    game.season,
                    game.game_date,
                    game.home_team,
                    game.away_team,
                    game.game_url,
                    game.status,
                    game.priority
                ))
            
            # Insert games, ignoring duplicates
            result = await conn.executemany("""
                INSERT INTO scraping_queue 
                (game_id, season, game_date, home_team, away_team, game_url, status, priority)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (game_id) DO NOTHING
            """, values)
            
            inserted_count = int(result.split()[-1])
            logger.info(f"Added {inserted_count} new games to queue")
            return inserted_count
            
    async def get_next_games(self, batch_size: int = 10) -> List[Dict]:
        """Get next batch of games to scrape"""
        async with self.pool.acquire() as conn:
            # Start transaction for atomic update
            async with conn.transaction():
                # Select and lock games for processing
                games = await conn.fetch("""
                    SELECT id, game_id, season, game_date, home_team, away_team, game_url, retry_count
                    FROM scraping_queue
                    WHERE status = 'pending' 
                    AND retry_count < max_retries
                    ORDER BY priority DESC, game_date DESC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                """, batch_size)
                
                if games:
                    # Update status to in_progress
                    game_ids = [g['game_id'] for g in games]
                    await conn.execute("""
                        UPDATE scraping_queue
                        SET status = 'in_progress',
                            started_at = NOW()
                        WHERE game_id = ANY($1::text[])
                    """, game_ids)
                    
                return [dict(g) for g in games]
                
    async def mark_game_completed(self, game_id: str, response_time_ms: int, data_size_bytes: int):
        """Mark a game as successfully scraped"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE scraping_queue
                SET status = 'completed',
                    completed_at = NOW(),
                    response_time_ms = $2,
                    data_size_bytes = $3
                WHERE game_id = $1
            """, game_id, response_time_ms, data_size_bytes)
            
            # Update season progress
            await self._update_season_progress(conn, game_id, 'completed')
            
    async def mark_game_failed(self, game_id: str, error_message: str, error_code: Optional[int] = None):
        """Mark a game as failed and increment retry count"""
        async with self.pool.acquire() as conn:
            # Update game status
            result = await conn.fetchrow("""
                UPDATE scraping_queue
                SET status = CASE 
                        WHEN retry_count + 1 >= max_retries THEN 'failed'
                        ELSE 'pending'
                    END,
                    retry_count = retry_count + 1,
                    error_message = $2,
                    error_code = $3,
                    started_at = NULL
                WHERE game_id = $1
                RETURNING status, retry_count
            """, game_id, error_message, error_code)
            
            # Log error
            await conn.execute("""
                INSERT INTO scraping_errors 
                (game_id, session_id, error_type, error_code, error_message, retry_number)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, game_id, self.session_id, 'scraping_error', error_code, error_message, result['retry_count'])
            
            if result['status'] == 'failed':
                await self._update_season_progress(conn, game_id, 'failed')
                
    async def mark_game_invalid(self, game_id: str, reason: str):
        """Mark a game URL as invalid (404, etc)"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE scraping_queue
                SET status = 'invalid',
                    error_message = $2
                WHERE game_id = $1
            """, game_id, reason)
            
            await self._update_season_progress(conn, game_id, 'invalid')
            
    async def _update_season_progress(self, conn, game_id: str, result_type: str):
        """Update season progress tracking"""
        season = await conn.fetchval("""
            SELECT season FROM scraping_queue WHERE game_id = $1
        """, game_id)
        
        if result_type == 'completed':
            await conn.execute("""
                UPDATE season_progress
                SET scraped_games = scraped_games + 1,
                    progress_percentage = (scraped_games + 1) * 100.0 / total_games,
                    last_updated = NOW()
                WHERE season = $1
            """, season)
        elif result_type == 'failed':
            await conn.execute("""
                UPDATE season_progress
                SET failed_games = failed_games + 1,
                    last_updated = NOW()
                WHERE season = $1
            """, season)
        elif result_type == 'invalid':
            await conn.execute("""
                UPDATE season_progress
                SET invalid_games = invalid_games + 1,
                    last_updated = NOW()
                WHERE season = $1
            """, season)
            
    async def get_queue_stats(self) -> Dict:
        """Get current queue statistics"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'invalid') as invalid,
                    COUNT(*) as total,
                    AVG(response_time_ms) FILTER (WHERE status = 'completed') as avg_response_time,
                    SUM(data_size_bytes) FILTER (WHERE status = 'completed') / 1024.0 / 1024.0 as total_data_mb
                FROM scraping_queue
            """)
            
            return dict(stats)
            
    async def get_season_progress(self) -> List[Dict]:
        """Get progress for all seasons"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT * FROM season_progress_view
                ORDER BY season
            """)
            
            return [dict(r) for r in results]
            
    async def reset_stale_games(self, timeout_minutes: int = 30):
        """Reset games that have been in progress too long"""
        async with self.pool.acquire() as conn:
            cutoff = datetime.now() - timedelta(minutes=timeout_minutes)
            
            result = await conn.execute("""
                UPDATE scraping_queue
                SET status = 'pending',
                    started_at = NULL
                WHERE status = 'in_progress'
                AND started_at < $1
            """, cutoff)
            
            count = int(result.split()[-1])
            if count > 0:
                logger.warning(f"Reset {count} stale games to pending status")
                
    async def initialize_season_progress(self, season_game_counts: Dict[str, int]):
        """Initialize season progress tracking"""
        async with self.pool.acquire() as conn:
            for season, total_games in season_game_counts.items():
                await conn.execute("""
                    INSERT INTO season_progress (season, total_games)
                    VALUES ($1, $2)
                    ON CONFLICT (season) 
                    DO UPDATE SET total_games = $2
                """, season, total_games)