#!/usr/bin/env python3
"""
Backfill script to populate season and game_type columns for existing games.

This script analyzes existing game_id values in the game table and populates
the new season and game_type columns based on the game ID format.

Usage:
    python -m src.scripts.backfill_game_metadata [--dry-run] [--verbose]
"""

import argparse
import logging
import sys
from typing import List, Tuple

from src.database.services import DatabaseService
from src.database.models import Game
from src.database.game_utils import parse_game_id


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def backfill_game_metadata(dry_run: bool = False, verbose: bool = False) -> Tuple[int, int, List[str]]:
    """
    Backfill season and game_type columns for existing games.
    
    Args:
        dry_run: If True, don't actually update the database
        verbose: Enable verbose logging
        
    Returns:
        tuple: (total_games, updated_games, errors)
    """
    logger = logging.getLogger(__name__)
    
    with DatabaseService() as db:
        session = db.get_session()
        
        # Get all games that need to be updated (where season or game_type is None)
        games_to_update = session.query(Game).filter(
            (Game.season.is_(None)) | (Game.game_type.is_(None))
        ).all()
        
        total_games = len(games_to_update)
        updated_games = 0
        errors = []
        
        logger.info(f"Found {total_games} games that need metadata updates")
        
        if dry_run:
            logger.info("DRY RUN MODE - No actual updates will be made")
        
        for game in games_to_update:
            try:
                # Parse the game ID to extract metadata
                metadata = parse_game_id(game.game_id)
                season = metadata['season']
                game_type = metadata['game_type']
                
                if season is None or game_type is None:
                    error_msg = f"Could not parse game_id {game.game_id}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Update the game record
                old_season = game.season
                old_game_type = game.game_type
                
                if not dry_run:
                    game.season = season
                    game.game_type = game_type
                
                updated_games += 1
                
                if verbose:
                    logger.debug(
                        f"Game {game.game_id}: season {old_season} -> {season}, "
                        f"game_type {old_game_type} -> {game_type}"
                    )
                
                # Commit periodically to avoid large transactions
                if not dry_run and updated_games % 1000 == 0:
                    session.commit()
                    logger.info(f"Committed {updated_games} updates...")
                    
            except Exception as e:
                error_msg = f"Error processing game {game.game_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Final commit
        if not dry_run and updated_games > 0:
            session.commit()
            logger.info(f"Final commit of {updated_games} updates")
    
    return total_games, updated_games, errors


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Backfill game metadata (season and game_type)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be updated without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting game metadata backfill...")
        
        total_games, updated_games, errors = backfill_game_metadata(
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        logger.info("=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total games examined: {total_games}")
        logger.info(f"Games updated: {updated_games}")
        logger.info(f"Errors encountered: {len(errors)}")
        
        if errors:
            logger.warning("Errors encountered:")
            for error in errors:
                logger.warning(f"  {error}")
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual changes were made")
        else:
            logger.info("Backfill completed successfully!")
            
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error during backfill: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()