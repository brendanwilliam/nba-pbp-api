"""
NBA Lineup Tracking System

This module provides functionality to track which players are on the court
at any given moment during an NBA game based on starting lineups and 
substitution events parsed from NBA JSON data.
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import timedelta


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
                # Construct player name from available fields
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
                # Construct player name from available fields
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
    
    def find_player_by_name(self, name: str, team_id: int) -> Optional[int]:
        """
        Find player ID by name within a specific team
        
        Args:
            name: Player name to search for
            team_id: Team ID to limit search to
            
        Returns:
            Player ID if found, None otherwise
        """
        name_normalized = self._normalize_name(name)
        
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
                player_in_id = self.find_player_by_name(player_in_name, team_id)
                if not player_in_id:
                    print(f"Warning: Could not find player '{player_in_name}' on team {team_id}")
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
    
    def detect_substitution_chains(self, substitutions: List[SubstitutionEvent]) -> List[List[SubstitutionEvent]]:
        """
        Detect substitution chains where players are substituted in quick succession
        
        Args:
            substitutions: List of substitution events sorted chronologically
            
        Returns:
            List of substitution chains (each chain is a list of related substitutions)
        """
        if not substitutions:
            return []
        
        chains = []
        current_chain = [substitutions[0]]  # Start with first substitution
        
        # Time window for detecting chains (15 seconds)
        CHAIN_TIME_WINDOW = 15
        
        for i in range(1, len(substitutions)):
            current_sub = substitutions[i]
            prev_sub = substitutions[i-1]
            
            # Calculate time difference
            time_diff = current_sub.seconds_elapsed - prev_sub.seconds_elapsed
            
            # Check if this substitution is part of a chain:
            # 1. Happens within time window
            # 2. Involves same team OR same players OR overlapping action numbers
            is_chain_substitution = False
            
            if time_diff <= CHAIN_TIME_WINDOW:
                # Check various chain conditions
                same_team = current_sub.team_id == prev_sub.team_id
                player_overlap = (current_sub.player_out_id == prev_sub.player_in_id or 
                                current_sub.player_in_id == prev_sub.player_out_id)
                consecutive_actions = abs(current_sub.action_number - prev_sub.action_number) <= 5
                
                if same_team or player_overlap or consecutive_actions:
                    is_chain_substitution = True
                    
                    # Log the type of chain detected
                    if player_overlap:
                        print(f"Chain detected: Player overlap - {current_sub.player_out_name} involved in consecutive substitutions (Actions #{prev_sub.action_number} -> #{current_sub.action_number}, {time_diff}s apart)")
                    elif same_team and time_diff <= 5:
                        print(f"Chain detected: Same team rapid substitutions - {current_sub.team_id} (Actions #{prev_sub.action_number} -> #{current_sub.action_number}, {time_diff}s apart)")
                    elif consecutive_actions and time_diff <= 10:
                        print(f"Chain detected: Consecutive actions - Actions #{prev_sub.action_number} -> #{current_sub.action_number}, {time_diff}s apart")
            
            if is_chain_substitution:
                # Add to current chain
                current_chain.append(current_sub)
            else:
                # End current chain and start new one
                chains.append(current_chain)
                current_chain = [current_sub]
        
        # Add final chain
        if current_chain:
            chains.append(current_chain)
        
        return chains
    
    def process_substitution_chain(self, chain: List[SubstitutionEvent], current_home: List[int], current_away: List[int]) -> bool:
        """
        Process a chain of related substitutions, handling them as a unit
        
        Args:
            chain: List of substitutions to process as a unit
            current_home: Current home team lineup (modified in place)
            current_away: Current away team lineup (modified in place)
            
        Returns:
            True if chain was processed successfully, False if skipped
        """
        if len(chain) == 1:
            # Single substitution - use normal logic
            return self.process_single_substitution(chain[0], current_home, current_away)
        
        print(f"Processing substitution chain of {len(chain)} substitutions:")
        for sub in chain:
            team_name = 'home' if sub.team_id == self.home_team_id else 'away'
            print(f"  Action #{sub.action_number} - {sub.player_out_name} OUT, {sub.player_in_name} IN ({team_name})")
        
        # For chains, we need to be more careful about the order
        # Group by team first
        home_chain = [sub for sub in chain if sub.team_id == self.home_team_id]
        away_chain = [sub for sub in chain if sub.team_id == self.away_team_id]
        
        # Process each team's chain
        success = True
        for team_chain, current_lineup, team_name in [
            (home_chain, current_home, 'home'),
            (away_chain, current_away, 'away')
        ]:
            if not team_chain:
                continue
                
            # For team chains, try to find a valid order
            if not self.process_team_substitution_chain(team_chain, current_lineup, team_name):
                success = False
        
        return success
    
    def process_team_substitution_chain(self, team_chain: List[SubstitutionEvent], current_lineup: List[int], team_name: str) -> bool:
        """
        Process substitutions for a single team within a chain
        
        Args:
            team_chain: Substitutions for one team
            current_lineup: Current lineup for this team (modified in place)
            team_name: 'home' or 'away' for logging
            
        Returns:
            True if processed successfully
        """
        if len(team_chain) == 1:
            return self.process_single_substitution(team_chain[0], 
                                                   current_lineup if team_name == 'home' else None,
                                                   current_lineup if team_name == 'away' else None)
        
        # For multiple substitutions on same team, we need to handle carefully
        # Try to find an order that works
        remaining_subs = team_chain.copy()
        processed_any = False
        
        while remaining_subs:
            made_progress = False
            
            for i, sub in enumerate(remaining_subs):
                # Check if this substitution can be made
                if (sub.player_out_id in current_lineup and 
                    sub.player_in_id not in current_lineup):
                    
                    # Make the substitution
                    try:
                        lineup_index = current_lineup.index(sub.player_out_id)
                        current_lineup[lineup_index] = sub.player_in_id
                        
                        print(f"  Chain: {sub.player_out_name} OUT, {sub.player_in_name} IN ({team_name}) - SUCCESS")
                        remaining_subs.pop(i)
                        made_progress = True
                        processed_any = True
                        break
                        
                    except ValueError:
                        continue
            
            if not made_progress:
                # Can't process remaining substitutions
                for sub in remaining_subs:
                    current_lineup_names = [self.player_roster.get(pid, {}).get('playerName', f'ID:{pid}') for pid in current_lineup]
                    print(f"  Chain: Action #{sub.action_number} - Cannot process {sub.player_out_name} OUT, {sub.player_in_name} IN ({team_name})")
                    print(f"         Current {team_name} lineup: {current_lineup_names}")
                    if sub.player_in_id in current_lineup:
                        print(f"         Reason: {sub.player_in_name} already in lineup")
                    elif sub.player_out_id not in current_lineup:
                        print(f"         Reason: {sub.player_out_name} not in lineup")
                break
        
        return processed_any
    
    def process_single_substitution(self, sub: SubstitutionEvent, current_home: List[int], current_away: List[int]) -> bool:
        """
        Process a single substitution with the original logic
        
        Returns:
            True if processed successfully, False if skipped
        """
        # Update appropriate team lineup
        if sub.team_id == self.home_team_id:
            current_lineup = current_home
        else:
            current_lineup = current_away
        
        team_name = 'home' if sub.team_id == self.home_team_id else 'away'
        
        # Check for phantom player situation first
        if sub.player_in_id in current_lineup and sub.player_out_id not in current_lineup:
            # This could be a data error - player_in is already there and player_out isn't
            # Let's check if we can find player_out in recent actions (indicating they were playing)
            if self._is_phantom_player_swap(sub):
                # Find a player to swap out (preferably one who hasn't had recent actions)
                swap_candidate = self._find_swap_candidate(current_lineup, sub.team_id, sub.period)
                if swap_candidate:
                    print(f"Info: Action #{sub.action_number} - Detected phantom player situation")
                    print(f"      {sub.player_out_name} was playing but not in tracked lineup")
                    print(f"      Swapping out {self.player_roster.get(swap_candidate, {}).get('playerName', f'ID:{swap_candidate}')} to fix lineup")
                    
                    # First swap the phantom player in for the candidate
                    lineup_index = current_lineup.index(swap_candidate)
                    current_lineup[lineup_index] = sub.player_out_id
                    
                    # Now do the actual substitution
                    current_lineup[lineup_index] = sub.player_in_id
                    return True
        
        try:
            # Check if incoming player is already in the lineup
            if sub.player_in_id in current_lineup:
                current_lineup_names = [self.player_roster.get(pid, {}).get('playerName', f'ID:{pid}') for pid in current_lineup]
                print(f"Warning: Action #{sub.action_number} - Player {sub.player_in_name} (ID: {sub.player_in_id}) already in {team_name} lineup")
                print(f"         Current {team_name} lineup: {current_lineup_names}")
                print(f"         Skipping invalid substitution: {sub.description}")
                return False
            
            lineup_index = current_lineup.index(sub.player_out_id)
            print(f"Debug: Found {sub.player_out_name} at position {lineup_index}, replacing with {sub.player_in_name}")
            current_lineup[lineup_index] = sub.player_in_id
            
            # Validate we still have exactly 5 unique players
            if len(set(current_lineup)) != 5:
                print(f"ERROR: Action #{sub.action_number} - {team_name} lineup has {len(set(current_lineup))} unique players instead of 5!")
                print(f"       Lineup IDs: {current_lineup}")
                print(f"       This should not happen after fix - please investigate")
                return False
            
            return True
            
        except ValueError:
            # Player out not in lineup - check for phantom player situation
            if sub.player_in_id not in current_lineup and self._is_phantom_player_swap(sub):
                # Both players involved aren't in our tracked lineup - this is a phantom substitution
                # We need to handle this by finding who should be swapped out
                swap_candidate = self._find_swap_candidate(current_lineup, sub.team_id, sub.period)
                if swap_candidate:
                    print(f"Info: Action #{sub.action_number} - Handling phantom substitution")
                    print(f"      {sub.player_out_name} wasn't tracked but was playing")
                    print(f"      Swapping {self.player_roster.get(swap_candidate, {}).get('playerName', f'ID:{swap_candidate}')} -> {sub.player_out_name} -> {sub.player_in_name}")
                    
                    # First put player_out in for the swap candidate
                    lineup_index = current_lineup.index(swap_candidate)
                    current_lineup[lineup_index] = sub.player_out_id
                    
                    # Then do the actual substitution
                    current_lineup[lineup_index] = sub.player_in_id
                    return True
            
            current_lineup_names = [self.player_roster.get(pid, {}).get('playerName', f'ID:{pid}') for pid in current_lineup]
            print(f"Warning: Action #{sub.action_number} - Player {sub.player_out_name} (ID: {sub.player_out_id}) not in current {team_name} lineup")
            print(f"         Current {team_name} lineup: {current_lineup_names}")
            return False
    
    def _is_phantom_player_swap(self, sub: SubstitutionEvent) -> bool:
        """
        Check if this substitution involves a player who was playing but not tracked
        
        Args:
            sub: The substitution event
            
        Returns:
            True if player_out has recent actions indicating they were playing
        """
        try:
            actions = self.game_data['props']['pageProps']['playByPlay']['actions']
        except KeyError:
            return False
        
        # Look for recent actions by player_out before this substitution
        recent_action_found = False
        for action in actions:
            action_num = action.get('actionNumber', 0)
            if action_num >= sub.action_number:
                break
            if action_num >= sub.action_number - 20:  # Look at last 20 actions
                if action.get('personId') == sub.player_out_id:
                    # Found an action by the player who's supposedly being subbed out
                    recent_action_found = True
                    break
        
        return recent_action_found
    
    def _find_swap_candidate(self, current_lineup: List[int], team_id: int, period: int) -> Optional[int]:
        """
        Find a player in the lineup who should be swapped out (hasn't had recent actions)
        
        Args:
            current_lineup: Current team lineup
            team_id: Team ID
            period: Current period
            
        Returns:
            Player ID to swap out, or None if no good candidate
        """
        try:
            actions = self.game_data['props']['pageProps']['playByPlay']['actions']
        except KeyError:
            return None
        
        # Count recent actions for each player in the lineup
        action_counts = {pid: 0 for pid in current_lineup}
        
        # Look at recent actions (last 50 or current period)
        for action in reversed(actions):
            if action.get('period', 0) < period:
                break
            
            player_id = action.get('personId')
            if player_id in action_counts:
                action_counts[player_id] += 1
        
        # Find player with fewest recent actions
        min_actions = float('inf')
        swap_candidate = None
        
        for pid, count in action_counts.items():
            if count < min_actions:
                min_actions = count
                swap_candidate = pid
        
        # Return the player with fewest actions (even if it's 0)
        return swap_candidate

    def detect_period_starting_lineups(self) -> Dict[int, Tuple[List[int], List[int]]]:
        """
        Detect actual starting lineups for each period by analyzing actions before first substitution
        
        Returns:
            Dictionary mapping period -> (home_lineup, away_lineup)
        """
        try:
            actions = self.game_data['props']['pageProps']['playByPlay']['actions']
        except KeyError:
            raise ValueError("Could not find game actions in JSON data")
        
        # Get all substitution events first
        substitutions = self.parse_substitution_events()
        
        # Find first substitution of each period
        first_sub_by_period = {}
        for sub in substitutions:
            if sub.period not in first_sub_by_period:
                first_sub_by_period[sub.period] = sub.action_number
            else:
                first_sub_by_period[sub.period] = min(first_sub_by_period[sub.period], sub.action_number)
        
        period_lineups = {}
        
        # For each period, analyze actions before first substitution to detect lineups
        for period in sorted(set(action.get('period', 0) for action in actions if action.get('period'))):
            if period == 1:
                # Use official starting lineups for period 1
                home_starters, away_starters = self.get_starting_lineups()
                period_lineups[period] = (home_starters, away_starters)
            else:
                # Detect lineups from actions before first substitution
                home_lineup, away_lineup = self._detect_lineup_from_actions(period, first_sub_by_period.get(period))
                if home_lineup and away_lineup:
                    period_lineups[period] = (home_lineup, away_lineup)
                    
                    # Debug output
                    home_names = [self.player_roster.get(pid, {}).get('playerName', f'ID:{pid}') for pid in home_lineup]
                    away_names = [self.player_roster.get(pid, {}).get('playerName', f'ID:{pid}') for pid in away_lineup]
                    print(f"Debug: Period {period} detected lineups:")
                    print(f"  Home: {home_names}")
                    print(f"  Away: {away_names}")
                else:
                    # Fall back to previous period's ending lineup
                    print(f"Debug: Could not detect Period {period} lineups, using fallback")
                    prev_period = period - 1
                    if prev_period in period_lineups:
                        period_lineups[period] = period_lineups[prev_period]
                    else:
                        # Ultimate fallback to starting lineups
                        home_starters, away_starters = self.get_starting_lineups()
                        period_lineups[period] = (home_starters, away_starters)
        
        return period_lineups
    
    def _detect_lineup_from_actions(self, period: int, first_sub_action: Optional[int]) -> Tuple[Optional[List[int]], Optional[List[int]]]:
        """
        Detect lineups by analyzing actions at the start of a period
        
        Args:
            period: Period number
            first_sub_action: Action number of first substitution in period (None if no subs)
            
        Returns:
            Tuple of (home_lineup, away_lineup) or (None, None) if detection fails
        """
        try:
            actions = self.game_data['props']['pageProps']['playByPlay']['actions']
        except KeyError:
            return None, None
        
        # Find actions in this period before first substitution
        period_actions = []
        for action in actions:
            if action.get('period') != period:
                continue
            if first_sub_action and action.get('actionNumber', 0) >= first_sub_action:
                break
            period_actions.append(action)
        
        # Look for actions that indicate players on court
        home_players_on_court = set()
        away_players_on_court = set()
        
        # Analyze first 30 actions to find as many players as possible
        for action in period_actions[:30]:
            player_id = action.get('personId')
            team_id = action.get('teamId')
            action_type = action.get('actionType', '')
            
            if not player_id or not team_id:
                continue
            
            # Skip team-level actions
            if self.is_team_id(player_id):
                continue
            
            # Actions that indicate a player is on court
            on_court_actions = [
                'Made Shot', 'Missed Shot', 'Rebound', 'Foul', 'Free Throw', 
                'Turnover', 'Jump Ball'
            ]
            
            if action_type in on_court_actions:
                if team_id == self.home_team_id:
                    home_players_on_court.add(player_id)
                elif team_id == self.away_team_id:
                    away_players_on_court.add(player_id)
            
            # Stop if we have enough players
            if len(home_players_on_court) >= 5 and len(away_players_on_court) >= 5:
                break
        
        # Accept lineups with at least 3 players detected, fill in remaining spots if needed
        home_lineup = None
        away_lineup = None
        
        if len(home_players_on_court) >= 3:
            home_lineup = list(home_players_on_court)
            # If we have fewer than 5, try to fill in from previous period's ending lineup
            if len(home_lineup) < 5:
                home_lineup = self._fill_incomplete_lineup(home_lineup, self.home_team_id, period)
        
        if len(away_players_on_court) >= 3:
            away_lineup = list(away_players_on_court)
            # If we have fewer than 5, try to fill in from previous period's ending lineup
            if len(away_lineup) < 5:
                away_lineup = self._fill_incomplete_lineup(away_lineup, self.away_team_id, period)
        
        return home_lineup, away_lineup
    
    def _fill_incomplete_lineup(self, detected_players: List[int], team_id: int, period: int) -> List[int]:
        """
        Fill incomplete lineup by using commonly substituted players or starters
        
        Args:
            detected_players: Players we detected from early period actions
            team_id: Team ID to fill lineup for
            period: Current period number
            
        Returns:
            Complete 5-player lineup
        """
        lineup = detected_players.copy()
        
        # Get all players from this team
        team_players = [
            pid for pid, pinfo in self.player_roster.items() 
            if pinfo['teamId'] == team_id and pid not in lineup
        ]
        
        # Sort by minutes played (descending) to prioritize starters/key players
        team_players.sort(
            key=lambda pid: self._convert_minutes_to_seconds(
                self.player_roster.get(pid, {}).get('minutes', '0:00')
            ),
            reverse=True
        )
        
        # Fill remaining spots
        while len(lineup) < 5 and team_players:
            lineup.append(team_players.pop(0))
        
        # Ensure we have exactly 5 players
        if len(lineup) >= 5:
            return lineup[:5]
        else:
            # Fallback: use starting lineup if we can't fill it
            if team_id == self.home_team_id:
                home_starters, _ = self.get_starting_lineups()
                return home_starters
            else:
                _, away_starters = self.get_starting_lineups()
                return away_starters
    
    def is_team_id(self, potential_player_id: int) -> bool:
        """Check if this ID is actually a team ID (NBA team IDs are 10 digits starting with 1610612)"""
        return potential_player_id and str(potential_player_id).startswith('1610612') and len(str(potential_player_id)) == 10

    def build_lineup_timeline(self) -> List[LineupState]:
        """
        Build complete timeline of lineup states throughout the game
        
        Returns:
            List of LineupState objects representing lineup at each substitution
        """
        timeline = []
        
        # Detect period-specific starting lineups
        period_lineups = self.detect_period_starting_lineups()
        
        # Process substitutions chronologically with chain detection
        substitutions = self.parse_substitution_events()
        chains = self.detect_substitution_chains(substitutions)
        
        print(f"Debug: Detected {len(chains)} substitution chains from {len(substitutions)} total substitutions")
        
        # Track current lineups
        current_home = None
        current_away = None
        current_period = 0
        
        for chain in chains:
            # Check if we've moved to a new period
            chain_period = chain[0].period
            if chain_period != current_period:
                current_period = chain_period
                
                # Update lineups for new period
                if chain_period in period_lineups:
                    current_home, current_away = period_lineups[chain_period]
                    current_home = current_home.copy()
                    current_away = current_away.copy()
                    
                    # Add period start lineup state
                    timeline.append(LineupState(
                        game_id=self.game_id,
                        period=chain_period,
                        clock="PT12M00.00S",
                        seconds_elapsed=self.parse_clock_to_seconds(chain_period, "PT12M00.00S"),
                        home_players=current_home.copy(),
                        away_players=current_away.copy(),
                        home_team_id=self.home_team_id,
                        away_team_id=self.away_team_id
                    ))
                    
                    # Debug output
                    home_names = [self.player_roster.get(pid, {}).get('playerName', f'ID:{pid}') for pid in current_home]
                    away_names = [self.player_roster.get(pid, {}).get('playerName', f'ID:{pid}') for pid in current_away]
                    print(f"Debug: Period {chain_period} starting lineups:")
                    print(f"  Home: {home_names}")
                    print(f"  Away: {away_names}")
            
            # Initialize lineups if not set (period 1)
            if current_home is None or current_away is None:
                if 1 in period_lineups:
                    current_home, current_away = period_lineups[1]
                    current_home = current_home.copy()
                    current_away = current_away.copy()
                    
                    # Add game start lineup state for period 1
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
            
            # Process substitution chain
            chain_processed = self.process_substitution_chain(chain, current_home, current_away)
            
            if chain_processed:
                # Add lineup state after successful chain processing
                last_sub = chain[-1]
                timeline.append(LineupState(
                    game_id=self.game_id,
                    period=last_sub.period,
                    clock=last_sub.clock,
                    seconds_elapsed=last_sub.seconds_elapsed,
                    home_players=current_home.copy(),
                    away_players=current_away.copy(),
                    home_team_id=self.home_team_id,
                    away_team_id=self.away_team_id
                ))
        
        # Add final lineup state at game end if needed
        if timeline and substitutions:
            # Get the last action in the game
            try:
                actions = self.game_data['props']['pageProps']['playByPlay']['actions']
                if actions:
                    last_action = actions[-1]
                    last_period = last_action.get('period', 0)
                    last_clock = last_action.get('clock', '')
                    
                    # Calculate game end time
                    if last_period <= 4:
                        game_end_seconds = last_period * 720  # 12 minutes per period
                    else:
                        # Overtime periods
                        game_end_seconds = 4 * 720 + (last_period - 4) * 300  # 5 min per OT
                    
                    # Check if we need to add a final state
                    last_timeline_state = timeline[-1]
                    if last_timeline_state.seconds_elapsed < game_end_seconds - 30:  # 30 second buffer
                        # Add final lineup state at game end
                        final_state = LineupState(
                            game_id=self.game_id,
                            period=last_period,
                            clock="PT00M00.00S",
                            seconds_elapsed=game_end_seconds,
                            home_players=current_home.copy() if current_home else last_timeline_state.home_players.copy(),
                            away_players=current_away.copy() if current_away else last_timeline_state.away_players.copy(),
                            home_team_id=self.home_team_id,
                            away_team_id=self.away_team_id
                        )
                        timeline.append(final_state)
                        print(f"Debug: Added final lineup state at game end (Period {last_period}, {game_end_seconds}s)")
            except Exception as e:
                print(f"Debug: Could not add final lineup state: {e}")
        
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