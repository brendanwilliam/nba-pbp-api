"""Database models for NBA play-by-play data."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Date, BigInteger
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
    game_id = Column(String(20), unique=True, nullable=False, index=True)  # NBA game ID
    game_url = Column(Text, nullable=False)
    raw_json = Column(JSON, nullable=False)  # Full JSON from __NEXT_DATA__
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    json_size = Column(Integer)  # Size in bytes
    processing_status = Column(String(20), default='raw', index=True)  # raw, processed, failed


class SubstitutionEvent(Base):
    """Individual substitution events during games."""
    __tablename__ = "substitution_events"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(20), nullable=False, index=True)
    action_number = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)
    clock_time = Column(String(20), nullable=False)
    seconds_elapsed = Column(Integer, nullable=False)
    team_id = Column(BigInteger, nullable=False, index=True)
    player_out_id = Column(BigInteger, nullable=False, index=True)
    player_out_name = Column(String(100), nullable=False)
    player_in_id = Column(BigInteger, nullable=False, index=True)
    player_in_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PlayEvent(Base):
    """Play-by-play events during games."""
    __tablename__ = "play_events"
    
    event_id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(20), nullable=False, index=True)
    
    # Timing
    period = Column(Integer, nullable=False)
    time_remaining = Column(String(20))  # format: PT12M34.56S
    time_elapsed_seconds = Column(Integer)  # calculated seconds from game start
    
    # Event details
    event_type = Column(String(50), nullable=False)
    event_action_type = Column(String(50))
    event_sub_type = Column(String(50))
    description = Column(Text)
    
    # Score context
    home_score = Column(Integer)
    away_score = Column(Integer)
    score_margin = Column(Integer)  # home_score - away_score
    
    # Player and team
    player_id = Column(Integer)
    team_id = Column(Integer)
    
    # Shot details
    shot_distance = Column(String(20))  # keeping as string like in enhanced_schema.sql
    shot_made = Column(Boolean)
    shot_type = Column(String(50))
    shot_zone = Column(String(50))
    shot_x = Column(String(20))  # keeping as string like in enhanced_schema.sql
    shot_y = Column(String(20))  # keeping as string like in enhanced_schema.sql
    
    # Assists
    assist_player_id = Column(Integer)
    
    # Event order
    event_order = Column(Integer)
    
    # Possession tracking
    possession_change = Column(Boolean, default=False)
    possession_id = Column(Integer, ForeignKey("possession_events.possession_id"), nullable=True, index=True)
    
    # Video/highlights
    video_available = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    possession = relationship("PossessionEvent", back_populates="play_events")


class PossessionEvent(Base):
    """Possession events during games - each possession by a team."""
    __tablename__ = "possession_events"
    
    possession_id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(20), nullable=False, index=True)
    possession_number = Column(Integer, nullable=False)
    team_id = Column(Integer, nullable=False, index=True)
    
    # Start timing
    start_period = Column(Integer, nullable=False)
    start_time_remaining = Column(String(20))
    start_seconds_elapsed = Column(Integer)
    
    # End timing
    end_period = Column(Integer)
    end_time_remaining = Column(String(20))
    end_seconds_elapsed = Column(Integer)
    
    # Outcome
    possession_outcome = Column(String(50))  # made_shot, turnover, defensive_rebound, etc.
    points_scored = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    play_events = relationship("PlayEvent", back_populates="possession")
    play_possession_events = relationship("PlayPossessionEvent", back_populates="possession")


class PlayPossessionEvent(Base):
    """Junction table linking plays to possessions (many-to-many)."""
    __tablename__ = "play_possession_events"
    
    play_possession_events_id = Column(Integer, primary_key=True, index=True)
    possession_id = Column(Integer, ForeignKey("possession_events.possession_id", ondelete="CASCADE"), nullable=False)
    play_id = Column(Integer, ForeignKey("play_events.event_id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    possession = relationship("PossessionEvent", back_populates="play_possession_events")
    play_event = relationship("PlayEvent")


class LineupState(Base):
    """Lineup state at specific moments during games."""
    __tablename__ = "lineup_states"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(20), nullable=False, index=True)
    period = Column(Integer, nullable=False)
    clock_time = Column(String(20), nullable=False)
    seconds_elapsed = Column(Integer, nullable=False, index=True)
    team_id = Column(BigInteger, nullable=False, index=True)
    player_1_id = Column(BigInteger, nullable=False)
    player_2_id = Column(BigInteger, nullable=False)
    player_3_id = Column(BigInteger, nullable=False)
    player_4_id = Column(BigInteger, nullable=False)
    player_5_id = Column(BigInteger, nullable=False)
    lineup_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Add back references
Team.players = relationship("Player", back_populates="team")
Game.scrape_status = relationship("ScrapeQueue", back_populates="game", uselist=False)
Game.raw_data = relationship("RawGameData", back_populates="game", uselist=False)