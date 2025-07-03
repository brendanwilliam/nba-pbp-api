"""
NBA Data Parser Module

This module contains data extraction and parsing functions for converting raw NBA JSON data
into structured database records. The module is designed to be modular and maintainable,
with separate components for different types of NBA data.

Components:
- game_parser: Basic game information and metadata
- arena_parser: Arena and venue information  
- player_parser: Player data and statistics
- team_parser: Team statistics and game data
- play_parser: Play-by-play event processing
- analytics_parser: Advanced analytics like lineups and possessions

Usage:
    from src.database.parser import game_parser, player_parser
    
    game_info = game_parser.extract_game_basic_info(raw_json)
    player_stats = player_parser.extract_player_stats(raw_json, game_id)
"""

from .game_parser import *
from .arena_parser import *
from .player_parser import *
from .team_parser import *
from .play_parser import *
from .analytics_parser import *
from .database_operations import DatabaseOperations

__version__ = "1.0.0"
__author__ = "NBA PBP API Team"