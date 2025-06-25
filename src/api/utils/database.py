"""
Database utility functions for API connections and query execution.
Handles connection pooling and async database operations.
"""

import asyncio
import asyncpg
import pandas as pd
from typing import List, Dict, Any, Optional
import os
from contextlib import asynccontextmanager


class DatabaseManager:
    """Async database connection manager with connection pooling"""
    
    def __init__(self):
        self.pool = None
        self._database_url = self._get_database_url()
    
    def _get_database_url(self) -> str:
        """Get database URL from environment variables"""
        # Try different environment variable names
        db_url = (
            os.getenv('DATABASE_URL') or 
            os.getenv('NEON_DATABASE_URL') or
            os.getenv('POSTGRES_URL')
        )
        
        if not db_url:
            # Construct from individual components if URL not available
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            database = os.getenv('DB_NAME', 'nba_pbp')
            user = os.getenv('DB_USER', 'postgres')
            password = os.getenv('DB_PASSWORD', '')
            
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        return db_url
    
    async def connect(self):
        """Initialize the connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self._database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'application_name': 'nba_api',
                    'tcp_keepalives_idle': '300',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3'
                }
            )
    
    async def disconnect(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager for getting a database connection"""
        if not self.pool:
            await self.connect()
        
        connection = await self.pool.acquire()
        try:
            yield connection
        finally:
            await self.pool.release(connection)
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_query_df(self, query: str, *args) -> pd.DataFrame:
        """Execute a query and return results as pandas DataFrame"""
        results = await self.execute_query(query, *args)
        return pd.DataFrame(results)
    
    async def execute_count_query(self, query: str, *args) -> int:
        """Execute a count query and return the count"""
        async with self.get_connection() as conn:
            result = await conn.fetchval(query, *args)
            return result or 0
    
    async def execute_scalar(self, query: str, *args) -> Any:
        """Execute a query and return a single scalar value"""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            result = await self.execute_scalar("SELECT 1")
            return result == 1
        except Exception:
            return False
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
        """
        return await self.execute_query(query, table_name)
    
    async def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = $1
        )
        """
        return await self.execute_scalar(query, table_name)


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_manager() -> DatabaseManager:
    """Dependency for getting database manager"""
    if not db_manager.pool:
        await db_manager.connect()
    return db_manager


async def startup_db():
    """Startup function to initialize database connection"""
    await db_manager.connect()


async def shutdown_db():
    """Shutdown function to close database connection"""
    await db_manager.disconnect()


class QueryExecutor:
    """High-level query execution with error handling and logging"""
    
    def __init__(self, db_manager: DatabaseManager):
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
        data_task = self.db_manager.execute_query(paginated_query, *params)
        count_task = self.db_manager.execute_count_query(count_query, *params)
        
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
        return await self.db_manager.execute_query_df(query, *params)
    
    async def validate_player_exists(self, player_id: int) -> bool:
        """Validate that a player exists in the database"""
        query = "SELECT EXISTS(SELECT 1 FROM players WHERE id = $1)"
        return await self.db_manager.execute_scalar(query, player_id)
    
    async def validate_team_exists(self, team_id: int) -> bool:
        """Validate that a team exists in the database"""
        query = "SELECT EXISTS(SELECT 1 FROM teams WHERE team_id = $1)"
        return await self.db_manager.execute_scalar(query, team_id)
    
    async def validate_game_exists(self, game_id: str) -> bool:
        """Validate that a game exists in the database"""
        query = "SELECT EXISTS(SELECT 1 FROM enhanced_games WHERE game_id = $1)"
        return await self.db_manager.execute_scalar(query, game_id)
    
    async def get_available_seasons(self) -> List[str]:
        """Get list of available seasons in the database"""
        query = "SELECT DISTINCT season FROM enhanced_games ORDER BY season DESC"
        results = await self.db_manager.execute_query(query)
        return [row['season'] for row in results]
    
    async def get_latest_season(self) -> Optional[str]:
        """Get the most recent season in the database"""
        query = "SELECT MAX(season) as latest_season FROM enhanced_games"
        result = await self.db_manager.execute_scalar(query)
        return result
    
    async def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get basic player information"""
        query = """
        SELECT id as player_id, player_name, first_name, last_name, team_id
        FROM players 
        WHERE id = $1
        """
        results = await self.db_manager.execute_query(query, player_id)
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
            results = await self.db_manager.execute_query(query, team_id, season)
        else:
            # Get current active team info
            query = """
            SELECT team_id, full_name as team_name, tricode as team_abbreviation, 
                   city as team_city, first_season, last_season, is_active
            FROM teams 
            WHERE team_id = $1 AND is_active = true
            LIMIT 1
            """
            results = await self.db_manager.execute_query(query, team_id)
        
        return results[0] if results else None