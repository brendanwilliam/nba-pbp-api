"""
Possession Tracker - Analyzes play-by-play data to identify possessions

This module implements the possession change logic as specified in possession-changes.md:
- Made shots change possession
- Defensive rebounds change possession 
- Turnovers change possession
- Free throws: final FT made = possession change, missed = rebound determines
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PossessionEvent:
    """Represents a single possession by a team."""
    possession_id: Optional[int]
    game_id: str
    possession_number: int
    team_id: int
    
    # Start timing
    start_period: int
    start_time_remaining: str
    start_seconds_elapsed: int
    
    # End timing (None until possession ends)
    end_period: Optional[int] = None
    end_time_remaining: Optional[str] = None
    end_seconds_elapsed: Optional[int] = None
    
    # Outcome
    possession_outcome: Optional[str] = None
    points_scored: int = 0
    
    # Associated play IDs
    play_ids: List[int] = None
    
    def __post_init__(self):
        if self.play_ids is None:
            self.play_ids = []


class PossessionTracker:
    """Tracks possession changes throughout a game."""
    
    def __init__(self, game_id: str, home_team_id: int, away_team_id: int):
        self.game_id = game_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        
        # Track current state
        self.current_possession: Optional[PossessionEvent] = None
        self.possessions: List[PossessionEvent] = []
        self.possession_counter = 0
        
        # Store play events for context
        self.play_events: List[Dict[str, Any]] = []
    
    def process_play_events(self, play_events: List[Dict[str, Any]]) -> List[PossessionEvent]:
        """Process a list of play events and generate possessions."""
        # Sort events by period and event order
        sorted_events = sorted(play_events, key=lambda x: (x.get('period', 0), x.get('event_order', 0)))
        self.play_events = sorted_events
        
        # Start with tip-off possession (usually home team starts)
        self._start_new_possession(self.home_team_id, sorted_events[0] if sorted_events else None)
        
        for i, event in enumerate(sorted_events):
            self._process_event(event, i)
        
        # Close final possession if still active
        if self.current_possession:
            self._end_current_possession("game_end", sorted_events[-1] if sorted_events else None)
        
        return self.possessions
    
    def _process_event(self, event: Dict[str, Any], event_index: int):
        """Process a single play event."""
        if not self.current_possession:
            # Start new possession if none exists
            team_id = event.get('team_id') or self.home_team_id
            self._start_new_possession(team_id, event)
        
        # Add this play to current possession
        self.current_possession.play_ids.append(event.get('event_id'))
        
        # Check for possession change
        possession_change, outcome = self._check_possession_change(event, event_index)
        
        if possession_change:
            # Store current possession team before ending it
            current_team_id = self.current_possession.team_id if self.current_possession else None
            
            # End current possession
            self._end_current_possession(outcome, event)
            
            # Start new possession for the other team
            new_team_id = self._get_opposing_team(current_team_id)
            if event.get('team_id') and event.get('team_id') != current_team_id:
                new_team_id = event.get('team_id')
            
            self._start_new_possession(new_team_id, event)
    
    def _check_possession_change(self, event: Dict[str, Any], event_index: int) -> Tuple[bool, str]:
        """
        Check if this event causes a possession change.
        Returns (possession_changed, outcome_description)
        """
        event_type = event.get('event_type', '').lower()
        
        # Made shots always change possession
        if event_type == 'made shot':
            return True, 'made_shot'
        
        # Turnovers always change possession
        if event_type == 'turnover':
            return True, 'turnover'
        
        # Rebounds - check if defensive
        if event_type == 'rebound':
            return self._check_defensive_rebound(event, event_index)
        
        # Free throws - complex logic for final FT
        if event_type == 'free throw':
            return self._check_free_throw_possession_change(event, event_index)
        
        return False, ''
    
    def _check_defensive_rebound(self, event: Dict[str, Any], event_index: int) -> Tuple[bool, str]:
        """Check if this rebound is defensive (changes possession)."""
        rebound_team = event.get('team_id')
        if not rebound_team:
            return False, ''
        
        # Look back for the most recent shot attempt
        for i in range(event_index - 1, max(0, event_index - 10), -1):
            prev_event = self.play_events[i]
            prev_type = prev_event.get('event_type', '').lower()
            
            # Found a missed shot or missed free throw
            if prev_type in ['missed shot', 'free throw']:
                # Check if it was a miss
                if prev_type == 'missed shot' or (prev_type == 'free throw' and 'miss' in prev_event.get('description', '').lower()):
                    shot_team = prev_event.get('team_id')
                    if shot_team and shot_team != rebound_team:
                        return True, 'defensive_rebound'
                    break
        
        return False, 'offensive_rebound'
    
    def _check_free_throw_possession_change(self, event: Dict[str, Any], event_index: int) -> Tuple[bool, str]:
        """Check if this free throw ends possession."""
        description = event.get('description', '')
        
        # Parse free throw number and total (e.g., "Free Throw 2 of 2")
        if 'of' in description:
            try:
                # Extract "X of Y" pattern
                parts = description.split()
                for i, part in enumerate(parts):
                    if part.lower() == 'of' and i > 0 and i < len(parts) - 1:
                        current_ft = int(parts[i-1])
                        total_ft = int(parts[i+1])
                        
                        # This is the final free throw
                        if current_ft == total_ft:
                            # If made, possession changes
                            if 'miss' not in description.lower():
                                return True, 'made_free_throw'
                            else:
                                # Missed final FT - possession determined by rebound
                                # Look ahead for rebound
                                rebound_outcome = self._look_ahead_for_rebound(event_index)
                                if rebound_outcome:
                                    return True, rebound_outcome
                        break
            except (ValueError, IndexError):
                pass
        
        return False, ''
    
    def _look_ahead_for_rebound(self, event_index: int) -> Optional[str]:
        """Look ahead for rebound after missed final free throw."""
        # Look at next few events for rebound
        for i in range(event_index + 1, min(len(self.play_events), event_index + 5)):
            next_event = self.play_events[i]
            if next_event.get('event_type', '').lower() == 'rebound':
                rebound_team = next_event.get('team_id')
                if rebound_team and rebound_team != self.current_possession.team_id:
                    return 'defensive_rebound_after_ft'
                else:
                    return 'offensive_rebound_after_ft'
        
        # Default to possession change if no rebound found
        return 'missed_free_throw_no_rebound'
    
    def _start_new_possession(self, team_id: int, event: Optional[Dict[str, Any]]):
        """Start a new possession for the given team."""
        self.possession_counter += 1
        
        if event:
            start_period = event.get('period', 1)
            start_time_remaining = event.get('time_remaining', '')
            start_seconds_elapsed = event.get('time_elapsed_seconds', 0)
        else:
            start_period = 1
            start_time_remaining = 'PT12M00.00S'
            start_seconds_elapsed = 0
        
        self.current_possession = PossessionEvent(
            possession_id=None,  # Will be set when saved to database
            game_id=self.game_id,
            possession_number=self.possession_counter,
            team_id=team_id,
            start_period=start_period,
            start_time_remaining=start_time_remaining,
            start_seconds_elapsed=start_seconds_elapsed
        )
    
    def _end_current_possession(self, outcome: str, event: Optional[Dict[str, Any]]):
        """End the current possession."""
        if not self.current_possession:
            return
        
        if event:
            self.current_possession.end_period = event.get('period')
            self.current_possession.end_time_remaining = event.get('time_remaining')
            self.current_possession.end_seconds_elapsed = event.get('time_elapsed_seconds')
        
        self.current_possession.possession_outcome = outcome
        
        # Calculate points scored during this possession
        self.current_possession.points_scored = self._calculate_points_scored()
        
        self.possessions.append(self.current_possession)
        self.current_possession = None
    
    def _calculate_points_scored(self) -> int:
        """Calculate points scored during current possession."""
        if not self.current_possession:
            return 0
        
        points = 0
        for play_id in self.current_possession.play_ids:
            # Find the play event
            for event in self.play_events:
                if event.get('event_id') == play_id:
                    # Check for scoring events
                    if event.get('event_type', '').lower() == 'made shot':
                        if event.get('shot_type') == '3PT':
                            points += 3
                        else:
                            points += 2
                    elif event.get('event_type', '').lower() == 'free throw':
                        if 'miss' not in event.get('description', '').lower():
                            points += 1
                    break
        
        return points
    
    def _get_opposing_team(self, team_id: Optional[int]) -> int:
        """Get the opposing team ID."""
        if team_id == self.home_team_id:
            return self.away_team_id
        else:
            return self.home_team_id
    
    def get_possession_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the tracked possessions."""
        if not self.possessions:
            return {}
        
        home_possessions = [p for p in self.possessions if p.team_id == self.home_team_id]
        away_possessions = [p for p in self.possessions if p.team_id == self.away_team_id]
        
        return {
            'total_possessions': len(self.possessions),
            'home_possessions': len(home_possessions),
            'away_possessions': len(away_possessions),
            'home_points_scored': sum(p.points_scored for p in home_possessions),
            'away_points_scored': sum(p.points_scored for p in away_possessions),
            'home_points_per_possession': sum(p.points_scored for p in home_possessions) / len(home_possessions) if home_possessions else 0,
            'away_points_per_possession': sum(p.points_scored for p in away_possessions) / len(away_possessions) if away_possessions else 0
        }