"""
Analytics Parser Module

Handles extraction of advanced analytics data from NBA JSON data.
This includes lineup tracking, possession analysis, and substitution events.
"""

from typing import Dict, Any, List, Tuple, Optional
import sys
from pathlib import Path

# Add src to path for analytics imports
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from analytics.lineup_tracker import LineupTracker
    from analytics.possession_tracker import PossessionTracker
except ImportError:
    # Handle gracefully if analytics modules aren't available
    LineupTracker = None
    PossessionTracker = None


def extract_lineup_tracking_data(raw_json: Dict[str, Any], game_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract lineup states and substitution events using LineupTracker.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        game_id: NBA game identifier
        
    Returns:
        Tuple of (lineup_states, substitution_events)
        
    Lineup states contain:
        - game_id: Game identifier
        - period: Period number
        - clock: Game clock time
        - seconds_elapsed: Elapsed seconds from game start
        - home_team_id: Home team ID
        - away_team_id: Away team ID
        - home_players: List of home team player IDs on court
        - away_players: List of away team player IDs on court
        
    Substitution events contain:
        - game_id: Game identifier
        - event_id: Event/action number
        - period: Period number
        - clock: Game clock time
        - seconds_elapsed: Elapsed seconds from game start
        - team_id: Team making substitution
        - player_in_id: Player entering game
        - player_out_id: Player leaving game
        - player_in_name: Player entering name
        - player_out_name: Player leaving name
        - event_description: Event description
    """
    try:
        if LineupTracker is None:
            raise ImportError("LineupTracker not available")
            
        # Initialize the lineup tracker with the game data
        tracker = LineupTracker(raw_json)
        
        # Build the lineup timeline
        timeline = tracker.build_lineup_timeline()
        
        # Convert LineupState objects to dictionaries for database insertion
        lineup_states = []
        for state in timeline:
            lineup_states.append({
                'game_id': state.game_id,
                'period': state.period,
                'clock': state.clock,
                'seconds_elapsed': state.seconds_elapsed,
                'home_team_id': state.home_team_id,
                'away_team_id': state.away_team_id,
                'home_players': state.home_players,
                'away_players': state.away_players
            })
        
        # Extract substitution events from the tracker
        substitutions = tracker.parse_substitution_events()
        substitution_events = []
        for sub in substitutions:
            substitution_events.append({
                'game_id': game_id,
                'event_id': sub.action_number,
                'period': sub.period,
                'clock': sub.clock,
                'seconds_elapsed': sub.seconds_elapsed,
                'team_id': sub.team_id,
                'player_in_id': sub.player_in_id,
                'player_out_id': sub.player_out_id,
                'player_in_name': sub.player_in_name,
                'player_out_name': sub.player_out_name,
                'event_description': sub.description
            })
        
        return lineup_states, substitution_events
        
    except Exception as e:
        print(f"    ⚠️ Failed to extract lineup tracking data: {str(e)[:150]}...")
        return [], []


def extract_possession_data(raw_json: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
    """
    Extract possession events using PossessionTracker.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        game_id: NBA game identifier
        
    Returns:
        List of dictionaries containing possession data
        
    Keys in each possession dictionary:
        - game_id: Game identifier
        - possession_number: Sequential possession number
        - team_id: Team that had possession
        - start_period: Period when possession started
        - start_time_remaining: Time remaining when possession started
        - start_seconds_elapsed: Elapsed seconds when possession started
        - end_period: Period when possession ended
        - end_time_remaining: Time remaining when possession ended
        - end_seconds_elapsed: Elapsed seconds when possession ended
        - possession_outcome: How possession ended
        - points_scored: Points scored during possession
        - play_ids: List of play event IDs in this possession
    """
    try:
        if PossessionTracker is None:
            raise ImportError("PossessionTracker not available")
            
        # Extract basic game info to get team IDs
        from .game_parser import extract_game_basic_info
        game_info = extract_game_basic_info(raw_json)
        if not game_info:
            return []
        
        home_team_id = game_info.get('home_team_id')
        away_team_id = game_info.get('away_team_id')
        
        if not home_team_id or not away_team_id:
            print(f"    ⚠️ Missing team IDs for possession tracking")
            return []
        
        # Extract play events for possession analysis
        from .play_parser import extract_play_events
        play_events = extract_play_events(raw_json, game_id)
        if not play_events:
            return []
        
        # Initialize possession tracker
        tracker = PossessionTracker(game_id, home_team_id, away_team_id)
        
        # Process events to generate possessions
        possessions = tracker.process_play_events(play_events)
        
        # Convert to database format
        possession_data = []
        for possession in possessions:
            possession_data.append({
                'game_id': possession.game_id,
                'possession_number': possession.possession_number,
                'team_id': possession.team_id,
                'start_period': possession.start_period,
                'start_time_remaining': possession.start_time_remaining,
                'start_seconds_elapsed': possession.start_seconds_elapsed,
                'end_period': possession.end_period,
                'end_time_remaining': possession.end_time_remaining,
                'end_seconds_elapsed': possession.end_seconds_elapsed,
                'possession_outcome': possession.possession_outcome,
                'points_scored': possession.points_scored,
                'play_ids': possession.play_ids
            })
        
        return possession_data
        
    except Exception as e:
        print(f"    ⚠️ Failed to extract possession data: {str(e)[:150]}...")
        return []