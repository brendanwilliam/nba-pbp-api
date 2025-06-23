"""
NBA Lineup Tracking System

This module provides functionality to track which players are on the court
at any given moment during an NBA game. It handles:
- Quarter boundary lineup changes
- Players who play full quarters without substitutions  
- Inference of starting lineups based on first substitution direction
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from datetime import timedelta
from collections import defaultdict


@dataclass
class LineupState:
    """Represents the on-court players for both teams at a specific moment"""
    game_id: str
    period: int
    clock: str
    seconds_elapsed: int
    home_players: List[int]
    away_players: List[int]
    home_team_id: int
    away_team_id: int


@dataclass 
class SubstitutionEvent:
    """Represents a single substitution event"""
    game_id: str
    action_number: int
    period: int
    clock: str
    seconds_elapsed: int
    team_id: int
    player_out_id: int
    player_out_name: str
    player_in_id: int
    player_in_name: str
    description: str


@dataclass
class QuarterBoundary:
    """Marks the start and end of a quarter"""
    period: int
    start_action_number: int
    end_action_number: int


@dataclass
class PlayerQuarterStatus:
    """Tracks a player's status for a specific quarter"""
    player_id: int
    period: int
    first_sub_type: Optional[str]  # 'IN', 'OUT', or None
    first_sub_action: Optional[int]
    action_count: int
    action_numbers: List[int]
    inferred_status: str  # 'STARTED', 'BENCHED', 'PLAYED_FULL'


class LineupTracker:
    """Main class for tracking NBA lineup changes throughout a game"""
    
    def __init__(self, game_data: Dict[str, Any]):
        """
        Initialize lineup tracker with NBA game JSON data
        
        Args:
            game_data: Complete NBA game JSON data from NBA.com
        """
        self.game_data = game_data
        self.game_id = self._extract_game_id()
        self.home_team_id, self.away_team_id = self._extract_team_ids()
        self.player_roster = self._build_player_roster()
        self.quarter_boundaries = self._analyze_quarter_boundaries()
        self.all_substitutions = self.parse_substitution_events()
        
    def _extract_game_id(self) -> str:
        """Extract game ID from JSON data"""
        try:
            return self.game_data['props']['pageProps']['game']['gameId']
        except KeyError:
            raise ValueError("Could not extract game ID from JSON data")
    
    def _extract_team_ids(self) -> Tuple[int, int]:
        """Extract home and away team IDs"""
        try:
            game = self.game_data['props']['pageProps']['game']
            home_team_id = game['homeTeam']['teamId']
            away_team_id = game['awayTeam']['teamId'] 
            return home_team_id, away_team_id
        except KeyError:
            raise ValueError("Could not extract team IDs from JSON data")
    
    def _analyze_quarter_boundaries(self) -> Dict[int, QuarterBoundary]:
        """Analyze and store quarter boundaries based on action numbers"""
        try:
            actions = self.game_data['props']['pageProps']['playByPlay']['actions']
        except KeyError:
            raise ValueError("Could not find game actions in JSON data")
        
        boundaries = {}
        current_period = None
        period_start = None
        
        for i, action in enumerate(actions):
            period = action.get('period', 0)
            action_num = action.get('actionNumber', 0)
            
            if period != current_period:
                # End previous period if exists
                if current_period is not None and period_start is not None:
                    boundaries[current_period] = QuarterBoundary(
                        period=current_period,
                        start_action_number=period_start,
                        end_action_number=actions[i-1].get('actionNumber', 0)
                    )
                
                # Start new period
                current_period = period
                period_start = action_num
        
        # Handle last period
        if current_period is not None and period_start is not None:
            boundaries[current_period] = QuarterBoundary(
                period=current_period,
                start_action_number=period_start,
                end_action_number=actions[-1].get('actionNumber', 0)
            )
        
        return boundaries
    
    def _convert_minutes_to_seconds(self, minutes_str: str) -> int:
        """Convert minutes string like '40:10' to total seconds"""
        if not minutes_str:
            return 0
        try:
            parts = minutes_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0
    
    def _identify_starters(self, team_players: List[Dict[str, Any]]) -> List[int]:
        """Identify starting 5 by finding players with position and highest minutes"""
        players_with_positions = [
            p for p in team_players 
            if p.get('position') and p.get('statistics', {}).get('minutes')
        ]
        
        # Sort by minutes played (descending) and take top 5
        sorted_players = sorted(
            players_with_positions,
            key=lambda p: self._convert_minutes_to_seconds(p['statistics']['minutes']),
            reverse=True
        )
        
        return [p['personId'] for p in sorted_players[:5]]
    
    def _build_player_roster(self) -> Dict[int, Dict[str, Any]]:
        """Build complete player roster with name mappings for both teams"""
        roster = {}
        
        try:
            game = self.game_data['props']['pageProps']['game']
            
            # Get starting lineups first
            home_starters = self._identify_starters(game['homeTeam']['players'])
            away_starters = self._identify_starters(game['awayTeam']['players'])
            
            # Process home team players
            for player in game['homeTeam']['players']:
                player_id = player['personId']
                first_name = player.get('firstName', '')
                family_name = player.get('familyName', '')
                name_i = player.get('nameI', '')
                player_name = name_i if name_i else f"{first_name} {family_name}".strip()
                
                roster[player_id] = {
                    'personId': player_id,
                    'firstName': first_name,
                    'familyName': family_name,
                    'playerName': player_name,
                    'nameI': name_i,
                    'jerseyNum': player.get('jerseyNum', ''),
                    'position': player.get('position', ''),
                    'teamId': self.home_team_id,
                    'isStarter': player_id in home_starters,
                    'minutes': player.get('statistics', {}).get('minutes', '0:00')
                }
            
            # Process away team players  
            for player in game['awayTeam']['players']:
                player_id = player['personId']
                first_name = player.get('firstName', '')
                family_name = player.get('familyName', '')
                name_i = player.get('nameI', '')
                player_name = name_i if name_i else f"{first_name} {family_name}".strip()
                
                roster[player_id] = {
                    'personId': player_id,
                    'firstName': first_name,
                    'familyName': family_name,
                    'playerName': player_name,
                    'nameI': name_i,
                    'jerseyNum': player.get('jerseyNum', ''),
                    'position': player.get('position', ''),
                    'teamId': self.away_team_id,
                    'isStarter': player_id in away_starters,
                    'minutes': player.get('statistics', {}).get('minutes', '0:00')
                }
                
        except KeyError as e:
            raise ValueError(f"Could not build player roster: {e}")
            
        return roster
    
    def get_starting_lineups(self) -> Tuple[List[int], List[int]]:
        """
        Extract starting lineups from game data
        
        Returns:
            Tuple of (home_starters, away_starters) as lists of player IDs
        """
        home_starters = []
        away_starters = []
        
        for player_id, player_info in self.player_roster.items():
            if player_info['isStarter']:
                if player_info['teamId'] == self.home_team_id:
                    home_starters.append(player_id)
                else:
                    away_starters.append(player_id)
        
        # Validate we have exactly 5 starters per team
        if len(home_starters) != 5:
            raise ValueError(f"Home team has {len(home_starters)} starters, expected 5")
        if len(away_starters) != 5:
            raise ValueError(f"Away team has {len(away_starters)} starters, expected 5")
            
        return home_starters, away_starters
    
    def parse_clock_to_seconds(self, period: int, clock: str) -> int:
        """
        Convert game clock to total seconds elapsed since game start
        
        Args:
            period: Quarter/period number (1-4, 5+ for OT)
            clock: Clock time in PT format (e.g., "PT07M30.00S")
            
        Returns:
            Total seconds elapsed since game start
        """
        # Parse PT07M30.00S format
        match = re.match(r'PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', clock)
        if not match:
            raise ValueError(f"Invalid clock format: {clock}")
        
        minutes = int(match.group(1)) if match.group(1) else 0
        seconds = float(match.group(2)) if match.group(2) else 0
        
        # Clock counts down from 12:00, so remaining time
        remaining_seconds = minutes * 60 + seconds
        
        # Calculate elapsed time in current period (12 minutes = 720 seconds per period)
        period_elapsed = 720 - remaining_seconds
        
        # Add elapsed time from previous periods
        if period <= 4:
            # Regular periods
            total_elapsed = (period - 1) * 720 + period_elapsed
        else:
            # Overtime periods (5 minutes each = 300 seconds)
            regular_time = 4 * 720  # 4 regular periods
            ot_periods = period - 4
            ot_elapsed = (ot_periods - 1) * 300 + (300 - remaining_seconds)
            total_elapsed = regular_time + ot_elapsed
            
        return int(total_elapsed)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison by removing accents and special characters"""
        import unicodedata
        # Remove accents and normalize unicode
        normalized = unicodedata.normalize('NFD', name)
        ascii_name = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return ascii_name.lower().strip()
    
    def find_player_by_name(self, name: str, team_id: int, suppress_warnings: bool = False) -> Optional[int]:
        """
        Find player ID by name within a specific team
        
        Args:
            name: Player name to search for
            team_id: Team ID to limit search to
            suppress_warnings: Whether to suppress warning output
            
        Returns:
            Player ID if found, None otherwise
        """
        name_normalized = self._normalize_name(name)
        
        # Handle common name variations
        common_variations = {
            'jay. williams': ['jayson williams', 'jaylen williams', 'jalen williams'],
            'jal. williams': ['jaylen williams', 'jalen williams', 'jayson williams'],
            'ja. green': ['jalen green', 'jamari green', 'javonte green'],
            'je. green': ['jalen green', 'jeff green', 'jerami green'],
            'martin jr.': ['kenyon martin jr.', 'kenyon martin jr'],
            'boston jr.': ['brandon boston jr.', 'brandon boston jr'],
        }
        
        # Check if we have a known variation
        if name_normalized in common_variations:
            for variation in common_variations[name_normalized]:
                var_normalized = self._normalize_name(variation)
                for player_id, player_info in self.player_roster.items():
                    if player_info['teamId'] != team_id:
                        continue
                    player_full = self._normalize_name(f"{player_info['firstName']} {player_info['familyName']}")
                    player_name = self._normalize_name(player_info['playerName'])
                    if var_normalized == player_full or var_normalized == player_name:
                        return player_id
        
        # Try exact matches first
        for player_id, player_info in self.player_roster.items():
            if player_info['teamId'] != team_id:
                continue
                
            # Check various name formats (normalized)
            player_full = self._normalize_name(f"{player_info['firstName']} {player_info['familyName']}")
            player_short = self._normalize_name(f"{player_info['firstName'][0]}. {player_info['familyName']}" if player_info['firstName'] else player_info['familyName'])
            player_name = self._normalize_name(player_info['playerName'])
            
            if (name_normalized == player_name or
                name_normalized == player_full or
                name_normalized == player_short):
                return player_id
        
        # Try partial matches (last name only)
        for player_id, player_info in self.player_roster.items():
            if player_info['teamId'] != team_id:
                continue
                
            family_name_normalized = self._normalize_name(player_info['familyName'])
            if name_normalized == family_name_normalized:
                return player_id
        
        # Try fuzzy matching for common nickname patterns
        for player_id, player_info in self.player_roster.items():
            if player_info['teamId'] != team_id:
                continue
                
            # Check if search name is contained in any player name
            player_full = self._normalize_name(f"{player_info['firstName']} {player_info['familyName']}")
            if name_normalized in player_full or player_full.split()[-1] == name_normalized:
                return player_id
        
        # Only print warning if not suppressed
        if not suppress_warnings:
            print(f"Warning: Could not find player '{name}' on team {team_id}")
        
        return None
    
    def parse_substitution_events(self) -> List[SubstitutionEvent]:
        """
        Parse all substitution events from game JSON data
        
        Returns:
            List of SubstitutionEvent objects sorted chronologically
        """
        substitutions = []
        
        try:
            actions = self.game_data['props']['pageProps']['playByPlay']['actions']
        except KeyError:
            raise ValueError("Could not find game actions in JSON data")
        
        for action in actions:
            if action.get('actionType') != 'Substitution':
                continue
                
            # Extract basic info
            period = action['period']
            clock = action['clock']
            team_id = action['teamId']
            player_out_id = action['personId']
            player_out_name = action.get('playerName', '')
            description = action['description']
            
            # Parse player coming in from description: "SUB: Brooks FOR Ward"
            try:
                sub_match = re.match(r'SUB:\s*(.+?)\s+FOR\s+(.+)', description)
                if not sub_match:
                    print(f"Warning: Could not parse substitution description: {description}")
                    continue
                    
                player_in_name = sub_match.group(1).strip()
                player_out_name_desc = sub_match.group(2).strip()
                
                # Find player IDs
                player_in_id = self.find_player_by_name(player_in_name, team_id, suppress_warnings=True)
                if not player_in_id:
                    continue
                
                # Create substitution event
                sub_event = SubstitutionEvent(
                    game_id=self.game_id,
                    action_number=action.get('actionNumber', 0),
                    period=period,
                    clock=clock,
                    seconds_elapsed=self.parse_clock_to_seconds(period, clock),
                    team_id=team_id,
                    player_out_id=player_out_id,
                    player_out_name=player_out_name,
                    player_in_id=player_in_id,
                    player_in_name=player_in_name,
                    description=description
                )
                
                substitutions.append(sub_event)
                
            except Exception as e:
                print(f"Warning: Error processing substitution {description}: {e}")
                continue
        
        # Sort chronologically (by period, then by seconds elapsed ascending)
        substitutions.sort(key=lambda x: (x.period, x.seconds_elapsed))
        
        return substitutions
    
    def analyze_player_quarter_patterns(self) -> Dict[int, Dict[int, PlayerQuarterStatus]]:
        """
        Analyze each player's pattern for each quarter
        
        Returns:
            Dict[player_id][period] -> PlayerQuarterStatus
        """
        patterns = defaultdict(dict)
        
        # First, get all player actions by period
        player_actions = self._get_all_player_actions_by_period()
        
        # Analyze each player for each period
        for player_id in self.player_roster:
            for period in range(1, 5):  # Regular periods 1-4
                if period not in self.quarter_boundaries:
                    continue
                
                # Find first substitution for this player in this period
                first_sub_in = None
                first_sub_out = None
                
                for sub in self.all_substitutions:
                    if sub.period != period:
                        continue
                    
                    if sub.player_in_id == player_id and first_sub_in is None:
                        first_sub_in = sub
                    if sub.player_out_id == player_id and first_sub_out is None:
                        first_sub_out = sub
                    
                    if first_sub_in and first_sub_out:
                        break
                
                # Determine first substitution type
                first_sub_type = None
                first_sub_action = None
                
                if first_sub_in and first_sub_out:
                    if first_sub_in.action_number < first_sub_out.action_number:
                        first_sub_type = 'IN'
                        first_sub_action = first_sub_in.action_number
                    else:
                        first_sub_type = 'OUT'
                        first_sub_action = first_sub_out.action_number
                elif first_sub_in:
                    first_sub_type = 'IN'
                    first_sub_action = first_sub_in.action_number
                elif first_sub_out:
                    first_sub_type = 'OUT'
                    first_sub_action = first_sub_out.action_number
                
                # Get player actions in this period
                period_actions = player_actions.get(player_id, {}).get(period, [])
                
                # Determine inferred status
                if first_sub_type == 'OUT':
                    inferred_status = 'STARTED'
                elif first_sub_type == 'IN':
                    inferred_status = 'BENCHED'
                elif len(period_actions) > 0:
                    inferred_status = 'PLAYED_FULL'
                else:
                    inferred_status = 'BENCHED'
                
                patterns[player_id][period] = PlayerQuarterStatus(
                    player_id=player_id,
                    period=period,
                    first_sub_type=first_sub_type,
                    first_sub_action=first_sub_action,
                    action_count=len(period_actions),
                    action_numbers=period_actions,
                    inferred_status=inferred_status
                )
        
        return patterns
    
    def _get_all_player_actions_by_period(self) -> Dict[int, Dict[int, List[int]]]:
        """
        Get all actions for each player organized by period
        
        Returns:
            Dict[player_id][period] -> List[action_numbers]
        """
        player_actions = defaultdict(lambda: defaultdict(list))
        
        try:
            actions = self.game_data['props']['pageProps']['playByPlay']['actions']
        except KeyError:
            return player_actions
        
        for action in actions:
            player_id = action.get('personId')
            if not player_id or self.is_team_id(player_id):
                continue
            
            period = action.get('period', 0)
            action_number = action.get('actionNumber', 0)
            
            # Only track actions that indicate on-court presence
            action_type = action.get('actionType', '')
            on_court_actions = [
                'Made Shot', 'Missed Shot', 'Rebound', 'Foul', 'Free Throw', 
                'Turnover', 'Jump Ball', 'Assist', 'Block', 'Steal'
            ]
            
            if action_type in on_court_actions:
                player_actions[player_id][period].append(action_number)
        
        return player_actions
    
    def is_team_id(self, potential_player_id: int) -> bool:
        """Check if this ID is actually a team ID (NBA team IDs are 10 digits starting with 1610612)"""
        return potential_player_id and str(potential_player_id).startswith('1610612') and len(str(potential_player_id)) == 10
    
    def infer_quarter_starting_lineup(self, period: int, player_patterns: Dict[int, Dict[int, PlayerQuarterStatus]]) -> Tuple[List[int], List[int]]:
        """
        Infer the starting lineup for a specific quarter based on player patterns
        
        Args:
            period: Quarter number
            player_patterns: Player quarter patterns from analyze_player_quarter_patterns
            
        Returns:
            Tuple of (home_lineup, away_lineup)
        """
        home_lineup = []
        away_lineup = []
        
        # Group players by team
        home_candidates = []
        away_candidates = []
        
        for player_id, periods in player_patterns.items():
            if period not in periods:
                continue
            
            pattern = periods[period]
            team_id = self.player_roster[player_id]['teamId']
            
            # Players who either STARTED or PLAYED_FULL were on court at quarter start
            if pattern.inferred_status in ['STARTED', 'PLAYED_FULL']:
                if team_id == self.home_team_id:
                    home_candidates.append((player_id, pattern))
                else:
                    away_candidates.append((player_id, pattern))
        
        # Sort candidates by action count (more actions = more likely to have started)
        home_candidates.sort(key=lambda x: x[1].action_count, reverse=True)
        away_candidates.sort(key=lambda x: x[1].action_count, reverse=True)
        
        # Take top 5 for each team
        home_lineup = [player_id for player_id, _ in home_candidates[:5]]
        away_lineup = [player_id for player_id, _ in away_candidates[:5]]
        
        # Validate and fill if needed
        if len(home_lineup) < 5:
            # Fill from players who might have been missed
            for player_id, player_info in self.player_roster.items():
                if (player_info['teamId'] == self.home_team_id and 
                    player_id not in home_lineup and
                    len(home_lineup) < 5):
                    # Check if they had significant minutes
                    minutes = self._convert_minutes_to_seconds(player_info.get('minutes', '0:00'))
                    if minutes > 300:  # More than 5 minutes
                        home_lineup.append(player_id)
        
        if len(away_lineup) < 5:
            # Fill from players who might have been missed
            for player_id, player_info in self.player_roster.items():
                if (player_info['teamId'] == self.away_team_id and 
                    player_id not in away_lineup and
                    len(away_lineup) < 5):
                    # Check if they had significant minutes
                    minutes = self._convert_minutes_to_seconds(player_info.get('minutes', '0:00'))
                    if minutes > 300:  # More than 5 minutes
                        away_lineup.append(player_id)
        
        # Final validation - ensure exactly 5
        home_lineup = home_lineup[:5]
        away_lineup = away_lineup[:5]
        
        return home_lineup, away_lineup
    
    def build_lineup_timeline(self) -> List[LineupState]:
        """
        Build complete timeline of lineup states throughout the game
        
        Returns:
            List of LineupState objects representing lineup at each change
        """
        timeline = []
        
        # Analyze player patterns for all quarters
        player_patterns = self.analyze_player_quarter_patterns()
        
        # Use inferred starting lineup for Q1 instead of official starters
        # This fixes discrepancies between official rosters and actual game starters
        inferred_home, inferred_away = self.infer_quarter_starting_lineup(1, player_patterns)
        if len(inferred_home) == 5 and len(inferred_away) == 5:
            current_home = inferred_home.copy()
            current_away = inferred_away.copy()
        else:
            # Fallback to official starters if inference fails
            home_starters, away_starters = self.get_starting_lineups()
            current_home = home_starters.copy()
            current_away = away_starters.copy()
        
        # Add initial state
        timeline.append(LineupState(
            game_id=self.game_id,
            period=1,
            clock="PT12M00.00S",
            seconds_elapsed=0,
            home_players=current_home.copy(),
            away_players=current_away.copy(),
            home_team_id=self.home_team_id,
            away_team_id=self.away_team_id
        ))
        
        # Process each period
        for period in sorted(self.quarter_boundaries.keys()):
            # For periods after 1, infer the starting lineup
            if period > 1:
                inferred_home, inferred_away = self.infer_quarter_starting_lineup(period, player_patterns)
                
                # Update current lineups if we have valid inferences
                if len(inferred_home) == 5:
                    current_home = inferred_home.copy()
                if len(inferred_away) == 5:
                    current_away = inferred_away.copy()
                
                # Add period start state
                timeline.append(LineupState(
                    game_id=self.game_id,
                    period=period,
                    clock="PT12M00.00S",
                    seconds_elapsed=self.parse_clock_to_seconds(period, "PT12M00.00S"),
                    home_players=current_home.copy(),
                    away_players=current_away.copy(),
                    home_team_id=self.home_team_id,
                    away_team_id=self.away_team_id
                ))
            
            # Process substitutions within this period
            period_subs = [s for s in self.all_substitutions if s.period == period]
            
            for sub in period_subs:
                # Apply substitution
                if sub.team_id == self.home_team_id:
                    if sub.player_out_id in current_home:
                        idx = current_home.index(sub.player_out_id)
                        current_home[idx] = sub.player_in_id
                    # else:
                    #     print(f"Warning: Player {sub.player_out_name} not in home lineup at action {sub.action_number}")
                else:
                    if sub.player_out_id in current_away:
                        idx = current_away.index(sub.player_out_id)
                        current_away[idx] = sub.player_in_id
                    # else:
                    #     print(f"Warning: Player {sub.player_out_name} not in away lineup at action {sub.action_number}")
                
                # Add new state after substitution
                timeline.append(LineupState(
                    game_id=self.game_id,
                    period=sub.period,
                    clock=sub.clock,
                    seconds_elapsed=sub.seconds_elapsed,
                    home_players=current_home.copy(),
                    away_players=current_away.copy(),
                    home_team_id=self.home_team_id,
                    away_team_id=self.away_team_id
                ))
        
        return timeline
    
    def get_players_on_court(self, period: int, clock: str) -> Dict[str, Any]:
        """
        Get players on court at a specific moment in the game
        
        Args:
            period: Quarter/period number
            clock: Game clock (PT format)
            
        Returns:
            Dictionary with home and away team lineups
        """
        target_seconds = self.parse_clock_to_seconds(period, clock)
        timeline = self.build_lineup_timeline()
        
        # Find most recent lineup state at or before target time
        current_state = timeline[0]  # Default to game start
        
        for state in timeline:
            if state.seconds_elapsed <= target_seconds:
                current_state = state
            else:
                break
                
        return {
            'game_id': current_state.game_id,
            'period': period,
            'clock': clock,
            'home_team_id': current_state.home_team_id,
            'away_team_id': current_state.away_team_id,
            'home_players': current_state.home_players,
            'away_players': current_state.away_players,
            'home_player_names': [self.player_roster[pid]['playerName'] for pid in current_state.home_players],
            'away_player_names': [self.player_roster[pid]['playerName'] for pid in current_state.away_players]
        }


def load_game_json(file_path: str) -> Dict[str, Any]:
    """Load NBA game JSON data from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)