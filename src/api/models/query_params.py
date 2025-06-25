"""
Query parameter models for API endpoints.
Defines the structure and validation for query parameters across all endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union, Literal, Tuple
from datetime import date


class BaseQueryParams(BaseModel):
    """Base query parameters shared across all endpoints"""
    season: Optional[str] = Field(None, description="Season filter: 'latest', '2023-24', 'all', or comma-separated list")
    game_id: Optional[str] = Field(None, description="Game filter: 'latest', specific ID, 'all', or comma-separated list")
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    filters: Optional[Dict[str, Any]] = Field(None, description="Dynamic column filters")
    fields: Optional[List[str]] = Field(None, description="Specific fields to return")
    sort: Optional[str] = Field(None, description="Sort specification: 'field1,-field2'")
    limit: int = Field(100, le=10000)
    offset: int = Field(0, ge=0)
    about: bool = Field(False, description="Include statistical summary")
    correlation: Optional[List[str]] = Field(None, description="Fields for correlation analysis")
    regression: Optional[Dict[str, str]] = Field(None, description="Regression specification")


class PlayerStatsQuery(BaseQueryParams):
    """Query parameters for player statistics endpoint"""
    player_id: Optional[Union[int, List[int]]] = None
    player_name: Optional[str] = None
    team_id: Optional[int] = None
    home_away: Optional[Literal["home", "away", "all"]] = None
    opponent_team_id: Optional[int] = None
    game_type: Optional[Literal["regular", "playoff", "all"]] = None


class TeamStatsQuery(BaseQueryParams):
    """Query parameters for team statistics endpoint"""
    team_id: Optional[Union[int, List[int]]] = None
    team_name: Optional[str] = None
    home_away: Optional[Literal["home", "away", "all"]] = None
    opponent_team_id: Optional[int] = None
    win_loss: Optional[Literal["win", "loss", "all"]] = None
    game_type: Optional[Literal["regular", "playoff", "all"]] = None


class LineupStatsQuery(BaseQueryParams):
    """Query parameters for lineup statistics endpoint"""
    player_ids: Optional[List[int]] = Field(None, description="Players that must be in lineup")
    exclude_player_ids: Optional[List[int]] = Field(None, description="Players that must NOT be in lineup")
    lineup_size: Optional[int] = Field(None, ge=1, le=5)
    team_id: Optional[int] = None
    min_minutes: Optional[float] = Field(None, description="Minimum minutes played together")
    compare_mode: Optional[Literal["on", "off", "both"]] = None


class ShotChartQuery(BaseModel):
    """Query parameters for shot chart endpoint"""
    # Entity selection (at least one required)
    player_id: Optional[int] = None
    team_id: Optional[int] = None
    game_id: Optional[str] = None
    
    # Time filters
    season: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    
    # Shot filters
    shot_type: Optional[List[str]] = Field(None, description="2PT, 3PT, etc.")
    shot_zone: Optional[List[str]] = None
    period: Optional[List[int]] = None
    time_remaining: Optional[str] = Field(None, description="e.g., '<2:00' for last 2 minutes")
    
    # Context filters
    clutch_only: bool = Field(False, description="Only clutch situations")
    made_only: bool = False
    missed_only: bool = False


class PlayByPlayQuery(BaseModel):
    """Query parameters for play-by-play endpoint"""
    # Game selection
    game_id: Optional[Union[str, List[str]]] = None
    
    # Time filters
    season: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    period: Optional[List[int]] = None
    time_range: Optional[Dict[str, str]] = Field(None, description="{'start': '10:00', 'end': '8:00'}")
    
    # Event filters
    event_types: Optional[List[str]] = None
    player_id: Optional[int] = None
    team_id: Optional[int] = None
    
    # Situation filters
    score_margin: Optional[Dict[str, int]] = Field(None, description="{'min': -5, 'max': 5} for close games")
    shot_clock: Optional[Dict[str, int]] = None
    
    # Output options
    include_lineup: bool = Field(False, description="Include current lineup for each play")
    fields: Optional[List[str]] = None
    sort: Optional[str] = Field("-game_date,period,time_elapsed")
    limit: int = Field(1000, le=50000)
    offset: int = Field(0, ge=0)