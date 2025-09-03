#!/usr/bin/env python3
"""
Backfill first_used timestamps for existing entities.

This script finds the earliest game date where each Arena, Team, and Person appears
and sets their first_used timestamp accordingly. This addresses entities that were
inserted before the temporal tracking system was implemented.
"""

import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import func, and_

from src.database.services import DatabaseService
from src.database.models import Arena, Team, Person, Game, TeamGame, PersonGame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirstUsedBackfiller:
    """Handles backfilling first_used timestamps for entities"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'arenas_updated': 0,
            'teams_updated': 0,
            'persons_updated': 0,
            'skipped_arenas': 0,
            'skipped_teams': 0,
            'skipped_persons': 0
        }
    
    def backfill_arenas(self, session) -> None:
        """Backfill first_used for arenas that have NULL first_used"""
        logger.info("Processing arenas...")
        
        # Find arenas with NULL first_used
        null_arenas = session.query(Arena).filter(Arena.first_used.is_(None)).all()
        logger.info(f"Found {len(null_arenas)} arenas with NULL first_used")
        
        for arena in null_arenas:
            # Find earliest game using this arena
            earliest_game = session.query(Game).filter(
                Game.arena_internal_id == arena.id
            ).order_by(Game.game_et.asc()).first()
            
            if earliest_game and earliest_game.game_et:
                if not self.dry_run:
                    arena.first_used = earliest_game.game_et
                    logger.debug(f"Set {arena.arena_name} first_used to {earliest_game.game_et}")
                else:
                    logger.info(f"[DRY RUN] Would set {arena.arena_name} first_used to {earliest_game.game_et}")
                self.stats['arenas_updated'] += 1
            else:
                logger.warning(f"No games found for arena {arena.arena_name} (ID: {arena.id})")
                self.stats['skipped_arenas'] += 1
    
    def backfill_teams(self, session) -> None:
        """Backfill first_used for teams that have NULL first_used"""
        logger.info("Processing teams...")
        
        # Find teams with NULL first_used
        null_teams = session.query(Team).filter(Team.first_used.is_(None)).all()
        logger.info(f"Found {len(null_teams)} teams with NULL first_used")
        
        for team in null_teams:
            # Find earliest game involving this team via TeamGame junction
            # Find earliest game involving this team via TeamGame junction
            # Use team.id (internal PK) since that's what TeamGame.team_id references
            earliest_game = session.query(Game).join(
                TeamGame, Game.game_id == TeamGame.game_id
            ).filter(
                TeamGame.team_id == team.id
            ).order_by(Game.game_et.asc()).first()
            
            if earliest_game and earliest_game.game_et:
                if not self.dry_run:
                    team.first_used = earliest_game.game_et
                    logger.debug(f"Set {team.team_city} {team.team_name} first_used to {earliest_game.game_et}")
                else:
                    logger.info(f"[DRY RUN] Would set {team.team_city} {team.team_name} first_used to {earliest_game.game_et}")
                self.stats['teams_updated'] += 1
            else:
                logger.warning(f"No games found for team {team.team_city} {team.team_name} (ID: {team.id})")
                self.stats['skipped_teams'] += 1
    
    def backfill_persons(self, session) -> None:
        """Backfill first_used for persons that have NULL first_used"""
        logger.info("Processing persons...")
        
        # Find persons with NULL first_used
        null_persons = session.query(Person).filter(Person.first_used.is_(None)).all()
        logger.info(f"Found {len(null_persons)} persons with NULL first_used")
        
        processed_count = 0
        for person in null_persons:
            # Find earliest game involving this person via PersonGame junction
            earliest_game = session.query(Game).join(
                PersonGame, Game.game_id == PersonGame.game_id
            ).filter(
                PersonGame.person_internal_id == person.id
            ).order_by(Game.game_et.asc()).first()
            
            if earliest_game and earliest_game.game_et:
                if not self.dry_run:
                    person.first_used = earliest_game.game_et
                    logger.debug(f"Set {person.person_name} first_used to {earliest_game.game_et}")
                else:
                    if processed_count < 5:  # Limit dry run output
                        logger.info(f"[DRY RUN] Would set {person.person_name} first_used to {earliest_game.game_et}")
                self.stats['persons_updated'] += 1
            else:
                logger.warning(f"No games found for person {person.person_name} (ID: {person.id})")
                self.stats['skipped_persons'] += 1
            
            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count}/{len(null_persons)} persons...")
    
    def run_backfill(self) -> Dict[str, Any]:
        """Run the complete backfill process"""
        logger.info(f"Starting first_used backfill {'(DRY RUN)' if self.dry_run else ''}")
        
        with DatabaseService() as db:
            try:
                # Process each entity type
                self.backfill_arenas(db._session)
                self.backfill_teams(db._session)
                self.backfill_persons(db._session)
                
                if not self.dry_run:
                    db._session.commit()
                    logger.info("Changes committed to database")
                else:
                    logger.info("DRY RUN - No changes made to database")
                
                return {
                    'success': True,
                    'stats': self.stats,
                    'dry_run': self.dry_run
                }
                
            except Exception as e:
                logger.error(f"Error during backfill: {e}")
                if not self.dry_run:
                    db._session.rollback()
                    logger.info("Database changes rolled back")
                raise


def main():
    parser = argparse.ArgumentParser(description="Backfill first_used timestamps for existing entities")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without modifying database')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the backfill
    backfiller = FirstUsedBackfiller(dry_run=args.dry_run)
    result = backfiller.run_backfill()
    
    # Print summary
    stats = result['stats']
    print("\n" + "="*60)
    print("BACKFILL SUMMARY")
    print("="*60)
    print(f"Mode: {'DRY RUN' if result['dry_run'] else 'LIVE UPDATE'}")
    print(f"Arenas updated: {stats['arenas_updated']}")
    print(f"Arenas skipped: {stats['skipped_arenas']}")
    print(f"Teams updated: {stats['teams_updated']}")
    print(f"Teams skipped: {stats['skipped_teams']}")
    print(f"Persons updated: {stats['persons_updated']}")
    print(f"Persons skipped: {stats['skipped_persons']}")
    print(f"Total entities updated: {stats['arenas_updated'] + stats['teams_updated'] + stats['persons_updated']}")
    print("="*60)


if __name__ == "__main__":
    main()