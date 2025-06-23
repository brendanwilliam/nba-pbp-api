#!/usr/bin/env python3
"""
Enhanced Backfill Lineup Tracking Script with Memory Monitoring

This script adds lineup tracking data to games that are already in the enhanced_games table
but don't have lineup tracking data yet, with enhanced memory monitoring and progress tracking.
"""

import sys
import json
import gc
import resource
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import argparse
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.database import SessionLocal
    from analytics.lineup_tracker import LineupTracker
    from sqlalchemy import text
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class EnhancedLineupTrackingBackfill:
    """Enhanced backfill with memory monitoring and better progress tracking"""
    
    def __init__(self, dry_run: bool = False, batch_size: int = 1000):
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.db = SessionLocal()
        self.stats = {
            'games_processed': 0,
            'games_failed': 0,
            'games_skipped': 0,
            'lineup_states_created': 0,
            'substitution_events_created': 0,
            'memory_peak_mb': 0
        }
        self.start_time = time.time()
    
    def __del__(self):
        """Close database connection"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            if sys.platform == 'darwin':  # macOS
                memory_mb = usage.ru_maxrss / (1024 * 1024)  # Convert from bytes to MB
            else:  # Linux
                memory_mb = usage.ru_maxrss / 1024  # Convert from KB to MB
            return memory_mb
        except:
            return 0.0
    
    def monitor_memory(self, game_id: str):
        """Monitor and log memory usage"""
        memory_mb = self.get_memory_usage()
        if memory_mb > self.stats['memory_peak_mb']:
            self.stats['memory_peak_mb'] = memory_mb
        
        # Warning if memory usage is high
        if memory_mb > 200:  # 200MB threshold
            print(f"    ⚠️ High memory usage: {memory_mb:.1f} MB for game {game_id}")
            # Force garbage collection
            gc.collect()
    
    def get_games_needing_lineup_data(self, limit: Optional[int] = None, game_id: Optional[str] = None) -> List[tuple]:
        """Get games that need lineup tracking data"""
        if game_id:
            query = text("""
                SELECT rgd.game_id, rgd.raw_json 
                FROM raw_game_data rgd
                INNER JOIN enhanced_games eg ON rgd.game_id = eg.game_id
                LEFT JOIN lineup_states ls ON rgd.game_id = ls.game_id
                WHERE rgd.game_id = :game_id AND ls.game_id IS NULL
            """)
            result = self.db.execute(query, {"game_id": game_id})
        else:
            query = text("""
                SELECT rgd.game_id, rgd.raw_json 
                FROM raw_game_data rgd
                INNER JOIN enhanced_games eg ON rgd.game_id = eg.game_id
                LEFT JOIN lineup_states ls ON rgd.game_id = ls.game_id
                WHERE ls.game_id IS NULL
                ORDER BY eg.game_date DESC
                LIMIT :limit
            """)
            result = self.db.execute(query, {"limit": limit or 1000000})
        
        return result.fetchall()
    
    def insert_lineup_states(self, lineup_states: List[Dict[str, Any]]) -> int:
        """Insert lineup states into the database"""
        inserted_count = 0
        error_count = 0
        
        for state in lineup_states:
            try:
                # Create lineup hash for uniqueness
                home_players = sorted(state['home_players'])
                away_players = sorted(state['away_players']) 
                lineup_hash = f"{state['game_id']}_{state['period']}_{state['seconds_elapsed']}"
                
                # Insert home team lineup
                if len(home_players) >= 5:
                    self.db.execute(text("""
                        INSERT INTO lineup_states (
                            game_id, period, clock_time, seconds_elapsed, team_id,
                            player_1_id, player_2_id, player_3_id, player_4_id, player_5_id,
                            lineup_hash
                        ) VALUES (
                            :game_id, :period, :clock_time, :seconds_elapsed, :team_id,
                            :player_1_id, :player_2_id, :player_3_id, :player_4_id, :player_5_id,
                            :lineup_hash
                        )
                    """), {
                        'game_id': state['game_id'],
                        'period': state['period'],
                        'clock_time': state['clock'],
                        'seconds_elapsed': state['seconds_elapsed'],
                        'team_id': state['home_team_id'],
                        'player_1_id': home_players[0],
                        'player_2_id': home_players[1],
                        'player_3_id': home_players[2],
                        'player_4_id': home_players[3],
                        'player_5_id': home_players[4],
                        'lineup_hash': f"{lineup_hash}_home"
                    })
                    
                # Insert away team lineup
                if len(away_players) >= 5:
                    self.db.execute(text("""
                        INSERT INTO lineup_states (
                            game_id, period, clock_time, seconds_elapsed, team_id,
                            player_1_id, player_2_id, player_3_id, player_4_id, player_5_id,
                            lineup_hash
                        ) VALUES (
                            :game_id, :period, :clock_time, :seconds_elapsed, :team_id,
                            :player_1_id, :player_2_id, :player_3_id, :player_4_id, :player_5_id,
                            :lineup_hash
                        )
                    """), {
                        'game_id': state['game_id'],
                        'period': state['period'],
                        'clock_time': state['clock'],
                        'seconds_elapsed': state['seconds_elapsed'],
                        'team_id': state['away_team_id'],
                        'player_1_id': away_players[0],
                        'player_2_id': away_players[1],
                        'player_3_id': away_players[2],
                        'player_4_id': away_players[3],
                        'player_5_id': away_players[4],
                        'lineup_hash': f"{lineup_hash}_away"
                    })
                
                inserted_count += 2  # Count both home and away lineups
                self.stats['lineup_states_created'] += 2
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"    ⚠️ Lineup state error: {str(e)[:100]}...")
                continue
        
        if error_count > 0:
            print(f"    Total lineup state errors: {error_count}")
        
        return inserted_count
    
    def insert_substitution_events(self, substitution_events: List[Dict[str, Any]]) -> int:
        """Insert substitution events into the database"""
        inserted_count = 0
        error_count = 0
        
        for event in substitution_events:
            try:
                self.db.execute(text("""
                    INSERT INTO substitution_events (
                        game_id, action_number, period, clock_time, seconds_elapsed,
                        team_id, player_out_id, player_out_name, player_in_id, player_in_name, description
                    ) VALUES (
                        :game_id, :action_number, :period, :clock_time, :seconds_elapsed,
                        :team_id, :player_out_id, :player_out_name, :player_in_id, :player_in_name, :description
                    )
                """), {
                    'game_id': event['game_id'],
                    'action_number': event['event_id'],
                    'period': event['period'],
                    'clock_time': event['clock'],
                    'seconds_elapsed': event['seconds_elapsed'],
                    'team_id': event['team_id'],
                    'player_out_id': event['player_out_id'],
                    'player_out_name': event.get('player_out_name', ''),
                    'player_in_id': event['player_in_id'],
                    'player_in_name': event.get('player_in_name', ''),
                    'description': event['event_description']
                })
                inserted_count += 1
                self.stats['substitution_events_created'] += 1
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"    ⚠️ Substitution event error: {str(e)[:100]}...")
                continue
        
        if error_count > 0:
            print(f"    Total substitution event errors: {error_count}")
        
        return inserted_count
    
    def extract_lineup_tracking_data(self, raw_json: Dict[str, Any], game_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract lineup states and substitution events using LineupTracker"""
        try:
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
            
            # Clean up tracker to free memory
            del tracker
            
            return lineup_states, substitution_events
        
        except Exception as e:
            print(f"    ⚠️ Failed to extract lineup tracking data: {str(e)[:150]}...")
            return [], []
    
    def process_game(self, game_id: str, raw_json: Dict[str, Any]) -> bool:
        """Process lineup tracking for a single game"""
        try:
            print(f"Processing lineup tracking for game: {game_id}")
            
            # Monitor memory before processing
            self.monitor_memory(game_id)
            
            # Extract lineup tracking data
            lineup_states, substitution_events = self.extract_lineup_tracking_data(raw_json, game_id)
            
            if not lineup_states and not substitution_events:
                print(f"  ⏭️ No lineup tracking data extracted")
                self.stats['games_skipped'] += 1
                return True
            
            if self.dry_run:
                print(f"  [DRY RUN] Would insert {len(lineup_states)} lineup states and {len(substitution_events)} substitution events")
                self.stats['games_processed'] += 1
                return True
            
            # Insert lineup states
            if lineup_states:
                lineup_states_inserted = self.insert_lineup_states(lineup_states)
                self.db.commit()
                print(f"  ✅ Inserted {lineup_states_inserted} lineup states")
            
            # Insert substitution events
            if substitution_events:
                substitution_events_inserted = self.insert_substitution_events(substitution_events)
                self.db.commit()
                print(f"  ✅ Inserted {substitution_events_inserted} substitution events")
            
            self.stats['games_processed'] += 1
            
            # Clean up variables to free memory
            del raw_json, lineup_states, substitution_events
            
            # Periodic garbage collection
            if self.stats['games_processed'] % 50 == 0:
                gc.collect()
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error processing game {game_id}: {e}")
            if not self.dry_run:
                try:
                    self.db.rollback()
                except:
                    pass
            self.stats['games_failed'] += 1
            return False
    
    def print_progress(self, current: int, total: int):
        """Print enhanced progress information"""
        elapsed = time.time() - self.start_time
        rate = current / elapsed if elapsed > 0 else 0
        remaining = total - current
        eta = remaining / rate if rate > 0 else 0
        memory_mb = self.get_memory_usage()
        
        print()
        print("=" * 60)
        print(f"📊 PROGRESS UPDATE - Game {current}/{total}")
        print(f"   Progress: {current/total*100:.1f}% complete")
        print(f"   Rate: {rate:.1f} games/sec")
        print(f"   ETA: {eta/60:.1f} minutes")
        print(f"   Memory: {memory_mb:.1f} MB (Peak: {self.stats['memory_peak_mb']:.1f} MB)")
        print(f"   Games processed: {self.stats['games_processed']}")
        print(f"   Games failed: {self.stats['games_failed']}")
        print(f"   Lineup states: {self.stats['lineup_states_created']:,}")
        print(f"   Substitution events: {self.stats['substitution_events_created']:,}")
        print("=" * 60)
        print()
    
    def run(self, limit: Optional[int] = None, game_id: Optional[str] = None):
        """Run the enhanced lineup tracking backfill process"""
        print(f"🏀 Enhanced Lineup Tracking Backfill {'(DRY RUN)' if self.dry_run else ''}")
        print("=" * 60)
        print(f"🔧 Memory monitoring enabled")
        print(f"🔧 Batch size: {self.batch_size}")
        print("=" * 60)
        
        # Get games to process
        games = self.get_games_needing_lineup_data(limit, game_id)
        
        if not games:
            print("No games found that need lineup tracking data")
            return
        
        print(f"Found {len(games)} games needing lineup tracking data")
        if limit:
            print(f"Processing first {limit} games")
        print("-" * 40)
        
        # Process each game
        for i, (game_id, raw_json) in enumerate(games, 1):
            if isinstance(raw_json, str):
                raw_json = json.loads(raw_json)
            
            print(f"[{i}/{len(games)}] ", end="")
            self.process_game(game_id, raw_json)
            
            # Enhanced progress update every 50 games
            if i % 50 == 0:
                self.print_progress(i, len(games))
        
        elapsed = time.time() - self.start_time
        print()
        print("=" * 60)
        print("FINAL SUMMARY:")
        print(f"  Time elapsed: {elapsed/60:.1f} minutes")
        print(f"  Games processed: {self.stats['games_processed']}")
        print(f"  Games failed: {self.stats['games_failed']}")
        print(f"  Games skipped: {self.stats['games_skipped']}")
        print(f"  Lineup states created: {self.stats['lineup_states_created']:,}")
        print(f"  Substitution events created: {self.stats['substitution_events_created']:,}")
        print(f"  Peak memory usage: {self.stats['memory_peak_mb']:.1f} MB")
        
        if self.stats['games_processed'] > 0:
            avg_rate = self.stats['games_processed'] / elapsed
            print(f"  Average rate: {avg_rate:.1f} games/sec")
        print("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Enhanced backfill lineup tracking data for enhanced games')
    parser.add_argument('--limit', type=int, help='Limit number of games to process')
    parser.add_argument('--game-id', type=str, help='Process specific game ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing (default: 1000)')
    
    args = parser.parse_args()
    
    backfiller = EnhancedLineupTrackingBackfill(dry_run=args.dry_run, batch_size=args.batch_size)
    try:
        backfiller.run(limit=args.limit, game_id=args.game_id)
    finally:
        # Ensure database connection is closed
        if hasattr(backfiller, 'db'):
            backfiller.db.close()


if __name__ == "__main__":
    main()