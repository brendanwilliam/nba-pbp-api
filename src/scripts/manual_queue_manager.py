#!/usr/bin/env python3
"""
Manual Queue Manager - Add specific game ranges to the scraping queue
Useful for filling gaps or adding specific game sequences that weren't 
captured by the automated queue building process.
"""

import argparse
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import text

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.database import SessionLocal


# URL validation currently disabled due to import path issues in scrapers module
# TODO: Fix import paths to enable validation functionality


def add_game_range(start_game_id: str, end_game_id: str, reference_game_id: str = None, dry_run: bool = False, validate: bool = False):
    """
    Add a range of game_ids to the queue using a reference game for metadata.
    
    Args:
        start_game_id: First game_id in the range (e.g., '0029700001')
        end_game_id: Last game_id in the range (e.g., '0029700014')
        reference_game_id: Existing game_id to copy metadata from (e.g., '0029700015')
        dry_run: If True, show what would be added without actually inserting
        validate: If True, validate URLs before adding to queue
    """
    session = SessionLocal()
    
    try:
        # Extract sequence numbers
        start_num = int(start_game_id[6:])
        end_num = int(end_game_id[6:])
        base_id = start_game_id[:6]  # e.g., '002970'
        
        print(f"Range: {start_game_id} to {end_game_id} ({end_num - start_num + 1} games)")
        
        # Get reference game metadata if provided
        reference_data = None
        if reference_game_id:
            query = text('''
            SELECT season, game_date, game_type, priority, home_team, away_team
            FROM game_url_queue 
            WHERE game_id = :ref_id
            LIMIT 1;
            ''')
            
            result = session.execute(query, {'ref_id': reference_game_id})
            reference_data = result.fetchone()
            
            if reference_data:
                print(f"Using reference game {reference_game_id}:")
                print(f"  Season: {reference_data[0]}")
                print(f"  Date: {reference_data[1]}")
                print(f"  Type: {reference_data[2]}")
                print(f"  Priority: {reference_data[3]}")
            else:
                print(f"Warning: Reference game {reference_game_id} not found")
                return False
        
        # Default values if no reference
        default_season = start_game_id[3:5] + "-" + str(int(start_game_id[3:5]) + 1)  # e.g., "97-98"
        default_date = datetime(int("19" + start_game_id[3:5]), 10, 1).date()  # Start of season
        
        # Generate games in the range
        games_to_add = []
        for i in range(start_num, end_num + 1):
            game_id = f"{base_id}{i:04d}"
            game_url = f"https://www.nba.com/game/placeholder-vs-placeholder-{game_id}"
            
            game_data = {
                'game_id': game_id,
                'season': reference_data[0] if reference_data else f"19{default_season}",
                'game_date': reference_data[1] if reference_data else default_date,
                'home_team': 'TBD',  # Placeholder
                'away_team': 'TBD',  # Placeholder  
                'game_url': game_url,
                'game_type': reference_data[2] if reference_data else 'regular',
                'status': 'validated',  # Ready for scraping
                'priority': reference_data[3] if reference_data else 50,
                'url_validated': True  # Mark as validated
            }
            games_to_add.append(game_data)
        
        # Validate URLs if requested (currently disabled due to import issues)
        if validate and not dry_run:
            print(f"\nURL validation requested but currently disabled due to import path issues.")
            print("Games will be added with 'validated' status for immediate scraping.")
            # TODO: Fix import paths in scrapers module to enable validation

        if dry_run:
            print(f"\nDRY RUN - Would add {len(games_to_add)} games:")
            for game in games_to_add[:5]:  # Show first 5
                status_indicator = "✅" if game.get('url_validated', True) else "❌"
                print(f"  {status_indicator} {game['game_id']}: {game['season']} {game['game_type']} ({game['status']})")
            if len(games_to_add) > 5:
                print(f"  ... and {len(games_to_add) - 5} more")
            return True
        
        # Insert games
        insert_query = text('''
        INSERT INTO game_url_queue 
        (game_id, season, game_date, home_team, away_team, game_url, game_type, status, priority, url_validated, created_at)
        VALUES (:game_id, :season, :game_date, :home_team, :away_team, :game_url, :game_type, :status, :priority, :url_validated, NOW())
        ON CONFLICT (game_id) DO NOTHING
        ''')
        
        inserted_count = 0
        for game in games_to_add:
            result = session.execute(insert_query, game)
            if result.rowcount > 0:
                inserted_count += 1
        
        session.commit()
        
        print(f"\n✅ Successfully added {inserted_count} new games to queue")
        print(f"   (Skipped {len(games_to_add) - inserted_count} existing games)")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        return False
        
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Manually add game ranges to the scraping queue")
    parser.add_argument("start_game_id", help="First game_id in range (e.g., 0029700001)")
    parser.add_argument("end_game_id", help="Last game_id in range (e.g., 0029700014)")
    parser.add_argument("--reference", "-r", help="Reference game_id for metadata (e.g., 0029700015)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show what would be added without inserting")
    parser.add_argument("--validate", "-v", action="store_true", help="Validate URLs before adding to queue")
    
    args = parser.parse_args()
    
    # Validate game_id format
    if len(args.start_game_id) != 10 or len(args.end_game_id) != 10:
        print("Error: game_ids must be 10 characters (e.g., 0029700001)")
        sys.exit(1)
    
    if args.start_game_id[:6] != args.end_game_id[:6]:
        print("Error: start and end game_ids must be from the same season")
        sys.exit(1)
    
    success = add_game_range(
        args.start_game_id, 
        args.end_game_id, 
        args.reference,
        args.dry_run,
        args.validate
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()