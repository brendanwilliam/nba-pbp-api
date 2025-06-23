#!/usr/bin/env python3
"""
Data Population Script - Migrate raw_game_data to Enhanced Schema

This script extracts JSON data from the raw_game_data table and populates
the enhanced schema tables with structured data.
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
    from core.database import get_db
    from analytics.lineup_tracker import LineupTracker
    from sqlalchemy import text, select, and_
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv activated.")
    sys.exit(1)


class EnhancedSchemaPopulator:
    """Populate enhanced schema tables from raw JSON data"""
    
    def __init__(self, dry_run: bool = False):
        self.db = next(get_db())
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
            'periods_created': 0
        }
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def player_exists(self, player_id: int) -> bool:
        """Check if player exists in players table"""
        if self.dry_run or not player_id:
            return True  # Assume exists in dry run
        try:
            result = self.db.execute(text("SELECT 1 FROM players WHERE id = :player_id"), {"player_id": player_id})
            return result.fetchone() is not None
        except:
            return False
    
    def team_exists_by_nba_id(self, nba_team_id: int) -> bool:
        """Check if team exists by NBA team ID"""
        if self.dry_run or not nba_team_id:
            return True
        try:
            result = self.db.execute(text("SELECT 1 FROM teams WHERE nba_team_id = :nba_team_id"), {"nba_team_id": str(nba_team_id)})
            return result.fetchone() is not None
        except:
            return False
    
    def get_internal_team_id(self, nba_team_id: int) -> Optional[int]:
        """Get internal team ID from NBA team ID"""
        if self.dry_run or not nba_team_id:
            return None
        try:
            result = self.db.execute(text("SELECT id FROM teams WHERE nba_team_id = :nba_team_id"), {"nba_team_id": str(nba_team_id)})
            row = result.fetchone()
            return row[0] if row else None
        except:
            return None
    
    def is_team_id(self, potential_player_id: int) -> bool:
        """Check if this ID is actually a team ID (NBA team IDs are 10 digits starting with 1610612)"""
        return potential_player_id and str(potential_player_id).startswith('1610612') and len(str(potential_player_id)) == 10
    
    def create_missing_player(self, player_data: Dict[str, Any]) -> bool:
        """Create a player record if it doesn't exist"""
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
                INSERT INTO players (id, nba_id, first_name, last_name, jersey_number, position, team_id)
                VALUES (:id, :nba_id, :first_name, :last_name, :jersey_number, :position, :team_id)
                ON CONFLICT (id) DO NOTHING
            """), {
                'id': player_id,
                'nba_id': str(player_id),  # Use same as id for now
                'first_name': first_name,
                'last_name': last_name,
                'jersey_number': player_data.get('jersey_number'),
                'position': player_data.get('position'),
                'team_id': internal_team_id
            })
            
            return True
            
        except Exception as e:
            print(f"    ⚠️ Failed to create player {player_id}: {str(e)[:150]}...")
            # Print debug info for failed players
            print(f"       Debug: first_name='{first_name}', last_name='{last_name}', name='{player_data.get('name')}', team_id={player_data.get('team_id')}")
            return False
    
    def get_games_to_process(self, limit: Optional[int] = None, game_id: Optional[str] = None) -> List[tuple]:
        """Get games that need to be processed"""
        if game_id:
            query = text("""
                SELECT rgd.game_id, rgd.raw_json 
                FROM raw_game_data rgd
                LEFT JOIN enhanced_games eg ON rgd.game_id = eg.game_id
                WHERE rgd.game_id = :game_id AND eg.game_id IS NULL
            """)
            result = self.db.execute(query, {"game_id": game_id})
        else:
            query = text("""
                SELECT rgd.game_id, rgd.raw_json 
                FROM raw_game_data rgd
                LEFT JOIN enhanced_games eg ON rgd.game_id = eg.game_id
                WHERE eg.game_id IS NULL
                ORDER BY rgd.scraped_at DESC
                LIMIT :limit
            """)
            result = self.db.execute(query, {"limit": limit or 1000000})
        
        return result.fetchall()
    
    def extract_game_basic_info(self, raw_json: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic game information"""
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        # If no game object exists, this is likely a schedule/template page, not actual game data
        if not game or not game.get('gameId'):
            return None
        
        # Convert sellout to boolean (handle various formats)
        sellout_value = game.get('sellout')
        if isinstance(sellout_value, (int, str)):
            sellout = sellout_value in (1, '1', 'true', 'True', True)
        else:
            sellout = bool(sellout_value) if sellout_value is not None else False
        
        # Convert if_necessary to boolean
        if_necessary_value = game.get('ifNecessary')
        if isinstance(if_necessary_value, (int, str)):
            if_necessary = if_necessary_value in (1, '1', 'true', 'True', True)
        else:
            if_necessary = bool(if_necessary_value) if if_necessary_value is not None else False
        
        # Parse game_date first (we'll need it for season derivation)
        game_date = game.get('gameDate')
        parsed_game_date = None
        
        # Try to extract date from game_time_utc if gameDate is missing
        if not game_date:
            game_time_utc = game.get('gameTimeUTC')
            if game_time_utc:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(game_time_utc.replace('Z', '+00:00'))
                    parsed_game_date = dt.date()
                    game_date = dt.strftime('%Y-%m-%d')  # For season calculation
                except ValueError:
                    pass
        
        if isinstance(game_date, str) and game_date and not parsed_game_date:
            try:
                # Convert from string format like "2004-03-20" to date
                from datetime import datetime
                parsed_game_date = datetime.strptime(game_date[:10], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Extract or derive season
        season = game.get('season')
        if not season:
            # Try to derive from game_id (format: 0020300999 = 2003-04 season)
            game_id = game.get('gameId', '')
            if game_id and len(game_id) >= 5:
                try:
                    year = int(game_id[1:5])  # Extract year from game_id (2003)
                    season = f"{year}-{str(year+1)[2:]}"  # Convert to season format (e.g., "2003-04")
                except (ValueError, IndexError):
                    season = None
            
            # Fallback: derive from date if available
            if not season and game_date:
                try:
                    date_year = int(game_date[:4])
                    # NBA season spans two years, games after June are next season
                    month = int(game_date[5:7]) if len(game_date) >= 7 else 12
                    if month >= 7:  # July onwards is new season
                        season = f"{date_year}-{str(date_year+1)[2:]}"
                    else:  # January-June is previous season
                        season = f"{date_year-1}-{str(date_year)[2:]}"
                except (ValueError, IndexError):
                    season = "unknown"
            
            if not season:
                season = "unknown"
        
        return {
            'game_id': game.get('gameId'),
            'game_code': game.get('gameCode'),
            'game_status': game.get('gameStatus'),
            'game_status_text': game.get('gameStatusText'),
            'season': season,
            'game_date': parsed_game_date,
            'game_time_utc': game.get('gameTimeUTC'),
            'game_time_et': game.get('gameTimeET'),
            'home_team_id': game.get('homeTeam', {}).get('teamId'),
            'away_team_id': game.get('awayTeam', {}).get('teamId'),
            'home_score': game.get('homeTeam', {}).get('score'),
            'away_score': game.get('awayTeam', {}).get('score'),
            'period': game.get('period'),
            'game_clock': game.get('gameClock'),
            'duration': game.get('duration'),
            'attendance': game.get('attendance'),
            'sellout': sellout,
            'series_game_number': game.get('seriesGameNumber'),
            'game_label': game.get('gameLabel'),
            'game_sub_label': game.get('gameSubLabel'),
            'series_text': game.get('seriesText'),
            'if_necessary': if_necessary,
            'is_neutral': bool(game.get('neutralSite', False))
        }
    
    def extract_arena_info(self, raw_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract arena information"""
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        arena = game.get('arena', {})
        
        if not arena.get('arenaName'):
            return None
            
        return {
            'arena_name': arena.get('arenaName'),
            'arena_city': arena.get('arenaCity'),
            'arena_state': arena.get('arenaState'),
            'arena_country': arena.get('arenaCountry', 'US'),
            'arena_timezone': arena.get('arenaTimezone'),
            'arena_street_address': arena.get('arenaStreetAddress'),
            'arena_postal_code': arena.get('arenaPostalCode'),
            'capacity': arena.get('capacity')
        }
    
    def extract_play_events(self, raw_json: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
        """Extract play-by-play events with enhanced data processing"""
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        
        # Try main playByPlay location first
        play_by_play = page_props.get('playByPlay', {})
        actions = play_by_play.get('actions', [])
        
        # Fallback to game.actions
        if not actions:
            game = page_props.get('game', {})
            actions = game.get('actions', [])
        
        events = []
        
        for action in actions:
            # Convert score strings to integers
            home_score = action.get('scoreHome')
            away_score = action.get('scoreAway')
            try:
                home_score = int(home_score) if home_score and home_score != '' else None
            except (ValueError, TypeError):
                home_score = None
            try:
                away_score = int(away_score) if away_score and away_score != '' else None
            except (ValueError, TypeError):
                away_score = None
            
            # Calculate score margin
            score_margin = None
            if home_score is not None and away_score is not None:
                score_margin = home_score - away_score
            
            # Extract shot coordinates from xLegacy/yLegacy
            shot_x = action.get('xLegacy')
            shot_y = action.get('yLegacy')
            
            # Determine shot type from shotValue (2 or 3 points)
            shot_type = None
            shot_value = action.get('shotValue')
            if shot_value == 2:
                shot_type = '2PT'
            elif shot_value == 3:
                shot_type = '3PT'
            
            # Calculate time elapsed seconds from clock
            time_elapsed_seconds = None
            clock = action.get('clock')
            period = action.get('period', 1)
            if clock and isinstance(clock, str):
                time_elapsed_seconds = self._convert_clock_to_elapsed_seconds(clock, period)
            
            # Get event sub type from subType field
            event_sub_type = action.get('subType')
            
            # Determine possession change events
            possession_change = self._is_possession_change_event(action)
            
            # Special handling for rebounds - check if it's a defensive rebound
            if action.get('actionType', '').lower() == 'rebound':
                # Look back for the most recent shot attempt (could be separated by blocks)
                last_shot_team = None
                
                # Find current action index in the actions array
                current_idx = None
                for idx, a in enumerate(actions):
                    if a.get('actionNumber') == action.get('actionNumber'):
                        current_idx = idx
                        break
                
                if current_idx is not None:
                    # Search backwards through recent actions (up to 5 events)
                    for j in range(current_idx-1, max(0, current_idx-6), -1):
                        prev_action = actions[j]
                        prev_type = prev_action.get('actionType', '').lower()
                        
                        # Check for missed shots or missed free throws
                        if prev_type == 'missed shot':
                            last_shot_team = prev_action.get('teamTricode')
                            break
                        elif prev_type == 'free throw':
                            if 'miss' in prev_action.get('description', '').lower():
                                last_shot_team = prev_action.get('teamTricode')
                                break
                
                # If we found a recent shot and teams are different, it's a defensive rebound
                if last_shot_team and action.get('teamTricode') and action.get('teamTricode') != last_shot_team:
                    possession_change = True
            
            events.append({
                'game_id': game_id,
                'period': action.get('period'),
                'time_remaining': action.get('clock'),
                'time_elapsed_seconds': time_elapsed_seconds,
                'event_type': action.get('actionType'),
                'event_action_type': action.get('subType'),
                'event_sub_type': event_sub_type,
                'description': action.get('description'),
                'home_score': home_score,
                'away_score': away_score,
                'score_margin': score_margin,
                'player_id': action.get('personId'),
                'team_id': action.get('teamId'),
                'shot_distance': action.get('shotDistance'),
                'shot_made': action.get('shotResult') == 'Made' if action.get('shotResult') else None,
                'shot_type': shot_type,
                'shot_zone': action.get('shotZone'),
                'shot_x': shot_x,
                'shot_y': shot_y,
                'assist_player_id': action.get('assistPersonId'),
                'event_order': action.get('actionNumber'),
                'possession_change': possession_change,
                'video_available': action.get('isVideoAvailable', False),
                # Store team tricode for later processing if needed
                '_team_tricode': action.get('teamTricode')
            })
        
        # Apply score backfill logic
        events = self._backfill_scores(events)
        
        return events
    
    def extract_team_stats(self, raw_json: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
        """Extract team game statistics"""
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        team_stats = []
        
        for is_home, team_key in [(True, 'homeTeam'), (False, 'awayTeam')]:
            team = game.get(team_key, {})
            statistics = team.get('statistics', {})
            
            # Convert in_bonus to boolean
            in_bonus_value = team.get('inBonus')
            if isinstance(in_bonus_value, str):
                in_bonus = in_bonus_value.lower() in ('true', '1', 'yes') if in_bonus_value else False
            else:
                in_bonus = bool(in_bonus_value) if in_bonus_value is not None else False
            
            # Convert team minutes from "MM:SS" format to total seconds
            team_minutes_str = statistics.get('minutes')
            team_minutes = None
            if team_minutes_str and isinstance(team_minutes_str, str):
                try:
                    if ':' in team_minutes_str:
                        parts = team_minutes_str.split(':')
                        team_minutes = int(parts[0]) * 60 + int(parts[1])  # Convert to seconds
                    else:
                        team_minutes = int(float(team_minutes_str) * 60)  # Assume decimal minutes
                except (ValueError, IndexError):
                    team_minutes = None
            
            team_stats.append({
                'game_id': game_id,
                'team_id': team.get('teamId'),
                'is_home_team': is_home,
                'stat_type': 'team',
                'wins': team.get('wins'),
                'losses': team.get('losses'),
                'in_bonus': in_bonus,
                'timeouts_remaining': team.get('timeoutsRemaining'),
                'seed': team.get('seed'),
                'minutes': team_minutes,
                'field_goals_made': statistics.get('fieldGoalsMade'),
                'field_goals_attempted': statistics.get('fieldGoalsAttempted'),
                'field_goals_percentage': statistics.get('fieldGoalsPercentage'),
                'three_pointers_made': statistics.get('threePointersMade'),
                'three_pointers_attempted': statistics.get('threePointersAttempted'),
                'three_pointers_percentage': statistics.get('threePointersPercentage'),
                'free_throws_made': statistics.get('freeThrowsMade'),
                'free_throws_attempted': statistics.get('freeThrowsAttempted'),
                'free_throws_percentage': statistics.get('freeThrowsPercentage'),
                'rebounds_offensive': statistics.get('reboundsOffensive'),
                'rebounds_defensive': statistics.get('reboundsDefensive'),
                'rebounds_total': statistics.get('reboundsTotal'),
                'assists': statistics.get('assists'),
                'steals': statistics.get('steals'),
                'blocks': statistics.get('blocks'),
                'turnovers': statistics.get('turnovers'),
                'fouls_personal': statistics.get('foulsPersonal'),
                'points': team.get('score'),
                'plus_minus_points': statistics.get('plusMinusPoints'),
                'points_fast_break': statistics.get('pointsFastBreak'),
                'points_in_paint': statistics.get('pointsInPaint'),
                'points_second_chance': statistics.get('pointsSecondChance')
            })
        
        return team_stats
    
    def extract_player_stats(self, raw_json: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
        """Extract player game statistics"""
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        player_stats = []
        
        for team_key in ['homeTeam', 'awayTeam']:
            team = game.get(team_key, {})
            team_id = team.get('teamId')
            players = team.get('players', [])
            
            for player in players:
                statistics = player.get('statistics', {})
                
                # Convert minutes from "MM:SS" format to total seconds
                minutes_str = statistics.get('minutes')
                minutes_played = None
                if minutes_str and isinstance(minutes_str, str):
                    try:
                        if ':' in minutes_str:
                            parts = minutes_str.split(':')
                            minutes_played = int(parts[0]) * 60 + int(parts[1])  # Convert to seconds
                        else:
                            minutes_played = int(float(minutes_str) * 60)  # Assume decimal minutes
                    except (ValueError, IndexError):
                        minutes_played = None
                
                player_stats.append({
                    'game_id': game_id,
                    'player_id': player.get('personId'),
                    'team_id': team_id,
                    'jersey_number': player.get('jerseyNum'),
                    'position': player.get('position'),
                    'starter': player.get('starter', False),
                    'active': player.get('played', True),
                    'dnp_reason': player.get('notPlayingReason'),
                    'minutes_played': minutes_played,
                    'field_goals_made': statistics.get('fieldGoalsMade'),
                    'field_goals_attempted': statistics.get('fieldGoalsAttempted'),
                    'field_goals_percentage': statistics.get('fieldGoalsPercentage'),
                    'three_pointers_made': statistics.get('threePointersMade'),
                    'three_pointers_attempted': statistics.get('threePointersAttempted'),
                    'three_pointers_percentage': statistics.get('threePointersPercentage'),
                    'free_throws_made': statistics.get('freeThrowsMade'),
                    'free_throws_attempted': statistics.get('freeThrowsAttempted'),
                    'free_throws_percentage': statistics.get('freeThrowsPercentage'),
                    'rebounds_offensive': statistics.get('reboundsOffensive'),
                    'rebounds_defensive': statistics.get('reboundsDefensive'),
                    'rebounds_total': statistics.get('reboundsTotal'),
                    'assists': statistics.get('assists'),
                    'steals': statistics.get('steals'),
                    'blocks': statistics.get('blocks'),
                    'turnovers': statistics.get('turnovers'),
                    'fouls_personal': statistics.get('foulsPersonal'),
                    'points': statistics.get('points'),
                    'plus_minus': statistics.get('plusMinus')
                })
        
        return player_stats
    
    def extract_all_players(self, raw_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all player information from game data for player creation"""
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        game = page_props.get('game', {})
        
        all_players = []
        
        # Extract players from team rosters
        for team_key in ['homeTeam', 'awayTeam']:
            team = game.get(team_key, {})
            team_id = team.get('teamId')
            players = team.get('players', [])
            
            for player in players:
                all_players.append({
                    'player_id': player.get('personId'),
                    'name': player.get('name'),
                    'first_name': player.get('firstName'),
                    'last_name': player.get('familyName'),
                    'jersey_number': player.get('jerseyNum'),
                    'position': player.get('position'),
                    'team_id': team_id
                })
        
        # Also extract players from play-by-play events
        play_by_play = page_props.get('playByPlay', {})
        actions = play_by_play.get('actions', [])
        
        # Fallback to game.actions
        if not actions:
            actions = game.get('actions', [])
        
        # Track unique player IDs from events
        event_players = {}
        for action in actions:
            # Main player
            if action.get('personId'):
                event_players[action['personId']] = {
                    'player_id': action.get('personId'),
                    'name': action.get('playerName', ''),
                    'team_id': action.get('teamId')
                }
            
            # Assist player
            if action.get('assistPersonId'):
                event_players[action['assistPersonId']] = {
                    'player_id': action.get('assistPersonId'),
                    'name': action.get('assistPlayerName', ''),
                    'team_id': action.get('teamId')
                }
        
        # Add event players to the list
        for player_data in event_players.values():
            if player_data['player_id'] and not any(p.get('player_id') == player_data['player_id'] for p in all_players):
                all_players.append(player_data)
        
        return [p for p in all_players if p.get('player_id')]
    
    def insert_arena(self, arena_data: Dict[str, Any]) -> Optional[int]:
        """Insert arena and return arena_id"""
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
    
    def insert_enhanced_game(self, game_data: Dict[str, Any], arena_id: Optional[int]):
        """Insert enhanced game record"""
        game_data['arena_id'] = arena_id
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create enhanced_game: {game_data['game_id']}")
            return
        
        self.db.execute(text("""
            INSERT INTO enhanced_games (
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
    
    def insert_play_events(self, events: List[Dict[str, Any]]):
        """Insert play-by-play events"""
        if not events:
            return
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create {len(events)} play events")
            return
        
        for i, event in enumerate(events):
            try:
                self.db.execute(text("""
                    INSERT INTO play_events (
                        game_id, period, time_remaining, time_elapsed_seconds,
                        event_type, event_action_type, event_sub_type, description,
                        home_score, away_score, score_margin, player_id, team_id,
                        shot_distance, shot_made, shot_type, shot_zone, shot_x, shot_y,
                        assist_player_id, event_order, possession_change, video_available
                    ) VALUES (
                        :game_id, :period, :time_remaining, :time_elapsed_seconds,
                        :event_type, :event_action_type, :event_sub_type, :description,
                        :home_score, :away_score, :score_margin, :player_id, :team_id,
                        :shot_distance, :shot_made, :shot_type, :shot_zone, :shot_x, :shot_y,
                        :assist_player_id, :event_order, :possession_change, :video_available
                    )
                """), event)
                self.stats['play_events_created'] += 1
            except Exception as e:
                # Log the specific error and continue
                print(f"    ⚠️ Skipping event {i+1}: {e}")
                continue
    
    def insert_play_events_safe(self, events: List[Dict[str, Any]]) -> int:
        """Insert play-by-play events with error counting"""
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
                        assist_player_id, event_order, possession_change, video_available
                    ) VALUES (
                        :game_id, :period, :time_remaining, :time_elapsed_seconds,
                        :event_type, :event_action_type, :event_sub_type, :description,
                        :home_score, :away_score, :score_margin, :player_id, :team_id,
                        :shot_distance, :shot_made, :shot_type, :shot_zone, :shot_x, :shot_y,
                        :assist_player_id, :event_order, :possession_change, :video_available
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
        """Insert team game statistics"""
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
    
    def insert_player_stats(self, player_stats: List[Dict[str, Any]]):
        """Insert player game statistics"""
        if not player_stats:
            return
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create {len(player_stats)} player stat records")
            return
        
        for stats in player_stats:
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
                """), stats)
                self.stats['player_stats_created'] += 1
            except IntegrityError:
                # Skip players that don't exist in players table
                continue
    
    def insert_player_stats_safe(self, player_stats: List[Dict[str, Any]]) -> int:
        """Insert player game statistics with error counting"""
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
    
    def _convert_clock_to_elapsed_seconds(self, clock: str, period: int) -> Optional[int]:
        """Convert NBA clock format (PT12M34.56S) to elapsed seconds from game start"""
        try:
            # Remove PT prefix and parse
            if clock.startswith('PT'):
                clock = clock[2:]
            
            # Extract minutes and seconds
            if 'M' in clock and 'S' in clock:
                parts = clock.replace('S', '').split('M')
                minutes_remaining = int(parts[0])
                seconds_remaining = float(parts[1])
                
                # Convert to total seconds remaining in period
                total_remaining = minutes_remaining * 60 + seconds_remaining
                
                # Calculate elapsed seconds from game start
                # Each period is 12 minutes (720 seconds) for regular periods
                period_length = 720  # 12 minutes in seconds
                overtime_length = 300  # 5 minutes in seconds for OT
                
                elapsed_in_game = 0
                
                # Add completed periods
                for p in range(1, period):
                    if p <= 4:
                        elapsed_in_game += period_length
                    else:
                        elapsed_in_game += overtime_length
                
                # Add elapsed time in current period
                if period <= 4:
                    elapsed_in_period = period_length - total_remaining
                else:
                    elapsed_in_period = overtime_length - total_remaining
                
                elapsed_in_game += elapsed_in_period
                
                return int(elapsed_in_game)
            
        except (ValueError, IndexError, TypeError):
            pass
        
        return None
    
    def _is_possession_change_event(self, action: Dict[str, Any]) -> bool:
        """Determine if an event represents a change of possession"""
        action_type = action.get('actionType', '').lower()
        
        # Made field goals change possession
        if action_type == 'made shot':
            return True
        
        # Turnovers change possession (includes steals and fouls that cause turnovers)
        if action_type == 'turnover':
            return True
        
        # Defensive rebounds change possession
        # Note: We'll need to check if previous action was a missed shot and team changed
        # This requires access to the previous action, which we'll handle in extract_play_events
        if action_type == 'rebound':
            # For now, just return False - we'll handle DREB detection in extract_play_events
            return False
        
        return False
    
    def _backfill_scores(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Backfill missing scores for events that don't have score changes"""
        if not events:
            return events
        
        # Sort events by period and then by event order to ensure chronological processing
        sorted_events = sorted(events, key=lambda x: (x.get('period', 0), x.get('event_order', 0)))
        
        current_home_score = 0
        current_away_score = 0
        
        for event in sorted_events:
            # If event has scores, update our running totals
            if event.get('home_score') is not None and event.get('away_score') is not None:
                current_home_score = event['home_score']
                current_away_score = event['away_score']
                
                # Ensure score_margin is calculated
                if event.get('score_margin') is None:
                    event['score_margin'] = current_home_score - current_away_score
            else:
                # Backfill missing scores with current running totals
                event['home_score'] = current_home_score
                event['away_score'] = current_away_score
                event['score_margin'] = current_home_score - current_away_score
        
        return sorted_events
    
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
                self.stats['lineup_states_created'] = self.stats.get('lineup_states_created', 0) + 2
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
                self.stats['substitution_events_created'] = self.stats.get('substitution_events_created', 0) + 1
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
            
            return lineup_states, substitution_events
        
        except Exception as e:
            print(f"    ⚠️ Failed to extract lineup tracking data: {str(e)[:150]}...")
            return [], []
    
    def process_game(self, game_id: str, raw_json: Dict[str, Any]) -> bool:
        """Process a single game"""
        success = True
        
        try:
            print(f"Processing game: {game_id}")
            
            # Extract all data
            game_info = self.extract_game_basic_info(raw_json)
            
            # Skip if this is not valid game data
            if game_info is None:
                print(f"  ⏭️ Skipping {game_id}: No valid game data (likely schedule/template page)")
                self.stats['games_skipped'] += 1
                return True  # This is not an error, just skip
            
            arena_info = self.extract_arena_info(raw_json)
            all_players = self.extract_all_players(raw_json)
            play_events = self.extract_play_events(raw_json, game_id)
            team_stats = self.extract_team_stats(raw_json, game_id)
            player_stats = self.extract_player_stats(raw_json, game_id)
            
            print(f"  Extracted: {len(all_players)} players, {len(play_events)} events, {len(team_stats)} team stats, {len(player_stats)} player stats")
            print(f"  Season: {game_info.get('season')}, Date: {game_info.get('game_date')}")
            
            # Process each section independently with error handling
            
            # 1. Insert arena first (if exists)
            arena_id = None
            if arena_info:
                try:
                    arena_id = self.insert_arena(arena_info)
                    print(f"  ✅ Arena ID: {arena_id}")
                except Exception as e:
                    print(f"  ❌ Arena insert failed: {e}")
                    success = False
            
            # 2. Insert enhanced game
            try:
                print(f"  Inserting enhanced_game...")
                self.insert_enhanced_game(game_info, arena_id)
                if not self.dry_run:
                    self.db.commit()  # Commit immediately
                print(f"  ✅ Enhanced game inserted")
            except Exception as e:
                print(f"  ❌ Enhanced game insert failed: {e}")
                if not self.dry_run:
                    self.db.rollback()
                success = False
                return False  # Can't continue without the main game record
            
            # 2.5. Create missing players
            try:
                print(f"  Creating missing players...")
                players_created = 0
                for player in all_players:
                    if not self.player_exists(player['player_id']):
                        try:
                            if self.create_missing_player(player):
                                players_created += 1
                                self.stats['players_created'] += 1
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
            
            # 3. Insert play events (continue even if some fail)
            try:
                print(f"  Inserting play events...")
                events_inserted = self.insert_play_events_safe(play_events)
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
            
            # 4. Insert team stats
            try:
                print(f"  Inserting team stats...")
                self.insert_team_stats(team_stats)
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
            
            # 5. Insert player stats
            try:
                print(f"  Inserting player stats...")
                players_inserted = self.insert_player_stats_safe(player_stats)
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
            
            # 6. Insert lineup tracking data
            try:
                print(f"  Extracting lineup tracking data...")
                lineup_states, substitution_events = self.extract_lineup_tracking_data(raw_json, game_id)
                
                if lineup_states or substitution_events:
                    print(f"  Inserting lineup states...")
                    lineup_states_inserted = self.insert_lineup_states(lineup_states)
                    if not self.dry_run:
                        self.db.commit()
                    
                    print(f"  Inserting substitution events...")
                    substitution_events_inserted = self.insert_substitution_events(substitution_events)
                    if not self.dry_run:
                        self.db.commit()
                    
                    print(f"  ✅ Lineup tracking: {lineup_states_inserted} states, {substitution_events_inserted} events inserted")
                else:
                    print(f"  ⏭️ No lineup tracking data extracted")
            except Exception as e:
                print(f"  ❌ Lineup tracking failed: {e}")
                if not self.dry_run:
                    try:
                        self.db.rollback()
                    except:
                        pass
                # Don't fail the whole process for lineup tracking issues
                print(f"  ⚠️ Continuing without lineup tracking data")
            
            if success:
                print(f"  ✅ Game {game_id} processed successfully")
                self.stats['games_processed'] += 1
            else:
                print(f"  ⚠️ Game {game_id} processed with some errors")
                self.stats['games_processed'] += 1  # Still count as processed
            
            return True
            
        except Exception as e:
            print(f"  ❌ Fatal error processing game {game_id}: {e}")
            if not self.dry_run:
                try:
                    self.db.rollback()
                except:
                    pass
            self.stats['games_failed'] += 1
            return False
    
    def run(self, limit: Optional[int] = None, game_id: Optional[str] = None):
        """Run the population process"""
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
        print(f"  Games processed: {self.stats['games_processed']}")
        print(f"  Games failed: {self.stats['games_failed']}")
        print(f"  Arenas created: {self.stats['arenas_created']}")
        print(f"  Players created: {self.stats['players_created']}")
        print(f"  Play events created: {self.stats['play_events_created']}")
        print(f"  Team stats created: {self.stats['team_stats_created']}")
        print(f"  Player stats created: {self.stats['player_stats_created']}")
        print(f"  Lineup states created: {self.stats.get('lineup_states_created', 0)}")
        print(f"  Substitution events created: {self.stats.get('substitution_events_created', 0)}")


def backfill_analytics_data(dry_run: bool = False, limit: Optional[int] = None):
    """Backfill all analytics-derived data by clearing and repopulating"""
    print("🔄 Analytics Data Backfill" + (" (DRY RUN)" if dry_run else ""))
    if limit:
        print(f"   Limited to {limit:,} games")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Get count of existing analytics data
        lineup_states_count = db.execute(text("SELECT COUNT(*) FROM lineup_states")).scalar()
        substitution_events_count = db.execute(text("SELECT COUNT(*) FROM substitution_events")).scalar()
        
        print(f"Found existing analytics data:")
        print(f"  Lineup states: {lineup_states_count:,}")
        print(f"  Substitution events: {substitution_events_count:,}")
        print()
        
        if not dry_run:
            # Clear existing analytics tables
            print("🗑️  Clearing existing analytics data...")
            db.execute(text("DELETE FROM lineup_states"))
            db.execute(text("DELETE FROM substitution_events"))
            db.commit()
            print("  ✅ Analytics tables cleared")
        else:
            print("  [DRY RUN] Would clear analytics tables")
        
        # Get all games that have been processed in enhanced_games
        print("📊 Finding games to reprocess...")
        if limit:
            result = db.execute(text("""
                SELECT game_id FROM enhanced_games 
                ORDER BY game_date DESC
                LIMIT :limit
            """), {"limit": limit})
        else:
            result = db.execute(text("""
                SELECT game_id FROM enhanced_games 
                ORDER BY game_date DESC
            """))
        all_game_ids = [row[0] for row in result.fetchall()]
        
        print(f"Found {len(all_game_ids):,} games to reprocess")
        print()
        
        # Process games in batches to get raw JSON and repopulate analytics
        batch_size = 100
        total_processed = 0
        total_errors = 0
        
        for i in range(0, len(all_game_ids), batch_size):
            batch_game_ids = all_game_ids[i:i + batch_size]
            
            print(f"Processing batch {i // batch_size + 1} ({len(batch_game_ids)} games)...")
            
            # Get raw JSON for this batch
            placeholders = ','.join([f':game_id_{j}' for j in range(len(batch_game_ids))])
            params = {f'game_id_{j}': game_id for j, game_id in enumerate(batch_game_ids)}
            
            raw_data_query = text(f"""
                SELECT game_id, raw_json 
                FROM raw_game_data 
                WHERE game_id IN ({placeholders})
            """)
            
            raw_data_result = db.execute(raw_data_query, params)
            raw_data_map = {row[0]: json.loads(row[1]) if isinstance(row[1], str) else row[1] 
                           for row in raw_data_result.fetchall()}
            
            # Process each game in the batch
            for game_id in batch_game_ids:
                if game_id not in raw_data_map:
                    print(f"  ⚠️ No raw data found for {game_id}")
                    total_errors += 1
                    continue
                
                try:
                    raw_json = raw_data_map[game_id]
                    
                    if not dry_run:
                        # Extract and insert lineup tracking data (suppress warnings for cleaner output)
                        import sys
                        from io import StringIO
                        
                        # Capture warnings temporarily
                        old_stdout = sys.stdout
                        sys.stdout = StringIO()
                        
                        try:
                            tracker = LineupTracker(raw_json)
                            timeline = tracker.build_lineup_timeline()
                            substitutions = tracker.parse_substitution_events()
                        finally:
                            # Restore stdout
                            sys.stdout = old_stdout
                        
                        # Convert to database format
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
                        
                        # Insert data
                        populator = EnhancedSchemaPopulator(dry_run=False)
                        populator.db = db  # Use same connection
                        populator.insert_lineup_states(lineup_states)
                        populator.insert_substitution_events(substitution_events)
                        db.commit()
                    
                    total_processed += 1
                    if total_processed % 10 == 0:
                        print(f"    Processed {total_processed}/{len(all_game_ids)} games...")
                        
                except Exception as e:
                    print(f"  ❌ Error processing {game_id}: {str(e)[:100]}...")
                    total_errors += 1
                    if not dry_run:
                        try:
                            db.rollback()
                        except:
                            pass
                    continue
        
        print()
        print("=" * 60)
        print("BACKFILL SUMMARY:")
        print(f"  Games processed: {total_processed:,}")
        print(f"  Games with errors: {total_errors:,}")
        
        if not dry_run:
            # Get final counts
            final_lineup_states = db.execute(text("SELECT COUNT(*) FROM lineup_states")).scalar()
            final_substitution_events = db.execute(text("SELECT COUNT(*) FROM substitution_events")).scalar()
            
            print(f"  Final lineup states: {final_lineup_states:,}")
            print(f"  Final substitution events: {final_substitution_events:,}")
        
    finally:
        db.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Populate enhanced schema from raw game data')
    parser.add_argument('--limit', type=int, help='Limit number of games to process')
    parser.add_argument('--game-id', type=str, help='Process specific game ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--backfill', action='store_true', help='Backfill all analytics-derived data (clears and repopulates lineup_states and substitution_events)')
    
    args = parser.parse_args()
    
    if args.backfill:
        backfill_analytics_data(dry_run=args.dry_run, limit=args.limit)
    else:
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