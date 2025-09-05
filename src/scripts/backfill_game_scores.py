#!/usr/bin/env python3
"""
Backfill script to populate final_home_score, final_away_score, and winner columns for existing game records.

This script extracts final scores from the raw game JSON data and determines the winner.

Usage:
    python -m src.scripts.backfill_game_scores [--dry-run] [--verbose] [--batch-size 100]
"""

import argparse
import logging
import sys
from typing import List, Tuple, Optional

from src.database.services import DatabaseService
from src.database.models import Game, RawGameData


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def extract_final_scores_and_winner(game_data: dict) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Extract final scores and winner from raw game JSON data.
    
    Args:
        game_data: Raw game JSON data
        
    Returns:
        tuple: (final_home_score, final_away_score, winner_team_id)
               winner_team_id is the team_id of the winning team
    """
    try:
        boxscore = game_data.get('boxscore', {})
        
        # Extract final scores and team IDs
        home_score = boxscore.get('homeTeam', {}).get('score')
        away_score = boxscore.get('awayTeam', {}).get('score')
        home_team_id = boxscore.get('homeTeam', {}).get('teamId')
        away_team_id = boxscore.get('awayTeam', {}).get('teamId')
        
        # Determine winner
        winner = None
        if home_score is not None and away_score is not None:
            if home_score > away_score:
                winner = home_team_id
            elif away_score > home_score:
                winner = away_team_id
            # Note: ties are theoretically possible in basketball but extremely rare
            # We'll leave winner as None for ties
        
        return home_score, away_score, winner
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Error extracting scores from game data: {str(e)}")
        return None, None, None


def backfill_game_scores(dry_run: bool = False, verbose: bool = False, batch_size: int = 100) -> Tuple[int, int, List[str]]:
    """
    Backfill final_home_score, final_away_score, and winner columns for existing game records.
    
    Args:
        dry_run: If True, don't actually update the database
        verbose: Enable verbose logging
        batch_size: Number of records to process in each batch
        
    Returns:
        tuple: (total_games, updated_games, errors)
    """
    logger = logging.getLogger(__name__)
    
    with DatabaseService() as db:
        session = db.get_session()
        
        # Get all games that need to be updated (where final scores or winner is None)
        # Join with raw_game_data to get the JSON data
        games_query = session.query(Game, RawGameData).join(
            RawGameData, Game.game_id == RawGameData.game_id
        ).filter(
            (Game.final_home_score.is_(None)) | 
            (Game.final_away_score.is_(None)) | 
            (Game.winner.is_(None))
        )
        
        games_to_update = games_query.all()
        total_games = len(games_to_update)
        updated_games = 0
        errors = []
        
        logger.info(f"Found {total_games} games to update")
        
        if dry_run:
            logger.info("DRY RUN MODE - No database changes will be made")
        
        # Process games in batches
        for i in range(0, total_games, batch_size):
            batch = games_to_update[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} games)")
            
            for game_record, raw_data in batch:
                try:
                    # Extract scores and winner from raw JSON data
                    final_home_score, final_away_score, winner = extract_final_scores_and_winner(
                        raw_data.game_data
                    )
                    
                    # Update game record if data was successfully extracted
                    updated = False
                    
                    if game_record.final_home_score is None and final_home_score is not None:
                        game_record.final_home_score = final_home_score
                        updated = True
                        
                    if game_record.final_away_score is None and final_away_score is not None:
                        game_record.final_away_score = final_away_score
                        updated = True
                        
                    if game_record.winner is None and winner is not None:
                        game_record.winner = winner
                        updated = True
                    
                    if updated:
                        updated_games += 1
                        if verbose:
                            logger.debug(
                                f"Updated game {game_record.game_id}: "
                                f"home={final_home_score}, away={final_away_score}, winner={winner}"
                            )
                    
                except Exception as e:
                    error_msg = f"Error processing game {game_record.game_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Commit batch changes
            if not dry_run:
                try:
                    session.commit()
                    logger.info(f"Committed batch {i // batch_size + 1}")
                except Exception as e:
                    session.rollback()
                    error_msg = f"Error committing batch {i // batch_size + 1}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"Backfill completed: {updated_games}/{total_games} games updated")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during processing")
        
        return total_games, updated_games, errors


def main():
    """Main entry point for the backfill script"""
    parser = argparse.ArgumentParser(
        description="Backfill final scores and winner in game table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m src.scripts.backfill_game_scores                    # Run the backfill
    python -m src.scripts.backfill_game_scores --dry-run         # Preview changes
    python -m src.scripts.backfill_game_scores --verbose         # Detailed logging
    python -m src.scripts.backfill_game_scores --batch-size 50   # Smaller batches
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating database'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of games to process in each batch (default: 100)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        total, updated, errors = backfill_game_scores(
            dry_run=args.dry_run,
            verbose=args.verbose,
            batch_size=args.batch_size
        )
        
        print(f"\nBackfill Summary:")
        print(f"  Total games: {total}")
        print(f"  Updated games: {updated}")
        print(f"  Errors: {len(errors)}")
        
        if errors:
            print(f"\nFirst few errors:")
            for error in errors[:5]:
                print(f"  - {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
        if args.dry_run:
            print("\nDRY RUN MODE - No changes were made to the database")
        
        return 0 if len(errors) == 0 else 1
        
    except Exception as e:
        logger.error(f"Backfill script failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())