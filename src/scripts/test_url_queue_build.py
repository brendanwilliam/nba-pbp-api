"""
Test script for the game URL queue building process.
"""

import asyncio
import logging
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..scrapers.game_url_generator import GameURLGenerator
from ..scrapers.url_validator import GameURLValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_single_season():
    """Test the URL generation for a single recent season."""
    logger.info("Testing URL generation for 2024-25 season")
    
    db = next(get_db())
    generator = GameURLGenerator(db)
    
    try:
        await generator.initialize()
        
        # Test with current season
        games = await generator.discover_season_games("2024-25")
        
        logger.info(f"Discovered {len(games)} games for 2024-25")
        
        # Show sample games
        for i, game in enumerate(games[:5]):
            logger.info(f"Game {i+1}: {game.game_id} - {game.away_team} @ {game.home_team}")
            logger.info(f"  Date: {game.game_date}")
            logger.info(f"  URL: {game.game_url}")
            logger.info(f"  Type: {game.game_type}")
            logger.info(f"  Priority: {game.priority}")
        
        # Test queue population with sample
        sample_games = games[:10]  # Just first 10 for testing
        stats = await generator.populate_queue(sample_games)
        
        logger.info(f"Queue population test: {stats}")
        
        return len(games) > 0
        
    except Exception as e:
        logger.error(f"Error in single season test: {e}")
        return False
    finally:
        await generator.close()
        db.close()


async def test_url_validation():
    """Test URL validation with known good URLs."""
    logger.info("Testing URL validation")
    
    db = next(get_db())
    validator = GameURLValidator(db)
    
    try:
        await validator.initialize()
        
        # Test with some known URLs
        test_urls = [
            ("test1", "https://www.nba.com/game/ind-vs-mem-0022400306"),
            ("test2", "https://www.nba.com/game/nop-vs-nyk-0022400308"),
            ("invalid", "https://www.nba.com/game/invalid-url-test"),
        ]
        
        results = await validator.validate_batch(test_urls)
        
        success_count = 0
        for result in results:
            logger.info(f"URL: {result.url}")
            logger.info(f"  Valid: {result.is_valid()}")
            logger.info(f"  Accessible: {result.is_accessible}")
            logger.info(f"  Has Next Data: {result.has_next_data}")
            logger.info(f"  Has Game Data: {result.has_game_data}")
            logger.info(f"  Response Time: {result.response_time_ms}ms")
            if result.error_message:
                logger.info(f"  Error: {result.error_message}")
            
            if result.is_valid():
                success_count += 1
        
        logger.info(f"Validation test: {success_count}/{len(results)} URLs valid")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error in validation test: {e}")
        return False
    finally:
        await validator.close()
        db.close()


async def test_team_mapping():
    """Test team mapping functionality."""
    logger.info("Testing team mapping")
    
    from ..scrapers.team_mapping import NBA_TEAMS
    
    # Test current teams
    current_teams = NBA_TEAMS.get_all_teams_for_season("2024-25")
    logger.info(f"Current teams (2024-25): {len(current_teams)} teams")
    logger.info(f"Sample teams: {current_teams[:10]}")
    
    # Test historical teams
    historical_teams_1997 = NBA_TEAMS.get_all_teams_for_season("1997-98")
    logger.info(f"Historical teams (1997-98): {len(historical_teams_1997)} teams")
    
    # Test specific team lookups
    test_cases = [
        ("BOS", "2024-25"),  # Current team
        ("SEA", "2007-08"),  # Seattle before relocation
        ("OKC", "2024-25"),  # OKC after relocation
        ("VAN", "1997-98"),  # Vancouver Grizzlies
    ]
    
    for tricode, season in test_cases:
        team_info = NBA_TEAMS.get_team_for_season(tricode, season)
        if team_info:
            logger.info(f"{tricode} in {season}: {team_info['name']}")
        else:
            logger.warning(f"{tricode} not found for {season}")
    
    return len(current_teams) == 30  # Should be 30 current NBA teams


async def run_all_tests():
    """Run all tests."""
    logger.info("Starting comprehensive tests...")
    
    tests = [
        ("Team Mapping", test_team_mapping),
        ("Single Season URL Generation", test_single_season),
        ("URL Validation", test_url_validation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n=== Running {test_name} ===")
        try:
            result = await test_func()
            results[test_name] = result
            logger.info(f"{test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"{test_name}: ERROR - {e}")
    
    # Summary
    logger.info(f"\n=== TEST SUMMARY ===")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)