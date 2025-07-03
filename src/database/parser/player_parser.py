"""
Player Parser Module

Handles extraction of player information and statistics from NBA JSON data.
This includes player rosters, game statistics, and player identification.
"""

from typing import Dict, Any, List, Optional


def extract_all_players(raw_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all player information from game data for player creation.
    
    This function collects player data from team rosters and play-by-play events
    to ensure we have comprehensive player information for database population.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        
    Returns:
        List of dictionaries containing player information
        
    Keys in each player dictionary:
        - player_id: NBA player identifier
        - name: Full player name
        - first_name: Player's first name
        - last_name: Player's last name (family name)
        - jersey_number: Jersey number for this game
        - position: Player position
        - team_id: Team NBA ID
    """
    props = raw_json.get('props', {})
    page_props = props.get('pageProps', {})
    game = page_props.get('game', {})
    
    all_players = []
    
    # Extract players from team rosters
    for team_key in ['homeTeam', 'awayTeam']:
        team = game.get(team_key, {})
        team_id = team.get('teamId')
        players = team.get('players', [])
        
        for player in players:
            all_players.append({
                'player_id': player.get('personId'),
                'name': player.get('name'),
                'first_name': player.get('firstName'),
                'last_name': player.get('familyName'),
                'jersey_number': player.get('jerseyNum'),
                'position': player.get('position'),
                'team_id': team_id
            })
    
    # Also extract players from play-by-play events
    play_by_play = page_props.get('playByPlay', {})
    actions = play_by_play.get('actions', [])
    
    # Fallback to game.actions
    if not actions:
        actions = game.get('actions', [])
    
    # Track unique player IDs from events
    event_players = {}
    for action in actions:
        # Main player
        if action.get('personId'):
            event_players[action['personId']] = {
                'player_id': action.get('personId'),
                'name': action.get('playerName', ''),
                'team_id': action.get('teamId')
            }
        
        # Assist player
        if action.get('assistPersonId'):
            event_players[action['assistPersonId']] = {
                'player_id': action.get('assistPersonId'),
                'name': action.get('assistPlayerName', ''),
                'team_id': action.get('teamId')
            }
    
    # Add event players to the list
    for player_data in event_players.values():
        if player_data['player_id'] and not any(p.get('player_id') == player_data['player_id'] for p in all_players):
            all_players.append(player_data)
    
    return [p for p in all_players if p.get('player_id')]


def extract_player_stats(raw_json: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
    """
    Extract player game statistics from raw NBA JSON data.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        game_id: NBA game identifier
        
    Returns:
        List of dictionaries containing player statistics
        
    Keys in each stats dictionary:
        - game_id: Game identifier
        - player_id: Player identifier
        - team_id: Team identifier
        - jersey_number: Jersey number
        - position: Player position
        - starter: Boolean starter indicator
        - active: Boolean active indicator
        - dnp_reason: Did not play reason
        - minutes_played: Minutes played in seconds
        - field_goals_made: Field goals made
        - field_goals_attempted: Field goals attempted
        - field_goals_percentage: Field goal percentage
        - three_pointers_made: Three pointers made
        - three_pointers_attempted: Three pointers attempted
        - three_pointers_percentage: Three point percentage
        - free_throws_made: Free throws made
        - free_throws_attempted: Free throws attempted
        - free_throws_percentage: Free throw percentage
        - rebounds_offensive: Offensive rebounds
        - rebounds_defensive: Defensive rebounds
        - rebounds_total: Total rebounds
        - assists: Assists
        - steals: Steals
        - blocks: Blocks
        - turnovers: Turnovers
        - fouls_personal: Personal fouls
        - points: Points scored
        - plus_minus: Plus/minus statistic
    """
    props = raw_json.get('props', {})
    page_props = props.get('pageProps', {})
    game = page_props.get('game', {})
    
    player_stats = []
    
    for team_key in ['homeTeam', 'awayTeam']:
        team = game.get(team_key, {})
        team_id = team.get('teamId')
        players = team.get('players', [])
        
        for player in players:
            statistics = player.get('statistics', {})
            
            # Convert minutes from "MM:SS" format to total seconds
            minutes_str = statistics.get('minutes')
            minutes_played = None
            if minutes_str and isinstance(minutes_str, str):
                try:
                    if ':' in minutes_str:
                        parts = minutes_str.split(':')
                        minutes_played = int(parts[0]) * 60 + int(parts[1])  # Convert to seconds
                    else:
                        minutes_played = int(float(minutes_str) * 60)  # Assume decimal minutes
                except (ValueError, IndexError):
                    minutes_played = None
            
            player_stats.append({
                'game_id': game_id,
                'player_id': player.get('personId'),
                'team_id': team_id,
                'jersey_number': player.get('jerseyNum'),
                'position': player.get('position'),
                'starter': player.get('starter', False),
                'active': player.get('played', True),
                'dnp_reason': player.get('notPlayingReason'),
                'minutes_played': minutes_played,
                'field_goals_made': statistics.get('fieldGoalsMade'),
                'field_goals_attempted': statistics.get('fieldGoalsAttempted'),
                'field_goals_percentage': statistics.get('fieldGoalsPercentage'),
                'three_pointers_made': statistics.get('threePointersMade'),
                'three_pointers_attempted': statistics.get('threePointersAttempted'),
                'three_pointers_percentage': statistics.get('threePointersPercentage'),
                'free_throws_made': statistics.get('freeThrowsMade'),
                'free_throws_attempted': statistics.get('freeThrowsAttempted'),
                'free_throws_percentage': statistics.get('freeThrowsPercentage'),
                'rebounds_offensive': statistics.get('reboundsOffensive'),
                'rebounds_defensive': statistics.get('reboundsDefensive'),
                'rebounds_total': statistics.get('reboundsTotal'),
                'assists': statistics.get('assists'),
                'steals': statistics.get('steals'),
                'blocks': statistics.get('blocks'),
                'turnovers': statistics.get('turnovers'),
                'fouls_personal': statistics.get('foulsPersonal'),
                'points': statistics.get('points'),
                'plus_minus': statistics.get('plusMinus')
            })
    
    return player_stats