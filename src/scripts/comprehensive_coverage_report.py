#!/usr/bin/env python3
"""
Comprehensive coverage gap analysis across all NBA game types and eras
"""

import os
from sqlalchemy import create_engine, text
from collections import defaultdict

def get_expected_counts():
    """Get expected game counts by season and type"""
    return {
        'regular': {
            '1996-97': 1189, '1997-98': 1189, '1998-99': 725, '1999-00': 1189, '2000-01': 1189,
            '2001-02': 1189, '2002-03': 1189, '2003-04': 1189, '2004-05': 1230, '2005-06': 1230,
            '2006-07': 1230, '2007-08': 1230, '2008-09': 1230, '2009-10': 1230, '2010-11': 1230,
            '2011-12': 990, '2012-13': 1229, '2013-14': 1230, '2014-15': 1230, '2015-16': 1230,
            '2016-17': 1230, '2017-18': 1230, '2018-19': 1230, '2019-20': 1059, '2020-21': 1080,
            '2021-22': 1230, '2022-23': 1230, '2023-24': 1230, '2024-25': 1230
        },
        'playoff': {
            '1996-97': 72, '1997-98': 71, '1998-99': 66, '1999-00': 75, '2000-01': 71,
            '2001-02': 71, '2002-03': 88, '2003-04': 82, '2004-05': 84, '2005-06': 89,
            '2006-07': 79, '2007-08': 86, '2008-09': 84, '2009-10': 78, '2010-11': 81,
            '2011-12': 84, '2012-13': 85, '2013-14': 87, '2014-15': 81, '2015-16': 86,
            '2016-17': 79, '2017-18': 82, '2018-19': 82, '2019-20': 83, '2020-21': 85,
            '2021-22': 87, '2022-23': 84, '2023-24': 83, '2024-25': 84
        }
    }

def extract_regular_season_sequence(game_id):
    """Extract sequence number from regular season game ID"""
    if len(game_id) == 10 and game_id.startswith('00') and game_id[4] == '2':
        try:
            return int(game_id[-4:])
        except ValueError:
            return None
    return None

def extract_early_playoff_sequence(game_id):
    """Extract sequence from early playoff game ID (1996-2000)"""
    if len(game_id) == 10 and game_id.startswith('004') and game_id[5:7] == '00':
        try:
            return int(game_id[7:10])
        except ValueError:
            return None
    return None

def parse_modern_playoff_id(game_id):
    """Parse modern playoff game ID (2001+)"""
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

def analyze_regular_season_gaps(conn, season, expected_count):
    """Analyze regular season sequence gaps"""
    result = conn.execute(text("""
        SELECT game_id FROM game_url_queue
        WHERE season = :season AND game_type = 'regular'
        ORDER BY game_id
    """), {"season": season})
    
    sequences = []
    invalid_ids = []
    
    for row in result:
        seq = extract_regular_season_sequence(row.game_id)
        if seq is not None:
            sequences.append(seq)
        else:
            invalid_ids.append(row.game_id)
    
    if not sequences:
        return {
            'type': 'no_valid_sequences',
            'total_games': len(invalid_ids),
            'expected': expected_count,
            'gap': len(invalid_ids) - expected_count,
            'issues': ['All game IDs have invalid format']
        }
    
    sequences.sort()
    min_seq = sequences[0]
    max_seq = sequences[-1]
    actual_sequences = set(sequences)
    expected_sequences = set(range(1, expected_count + 1))
    
    missing_sequences = expected_sequences - actual_sequences
    extra_sequences = actual_sequences - expected_sequences
    
    issues = []
    if invalid_ids:
        issues.append(f"{len(invalid_ids)} invalid game IDs")
    if missing_sequences:
        issues.append(f"{len(missing_sequences)} missing sequences")
    if extra_sequences:
        issues.append(f"{len(extra_sequences)} extra sequences")
    if min_seq != 1:
        issues.append(f"Sequences start at {min_seq} instead of 1")
    if max_seq != expected_count:
        issues.append(f"Sequences end at {max_seq} instead of {expected_count}")
    
    return {
        'type': 'regular_season',
        'total_games': len(sequences),
        'expected': expected_count,
        'gap': len(sequences) - expected_count,
        'sequence_range': (min_seq, max_seq),
        'missing_sequences': sorted(missing_sequences) if missing_sequences else [],
        'extra_sequences': sorted(extra_sequences) if extra_sequences else [],
        'invalid_ids': invalid_ids,
        'issues': issues
    }

def analyze_early_playoff_gaps(conn, season, expected_count):
    """Analyze early playoff sequence gaps (1996-2000)"""
    result = conn.execute(text("""
        SELECT game_id FROM game_url_queue
        WHERE season = :season AND game_type = 'playoff'
        ORDER BY game_id
    """), {"season": season})
    
    sequences = []
    invalid_ids = []
    
    for row in result:
        seq = extract_early_playoff_sequence(row.game_id)
        if seq is not None:
            sequences.append(seq)
        else:
            invalid_ids.append(row.game_id)
    
    if not sequences:
        return {
            'type': 'no_valid_sequences',
            'total_games': len(invalid_ids),
            'expected': expected_count,
            'gap': len(invalid_ids) - expected_count,
            'issues': ['All game IDs have invalid format']
        }
    
    sequences.sort()
    min_seq = sequences[0]
    max_seq = sequences[-1]
    
    # For early playoffs, we expect the exact number of games but with gaps in numbering
    issues = []
    if len(sequences) != expected_count:
        issues.append(f"Have {len(sequences)} games, expected {expected_count}")
    
    if invalid_ids:
        issues.append(f"{len(invalid_ids)} invalid game IDs")
    
    # Calculate theoretical missing sequences (gaps in the range)
    full_range = set(range(min_seq, max_seq + 1))
    actual_sequences = set(sequences)
    missing_in_range = full_range - actual_sequences
    
    return {
        'type': 'early_playoff',
        'total_games': len(sequences),
        'expected': expected_count,
        'gap': len(sequences) - expected_count,
        'sequence_range': (min_seq, max_seq),
        'missing_in_range': sorted(missing_in_range) if missing_in_range else [],
        'invalid_ids': invalid_ids,
        'issues': issues,
        'note': 'Early playoffs use sparse sequential numbering - gaps are expected'
    }

def analyze_modern_playoff_structure(conn, season, expected_count):
    """Analyze modern playoff structure (2001+)"""
    result = conn.execute(text("""
        SELECT game_id FROM game_url_queue
        WHERE season = :season AND game_type = 'playoff'
        ORDER BY game_id
    """), {"season": season})
    
    parsed_games = []
    invalid_ids = []
    
    for row in result:
        parsed = parse_modern_playoff_id(row.game_id)
        if parsed:
            parsed_games.append(parsed)
        else:
            invalid_ids.append(row.game_id)
    
    if not parsed_games:
        return {
            'type': 'no_valid_sequences',
            'total_games': len(invalid_ids),
            'expected': expected_count,
            'gap': len(invalid_ids) - expected_count,
            'issues': ['All game IDs have invalid format']
        }
    
    # Group by round
    rounds = defaultdict(lambda: defaultdict(set))
    for parsed in parsed_games:
        rounds[parsed['round']][parsed['series']].add(parsed['game'])
    
    issues = []
    if len(parsed_games) != expected_count:
        issues.append(f"Have {len(parsed_games)} games, expected {expected_count}")
    
    # Expected series counts per round
    expected_series = {0: 8, 1: 4, 2: 2, 3: 1}
    
    # Check structure
    for round_num in range(4):
        if round_num in rounds:
            series_count = len(rounds[round_num])
            expected_series_count = expected_series[round_num]
            
            if series_count > expected_series_count:
                issues.append(f"Round {round_num}: {series_count} series (max {expected_series_count})")
        else:
            # Missing entire round
            if round_num == 0:  # First round is most important
                issues.append(f"Missing entire first round")
    
    if invalid_ids:
        issues.append(f"{len(invalid_ids)} invalid game IDs")
    
    return {
        'type': 'modern_playoff',
        'total_games': len(parsed_games),
        'expected': expected_count,
        'gap': len(parsed_games) - expected_count,
        'rounds_found': len(rounds),
        'invalid_ids': invalid_ids,
        'issues': issues
    }

def main():
    print("COMPREHENSIVE NBA GAME COVERAGE REPORT")
    print("=" * 80)
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://brendan@localhost:5432/nba_pbp')
    engine = create_engine(db_url)
    expected_counts = get_expected_counts()
    
    # Summary statistics
    total_gaps = {'regular': 0, 'early_playoff': 0, 'modern_playoff': 0}
    seasons_with_gaps = {'regular': 0, 'early_playoff': 0, 'modern_playoff': 0}
    critical_gaps = []  # Gaps of 10+ games
    
    with engine.connect() as conn:
        # Analyze regular season coverage
        print("\n🏀 REGULAR SEASON COVERAGE ANALYSIS")
        print("=" * 60)
        
        for season in sorted(expected_counts['regular'].keys()):
            if season == '2024-25':  # Skip current season
                continue
                
            expected = expected_counts['regular'][season]
            analysis = analyze_regular_season_gaps(conn, season, expected)
            
            gap = analysis['gap']
            total_gaps['regular'] += abs(gap)
            
            if gap != 0:
                seasons_with_gaps['regular'] += 1
                
            if abs(gap) >= 10:
                critical_gaps.append(f"Regular {season}: {gap:+d}")
            
            # Print summary for seasons with issues
            if analysis['issues']:
                status = "❌" if abs(gap) >= 10 else "⚠️" if gap != 0 else "✅"
                print(f"{status} {season}: {analysis['total_games']}/{expected} ({gap:+d}) - {', '.join(analysis['issues'][:2])}")
        
        # Analyze early playoff coverage (1996-2000)
        print(f"\n🏆 EARLY PLAYOFF COVERAGE ANALYSIS (1996-2000)")
        print("=" * 60)
        
        for season in ['1996-97', '1997-98', '1998-99', '1999-00']:
            expected = expected_counts['playoff'][season]
            analysis = analyze_early_playoff_gaps(conn, season, expected)
            
            gap = analysis['gap']
            total_gaps['early_playoff'] += abs(gap)
            
            if gap != 0:
                seasons_with_gaps['early_playoff'] += 1
            
            if abs(gap) >= 5:
                critical_gaps.append(f"Early Playoff {season}: {gap:+d}")
            
            status = "❌" if abs(gap) >= 5 else "⚠️" if gap != 0 else "✅"
            print(f"{status} {season}: {analysis['total_games']}/{expected} ({gap:+d})")
            
            if 'missing_in_range' in analysis and analysis['missing_in_range']:
                print(f"    Gaps in sequence: {len(analysis['missing_in_range'])} (normal for early playoffs)")
        
        # Analyze modern playoff coverage (2001+)
        print(f"\n🏆 MODERN PLAYOFF COVERAGE ANALYSIS (2001+)")
        print("=" * 60)
        
        modern_playoff_seasons = [s for s in expected_counts['playoff'].keys() if s not in ['1996-97', '1997-98', '1998-99', '1999-00'] and s != '2024-25']
        
        for season in sorted(modern_playoff_seasons):
            expected = expected_counts['playoff'][season]
            analysis = analyze_modern_playoff_structure(conn, season, expected)
            
            gap = analysis['gap']
            total_gaps['modern_playoff'] += abs(gap)
            
            if gap != 0:
                seasons_with_gaps['modern_playoff'] += 1
            
            if abs(gap) >= 5:
                critical_gaps.append(f"Modern Playoff {season}: {gap:+d}")
            
            # Only show seasons with issues
            if analysis['issues']:
                status = "❌" if abs(gap) >= 5 else "⚠️" if gap != 0 else "✅"
                print(f"{status} {season}: {analysis['total_games']}/{expected} ({gap:+d}) - {', '.join(analysis['issues'][:2])}")
        
        # Overall summary
        print(f"\n" + "=" * 80)
        print("📊 COMPREHENSIVE COVERAGE SUMMARY")
        print("=" * 80)
        
        total_seasons = len(expected_counts['regular']) + len(expected_counts['playoff']) - 2  # Exclude 2024-25
        total_seasons_with_gaps = sum(seasons_with_gaps.values())
        total_all_gaps = sum(total_gaps.values())
        
        print(f"Total seasons analyzed: {total_seasons}")
        print(f"Seasons with perfect coverage: {total_seasons - total_seasons_with_gaps}")
        print(f"Seasons with gaps: {total_seasons_with_gaps}")
        print(f"Total games missing/extra: {total_all_gaps}")
        
        print(f"\nBY GAME TYPE:")
        print(f"Regular Season: {seasons_with_gaps['regular']} seasons with gaps, {total_gaps['regular']} total gap")
        print(f"Early Playoffs:  {seasons_with_gaps['early_playoff']} seasons with gaps, {total_gaps['early_playoff']} total gap")  
        print(f"Modern Playoffs: {seasons_with_gaps['modern_playoff']} seasons with gaps, {total_gaps['modern_playoff']} total gap")
        
        if critical_gaps:
            print(f"\n🚨 CRITICAL GAPS (10+ games):")
            for gap in critical_gaps:
                print(f"   {gap}")
        
        print(f"\n📋 PRIORITY RECOMMENDATIONS:")
        print("1. Focus on critical regular season gaps (10+ missing games)")
        print("2. Early playoff gaps are mostly due to sparse numbering (acceptable)")
        print("3. Modern playoff gaps need structural analysis")
        print("4. Consider adjusting expected counts based on actual NBA schedules")
        
        # Top gap seasons for follow-up
        print(f"\n🎯 TOP SEASONS FOR IMMEDIATE ATTENTION:")
        
        # Get worst regular season gaps
        worst_regular = []
        for season in expected_counts['regular'].keys():
            if season == '2024-25':
                continue
            analysis = analyze_regular_season_gaps(conn, season, expected_counts['regular'][season])
            if abs(analysis['gap']) >= 5:
                worst_regular.append((season, analysis['gap']))
        
        worst_regular.sort(key=lambda x: abs(x[1]), reverse=True)
        
        for i, (season, gap) in enumerate(worst_regular[:5]):
            print(f"{i+1}. {season} Regular Season: {gap:+d} games")

if __name__ == "__main__":
    main()