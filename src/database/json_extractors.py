"""
JSON data extractors for converting raw game JSON into normalized table records.
Each extractor handles one type of data transformation from the raw WNBA game data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from .game_utils import parse_game_id


class ArenaExtractor:
    """Extract arena data from game JSON"""
    
    @staticmethod
    def extract(game_json: Dict[str, Any]) -> Dict[str, Any]:
        """Extract arena data from .boxscore.arena"""
        arena_data = game_json['boxscore']['arena']
        
        return {
            'arena_id': arena_data['arenaId'],
            'arena_city': arena_data.get('arenaCity'),
            'arena_name': arena_data.get('arenaName'),
            'arena_state': arena_data.get('arenaState'),
            'arena_country': arena_data.get('arenaCountry'),
            'arena_timezone': arena_data.get('arenaTimezone'),
            'arena_postal_code': arena_data.get('arenaPostalCode') or None,
            'arena_street_address': arena_data.get('arenaStreetAddress') or None
        }


class TeamExtractor:
    """Extract team data from various teamId references in game JSON"""
    
    @staticmethod
    def extract_teams_from_game(game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all unique teams from a game"""
        teams = {}
        boxscore = game_json['boxscore']
        
        # Home and away teams with full details
        for team_key in ['homeTeam', 'awayTeam']:
            if team_key in boxscore:
                team_data = boxscore[team_key]
                team_id = team_data['teamId']
                teams[team_id] = {
                    'team_id': team_id,
                    'team_city': team_data.get('teamCity'),
                    'team_name': team_data.get('teamName'),
                    'team_tricode': team_data.get('teamTricode')
                }
        
        # Teams from play-by-play data (basic info only)
        if 'postGameData' in game_json and 'postPlayByPlayData' in game_json['postGameData']:
            for period in game_json['postGameData']['postPlayByPlayData']:
                for action in period.get('actions', []):
                    if 'teamId' in action and action['teamId']:
                        team_id = action['teamId']
                        if team_id not in teams:
                            teams[team_id] = {
                                'team_id': team_id,
                                'team_city': None,
                                'team_name': None,
                                'team_tricode': None
                            }
        
        return list(teams.values())


class GameExtractor:
    """Extract game data from .boxscore"""
    
    @staticmethod
    def normalize_duration(duration: str) -> Optional[str]:
        """
        Normalize game duration format to handle invalid formats like '1:60' -> '2:00'.
        
        Args:
            duration: Original duration string
            
        Returns:
            Normalized duration string, or original if already valid/invalid format
        """
        if not duration:
            return duration
            
        # Match format like 'H:MM' or 'H:M'
        match = re.match(r'^(\d+):(\d+)$', duration.strip())
        if not match:
            return duration
            
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        # Normalize minutes >= 60
        if minutes >= 60:
            additional_hours = minutes // 60
            remaining_minutes = minutes % 60
            hours += additional_hours
            minutes = remaining_minutes
            
            # Return normalized format
            return f"{hours}:{minutes:02d}"
        
        # Already valid, return original
        return duration
    
    @staticmethod
    def extract(game_json: Dict[str, Any]) -> Dict[str, Any]:
        """Extract game data from .boxscore"""
        boxscore = game_json['boxscore']
        
        # Parse game datetime
        game_et = None
        if 'gameEt' in boxscore and boxscore['gameEt']:
            try:
                game_et = datetime.fromisoformat(boxscore['gameEt'].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        game_id = int(boxscore['gameId'])
        game_metadata = parse_game_id(game_id)
        
        return {
            'game_id': game_id,
            'game_code': boxscore.get('gameCode'),
            'arena_id': boxscore['arena']['arenaId'],
            'game_et': game_et,
            'game_sellout': bool(boxscore.get('sellout', 0)),
            'home_team_id': boxscore['homeTeam']['teamId'],
            'home_team_wins': boxscore['homeTeam'].get('teamWins'),
            'home_team_losses': boxscore['homeTeam'].get('teamLosses'),
            'away_team_id': boxscore['awayTeam']['teamId'],
            'away_team_wins': boxscore['awayTeam'].get('teamWins'),
            'away_team_losses': boxscore['awayTeam'].get('teamLosses'),
            'game_duration': GameExtractor.normalize_duration(boxscore.get('duration')),
            'game_label': boxscore.get('gameLabel'),
            'game_attendance': boxscore.get('attendance'),
            'season': game_metadata['season'],
            'game_type': game_metadata['game_type']
        }


class PersonExtractor:
    """Extract person data from players and officials"""
    
    @staticmethod
    def extract_persons_from_game(game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all unique persons (players, officials) from a game"""
        persons = {}
        boxscore = game_json['boxscore']
        
        # Players from both teams
        for team_key in ['homeTeam', 'awayTeam']:
            if team_key in boxscore and 'players' in boxscore[team_key]:
                for player in boxscore[team_key]['players']:
                    person_id = player['personId']
                    if person_id not in persons:
                        persons[person_id] = {
                            'person_id': person_id,
                            'person_name': player.get('name'),
                            'person_iname': player.get('nameI'),
                            'person_fname': player.get('firstName'),
                            'person_lname': player.get('familyName'),
                            'person_role': 'player'
                        }
        
        # Officials
        if 'officials' in boxscore:
            for official in boxscore['officials']:
                person_id = official['personId']
                if person_id not in persons:
                    persons[person_id] = {
                        'person_id': person_id,
                        'person_name': official.get('name'),
                        'person_iname': official.get('nameI'),
                        'person_fname': official.get('firstName'),
                        'person_lname': official.get('familyName'),
                        'person_role': 'official'
                    }
        
        # Additional players from postBoxscoreData (contains more complete data)
        if 'postGameData' in game_json and 'postBoxscoreData' in game_json['postGameData']:
            post_boxscore = game_json['postGameData']['postBoxscoreData']
            for team_key in ['homeTeam', 'awayTeam']:
                if team_key in post_boxscore and 'players' in post_boxscore[team_key]:
                    for player_stats in post_boxscore[team_key]['players']:
                        person_id = player_stats.get('personId')
                        # Filter out invalid person IDs (same logic as BoxscoreExtractor)
                        if person_id and not ((1611661300 <= person_id <= 1611661399) or person_id < 1000):
                            if person_id not in persons:
                                persons[person_id] = {
                                    'person_id': person_id,
                                    'person_name': player_stats.get('name'),
                                    'person_iname': player_stats.get('nameI'), 
                                    'person_fname': player_stats.get('firstName'),
                                    'person_lname': player_stats.get('familyName'),
                                    'person_role': 'player'
                                }

        # Persons from play-by-play data
        if 'postGameData' in game_json and 'postPlayByPlayData' in game_json['postGameData']:
            for period in game_json['postGameData']['postPlayByPlayData']:
                for action in period.get('actions', []):
                    person_id = action.get('personId')
                    # Filter out invalid person IDs:
                    # - Team IDs (WNBA team IDs are in range 1611661300-1611661399)
                    # - System/administrative action IDs (typically < 1000)
                    # - Only include if we have an actual player name
                    if (person_id and person_id != 0 and person_id not in persons 
                        and not (1611661300 <= person_id <= 1611661399)
                        and person_id >= 1000
                        and action.get('playerName')):
                        persons[person_id] = {
                            'person_id': person_id,
                            'person_name': action.get('playerName'),
                            'person_iname': action.get('playerNameI'),
                            'person_fname': None,
                            'person_lname': None,
                            'person_role': 'player'  # Persons from play actions are players
                        }
        
        return list(persons.values())


class PlayExtractor:
    """Extract play-by-play data from .postGameData.postPlayByPlayData"""
    
    @staticmethod
    def extract_plays_from_game(game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all plays from a game"""
        plays = []
        game_id = int(game_json['boxscore']['gameId'])
        
        if 'postGameData' not in game_json or 'postPlayByPlayData' not in game_json['postGameData']:
            return plays
        
        for period_data in game_json['postGameData']['postPlayByPlayData']:
            period = period_data['period']
            
            for action in period_data.get('actions', []):
                # Handle nullable personId and filter out invalid IDs
                person_id = action.get('personId')
                if person_id == 0:
                    person_id = None
                elif person_id:
                    # Filter out invalid person IDs (same logic as PersonExtractor):
                    # - Team IDs (1611661300-1611661399)
                    # - System/administrative IDs (< 1000)
                    if (1611661300 <= person_id <= 1611661399) or person_id < 1000:
                        person_id = None
                
                play_data = {
                    'game_id': game_id,
                    'person_id': person_id,
                    'team_id': action.get('teamId'),
                    'action_id': action.get('actionId'),
                    'action_type': action.get('actionType'),
                    'sub_type': action.get('subType'),
                    'period': period,
                    'clock': action.get('clock'),
                    'x_legacy': action.get('xLegacy'),
                    'y_legacy': action.get('yLegacy'),
                    'location': action.get('location'),
                    'score_away': action.get('scoreAway'),
                    'score_home': action.get('scoreHome'),
                    'shot_value': action.get('shotValue'),
                    'shot_result': action.get('shotResult'),
                    'description': action.get('description'),
                    'is_field_goal': action.get('isFieldGoal', False),
                    'points_total': action.get('pointsTotal'),
                    'action_number': action.get('actionNumber'),
                    'shot_distance': action.get('shotDistance')
                }
                
                plays.append(play_data)
        
        return plays


class BoxscoreExtractor:
    """Extract boxscore statistics from .postGameData.postBoxscoreData"""
    
    # Mapping from API field names to database column names
    STAT_MAPPING = {
        'minutes': 'min',
        'points': 'pts',
        'reboundsTotal': 'reb',
        'assists': 'ast',
        'steals': 'stl',
        'blocks': 'blk',
        'plusMinusPoints': 'pm',
        'fieldGoalsMade': 'fgm',
        'fieldGoalsAttempted': 'fga',
        'fieldGoalsPercentage': 'fgp',
        'threePointersMade': 'tpm',
        'threePointersAttempted': 'tpa',
        'threePointersPercentage': 'tpp',
        'freeThrowsMade': 'ftm',
        'freeThrowsAttempted': 'fta',
        'freeThrowsPercentage': 'ftp',
        'turnovers': 'to',
        'foulsPersonal': 'pf',
        'reboundsOffensive': 'orebs',
        'reboundsDefensive': 'drebs'
    }
    
    @staticmethod
    def extract_boxscores_from_game(game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all boxscore entries from a game"""
        boxscores = []
        game_id = int(game_json['boxscore']['gameId'])
        
        # Try to get postBoxscoreData first (preferred source)
        boxscore_data = None
        use_fallback = False
        
        if ('postGameData' in game_json and 
            'postBoxscoreData' in game_json['postGameData'] and
            game_json['postGameData']['postBoxscoreData']):
            
            boxscore_data = game_json['postGameData']['postBoxscoreData']
            
            # Check if postBoxscoreData actually has meaningful content
            if isinstance(boxscore_data, dict) and boxscore_data:
                # Check if it has team data with real statistics
                home_team = boxscore_data.get('homeTeam', {})
                away_team = boxscore_data.get('awayTeam', {})
                
                home_stats = home_team.get('statistics', {})
                away_stats = away_team.get('statistics', {})
                
                # If statistics are empty or only contain dummy keys, use fallback
                if (not home_stats or 'dummyKey' in home_stats) and (not away_stats or 'dummyKey' in away_stats):
                    use_fallback = True
            else:
                use_fallback = True
        else:
            use_fallback = True
        
        # Use fallback if postBoxscoreData is not available or contains dummy data
        if use_fallback:
            return BoxscoreExtractor._extract_from_boxscore_fallback(game_json)
        
        # Continue with existing postBoxscoreData extraction
        boxscore_data = game_json['postGameData']['postBoxscoreData']
        
        # Process home and away team data
        for team_type in ['homeTeam', 'awayTeam']:
            if team_type not in boxscore_data:
                continue
                
            team_data = boxscore_data[team_type]
            home_away = 'h' if team_type == 'homeTeam' else 'a'
            
            # Team totals (from statistics key)
            if 'statistics' in team_data and team_data['statistics'] and isinstance(team_data['statistics'], dict):
                # Skip dummy statistics (older games have {'dummyKey': ...})
                if 'dummyKey' not in team_data['statistics']:
                    boxscore_entry = BoxscoreExtractor._create_boxscore_entry(
                        game_id=game_id,
                        team_id=None,  # Will need to be resolved from team mapping
                        person_id=None,
                        home_away_team=home_away,
                        box_type='totals',
                        stats=team_data['statistics']
                    )
                    boxscores.append(boxscore_entry)
            
            # Team-level stats (starters and bench) - these have statistics directly at top level
            for box_type in ['starters', 'bench']:
                if box_type in team_data and team_data[box_type] is not None:
                    # For starters/bench, the statistics are directly at the top level
                    stats = team_data[box_type]
                    boxscore_entry = BoxscoreExtractor._create_boxscore_entry(
                        game_id=game_id,
                        team_id=None,  # Will need to be resolved from team mapping
                        person_id=None,
                        home_away_team=home_away,
                        box_type=box_type,
                        stats=stats
                    )
                    boxscores.append(boxscore_entry)
            
            # Individual player stats - these have statistics sub-object
            if 'players' in team_data:
                for player_stats in team_data['players']:
                    # Player stats are in the 'statistics' sub-object
                    if 'statistics' in player_stats:
                        # Filter out invalid person IDs (same logic as PersonExtractor)
                        person_id = player_stats.get('personId')
                        if person_id and ((1611661300 <= person_id <= 1611661399) or person_id < 1000):
                            person_id = None
                            
                        boxscore_entry = BoxscoreExtractor._create_boxscore_entry(
                            game_id=game_id,
                            team_id=None,  # Will need to be resolved
                            person_id=person_id,
                            home_away_team=home_away,
                            box_type='player',
                            stats=player_stats['statistics']
                        )
                        boxscores.append(boxscore_entry)
        
        return boxscores
    
    @staticmethod 
    def _extract_from_boxscore_fallback(game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fallback extraction from .boxscore.homeTeam and .boxscore.awayTeam
        when postBoxscoreData is empty or contains dummy data.
        
        For older games (1997-era), check postgameCharts for team statistics.
        For newer games, check team and player statistics directly.
        """
        boxscores = []
        game_id = int(game_json['boxscore']['gameId'])
        
        if 'boxscore' not in game_json:
            return boxscores
        
        boxscore = game_json['boxscore']
        
        # First, try extracting from postgameCharts (for older games like 1997)
        if 'postgameCharts' in boxscore:
            postgame_charts = boxscore['postgameCharts']
            
            for team_key in ['homeTeam', 'awayTeam']:
                if team_key not in postgame_charts:
                    continue
                    
                team_chart = postgame_charts[team_key]
                team_stats = team_chart.get('statistics', {})
                
                if team_stats and isinstance(team_stats, dict) and 'dummyKey' not in team_stats:
                    home_away = 'h' if team_key == 'homeTeam' else 'a'
                    
                    # Create team totals entry from postgameCharts
                    boxscore_entry = BoxscoreExtractor._create_boxscore_entry(
                        game_id=game_id,
                        team_id=team_chart.get('teamId'),
                        person_id=None,
                        home_away_team=home_away,
                        box_type='totals',
                        stats=team_stats
                    )
                    boxscores.append(boxscore_entry)
        
        # If we found data from postgameCharts, return it
        if boxscores:
            return boxscores
        
        # Fallback to original method: Process home and away teams from boxscore directly
        for team_key in ['homeTeam', 'awayTeam']:
            if team_key not in boxscore:
                continue
                
            team_data = boxscore[team_key]
            home_away = 'h' if team_key == 'homeTeam' else 'a'
            
            # Extract team-level statistics if available
            team_stats = team_data.get('statistics', {})
            if team_stats and isinstance(team_stats, dict) and 'dummyKey' not in team_stats:
                # Create team totals entry
                boxscore_entry = BoxscoreExtractor._create_boxscore_entry(
                    game_id=game_id,
                    team_id=team_data.get('teamId'),
                    person_id=None,
                    home_away_team=home_away,
                    box_type='totals',
                    stats=team_stats
                )
                boxscores.append(boxscore_entry)
            
            # Extract individual player statistics if available
            players = team_data.get('players', [])
            for player in players:
                if not isinstance(player, dict):
                    continue
                    
                player_stats = player.get('statistics', {})
                if not player_stats or isinstance(player_stats, dict) and 'dummyKey' in player_stats:
                    continue
                
                # Filter out invalid person IDs (same logic as main extraction)
                person_id = player.get('personId')
                if person_id and ((1611661300 <= person_id <= 1611661399) or person_id < 1000):
                    person_id = None
                
                boxscore_entry = BoxscoreExtractor._create_boxscore_entry(
                    game_id=game_id,
                    team_id=team_data.get('teamId'), 
                    person_id=person_id,
                    home_away_team=home_away,
                    box_type='player',
                    stats=player_stats
                )
                boxscores.append(boxscore_entry)
        
        return boxscores
    
    @staticmethod
    def _create_boxscore_entry(game_id: int, team_id: Optional[int], person_id: Optional[int], 
                              home_away_team: str, box_type: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single boxscore entry from stats data"""
        entry = {
            'game_id': game_id,
            'team_id': team_id,
            'person_id': person_id,
            'home_away_team': home_away_team,
            'box_type': box_type
        }
        
        # Map all known statistics
        for api_field, db_column in BoxscoreExtractor.STAT_MAPPING.items():
            value = stats.get(api_field)
            
            # Handle special cases
            if api_field == 'minutes' and value:
                # Keep as string for minutes format (e.g., "25:30")
                entry[db_column] = str(value)
            elif api_field == 'plusMinusPoints':
                # plusMinusPoints is only for players, null for team totals
                if box_type in ['totals', 'starters', 'bench']:
                    entry[db_column] = None
                else:
                    # For players, use the actual value (could be None or a number)
                    entry[db_column] = int(value) if value is not None and value != '' else None
            elif api_field in ['fieldGoalsPercentage', 'threePointersPercentage', 'freeThrowsPercentage']:
                # Convert percentage to float
                if value is None or value == '':
                    entry[db_column] = None
                else:
                    try:
                        entry[db_column] = float(value)
                    except (ValueError, TypeError):
                        entry[db_column] = None
            else:
                # Convert to int for count stats, None for missing/empty
                if value is None or value == '' or value == 0:
                    entry[db_column] = None if value is None or value == '' else 0
                else:
                    try:
                        entry[db_column] = int(value)
                    except (ValueError, TypeError):
                        entry[db_column] = None
        
        return entry