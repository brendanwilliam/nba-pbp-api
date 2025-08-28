from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

Base = declarative_base()

class DatabaseVersion(Base):
    """Track database schema versions and migrations"""
    __tablename__ = 'database_versions'
    
    id = Column(Integer, primary_key=True)
    version = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    applied_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<DatabaseVersion(version='{self.version}', applied_at='{self.applied_at}')>"

class ScrapingSession(Base):
    """Track scraping sessions for WNBA games"""
    __tablename__ = 'scraping_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(100), nullable=False)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    status = Column(String(20), default='running')  # running, completed, failed
    games_scraped = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<ScrapingSession(name='{self.session_name}', status='{self.status}')>"

class RawGameData(Base):
    """Store raw WNBA game data from scraping"""
    __tablename__ = 'raw_game_data'
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False, unique=True, index=True)
    season = Column(Integer, nullable=False)
    game_type = Column(String(20), nullable=False)
    game_url = Column(String(500), nullable=False)
    game_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RawGameData(game_id='{self.game_id}', created_at='{self.created_at}')>"