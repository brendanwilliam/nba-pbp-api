"""
Population services for inserting extracted JSON data into normalized tables.
Handles bulk insertions, conflict resolution, and transaction management.
"""

from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
import logging

from .models import Arena, Team, Person, Game, TeamGame, PersonGame, Play, Boxscore
from .json_extractors import (
    ArenaExtractor, TeamExtractor, GameExtractor, 
    PersonExtractor, PlayExtractor, BoxscoreExtractor
)

logger = logging.getLogger(__name__)


class DataValidationService:
    """Validates extracted data before insertion"""
    
    @staticmethod
    def validate_arena(arena_data: Dict[str, Any]) -> bool:
        """Validate arena data"""
        required_fields = ['arena_id']
        return all(arena_data.get(field) is not None for field in required_fields)
    
    @staticmethod
    def validate_team(team_data: Dict[str, Any]) -> bool:
        """Validate team data"""
        required_fields = ['team_id']
        return all(team_data.get(field) is not None for field in required_fields)
    
    @staticmethod
    def validate_person(person_data: Dict[str, Any]) -> bool:
        """Validate person data"""
        required_fields = ['person_id']
        return all(person_data.get(field) is not None for field in required_fields)
    
    @staticmethod
    def validate_game(game_data: Dict[str, Any]) -> bool:
        """Validate game data"""
        required_fields = ['game_id', 'arena_id', 'home_team_id', 'away_team_id']
        return all(game_data.get(field) is not None for field in required_fields)
    
    @staticmethod
    def validate_play(play_data: Dict[str, Any]) -> bool:
        """Validate play data"""
        required_fields = ['game_id']
        return all(play_data.get(field) is not None for field in required_fields)
    
    @staticmethod
    def validate_boxscore(boxscore_data: Dict[str, Any]) -> bool:
        """Validate boxscore data"""
        required_fields = ['game_id', 'home_away_team', 'box_type']
        return all(boxscore_data.get(field) is not None for field in required_fields)


class BulkInsertService:
    """Handles efficient bulk insertions with conflict resolution"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def bulk_insert_arenas(self, arenas: List[Dict[str, Any]], game_et: datetime) -> int:
        """
        Bulk insert arenas with value-based conflict detection and temporal tracking.
        Only skips insertion if arena_id exists AND all values are identical.
        Updates last_used for exact matches, creates new versions for different values.
        """
        if not arenas:
            return 0
        
        valid_arenas = [
            arena for arena in arenas 
            if DataValidationService.validate_arena(arena)
        ]
        
        if not valid_arenas:
            return 0
        
        try:
            inserted_count = 0
            updated_count = 0
            
            for arena_data in valid_arenas:
                arena_id = arena_data['arena_id']
                
                # Find existing arenas with same arena_id
                existing_arenas = self.session.query(Arena).filter_by(arena_id=arena_id).all()
                
                # Check if any existing arena has identical values
                exact_match = None
                for existing in existing_arenas:
                    if self._arenas_match(existing, arena_data):
                        exact_match = existing
                        break
                
                if exact_match:
                    # Update last_used timestamp only if this game is more recent
                    # Handle timezone comparison carefully
                    should_update = exact_match.last_used is None
                    if not should_update and exact_match.last_used is not None:
                        try:
                            # Convert both to naive datetime for comparison if needed
                            game_et_naive = game_et.replace(tzinfo=None) if game_et.tzinfo else game_et
                            last_used_naive = exact_match.last_used.replace(tzinfo=None) if exact_match.last_used.tzinfo else exact_match.last_used
                            should_update = game_et_naive > last_used_naive
                        except (AttributeError, TypeError):
                            # Fallback - just update if we can't compare
                            should_update = True
                    
                    if should_update:
                        exact_match.last_used = game_et
                        updated_count += 1
                        logger.debug(f"Updated last_used for arena {arena_id} to {game_et}")
                    else:
                        logger.debug(f"Arena {arena_id} already has more recent last_used: {exact_match.last_used}")
                else:
                    # Insert new version with temporal tracking
                    arena_data['first_used'] = game_et
                    arena_data['last_used'] = game_et
                    
                    stmt = insert(Arena).values([arena_data])
                    self.session.execute(stmt)
                    inserted_count += 1
                    logger.debug(f"Inserted new arena version {arena_id} with timestamp {game_et}")
            
            logger.info(f"Arena processing: {inserted_count} inserted, {updated_count} updated")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error bulk inserting arenas: {e}")
            raise
    
    def _arenas_match(self, existing_arena: Arena, arena_data: Dict[str, Any]) -> bool:
        """Check if existing arena matches all values in arena_data (excluding temporal fields)"""
        comparison_fields = [
            'arena_city', 'arena_name', 'arena_state', 'arena_country',
            'arena_timezone', 'arena_postal_code', 'arena_street_address'
        ]
        
        for field in comparison_fields:
            existing_value = getattr(existing_arena, field, None)
            new_value = arena_data.get(field)
            if existing_value != new_value:
                return False
        return True
    
    def bulk_insert_teams(self, teams: List[Dict[str, Any]], game_et: datetime) -> int:
        """
        Bulk insert teams with value-based conflict detection and temporal tracking.
        Only skips insertion if team_id exists AND all values are identical.
        Updates last_used for exact matches, creates new versions for different values.
        """
        if not teams:
            return 0
        
        valid_teams = [
            team for team in teams 
            if DataValidationService.validate_team(team)
        ]
        
        if not valid_teams:
            return 0
        
        try:
            inserted_count = 0
            updated_count = 0
            
            # Remove duplicates within the batch first
            seen = {}
            unique_teams = []
            for team in valid_teams:
                team_id = team['team_id']
                # Use values as key to identify truly unique teams in this batch
                team_key = (team_id, team.get('team_city'), team.get('team_name'), team.get('team_tricode'))
                if team_key not in seen:
                    seen[team_key] = team
                    unique_teams.append(team)
            
            for team_data in unique_teams:
                team_id = team_data['team_id']
                
                # Find existing teams with same team_id
                existing_teams = self.session.query(Team).filter_by(team_id=team_id).all()
                
                # Check if any existing team has identical values
                exact_match = None
                for existing in existing_teams:
                    if self._teams_match(existing, team_data):
                        exact_match = existing
                        break
                
                if exact_match:
                    # Update last_used timestamp only if this game is more recent
                    # Handle timezone comparison carefully
                    should_update = exact_match.last_used is None
                    if not should_update and exact_match.last_used is not None:
                        try:
                            # Convert both to naive datetime for comparison if needed
                            game_et_naive = game_et.replace(tzinfo=None) if game_et.tzinfo else game_et
                            last_used_naive = exact_match.last_used.replace(tzinfo=None) if exact_match.last_used.tzinfo else exact_match.last_used
                            should_update = game_et_naive > last_used_naive
                        except (AttributeError, TypeError):
                            # Fallback - just update if we can't compare
                            should_update = True
                    
                    if should_update:
                        exact_match.last_used = game_et
                        updated_count += 1
                        logger.debug(f"Updated last_used for team {team_id} to {game_et}")
                    else:
                        logger.debug(f"Team {team_id} already has more recent last_used: {exact_match.last_used}")
                else:
                    # Insert new version with temporal tracking
                    team_data['first_used'] = game_et
                    team_data['last_used'] = game_et
                    
                    stmt = insert(Team).values([team_data])
                    self.session.execute(stmt)
                    inserted_count += 1
                    logger.debug(f"Inserted new team version {team_id} with timestamp {game_et}")
            
            logger.info(f"Team processing: {inserted_count} inserted, {updated_count} updated")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error bulk inserting teams: {e}")
            raise
    
    def _teams_match(self, existing_team: Team, team_data: Dict[str, Any]) -> bool:
        """Check if existing team matches all values in team_data (excluding temporal fields)"""
        comparison_fields = ['team_city', 'team_name', 'team_tricode']
        
        for field in comparison_fields:
            existing_value = getattr(existing_team, field, None)
            new_value = team_data.get(field)
            if existing_value != new_value:
                return False
        return True
    
    def bulk_insert_persons(self, persons: List[Dict[str, Any]], game_et: datetime) -> int:
        """
        Bulk insert persons with value-based conflict detection and temporal tracking.
        Only skips insertion if person_id exists AND all values are identical.
        Updates last_used for exact matches, creates new versions for different values.
        """
        if not persons:
            return 0
        
        valid_persons = [
            person for person in persons 
            if DataValidationService.validate_person(person)
        ]
        
        if not valid_persons:
            return 0
        
        try:
            inserted_count = 0
            updated_count = 0
            
            # Remove duplicates within the batch first
            seen = {}
            unique_persons = []
            for person in valid_persons:
                person_id = person['person_id']
                # Use values as key to identify truly unique persons in this batch
                person_key = (
                    person_id, 
                    person.get('person_name'), 
                    person.get('person_iname'),
                    person.get('person_fname'),
                    person.get('person_lname'),
                    person.get('person_role')
                )
                if person_key not in seen:
                    seen[person_key] = person
                    unique_persons.append(person)
            
            for person_data in unique_persons:
                person_id = person_data['person_id']
                
                # Find existing persons with same person_id
                existing_persons = self.session.query(Person).filter_by(person_id=person_id).all()
                
                # Check if any existing person has identical values
                exact_match = None
                for existing in existing_persons:
                    if self._persons_match(existing, person_data):
                        exact_match = existing
                        break
                
                if exact_match:
                    # Update last_used timestamp only if this game is more recent
                    # Handle timezone comparison carefully
                    should_update = exact_match.last_used is None
                    if not should_update and exact_match.last_used is not None:
                        try:
                            # Convert both to naive datetime for comparison if needed
                            game_et_naive = game_et.replace(tzinfo=None) if game_et.tzinfo else game_et
                            last_used_naive = exact_match.last_used.replace(tzinfo=None) if exact_match.last_used.tzinfo else exact_match.last_used
                            should_update = game_et_naive > last_used_naive
                        except (AttributeError, TypeError):
                            # Fallback - just update if we can't compare
                            should_update = True
                    
                    if should_update:
                        exact_match.last_used = game_et
                        updated_count += 1
                        logger.debug(f"Updated last_used for person {person_id} to {game_et}")
                    else:
                        logger.debug(f"Person {person_id} already has more recent last_used: {exact_match.last_used}")
                else:
                    # Insert new version with temporal tracking
                    person_data['first_used'] = game_et
                    person_data['last_used'] = game_et
                    
                    stmt = insert(Person).values([person_data])
                    self.session.execute(stmt)
                    inserted_count += 1
                    logger.debug(f"Inserted new person version {person_id} with timestamp {game_et}")
            
            logger.info(f"Person processing: {inserted_count} inserted, {updated_count} updated")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error bulk inserting persons: {e}")
            raise
    
    def _persons_match(self, existing_person: Person, person_data: Dict[str, Any]) -> bool:
        """Check if existing person matches all values in person_data (excluding temporal fields)"""
        comparison_fields = [
            'person_name', 'person_iname', 'person_fname', 
            'person_lname', 'person_role'
        ]
        
        for field in comparison_fields:
            existing_value = getattr(existing_person, field, None)
            new_value = person_data.get(field)
            if existing_value != new_value:
                return False
        return True
    
    def bulk_insert_games(self, games: List[Dict[str, Any]]) -> int:
        """Bulk insert games with ON CONFLICT DO NOTHING"""
        if not games:
            return 0
        
        valid_games = [
            game for game in games 
            if DataValidationService.validate_game(game)
        ]
        
        if not valid_games:
            return 0
        
        try:
            # Check for existing games to avoid conflicts
            game_ids_to_check = [game['game_id'] for game in valid_games]
            existing_games = self.session.query(Game.game_id).filter(
                Game.game_id.in_(game_ids_to_check)
            ).all()
            existing_game_ids = {game.game_id for game in existing_games}
            
            # Filter out games that already exist
            new_games = [
                game for game in valid_games 
                if game['game_id'] not in existing_game_ids
            ]
            
            if not new_games:
                return 0
            
            stmt = insert(Game).values(new_games)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting games: {e}")
            raise
    
    def bulk_insert_team_games(self, team_games: List[Dict[str, Any]]) -> int:
        """Bulk insert team-game relationships"""
        if not team_games:
            return 0
        
        try:
            # Remove duplicates based on game_id + team_id
            seen = set()
            unique_team_games = []
            for tg in team_games:
                key = (tg['game_id'], tg['team_id'])
                if key not in seen:
                    seen.add(key)
                    unique_team_games.append(tg)
            
            stmt = insert(TeamGame).values(unique_team_games)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting team games: {e}")
            raise
    
    def bulk_insert_person_games(self, person_games: List[Dict[str, Any]]) -> int:
        """Bulk insert person-game relationships"""
        if not person_games:
            return 0
        
        try:
            # Remove duplicates based on game_id + person_id + team_id
            seen = set()
            unique_person_games = []
            for pg in person_games:
                key = (pg['game_id'], pg['person_id'], pg.get('team_id'))
                if key not in seen:
                    seen.add(key)
                    unique_person_games.append(pg)
            
            stmt = insert(PersonGame).values(unique_person_games)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting person games: {e}")
            raise
    
    def bulk_insert_plays(self, plays: List[Dict[str, Any]]) -> int:
        """Bulk insert plays with validation"""
        if not plays:
            return 0
        
        valid_plays = [
            play for play in plays 
            if DataValidationService.validate_play(play)
        ]
        
        if not valid_plays:
            return 0
        
        try:
            stmt = insert(Play).values(valid_plays)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting plays: {e}")
            raise
    
    def bulk_insert_boxscores(self, boxscores: List[Dict[str, Any]]) -> int:
        """Bulk insert boxscore entries"""
        if not boxscores:
            return 0
        
        valid_boxscores = [
            boxscore for boxscore in boxscores 
            if DataValidationService.validate_boxscore(boxscore)
        ]
        
        if not valid_boxscores:
            return 0
        
        try:
            stmt = insert(Boxscore).values(valid_boxscores)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting boxscores: {e}")
            raise


class GamePopulationService:
    """Orchestrates the full game population process"""
    
    def __init__(self, session: Session):
        self.session = session
        self.bulk_service = BulkInsertService(session)
    
    def populate_game(self, game_json: Dict[str, Any]) -> Dict[str, int]:
        """
        Populate all tables for a single game.
        Returns count of records inserted for each table.
        """
        game_id = int(game_json['boxscore']['gameId'])
        logger.info(f"Starting population for game {game_id}")
        
        # Extract game datetime for temporal tracking
        game_data = GameExtractor.extract(game_json)
        game_et = game_data.get('game_et')
        
        if not game_et:
            logger.warning(f"No game_et found for game {game_id}, using current time")
            game_et = datetime.now()
        
        results = {
            'arenas': 0,
            'teams': 0,
            'persons': 0,
            'games': 0,
            'team_games': 0,
            'person_games': 0,
            'plays': 0,
            'boxscores': 0
        }
        
        try:
            # Phase 1: Independent tables (no foreign key dependencies)
            
            # 1. Arena
            arena_data = ArenaExtractor.extract(game_json)
            results['arenas'] = self.bulk_service.bulk_insert_arenas([arena_data], game_et)
            
            # 2. Teams
            team_data = TeamExtractor.extract_teams_from_game(game_json)
            results['teams'] = self.bulk_service.bulk_insert_teams(team_data, game_et)
            
            # 3. Persons
            person_data = PersonExtractor.extract_persons_from_game(game_json)
            results['persons'] = self.bulk_service.bulk_insert_persons(person_data, game_et)
            
            # Phase 2: Game table (depends on Arena)
            
            # 4. Game - resolve arena_internal_id (we already have game_data from above)
            arena_api_id = game_data['arena_id']
            arena = self.session.query(Arena).filter_by(arena_id=arena_api_id).first()
            if arena:
                game_data['arena_internal_id'] = arena.id
            else:
                # This shouldn't happen if arena was inserted above
                logger.warning(f"Arena with arena_id {arena_api_id} not found for game {game_id}")
                game_data['arena_internal_id'] = None
            
            results['games'] = self.bulk_service.bulk_insert_games([game_data])
            
            # Phase 3: Junction tables and dependent data
            
            # 5. TeamGame relationships
            team_games = self._create_team_game_relationships(game_json)
            results['team_games'] = self.bulk_service.bulk_insert_team_games(team_games)
            
            # 6. PersonGame relationships  
            person_games = self._create_person_game_relationships(game_json)
            results['person_games'] = self.bulk_service.bulk_insert_person_games(person_games)
            
            # 7. Plays
            plays = PlayExtractor.extract_plays_from_game(game_json)
            # Resolve team_id for plays
            plays = self._resolve_team_ids_for_plays(plays, game_json)
            results['plays'] = self.bulk_service.bulk_insert_plays(plays)
            
            # 8. Boxscores
            boxscores = BoxscoreExtractor.extract_boxscores_from_game(game_json)
            # Resolve team_id for boxscores
            boxscores = self._resolve_team_ids_for_boxscores(boxscores, game_json)
            results['boxscores'] = self.bulk_service.bulk_insert_boxscores(boxscores)
            
            logger.info(f"Completed population for game {game_id}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error populating game {game_id}: {e}")
            raise
    
    def _create_team_game_relationships(self, game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create TeamGame junction records"""
        game_id = int(game_json['boxscore']['gameId'])
        boxscore = game_json['boxscore']
        
        team_games = []
        
        # Get team IDs from database
        home_team_api_id = boxscore['homeTeam']['teamId']
        away_team_api_id = boxscore['awayTeam']['teamId']
        
        # Query database to get internal team IDs
        home_team = self.session.query(Team).filter_by(team_id=home_team_api_id).first()
        away_team = self.session.query(Team).filter_by(team_id=away_team_api_id).first()
        
        if home_team:
            team_games.append({
                'game_id': game_id,
                'team_id': home_team.id
            })
        
        if away_team:
            team_games.append({
                'game_id': game_id,
                'team_id': away_team.id
            })
        
        return team_games
    
    def _create_person_game_relationships(self, game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create PersonGame junction records"""
        game_id = int(game_json['boxscore']['gameId'])
        boxscore = game_json['boxscore']
        person_games = []
        
        # Map team API IDs to database IDs
        team_id_mapping = {}
        for team_type, team_key in [('homeTeam', 'home'), ('awayTeam', 'away')]:
            if team_type in boxscore:
                api_team_id = boxscore[team_type]['teamId']
                db_team = self.session.query(Team).filter_by(team_id=api_team_id).first()
                if db_team:
                    team_id_mapping[api_team_id] = db_team.id
        
        # Players from both teams
        for team_type in ['homeTeam', 'awayTeam']:
            if team_type in boxscore and 'players' in boxscore[team_type]:
                api_team_id = boxscore[team_type]['teamId']
                db_team_id = team_id_mapping.get(api_team_id)
                
                for player in boxscore[team_type]['players']:
                    person_api_id = player['personId']
                    # Resolve person_internal_id
                    db_person = self.session.query(Person).filter_by(person_id=person_api_id).first()
                    person_internal_id = db_person.id if db_person else None
                    
                    person_games.append({
                        'game_id': game_id,
                        'person_id': person_api_id,
                        'person_internal_id': person_internal_id,
                        'team_id': db_team_id
                    })
        
        # Officials (no team association)
        if 'officials' in boxscore:
            for official in boxscore['officials']:
                person_api_id = official['personId']
                # Resolve person_internal_id
                db_person = self.session.query(Person).filter_by(person_id=person_api_id).first()
                person_internal_id = db_person.id if db_person else None
                
                person_games.append({
                    'game_id': game_id,
                    'person_id': person_api_id,
                    'person_internal_id': person_internal_id,
                    'team_id': None
                })
        
        return person_games
    
    def _resolve_team_ids_for_plays(self, plays: List[Dict[str, Any]], 
                                   game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve API team IDs to database team IDs in plays"""
        # Get team ID mapping
        team_id_mapping = self._get_team_id_mapping(game_json)
        
        # Update plays with resolved team IDs
        for play in plays:
            if play.get('team_id') in team_id_mapping:
                play['team_id'] = team_id_mapping[play['team_id']]
            else:
                play['team_id'] = None
        
        # Also resolve person_internal_id for plays
        for play in plays:
            person_api_id = play.get('person_id')
            if person_api_id:
                db_person = self.session.query(Person).filter_by(person_id=person_api_id).first()
                play['person_internal_id'] = db_person.id if db_person else None
            else:
                play['person_internal_id'] = None
        
        return plays
    
    def _resolve_team_ids_for_boxscores(self, boxscores: List[Dict[str, Any]], 
                                       game_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve API team IDs to database team IDs in boxscores"""
        boxscore = game_json['boxscore']
        
        # Map home/away to database team IDs
        home_team_api_id = boxscore['homeTeam']['teamId']
        away_team_api_id = boxscore['awayTeam']['teamId']
        
        home_team = self.session.query(Team).filter_by(team_id=home_team_api_id).first()
        away_team = self.session.query(Team).filter_by(team_id=away_team_api_id).first()
        
        # Update boxscores with resolved team IDs and person_internal_id
        for boxscore_entry in boxscores:
            if boxscore_entry['home_away_team'] == 'h' and home_team:
                boxscore_entry['team_id'] = home_team.id
            elif boxscore_entry['home_away_team'] == 'a' and away_team:
                boxscore_entry['team_id'] = away_team.id
                
            # Resolve person_internal_id for boxscore entries
            person_api_id = boxscore_entry.get('person_id')
            if person_api_id:
                db_person = self.session.query(Person).filter_by(person_id=person_api_id).first()
                boxscore_entry['person_internal_id'] = db_person.id if db_person else None
            else:
                boxscore_entry['person_internal_id'] = None
        
        return boxscores
    
    def _get_team_id_mapping(self, game_json: Dict[str, Any]) -> Dict[int, int]:
        """Get mapping from API team IDs to database team IDs"""
        boxscore = game_json['boxscore']
        mapping = {}
        
        for team_type in ['homeTeam', 'awayTeam']:
            if team_type in boxscore:
                api_team_id = boxscore[team_type]['teamId']
                db_team = self.session.query(Team).filter_by(team_id=api_team_id).first()
                if db_team:
                    mapping[api_team_id] = db_team.id
        
        return mapping
    
    def clear_game_data(self, game_id: int) -> Dict[str, int]:
        """
        Clear all data for a specific game from all tables.
        Returns count of records deleted from each table.
        
        Args:
            game_id: The game ID to clear data for
            
        Returns:
            Dictionary with deletion counts for each table
        """
        logger.info(f"Clearing existing data for game {game_id}")
        
        deletion_counts = {
            'boxscores': 0,
            'plays': 0, 
            'person_games': 0,
            'team_games': 0,
            'games': 0
            # Note: Not clearing arenas, teams, persons as they may be shared across games
        }
        
        try:
            # Delete in reverse dependency order
            
            # 1. Boxscores (depends on game, person, team)
            result = self.session.query(Boxscore).filter(Boxscore.game_id == game_id).delete()
            deletion_counts['boxscores'] = result
            logger.info(f"Deleted {result} boxscore records for game {game_id}")
            
            # 2. Plays (depends on game, person, team)  
            result = self.session.query(Play).filter(Play.game_id == game_id).delete()
            deletion_counts['plays'] = result
            logger.info(f"Deleted {result} play records for game {game_id}")
            
            # 3. PersonGame junction records
            result = self.session.query(PersonGame).filter(PersonGame.game_id == game_id).delete()
            deletion_counts['person_games'] = result
            logger.info(f"Deleted {result} person_game records for game {game_id}")
            
            # 4. TeamGame junction records
            result = self.session.query(TeamGame).filter(TeamGame.game_id == game_id).delete()
            deletion_counts['team_games'] = result
            logger.info(f"Deleted {result} team_game records for game {game_id}")
            
            # 5. Game record itself
            result = self.session.query(Game).filter(Game.game_id == game_id).delete()
            deletion_counts['games'] = result
            logger.info(f"Deleted {result} game record for game {game_id}")
            
            logger.info(f"Completed clearing data for game {game_id}: {deletion_counts}")
            return deletion_counts
            
        except Exception as e:
            logger.error(f"Error clearing data for game {game_id}: {e}")
            raise