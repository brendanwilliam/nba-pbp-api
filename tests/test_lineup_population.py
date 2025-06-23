#!/usr/bin/env python3
"""
Test for lineup tracking database population
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analytics.lineup_tracker import LineupTracker
from core.database import SessionLocal
from sqlalchemy import text

def test_lineup_population():
    """Test lineup tracking database population with a real game"""
    db = SessionLocal()
    try:
        # Get a game that should have valid data
        result = db.execute(text("SELECT game_id, raw_json FROM raw_game_data WHERE game_id = '0022200650'"))
        game_data = result.fetchone()
        
        if not game_data:
            print("No game data found")
            return
        
        game_id, raw_json = game_data
        if isinstance(raw_json, str):
            raw_json = json.loads(raw_json)
        
        print(f"Testing lineup population for game: {game_id}")
        
        # Initialize tracker and extract data
        tracker = LineupTracker(raw_json)
        timeline = tracker.build_lineup_timeline()
        substitutions = tracker.parse_substitution_events()
        
        print(f"Extracted {len(timeline)} lineup states and {len(substitutions)} substitution events")
        
        # Test database insertion format
        lineup_states = []
        for state in timeline:
            lineup_states.append({
                'game_id': state.game_id,
                'period': state.period,
                'clock': state.clock,
                'seconds_elapsed': state.seconds_elapsed,
                'home_team_id': state.home_team_id,
                'away_team_id': state.away_team_id,
                'home_players': state.home_players,
                'away_players': state.away_players
            })
        
        substitution_events = []
        for sub in substitutions:
            substitution_events.append({
                'game_id': game_id,
                'event_id': sub.action_number,
                'period': sub.period,
                'clock': sub.clock,
                'seconds_elapsed': sub.seconds_elapsed,
                'team_id': sub.team_id,
                'player_in_id': sub.player_in_id,
                'player_out_id': sub.player_out_id,
                'player_in_name': sub.player_in_name,
                'player_out_name': sub.player_out_name,
                'event_description': sub.description
            })
        
        print(f"✅ Converted {len(lineup_states)} lineup states for database insertion")
        print(f"✅ Converted {len(substitution_events)} substitution events for database insertion")
        
        # Test a few sample insertions (but don't commit)
        try:
            # Test lineup state insertion
            if lineup_states:
                sample_state = lineup_states[0]
                home_players = sorted(sample_state['home_players'])
                if len(home_players) >= 5:
                    db.execute(text("""
                        INSERT INTO lineup_states (
                            game_id, period, clock_time, seconds_elapsed, team_id,
                            player_1_id, player_2_id, player_3_id, player_4_id, player_5_id,
                            lineup_hash
                        ) VALUES (
                            :game_id, :period, :clock_time, :seconds_elapsed, :team_id,
                            :player_1_id, :player_2_id, :player_3_id, :player_4_id, :player_5_id,
                            :lineup_hash
                        )
                    """), {
                        'game_id': sample_state['game_id'],
                        'period': sample_state['period'],
                        'clock_time': sample_state['clock'],
                        'seconds_elapsed': sample_state['seconds_elapsed'],
                        'team_id': sample_state['home_team_id'],
                        'player_1_id': home_players[0],
                        'player_2_id': home_players[1],
                        'player_3_id': home_players[2],
                        'player_4_id': home_players[3],
                        'player_5_id': home_players[4],
                        'lineup_hash': f"test_{sample_state['game_id']}_home"
                    })
                    print("✅ Lineup state insertion test passed")
            
            # Test substitution event insertion
            if substitution_events:
                sample_event = substitution_events[0]
                db.execute(text("""
                    INSERT INTO substitution_events (
                        game_id, action_number, period, clock_time, seconds_elapsed,
                        team_id, player_out_id, player_out_name, player_in_id, player_in_name, description
                    ) VALUES (
                        :game_id, :action_number, :period, :clock_time, :seconds_elapsed,
                        :team_id, :player_out_id, :player_out_name, :player_in_id, :player_in_name, :description
                    )
                """), {
                    'game_id': sample_event['game_id'],
                    'action_number': sample_event['event_id'],
                    'period': sample_event['period'],
                    'clock_time': sample_event['clock'],
                    'seconds_elapsed': sample_event['seconds_elapsed'],
                    'team_id': sample_event['team_id'],
                    'player_out_id': sample_event['player_out_id'],
                    'player_out_name': sample_event.get('player_out_name', ''),
                    'player_in_id': sample_event['player_in_id'],
                    'player_in_name': sample_event.get('player_in_name', ''),
                    'description': sample_event['event_description']
                })
                print("✅ Substitution event insertion test passed")
            
            # Rollback to not actually insert
            db.rollback()
            print("✅ Database operations rolled back")
            
        except Exception as e:
            print(f"❌ Database insertion test failed: {e}")
            db.rollback()
            
    finally:
        db.close()

if __name__ == "__main__":
    test_lineup_population()