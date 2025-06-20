"""Test play-by-play data extraction in detail."""

import sys
from pathlib import Path
from pprint import pprint

# Add tests and src to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.database import SessionLocal
from sqlalchemy import text
from json_parser import JSONGameParser


def test_play_by_play_details():
    """Test detailed play-by-play extraction."""
    parser = JSONGameParser()
    
    try:
        # Get a sample game
        session = SessionLocal()
        result = session.execute(text("SELECT game_id FROM raw_game_data LIMIT 1"))
        sample_game = result.fetchone()
        session.close()
        
        if not sample_game:
            print("❌ No game data available")
            return
        
        game_id = sample_game[0]
        
        # Get raw JSON data
        _, raw_json = parser.get_sample_game(game_id)
        
        print(f"🏀 Play-by-Play Details for Game: {game_id}")
        print("=" * 60)
        
        # Parse basic info
        basic_info = parser.parse_game_basic_info(raw_json)
        home_team, away_team = parser.parse_teams(raw_json)
        
        print(f"📊 Game: {basic_info.get('game_code', 'N/A')}")
        print(f"👥 Teams: {away_team.get('team_tricode', 'N/A')} @ {home_team.get('team_tricode', 'N/A')}")
        print(f"🏟️ Status: {basic_info.get('game_status_text', 'N/A')}")
        
        # Get play-by-play data
        event_count = parser.count_play_events(raw_json)
        sample_events = parser.sample_play_events(raw_json, 10)
        
        print(f"\n🎬 Play-by-Play Events: {event_count:,} total")
        
        if sample_events:
            print(f"\n📋 Sample Events (first 10):")
            print("-" * 60)
            
            for i, event in enumerate(sample_events, 1):
                period = event.get('period', 'N/A')
                clock = event.get('time_remaining', 'N/A')
                action_type = event.get('event_type', 'N/A')
                description = event.get('description', 'N/A')
                home_score = event.get('home_score', 0)
                away_score = event.get('away_score', 0)
                
                print(f"{i:2d}. Q{period} {clock} | {action_type}")
                print(f"    {description}")
                print(f"    Score: {away_team.get('team_tricode', 'AWAY')} {away_score} - {home_team.get('team_tricode', 'HOME')} {home_score}")
                
                if event.get('shot_distance'):
                    shot_distance = event.get('shot_distance')
                    shot_result = event.get('shot_result')
                    print(f"    Shot: {shot_distance}ft - {shot_result}")
                
                print()
        
        # Show event type distribution
        print(f"📊 Event Type Analysis:")
        print("-" * 40)
        
        # Get all events for analysis
        props = raw_json.get('props', {})
        page_props = props.get('pageProps', {})
        play_by_play = page_props.get('playByPlay', {})
        all_actions = play_by_play.get('actions', [])
        
        if all_actions:
            # Count event types
            event_types = {}
            for action in all_actions:
                action_type = action.get('actionType', 'Unknown')
                event_types[action_type] = event_types.get(action_type, 0) + 1
            
            # Sort by frequency
            sorted_types = sorted(event_types.items(), key=lambda x: x[1], reverse=True)
            
            for event_type, count in sorted_types[:10]:  # Top 10 event types
                percentage = (count / len(all_actions)) * 100
                print(f"  {event_type:20} {count:4d} ({percentage:5.1f}%)")
            
            print(f"\nTotal unique event types: {len(event_types)}")
        
        # Show periods analysis
        print(f"\n⏱️ Period Analysis:")
        print("-" * 30)
        
        if all_actions:
            periods = {}
            for action in all_actions:
                period = action.get('period', 0)
                periods[period] = periods.get(period, 0) + 1
            
            for period in sorted(periods.keys()):
                count = periods[period]
                print(f"  Period {period}: {count:3d} events")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing play-by-play: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        parser.close()


if __name__ == "__main__":
    test_play_by_play_details()