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

from ..database.database import get_db_engine
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
        self.engine = get_db_engine()
        self.Session = sessionmaker(bind=self.engine)
    
    def populate_all_games(self, limit: Optional[int] = None, 
                          resume_from_game_id: Optional[int] = None) -> dict:
        """
        Populate all games from raw_game_data table.
        
        Args:
            limit: Maximum number of games to process
            resume_from_game_id: Resume processing from this game ID
            
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
            
            return self._process_games(games)
    
    def populate_specific_games(self, game_ids: List[int]) -> dict:
        """
        Populate specific games by ID.
        
        Args:
            game_ids: List of game IDs to process
            
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
            return self._process_games(games)
    
    def populate_games_by_season(self, seasons: List[int], 
                                limit: Optional[int] = None) -> dict:
        """
        Populate games by season(s).
        
        Args:
            seasons: List of seasons to process (e.g., [2024])
            limit: Maximum number of games per season
            
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
            
            return self._process_games(games)
    
    def _process_games(self, games: List[RawGameData]) -> dict:
        """
        Process a list of games with transaction management.
        
        Args:
            games: List of RawGameData objects to process
            
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
    
    args = parser.parse_args()
    
    # Validation
    if args.resume_from and not args.all:
        parser.error("--resume-from can only be used with --all")
    
    try:
        populator = GameTablePopulator()
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual processing will occur")
            return
        
        # Execute population based on mode
        if args.all:
            stats = populator.populate_all_games(
                limit=args.limit,
                resume_from_game_id=args.resume_from
            )
        elif args.games:
            stats = populator.populate_specific_games(args.games)
        elif args.seasons:
            stats = populator.populate_games_by_season(
                args.seasons,
                limit=args.limit
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