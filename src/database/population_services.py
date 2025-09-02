"""
Population services for inserting extracted JSON data into normalized tables.
Handles bulk insertions, conflict resolution, and transaction management.
"""

from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
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
    
    def bulk_insert_arenas(self, arenas: List[Dict[str, Any]]) -> int:
        """Bulk insert arenas with ON CONFLICT DO NOTHING"""
        if not arenas:
            return 0
        
        valid_arenas = [
            arena for arena in arenas 
            if DataValidationService.validate_arena(arena)
        ]
        
        if not valid_arenas:
            return 0
        
        try:
            # Check for existing arenas to avoid conflicts
            arena_ids_to_check = [arena['arena_id'] for arena in valid_arenas]
            existing_arenas = self.session.query(Arena.arena_id).filter(
                Arena.arena_id.in_(arena_ids_to_check)
            ).all()
            existing_arena_ids = {arena.arena_id for arena in existing_arenas}
            
            # Filter out arenas that already exist
            new_arenas = [
                arena for arena in valid_arenas 
                if arena['arena_id'] not in existing_arena_ids
            ]
            
            if not new_arenas:
                return 0
            
            stmt = insert(Arena).values(new_arenas)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting arenas: {e}")
            raise
    
    def bulk_insert_teams(self, teams: List[Dict[str, Any]]) -> int:
        """Bulk insert teams, avoiding duplicates"""
        if not teams:
            return 0
        
        valid_teams = [
            team for team in teams 
            if DataValidationService.validate_team(team)
        ]
        
        if not valid_teams:
            return 0
        
        try:
            # Remove duplicates within the batch first
            seen = set()
            unique_teams = []
            for team in valid_teams:
                team_id = team['team_id']
                if team_id not in seen:
                    seen.add(team_id)
                    unique_teams.append(team)
            
            if not unique_teams:
                return 0
            
            # Check for existing teams to avoid trying to insert duplicates
            existing_team_ids = set()
            team_ids_to_check = [team['team_id'] for team in unique_teams]
            
            if team_ids_to_check:
                existing_teams = self.session.query(Team.team_id).filter(
                    Team.team_id.in_(team_ids_to_check)
                ).all()
                existing_team_ids = {team.team_id for team in existing_teams}
            
            # Filter out teams that already exist
            new_teams = [
                team for team in unique_teams 
                if team['team_id'] not in existing_team_ids
            ]
            
            if not new_teams:
                return 0
            
            # Insert new teams without conflict resolution
            stmt = insert(Team).values(new_teams)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting teams: {e}")
            raise
    
    def bulk_insert_persons(self, persons: List[Dict[str, Any]]) -> int:
        """Bulk insert persons with ON CONFLICT DO NOTHING"""
        if not persons:
            return 0
        
        valid_persons = [
            person for person in persons 
            if DataValidationService.validate_person(person)
        ]
        
        if not valid_persons:
            return 0
        
        try:
            # Check for existing persons to avoid conflicts
            person_ids_to_check = [person['person_id'] for person in valid_persons]
            existing_persons = self.session.query(Person.person_id).filter(
                Person.person_id.in_(person_ids_to_check)
            ).all()
            existing_person_ids = {person.person_id for person in existing_persons}
            
            # Filter out persons that already exist
            new_persons = [
                person for person in valid_persons 
                if person['person_id'] not in existing_person_ids
            ]
            
            if not new_persons:
                return 0
            
            stmt = insert(Person).values(new_persons)
            result = self.session.execute(stmt)
            return result.rowcount
        except Exception as e:
            logger.error(f"Error bulk inserting persons: {e}")
            raise
    
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
            results['arenas'] = self.bulk_service.bulk_insert_arenas([arena_data])
            
            # 2. Teams
            team_data = TeamExtractor.extract_teams_from_game(game_json)
            results['teams'] = self.bulk_service.bulk_insert_teams(team_data)
            
            # 3. Persons
            person_data = PersonExtractor.extract_persons_from_game(game_json)
            results['persons'] = self.bulk_service.bulk_insert_persons(person_data)
            
            # Phase 2: Game table (depends on Arena)
            
            # 4. Game - need to resolve arena_internal_id
            game_data = GameExtractor.extract(game_json)
            
            # Resolve arena_internal_id from arena_id
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