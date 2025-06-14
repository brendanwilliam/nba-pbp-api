"""
Offline test for queue building functionality (no network calls).
"""

import logging
from datetime import date
from ..scrapers.team_mapping import NBA_TEAMS
from ..scrapers.game_url_generator import GameURLInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_team_mapping():
    """Test team mapping functionality."""
    logger.info("Testing team mapping...")
    
    # Test current teams
    current_teams = NBA_TEAMS.get_all_teams_for_season("2024-25")
    logger.info(f"Current teams (2024-25): {len(current_teams)} teams")
    
    if len(current_teams) != 30:
        logger.error(f"Expected 30 teams, got {len(current_teams)}")
        return False
    
    # Test historical teams
    historical_teams = NBA_TEAMS.get_all_teams_for_season("1997-98")
    logger.info(f"Historical teams (1997-98): {len(historical_teams)} teams")
    
    # Test specific lookups
    test_cases = [
        ("BOS", "2024-25", True),   # Current team
        ("LAL", "2024-25", True),   # Current team
        ("SEA", "2007-08", True),   # Seattle before relocation
        ("OKC", "2024-25", True),   # OKC after relocation
        ("VAN", "1997-98", True),   # Vancouver Grizzlies
        ("XYZ", "2024-25", False),  # Invalid team
    ]
    
    for tricode, season, should_exist in test_cases:
        team_info = NBA_TEAMS.get_team_for_season(tricode, season)
        exists = team_info is not None
        
        if exists != should_exist:
            logger.error(f"Team lookup failed: {tricode} in {season}, expected {should_exist}, got {exists}")
            return False
        
        if exists:
            logger.info(f"✓ {tricode} in {season}: {team_info['name']}")
        else:
            logger.info(f"✓ {tricode} in {season}: Not found (expected)")
    
    return True


def test_game_url_info():
    """Test GameURLInfo data structure."""
    logger.info("Testing GameURLInfo...")
    
    # Create sample game info
    game_info = GameURLInfo(
        game_id="0022400306",
        season="2024-25",
        game_date=date(2024, 12, 1),
        home_team="MEM",
        away_team="IND",
        game_url="https://www.nba.com/game/ind-vs-mem-0022400306",
        game_type="regular",
        priority=100
    )
    
    # Test conversion to dict
    game_dict = game_info.to_dict()
    
    required_fields = ['game_id', 'season', 'game_date', 'home_team', 'away_team', 'game_url', 'game_type', 'priority']
    
    for field in required_fields:
        if field not in game_dict:
            logger.error(f"Missing field in game dict: {field}")
            return False
    
    logger.info(f"✓ GameURLInfo structure valid: {game_dict}")
    return True


def test_url_generation():
    """Test URL generation algorithm."""
    logger.info("Testing URL generation...")
    
    from ..scrapers.game_url_generator import GameURLGenerator
    
    generator = GameURLGenerator()
    
    # Test URL generation
    test_cases = [
        ("IND", "MEM", "0022400306", "https://www.nba.com/game/ind-vs-mem-0022400306"),
        ("LAL", "BOS", "0012345678", "https://www.nba.com/game/lal-vs-bos-0012345678"),
    ]
    
    for away, home, game_id, expected_url in test_cases:
        generated_url = generator.generate_game_url(away, home, game_id)
        
        if generated_url != expected_url:
            logger.error(f"URL generation failed: expected {expected_url}, got {generated_url}")
            return False
        
        logger.info(f"✓ URL generation: {away} @ {home} -> {generated_url}")
    
    return True


def test_database_schema():
    """Test database schema exists."""
    logger.info("Testing database schema...")
    
    try:
        from sqlalchemy import text
        from ..core.database import get_db
        
        db = next(get_db())
        
        # Check if game_url_queue table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'game_url_queue'
            );
        """))
        
        exists = result.scalar()
        
        if not exists:
            logger.error("game_url_queue table does not exist")
            return False
        
        # Check table structure
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'game_url_queue'
            ORDER BY ordinal_position;
        """))
        
        columns = result.fetchall()
        required_columns = ['id', 'game_id', 'season', 'game_date', 'home_team', 'away_team', 'game_url']
        
        column_names = [col.column_name for col in columns]
        
        for req_col in required_columns:
            if req_col not in column_names:
                logger.error(f"Missing required column: {req_col}")
                return False
        
        logger.info(f"✓ Database schema valid with columns: {column_names}")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"Database schema test failed: {e}")
        return False


def run_offline_tests():
    """Run all offline tests."""
    logger.info("Starting offline tests...")
    
    tests = [
        ("Team Mapping", test_team_mapping),
        ("GameURLInfo Structure", test_game_url_info),
        ("URL Generation", test_url_generation),
        ("Database Schema", test_database_schema),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n=== {test_name} ===")
        try:
            result = test_func()
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
    success = run_offline_tests()
    exit(0 if success else 1)