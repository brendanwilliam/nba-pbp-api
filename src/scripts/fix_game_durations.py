#!/usr/bin/env python3
"""
Fix invalid game duration formats in the database.

This script finds and corrects invalid duration formats like '1:60' -> '2:00',
'2:60' -> '3:00', etc. It also handles edge cases like '0:60' -> '1:00'.
"""

import argparse
import logging
import re
from typing import Dict, Any, List, Optional

from src.database.services import DatabaseService
from src.database.models import Game

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameDurationFixer:
    """Handles fixing invalid game duration formats"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'games_updated': 0,
            'games_skipped': 0,
            'duration_mappings': {}
        }
    
    @staticmethod
    def normalize_duration(duration: str) -> Optional[str]:
        """
        Normalize game duration format.
        
        Examples:
        - '1:60' -> '2:00'
        - '2:60' -> '3:00'  
        - '0:60' -> '1:00'
        - '1:75' -> '2:15'
        - '1:45' -> '1:45' (unchanged)
        
        Args:
            duration: Original duration string
            
        Returns:
            Normalized duration string, or None if invalid format
        """
        if not duration:
            return None
            
        # Match format like 'H:MM' or 'H:M'
        match = re.match(r'^(\d+):(\d+)$', duration.strip())
        if not match:
            return None
            
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        # Normalize minutes >= 60
        if minutes >= 60:
            additional_hours = minutes // 60
            remaining_minutes = minutes % 60
            hours += additional_hours
            minutes = remaining_minutes
        
        # Format as H:MM
        normalized = f"{hours}:{minutes:02d}"
        return normalized
    
    def find_invalid_durations(self, session) -> List[Dict[str, Any]]:
        """Find all games with invalid duration formats"""
        # Look for durations with minutes >= 60
        games = session.query(Game).filter(
            Game.game_duration.op('~')(r'\d+:[6-9]\d|\d+:\d{3,}')
        ).all()
        
        invalid_games = []
        for game in games:
            if game.game_duration:
                normalized = self.normalize_duration(game.game_duration)
                if normalized and normalized != game.game_duration:
                    invalid_games.append({
                        'game': game,
                        'old_duration': game.game_duration,
                        'new_duration': normalized
                    })
        
        return invalid_games
    
    def fix_durations(self, session) -> None:
        """Fix all invalid game durations"""
        logger.info("Finding games with invalid duration formats...")
        
        invalid_games = self.find_invalid_durations(session)
        logger.info(f"Found {len(invalid_games)} games with invalid durations")
        
        if not invalid_games:
            logger.info("No invalid durations found")
            return
        
        # Group by transformation for reporting
        transformations = {}
        for game_info in invalid_games:
            old = game_info['old_duration']
            new = game_info['new_duration']
            
            if old not in transformations:
                transformations[old] = {'new': new, 'count': 0, 'games': []}
            transformations[old]['count'] += 1
            transformations[old]['games'].append(game_info['game'].game_id)
        
        # Show transformations
        logger.info("Duration transformations to be applied:")
        for old, info in transformations.items():
            logger.info(f"  '{old}' -> '{info['new']}': {info['count']} games")
            if self.dry_run:
                sample_games = info['games'][:3]
                logger.info(f"    Sample games: {sample_games}")
        
        # Apply fixes
        for game_info in invalid_games:
            game = game_info['game']
            old_duration = game_info['old_duration']
            new_duration = game_info['new_duration']
            
            if not self.dry_run:
                game.game_duration = new_duration
                logger.debug(f"Updated game {game.game_id}: '{old_duration}' -> '{new_duration}'")
            
            self.stats['games_updated'] += 1
            
            # Track transformations for summary
            if old_duration not in self.stats['duration_mappings']:
                self.stats['duration_mappings'][old_duration] = {
                    'new': new_duration,
                    'count': 0
                }
            self.stats['duration_mappings'][old_duration]['count'] += 1
    
    def run_fix(self) -> Dict[str, Any]:
        """Run the complete duration fix process"""
        logger.info(f"Starting game duration fix {'(DRY RUN)' if self.dry_run else ''}")
        
        with DatabaseService() as db:
            try:
                self.fix_durations(db._session)
                
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
                logger.error(f"Error during duration fix: {e}")
                if not self.dry_run:
                    db._session.rollback()
                    logger.info("Database changes rolled back")
                raise


def main():
    parser = argparse.ArgumentParser(description="Fix invalid game duration formats")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without modifying database')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the fix
    fixer = GameDurationFixer(dry_run=args.dry_run)
    result = fixer.run_fix()
    
    # Print summary
    stats = result['stats']
    print("\n" + "="*60)
    print("GAME DURATION FIX SUMMARY")
    print("="*60)
    print(f"Mode: {'DRY RUN' if result['dry_run'] else 'LIVE UPDATE'}")
    print(f"Games updated: {stats['games_updated']}")
    print(f"Games skipped: {stats['games_skipped']}")
    
    if stats['duration_mappings']:
        print("\nDuration transformations applied:")
        for old, info in stats['duration_mappings'].items():
            print(f"  '{old}' -> '{info['new']}': {info['count']} games")
    
    print("="*60)


if __name__ == "__main__":
    main()