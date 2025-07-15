"""Unified database abstraction layer supporting both sync and async operations."""

import asyncio
import asyncpg
import pandas as pd
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from .config import get_database_config

load_dotenv()

# SQLAlchemy Base for models
Base = declarative_base()


class UnifiedDatabaseManager:
    """Unified database manager supporting both sync and async operations"""
    
    def __init__(self):
        self.async_pool = None
        self.sync_engine = None
        self.sync_session_factory = None
        self._db_config = get_database_config()
        self._database_url = self._db_config.get_connection_url()
        self._is_connected = False
    
    def _get_database_url(self) -> str:
        """Get database URL using unified configuration"""
        return self._db_config.get_connection_url()
    
    def _get_sync_database_url(self) -> str:
        """Get database URL formatted for SQLAlchemy sync connections"""
        return self._database_url
    
    def _get_async_database_url(self) -> str:
        """Get database URL formatted for asyncpg async connections"""
        return self._database_url
    
    # === ASYNC CONNECTION METHODS ===
    
    async def connect_async(self):
        """Initialize the async connection pool"""
        if not self.async_pool:
            self.async_pool = await asyncpg.create_pool(
                self._get_async_database_url(),
                min_size=self._db_config.min_connections,
                max_size=self._db_config.max_connections,
                command_timeout=self._db_config.command_timeout,
                server_settings={
                    'application_name': self._db_config.application_name,
                    'tcp_keepalives_idle': '300',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3'
                }
            )
        self._is_connected = True
    
    async def disconnect_async(self):
        """Close the async connection pool"""
        if self.async_pool:
            await self.async_pool.close()
            self.async_pool = None
        self._is_connected = False
    
    @asynccontextmanager
    async def get_async_connection(self):
        """Context manager for getting an async database connection"""
        if not self.async_pool:
            await self.connect_async()
        
        connection = await self.async_pool.acquire()
        try:
            yield connection
        finally:
            await self.async_pool.release(connection)
    
    async def execute_async_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute an async query and return results as list of dictionaries"""
        async with self.get_async_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_async_query_df(self, query: str, *args) -> pd.DataFrame:
        """Execute an async query and return results as pandas DataFrame"""
        results = await self.execute_async_query(query, *args)
        return pd.DataFrame(results)
    
    async def execute_async_count_query(self, query: str, *args) -> int:
        """Execute an async count query and return the count"""
        async with self.get_async_connection() as conn:
            result = await conn.fetchval(query, *args)
            return result or 0
    
    async def execute_async_scalar(self, query: str, *args) -> Any:
        """Execute an async query and return a single scalar value"""
        async with self.get_async_connection() as conn:
            return await conn.fetchval(query, *args)
    
    # === SYNC CONNECTION METHODS ===
    
    def connect_sync(self):
        """Initialize the sync SQLAlchemy engine and session factory"""
        if not self.sync_engine:
            self.sync_engine = create_engine(self._get_sync_database_url())
            self.sync_session_factory = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.sync_engine
            )
        self._is_connected = True
    
    def disconnect_sync(self):
        """Close the sync SQLAlchemy engine"""
        if self.sync_engine:
            self.sync_engine.dispose()
            self.sync_engine = None
            self.sync_session_factory = None
        self._is_connected = False
    
    def get_sync_session(self) -> Session:
        """Get a sync SQLAlchemy session"""
        if not self.sync_session_factory:
            self.connect_sync()
        return self.sync_session_factory()
    
    @asynccontextmanager
    async def get_sync_session_context(self):
        """Context manager for getting a sync database session"""
        session = self.get_sync_session()
        try:
            yield session
        finally:
            session.close()
    
    # === UNIFIED UTILITY METHODS ===
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of both sync and async connections"""
        async_healthy = False
        sync_healthy = False
        
        # Check async connection
        try:
            result = await self.execute_async_scalar("SELECT 1")
            async_healthy = result == 1
        except Exception:
            pass
        
        # Check sync connection
        try:
            session = self.get_sync_session()
            result = session.execute("SELECT 1").scalar()
            sync_healthy = result == 1
            session.close()
        except Exception:
            pass
        
        return {
            "async_healthy": async_healthy,
            "sync_healthy": sync_healthy,
            "overall_healthy": async_healthy or sync_healthy
        }
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
        """
        return await self.execute_async_query(query, table_name)
    
    async def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = $1
        )
        """
        return await self.execute_async_scalar(query, table_name)
    
    def get_database_url(self) -> str:
        """Get the database URL"""
        return self._database_url
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._is_connected


# Global unified database manager instance
_global_db_manager = UnifiedDatabaseManager()


def get_db_manager() -> UnifiedDatabaseManager:
    """Get the global unified database manager instance"""
    return _global_db_manager


def get_db() -> AsyncGenerator[Session, None]:
    """Get database session (legacy compatibility)"""
    db_manager = get_db_manager()
    session = db_manager.get_sync_session()
    try:
        yield session
    finally:
        session.close()


def get_database_url() -> str:
    """Get database URL (legacy compatibility)"""
    return get_db_manager().get_database_url()


# === ASYNC CONVENIENCE FUNCTIONS ===

async def get_async_db_manager() -> UnifiedDatabaseManager:
    """Get database manager and ensure async connection is initialized"""
    db_manager = get_db_manager()
    if not db_manager.async_pool:
        await db_manager.connect_async()
    return db_manager


async def startup_db():
    """Startup function to initialize both sync and async database connections"""
    db_manager = get_db_manager()
    await db_manager.connect_async()
    db_manager.connect_sync()


async def shutdown_db():
    """Shutdown function to close both sync and async database connections"""
    db_manager = get_db_manager()
    await db_manager.disconnect_async()
    db_manager.disconnect_sync()


class QueryExecutor:
    """High-level query execution with error handling and logging"""
    
    def __init__(self, db_manager: UnifiedDatabaseManager):
        self.db_manager = db_manager
    
    async def execute_with_pagination(self, 
                                    base_query: str, 
                                    count_query: str,
                                    params: List[Any],
                                    limit: int = 100,
                                    offset: int = 0) -> Dict[str, Any]:
        """Execute query with pagination and return results with metadata"""
        
        # Add pagination to the base query
        paginated_query = f"{base_query} LIMIT {limit} OFFSET {offset}"
        
        # Execute both queries concurrently
        data_task = self.db_manager.execute_async_query(paginated_query, *params)
        count_task = self.db_manager.execute_async_count_query(count_query, *params)
        
        data, total_count = await asyncio.gather(data_task, count_task)
        
        return {
            "data": data,
            "total_records": total_count,
            "limit": limit,
            "offset": offset,
            "has_next": offset + limit < total_count,
            "has_prev": offset > 0
        }
    
    async def execute_for_analysis(self, query: str, params: List[Any]) -> pd.DataFrame:
        """Execute query and return DataFrame for statistical analysis"""
        return await self.db_manager.execute_async_query_df(query, *params)
    
    async def validate_player_exists(self, player_id: int) -> bool:
        """Validate that a player exists in the database"""
        query = "SELECT EXISTS(SELECT 1 FROM players WHERE id = $1)"
        return await self.db_manager.execute_async_scalar(query, player_id)
    
    async def validate_team_exists(self, team_id: int) -> bool:
        """Validate that a team exists in the database"""
        query = "SELECT EXISTS(SELECT 1 FROM teams WHERE team_id = $1)"
        return await self.db_manager.execute_async_scalar(query, team_id)
    
    async def validate_game_exists(self, game_id: str) -> bool:
        """Validate that a game exists in the database"""
        query = "SELECT EXISTS(SELECT 1 FROM enhanced_games WHERE game_id = $1)"
        return await self.db_manager.execute_async_scalar(query, game_id)
    
    async def get_available_seasons(self) -> List[str]:
        """Get list of available seasons in the database"""
        query = "SELECT DISTINCT season FROM enhanced_games ORDER BY season DESC"
        results = await self.db_manager.execute_async_query(query)
        return [row['season'] for row in results]
    
    async def get_latest_season(self) -> Optional[str]:
        """Get the most recent season in the database"""
        query = "SELECT MAX(season) as latest_season FROM enhanced_games"
        result = await self.db_manager.execute_async_scalar(query)
        return result
    
    async def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get basic player information"""
        query = """
        SELECT id as player_id, player_name, first_name, last_name, team_id
        FROM players 
        WHERE id = $1
        """
        results = await self.db_manager.execute_async_query(query, player_id)
        return results[0] if results else None
    
    async def get_team_info(self, team_id: int, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get team information, optionally for a specific season"""
        if season:
            # Get team info for specific season
            query = """
            SELECT team_id, full_name as team_name, tricode as team_abbreviation, 
                   city as team_city, first_season, last_season, is_active
            FROM teams 
            WHERE team_id = $1 
              AND (first_season <= $2 AND (last_season >= $2 OR last_season IS NULL))
            ORDER BY first_season DESC
            LIMIT 1
            """
            results = await self.db_manager.execute_async_query(query, team_id, season)
        else:
            # Get current active team info
            query = """
            SELECT team_id, full_name as team_name, tricode as team_abbreviation, 
                   city as team_city, first_season, last_season, is_active
            FROM teams 
            WHERE team_id = $1 AND is_active = true
            LIMIT 1
            """
            results = await self.db_manager.execute_async_query(query, team_id)
        
        return results[0] if results else None