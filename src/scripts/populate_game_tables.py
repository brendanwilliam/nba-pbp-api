#!/usr/bin/env python3
"""
Main script for populating normalized WNBA game tables from raw JSON data.
Processes games from raw_game_data table and populates the 8 normalized tables.
"""

import argparse
import logging
import sys
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text

from ..database.services import DatabaseConnection
from ..database.models import RawGameData
from ..database.population_services import GamePopulationService
from ..database.services import DatabaseService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('game_population.log')
    ]
)
logger = logging.getLogger(__name__)


class GameTablePopulator:
    """Main orchestrator for populating game tables"""
    
    def __init__(self):
        self.db_connection = DatabaseConnection()
        self.engine = self.db_connection.get_engine()
        self.Session = sessionmaker(bind=self.engine)
    
    def populate_all_games(self, limit: Optional[int] = None, 
                          resume_from_game_id: Optional[int] = None,
                          override_existing: bool = False) -> dict:
        """
        Populate all games from raw_game_data table.
        
        Args:
            limit: Maximum number of games to process
            resume_from_game_id: Resume processing from this game ID
            override_existing: If True, reprocess games that already exist in tables
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info("Starting population of all games")
        
        with self.Session() as session:
            # Get games to process
            query = session.query(RawGameData).order_by(RawGameData.game_id)
            
            if resume_from_game_id:
                query = query.filter(RawGameData.game_id >= resume_from_game_id)
                logger.info(f"Resuming from game ID: {resume_from_game_id}")
            
            if limit:
                query = query.limit(limit)
                logger.info(f"Processing limit: {limit} games")
            
            games = query.all()
            logger.info(f"Found {len(games)} games to process")
            
            # Sort games chronologically by extracting game_et from JSON data
            logger.info("Sorting games chronologically to ensure correct first_used timestamps...")
            games = self._sort_games_chronologically(games)
            
            return self._process_games(games, override_existing=override_existing)
    
    def populate_specific_games(self, game_ids: List[int], override_existing: bool = False) -> dict:
        """
        Populate specific games by ID.
        
        Args:
            game_ids: List of game IDs to process
            override_existing: If True, reprocess games that already exist in tables
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Starting population of {len(game_ids)} specific games")
        
        with self.Session() as session:
            games = (session.query(RawGameData)
                    .filter(RawGameData.game_id.in_(game_ids))
                    .order_by(RawGameData.game_id)
                    .all())
            
            found_ids = [g.game_id for g in games]
            missing_ids = set(game_ids) - set(found_ids)
            
            if missing_ids:
                logger.warning(f"Games not found in raw data: {sorted(missing_ids)}")
            
            logger.info(f"Found {len(games)} games to process")
            
            # Sort games chronologically by extracting game_et from JSON data
            logger.info("Sorting games chronologically to ensure correct first_used timestamps...")
            games = self._sort_games_chronologically(games)
            
            return self._process_games(games, override_existing=override_existing)
    
    def populate_games_by_season(self, seasons: List[int], 
                                limit: Optional[int] = None,
                                override_existing: bool = False) -> dict:
        """
        Populate games by season(s).
        
        Args:
            seasons: List of seasons to process (e.g., [2024])
            limit: Maximum number of games per season
            override_existing: If True, reprocess games that already exist in tables
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Starting population for seasons: {seasons}")
        
        with self.Session() as session:
            query = (session.query(RawGameData)
                    .filter(RawGameData.season.in_(seasons))
                    .order_by(RawGameData.season, RawGameData.game_id))
            
            if limit:
                query = query.limit(limit)
                logger.info(f"Processing limit: {limit} games per season")
            
            games = query.all()
            logger.info(f"Found {len(games)} games to process")
            
            # Sort games chronologically by extracting game_et from JSON data
            logger.info("Sorting games chronologically to ensure correct first_used timestamps...")
            games = self._sort_games_chronologically(games)
            
            return self._process_games(games, override_existing=override_existing)
    
    def _sort_games_chronologically(self, games: List[RawGameData]) -> List[RawGameData]:
        """
        Sort games chronologically by extracting game_et from JSON data.
        This ensures first_used timestamps are set correctly.
        """
        def extract_game_et(raw_game: RawGameData):
            """Extract game_et timestamp from JSON data for sorting"""
            try:
                game_data = raw_game.game_data
                if 'boxscore' in game_data and 'gameEt' in game_data['boxscore']:
                    game_et_str = game_data['boxscore']['gameEt']
                    if game_et_str:
                        from datetime import datetime
                        return datetime.fromisoformat(game_et_str.replace('Z', '+00:00'))
                
                # Fallback: use game_id as proxy for chronological order within same format
                return datetime(1900, 1, 1)  # Very early date for games without timestamps
                
            except Exception as e:
                logger.warning(f"Could not extract game_et from game {raw_game.game_id}: {e}")
                return datetime(1900, 1, 1)  # Very early date for problematic games
        
        # Sort by game_et timestamp
        sorted_games = sorted(games, key=extract_game_et)
        
        if len(sorted_games) > 0:
            first_date = extract_game_et(sorted_games[0])
            last_date = extract_game_et(sorted_games[-1])
            logger.info(f"Games sorted chronologically: {first_date} to {last_date}")
        
        return sorted_games
    
    def _process_games(self, games: List[RawGameData], override_existing: bool = False) -> dict:
        """
        Process a list of games with transaction management.
        
        Args:
            games: List of RawGameData objects to process
            override_existing: If True, clear existing data for each game before processing
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'total_games': len(games),
            'successful_games': 0,
            'failed_games': 0,
            'failed_game_ids': [],
            'table_counts': {
                'arenas': 0,
                'teams': 0,
                'persons': 0,
                'games': 0,
                'team_games': 0,
                'person_games': 0,
                'plays': 0,
                'boxscores': 0
            },
            'start_time': datetime.now(),
            'end_time': None
        }
        
        for i, raw_game in enumerate(games, 1):
            game_id = raw_game.game_id
            
            try:
                # Process each game in its own transaction
                with self.Session() as session:
                    population_service = GamePopulationService(session)
                    
                    logger.info(f"Processing game {game_id} ({i}/{len(games)})")
                    
                    # Clear existing data if override is requested
                    if override_existing:
                        logger.info(f"Override flag set - clearing existing data for game {game_id}")
                        population_service.clear_game_data(game_id)
                    
                    # Populate the game
                    game_results = population_service.populate_game(raw_game.game_data)
                    
                    # Commit the transaction
                    session.commit()
                    
                    # Update statistics
                    stats['successful_games'] += 1
                    for table, count in game_results.items():
                        stats['table_counts'][table] += count
                    
                    # Log progress every 10 games
                    if i % 10 == 0:
                        logger.info(f"Progress: {i}/{len(games)} games processed")
                    
            except Exception as e:
                logger.error(f"Failed to process game {game_id}: {e}")
                stats['failed_games'] += 1
                stats['failed_game_ids'].append(game_id)
                
                # Continue with next game
                continue
        
        stats['end_time'] = datetime.now()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        self._log_final_statistics(stats)
        return stats
    
    def _log_final_statistics(self, stats: dict):
        """Log final processing statistics"""
        logger.info("=" * 60)
        logger.info("POPULATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total games processed: {stats['total_games']}")
        logger.info(f"Successful: {stats['successful_games']}")
        logger.info(f"Failed: {stats['failed_games']}")
        logger.info(f"Duration: {stats['duration']}")
        
        if stats['failed_game_ids']:
            logger.warning(f"Failed game IDs: {stats['failed_game_ids']}")
        
        logger.info("\nRecords inserted by table:")
        for table, count in stats['table_counts'].items():
            logger.info(f"  {table}: {count}")
    
    def clear_all_tables(self) -> bool:
        """
        Clear all populated tables and reset sequences (hard reset).
        
        Returns:
            True if successful
        """
        logger.info("Starting hard reset - clearing all populated tables...")
        
        # Define tables in dependency order (children first, parents last)
        tables_to_clear = [
            'boxscore',
            'play', 
            'person_game',
            'team_game',
            'game',
            'person',
            'team',
            'arena'
        ]
        
        with self.Session() as session:
            try:
                # Clear tables in dependency order
                for table_name in tables_to_clear:
                    logger.info(f"Clearing table: {table_name}")
                    session.execute(text(f"DELETE FROM {table_name}"))
                
                # Reset sequences for tables with auto-incrementing IDs
                sequences_to_reset = [
                    ('arena', 'arena_arena_id_seq'),
                    ('team', 'team_id_seq'), 
                    ('person', 'person_person_id_seq'),
                    ('game', 'game_game_id_seq'),
                    ('team_game', 'team_game_team_game_id_seq'),
                    ('person_game', 'person_game_person_game_id_seq'),
                    ('play', 'play_play_id_seq'),
                    ('boxscore', 'boxscore_boxscore_id_seq')
                ]
                
                for table_name, seq_name in sequences_to_reset:
                    logger.info(f"Resetting sequence: {seq_name}")
                    session.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH 1"))
                
                session.commit()
                logger.info("✅ All tables cleared and sequences reset successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error during table clearing: {e}")
                session.rollback()
                raise
    
    def validate_foreign_keys(self) -> bool:
        """
        Validate foreign key integrity after population.
        
        Returns:
            True if all foreign keys are valid
        """
        logger.info("Validating foreign key integrity...")
        
        validation_queries = [
            # Game -> Arena
            """
            SELECT COUNT(*) FROM game g 
            LEFT JOIN arena a ON g.arena_id = a.arena_id 
            WHERE a.arena_id IS NULL
            """,
            # Play -> Game
            """
            SELECT COUNT(*) FROM play p 
            LEFT JOIN game g ON p.game_id = g.game_id 
            WHERE g.game_id IS NULL
            """,
            # Play -> Person (nullable)
            """
            SELECT COUNT(*) FROM play p 
            LEFT JOIN person pe ON p.person_id = pe.person_id 
            WHERE p.person_id IS NOT NULL AND pe.person_id IS NULL
            """,
            # Play -> Team
            """
            SELECT COUNT(*) FROM play p 
            LEFT JOIN team t ON p.team_id = t.id 
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
            """,
            # Boxscore -> Game
            """
            SELECT COUNT(*) FROM boxscore b 
            LEFT JOIN game g ON b.game_id = g.game_id 
            WHERE g.game_id IS NULL
            """,
            # Boxscore -> Person (nullable)
            """
            SELECT COUNT(*) FROM boxscore b 
            LEFT JOIN person pe ON b.person_id = pe.person_id 
            WHERE b.person_id IS NOT NULL AND pe.person_id IS NULL
            """,
            # Boxscore -> Team
            """
            SELECT COUNT(*) FROM boxscore b 
            LEFT JOIN team t ON b.team_id = t.id 
            WHERE b.team_id IS NOT NULL AND t.id IS NULL
            """
        ]
        
        validation_names = [
            "Game -> Arena",
            "Play -> Game", 
            "Play -> Person",
            "Play -> Team",
            "Boxscore -> Game",
            "Boxscore -> Person", 
            "Boxscore -> Team"
        ]
        
        all_valid = True
        
        with self.Session() as session:
            for query, name in zip(validation_queries, validation_names):
                result = session.execute(text(query)).scalar()
                if result > 0:
                    logger.error(f"Foreign key violation: {name} - {result} orphaned records")
                    all_valid = False
                else:
                    logger.info(f"✓ {name} - No violations")
        
        return all_valid


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Populate WNBA game tables from raw JSON data"
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--all', action='store_true',
        help='Process all games in raw_game_data table'
    )
    mode_group.add_argument(
        '--games', type=int, nargs='+',
        help='Process specific game IDs'
    )
    mode_group.add_argument(
        '--seasons', type=int, nargs='+',
        help='Process games from specific seasons'
    )
    
    # Options
    parser.add_argument(
        '--limit', type=int,
        help='Limit number of games to process'
    )
    parser.add_argument(
        '--resume-from', type=int,
        help='Resume processing from this game ID (only with --all)'
    )
    parser.add_argument(
        '--validate', action='store_true',
        help='Validate foreign key integrity after population'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be processed without actual processing'
    )
    parser.add_argument(
        '--override', action='store_true',
        help='Override existing data - clear and repopulate games that already exist'
    )
    parser.add_argument(
        '--clear-tables', action='store_true',
        help='Clear all populated tables and reset sequences before processing (hard reset)'
    )
    
    args = parser.parse_args()
    
    # Validation
    if args.resume_from and not args.all:
        parser.error("--resume-from can only be used with --all")
    
    try:
        populator = GameTablePopulator()
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual processing will occur")
            return
        
        # Clear all tables if requested (hard reset)
        if args.clear_tables:
            logger.info("🗑️  HARD RESET requested - clearing all tables and resetting sequences")
            populator.clear_all_tables()
            logger.info("Hard reset complete. Starting fresh population...")
        
        # Execute population based on mode
        if args.all:
            stats = populator.populate_all_games(
                limit=args.limit,
                resume_from_game_id=args.resume_from,
                override_existing=args.override
            )
        elif args.games:
            stats = populator.populate_specific_games(args.games, override_existing=args.override)
        elif args.seasons:
            stats = populator.populate_games_by_season(
                args.seasons,
                limit=args.limit,
                override_existing=args.override
            )
        
        # Validate foreign keys if requested
        if args.validate:
            logger.info("\nRunning foreign key validation...")
            is_valid = populator.validate_foreign_keys()
            if not is_valid:
                logger.error("Foreign key validation failed!")
                sys.exit(1)
            else:
                logger.info("✓ Foreign key validation passed!")
        
        # Exit with error code if any games failed
        if stats['failed_games'] > 0:
            logger.error(f"Population completed with {stats['failed_games']} failed games")
            sys.exit(1)
        else:
            logger.info("Population completed successfully!")
    
    except Exception as e:
        logger.error(f"Population failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()