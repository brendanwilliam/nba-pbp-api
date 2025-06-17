#!/usr/bin/env python3
"""
Verify playoff game ID sequences based on NBA playoff structure
Playoff IDs: 00{4}{YY}00{round}{series}{game}
- Round: 0-3 (1st round, conf semis, conf finals, finals)
- Series: varies by round (0-7 for 1st round, 0-3 for conf semis, 0-1 for conf finals, 0 for finals)
- Game: 1-7 (game number in series)
"""

import os
from sqlalchemy import create_engine, text
from collections import defaultdict

def parse_playoff_game_id(game_id):
    """
    Parse playoff game ID to extract components
    Format: 00{4}{YY}00{round}{series}{game}
    """
    if len(game_id) != 10 or not game_id.startswith('004'):
        return None
    
    try:
        year_code = game_id[3:5]
        if game_id[5:7] != '00':
            return None
            
        round_num = int(game_id[7])
        series_num = int(game_id[8])
        game_num = int(game_id[9])
        
        return {
            'year_code': year_code,
            'round': round_num,
            'series': series_num,
            'game': game_num
        }
    except ValueError:
        return None

def get_expected_series_counts():
    """Expected number of series per round"""
    return {
        0: 8,  # 1st round: 8 series (16 teams -> 8 matchups)
        1: 4,  # Conference semifinals: 4 series
        2: 2,  # Conference finals: 2 series
        3: 1   # Finals: 1 series
    }

def validate_playoff_structure(parsed_games):
    """Validate that playoff structure makes sense"""
    issues = []
    expected_series = get_expected_series_counts()
    
    # Group by round
    rounds = defaultdict(lambda: defaultdict(list))
    
    for game_info in parsed_games:
        parsed = game_info['parsed']
        rounds[parsed['round']][parsed['series']].append(parsed['game'])
    
    for round_num in range(4):
        if round_num not in rounds:
            continue
            
        series_in_round = rounds[round_num]
        expected_count = expected_series[round_num]
        
        # Check series numbers
        max_series = max(series_in_round.keys()) if series_in_round else -1
        
        if max_series >= expected_count:
            issues.append(f"Round {round_num}: Series {max_series} exceeds expected max {expected_count-1}")
        
        # Check for missing series
        for expected_series_num in range(expected_count):
            if expected_series_num not in series_in_round:
                issues.append(f"Round {round_num}: Missing series {expected_series_num}")
        
        # Check game numbers in each series
        for series_num, games in series_in_round.items():
            games.sort()
            if games[0] != 1:
                issues.append(f"Round {round_num}, Series {series_num}: Games don't start at 1 (start at {games[0]})")
            
            if max(games) > 7:
                issues.append(f"Round {round_num}, Series {series_num}: Game {max(games)} exceeds max 7")
            
            # Check for gaps in game sequence
            for i in range(len(games) - 1):
                if games[i+1] - games[i] > 1:
                    issues.append(f"Round {round_num}, Series {series_num}: Gap between game {games[i]} and {games[i+1]}")
    
    return issues

def main():
    print("Playoff Game ID Sequence Verification")
    print("=" * 80)
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://brendan@localhost:5432/nba_pbp')
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Get all playoff games
        result = conn.execute(text("""
            SELECT 
                season,
                game_id,
                game_type,
                game_date,
                home_team,
                away_team
            FROM game_url_queue
            WHERE game_type = 'playoff'
            AND season != '2024-25'  -- Exclude current season in progress
            ORDER BY season, game_id
        """))
        
        # Group by season
        season_data = defaultdict(list)
        for row in result:
            season_data[row.season].append({
                'game_id': row.game_id,
                'game_type': row.game_type,
                'game_date': row.game_date,
                'home_team': row.home_team,
                'away_team': row.away_team
            })
        
        print("PLAYOFF GAME ID STRUCTURE ANALYSIS")
        print("=" * 80)
        
        total_issues = 0
        total_invalid_ids = 0
        
        for season in sorted(season_data.keys()):
            games = season_data[season]
            
            print(f"\nSEASON: {season}")
            print(f"Playoff games: {len(games)}")
            
            # Parse all game IDs
            parsed_games = []
            invalid_games = []
            
            for game in games:
                parsed = parse_playoff_game_id(game['game_id'])
                if parsed:
                    parsed_games.append({
                        'game': game,
                        'parsed': parsed
                    })
                else:
                    invalid_games.append(game['game_id'])
            
            if invalid_games:
                print(f"  ⚠️  {len(invalid_games)} invalid playoff game IDs:")
                for game_id in invalid_games[:5]:
                    print(f"    {game_id}")
                if len(invalid_games) > 5:
                    print(f"    ... and {len(invalid_games) - 5} more")
                total_invalid_ids += len(invalid_games)
            
            if not parsed_games:
                print(f"  ❌ No valid playoff game IDs found")
                continue
            
            # Analyze structure
            rounds = defaultdict(lambda: defaultdict(set))
            
            for game_info in parsed_games:
                parsed = game_info['parsed']
                rounds[parsed['round']][parsed['series']].add(parsed['game'])
            
            print(f"  Playoff structure:")
            
            round_names = ["1st Round", "Conf Semifinals", "Conf Finals", "Finals"]
            expected_series = get_expected_series_counts()
            
            for round_num in range(4):
                if round_num in rounds:
                    series_count = len(rounds[round_num])
                    expected_count = expected_series[round_num]
                    
                    print(f"    {round_names[round_num]}: {series_count}/{expected_count} series")
                    
                    # Show series details
                    for series_num in sorted(rounds[round_num].keys()):
                        games_in_series = sorted(rounds[round_num][series_num])
                        game_range = f"{games_in_series[0]}-{games_in_series[-1]}" if len(games_in_series) > 1 else str(games_in_series[0])
                        print(f"      Series {series_num}: Games {game_range} ({len(games_in_series)} games)")
                else:
                    print(f"    {round_names[round_num]}: No games found")
            
            # Validate structure
            issues = validate_playoff_structure(parsed_games)
            
            if issues:
                print(f"  ❌ Structure issues found:")
                for issue in issues[:10]:  # Show first 10 issues
                    print(f"    • {issue}")
                if len(issues) > 10:
                    print(f"    ... and {len(issues) - 10} more issues")
                total_issues += len(issues)
            else:
                print(f"  ✅ Playoff structure looks valid")
            
            # Look for missing games in series
            missing_games = []
            
            for round_num, series_dict in rounds.items():
                for series_num, games_set in series_dict.items():
                    games_list = sorted(games_set)
                    
                    # Check for missing games in the middle of series
                    for game_num in range(1, max(games_list) + 1):
                        if game_num not in games_set:
                            missing_games.append(f"Round {round_num}, Series {series_num}, Game {game_num}")
            
            if missing_games:
                print(f"  ⚠️  Missing games in existing series:")
                for missing in missing_games[:5]:
                    print(f"    {missing}")
                if len(missing_games) > 5:
                    print(f"    ... and {len(missing_games) - 5} more")
        
        # Summary
        print(f"\n" + "=" * 80)
        print("PLAYOFF STRUCTURE SUMMARY")
        print("=" * 80)
        
        total_seasons = len(season_data)
        seasons_with_issues = sum(1 for season in season_data.keys() 
                                if validate_playoff_structure([
                                    {'game': g, 'parsed': parse_playoff_game_id(g['game_id'])}
                                    for g in season_data[season]
                                    if parse_playoff_game_id(g['game_id'])
                                ]))
        
        print(f"Seasons analyzed: {total_seasons}")
        print(f"Total invalid game IDs: {total_invalid_ids}")
        print(f"Total structure issues: {total_issues}")
        
        if total_issues > 0:
            print(f"\n📋 COMMON ISSUES TO INVESTIGATE:")
            print("1. Missing series in early rounds")
            print("2. Games numbered beyond 7 in a series")
            print("3. Series numbers exceeding expected maximums")
            print("4. Missing games within existing series")
        
        # Generate missing game IDs for key gaps
        print(f"\n" + "=" * 80)
        print("POTENTIAL MISSING GAME IDS TO INVESTIGATE")
        print("=" * 80)
        
        for season in sorted(season_data.keys())[-5:]:  # Last 5 seasons
            games = season_data[season]
            parsed_games = []
            
            for game in games:
                parsed = parse_playoff_game_id(game['game_id'])
                if parsed:
                    parsed_games.append({'game': game, 'parsed': parsed})
            
            if not parsed_games:
                continue
                
            # Look for structural gaps
            rounds = defaultdict(lambda: defaultdict(set))
            for game_info in parsed_games:
                parsed = game_info['parsed']
                rounds[parsed['round']][parsed['series']].add(parsed['game'])
            
            print(f"\n{season}:")
            
            missing_series_games = []
            expected_series = get_expected_series_counts()
            
            # Check for completely missing series
            for round_num in range(4):
                if round_num in rounds:
                    for expected_series_num in range(expected_series[round_num]):
                        if expected_series_num not in rounds[round_num]:
                            # Generate game ID for first game of missing series
                            year_code = season.split('-')[1]
                            game_id = f"004{year_code}00{round_num}{expected_series_num}1"
                            missing_series_games.append(game_id)
            
            if missing_series_games:
                print(f"  Missing series (first games): {', '.join(missing_series_games[:5])}")
                if len(missing_series_games) > 5:
                    print(f"  ... and {len(missing_series_games) - 5} more")

if __name__ == "__main__":
    main()