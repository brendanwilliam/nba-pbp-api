"""
Test suite for NBA Lineup Tracker

Tests the lineup tracking functionality using sample game data
from tests/data/ directory across different eras.
"""

import json
import os
import pytest
from typing import Dict, Any

import sys
sys.path.append('/Users/brendan/nba-pbp-api')

from src.analytics.lineup_tracker import LineupTracker, load_game_json


class TestLineupTracker:
    """Test cases for LineupTracker functionality"""
    
    @pytest.fixture
    def sample_games(self):
        """Load sample game data from tests/data directory"""
        test_data_dir = '/Users/brendan/nba-pbp-api/tests/data'
        games = {}
        
        # Load a few representative games from different eras
        sample_files = [
            '199697_reg_NYK-vs-BOS_0110_0029600481.json',  # 1996-97 season
            '202324_reg_MIL-vs-DAL_0203_0022300702.json',  # 2023-24 season
            '201920_pla_LAL-vs-MIA_0930_0041900401.json',  # 2019-20 playoffs
        ]
        
        for filename in sample_files:
            file_path = os.path.join(test_data_dir, filename)
            if os.path.exists(file_path):
                games[filename] = load_game_json(file_path)
        
        return games
    
    def test_lineup_tracker_initialization(self, sample_games):
        """Test that LineupTracker initializes correctly with game data"""
        for game_name, game_data in sample_games.items():
            tracker = LineupTracker(game_data)
            
            # Verify basic attributes are set
            assert tracker.game_id is not None
            assert tracker.home_team_id is not None
            assert tracker.away_team_id is not None
            assert tracker.home_team_id != tracker.away_team_id
            assert len(tracker.player_roster) > 0
            
            print(f"✓ {game_name}: Initialized successfully")
            print(f"  Game ID: {tracker.game_id}")
            print(f"  Home Team: {tracker.home_team_id}, Away Team: {tracker.away_team_id}")
            print(f"  Total Players: {len(tracker.player_roster)}")
    
    def test_starting_lineups(self, sample_games):
        """Test extraction of starting lineups"""
        for game_name, game_data in sample_games.items():
            tracker = LineupTracker(game_data)
            
            try:
                home_starters, away_starters = tracker.get_starting_lineups()
                
                # Verify we have exactly 5 starters per team
                assert len(home_starters) == 5, f"Home team should have 5 starters, got {len(home_starters)}"
                assert len(away_starters) == 5, f"Away team should have 5 starters, got {len(away_starters)}"
                
                # Verify no duplicate players
                assert len(set(home_starters)) == 5, "Home starters should be unique"
                assert len(set(away_starters)) == 5, "Away starters should be unique"
                
                # Verify no overlap between teams
                assert len(set(home_starters) & set(away_starters)) == 0, "No player should start for both teams"
                
                print(f"✓ {game_name}: Starting lineups extracted")
                print(f"  Home starters: {[tracker.player_roster[pid]['playerName'] for pid in home_starters]}")
                print(f"  Away starters: {[tracker.player_roster[pid]['playerName'] for pid in away_starters]}")
                
            except Exception as e:
                print(f"✗ {game_name}: Failed to extract starting lineups - {e}")
                raise
    
    def test_substitution_parsing(self, sample_games):
        """Test parsing of substitution events"""
        for game_name, game_data in sample_games.items():
            tracker = LineupTracker(game_data)
            
            try:
                substitutions = tracker.parse_substitution_events()
                
                # Verify we found some substitutions
                assert len(substitutions) > 0, "Should find at least some substitutions"
                
                # Verify substitutions are sorted chronologically
                for i in range(1, len(substitutions)):
                    prev_sub = substitutions[i-1]
                    curr_sub = substitutions[i]
                    
                    # Either later period, or same period with earlier/equal time
                    assert (curr_sub.period > prev_sub.period or 
                           (curr_sub.period == prev_sub.period and 
                            curr_sub.seconds_elapsed >= prev_sub.seconds_elapsed)), \
                           "Substitutions should be in chronological order"
                
                print(f"✓ {game_name}: Parsed {len(substitutions)} substitutions")
                
                # Show first few substitutions
                for i, sub in enumerate(substitutions[:3]):
                    print(f"  Sub {i+1}: {sub.player_in_name} FOR {sub.player_out_name} "
                          f"at {sub.clock} in period {sub.period}")
                          
            except Exception as e:
                print(f"✗ {game_name}: Failed to parse substitutions - {e}")
                raise
    
    def test_clock_parsing(self, sample_games):
        """Test game clock parsing functionality"""
        for game_name, game_data in sample_games.items():
            tracker = LineupTracker(game_data)
            
            # Test various clock formats
            test_cases = [
                (1, "PT12M00.00S", 0),      # Start of 1st quarter
                (1, "PT06M00.00S", 360),    # 6 minutes into 1st quarter
                (1, "PT00M00.00S", 720),    # End of 1st quarter
                (2, "PT12M00.00S", 720),    # Start of 2nd quarter
                (2, "PT00M00.00S", 1440),   # End of 2nd quarter (halftime)
                (4, "PT00M00.00S", 2880),   # End of regulation
                (5, "PT05M00.00S", 2880),   # Start of OT
                (5, "PT00M00.00S", 3180),   # End of first OT
            ]
            
            for period, clock, expected_seconds in test_cases:
                result = tracker.parse_clock_to_seconds(period, clock)
                assert result == expected_seconds, \
                    f"Period {period}, Clock {clock}: expected {expected_seconds}, got {result}"
            
            print(f"✓ {game_name}: Clock parsing works correctly")
            break  # Only need to test once
    
    def test_lineup_timeline(self, sample_games):
        """Test building complete lineup timeline"""
        for game_name, game_data in sample_games.items():
            tracker = LineupTracker(game_data)
            
            try:
                timeline = tracker.build_lineup_timeline()
                
                # Verify we have at least starting lineup
                assert len(timeline) >= 1, "Should have at least starting lineup in timeline"
                
                # Verify first state is game start
                first_state = timeline[0]
                assert first_state.period == 1
                assert first_state.seconds_elapsed == 0
                assert len(first_state.home_players) == 5
                assert len(first_state.away_players) == 5
                
                # Verify timeline is chronologically ordered
                for i in range(1, len(timeline)):
                    prev_state = timeline[i-1]
                    curr_state = timeline[i]
                    assert curr_state.seconds_elapsed >= prev_state.seconds_elapsed, \
                        "Timeline should be chronologically ordered"
                
                print(f"✓ {game_name}: Built timeline with {len(timeline)} states")
                
            except Exception as e:
                print(f"✗ {game_name}: Failed to build timeline - {e}")
                raise
    
    def test_get_players_on_court(self, sample_games):
        """Test querying players on court at specific moments"""
        for game_name, game_data in sample_games.items():
            tracker = LineupTracker(game_data)
            
            # Test queries at various game moments
            test_queries = [
                (1, "PT12M00.00S"),  # Game start
                (1, "PT06M00.00S"),  # 6 minutes in
                (2, "PT12M00.00S"),  # 2nd quarter start
                (2, "PT03M15.00S"),  # Late 2nd quarter
                (4, "PT02M00.00S"),  # Late 4th quarter
            ]
            
            for period, clock in test_queries:
                try:
                    result = tracker.get_players_on_court(period, clock)
                    
                    # Verify result structure
                    assert 'home_players' in result
                    assert 'away_players' in result
                    assert 'home_player_names' in result
                    assert 'away_player_names' in result
                    
                    # Verify exactly 5 players per team
                    assert len(result['home_players']) == 5
                    assert len(result['away_players']) == 5
                    assert len(result['home_player_names']) == 5
                    assert len(result['away_player_names']) == 5
                    
                    # Verify no duplicates
                    assert len(set(result['home_players'])) == 5
                    assert len(set(result['away_players'])) == 5
                    
                    print(f"✓ {game_name}: Period {period}, Clock {clock}")
                    print(f"  Home: {result['home_player_names']}")
                    print(f"  Away: {result['away_player_names']}")
                    
                except Exception as e:
                    print(f"✗ {game_name}: Query failed at Period {period}, Clock {clock} - {e}")
                    raise
    
    def test_player_name_resolution(self, sample_games):
        """Test player name resolution functionality"""
        for game_name, game_data in sample_games.items():
            tracker = LineupTracker(game_data)
            
            # Test finding players by various name formats
            for player_id, player_info in list(tracker.player_roster.items())[:5]:  # Test first 5
                team_id = player_info['teamId']
                
                # Test full name
                if player_info['playerName']:
                    found_id = tracker.find_player_by_name(player_info['playerName'], team_id)
                    assert found_id == player_id, \
                        f"Should find player by full name: {player_info['playerName']}"
                
                # Test first initial + last name format
                if player_info['firstName'] and player_info['familyName']:
                    short_name = f"{player_info['firstName'][0]}. {player_info['familyName']}"
                    found_id = tracker.find_player_by_name(short_name, team_id)
                    assert found_id == player_id, \
                        f"Should find player by short name: {short_name}"
            
            print(f"✓ {game_name}: Player name resolution works")
            break  # Only need to test once


def test_multiple_games():
    """Test lineup tracker across multiple games from different eras"""
    test_data_dir = '/Users/brendan/nba-pbp-api/tests/data'
    
    # Test games from different decades
    test_files = [
        '199697_reg_NYK-vs-BOS_0110_0029600481.json',  # 1990s
        '200304_reg_PHX-vs-MIN_0217_0020300766.json',  # 2000s
        '201415_reg_DAL-vs-OKC_0219_0021400801.json',  # 2010s
        '202324_reg_MIL-vs-DAL_0203_0022300702.json',  # 2020s
    ]
    
    results = {}
    
    for filename in test_files:
        file_path = os.path.join(test_data_dir, filename)
        if not os.path.exists(file_path):
            continue
            
        try:
            game_data = load_game_json(file_path)
            tracker = LineupTracker(game_data)
            
            # Get basic game info
            home_starters, away_starters = tracker.get_starting_lineups()
            substitutions = tracker.parse_substitution_events()
            
            results[filename] = {
                'game_id': tracker.game_id,
                'home_team': tracker.home_team_id,
                'away_team': tracker.away_team_id,
                'total_players': len(tracker.player_roster),
                'substitutions': len(substitutions),
                'status': 'SUCCESS'
            }
            
        except Exception as e:
            results[filename] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    print("\n" + "="*60)
    print("MULTI-GAME TEST RESULTS")
    print("="*60)
    
    for filename, result in results.items():
        era = filename[:6]  # Extract year
        if result['status'] == 'SUCCESS':
            print(f"✓ {era}: {filename}")
            print(f"  Game ID: {result['game_id']}")
            print(f"  Teams: {result['home_team']} vs {result['away_team']}")
            print(f"  Players: {result['total_players']}, Subs: {result['substitutions']}")
        else:
            print(f"✗ {era}: {filename}")
            print(f"  Error: {result['error']}")
    
    print("="*60)
    
    success_count = sum(1 for r in results.values() if r['status'] == 'SUCCESS')
    total_count = len(results)
    print(f"SUMMARY: {success_count}/{total_count} games processed successfully")


if __name__ == "__main__":
    # Run comprehensive test
    test_multiple_games()
    
    print("\n" + "="*60)
    print("Running pytest tests...")
    print("="*60)
    
    # Run pytest with verbose output
    pytest.main([__file__, "-v"])