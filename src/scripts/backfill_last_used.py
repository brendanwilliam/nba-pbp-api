#!/usr/bin/env python3
"""
Backfill last_used timestamps for existing entities.

This script finds the actual latest game date where each Arena, Team, and Person appears
and sets their last_used timestamp accordingly. This ensures temporal accuracy for all entities.
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


class LastUsedBackfiller:
    """Handles backfilling last_used timestamps for entities"""
    
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
        """Backfill last_used for all arenas"""
        logger.info("Processing arenas...")
        
        # Get all arenas
        all_arenas = session.query(Arena).all()
        logger.info(f"Found {len(all_arenas)} arenas to process")
        
        for arena in all_arenas:
            # Find latest game using this arena
            latest_game = session.query(Game).filter(
                Game.arena_internal_id == arena.id
            ).order_by(Game.game_et.desc()).first()
            
            if latest_game and latest_game.game_et:
                old_last_used = arena.last_used
                new_last_used = latest_game.game_et
                
                if old_last_used != new_last_used:
                    if not self.dry_run:
                        arena.last_used = new_last_used
                        logger.debug(f"Updated {arena.arena_name} last_used: {old_last_used} → {new_last_used}")
                    else:
                        logger.info(f"[DRY RUN] Would update {arena.arena_name} last_used: {old_last_used} → {new_last_used}")
                    self.stats['arenas_updated'] += 1
                else:
                    logger.debug(f"Arena {arena.arena_name} already has correct last_used: {old_last_used}")
            else:
                logger.warning(f"No games found for arena {arena.arena_name} (ID: {arena.id})")
                self.stats['skipped_arenas'] += 1
    
    def backfill_teams(self, session) -> None:
        """Backfill last_used for all teams"""
        logger.info("Processing teams...")
        
        # Get all teams
        all_teams = session.query(Team).all()
        logger.info(f"Found {len(all_teams)} teams to process")
        
        for team in all_teams:
            # Find latest game involving this team via TeamGame junction
            latest_game = session.query(Game).join(
                TeamGame, Game.game_id == TeamGame.game_id
            ).filter(
                TeamGame.team_id == team.id
            ).order_by(Game.game_et.desc()).first()
            
            if latest_game and latest_game.game_et:
                old_last_used = team.last_used
                new_last_used = latest_game.game_et
                
                if old_last_used != new_last_used:
                    if not self.dry_run:
                        team.last_used = new_last_used
                        logger.debug(f"Updated {team.team_city} {team.team_name} last_used: {old_last_used} → {new_last_used}")
                    else:
                        logger.info(f"[DRY RUN] Would update {team.team_city} {team.team_name} last_used: {old_last_used} → {new_last_used}")
                    self.stats['teams_updated'] += 1
                else:
                    logger.debug(f"Team {team.team_city} {team.team_name} already has correct last_used: {old_last_used}")
            else:
                logger.warning(f"No games found for team {team.team_city} {team.team_name} (ID: {team.id})")
                self.stats['skipped_teams'] += 1
    
    def backfill_persons(self, session) -> None:
        """Backfill last_used for all persons"""
        logger.info("Processing persons...")
        
        # Get all persons
        all_persons = session.query(Person).all()
        logger.info(f"Found {len(all_persons)} persons to process")
        
        processed_count = 0
        updates_shown = 0
        
        for person in all_persons:
            # Find latest game involving this person via PersonGame junction
            latest_game = session.query(Game).join(
                PersonGame, Game.game_id == PersonGame.game_id
            ).filter(
                PersonGame.person_internal_id == person.id
            ).order_by(Game.game_et.desc()).first()
            
            if latest_game and latest_game.game_et:
                old_last_used = person.last_used
                new_last_used = latest_game.game_et
                
                if old_last_used != new_last_used:
                    if not self.dry_run:
                        person.last_used = new_last_used
                        logger.debug(f"Updated {person.person_name} last_used: {old_last_used} → {new_last_used}")
                    else:
                        if updates_shown < 10:  # Show first 10 in dry run
                            logger.info(f"[DRY RUN] Would update {person.person_name} last_used: {old_last_used} → {new_last_used}")
                            updates_shown += 1
                        elif updates_shown == 10:
                            logger.info("[DRY RUN] ... (showing first 10 person updates only)")
                            updates_shown += 1
                    self.stats['persons_updated'] += 1
                else:
                    logger.debug(f"Person {person.person_name} already has correct last_used: {old_last_used}")
            else:
                logger.warning(f"No games found for person {person.person_name} (ID: {person.id})")
                self.stats['skipped_persons'] += 1
            
            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count}/{len(all_persons)} persons...")
    
    def run_backfill(self) -> Dict[str, Any]:
        """Run the complete backfill process"""
        logger.info(f"Starting last_used backfill {'(DRY RUN)' if self.dry_run else ''}")
        
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
    parser = argparse.ArgumentParser(description="Backfill last_used timestamps for existing entities")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without modifying database')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the backfill
    backfiller = LastUsedBackfiller(dry_run=args.dry_run)
    result = backfiller.run_backfill()
    
    # Print summary
    stats = result['stats']
    print("\n" + "="*60)
    print("LAST_USED BACKFILL SUMMARY")
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