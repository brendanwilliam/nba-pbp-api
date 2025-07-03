"""
Play Parser Module

Handles extraction of play-by-play events from NBA JSON data.
This includes event processing, timing calculations, and play context.
"""

from typing import Dict, Any, List, Optional


def extract_play_events(raw_json: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
    """
    Extract play-by-play events with enhanced data processing.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        game_id: NBA game identifier
        
    Returns:
        List of dictionaries containing play-by-play events
        
    Keys in each event dictionary:
        - game_id: Game identifier
        - period: Period number
        - time_remaining: Time remaining in period (NBA format)
        - time_elapsed_seconds: Calculated elapsed seconds from game start
        - event_type: Type of event (shot, rebound, etc.)
        - event_action_type: Action type within event
        - event_sub_type: Sub-type of event
        - description: Event description
        - home_score: Home team score at this event
        - away_score: Away team score at this event
        - score_margin: Score margin (home - away)
        - player_id: Player involved in event
        - team_id: Team involved in event
        - shot_distance: Shot distance (for shots)
        - shot_made: Boolean shot made indicator
        - shot_type: Type of shot (2PT, 3PT)
        - shot_zone: Shot zone description
        - shot_x: Shot X coordinate
        - shot_y: Shot Y coordinate
        - assist_player_id: Assisting player ID
        - event_order: Event sequence number
        - possession_change: Boolean possession change indicator
        - video_available: Boolean video availability
    """
    props = raw_json.get('props', {})
    page_props = props.get('pageProps', {})
    
    # Try main playByPlay location first
    play_by_play = page_props.get('playByPlay', {})
    actions = play_by_play.get('actions', [])
    
    # Fallback to game.actions
    if not actions:
        game = page_props.get('game', {})
        actions = game.get('actions', [])
    
    events = []
    
    for action in actions:
        # Convert score strings to integers
        home_score = action.get('scoreHome')
        away_score = action.get('scoreAway')
        try:
            home_score = int(home_score) if home_score and home_score != '' else None
        except (ValueError, TypeError):
            home_score = None
        try:
            away_score = int(away_score) if away_score and away_score != '' else None
        except (ValueError, TypeError):
            away_score = None
        
        # Calculate score margin
        score_margin = None
        if home_score is not None and away_score is not None:
            score_margin = home_score - away_score
        
        # Extract shot coordinates from xLegacy/yLegacy
        shot_x = action.get('xLegacy')
        shot_y = action.get('yLegacy')
        
        # Determine shot type from shotValue (2 or 3 points)
        shot_type = None
        shot_value = action.get('shotValue')
        if shot_value == 2:
            shot_type = '2PT'
        elif shot_value == 3:
            shot_type = '3PT'
        
        # Calculate time elapsed seconds from clock
        time_elapsed_seconds = None
        clock = action.get('clock')
        period = action.get('period', 1)
        if clock and isinstance(clock, str):
            time_elapsed_seconds = _convert_clock_to_elapsed_seconds(clock, period)
        
        # Get event sub type from subType field
        event_sub_type = action.get('subType')
        
        # Determine possession change events
        possession_change = _is_possession_change_event(action)
        
        # Special handling for rebounds - check if it's a defensive rebound
        if action.get('actionType', '').lower() == 'rebound':
            # Look back for the most recent shot attempt (could be separated by blocks)
            last_shot_team = None
            
            # Find current action index in the actions array
            current_idx = None
            for idx, a in enumerate(actions):
                if a.get('actionNumber') == action.get('actionNumber'):
                    current_idx = idx
                    break
            
            if current_idx is not None:
                # Search backwards through recent actions (up to 5 events)
                for j in range(current_idx-1, max(0, current_idx-6), -1):
                    prev_action = actions[j]
                    prev_type = prev_action.get('actionType', '').lower()
                    
                    # Check for missed shots or missed free throws
                    if prev_type == 'missed shot':
                        last_shot_team = prev_action.get('teamTricode')
                        break
                    elif prev_type == 'free throw':
                        if 'miss' in prev_action.get('description', '').lower():
                            last_shot_team = prev_action.get('teamTricode')
                            break
            
            # If we found a recent shot and teams are different, it's a defensive rebound
            if last_shot_team and action.get('teamTricode') and action.get('teamTricode') != last_shot_team:
                possession_change = True
        
        events.append({
            'game_id': game_id,
            'period': action.get('period'),
            'time_remaining': action.get('clock'),
            'time_elapsed_seconds': time_elapsed_seconds,
            'event_type': action.get('actionType'),
            'event_action_type': action.get('subType'),
            'event_sub_type': event_sub_type,
            'description': action.get('description'),
            'home_score': home_score,
            'away_score': away_score,
            'score_margin': score_margin,
            'player_id': action.get('personId'),
            'team_id': action.get('teamId'),
            'shot_distance': action.get('shotDistance'),
            'shot_made': action.get('shotResult') == 'Made' if action.get('shotResult') else None,
            'shot_type': shot_type,
            'shot_zone': action.get('shotZone'),
            'shot_x': shot_x,
            'shot_y': shot_y,
            'assist_player_id': action.get('assistPersonId'),
            'event_order': action.get('actionNumber'),
            'possession_change': possession_change,
            'video_available': action.get('isVideoAvailable', False),
            # Store team tricode for later processing if needed
            '_team_tricode': action.get('teamTricode')
        })
    
    # Apply score backfill logic
    events = _backfill_scores(events)
    
    return events


def _convert_clock_to_elapsed_seconds(clock: str, period: int) -> Optional[int]:
    """
    Convert NBA clock format (PT12M34.56S) to elapsed seconds from game start.
    
    Args:
        clock: NBA clock format string
        period: Period number
        
    Returns:
        Elapsed seconds from game start, or None if conversion fails
    """
    try:
        # Remove PT prefix and parse
        if clock.startswith('PT'):
            clock = clock[2:]
        
        # Extract minutes and seconds
        if 'M' in clock and 'S' in clock:
            parts = clock.replace('S', '').split('M')
            minutes_remaining = int(parts[0])
            seconds_remaining = float(parts[1])
            
            # Convert to total seconds remaining in period
            total_remaining = minutes_remaining * 60 + seconds_remaining
            
            # Calculate elapsed seconds from game start
            # Each period is 12 minutes (720 seconds) for regular periods
            period_length = 720  # 12 minutes in seconds
            overtime_length = 300  # 5 minutes in seconds for OT
            
            elapsed_in_game = 0
            
            # Add completed periods
            for p in range(1, period):
                if p <= 4:
                    elapsed_in_game += period_length
                else:
                    elapsed_in_game += overtime_length
            
            # Add elapsed time in current period
            if period <= 4:
                elapsed_in_period = period_length - total_remaining
            else:
                elapsed_in_period = overtime_length - total_remaining
            
            elapsed_in_game += elapsed_in_period
            
            return int(elapsed_in_game)
        
    except (ValueError, IndexError, TypeError):
        pass
    
    return None


def _is_possession_change_event(action: Dict[str, Any]) -> bool:
    """
    Determine if an event represents a change of possession.
    
    Args:
        action: Individual play-by-play action
        
    Returns:
        Boolean indicating if this event changes possession
    """
    action_type = action.get('actionType', '').lower()
    
    # Made field goals change possession
    if action_type == 'made shot':
        return True
    
    # Turnovers change possession (includes steals and fouls that cause turnovers)
    if action_type == 'turnover':
        return True
    
    # Defensive rebounds change possession
    # Note: We'll need to check if previous action was a missed shot and team changed
    # This requires access to the previous action, which we'll handle in extract_play_events
    if action_type == 'rebound':
        # For now, just return False - we'll handle DREB detection in extract_play_events
        return False
    
    return False


def _backfill_scores(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Backfill missing scores for events that don't have score changes.
    
    Args:
        events: List of play-by-play events
        
    Returns:
        List of events with backfilled scores
    """
    if not events:
        return events
    
    # Sort events by period and then by event order to ensure chronological processing
    sorted_events = sorted(events, key=lambda x: (x.get('period', 0), x.get('event_order', 0)))
    
    current_home_score = 0
    current_away_score = 0
    
    for event in sorted_events:
        # If event has scores, update our running totals
        if event.get('home_score') is not None and event.get('away_score') is not None:
            current_home_score = event['home_score']
            current_away_score = event['away_score']
            
            # Ensure score_margin is calculated
            if event.get('score_margin') is None:
                event['score_margin'] = current_home_score - current_away_score
        else:
            # Backfill missing scores with current running totals
            event['home_score'] = current_home_score
            event['away_score'] = current_away_score
            event['score_margin'] = current_home_score - current_away_score
    
    return sorted_events