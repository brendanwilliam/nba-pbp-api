"""
SQLite-compatible models for testing.

This module provides SQLite-compatible versions of the database models
for testing purposes, replacing PostgreSQL-specific types like JSONB with JSON.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, func, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

SqliteTestBase = declarative_base()

class SqliteDatabaseVersion(SqliteTestBase):
    """SQLite-compatible version of DatabaseVersion model."""
    __tablename__ = 'database_versions'
    
    id = Column(Integer, primary_key=True)
    version = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    applied_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<DatabaseVersion(version='{self.version}', applied_at='{self.applied_at}')>"

class SqliteScrapingSession(SqliteTestBase):
    """SQLite-compatible version of ScrapingSession model."""
    __tablename__ = 'scraping_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(100), nullable=False)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    status = Column(String(20), default='running')
    games_scraped = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<ScrapingSession(name='{self.session_name}', status='{self.status}')>"

class SqliteRawGameData(SqliteTestBase):
    """SQLite-compatible version of RawGameData model."""
    __tablename__ = 'raw_game_data'
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False, unique=True, index=True)
    season = Column(Integer, nullable=False)
    game_type = Column(String(20), nullable=False)
    game_url = Column(String(500), nullable=False)
    game_data = Column(JSON, nullable=False)  # JSON instead of JSONB for SQLite
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RawGameData(game_id='{self.game_id}', created_at='{self.created_at}')>"