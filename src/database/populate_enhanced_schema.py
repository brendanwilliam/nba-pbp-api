#!/usr/bin/env python3
"""
Enhanced Schema Population Script

This script extracts JSON data from the raw_game_data table and populates
the enhanced schema tables with structured data using the modular parser system.

The script now uses the parser module for data extraction and database operations,
providing a clean separation of concerns and improved maintainability.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.database import get_db_manager
    from sqlalchemy import text, select, and_
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    
    # Import parser modules
    from database.parser import (
        extract_game_basic_info,
        extract_arena_info,
        extract_all_players,
        extract_player_stats,
        extract_team_stats,
        extract_play_events,
        extract_lineup_tracking_data,
        extract_possession_data,
        DatabaseOperations
    )
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv activated.")
    sys.exit(1)


class EnhancedSchemaPopulator:
    """
    Populate enhanced schema tables from raw JSON data using modular parser system.
    
    This class orchestrates the data extraction and insertion process by:
    1. Using parser modules to extract structured data from raw JSON
    2. Using DatabaseOperations for all database interactions
    3. Providing comprehensive error handling and progress tracking
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the populator.
        
        Args:
            dry_run: If True, only simulate operations without database changes
        """
        self.db = next(get_db())
        self.dry_run = dry_run
        self.db_ops = DatabaseOperations(self.db, dry_run)
    
    def close(self):
        """Close database connection."""
        self.db.close()
    
    def get_games_to_process(self, limit: Optional[int] = None, game_id: Optional[str] = None) -> List[tuple]:
        """
        Get games that need to be processed.
        
        Args:
            limit: Maximum number of games to process
            game_id: Specific game ID to process
            
        Returns:
            List of tuples containing (game_id, raw_json)
        """
        if game_id:
            query = text("""
                SELECT rgd.game_id, rgd.raw_json 
                FROM raw_game_data rgd
                LEFT JOIN games g ON rgd.game_id = g.game_id
                WHERE rgd.game_id = :game_id AND g.game_id IS NULL
            """)
            result = self.db.execute(query, {"game_id": game_id})
        else:
            query = text("""
                SELECT rgd.game_id, rgd.raw_json 
                FROM raw_game_data rgd
                LEFT JOIN games g ON rgd.game_id = g.game_id
                WHERE g.game_id IS NULL
                ORDER BY rgd.scraped_at DESC
                LIMIT :limit
            """)
            result = self.db.execute(query, {"limit": limit or 1000000})
        
        return result.fetchall()
    
    def process_game(self, game_id: str, raw_json: Dict[str, Any]) -> bool:
        """
        Process a single game using the modular parser system.
        
        Args:
            game_id: NBA game identifier
            raw_json: Raw JSON data from NBA.com
            
        Returns:
            Boolean indicating if processing was successful
        """
        success = True
        
        try:
            print(f"Processing game: {game_id}")
            
            # Extract all data using parser modules
            game_info = extract_game_basic_info(raw_json)
            
            # Skip if this is not valid game data
            if game_info is None:
                print(f"  ⏭️ Skipping {game_id}: No valid game data (likely schedule/template page)")
                self.db_ops.stats['games_skipped'] += 1
                return True  # This is not an error, just skip
            
            arena_info = extract_arena_info(raw_json)
            all_players = extract_all_players(raw_json)
            play_events = extract_play_events(raw_json, game_id)
            team_stats = extract_team_stats(raw_json, game_id)
            player_stats = extract_player_stats(raw_json, game_id)
            
            print(f"  Extracted: {len(all_players)} players, {len(play_events)} events, {len(team_stats)} team stats, {len(player_stats)} player stats")
            print(f"  Season: {game_info.get('season')}, Date: {game_info.get('game_date')}")
            
            # Process each section independently with error handling
            
            # 1. Insert arena first (if exists)
            arena_id = None
            if arena_info:
                try:
                    arena_id = self.db_ops.insert_arena(arena_info)
                    print(f"  ✅ Arena ID: {arena_id}")
                except Exception as e:
                    print(f"  ❌ Arena insert failed: {e}")
                    success = False
            
            # 2. Insert game
            try:
                print(f"  Inserting game...")
                self.db_ops.insert_game(game_info, arena_id)
                if not self.dry_run:
                    self.db.commit()  # Commit immediately
                print(f"  ✅ Game inserted")
            except Exception as e:
                print(f"  ❌ Game insert failed: {e}")
                if not self.dry_run:
                    self.db.rollback()
                success = False
                return False  # Can't continue without the main game record
            
            # 3. Create missing players
            try:
                print(f"  Creating missing players...")
                players_created = 0
                for player in all_players:
                    if not self.db_ops.player_exists(player['player_id']):
                        try:
                            if self.db_ops.create_missing_player(player):
                                players_created += 1
                                self.db_ops.stats['players_created'] += 1
                                if not self.dry_run:
                                    self.db.commit()  # Commit each player individually
                        except Exception as player_error:
                            if not self.dry_run:
                                try:
                                    self.db.rollback()
                                except:
                                    pass
                            # Continue with next player
                            continue
                
                # Ensure we're in a clean transaction state for next operations
                if not self.dry_run:
                    try:
                        # Force a clean transaction by doing a simple select
                        self.db.execute(text("SELECT 1"))
                        self.db.commit()
                    except:
                        try:
                            self.db.rollback()
                        except:
                            pass
                
                print(f"  ✅ Created {players_created} missing players")
            except Exception as e:
                print(f"  ❌ Player creation failed: {e}")
                if not self.dry_run:
                    try:
                        self.db.rollback()
                    except:
                        pass
                # Don't fail the whole process for player creation issues
            
            # 4. Insert play events (continue even if some fail)
            try:
                print(f"  Inserting play events...")
                events_inserted = self.db_ops.insert_play_events_safe(play_events)
                # No commit here - each event commits individually
                print(f"  ✅ Play events: {events_inserted}/{len(play_events)} inserted")
            except Exception as e:
                print(f"  ❌ Play events failed: {e}")
                if not self.dry_run:
                    try:
                        self.db.rollback()
                    except:
                        pass
                success = False
            
            # 5. Insert team stats
            try:
                print(f"  Inserting team stats...")
                self.db_ops.insert_team_stats(team_stats)
                if not self.dry_run:
                    self.db.commit()
                print(f"  ✅ Team stats inserted")
            except Exception as e:
                print(f"  ❌ Team stats failed: {e}")
                if not self.dry_run:
                    try:
                        self.db.rollback()
                    except:
                        pass
                success = False
            
            # 6. Insert player stats
            try:
                print(f"  Inserting player stats...")
                players_inserted = self.db_ops.insert_player_stats_safe(player_stats)
                if not self.dry_run:
                    self.db.commit()
                print(f"  ✅ Player stats: {players_inserted}/{len(player_stats)} inserted")
            except Exception as e:
                print(f"  ❌ Player stats failed: {e}")
                if not self.dry_run:
                    try:
                        self.db.rollback()
                    except:
                        pass
                success = False
            
            # 7. Insert analytics data (lineup tracking and possessions)
            try:
                print(f"  Extracting analytics data...")
                lineup_states, substitution_events = extract_lineup_tracking_data(raw_json, game_id)
                possession_data = extract_possession_data(raw_json, game_id)
                
                if lineup_states or substitution_events or possession_data:
                    print(f"  ✅ Analytics: {len(lineup_states)} lineups, {len(substitution_events)} subs, {len(possession_data)} possessions extracted")
                else:
                    print(f"  ⏭️ No analytics data extracted")
            except Exception as e:
                print(f"  ❌ Analytics extraction failed: {e}")
                # Don't fail the whole process for analytics issues
                print(f"  ⚠️ Continuing without analytics data")
            
            if success:
                print(f"  ✅ Game {game_id} processed successfully")
                self.db_ops.stats['games_processed'] += 1
            else:
                print(f"  ⚠️ Game {game_id} processed with some errors")
                self.db_ops.stats['games_processed'] += 1  # Still count as processed
            
            return True
            
        except Exception as e:
            print(f"  ❌ Fatal error processing game {game_id}: {e}")
            if not self.dry_run:
                try:
                    self.db.rollback()
                except:
                    pass
            self.db_ops.stats['games_failed'] += 1
            return False
    
    def run(self, limit: Optional[int] = None, game_id: Optional[str] = None):
        """
        Run the population process.
        
        Args:
            limit: Maximum number of games to process
            game_id: Specific game ID to process
        """
        print(f"🏀 Enhanced Schema Population {'(DRY RUN)' if self.dry_run else ''}")
        print("=" * 60)
        
        # Get games to process
        games = self.get_games_to_process(limit, game_id)
        
        if not games:
            print("No games found to process")
            return
        
        print(f"Found {len(games)} games to process")
        print("-" * 40)
        
        # Process each game
        for game_id, raw_json in games:
            if isinstance(raw_json, str):
                raw_json = json.loads(raw_json)
            
            self.process_game(game_id, raw_json)
        
        # Print summary
        print("-" * 40)
        print("SUMMARY:")
        print(f"  Games processed: {self.db_ops.stats['games_processed']}")
        print(f"  Games failed: {self.db_ops.stats['games_failed']}")
        print(f"  Arenas created: {self.db_ops.stats['arenas_created']}")
        print(f"  Players created: {self.db_ops.stats['players_created']}")
        print(f"  Play events created: {self.db_ops.stats['play_events_created']}")
        print(f"  Team stats created: {self.db_ops.stats['team_stats_created']}")
        print(f"  Player stats created: {self.db_ops.stats['player_stats_created']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Populate enhanced schema from raw game data')
    parser.add_argument('--limit', type=int, help='Limit number of games to process')
    parser.add_argument('--game-id', type=str, help='Process specific game ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    populator = EnhancedSchemaPopulator(dry_run=args.dry_run)
    
    try:
        populator.run(limit=args.limit, game_id=args.game_id)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        populator.close()


if __name__ == "__main__":
    main()