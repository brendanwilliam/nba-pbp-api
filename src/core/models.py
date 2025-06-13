"""Database models for NBA play-by-play data."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Team(Base):
    """NBA team information."""
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    tricode = Column(String(3), unique=True, index=True, nullable=False)  # e.g., "BOS", "LAL"
    name = Column(String(100), nullable=False)  # e.g., "Boston Celtics"
    city = Column(String(50), nullable=False)  # e.g., "Boston"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Player(Base):
    """NBA player information."""
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    nba_id = Column(String(20), unique=True, index=True, nullable=False)  # NBA's player ID
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    jersey_number = Column(String(3))
    position = Column(String(10))
    team_id = Column(Integer, ForeignKey("teams.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    team = relationship("Team", back_populates="players")


class Game(Base):
    """NBA game information."""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    nba_game_id = Column(String(20), unique=True, index=True, nullable=False)  # NBA's game ID
    game_date = Column(Date, nullable=False, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(String(10), nullable=False, index=True)  # e.g., "2024-25"
    game_type = Column(String(20), nullable=False)  # "Regular Season", "Playoffs", etc.
    game_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])


class ScrapeQueue(Base):
    """Queue for tracking game scraping status."""
    __tablename__ = "scrape_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, in_progress, completed, failed
    attempts = Column(Integer, default=0)
    last_attempt = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    game = relationship("Game", back_populates="scrape_status")


class RawGameData(Base):
    """Raw JSON data scraped from NBA.com."""
    __tablename__ = "raw_game_data"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    raw_json = Column(JSON, nullable=False)  # Full JSON from __NEXT_DATA__
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    
    game = relationship("Game", back_populates="raw_data")


# Add back references
Team.players = relationship("Player", back_populates="team")
Game.scrape_status = relationship("ScrapeQueue", back_populates="game", uselist=False)
Game.raw_data = relationship("RawGameData", back_populates="game", uselist=False)