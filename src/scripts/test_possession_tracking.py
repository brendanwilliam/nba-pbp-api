#!/usr/bin/env python3
"""
Simple test script for possession tracking logic
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.possession_tracker import PossessionTracker

def test_basic_possession_logic():
    """Test basic possession change logic with sample data."""
    
    # Sample play events for testing
    sample_events = [
        {
            'event_id': 1,
            'game_id': 'test_game',
            'period': 1,
            'time_remaining': 'PT11M30.00S',
            'time_elapsed_seconds': 30,
            'event_type': 'Made Shot',
            'team_id': 1610612737,  # Hawks
            'player_id': 12345,
            'event_order': 1
        },
        {
            'event_id': 2,
            'game_id': 'test_game',
            'period': 1,
            'time_remaining': 'PT11M15.00S',
            'time_elapsed_seconds': 45,
            'event_type': 'Missed Shot',
            'team_id': 1610612738,  # Celtics
            'player_id': 23456,
            'event_order': 2
        },
        {
            'event_id': 3,
            'game_id': 'test_game',
            'period': 1,
            'time_remaining': 'PT11M14.00S',
            'time_elapsed_seconds': 46,
            'event_type': 'Rebound',
            'team_id': 1610612737,  # Hawks (defensive rebound)
            'player_id': 34567,
            'event_order': 3
        },
        {
            'event_id': 4,
            'game_id': 'test_game',
            'period': 1,
            'time_remaining': 'PT11M00.00S',
            'time_elapsed_seconds': 60,
            'event_type': 'Turnover',
            'team_id': 1610612737,  # Hawks
            'player_id': 45678,
            'event_order': 4
        }
    ]
    
    print("🧪 Testing Possession Tracking Logic")
    print("=" * 50)
    
    # Initialize tracker
    tracker = PossessionTracker('test_game', 1610612737, 1610612738)  # Hawks vs Celtics
    
    # Process events
    possessions = tracker.process_play_events(sample_events)
    
    print(f"Generated {len(possessions)} possessions:")
    print()
    
    for i, possession in enumerate(possessions):
        team_name = "Hawks" if possession.team_id == 1610612737 else "Celtics"
        print(f"Possession {possession.possession_number} ({team_name}):")
        print(f"  Start: Period {possession.start_period}, {possession.start_time_remaining}")
        print(f"  End: Period {possession.end_period}, {possession.end_time_remaining}")
        print(f"  Outcome: {possession.possession_outcome}")
        print(f"  Points: {possession.points_scored}")
        print(f"  Play IDs: {possession.play_ids}")
        print()
    
    # Get summary
    summary = tracker.get_possession_summary()
    print("Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Validate expected results
    print("\n✅ Validation:")
    
    # Should have at least 3 possessions (Hawks -> Celtics -> Hawks -> Celtics)
    assert len(possessions) >= 3, f"Expected at least 3 possessions, got {len(possessions)}"
    print("  ✓ Generated expected number of possessions")
    
    # First possession should be Hawks (game starts with home team)
    assert possessions[0].team_id == 1610612737, "First possession should be Hawks"
    print("  ✓ First possession assigned correctly")
    
    # Made shot should change possession
    made_shot_possession = next((p for p in possessions if p.possession_outcome == 'made_shot'), None)
    assert made_shot_possession is not None, "Should have a possession ending with made_shot"
    print("  ✓ Made shot possession change detected")
    
    # Defensive rebound should change possession
    defensive_rebound_possession = next((p for p in possessions if p.possession_outcome == 'defensive_rebound'), None)
    assert defensive_rebound_possession is not None, "Should have a possession ending with defensive_rebound"
    print("  ✓ Defensive rebound possession change detected")
    
    # Turnover should change possession
    turnover_possession = next((p for p in possessions if p.possession_outcome == 'turnover'), None)
    assert turnover_possession is not None, "Should have a possession ending with turnover"
    print("  ✓ Turnover possession change detected")
    
    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    test_basic_possession_logic()