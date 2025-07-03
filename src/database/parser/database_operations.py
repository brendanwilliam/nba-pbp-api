"""
Database Operations Module

Handles database insertion and update operations for parsed NBA data.
This module contains all the database-specific logic separated from parsing logic.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


class DatabaseOperations:
    """
    Handles all database operations for NBA data insertion.
    
    This class provides methods for inserting various types of NBA data
    into the database while handling errors gracefully.
    """
    
    def __init__(self, db_session: Session, dry_run: bool = False):
        """
        Initialize database operations.
        
        Args:
            db_session: SQLAlchemy database session
            dry_run: If True, only simulate operations without actual database changes
        """
        self.db = db_session
        self.dry_run = dry_run
        self.stats = {
            'games_processed': 0,
            'games_skipped': 0,
            'games_failed': 0,
            'arenas_created': 0,
            'players_created': 0,
            'officials_created': 0,
            'play_events_created': 0,
            'player_stats_created': 0,
            'team_stats_created': 0,
            'periods_created': 0,
            'possessions_created': 0,
            'play_possession_links_created': 0
        }
    
    def player_exists(self, player_id: int) -> bool:
        """Check if player exists in players table."""
        if self.dry_run or not player_id:
            return True  # Assume exists in dry run
        try:
            result = self.db.execute(text("SELECT 1 FROM players WHERE id = :player_id"), {"player_id": player_id})
            return result.fetchone() is not None
        except:
            return False
    
    def team_exists_by_nba_id(self, nba_team_id: int) -> bool:
        """Check if team exists by NBA team ID."""
        if self.dry_run or not nba_team_id:
            return True
        try:
            result = self.db.execute(text("SELECT 1 FROM teams WHERE team_id = :nba_team_id"), {"nba_team_id": str(nba_team_id)})
            return result.fetchone() is not None
        except:
            return False
    
    def get_internal_team_id(self, nba_team_id: int) -> Optional[int]:
        """Get internal team ID from NBA team ID."""
        if self.dry_run or not nba_team_id:
            return None
        try:
            result = self.db.execute(text("SELECT id FROM teams WHERE team_id = :nba_team_id"), {"nba_team_id": str(nba_team_id)})
            row = result.fetchone()
            return row[0] if row else None
        except:
            return None
    
    def is_team_id(self, potential_player_id: int) -> bool:
        """Check if this ID is actually a team ID (NBA team IDs are 10 digits starting with 1610612)."""
        return potential_player_id and str(potential_player_id).startswith('1610612') and len(str(potential_player_id)) == 10
    
    def create_missing_player(self, player_data: Dict[str, Any]) -> bool:
        """Create a player record if it doesn't exist."""
        player_id = player_data.get('player_id')
        if not player_id or self.dry_run:
            return True
        
        # Skip if this is actually a team ID
        if self.is_team_id(player_id):
            return False  # Don't create players for team IDs
        
        if self.player_exists(player_id):
            return True
        
        try:
            # Extract player info from the data
            first_name = player_data.get('first_name', '')
            last_name = player_data.get('last_name', '')
            
            # If we don't have names, try to parse from full name or use placeholder
            if not first_name and not last_name:
                full_name = player_data.get('name') or f'Player {player_id}'
                if full_name:
                    name_parts = full_name.split(' ', 1)
                    first_name = name_parts[0] if len(name_parts) > 0 else 'Unknown'
                    last_name = name_parts[1] if len(name_parts) > 1 else 'Player'
                else:
                    first_name = 'Unknown'
                    last_name = f'Player {player_id}'
            
            # Handle team_id - convert NBA team ID to internal team ID
            internal_team_id = None
            nba_team_id = player_data.get('team_id')
            if nba_team_id:
                internal_team_id = self.get_internal_team_id(nba_team_id)
            
            self.db.execute(text("""
                INSERT INTO players (player_id, player_name, first_name, family_name, jersey_number, position)
                VALUES (:id, :player_name, :first_name, :family_name, :jersey_number, :position)
                ON CONFLICT (player_id) DO NOTHING
            """), {
                'id': player_id,
                'player_name': f"{first_name} {last_name}".strip(),
                'first_name': first_name,
                'family_name': last_name,
                'jersey_number': player_data.get('jersey_number'),
                'position': player_data.get('position')
            })
            
            return True
            
        except Exception as e:
            print(f"    ⚠️ Failed to create player {player_id}: {str(e)[:150]}...")
            return False
    
    def insert_arena(self, arena_data: Dict[str, Any]) -> Optional[int]:
        """Insert arena and return arena_id."""
        if not arena_data or not arena_data.get('arena_name'):
            return None
        
        # Check if arena already exists
        existing = self.db.execute(text("""
            SELECT arena_id FROM arenas 
            WHERE arena_name = :name AND arena_city = :city
        """), {
            "name": arena_data['arena_name'],
            "city": arena_data.get('arena_city')
        }).fetchone()
        
        if existing:
            return existing[0]
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create arena: {arena_data['arena_name']}")
            return 1  # Return dummy ID for dry run
        
        # Insert new arena
        result = self.db.execute(text("""
            INSERT INTO arenas (arena_name, arena_city, arena_state, arena_country, 
                               arena_timezone, arena_street_address, arena_postal_code, capacity)
            VALUES (:arena_name, :arena_city, :arena_state, :arena_country,
                    :arena_timezone, :arena_street_address, :arena_postal_code, :capacity)
            RETURNING arena_id
        """), arena_data)
        
        arena_id = result.fetchone()[0]
        self.stats['arenas_created'] += 1
        return arena_id
    
    def insert_game(self, game_data: Dict[str, Any], arena_id: Optional[int]):
        """Insert game record."""
        game_data['arena_id'] = arena_id
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create game: {game_data['game_id']}")
            return
        
        self.db.execute(text("""
            INSERT INTO games (
                game_id, game_code, game_status, game_status_text, season,
                game_date, game_time_utc, game_time_et, home_team_id, away_team_id,
                home_score, away_score, period, game_clock, duration, attendance,
                sellout, series_game_number, game_label, game_sub_label, series_text,
                if_necessary, arena_id, is_neutral
            ) VALUES (
                :game_id, :game_code, :game_status, :game_status_text, :season,
                :game_date, :game_time_utc, :game_time_et, :home_team_id, :away_team_id,
                :home_score, :away_score, :period, :game_clock, :duration, :attendance,
                :sellout, :series_game_number, :game_label, :game_sub_label, :series_text,
                :if_necessary, :arena_id, :is_neutral
            )
        """), game_data)
    
    def insert_play_events_safe(self, events: List[Dict[str, Any]]) -> int:
        """Insert play-by-play events with error counting."""
        if not events:
            return 0
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create {len(events)} play events")
            return len(events)
        
        inserted_count = 0
        error_count = 0
        
        for i, orig_event in enumerate(events):
            # Skip events with missing required foreign keys
            event = orig_event.copy()  # Don't modify original
            
            # Handle invalid IDs (0 means no player/team for these events)
            if event.get('player_id') == 0:
                event['player_id'] = None
            elif event.get('player_id') and not self.player_exists(event['player_id']):
                event['player_id'] = None
                
            if event.get('assist_player_id') == 0:
                event['assist_player_id'] = None
            elif event.get('assist_player_id') and not self.player_exists(event['assist_player_id']):
                event['assist_player_id'] = None
            
            # Handle invalid team IDs (0 means system event, not team-specific)
            if event.get('team_id') == 0:
                event['team_id'] = None
            
            try:
                # Each event gets its own transaction to avoid rollback cascading
                self.db.execute(text("""
                    INSERT INTO play_events (
                        game_id, period, time_remaining, time_elapsed_seconds,
                        event_type, event_action_type, event_sub_type, description,
                        home_score, away_score, score_margin, player_id, team_id,
                        shot_distance, shot_made, shot_type, shot_zone, shot_x, shot_y,
                        assist_player_id, event_order, video_available
                    ) VALUES (
                        :game_id, :period, :time_remaining, :time_elapsed_seconds,
                        :event_type, :event_action_type, :event_sub_type, :description,
                        :home_score, :away_score, :score_margin, :player_id, :team_id,
                        :shot_distance, :shot_made, :shot_type, :shot_zone, :shot_x, :shot_y,
                        :assist_player_id, :event_order, :video_available
                    )
                """), event)
                self.db.commit()  # Commit each event individually
                inserted_count += 1
                self.stats['play_events_created'] += 1
            except Exception as e:
                # Rollback this failed event and continue
                try:
                    self.db.rollback()
                except:
                    pass
                
                error_count += 1
                if error_count <= 5:  # Show first 5 errors with more detail
                    error_msg = str(e)
                    print(f"    ⚠️ Event {i+1} error: {error_msg[:200]}...")
                    
                    # Print the problematic event data for debugging
                    if error_count <= 2:  # Only show data for first 2 errors
                        print(f"       Event data: player_id={event.get('player_id')}, team_id={event.get('team_id')}, event_type={event.get('event_type')}")
                elif error_count == 6:
                    print(f"    ⚠️ ... and {len(events) - i - 1} more event errors (suppressed)")
                continue
        
        if error_count > 0:
            print(f"    Total event errors: {error_count}")
        
        return inserted_count
    
    def insert_team_stats(self, team_stats: List[Dict[str, Any]]):
        """Insert team game statistics."""
        if not team_stats:
            return
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create {len(team_stats)} team stat records")
            return
        
        for stats in team_stats:
            self.db.execute(text("""
                INSERT INTO team_game_stats (
                    game_id, team_id, is_home_team, stat_type, wins, losses,
                    in_bonus, timeouts_remaining, seed, minutes, field_goals_made,
                    field_goals_attempted, field_goals_percentage, three_pointers_made,
                    three_pointers_attempted, three_pointers_percentage, free_throws_made,
                    free_throws_attempted, free_throws_percentage, rebounds_offensive,
                    rebounds_defensive, rebounds_total, assists, steals, blocks,
                    turnovers, fouls_personal, points, plus_minus_points,
                    points_fast_break, points_in_paint, points_second_chance
                ) VALUES (
                    :game_id, :team_id, :is_home_team, :stat_type, :wins, :losses,
                    :in_bonus, :timeouts_remaining, :seed, :minutes, :field_goals_made,
                    :field_goals_attempted, :field_goals_percentage, :three_pointers_made,
                    :three_pointers_attempted, :three_pointers_percentage, :free_throws_made,
                    :free_throws_attempted, :free_throws_percentage, :rebounds_offensive,
                    :rebounds_defensive, :rebounds_total, :assists, :steals, :blocks,
                    :turnovers, :fouls_personal, :points, :plus_minus_points,
                    :points_fast_break, :points_in_paint, :points_second_chance
                )
            """), stats)
            self.stats['team_stats_created'] += 1
    
    def insert_player_stats_safe(self, player_stats: List[Dict[str, Any]]) -> int:
        """Insert player game statistics with error counting."""
        if not player_stats:
            return 0
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create {len(player_stats)} player stat records")
            return len(player_stats)
        
        inserted_count = 0
        error_count = 0
        
        for i, orig_stats in enumerate(player_stats):
            # Skip players that don't exist in players table
            if orig_stats.get('player_id') and not self.player_exists(orig_stats['player_id']):
                error_count += 1
                if error_count <= 3:
                    print(f"    ⚠️ Player {i+1} error: Player ID {orig_stats['player_id']} not found in players table")
                    print(f"       Will try to create missing player...")
                    # Try to create the missing player
                    player_data = {
                        'player_id': orig_stats['player_id'],
                        'team_id': orig_stats.get('team_id'),
                        'jersey_number': orig_stats.get('jersey_number'),
                        'position': orig_stats.get('position'),
                        'name': None  # We don't have name in stats
                    }
                    try:
                        if self.create_missing_player(player_data):
                            print(f"       ✅ Created missing player {orig_stats['player_id']}")
                            # Don't skip this player, continue with stats insertion
                        else:
                            continue  # Skip if creation failed
                    except:
                        continue  # Skip if creation failed
                else:
                    continue
            
            try:
                self.db.execute(text("""
                    INSERT INTO player_game_stats (
                        game_id, player_id, team_id, jersey_number, position,
                        starter, active, dnp_reason, minutes_played, field_goals_made,
                        field_goals_attempted, field_goals_percentage, three_pointers_made,
                        three_pointers_attempted, three_pointers_percentage, free_throws_made,
                        free_throws_attempted, free_throws_percentage, rebounds_offensive,
                        rebounds_defensive, rebounds_total, assists, steals, blocks,
                        turnovers, fouls_personal, points, plus_minus
                    ) VALUES (
                        :game_id, :player_id, :team_id, :jersey_number, :position,
                        :starter, :active, :dnp_reason, :minutes_played, :field_goals_made,
                        :field_goals_attempted, :field_goals_percentage, :three_pointers_made,
                        :three_pointers_attempted, :three_pointers_percentage, :free_throws_made,
                        :free_throws_attempted, :free_throws_percentage, :rebounds_offensive,
                        :rebounds_defensive, :rebounds_total, :assists, :steals, :blocks,
                        :turnovers, :fouls_personal, :points, :plus_minus
                    )
                """), orig_stats)
                inserted_count += 1
                self.stats['player_stats_created'] += 1
            except Exception as e:
                error_count += 1
                if error_count <= 3:  # Only show first 3 errors
                    print(f"    ⚠️ Player {i+1} error: {str(e)[:100]}...")
                continue
        
        if error_count > 0:
            print(f"    Total player stat errors: {error_count}")
        
        return inserted_count