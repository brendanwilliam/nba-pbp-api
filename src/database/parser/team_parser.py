"""
Team Parser Module

Handles extraction of team statistics and information from NBA JSON data.
This includes team game statistics, team context, and team performance data.
"""

from typing import Dict, Any, List


def extract_team_stats(raw_json: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
    """
    Extract team game statistics from raw NBA JSON data.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        game_id: NBA game identifier
        
    Returns:
        List of dictionaries containing team statistics (home and away)
        
    Keys in each stats dictionary:
        - game_id: Game identifier
        - team_id: Team identifier
        - is_home_team: Boolean indicating if this is the home team
        - stat_type: Type of stats ('team' for overall team stats)
        - wins: Team wins at time of game
        - losses: Team losses at time of game
        - in_bonus: Boolean bonus situation indicator
        - timeouts_remaining: Timeouts remaining
        - seed: Playoff seed
        - minutes: Team minutes in seconds
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
        - plus_minus_points: Plus/minus points
        - points_fast_break: Fast break points
        - points_in_paint: Points in the paint
        - points_second_chance: Second chance points
    """
    props = raw_json.get('props', {})
    page_props = props.get('pageProps', {})
    game = page_props.get('game', {})
    
    team_stats = []
    
    for is_home, team_key in [(True, 'homeTeam'), (False, 'awayTeam')]:
        team = game.get(team_key, {})
        statistics = team.get('statistics', {})
        
        # Convert in_bonus to boolean
        in_bonus_value = team.get('inBonus')
        if isinstance(in_bonus_value, str):
            in_bonus = in_bonus_value.lower() in ('true', '1', 'yes') if in_bonus_value else False
        else:
            in_bonus = bool(in_bonus_value) if in_bonus_value is not None else False
        
        # Convert team minutes from "MM:SS" format to total seconds
        team_minutes_str = statistics.get('minutes')
        team_minutes = None
        if team_minutes_str and isinstance(team_minutes_str, str):
            try:
                if ':' in team_minutes_str:
                    parts = team_minutes_str.split(':')
                    team_minutes = int(parts[0]) * 60 + int(parts[1])  # Convert to seconds
                else:
                    team_minutes = int(float(team_minutes_str) * 60)  # Assume decimal minutes
            except (ValueError, IndexError):
                team_minutes = None
        
        team_stats.append({
            'game_id': game_id,
            'team_id': team.get('teamId'),
            'is_home_team': is_home,
            'stat_type': 'team',
            'wins': team.get('wins'),
            'losses': team.get('losses'),
            'in_bonus': in_bonus,
            'timeouts_remaining': team.get('timeoutsRemaining'),
            'seed': team.get('seed'),
            'minutes': team_minutes,
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
            'points': team.get('score'),
            'plus_minus_points': statistics.get('plusMinusPoints'),
            'points_fast_break': statistics.get('pointsFastBreak'),
            'points_in_paint': statistics.get('pointsInPaint'),
            'points_second_chance': statistics.get('pointsSecondChance')
        })
    
    return team_stats