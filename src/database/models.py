from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
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


class Arena(Base):
    """Arena information for WNBA games"""
    __tablename__ = 'arena'
    
    id = Column(Integer, primary_key=True)
    arena_id = Column(Integer)
    arena_city = Column(String(100))
    arena_name = Column(String(200))
    arena_state = Column(String(50))
    arena_country = Column(String(50))
    arena_timezone = Column(String(50))
    arena_postal_code = Column(String(20))
    arena_street_address = Column(String(500))
    
    # Relationship
    games = relationship("Game", back_populates="arena")
    
    def __repr__(self):
        return f"<Arena(id={self.id}, arena_id={self.arena_id}, name='{self.arena_name}')>"


class Person(Base):
    """Player and official information"""
    __tablename__ = 'person'
    
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer)
    person_name = Column(String(200))
    person_name_i = Column(String(50))
    person_name_first = Column(String(100))
    person_name_family = Column(String(100))
    person_role = Column(String(20))
    
    # Relationships
    person_games = relationship("PersonGame", back_populates="person")
    plays = relationship("Play", back_populates="person")
    boxscores = relationship("Boxscore", back_populates="person")
    
    def __repr__(self):
        return f"<Person(id={self.id}, person_id={self.person_id}, name='{self.person_name}')>"


class Team(Base):
    """Team information for WNBA franchises"""
    __tablename__ = 'team'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer)
    team_city = Column(String(100))
    team_name = Column(String(100))
    team_tricode = Column(String(10))
    
    # Relationships
    team_games = relationship("TeamGame", back_populates="team")
    person_games = relationship("PersonGame", back_populates="team")
    plays = relationship("Play", back_populates="team")
    boxscores = relationship("Boxscore", back_populates="team")
    
    def __repr__(self):
        return f"<Team(id={self.id}, team_id={self.team_id}, tricode='{self.team_tricode}')>"


class Game(Base):
    """WNBA game information"""
    __tablename__ = 'game'
    
    game_id = Column(Integer, primary_key=True)
    game_code = Column(String(50))
    arena_id = Column(Integer)
    arena_internal_id = Column(Integer, ForeignKey('arena.id'))
    game_et = Column(DateTime)
    game_sellout = Column(Boolean)
    home_team_id = Column(Integer)
    home_team_wins = Column(Integer)
    home_team_losses = Column(Integer)
    away_team_id = Column(Integer)
    away_team_wins = Column(Integer)
    away_team_losses = Column(Integer)
    game_duration = Column(String(20))
    game_label = Column(String(100))
    game_attendance = Column(Integer)
    
    # Relationships
    arena = relationship("Arena", back_populates="games")
    team_games = relationship("TeamGame", back_populates="game")
    person_games = relationship("PersonGame", back_populates="game")
    plays = relationship("Play", back_populates="game")
    boxscores = relationship("Boxscore", back_populates="game")
    
    def __repr__(self):
        return f"<Game(id={self.game_id}, code='{self.game_code}')>"


class TeamGame(Base):
    """Junction table for teams and games"""
    __tablename__ = 'team_game'
    
    team_game_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.game_id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    
    # Relationships
    game = relationship("Game", back_populates="team_games")
    team = relationship("Team", back_populates="team_games")
    
    def __repr__(self):
        return f"<TeamGame(id={self.team_game_id}, game_id={self.game_id}, team_id={self.team_id})>"


class PersonGame(Base):
    """Junction table for persons and games"""
    __tablename__ = 'person_game'
    
    person_game_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.game_id'))
    person_id = Column(Integer)
    person_internal_id = Column(Integer, ForeignKey('person.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    
    # Relationships
    game = relationship("Game", back_populates="person_games")
    person = relationship("Person", back_populates="person_games")
    team = relationship("Team", back_populates="person_games")
    
    def __repr__(self):
        return f"<PersonGame(id={self.person_game_id}, game_id={self.game_id}, person_id={self.person_id})>"


class Play(Base):
    """Play-by-play data for WNBA games"""
    __tablename__ = 'play'
    
    play_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.game_id'))
    person_id = Column(Integer, nullable=True)
    person_internal_id = Column(Integer, ForeignKey('person.id'), nullable=True)
    team_id = Column(Integer, ForeignKey('team.id'))
    action_id = Column(Integer)
    action_type = Column(String(50))
    sub_type = Column(String(50))
    period = Column(Integer)
    clock = Column(String(20))
    x_legacy = Column(Integer)
    y_legacy = Column(Integer)
    location = Column(String(200))
    score_away = Column(String(10))
    score_home = Column(String(10))
    shot_value = Column(Integer)
    shot_result = Column(String(50))
    description = Column(String(500))
    is_field_goal = Column(Boolean)
    points_total = Column(Integer)
    action_number = Column(Integer)
    shot_distance = Column(Float)
    
    # Relationships
    game = relationship("Game", back_populates="plays")
    person = relationship("Person", back_populates="plays")
    team = relationship("Team", back_populates="plays")
    
    def __repr__(self):
        return f"<Play(id={self.play_id}, game_id={self.game_id}, action_type='{self.action_type}')>"


class Boxscore(Base):
    """Boxscore statistics for WNBA games"""
    __tablename__ = 'boxscore'
    
    boxscore_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.game_id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    person_id = Column(Integer, nullable=True)
    person_internal_id = Column(Integer, ForeignKey('person.id'), nullable=True)
    home_away_team = Column(String(1))  # 'h' or 'a'
    box_type = Column(String(20))  # 'starters', 'bench', or 'player'
    min = Column(String(10))
    pts = Column(Integer)
    reb = Column(Integer)
    ast = Column(Integer)
    stl = Column(Integer)
    blk = Column(Integer)
    pm = Column(Integer, nullable=True)
    fgm = Column(Integer)
    fga = Column(Integer)
    fgp = Column(Float)
    tpm = Column(Integer)  # 3pm - using tpm since 3pm starts with number
    tpa = Column(Integer)  # 3pa
    tpp = Column(Float)    # 3pp
    ftm = Column(Integer)
    fta = Column(Integer)
    ftp = Column(Float)
    to = Column(Integer)
    pf = Column(Integer)
    orebs = Column(Integer)
    drebs = Column(Integer)
    
    # Relationships
    game = relationship("Game", back_populates="boxscores")
    team = relationship("Team", back_populates="boxscores")
    person = relationship("Person", back_populates="boxscores")
    
    def __repr__(self):
        return f"<Boxscore(id={self.boxscore_id}, game_id={self.game_id}, box_type='{self.box_type}')>"