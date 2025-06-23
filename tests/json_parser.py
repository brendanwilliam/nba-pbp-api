"""JSON Game Parser module for test utilities."""

import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.database import SessionLocal
from sqlalchemy import text


class JSONGameParser:
    """Parser for NBA game JSON data to extract structured information."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def get_sample_game(self, game_id: str = None) -> tuple[str, Dict[str, Any]]:
        """Get a sample game's raw JSON data."""
        if game_id:
            query = text("SELECT game_id, raw_json FROM raw_game_data WHERE game_id = :game_id")
            result = self.session.execute(query, {"game_id": game_id}).fetchone()
        else:
            query = text("SELECT game_id, raw_json FROM raw_game_data LIMIT 1")
            result = self.session.execute(query).fetchone()
        
        if not result:
            raise ValueError(f"No game found with ID: {game_id}")
        
        return result[0], result[1]
    
    def parse_game_basic_info(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic game information."""
        props = game_data.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        return {
            'game_id': game.get('gameId'),
            'game_code': game.get('gameCode'), 
            'game_status': game.get('gameStatus'),
            'game_status_text': game.get('gameStatusText'),
            'season': game.get('season'),
            'game_date': game.get('gameDate'),
            'game_time_utc': game.get('gameTimeUTC'),
            'game_time_et': game.get('gameTimeET'),
            'period': game.get('period'),
            'game_clock': game.get('gameClock'),
            'attendance': game.get('attendance'),
            'sellout': game.get('sellout')
        }
    
    def parse_teams(self, game_data: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Extract team information."""
        props = game_data.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        home_team = game.get('homeTeam', {})
        away_team = game.get('awayTeam', {})
        
        def extract_team_info(team_data):
            return {
                'team_id': team_data.get('teamId'),
                'team_code': team_data.get('teamCode'),
                'team_name': team_data.get('teamName'),
                'team_city': team_data.get('teamCity'),
                'team_slug': team_data.get('teamSlug'),
                'team_tricode': team_data.get('teamTricode'),
                'wins': team_data.get('wins'),
                'losses': team_data.get('losses'),
                'score': team_data.get('score'),
                'in_bonus': team_data.get('inBonus'),
                'timeouts_remaining': team_data.get('timeoutsRemaining'),
                'seed': team_data.get('seed')
            }
        
        return extract_team_info(home_team), extract_team_info(away_team)
    
    def parse_periods(self, game_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract period scores."""
        props = game_data.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        periods = []
        
        # Check if we have period data - it might be in different formats
        period_data = game.get('period')
        if isinstance(period_data, list):
            # Period data is a list of quarters/overtimes
            for i, quarter in enumerate(period_data, 1):
                periods.append({
                    'period_number': i,
                    'period_type': 'quarter' if i <= 4 else 'overtime',
                    'home_score': quarter.get('homeTeam', {}).get('score'),
                    'away_score': quarter.get('awayTeam', {}).get('score')
                })
        elif isinstance(period_data, int):
            # Period data is just the current period number
            # Look for period scores elsewhere in the data
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            
            # Check if there are period scores in the team data
            home_periods = home_team.get('periods', [])
            away_periods = away_team.get('periods', [])
            
            if home_periods and away_periods:
                for i, (home_period, away_period) in enumerate(zip(home_periods, away_periods), 1):
                    periods.append({
                        'period_number': i,
                        'period_type': 'quarter' if i <= 4 else 'overtime',
                        'home_score': home_period.get('score', 0),
                        'away_score': away_period.get('score', 0)
                    })
        
        return periods
    
    def parse_arena(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract arena information."""
        props = game_data.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        arena = game.get('arena', {})
        
        return {
            'arena_name': arena.get('arenaName'),
            'arena_city': arena.get('arenaCity'),
            'arena_state': arena.get('arenaState'),
            'arena_country': arena.get('arenaCountry'),
            'arena_timezone': arena.get('arenaTimezone')
        }
    
    def count_play_events(self, game_data: Dict[str, Any]) -> int:
        """Count play-by-play events."""
        props = game_data.get('props', {})
        page_props = props.get('pageProps', {})
        
        # First try the main playByPlay location
        play_by_play = page_props.get('playByPlay', {})
        actions = play_by_play.get('actions', [])
        
        # Fallback to game.actions if playByPlay is empty
        if not actions:
            game = page_props.get('game', {})
            actions = game.get('actions', [])
        
        return len(actions)
    
    def sample_play_events(self, game_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample play-by-play events."""
        props = game_data.get('props', {})
        page_props = props.get('pageProps', {})
        
        # First try the main playByPlay location
        play_by_play = page_props.get('playByPlay', {})
        actions = play_by_play.get('actions', [])
        
        # Fallback to game.actions if playByPlay is empty
        if not actions:
            game = page_props.get('game', {})
            actions = game.get('actions', [])
        
        sample_events = []
        for action in actions[:limit]:
            sample_events.append({
                'event_type': action.get('actionType'),
                'period': action.get('period'),
                'time_remaining': action.get('clock'),  # Changed from timeRemaining to clock
                'description': action.get('description'),
                'player_id': action.get('personId'),
                'team_id': action.get('teamId'),
                'home_score': action.get('scoreHome'),
                'away_score': action.get('scoreAway'),
                'action_number': action.get('actionNumber'),
                'shot_distance': action.get('shotDistance'),
                'shot_result': action.get('shotResult')
            })
        
        return sample_events
    
    def count_player_stats(self, game_data: Dict[str, Any]) -> tuple[int, int]:
        """Count player statistics for home and away teams."""
        props = game_data.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        home_players = game.get('homeTeam', {}).get('players', [])
        away_players = game.get('awayTeam', {}).get('players', [])
        
        return len(home_players), len(away_players)
    
    def close(self):
        """Close database session."""
        self.session.close()