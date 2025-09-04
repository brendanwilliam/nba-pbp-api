"""
Manages the scraping of raw game data for WNBA games and populating the database.

This manager coordinates URL generation, raw data scraping, and session management
to provide a comprehensive scraping solution for WNBA game data.
"""

import argparse
import logging
import sys
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..scrapers.game_url_generator import GameURLGenerator, GameURLInfo
from ..scrapers.raw_data_extractor import RawDataExtractor, ExtractionResult
from ..database.services import DatabaseService

logger = logging.getLogger(__name__)


class ScraperManager:
    """Coordinates WNBA game data scraping operations."""
    
    def __init__(self):
        self.url_generator = GameURLGenerator()
        self.data_extractor = RawDataExtractor()
        self.current_session_id = None
    
    def start_scraping_session(self, session_name: str) -> Optional[int]:
        """Start a new scraping session and return session ID."""
        with DatabaseService() as db:
            session = db.scraping_session.start_session(session_name)
            if session:
                self.current_session_id = session.id
                logger.info(f"Started scraping session '{session_name}' with ID {session.id}")
                return session.id
            return None
    
    def update_session_progress(self, games_scraped: int, errors_count: int = 0):
        """Update current session progress."""
        if not self.current_session_id:
            logger.warning("No active session to update")
            return
        
        with DatabaseService() as db:
            db.scraping_session.update_session(
                self.current_session_id, 
                games_scraped=games_scraped,
                errors_count=errors_count
            )
    
    def complete_session(self, status: str = 'completed'):
        """Complete the current scraping session."""
        if not self.current_session_id:
            logger.warning("No active session to complete")
            return
        
        with DatabaseService() as db:
            db.scraping_session.update_session(self.current_session_id, status=status)
            logger.info(f"Completed scraping session {self.current_session_id} with status: {status}")
    
    def generate_urls_for_season(self, season: int, game_type: str = 'regular') -> List[GameURLInfo]:
        """Generate game URLs for a specific season and game type."""
        game_urls = []
        
        if game_type == 'regular':
            game_ids = self.url_generator.generate_regular_season_ids(season)
        elif game_type == 'playoff':
            game_ids = self.url_generator.generate_playoff_ids(season)
        else:
            logger.error(f"Invalid game_type: {game_type}. Must be 'regular' or 'playoff'")
            return []
        
        for game_id in game_ids:
            game_url = self.url_generator.generate_game_url(game_id)
            game_urls.append(GameURLInfo(
                game_id=game_id,
                season=str(season),
                game_url=game_url,
                game_type=game_type
            ))
        
        logger.info(f"Generated {len(game_urls)} URLs for {season} {game_type} season")
        return game_urls
    
    def scrape_single_game(self, game_url_info: GameURLInfo, override_existing: bool = False) -> bool:
        """Scrape a single game and save to database."""
        try:
            # Check if game already exists (unless overriding)
            with DatabaseService() as db:
                if not override_existing and db.game_data.game_exists(int(game_url_info.game_id)):
                    logger.info(f"Game {game_url_info.game_id} already exists, skipping")
                    return True
                elif override_existing and db.game_data.game_exists(int(game_url_info.game_id)):
                    logger.info(f"Game {game_url_info.game_id} already exists, but override_existing=True - will re-scrape")
            
            # Extract game data
            result, game_data, metadata = self.data_extractor.extract_game_data(game_url_info.game_url)
            
            if result != ExtractionResult.SUCCESS or not game_data:
                logger.warning(f"Failed to extract data for game {game_url_info.game_id}: {result}")
                return False
            
            # Save to database (with override handling)
            with DatabaseService() as db:
                if override_existing and db.game_data.game_exists(int(game_url_info.game_id)):
                    # Delete existing data first
                    logger.info(f"Deleting existing data for game {game_url_info.game_id}")
                    db.game_data.delete_game_data(int(game_url_info.game_id))
                
                success = db.game_data.insert_game_data(
                    game_id=int(game_url_info.game_id),
                    season=int(game_url_info.season),
                    game_type=game_url_info.game_type,
                    game_url=game_url_info.game_url,
                    game_data=game_data
                )
                
                if success:
                    action = "re-scraped" if override_existing else "scraped"
                    logger.info(f"Successfully {action} game {game_url_info.game_id}")
                    return True
                else:
                    logger.error(f"Failed to save game {game_url_info.game_id} to database")
                    return False
        
        except Exception as e:
            logger.error(f"Error scraping game {game_url_info.game_id}: {e}")
            return False
    
    def _detect_data_changes(self, existing_data: Dict[str, Any], fresh_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect specific changes between existing and fresh game data.
        
        Returns:
            Dict with detailed change information
        """
        changes = {
            'total_changes': 0,
            'sections_changed': [],
            'details': {}
        }
        
        try:
            # Helper function to safely get nested values
            def safe_get(data, *keys, default=None):
                for key in keys:
                    if isinstance(data, dict) and key in data:
                        data = data[key]
                    else:
                        return default
                return data
            
            # Check game metadata changes
            game_changes = []
            
            # Basic game info
            existing_status = safe_get(existing_data, 'gameStatus')
            fresh_status = safe_get(fresh_data, 'gameStatus')
            if existing_status != fresh_status:
                game_changes.append(f"Game status: '{existing_status}' → '{fresh_status}'")
            
            existing_period = safe_get(existing_data, 'period')
            fresh_period = safe_get(fresh_data, 'period')
            if existing_period != fresh_period:
                game_changes.append(f"Period: {existing_period} → {fresh_period}")
            
            # Score changes
            existing_home_score = safe_get(existing_data, 'homeTeam', 'score')
            fresh_home_score = safe_get(fresh_data, 'homeTeam', 'score')
            existing_away_score = safe_get(existing_data, 'awayTeam', 'score')
            fresh_away_score = safe_get(fresh_data, 'awayTeam', 'score')
            
            if existing_home_score != fresh_home_score or existing_away_score != fresh_away_score:
                game_changes.append(f"Score: {existing_away_score}-{existing_home_score} → {fresh_away_score}-{fresh_home_score}")
            
            if game_changes:
                changes['sections_changed'].append('game_metadata')
                changes['details']['game_metadata'] = game_changes
                changes['total_changes'] += len(game_changes)
            
            # Check play-by-play changes
            existing_plays = safe_get(existing_data, 'game', 'actions', default=[])
            fresh_plays = safe_get(fresh_data, 'game', 'actions', default=[])
            
            play_changes = []
            if len(existing_plays) != len(fresh_plays):
                play_changes.append(f"Play count: {len(existing_plays)} → {len(fresh_plays)}")
                changes['total_changes'] += 1
            
            # Check for play modifications (sample first 5 differences)
            max_check = min(len(existing_plays), len(fresh_plays), 100)  # Limit to avoid performance issues
            play_diffs = 0
            for i in range(max_check):
                if i < len(existing_plays) and i < len(fresh_plays):
                    existing_play = existing_plays[i]
                    fresh_play = fresh_plays[i]
                    
                    # Check key play fields
                    existing_desc = safe_get(existing_play, 'description', '')
                    fresh_desc = safe_get(fresh_play, 'description', '')
                    if existing_desc != fresh_desc and play_diffs < 5:  # Show max 5 examples
                        play_changes.append(f"Play {i+1} description changed")
                        play_diffs += 1
                    
                    existing_clock = safe_get(existing_play, 'clock')
                    fresh_clock = safe_get(fresh_play, 'clock')
                    if existing_clock != fresh_clock and play_diffs < 5:
                        play_changes.append(f"Play {i+1} clock: {existing_clock} → {fresh_clock}")
                        play_diffs += 1
            
            if play_diffs > 5:
                play_changes.append(f"... and {play_diffs - 5} more play modifications")
            
            if play_changes:
                changes['sections_changed'].append('play_by_play')
                changes['details']['play_by_play'] = play_changes
                changes['total_changes'] += len(play_changes)
            
            # Check boxscore/stats changes
            boxscore_changes = []
            
            # Home team stats
            existing_home_stats = safe_get(existing_data, 'homeTeam', 'statistics', default={})
            fresh_home_stats = safe_get(fresh_data, 'homeTeam', 'statistics', default={})
            
            home_team_name = safe_get(fresh_data, 'homeTeam', 'teamName', 'Home')
            for stat_key in ['points', 'rebounds', 'assists', 'fieldGoalsMade', 'freeThrowsMade']:
                existing_val = safe_get(existing_home_stats, stat_key)
                fresh_val = safe_get(fresh_home_stats, stat_key)
                if existing_val != fresh_val:
                    boxscore_changes.append(f"{home_team_name} {stat_key}: {existing_val} → {fresh_val}")
            
            # Away team stats  
            existing_away_stats = safe_get(existing_data, 'awayTeam', 'statistics', default={})
            fresh_away_stats = safe_get(fresh_data, 'awayTeam', 'statistics', default={})
            
            away_team_name = safe_get(fresh_data, 'awayTeam', 'teamName', 'Away')
            for stat_key in ['points', 'rebounds', 'assists', 'fieldGoalsMade', 'freeThrowsMade']:
                existing_val = safe_get(existing_away_stats, stat_key)
                fresh_val = safe_get(fresh_away_stats, stat_key)
                if existing_val != fresh_val:
                    boxscore_changes.append(f"{away_team_name} {stat_key}: {existing_val} → {fresh_val}")
            
            # Player stats (check if player lists changed)
            existing_players = safe_get(existing_data, 'game', 'homeTeam', 'players', default=[])
            fresh_players = safe_get(fresh_data, 'game', 'homeTeam', 'players', default=[])
            
            if len(existing_players) != len(fresh_players):
                boxscore_changes.append(f"Home team player count: {len(existing_players)} → {len(fresh_players)}")
                changes['total_changes'] += 1
            
            existing_away_players = safe_get(existing_data, 'game', 'awayTeam', 'players', default=[])
            fresh_away_players = safe_get(fresh_data, 'game', 'awayTeam', 'players', default=[])
            
            if len(existing_away_players) != len(fresh_away_players):
                boxscore_changes.append(f"Away team player count: {len(existing_away_players)} → {len(fresh_away_players)}")
                changes['total_changes'] += 1
            
            if boxscore_changes:
                changes['sections_changed'].append('boxscore_stats')
                changes['details']['boxscore_stats'] = boxscore_changes
                changes['total_changes'] += len(boxscore_changes)
            
            # Check officials/referees
            existing_officials = safe_get(existing_data, 'officials', default=[])
            fresh_officials = safe_get(fresh_data, 'officials', default=[])
            
            if len(existing_officials) != len(fresh_officials):
                changes['sections_changed'].append('officials')
                changes['details']['officials'] = [f"Official count: {len(existing_officials)} → {len(fresh_officials)}"]
                changes['total_changes'] += 1
            
            # Fallback: if no specific changes detected but data is different
            if changes['total_changes'] == 0:
                # Do a high-level JSON comparison to catch any missed changes
                import json
                existing_json = json.dumps(existing_data, sort_keys=True)
                fresh_json = json.dumps(fresh_data, sort_keys=True)
                
                if existing_json != fresh_json:
                    changes['sections_changed'].append('other_data')
                    changes['details']['other_data'] = ['Unspecified data changes detected']
                    changes['total_changes'] = 1
            
        except Exception as e:
            logger.warning(f"Error detecting specific changes: {e}")
            changes['sections_changed'] = ['unknown']
            changes['details']['unknown'] = [f'Change detection failed: {str(e)}']
            changes['total_changes'] = 1
        
        return changes
    
    def compare_and_update_game(self, game_url_info: GameURLInfo) -> Dict[str, Any]:
        """
        Re-scrape a game and compare it to existing data. Update if different.
        
        Returns:
            Dict with comparison results and action taken
        """
        try:
            # Check if game exists
            with DatabaseService() as db:
                if not db.game_data.game_exists(int(game_url_info.game_id)):
                    logger.warning(f"Game {game_url_info.game_id} does not exist in database")
                    return {
                        'game_id': game_url_info.game_id,
                        'status': 'not_found',
                        'action': 'none',
                        'changes_detected': False
                    }
                
                # Get existing game data
                existing_game = db.game_data.get_game_data(int(game_url_info.game_id))
                if not existing_game:
                    logger.error(f"Could not retrieve existing data for game {game_url_info.game_id}")
                    return {
                        'game_id': game_url_info.game_id,
                        'status': 'error',
                        'action': 'none',
                        'changes_detected': False
                    }
                
                existing_data = existing_game.game_data
            
            # Extract fresh game data
            result, fresh_data, metadata = self.data_extractor.extract_game_data(game_url_info.game_url)
            
            if result != ExtractionResult.SUCCESS or not fresh_data:
                logger.warning(f"Failed to extract fresh data for game {game_url_info.game_id}: {result}")
                return {
                    'game_id': game_url_info.game_id,
                    'status': 'extraction_failed',
                    'action': 'none',
                    'changes_detected': False
                }
            
            # Detect specific changes
            changes = self._detect_data_changes(existing_data, fresh_data)
            
            if changes['total_changes'] == 0:
                logger.info(f"Game {game_url_info.game_id} data is identical - no update needed")
                return {
                    'game_id': game_url_info.game_id,
                    'status': 'identical',
                    'action': 'none',
                    'changes_detected': False,
                    'changes': changes
                }
            else:
                # Data is different - update the database
                logger.info(f"Game {game_url_info.game_id} has changed data - updating database")
                logger.info(f"Changes detected in {len(changes['sections_changed'])} sections: {', '.join(changes['sections_changed'])}")
                
                # Log specific changes if verbose logging
                if logger.isEnabledFor(logging.INFO):
                    for section, section_changes in changes['details'].items():
                        logger.info(f"  {section}: {len(section_changes)} changes")
                        for change in section_changes[:3]:  # Show first 3 changes per section
                            logger.info(f"    - {change}")
                        if len(section_changes) > 3:
                            logger.info(f"    - ... and {len(section_changes) - 3} more changes")
                
                with DatabaseService() as db:
                    # Delete existing and insert fresh data
                    db.game_data.delete_game_data(int(game_url_info.game_id))
                    
                    success = db.game_data.insert_game_data(
                        game_id=int(game_url_info.game_id),
                        season=int(game_url_info.season),
                        game_type=game_url_info.game_type,
                        game_url=game_url_info.game_url,
                        game_data=fresh_data
                    )
                    
                    if success:
                        logger.info(f"Successfully updated game {game_url_info.game_id} with fresh data")
                        return {
                            'game_id': game_url_info.game_id,
                            'status': 'updated',
                            'action': 'updated',
                            'changes_detected': True,
                            'changes': changes
                        }
                    else:
                        logger.error(f"Failed to update game {game_url_info.game_id}")
                        return {
                            'game_id': game_url_info.game_id,
                            'status': 'update_failed',
                            'action': 'none',
                            'changes_detected': True,
                            'changes': changes
                        }
        
        except Exception as e:
            logger.error(f"Error comparing/updating game {game_url_info.game_id}: {e}")
            return {
                'game_id': game_url_info.game_id,
                'status': 'error',
                'action': 'none',
                'changes_detected': False,
                'changes': {'total_changes': 0, 'sections_changed': [], 'details': {}},
                'error': str(e)
            }
    
    def verify_and_update_games(self, game_ids: List[str]) -> Dict[str, Any]:
        """
        Verify and update multiple games by comparing fresh scrapes to existing data.
        
        Args:
            game_ids: List of game IDs to verify and update
            
        Returns:
            Dict with verification statistics
        """
        session_name = f"verify_update_{len(game_ids)}games_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start verification session")
            return {
                'total': 0,
                'identical': 0,
                'updated': 0,
                'failed': 0,
                'not_found': 0,
                'results': []
            }
        
        # Statistics
        stats = {
            'total': len(game_ids),
            'identical': 0,
            'updated': 0,
            'failed': 0,
            'not_found': 0,
            'results': []
        }
        
        logger.info(f"Starting verification and update of {stats['total']} games")
        
        for i, game_id in enumerate(game_ids, 1):
            logger.info(f"Verifying game {i}/{stats['total']}: {game_id}")
            
            try:
                # Determine season and create game URL info
                season = self._determine_season_from_game_id(game_id)
                game_url = self.url_generator.generate_game_url(game_id)
                
                game_url_info = GameURLInfo(
                    game_id=game_id,
                    season=str(season),
                    game_url=game_url,
                    game_type='regular'  # Assume regular for now
                )
                
                # Compare and update if needed
                result = self.compare_and_update_game(game_url_info)
                stats['results'].append(result)
                
                # Update counters
                if result['status'] == 'identical':
                    stats['identical'] += 1
                elif result['status'] == 'updated':
                    stats['updated'] += 1
                elif result['status'] == 'not_found':
                    stats['not_found'] += 1
                else:
                    stats['failed'] += 1
                
                # Update session progress every 5 games
                if i % 5 == 0:
                    self.update_session_progress(stats['updated'], stats['failed'])
                
                # Small delay to be respectful
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error verifying game {game_id}: {e}")
                stats['failed'] += 1
                stats['results'].append({
                    'game_id': game_id,
                    'status': 'error',
                    'action': 'none',
                    'changes_detected': False,
                    'error': str(e)
                })
        
        # Final session update
        self.update_session_progress(stats['updated'], stats['failed'])
        
        # Complete session
        session_status = 'completed' if stats['failed'] == 0 else 'completed_with_errors'
        self.complete_session(session_status)
        
        logger.info(f"Verification completed. Identical: {stats['identical']}, "
                   f"Updated: {stats['updated']}, Failed: {stats['failed']}, "
                   f"Not Found: {stats['not_found']}")
        
        return stats
    
    def verify_and_update_season(self, season: int, game_type: str = 'regular', 
                                max_games: Optional[int] = None) -> Dict[str, Any]:
        """
        Verify and update all games in a season by comparing fresh scrapes to existing data.
        
        Args:
            season: WNBA season year
            game_type: 'regular' or 'playoff'
            max_games: Maximum number of games to process
            
        Returns:
            Dict with verification statistics
        """
        session_name = f"verify_season_{season}_{game_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start season verification session")
            return {
                'total': 0,
                'identical': 0,
                'updated': 0,
                'failed': 0,
                'not_found': 0,
                'results': []
            }
        
        # Get all game IDs for this season from the database
        with DatabaseService() as db:
            # Query games by season from raw_game_data
            from ..database.models import RawGameData
            
            session = db.get_session()
            query = session.query(RawGameData).filter(
                RawGameData.season == season
            )
            
            # Filter by game_type if we can determine it from the data
            # For now, we'll process all games in the season
            if max_games:
                query = query.limit(max_games)
            
            games = query.all()
            game_ids = [str(game.game_id) for game in games]
        
        if not game_ids:
            logger.warning(f"No games found for season {season}")
            return {
                'total': 0,
                'identical': 0,
                'updated': 0,
                'failed': 0,
                'not_found': 0,
                'results': []
            }
        
        logger.info(f"Starting verification and update of {len(game_ids)} games from {season} {game_type} season")
        
        # Use the existing verify_and_update_games method
        stats = self.verify_and_update_games(game_ids)
        
        # Update session name to reflect actual processing
        stats['season'] = season
        stats['game_type'] = game_type
        
        logger.info(f"Season verification completed for {season} {game_type}. "
                   f"Identical: {stats['identical']}, Updated: {stats['updated']}, "
                   f"Failed: {stats['failed']}")
        
        return stats
    
    def scrape_season(self, season: int, game_type: str = 'regular', max_games: Optional[int] = None) -> Dict[str, int]:
        """
        Scrape all games for a season.
        
        Args:
            season: WNBA season year
            game_type: 'regular' or 'playoff'
            max_games: Maximum number of games to scrape (for testing)
            
        Returns:
            Dict with scraping statistics
        """
        session_name = f"{season}_{game_type}_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start scraping session")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
        
        # Generate URLs
        game_urls = self.generate_urls_for_season(season, game_type)
        
        if max_games:
            game_urls = game_urls[:max_games]
            logger.info(f"Limited to first {max_games} games for testing")
        
        # Scraping statistics
        stats = {'total': len(game_urls), 'success': 0, 'failed': 0, 'skipped': 0}
        
        logger.info(f"Starting to scrape {stats['total']} games for {season} {game_type} season")
        
        for i, game_url_info in enumerate(game_urls, 1):
            logger.info(f"Scraping game {i}/{stats['total']}: {game_url_info.game_id}")
            
            # Check if already exists
            with DatabaseService() as db:
                if db.game_data.game_exists(int(game_url_info.game_id)):
                    stats['skipped'] += 1
                    logger.info(f"Game {game_url_info.game_id} already exists, skipping")
                    continue
            
            success = self.scrape_single_game(game_url_info, override_existing=False)
            
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            
            # Update session progress every 10 games
            if i % 10 == 0:
                self.update_session_progress(stats['success'], stats['failed'])
            
            # Small delay to be respectful to the server
            time.sleep(1)
        
        # Final session update
        self.update_session_progress(stats['success'], stats['failed'])
        
        # Complete session
        session_status = 'completed' if stats['failed'] == 0 else 'completed_with_errors'
        self.complete_session(session_status)
        
        logger.info(f"Scraping completed. Success: {stats['success']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
        return stats
    
    def scrape_specific_games(self, game_ids: List[str], override_existing: bool = False) -> Dict[str, int]:
        """
        Scrape specific games by ID.
        
        Args:
            game_ids: List of game IDs to scrape
            override_existing: If True, re-scrape games that already exist
            
        Returns:
            Dict with scraping statistics
        """
        session_name = f"specific_games_scraping_{len(game_ids)}games_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start scraping session")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
        
        # Determine seasons for each game ID
        game_url_infos = []
        for game_id in game_ids:
            try:
                # Extract season from game ID format (1SYYTTGGG where SYY is season)
                season = self._determine_season_from_game_id(game_id)
                game_url = self.url_generator.generate_game_url(game_id)
                
                game_url_info = GameURLInfo(
                    game_id=game_id,
                    season=str(season),
                    game_url=game_url,
                    game_type='regular'  # Assume regular for now
                )
                game_url_infos.append(game_url_info)
                
            except Exception as e:
                logger.error(f"Failed to create URL info for game {game_id}: {e}")
                continue
        
        # Scraping statistics
        stats = {'total': len(game_url_infos), 'success': 0, 'failed': 0, 'skipped': 0}
        
        logger.info(f"Starting to scrape {stats['total']} specific games (override_existing={override_existing})")
        
        for i, game_url_info in enumerate(game_url_infos, 1):
            logger.info(f"Scraping game {i}/{stats['total']}: {game_url_info.game_id}")
            
            # Check if already exists (unless overriding)
            if not override_existing:
                with DatabaseService() as db:
                    if db.game_data.game_exists(int(game_url_info.game_id)):
                        stats['skipped'] += 1
                        logger.info(f"Game {game_url_info.game_id} already exists, skipping")
                        continue
            
            success = self.scrape_single_game(game_url_info, override_existing=override_existing)
            
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            
            # Update session progress every 5 games
            if i % 5 == 0:
                self.update_session_progress(stats['success'], stats['failed'])
            
            # Small delay to be respectful to the server
            time.sleep(2)  # Slightly longer for specific scraping
        
        # Final session update
        self.update_session_progress(stats['success'], stats['failed'])
        
        # Complete session
        session_status = 'completed' if stats['failed'] == 0 else 'completed_with_errors'
        self.complete_session(session_status)
        
        logger.info(f"Specific game scraping completed. Success: {stats['success']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
        return stats
    
    def _determine_season_from_game_id(self, game_id: str) -> int:
        """Determine the season from game ID format."""
        # WNBA game IDs follow format: 10SYY00GGG where:
        # - 10 = League prefix
        # - S = Season type (2=regular, 4=playoff) 
        # - YY = Year (24=2024, 23=2023, etc.)
        # - 00 = Fixed padding
        # - GGG = Game number
        if len(game_id) >= 6:
            season_part = game_id[3:5]  # Extract YY part from position 3-4
            try:
                year_suffix = int(season_part)
                if year_suffix >= 97:  # 1997-1999
                    return 1900 + year_suffix
                else:  # 2000+
                    return 2000 + year_suffix
            except ValueError:
                pass
        
        # Fallback - assume recent season
        logger.warning(f"Could not determine season from game_id {game_id}, assuming 2024")
        return 2024
    
    def scrape_all_seasons(self, game_type: str = 'regular', max_games_total: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape all available seasons for a specific game type.
        
        Args:
            game_type: 'regular' or 'playoff'
            max_games_total: Maximum total games across ALL seasons (for testing)
            
        Returns:
            Dict with overall scraping statistics
        """
        session_name = f"all_seasons_{game_type}_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start bulk scraping session")
            return {'seasons_processed': 0, 'total_games': 0, 'total_success': 0, 'total_failed': 0, 'total_skipped': 0}
        
        # Get available seasons from the generator
        if game_type == 'regular':
            seasons = self.url_generator.regular_season_df['season'].unique().tolist()
        else:
            seasons = self.url_generator.playoff_df['season'].unique().tolist()
        
        seasons = sorted(seasons)
        logger.info(f"Starting bulk scraping for {len(seasons)} seasons ({game_type} games)")
        if max_games_total:
            logger.info(f"Limited to maximum {max_games_total} total games across all seasons")
        
        overall_stats = {
            'seasons_processed': 0,
            'total_games': 0,
            'total_success': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'season_results': []
        }
        
        games_scraped = 0
        
        for season in seasons:
            # Check if we've hit the total game limit
            if max_games_total and games_scraped >= max_games_total:
                logger.info(f"Reached maximum total games limit ({max_games_total}), stopping")
                break
                
            logger.info(f"Processing season {season} ({game_type})...")
            
            try:
                # Calculate remaining games for this season
                remaining_games = max_games_total - games_scraped if max_games_total else None
                
                # Generate URLs for this season
                game_urls = self.generate_urls_for_season(season, game_type)
                
                if remaining_games:
                    game_urls = game_urls[:remaining_games]
                
                if not game_urls:
                    logger.info(f"No games to scrape for season {season}")
                    overall_stats['season_results'].append({
                        'season': season,
                        'stats': {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
                    })
                    continue
                
                # Process this season's games
                season_stats = {'total': len(game_urls), 'success': 0, 'failed': 0, 'skipped': 0}
                
                for i, game_url_info in enumerate(game_urls, 1):
                    logger.info(f"Season {season} - Game {i}/{len(game_urls)}: {game_url_info.game_id}")
                    
                    # Check if already exists
                    with DatabaseService() as db:
                        if db.game_data.game_exists(int(game_url_info.game_id)):
                            season_stats['skipped'] += 1
                            logger.info(f"Game {game_url_info.game_id} already exists, skipping")
                            continue
                    
                    success = self.scrape_single_game(game_url_info, override_existing=False)
                    
                    if success:
                        season_stats['success'] += 1
                        games_scraped += 1
                    else:
                        season_stats['failed'] += 1
                    
                    # Update progress every 10 games
                    if (season_stats['success'] + season_stats['failed']) % 10 == 0:
                        self.update_session_progress(
                            overall_stats['total_success'] + season_stats['success'], 
                            overall_stats['total_failed'] + season_stats['failed']
                        )
                    
                    # Small delay to be respectful
                    time.sleep(1)
                    
                    # Check total limit again
                    if max_games_total and games_scraped >= max_games_total:
                        logger.info(f"Reached maximum total games limit ({max_games_total})")
                        break
                
                # Update overall stats
                overall_stats['seasons_processed'] += 1
                overall_stats['total_games'] += season_stats['total']
                overall_stats['total_success'] += season_stats['success']
                overall_stats['total_failed'] += season_stats['failed']
                overall_stats['total_skipped'] += season_stats['skipped']
                
                overall_stats['season_results'].append({
                    'season': season,
                    'stats': season_stats
                })
                
                logger.info(f"Completed season {season}: {season_stats['success']} success, "
                           f"{season_stats['failed']} failed, {season_stats['skipped']} skipped")
                
            except Exception as e:
                logger.error(f"Error processing season {season}: {e}")
                overall_stats['season_results'].append({
                    'season': season,
                    'error': str(e)
                })
        
        # Update session with final stats
        self.update_session_progress(overall_stats['total_success'], overall_stats['total_failed'])
        self.complete_session('completed' if overall_stats['total_failed'] == 0 else 'completed_with_errors')
        
        logger.info(f"Bulk scraping completed. Seasons: {overall_stats['seasons_processed']}, "
                   f"Total games: {overall_stats['total_games']}, "
                   f"Success: {overall_stats['total_success']}, "
                   f"Failed: {overall_stats['total_failed']}, "
                   f"Skipped: {overall_stats['total_skipped']}")
        
        return overall_stats
    
    def scrape_all_games(self, max_games_per_season: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape all regular and playoff games for all seasons.
        
        Args:
            max_games_per_season: Maximum games per season (for testing)
            
        Returns:
            Dict with overall scraping statistics
        """
        session_name = f"all_games_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = self.start_scraping_session(session_name)
        
        if not session_id:
            logger.error("Failed to start all-games scraping session")
            return {'regular_stats': {}, 'playoff_stats': {}, 'combined_stats': {}}
        
        logger.info("Starting comprehensive scraping of ALL WNBA games (regular + playoff)")
        
        # Scrape all regular season games
        logger.info("=== SCRAPING ALL REGULAR SEASON GAMES ===")
        regular_stats = self.scrape_all_seasons('regular', max_games_per_season)
        
        # Scrape all playoff games  
        logger.info("=== SCRAPING ALL PLAYOFF GAMES ===")
        playoff_stats = self.scrape_all_seasons('playoff', max_games_per_season)
        
        # Combined statistics
        combined_stats = {
            'total_seasons': regular_stats['seasons_processed'] + playoff_stats['seasons_processed'],
            'total_games': regular_stats['total_games'] + playoff_stats['total_games'],
            'total_success': regular_stats['total_success'] + playoff_stats['total_success'],
            'total_failed': regular_stats['total_failed'] + playoff_stats['total_failed'],
            'total_skipped': regular_stats['total_skipped'] + playoff_stats['total_skipped']
        }
        
        # Update session with combined stats
        self.update_session_progress(combined_stats['total_success'], combined_stats['total_failed'])
        self.complete_session('completed' if combined_stats['total_failed'] == 0 else 'completed_with_errors')
        
        logger.info(f"ALL-GAMES SCRAPING COMPLETED!")
        logger.info(f"Regular seasons: {regular_stats['seasons_processed']}, "
                   f"Playoff seasons: {playoff_stats['seasons_processed']}")
        logger.info(f"Total games processed: {combined_stats['total_games']}")
        logger.info(f"Success: {combined_stats['total_success']}, "
                   f"Failed: {combined_stats['total_failed']}, "
                   f"Skipped: {combined_stats['total_skipped']}")
        
        return {
            'regular_stats': regular_stats,
            'playoff_stats': playoff_stats,
            'combined_stats': combined_stats
        }
    
    def list_active_sessions(self):
        """List all currently active scraping sessions."""
        with DatabaseService() as db:
            sessions = db.scraping_session.get_active_sessions()
            if sessions:
                print("\nActive scraping sessions:")
                for session in sessions:
                    print(f"  ID: {session.id}, Name: {session.session_name}, Started: {session.start_time}")
            else:
                print("No active scraping sessions found.")


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('scraper_manager.log')
        ]
    )


def main():
    """Main CLI interface for the scraper manager."""
    parser = argparse.ArgumentParser(description='WNBA Game Data Scraper Manager')
    
    parser.add_argument('command', choices=['scrape-season', 'scrape-all-regular', 'scrape-all-playoff', 'scrape-all-games', 'scrape-games', 'test-single', 'verify-games', 'verify-season', 'list-sessions'],
                       help='Command to execute')
    
    parser.add_argument('--season', type=int, required=False,
                       help='WNBA season year (e.g., 2024)')
    
    parser.add_argument('--game-type', choices=['regular', 'playoff'], default='regular',
                       help='Type of games to scrape (default: regular)')
    
    parser.add_argument('--max-games', type=int, default=None,
                       help='Maximum number of games to scrape (for testing)')
    
    parser.add_argument('--game-id', type=str, default=None,
                       help='Single game ID to scrape (for test-single command)')
    
    parser.add_argument('--game-ids', type=str, nargs='+', default=None,
                       help='Multiple game IDs to scrape (for scrape-games command)')
    
    parser.add_argument('--override', action='store_true',
                       help='Override existing games - re-scrape games that already exist')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Initialize scraper manager
    manager = ScraperManager()
    
    try:
        if args.command == 'scrape-season':
            if not args.season:
                logger.error("--season is required for scrape-season command")
                sys.exit(1)
            
            stats = manager.scrape_season(args.season, args.game_type, args.max_games)
            
            print(f"\nScraping Results for {args.season} {args.game_type} season:")
            print(f"  Total games: {stats['total']}")
            print(f"  Successfully scraped: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Skipped (already exist): {stats['skipped']}")
            
        elif args.command == 'test-single':
            if not args.game_id or not args.season:
                logger.error("--game-id and --season are required for test-single command")
                sys.exit(1)
            
            # Create test game URL info
            game_url = manager.url_generator.generate_game_url(args.game_id)
            game_url_info = GameURLInfo(
                game_id=args.game_id,
                season=str(args.season),
                game_url=game_url,
                game_type=args.game_type
            )
            
            session_name = f"test_single_{args.game_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            manager.start_scraping_session(session_name)
            
            success = manager.scrape_single_game(game_url_info, override_existing=args.override)
            
            if success:
                print(f"Successfully scraped game {args.game_id}")
                manager.complete_session('completed')
            else:
                print(f"Failed to scrape game {args.game_id}")
                manager.complete_session('failed')
                
        elif args.command == 'scrape-games':
            if not args.game_ids:
                logger.error("--game-ids is required for scrape-games command")
                sys.exit(1)
            
            stats = manager.scrape_specific_games(args.game_ids, override_existing=args.override)
            
            print(f"\nSpecific Games Scraping Results:")
            print(f"  Total games: {stats['total']}")
            print(f"  Successfully scraped: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Skipped (already exist): {stats['skipped']}")
            
            if args.override:
                print(f"  Override mode: {'ON' if args.override else 'OFF'}")
                
        elif args.command == 'scrape-all-regular':
            stats = manager.scrape_all_seasons('regular', args.max_games)
            
            print(f"\nAll Regular Season Scraping Results:")
            print(f"  Seasons processed: {stats['seasons_processed']}")
            print(f"  Total games: {stats['total_games']}")
            print(f"  Successfully scraped: {stats['total_success']}")
            print(f"  Failed: {stats['total_failed']}")
            print(f"  Skipped (already exist): {stats['total_skipped']}")
            
            print(f"\nSeason-by-season breakdown:")
            for result in stats['season_results']:
                if 'error' in result:
                    print(f"  {result['season']}: ERROR - {result['error']}")
                else:
                    s = result['stats']
                    print(f"  {result['season']}: {s['success']} success, {s['failed']} failed, {s['skipped']} skipped")
        
        elif args.command == 'scrape-all-playoff':
            stats = manager.scrape_all_seasons('playoff', args.max_games)
            
            print(f"\nAll Playoff Scraping Results:")
            print(f"  Seasons processed: {stats['seasons_processed']}")
            print(f"  Total games: {stats['total_games']}")
            print(f"  Successfully scraped: {stats['total_success']}")
            print(f"  Failed: {stats['total_failed']}")
            print(f"  Skipped (already exist): {stats['total_skipped']}")
            
            print(f"\nSeason-by-season breakdown:")
            for result in stats['season_results']:
                if 'error' in result:
                    print(f"  {result['season']}: ERROR - {result['error']}")
                else:
                    s = result['stats']
                    print(f"  {result['season']}: {s['success']} success, {s['failed']} failed, {s['skipped']} skipped")
        
        elif args.command == 'scrape-all-games':
            results = manager.scrape_all_games(args.max_games)
            
            print(f"\nALL GAMES SCRAPING RESULTS:")
            print(f"="*50)
            
            combined = results['combined_stats']
            print(f"COMBINED TOTALS:")
            print(f"  Total games processed: {combined['total_games']}")
            print(f"  Successfully scraped: {combined['total_success']}")
            print(f"  Failed: {combined['total_failed']}")
            print(f"  Skipped (already exist): {combined['total_skipped']}")
            
            regular = results['regular_stats']
            playoff = results['playoff_stats']
            
            print(f"\nREGULAR SEASON SUMMARY:")
            print(f"  Seasons: {regular['seasons_processed']}")
            print(f"  Games: {regular['total_games']} (Success: {regular['total_success']}, Failed: {regular['total_failed']}, Skipped: {regular['total_skipped']})")
            
            print(f"\nPLAYOFF SUMMARY:")
            print(f"  Seasons: {playoff['seasons_processed']}")
            print(f"  Games: {playoff['total_games']} (Success: {playoff['total_success']}, Failed: {playoff['total_failed']}, Skipped: {playoff['total_skipped']})")
            
        elif args.command == 'verify-games':
            if not args.game_ids:
                logger.error("--game-ids is required for verify-games command")
                sys.exit(1)
            
            stats = manager.verify_and_update_games(args.game_ids)
            
            print(f"\nGame Verification Results:")
            print(f"  Total games: {stats['total']}")
            print(f"  Identical (no update needed): {stats['identical']}")
            print(f"  Updated: {stats['updated']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Not found: {stats['not_found']}")
            
            if stats['updated'] > 0:
                print(f"\nGames that were updated:")
                for result in stats['results']:
                    if result['status'] == 'updated':
                        changes = result.get('changes', {})
                        sections = ', '.join(changes.get('sections_changed', []))
                        total_changes = changes.get('total_changes', 0)
                        print(f"  - Game {result['game_id']}: {total_changes} changes in [{sections}]")
                        
                        # Show detailed changes for each section
                        for section, section_changes in changes.get('details', {}).items():
                            if section_changes:
                                print(f"    {section}:")
                                for change in section_changes[:2]:  # Show first 2 changes per section
                                    print(f"      • {change}")
                                if len(section_changes) > 2:
                                    print(f"      • ... and {len(section_changes) - 2} more changes")
            
            if stats['failed'] > 0:
                print(f"\nFailed games:")
                for result in stats['results']:
                    if result['status'] in ['error', 'extraction_failed', 'update_failed']:
                        error_msg = result.get('error', result['status'])
                        print(f"  - Game {result['game_id']}: {error_msg}")
        
        elif args.command == 'verify-season':
            if not args.season:
                logger.error("--season is required for verify-season command")
                sys.exit(1)
            
            stats = manager.verify_and_update_season(args.season, args.game_type, args.max_games)
            
            print(f"\nSeason Verification Results ({args.season} {args.game_type}):")
            print(f"  Total games: {stats['total']}")
            print(f"  Identical (no update needed): {stats['identical']}")
            print(f"  Updated: {stats['updated']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Not found: {stats['not_found']}")
            
            if stats['updated'] > 0:
                print(f"\nGames that were updated:")
                for result in stats['results']:
                    if result['status'] == 'updated':
                        changes = result.get('changes', {})
                        sections = ', '.join(changes.get('sections_changed', []))
                        total_changes = changes.get('total_changes', 0)
                        print(f"  - Game {result['game_id']}: {total_changes} changes in [{sections}]")
                        
                        # Show detailed changes for each section
                        for section, section_changes in changes.get('details', {}).items():
                            if section_changes:
                                print(f"    {section}:")
                                for change in section_changes[:2]:  # Show first 2 changes per section
                                    print(f"      • {change}")
                                if len(section_changes) > 2:
                                    print(f"      • ... and {len(section_changes) - 2} more changes")
            
            if stats['failed'] > 0:
                print(f"\nFailed games:")
                for result in stats['results']:
                    if result['status'] in ['error', 'extraction_failed', 'update_failed']:
                        error_msg = result.get('error', result['status'])
                        print(f"  - Game {result['game_id']}: {error_msg}")
        
        elif args.command == 'list-sessions':
            manager.list_active_sessions()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        if manager.current_session_id:
            manager.complete_session('failed')
        sys.exit(1)


if __name__ == "__main__":
    main()