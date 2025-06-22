#!/usr/bin/env python3
"""
Fix Play Events Data Script

This script reprocesses existing play_events records to fix:
1. Missing shot coordinates (xLegacy/yLegacy -> shot_x/shot_y)
2. Missing shot types (2PT/3PT classification)
3. Missing time_elapsed_seconds calculations
4. Missing score backfill for non-scoring events
5. Missing possession_change detection

Run this after the Alembic migration to add the possession_change column.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.database import get_db
    from scripts.populate_enhanced_schema import EnhancedSchemaPopulator
    from sqlalchemy import text
    from sqlalchemy.orm import Session
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv activated.")
    sys.exit(1)


class PlayEventsDataFixer:
    """Fix existing play_events records with improved data processing"""
    
    def __init__(self, dry_run: bool = False):
        self.db = next(get_db())
        self.dry_run = dry_run
        self.stats = {
            'games_processed': 0,
            'events_updated': 0,
            'events_failed': 0,
            'shot_coordinates_fixed': 0,
            'shot_types_fixed': 0,
            'time_calculations_fixed': 0,
            'scores_backfilled': 0,
            'possession_changes_detected': 0
        }
        
        # Create an instance of the populator to access helper methods
        self.populator = EnhancedSchemaPopulator(dry_run=True)
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def get_games_with_play_events(self, limit: Optional[int] = None) -> List[str]:
        """Get games that have play_events to fix"""
        query = text("""
            SELECT DISTINCT game_id 
            FROM play_events 
            ORDER BY game_id
            LIMIT :limit
        """)
        result = self.db.execute(query, {"limit": limit or 1000000})
        return [row[0] for row in result.fetchall()]
    
    def get_raw_json_for_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get raw JSON data for a game"""
        query = text("SELECT raw_json FROM raw_game_data WHERE game_id = :game_id")
        result = self.db.execute(query, {"game_id": game_id})
        row = result.fetchone()
        
        if row:
            raw_json = row[0]
            if isinstance(raw_json, str):
                return json.loads(raw_json)
            return raw_json
        return None
    
    def get_play_events_for_game(self, game_id: str) -> List[Dict[str, Any]]:
        """Get existing play events for a game"""
        query = text("""
            SELECT event_id, game_id, period, time_remaining, time_elapsed_seconds,
                   event_type, event_action_type, event_sub_type, description,
                   home_score, away_score, score_margin, player_id, team_id,
                   shot_distance, shot_made, shot_type, shot_zone, shot_x, shot_y,
                   assist_player_id, event_order, possession_change, video_available
            FROM play_events 
            WHERE game_id = :game_id
            ORDER BY period, event_order
        """)
        result = self.db.execute(query, {"game_id": game_id})
        
        events = []
        for row in result.fetchall():
            events.append({
                'event_id': row[0],
                'game_id': row[1],
                'period': row[2],
                'time_remaining': row[3],
                'time_elapsed_seconds': row[4],
                'event_type': row[5],
                'event_action_type': row[6],
                'event_sub_type': row[7],
                'description': row[8],
                'home_score': row[9],
                'away_score': row[10],
                'score_margin': row[11],
                'player_id': row[12],
                'team_id': row[13],
                'shot_distance': row[14],
                'shot_made': row[15],
                'shot_type': row[16],
                'shot_zone': row[17],
                'shot_x': row[18],
                'shot_y': row[19],
                'assist_player_id': row[20],
                'event_order': row[21],
                'possession_change': row[22],
                'video_available': row[23]
            })
        
        return events
    
    def extract_action_by_event_order(self, raw_json: Dict[str, Any], event_order: int) -> Optional[Dict[str, Any]]:
        """Extract specific action from raw JSON by event order (actionNumber)"""
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        
        # Try main playByPlay location first
        play_by_play = page_props.get('playByPlay', {})
        actions = play_by_play.get('actions', [])
        
        # Fallback to game.actions
        if not actions:
            game = page_props.get('game', {})
            actions = game.get('actions', [])
        
        # Find action by actionNumber
        for action in actions:
            if action.get('actionNumber') == event_order:
                return action
        
        return None
    
    def fix_event_data(self, event: Dict[str, Any], raw_json: Dict[str, Any]) -> Dict[str, Any]:
        """Fix data for a single event using raw JSON"""
        fixed_event = event.copy()
        changes_made = []
        
        # Get the corresponding action from raw JSON
        action = self.extract_action_by_event_order(raw_json, event['event_order'])
        if not action:
            return fixed_event, []
        
        # Fix shot coordinates if missing
        if (not event.get('shot_x') or event.get('shot_x') == '0') and action.get('xLegacy'):
            fixed_event['shot_x'] = action.get('xLegacy')
            changes_made.append('shot_x')
            self.stats['shot_coordinates_fixed'] += 1
        
        if (not event.get('shot_y') or event.get('shot_y') == '0') and action.get('yLegacy'):
            fixed_event['shot_y'] = action.get('yLegacy')
            changes_made.append('shot_y')
            self.stats['shot_coordinates_fixed'] += 1
        
        # Fix shot type if missing
        if not event.get('shot_type') and action.get('shotValue'):
            shot_value = action.get('shotValue')
            if shot_value == 2:
                fixed_event['shot_type'] = '2PT'
                changes_made.append('shot_type')
                self.stats['shot_types_fixed'] += 1
            elif shot_value == 3:
                fixed_event['shot_type'] = '3PT'
                changes_made.append('shot_type')
                self.stats['shot_types_fixed'] += 1
        
        # Fix time_elapsed_seconds if missing
        if not event.get('time_elapsed_seconds') and event.get('time_remaining') and event.get('period'):
            time_elapsed = self.populator._convert_clock_to_elapsed_seconds(
                event['time_remaining'], event['period']
            )
            if time_elapsed is not None:
                fixed_event['time_elapsed_seconds'] = time_elapsed
                changes_made.append('time_elapsed_seconds')
                self.stats['time_calculations_fixed'] += 1
        
        # Fix event_sub_type if missing
        if not event.get('event_sub_type') and action.get('subType'):
            fixed_event['event_sub_type'] = action.get('subType')
            changes_made.append('event_sub_type')
        
        # Fix possession_change detection
        # For basic events (Made Shot, Turnover), use the standard detection
        possession_change = self.populator._is_possession_change_event(action)
        
        # For rebounds, we need to check if it's a defensive rebound
        if action.get('actionType', '').lower() == 'rebound':
            # We need to check if the previous event was a missed shot
            # Since we're processing one event at a time, we'll mark this for special handling
            # The reprocessing logic will need to handle this in a batch
            possession_change = None  # Will be determined in batch processing
        
        if possession_change is not None and event.get('possession_change') != possession_change:
            fixed_event['possession_change'] = possession_change
            changes_made.append('possession_change')
            if possession_change:
                self.stats['possession_changes_detected'] += 1
        
        return fixed_event, changes_made
    
    def apply_score_backfill(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply score backfill logic to events"""
        if not events:
            return events
        
        current_home_score = 0
        current_away_score = 0
        fixed_events = []
        
        for event in events:
            fixed_event = event.copy()
            changes_made = False
            
            # If event has scores, update our running totals
            if event.get('home_score') is not None and event.get('away_score') is not None:
                current_home_score = event['home_score']
                current_away_score = event['away_score']
                
                # Ensure score_margin is calculated
                expected_margin = current_home_score - current_away_score
                if event.get('score_margin') != expected_margin:
                    fixed_event['score_margin'] = expected_margin
                    changes_made = True
            else:
                # Backfill missing scores with current running totals
                if event.get('home_score') != current_home_score:
                    fixed_event['home_score'] = current_home_score
                    changes_made = True
                    
                if event.get('away_score') != current_away_score:
                    fixed_event['away_score'] = current_away_score
                    changes_made = True
                    
                expected_margin = current_home_score - current_away_score
                if event.get('score_margin') != expected_margin:
                    fixed_event['score_margin'] = expected_margin
                    changes_made = True
            
            if changes_made:
                self.stats['scores_backfilled'] += 1
            
            fixed_events.append(fixed_event)
        
        return fixed_events
    
    def update_event_in_db(self, event: Dict[str, Any]):
        """Update a single event in the database"""
        if self.dry_run:
            return
        
        try:
            self.db.execute(text("""
                UPDATE play_events SET
                    time_elapsed_seconds = :time_elapsed_seconds,
                    event_sub_type = :event_sub_type,
                    home_score = :home_score,
                    away_score = :away_score,
                    score_margin = :score_margin,
                    shot_type = :shot_type,
                    shot_x = :shot_x,
                    shot_y = :shot_y,
                    possession_change = :possession_change
                WHERE event_id = :event_id
            """), {
                'event_id': event['event_id'],
                'time_elapsed_seconds': event.get('time_elapsed_seconds'),
                'event_sub_type': event.get('event_sub_type'),
                'home_score': event.get('home_score'),
                'away_score': event.get('away_score'),
                'score_margin': event.get('score_margin'),
                'shot_type': event.get('shot_type'),
                'shot_x': event.get('shot_x'),
                'shot_y': event.get('shot_y'),
                'possession_change': event.get('possession_change', False)
            })
            self.stats['events_updated'] += 1
        except Exception as e:
            print(f"    ⚠️ Failed to update event {event['event_id']}: {str(e)[:100]}...")
            self.stats['events_failed'] += 1
    
    def process_game(self, game_id: str) -> bool:
        """Process and fix play events for a single game"""
        try:
            print(f"Processing game: {game_id}")
            
            # Get raw JSON and existing events
            raw_json = self.get_raw_json_for_game(game_id)
            if not raw_json:
                print(f"  ⚠️ No raw JSON found for game {game_id}")
                return False
            
            events = self.get_play_events_for_game(game_id)
            if not events:
                print(f"  ⚠️ No play events found for game {game_id}")
                return False
            
            print(f"  Found {len(events)} events to process")
            
            # Extract raw actions for possession change detection
            props = raw_json.get('props', {})
            page_props = props.get('pageProps', {})
            play_by_play = page_props.get('playByPlay', {})
            actions = play_by_play.get('actions', [])
            if not actions:
                game = page_props.get('game', {})
                actions = game.get('actions', [])
            
            # Create a map of event_order to actions for easy lookup
            action_map = {action.get('actionNumber'): action for action in actions}
            
            # Fix individual event data
            fixed_events = []
            total_changes = 0
            previous_action = None
            
            for i, event in enumerate(events):
                fixed_event, changes_made = self.fix_event_data(event, raw_json)
                
                # Handle defensive rebound detection
                if event.get('event_type', '').lower() == 'rebound':
                    action = action_map.get(event.get('event_order'))
                    if action and previous_action:
                        # Check if previous action was a missed shot
                        if previous_action.get('actionType', '').lower() == 'missed shot':
                            # Check if team changed (defensive rebound)
                            if action.get('teamTricode') != previous_action.get('teamTricode'):
                                if not fixed_event.get('possession_change'):
                                    fixed_event['possession_change'] = True
                                    changes_made.append('possession_change')
                                    self.stats['possession_changes_detected'] += 1
                
                # Keep track of previous action
                if event.get('event_order') and event['event_order'] in action_map:
                    previous_action = action_map[event['event_order']]
                
                if changes_made:
                    total_changes += len(changes_made)
                fixed_events.append(fixed_event)
            
            # Apply score backfill
            fixed_events = self.apply_score_backfill(fixed_events)
            
            # Update events in database
            if not self.dry_run:
                for fixed_event in fixed_events:
                    self.update_event_in_db(fixed_event)
                self.db.commit()
            
            print(f"  ✅ Fixed {total_changes} individual field issues")
            self.stats['games_processed'] += 1
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to process game {game_id}: {str(e)[:150]}...")
            if not self.dry_run:
                try:
                    self.db.rollback()
                except:
                    pass
            return False
    
    def run(self, limit: Optional[int] = None):
        """Run the data fixing process"""
        print(f"🔧 Play Events Data Fix {'(DRY RUN)' if self.dry_run else ''}")
        print("=" * 60)
        
        # Get games to process
        games = self.get_games_with_play_events(limit)
        
        if not games:
            print("No games found with play events to fix")
            return
        
        print(f"Found {len(games)} games with play events to process")
        print("-" * 40)
        
        # Process each game
        for game_id in games:
            self.process_game(game_id)
        
        # Print summary
        print("-" * 40)
        print("SUMMARY:")
        print(f"  Games processed: {self.stats['games_processed']}")
        print(f"  Events updated: {self.stats['events_updated']}")
        print(f"  Events failed: {self.stats['events_failed']}")
        print(f"  Shot coordinates fixed: {self.stats['shot_coordinates_fixed']}")
        print(f"  Shot types fixed: {self.stats['shot_types_fixed']}")
        print(f"  Time calculations fixed: {self.stats['time_calculations_fixed']}")
        print(f"  Scores backfilled: {self.stats['scores_backfilled']}")
        print(f"  Possession changes detected: {self.stats['possession_changes_detected']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Fix existing play_events data')
    parser.add_argument('--limit', type=int, help='Limit number of games to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    fixer = PlayEventsDataFixer(dry_run=args.dry_run)
    
    try:
        fixer.run(limit=args.limit)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        fixer.close()


if __name__ == "__main__":
    main()