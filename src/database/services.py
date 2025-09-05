"""
Database services for WNBA data operations.

This module provides service classes for database operations, keeping
business logic separate from models and providing clean interfaces
for the scraping and analytics components.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv
import psycopg2

from .models import (Base, RawGameData, ScrapingSession, DatabaseVersion, 
                     Person, Team, Game, Boxscore, Play, Arena, PersonGame, TeamGame)

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def get_engine(self):
        """Get the database engine."""
        return self.engine


class GameDataService:
    """Service for managing raw game data operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def insert_game_data(self, game_id: int, season: int, game_type: str, 
                        game_url: str, game_data: Dict[str, Any]) -> Optional[RawGameData]:
        """
        Insert new game data into the database.
        
        Args:
            game_id: Unique game identifier
            season: WNBA season year
            game_type: Type of game ('regular', 'playoff', etc.)
            game_url: URL where game data was scraped from
            game_data: JSON data from the game
            
        Returns:
            RawGameData object if successful, None if failed
        """
        try:
            # Check if game already exists
            existing = self.session.query(RawGameData).filter_by(game_id=game_id).first()
            if existing:
                logger.warning(f"Game {game_id} already exists, use update_game_data instead")
                return existing
            
            # Create new game data record
            game_record = RawGameData(
                game_id=game_id,
                season=season,
                game_type=game_type,
                game_url=game_url,
                game_data=game_data
            )
            
            self.session.add(game_record)
            self.session.commit()
            
            logger.info(f"Successfully inserted game data for game_id: {game_id}")
            return game_record
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error inserting game data for game_id {game_id}: {e}")
            return None
    
    def update_game_data(self, game_id: int, game_data: Dict[str, Any], 
                        game_url: Optional[str] = None) -> Optional[RawGameData]:
        """
        Update existing game data.
        
        Args:
            game_id: Game identifier to update
            game_data: New JSON data
            game_url: Optional new URL
            
        Returns:
            Updated RawGameData object if successful, None if failed
        """
        try:
            game_record = self.session.query(RawGameData).filter_by(game_id=game_id).first()
            if not game_record:
                logger.warning(f"Game {game_id} not found for update")
                return None
            
            # Store old values for logging
            old_url = game_record.game_url if game_url else None
            
            # Update the data
            game_record.game_data = game_data
            if game_url:
                game_record.game_url = game_url
            
            self.session.commit()
            
            logger.info(f"Successfully updated game data for game_id: {game_id}")
            if old_url and game_url and old_url != game_url:
                logger.info(f"Updated URL from {old_url} to {game_url}")
            return game_record
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating game data for game_id {game_id}: {e}")
            return None
    
    def upsert_game_data(self, game_id: int, season: int, game_type: str,
                        game_url: str, game_data: Dict[str, Any]) -> Optional[RawGameData]:
        """
        Insert or update game data (upsert operation).
        
        Args:
            game_id: Unique game identifier
            season: WNBA season year
            game_type: Type of game ('regular', 'playoff', etc.)
            game_url: URL where game data was scraped from
            game_data: JSON data from the game
            
        Returns:
            RawGameData object if successful, None if failed
        """
        try:
            existing = self.session.query(RawGameData).filter_by(game_id=game_id).first()
            
            if existing:
                # Update existing record
                logger.info(f"Game {game_id} exists, updating...")
                existing.game_data = game_data
                existing.game_url = game_url
                existing.season = season
                existing.game_type = game_type
                
                self.session.commit()
                logger.info(f"Successfully updated existing game data for game_id: {game_id}")
                return existing
            else:
                # Insert new record
                logger.info(f"Game {game_id} not found, inserting...")
                return self.insert_game_data(game_id, season, game_type, game_url, game_data)
                
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error upserting game data for game_id {game_id}: {e}")
            return None
    
    def update_multiple_games(self, updates: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Update multiple games in a batch operation.
        
        Args:
            updates: List of dicts with keys: game_id, game_data, game_url (optional)
            
        Returns:
            Dict with update statistics
        """
        stats = {'total': len(updates), 'updated': 0, 'not_found': 0, 'failed': 0}
        
        try:
            for update_data in updates:
                game_id = update_data['game_id']
                game_data = update_data['game_data']
                game_url = update_data.get('game_url')
                
                try:
                    result = self.update_game_data(game_id, game_data, game_url)
                    if result:
                        stats['updated'] += 1
                    else:
                        stats['not_found'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to update game {game_id}: {e}")
                    stats['failed'] += 1
            
            logger.info(f"Batch update completed. Updated: {stats['updated']}, "
                       f"Not found: {stats['not_found']}, Failed: {stats['failed']}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in batch update operation: {e}")
            stats['failed'] = stats['total']
            return stats
    
    def refresh_game_from_url(self, game_id: int, force_refresh: bool = False) -> Optional[RawGameData]:
        """
        Re-scrape and update a game from its stored URL.
        
        Args:
            game_id: Game identifier to refresh
            force_refresh: If True, refresh even if recently updated
            
        Returns:
            Updated RawGameData object if successful, None if failed
        """
        try:
            from ..scrapers.raw_data_extractor import RawDataExtractor, ExtractionResult
            
            game_record = self.session.query(RawGameData).filter_by(game_id=game_id).first()
            if not game_record:
                logger.warning(f"Game {game_id} not found for refresh")
                return None
            
            # Check if recently updated (unless forced)
            if not force_refresh:
                from datetime import datetime, timedelta
                if game_record.updated_at and game_record.updated_at > datetime.now(timezone.utc) - timedelta(hours=1):
                    logger.info(f"Game {game_id} was recently updated, skipping refresh (use force_refresh=True)")
                    return game_record
            
            # Re-scrape the data
            extractor = RawDataExtractor()
            result, new_game_data, metadata = extractor.extract_game_data(game_record.game_url)
            
            if result != ExtractionResult.SUCCESS or not new_game_data:
                logger.warning(f"Failed to refresh game {game_id} from URL: {result}")
                return None
            
            # Update with fresh data
            game_record.game_data = new_game_data
            self.session.commit()
            
            logger.info(f"Successfully refreshed game data for game_id: {game_id}")
            return game_record
            
        except ImportError:
            logger.error("RawDataExtractor not available for refresh operation")
            return None
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error refreshing game data for game_id {game_id}: {e}")
            return None
    
    def get_game_data(self, game_id: int) -> Optional[RawGameData]:
        """Get game data by game_id."""
        try:
            return self.session.query(RawGameData).filter_by(game_id=game_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving game data for game_id {game_id}: {e}")
            return None
    
    def get_games_by_season(self, season: int, game_type: Optional[str] = None) -> List[RawGameData]:
        """
        Get all games for a specific season.
        
        Args:
            season: WNBA season year
            game_type: Optional filter by game type
            
        Returns:
            List of RawGameData objects
        """
        try:
            query = self.session.query(RawGameData).filter_by(season=season)
            if game_type:
                query = query.filter_by(game_type=game_type)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving games for season {season}: {e}")
            return []
    
    def game_exists(self, game_id: int) -> bool:
        """Check if a game already exists in the database."""
        try:
            return self.session.query(RawGameData).filter_by(game_id=game_id).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking if game {game_id} exists: {e}")
            return False
    
    def delete_game_data(self, game_id: int) -> bool:
        """
        Delete a specific game by game_id.
        
        Args:
            game_id: Game identifier to delete
            
        Returns:
            True if deleted successfully, False if not found or failed
        """
        try:
            game_record = self.session.query(RawGameData).filter_by(game_id=game_id).first()
            if not game_record:
                logger.warning(f"Game {game_id} not found for deletion")
                return False
            
            self.session.delete(game_record)
            self.session.commit()
            
            logger.info(f"Successfully deleted game data for game_id: {game_id}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error deleting game data for game_id {game_id}: {e}")
            return False
    
    def delete_games_by_season(self, season: int, game_type: Optional[str] = None, 
                              dry_run: bool = True) -> Dict[str, int]:
        """
        Delete all games for a specific season.
        
        Args:
            season: WNBA season year
            game_type: Optional filter by game type ('regular', 'playoff')
            dry_run: If True, only count games that would be deleted
            
        Returns:
            Dict with deletion statistics
        """
        try:
            query = self.session.query(RawGameData).filter_by(season=season)
            if game_type:
                query = query.filter_by(game_type=game_type)
            
            games_to_delete = query.all()
            count = len(games_to_delete)
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {count} games for season {season}" + 
                           (f" ({game_type})" if game_type else ""))
                return {'would_delete': count, 'deleted': 0}
            
            if count == 0:
                logger.info(f"No games found for season {season}" + 
                           (f" ({game_type})" if game_type else ""))
                return {'would_delete': 0, 'deleted': 0}
            
            # Delete all matching games
            deleted_count = query.delete()
            self.session.commit()
            
            logger.info(f"Successfully deleted {deleted_count} games for season {season}" + 
                       (f" ({game_type})" if game_type else ""))
            return {'would_delete': count, 'deleted': deleted_count}
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error deleting games for season {season}: {e}")
            return {'would_delete': 0, 'deleted': 0}
    
    def delete_games_by_url_pattern(self, url_pattern: str, dry_run: bool = True) -> Dict[str, int]:
        """
        Delete games matching a URL pattern.
        
        Args:
            url_pattern: SQL LIKE pattern to match against game_url
            dry_run: If True, only count games that would be deleted
            
        Returns:
            Dict with deletion statistics
        """
        try:
            query = self.session.query(RawGameData).filter(RawGameData.game_url.like(url_pattern))
            games_to_delete = query.all()
            count = len(games_to_delete)
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {count} games matching pattern '{url_pattern}'")
                game_ids = [game.game_id for game in games_to_delete[:10]]  # Show first 10
                logger.info(f"Sample game_ids: {game_ids}{'...' if count > 10 else ''}")
                return {'would_delete': count, 'deleted': 0}
            
            if count == 0:
                logger.info(f"No games found matching pattern '{url_pattern}'")
                return {'would_delete': 0, 'deleted': 0}
            
            # Delete all matching games
            deleted_count = query.delete(synchronize_session=False)
            self.session.commit()
            
            logger.info(f"Successfully deleted {deleted_count} games matching pattern '{url_pattern}'")
            return {'would_delete': count, 'deleted': deleted_count}
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error deleting games by URL pattern '{url_pattern}': {e}")
            return {'would_delete': 0, 'deleted': 0}


class ScrapingSessionService:
    """Service for managing scraping sessions."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def start_session(self, session_name: str) -> Optional[ScrapingSession]:
        """Start a new scraping session."""
        try:
            scraping_session = ScrapingSession(
                session_name=session_name,
                status='running'
            )
            
            self.session.add(scraping_session)
            self.session.commit()
            
            logger.info(f"Started scraping session: {session_name}")
            return scraping_session
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error starting scraping session {session_name}: {e}")
            return None
    
    def update_session(self, session_id: int, games_scraped: Optional[int] = None,
                      errors_count: Optional[int] = None, status: Optional[str] = None) -> Optional[ScrapingSession]:
        """Update scraping session progress."""
        try:
            scraping_session = self.session.query(ScrapingSession).filter_by(id=session_id).first()
            if not scraping_session:
                logger.warning(f"Scraping session {session_id} not found")
                return None
            
            if games_scraped is not None:
                scraping_session.games_scraped = games_scraped
            if errors_count is not None:
                scraping_session.errors_count = errors_count
            if status is not None:
                scraping_session.status = status
                if status in ['completed', 'failed']:
                    scraping_session.end_time = datetime.now(timezone.utc)
            
            self.session.commit()
            return scraping_session
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating scraping session {session_id}: {e}")
            return None
    
    def get_active_sessions(self) -> List[ScrapingSession]:
        """Get all currently running scraping sessions."""
        try:
            return self.session.query(ScrapingSession).filter_by(status='running').all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving active sessions: {e}")
            return []


class PersonService:
    """Service for managing person/player operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_player_by_id(self, person_id: int) -> Optional[Person]:
        """Get a player by their person_id."""
        try:
            return self.session.query(Person).filter_by(person_id=person_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving player {person_id}: {e}")
            return None
    
    def get_player_by_name(self, name: str) -> Optional[Person]:
        """Get a player by their name (case-insensitive)."""
        try:
            return self.session.query(Person).filter(
                Person.person_name.ilike(f"%{name}%")
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving player by name '{name}': {e}")
            return None
    
    def get_all_active_players(self, cutoff_date: Optional[datetime] = None, 
                              role: str = "player") -> List[Person]:
        """
        Get all active players based on last_used date.
        
        Args:
            cutoff_date: Players must have last_used after this date. 
                        Defaults to 1 year ago from now.
            role: Player role filter (default: 'player')
            
        Returns:
            List of active Person objects
        """
        try:
            if cutoff_date is None:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
            
            return self.session.query(Person).filter(
                Person.person_role == role,
                Person.last_used > cutoff_date
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving active players: {e}")
            return []
    
    def get_player_stats_by_season(self, person_id: int, season: int, 
                                  game_type: str = "regular") -> List[Boxscore]:
        """Get player stats for a specific season."""
        try:
            return self.session.query(Boxscore).join(Game).filter(
                Boxscore.person_id == person_id,
                Game.season == season,
                Game.game_type == game_type,
                Boxscore.box_type == "player"
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving stats for player {person_id}, season {season}: {e}")
            return []
    
    def get_player_season_totals(self, person_id: int, season: int, 
                               game_type: str = "regular") -> Optional[Dict[str, Any]]:
        """Get aggregated season totals for a player."""
        try:
            from sqlalchemy import func
            result = self.session.query(
                func.count(Boxscore.boxscore_id).label('games_played'),
                func.sum(Boxscore.pts).label('total_pts'),
                func.sum(Boxscore.reb).label('total_reb'),
                func.sum(Boxscore.ast).label('total_ast'),
                func.sum(Boxscore.stl).label('total_stl'),
                func.sum(Boxscore.blk).label('total_blk'),
                func.sum(Boxscore.fgm).label('total_fgm'),
                func.sum(Boxscore.fga).label('total_fga'),
                func.sum(Boxscore.tpm).label('total_3pm'),
                func.sum(Boxscore.tpa).label('total_3pa'),
                func.sum(Boxscore.ftm).label('total_ftm'),
                func.sum(Boxscore.fta).label('total_fta'),
                func.sum(Boxscore.to).label('total_to'),
                func.sum(Boxscore.pf).label('total_pf')
            ).join(Game).filter(
                Boxscore.person_id == person_id,
                Game.season == season,
                Game.game_type == game_type,
                Boxscore.box_type == "player"
            ).first()
            
            if result and result.games_played:
                return {
                    'person_id': person_id,
                    'season': season,
                    'game_type': game_type,
                    'games_played': result.games_played,
                    'pts': result.total_pts or 0,
                    'reb': result.total_reb or 0,
                    'ast': result.total_ast or 0,
                    'stl': result.total_stl or 0,
                    'blk': result.total_blk or 0,
                    'fgm': result.total_fgm or 0,
                    'fga': result.total_fga or 0,
                    'fg_pct': round((result.total_fgm / result.total_fga * 100) if result.total_fga else 0, 1),
                    'tpm': result.total_3pm or 0,
                    'tpa': result.total_3pa or 0,
                    'tp_pct': round((result.total_3pm / result.total_3pa * 100) if result.total_3pa else 0, 1),
                    'ftm': result.total_ftm or 0,
                    'fta': result.total_fta or 0,
                    'ft_pct': round((result.total_ftm / result.total_fta * 100) if result.total_fta else 0, 1),
                    'to': result.total_to or 0,
                    'pf': result.total_pf or 0,
                    'ppg': round((result.total_pts / result.games_played) if result.games_played else 0, 1),
                    'rpg': round((result.total_reb / result.games_played) if result.games_played else 0, 1),
                    'apg': round((result.total_ast / result.games_played) if result.games_played else 0, 1)
                }
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error calculating season totals for player {person_id}: {e}")
            return None


class TeamService:
    """Service for managing team operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Get a team by their team_id."""
        try:
            return self.session.query(Team).filter_by(team_id=team_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving team {team_id}: {e}")
            return None
    
    def get_team_by_tricode(self, tricode: str) -> Optional[Team]:
        """Get a team by their tricode (e.g., 'LAS', 'NY')."""
        try:
            return self.session.query(Team).filter_by(team_tricode=tricode).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving team by tricode '{tricode}': {e}")
            return None
    
    def get_all_teams(self) -> List[Team]:
        """Get all teams."""
        try:
            return self.session.query(Team).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving all teams: {e}")
            return []
    
    def get_all_active_teams(self, cutoff_date: Optional[datetime] = None) -> List[Team]:
        """
        Get all active teams based on last_used date.
        
        Args:
            cutoff_date: Teams must have last_used after this date. 
                        Defaults to 1 year ago from now.
            
        Returns:
            List of active Team objects
        """
        try:
            if cutoff_date is None:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
            
            return self.session.query(Team).filter(
                Team.last_used > cutoff_date
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving active teams: {e}")
            return []
    
    def get_team_games_by_season(self, team_id: int, season: int, 
                               game_type: str = "regular") -> List[Game]:
        """Get all games for a team in a specific season."""
        try:
            return self.session.query(Game).join(TeamGame).filter(
                TeamGame.team_id == team_id,
                Game.season == season,
                Game.game_type == game_type
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving games for team {team_id}, season {season}: {e}")
            return []
    
    def get_team_stats_by_season(self, team_id: int, season: int, 
                               game_type: str = "regular") -> Optional[Dict[str, Any]]:
        """Get aggregated team stats for a season."""
        try:
            from sqlalchemy import func
            result = self.session.query(
                func.count(Game.game_id).label('games_played'),
                func.sum(Boxscore.pts).label('total_pts'),
                func.sum(Boxscore.reb).label('total_reb'),
                func.sum(Boxscore.ast).label('total_ast'),
                func.sum(Boxscore.stl).label('total_stl'),
                func.sum(Boxscore.blk).label('total_blk'),
                func.sum(Boxscore.fgm).label('total_fgm'),
                func.sum(Boxscore.fga).label('total_fga'),
                func.sum(Boxscore.tpm).label('total_3pm'),
                func.sum(Boxscore.tpa).label('total_3pa'),
                func.sum(Boxscore.ftm).label('total_ftm'),
                func.sum(Boxscore.fta).label('total_fta'),
                func.sum(Boxscore.to).label('total_to')
            ).join(Game).filter(
                Boxscore.team_id == team_id,
                Game.season == season,
                Game.game_type == game_type,
                Boxscore.box_type == "starters"  # Team totals usually in starters
            ).first()
            
            if result and result.games_played:
                return {
                    'team_id': team_id,
                    'season': season,
                    'game_type': game_type,
                    'games_played': result.games_played,
                    'pts': result.total_pts or 0,
                    'reb': result.total_reb or 0,
                    'ast': result.total_ast or 0,
                    'stl': result.total_stl or 0,
                    'blk': result.total_blk or 0,
                    'fgm': result.total_fgm or 0,
                    'fga': result.total_fga or 0,
                    'fg_pct': round((result.total_fgm / result.total_fga * 100) if result.total_fga else 0, 1),
                    'tpm': result.total_3pm or 0,
                    'tpa': result.total_3pa or 0,
                    'tp_pct': round((result.total_3pm / result.total_3pa * 100) if result.total_3pa else 0, 1),
                    'ftm': result.total_ftm or 0,
                    'fta': result.total_fta or 0,
                    'ft_pct': round((result.total_ftm / result.total_fta * 100) if result.total_fta else 0, 1),
                    'to': result.total_to or 0,
                    'ppg': round((result.total_pts / result.games_played) if result.games_played else 0, 1),
                    'rpg': round((result.total_reb / result.games_played) if result.games_played else 0, 1),
                    'apg': round((result.total_ast / result.games_played) if result.games_played else 0, 1)
                }
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error calculating team stats for team {team_id}: {e}")
            return None


class DatabaseService:
    """Main service class that coordinates all database operations."""
    
    def __init__(self):
        self.db_connection = DatabaseConnection()
        self._session = None
    
    def __enter__(self):
        """Context manager entry."""
        self._session = self.db_connection.get_session()
        self.game_data = GameDataService(self._session)
        self.scraping_session = ScrapingSessionService(self._session)
        self.person = PersonService(self._session)
        self.team = TeamService(self._session)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._session:
            if exc_type is not None:
                self._session.rollback()
            self._session.close()
    
    def get_session(self) -> Session:
        """Get the current session (for advanced usage)."""
        return self._session


# Utility functions for common operations
def with_database(func):
    """Decorator to automatically handle database sessions."""
    def wrapper(*args, **kwargs):
        with DatabaseService() as db:
            return func(db, *args, **kwargs)
    return wrapper


# Example usage functions
def insert_scraped_game(game_id: int, season: int, game_type: str, 
                       game_url: str, game_data: Dict[str, Any]) -> bool:
    """Convenience function to insert a single game's data."""
    with DatabaseService() as db:
        result = db.game_data.insert_game_data(game_id, season, game_type, game_url, game_data)
        return result is not None


def get_games_for_analysis(season: int, game_type: str = 'regular') -> List[RawGameData]:
    """Convenience function to get games for analysis."""
    with DatabaseService() as db:
        return db.game_data.get_games_by_season(season, game_type)


# Deletion convenience functions
def delete_single_game(game_id: int) -> bool:
    """Convenience function to delete a single game."""
    with DatabaseService() as db:
        return db.game_data.delete_game_data(game_id)


def delete_season_games(season: int, game_type: Optional[str] = None, 
                       dry_run: bool = True) -> Dict[str, int]:
    """Convenience function to delete games by season."""
    with DatabaseService() as db:
        return db.game_data.delete_games_by_season(season, game_type, dry_run)


def delete_games_by_pattern(url_pattern: str, dry_run: bool = True) -> Dict[str, int]:
    """Convenience function to delete games by URL pattern."""
    with DatabaseService() as db:
        return db.game_data.delete_games_by_url_pattern(url_pattern, dry_run)


# Update convenience functions
def update_single_game(game_id: int, game_data: Dict[str, Any], 
                      game_url: Optional[str] = None) -> bool:
    """Convenience function to update a single game."""
    with DatabaseService() as db:
        result = db.game_data.update_game_data(game_id, game_data, game_url)
        return result is not None


def upsert_single_game(game_id: int, season: int, game_type: str,
                      game_url: str, game_data: Dict[str, Any]) -> bool:
    """Convenience function to insert or update a game (upsert)."""
    with DatabaseService() as db:
        result = db.game_data.upsert_game_data(game_id, season, game_type, game_url, game_data)
        return result is not None


def refresh_game_data(game_id: int, force_refresh: bool = False) -> bool:
    """Convenience function to refresh game data from its URL."""
    with DatabaseService() as db:
        result = db.game_data.refresh_game_from_url(game_id, force_refresh)
        return result is not None


def update_multiple_games(updates: List[Dict[str, Any]]) -> Dict[str, int]:
    """Convenience function to update multiple games in batch."""
    with DatabaseService() as db:
        return db.game_data.update_multiple_games(updates)


# Player convenience functions
def get_player_by_id(person_id: int) -> Optional[Person]:
    """Convenience function to get a player by ID."""
    with DatabaseService() as db:
        return db.person.get_player_by_id(person_id)


def get_player_by_name(name: str) -> Optional[Person]:
    """Convenience function to get a player by name."""
    with DatabaseService() as db:
        return db.person.get_player_by_name(name)


def get_player_season_stats(person_id: int, season: int, 
                          game_type: str = "regular") -> Optional[Dict[str, Any]]:
    """Convenience function to get player season totals."""
    with DatabaseService() as db:
        return db.person.get_player_season_totals(person_id, season, game_type)


def get_player_games(person_id: int, season: int, 
                   game_type: str = "regular") -> List[Boxscore]:
    """Convenience function to get all games for a player in a season."""
    with DatabaseService() as db:
        return db.person.get_player_stats_by_season(person_id, season, game_type)


# Team convenience functions
def get_team_by_id(team_id: int) -> Optional[Team]:
    """Convenience function to get a team by ID."""
    with DatabaseService() as db:
        return db.team.get_team_by_id(team_id)


def get_team_by_tricode(tricode: str) -> Optional[Team]:
    """Convenience function to get a team by tricode."""
    with DatabaseService() as db:
        return db.team.get_team_by_tricode(tricode)


def get_team_season_stats(team_id: int, season: int, 
                        game_type: str = "regular") -> Optional[Dict[str, Any]]:
    """Convenience function to get team season stats."""
    with DatabaseService() as db:
        return db.team.get_team_stats_by_season(team_id, season, game_type)


def get_all_teams() -> List[Team]:
    """Convenience function to get all teams."""
    with DatabaseService() as db:
        return db.team.get_all_teams()


def get_all_active_players(cutoff_date: Optional[datetime] = None, 
                          role: str = "player") -> List[Person]:
    """Convenience function to get all active players."""
    with DatabaseService() as db:
        return db.person.get_all_active_players(cutoff_date, role)


def get_all_active_teams(cutoff_date: Optional[datetime] = None) -> List[Team]:
    """Convenience function to get all active teams."""
    with DatabaseService() as db:
        return db.team.get_all_active_teams(cutoff_date)


# Analytics convenience functions
def compare_players_by_season(player_ids: List[int], season: int, 
                            game_type: str = "regular") -> List[Dict[str, Any]]:
    """Compare multiple players' stats for a season."""
    results = []
    with DatabaseService() as db:
        for player_id in player_ids:
            stats = db.person.get_player_season_totals(player_id, season, game_type)
            if stats:
                player = db.person.get_player_by_id(player_id)
                if player:
                    stats['player_name'] = player.person_name
                results.append(stats)
    return results


def get_season_leaders(season: int, stat: str, game_type: str = "regular", 
                      limit: int = 10) -> List[Dict[str, Any]]:
    """Get season leaders for a specific stat."""
    # This would require more complex aggregation - placeholder for now
    # Implementation would aggregate stats and order by the specified stat
    with DatabaseService() as db:
        # Would implement proper aggregation query here
        return []


def get_head_to_head_stats(team1_id: int, team2_id: int, season: int, 
                          game_type: str = "regular") -> Dict[str, Any]:
    """Get head-to-head stats between two teams for a season."""
    with DatabaseService() as db:
        # Would implement head-to-head comparison logic here
        return {
            'team1_id': team1_id,
            'team2_id': team2_id,
            'season': season,
            'game_type': game_type,
            'games_played': 0,  # Placeholder
            'team1_wins': 0,
            'team2_wins': 0
        }