"""
Demo script for game URL queue building using known game data.
"""

import asyncio
import logging
from datetime import date
from sqlalchemy import text
from ..core.database import get_db
from ..scrapers.game_url_generator import GameURLInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_queue_population():
    """Demonstrate queue population with sample game data."""
    logger.info("Demo: Populating queue with sample games")
    
    # Create sample games based on test data we know exists
    sample_games = [
        GameURLInfo(
            game_id="0022400306",
            season="2024-25",
            game_date=date(2024, 12, 1),
            home_team="MEM",
            away_team="IND",
            game_url="https://www.nba.com/game/ind-vs-mem-0022400306",
            game_type="regular",
            priority=50
        ),
        GameURLInfo(
            game_id="0022400308",
            season="2024-25", 
            game_date=date(2024, 12, 2),
            home_team="NYK",
            away_team="NOP",
            game_url="https://www.nba.com/game/nop-vs-nyk-0022400308",
            game_type="regular",
            priority=50
        ),
        GameURLInfo(
            game_id="0021900001",
            season="2019-20",
            game_date=date(2019, 10, 22),
            home_team="LAL",
            away_team="LAC",
            game_url="https://www.nba.com/game/lac-vs-lal-0021900001",
            game_type="regular",
            priority=75
        ),
        GameURLInfo(
            game_id="0041900401",
            season="2019-20",
            game_date=date(2020, 9, 30),
            home_team="MIA",
            away_team="LAL",
            game_url="https://www.nba.com/game/lal-vs-mia-0041900401",
            game_type="playoff",
            priority=25
        ),
    ]
    
    db = next(get_db())
    
    try:
        # Insert sample games
        logger.info(f"Inserting {len(sample_games)} sample games...")
        
        stats = {'total': len(sample_games), 'inserted': 0, 'duplicates': 0, 'errors': 0}
        
        for game in sample_games:
            try:
                game_data = game.to_dict()
                
                insert_query = text("""
                    INSERT INTO game_url_queue 
                    (game_id, season, game_date, home_team, away_team, game_url, game_type, priority)
                    VALUES (:game_id, :season, :game_date, :home_team, :away_team, :game_url, :game_type, :priority)
                    ON CONFLICT (game_id) DO NOTHING
                    RETURNING id
                """)
                
                result = db.execute(insert_query, game_data)
                
                if result.rowcount > 0:
                    stats['inserted'] += 1
                    logger.info(f"✓ Inserted: {game.game_id} ({game.away_team} @ {game.home_team})")
                else:
                    stats['duplicates'] += 1
                    logger.info(f"○ Duplicate: {game.game_id} ({game.away_team} @ {game.home_team})")
                    
            except Exception as e:
                logger.error(f"✗ Error inserting {game.game_id}: {e}")
                stats['errors'] += 1
        
        db.commit()
        
        logger.info(f"\nInsertion stats: {stats}")
        
        # Query and display results
        logger.info("\nQuerying inserted games...")
        
        result = db.execute(text("""
            SELECT game_id, season, game_date, away_team, home_team, game_type, priority, status
            FROM game_url_queue
            ORDER BY priority ASC, game_date DESC
        """))
        
        games = result.fetchall()
        
        logger.info(f"\nQueue contains {len(games)} games:")
        for game in games:
            logger.info(f"  {game.game_id}: {game.away_team} @ {game.home_team} ({game.game_date}) - {game.game_type} (Priority: {game.priority}, Status: {game.status})")
        
        # Show queue statistics
        logger.info("\nQueue statistics:")
        
        # By status
        result = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM game_url_queue
            GROUP BY status
        """))
        
        status_counts = result.fetchall()
        for row in status_counts:
            logger.info(f"  {row.status}: {row.count}")
        
        # By season
        result = db.execute(text("""
            SELECT season, COUNT(*) as count
            FROM game_url_queue
            GROUP BY season
            ORDER BY season
        """))
        
        season_counts = result.fetchall()
        logger.info("\nBy season:")
        for row in season_counts:
            logger.info(f"  {row.season}: {row.count}")
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Demo failed: {e}")
        return False
    finally:
        db.close()


async def demo_queue_management():
    """Demonstrate queue management operations."""
    logger.info("\nDemo: Queue management operations")
    
    db = next(get_db())
    
    try:
        # Update status of some games
        logger.info("Updating game statuses...")
        
        # Mark one game as validated
        db.execute(text("""
            UPDATE game_url_queue 
            SET status = 'validated', url_validated = true
            WHERE game_id = '0022400306'
        """))
        
        # Mark one game as invalid
        db.execute(text("""
            UPDATE game_url_queue 
            SET status = 'invalid', url_validated = false
            WHERE game_id = '0021900001'
        """))
        
        db.commit()
        
        # Show updated status
        result = db.execute(text("""
            SELECT game_id, status, url_validated
            FROM game_url_queue
            WHERE status != 'pending'
        """))
        
        updated_games = result.fetchall()
        logger.info("Updated game statuses:")
        for game in updated_games:
            logger.info(f"  {game.game_id}: {game.status} (validated: {game.url_validated})")
        
        return True
        
    except Exception as e:
        logger.error(f"Queue management demo failed: {e}")
        return False
    finally:
        db.close()


async def main():
    """Run queue building demonstration."""
    logger.info("=== NBA Game URL Queue Building Demo ===\n")
    
    # Run demonstrations
    demos = [
        ("Queue Population", demo_queue_population),
        ("Queue Management", demo_queue_management),
    ]
    
    for demo_name, demo_func in demos:
        logger.info(f"Running {demo_name}...")
        try:
            success = await demo_func()
            logger.info(f"{demo_name}: {'SUCCESS' if success else 'FAILED'}")
        except Exception as e:
            logger.error(f"{demo_name}: ERROR - {e}")
    
    logger.info("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())