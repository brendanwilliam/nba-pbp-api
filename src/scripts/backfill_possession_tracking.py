#!/usr/bin/env python3
"""
Possession Tracking Backfill Script

This script backfills possession tracking data for existing games that have
play_events but no possession_events data.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.database import get_db
    from analytics.possession_tracker import PossessionTracker
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv activated.")
    sys.exit(1)


class PossessionBackfillProcessor:
    """Backfill possession tracking for existing games."""
    
    def __init__(self, dry_run: bool = False):
        self.db = next(get_db())
        self.dry_run = dry_run
        self.stats = {
            'games_processed': 0,
            'games_failed': 0,
            'possessions_created': 0,
            'play_possession_links_created': 0
        }
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def get_games_needing_possession_data(self, limit: Optional[int] = None) -> list:
        """Get games that have play_events but no possession_events."""
        query = text("""
            SELECT DISTINCT pe.game_id, eg.home_team_id, eg.away_team_id
            FROM play_events pe
            JOIN enhanced_games eg ON pe.game_id = eg.game_id
            LEFT JOIN possession_events pev ON pe.game_id = pev.game_id
            WHERE pev.game_id IS NULL
            ORDER BY eg.game_date DESC
            LIMIT :limit
        """)
        result = self.db.execute(query, {"limit": limit or 1000000})
        return result.fetchall()
    
    def get_play_events_for_game(self, game_id: str) -> list:
        """Get all play events for a game in chronological order."""
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
        
        # Convert to dictionaries
        columns = [
            'event_id', 'game_id', 'period', 'time_remaining', 'time_elapsed_seconds',
            'event_type', 'event_action_type', 'event_sub_type', 'description',
            'home_score', 'away_score', 'score_margin', 'player_id', 'team_id',
            'shot_distance', 'shot_made', 'shot_type', 'shot_zone', 'shot_x', 'shot_y',
            'assist_player_id', 'event_order', 'possession_change', 'video_available'
        ]
        
        return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def insert_possession_events(self, possession_data: list) -> int:
        """Insert possession events into the database."""
        if not possession_data:
            return 0
        
        if self.dry_run:
            print(f"    [DRY RUN] Would create {len(possession_data)} possession events")
            return len(possession_data)
        
        inserted_count = 0
        
        for possession in possession_data:
            try:
                # Store play_ids for later use, then remove from possession data
                play_ids = possession.pop('play_ids', [])
                
                # Insert possession event
                result = self.db.execute(text("""
                    INSERT INTO possession_events (
                        game_id, possession_number, team_id, start_period, start_time_remaining,
                        start_seconds_elapsed, end_period, end_time_remaining, end_seconds_elapsed,
                        possession_outcome, points_scored
                    ) VALUES (
                        :game_id, :possession_number, :team_id, :start_period, :start_time_remaining,
                        :start_seconds_elapsed, :end_period, :end_time_remaining, :end_seconds_elapsed,
                        :possession_outcome, :points_scored
                    ) RETURNING possession_id
                """), possession)
                
                possession_id = result.fetchone()[0]
                inserted_count += 1
                self.stats['possessions_created'] += 1
                
                # Insert play-possession links
                links_created = self.insert_play_possession_links(possession_id, play_ids)
                self.stats['play_possession_links_created'] += links_created
                
                # Update play_events with possession_id
                self.update_play_events_with_possession_id(possession_id, play_ids)
                
            except Exception as e:
                print(f"    ⚠️ Error inserting possession: {str(e)[:100]}...")
                continue
        
        return inserted_count
    
    def insert_play_possession_links(self, possession_id: int, play_ids: list) -> int:
        """Insert play-possession junction table entries."""
        if not play_ids:
            return 0
        
        inserted_count = 0
        
        for play_id in play_ids:
            try:
                self.db.execute(text("""
                    INSERT INTO play_possession_events (possession_id, play_id)
                    VALUES (:possession_id, :play_id)
                    ON CONFLICT DO NOTHING
                """), {
                    'possession_id': possession_id,
                    'play_id': play_id
                })
                inserted_count += 1
            except Exception:
                continue
        
        return inserted_count
    
    def update_play_events_with_possession_id(self, possession_id: int, play_ids: list):
        """Update play_events table with possession_id references."""
        for play_id in play_ids:
            try:
                self.db.execute(text("""
                    UPDATE play_events SET possession_id = :possession_id 
                    WHERE event_id = :play_id
                """), {
                    'possession_id': possession_id,
                    'play_id': play_id
                })
            except Exception:
                continue
    
    def process_game(self, game_id: str, home_team_id: int, away_team_id: int) -> bool:
        """Process possession tracking for a single game."""
        try:
            print(f"  Processing game: {game_id}")
            
            # Get play events for this game
            play_events = self.get_play_events_for_game(game_id)
            if not play_events:
                print(f"    ⏭️ No play events found")
                return True
            
            print(f"    Found {len(play_events)} play events")
            
            # Initialize possession tracker
            tracker = PossessionTracker(game_id, home_team_id, away_team_id)
            
            # Process events to generate possessions
            possessions = tracker.process_play_events(play_events)
            
            if not possessions:
                print(f"    ⚠️ No possessions generated")
                return False
            
            print(f"    Generated {len(possessions)} possessions")
            
            # Convert to database format
            possession_data = []
            for possession in possessions:
                possession_data.append({
                    'game_id': possession.game_id,
                    'possession_number': possession.possession_number,
                    'team_id': possession.team_id,
                    'start_period': possession.start_period,
                    'start_time_remaining': possession.start_time_remaining,
                    'start_seconds_elapsed': possession.start_seconds_elapsed,
                    'end_period': possession.end_period,
                    'end_time_remaining': possession.end_time_remaining,
                    'end_seconds_elapsed': possession.end_seconds_elapsed,
                    'possession_outcome': possession.possession_outcome,
                    'points_scored': possession.points_scored,
                    'play_ids': possession.play_ids
                })
            
            # Insert possession data
            possessions_inserted = self.insert_possession_events(possession_data)
            
            if not self.dry_run:
                self.db.commit()
            
            print(f"    ✅ Inserted {possessions_inserted} possessions")
            self.stats['games_processed'] += 1
            return True
            
        except Exception as e:
            print(f"    ❌ Error processing game {game_id}: {str(e)[:150]}...")
            if not self.dry_run:
                try:
                    self.db.rollback()
                except:
                    pass
            self.stats['games_failed'] += 1
            return False
    
    def run(self, limit: Optional[int] = None):
        """Run the backfill process."""
        print(f"🏀 Possession Tracking Backfill {'(DRY RUN)' if self.dry_run else ''}")
        print("=" * 60)
        
        # Get games needing possession data
        games = self.get_games_needing_possession_data(limit)
        
        if not games:
            print("No games found needing possession data")
            return
        
        print(f"Found {len(games)} games needing possession tracking")
        print("-" * 40)
        
        # Process each game
        for game_id, home_team_id, away_team_id in games:
            self.process_game(game_id, home_team_id, away_team_id)
        
        # Print summary
        print("-" * 40)
        print("BACKFILL SUMMARY:")
        print(f"  Games processed: {self.stats['games_processed']}")
        print(f"  Games failed: {self.stats['games_failed']}")
        print(f"  Possessions created: {self.stats['possessions_created']}")
        print(f"  Play-possession links created: {self.stats['play_possession_links_created']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Backfill possession tracking for existing games')
    parser.add_argument('--limit', type=int, help='Limit number of games to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    processor = PossessionBackfillProcessor(dry_run=args.dry_run)
    
    try:
        processor.run(limit=args.limit)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        processor.close()


if __name__ == "__main__":
    main()