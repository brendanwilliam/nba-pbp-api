#!/usr/bin/env python3
"""
Verify data coverage by checking for gaps in game ID sequences
Regular season games follow sequential patterns: 00{season}2{sequence}
where sequence goes from 0001 to the total number of games that season
"""

import os
from sqlalchemy import create_engine, text
from collections import defaultdict

def get_expected_regular_season_counts():
    """Expected regular season game counts by season"""
    return {
        '1996-97': 1189, '1997-98': 1189, '1998-99': 725, '1999-00': 1189, '2000-01': 1189,
        '2001-02': 1189, '2002-03': 1189, '2003-04': 1189, '2004-05': 1230, '2005-06': 1230,
        '2006-07': 1230, '2007-08': 1230, '2008-09': 1230, '2009-10': 1230, '2010-11': 1230,
        '2011-12': 990, '2012-13': 1229, '2013-14': 1230, '2014-15': 1230, '2015-16': 1230,
        '2016-17': 1230, '2017-18': 1230, '2018-19': 1230, '2019-20': 1059, '2020-21': 1080,
        '2021-22': 1230, '2022-23': 1230, '2023-24': 1230
    }

def extract_game_sequence(game_id, game_type):
    """Extract sequence number from game ID"""
    if len(game_id) != 10:
        return None
    
    if game_type == 'regular':
        # Regular season: 00{YY}{game_type}{NNNN} where NNNN is sequence 0001-1230
        # For regular season games, check if it follows the pattern
        if game_id.startswith('00') and len(game_id) == 10:
            # Extract the last 4 digits as sequence number
            try:
                # The sequence is always the last 4 digits
                return int(game_id[-4:])
            except ValueError:
                return None
    elif game_type == 'playoff':
        # Playoffs use different schema, skip sequence analysis
        return None
    elif game_type == 'playin':
        # Play-in games use different schema, skip sequence analysis  
        return None
    
    return None

def main():
    print("Game ID Sequence Coverage Verification")
    print("=" * 80)
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://brendan@localhost:5432/nba_pbp')
    engine = create_engine(db_url)
    
    expected_counts = get_expected_regular_season_counts()
    
    with engine.connect() as conn:
        # Get all regular season games with their game IDs
        result = conn.execute(text("""
            SELECT 
                season,
                game_id,
                game_type,
                game_date,
                home_team,
                away_team
            FROM game_url_queue
            WHERE game_type = 'regular'
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
        
        print("REGULAR SEASON GAME ID SEQUENCE ANALYSIS")
        print("=" * 80)
        
        total_gaps_found = 0
        total_seasons_with_gaps = 0
        
        for season in sorted(season_data.keys()):
            games = season_data[season]
            expected_count = expected_counts.get(season, 0)
            
            print(f"\nSEASON: {season}")
            print(f"Expected games: {expected_count}")
            print(f"Games in queue: {len(games)}")
            
            if expected_count == 0:
                print("  ⚠️  No expected count available for this season")
                continue
            
            # Extract sequence numbers
            sequences = []
            invalid_ids = []
            
            for game in games:
                seq = extract_game_sequence(game['game_id'], game['game_type'])
                if seq is not None:
                    sequences.append((seq, game))
                else:
                    invalid_ids.append(game['game_id'])
            
            sequences.sort(key=lambda x: x[0])
            
            if invalid_ids:
                print(f"  ⚠️  {len(invalid_ids)} invalid game IDs found:")
                for game_id in invalid_ids[:5]:  # Show first 5
                    print(f"    {game_id}")
                if len(invalid_ids) > 5:
                    print(f"    ... and {len(invalid_ids) - 5} more")
            
            # Check for sequence gaps
            if sequences:
                min_seq = sequences[0][0]
                max_seq = sequences[-1][0]
                actual_sequences = set(seq for seq, _ in sequences)
                expected_sequences = set(range(1, expected_count + 1))
                
                print(f"  Sequence range: {min_seq} to {max_seq}")
                print(f"  Expected range: 1 to {expected_count}")
                
                # Find missing sequences
                missing_sequences = expected_sequences - actual_sequences
                extra_sequences = actual_sequences - expected_sequences
                
                if missing_sequences:
                    total_gaps_found += len(missing_sequences)
                    total_seasons_with_gaps += 1
                    print(f"  ❌ Missing sequences: {len(missing_sequences)}")
                    
                    # Show missing ranges
                    missing_list = sorted(missing_sequences)
                    ranges = []
                    start = missing_list[0]
                    end = start
                    
                    for seq in missing_list[1:]:
                        if seq == end + 1:
                            end = seq
                        else:
                            if start == end:
                                ranges.append(str(start))
                            else:
                                ranges.append(f"{start}-{end}")
                            start = end = seq
                    
                    if start == end:
                        ranges.append(str(start))
                    else:
                        ranges.append(f"{start}-{end}")
                    
                    print(f"    Missing: {', '.join(ranges[:10])}")
                    if len(ranges) > 10:
                        print(f"    ... and {len(ranges) - 10} more ranges")
                
                if extra_sequences:
                    print(f"  ⚠️  Extra sequences beyond expected range: {len(extra_sequences)}")
                    extra_list = sorted(extra_sequences)[:10]
                    print(f"    Extra: {', '.join(map(str, extra_list))}")
                    if len(extra_sequences) > 10:
                        print(f"    ... and {len(extra_sequences) - 10} more")
                
                if not missing_sequences and not extra_sequences:
                    print(f"  ✅ Perfect sequence coverage (1-{expected_count})")
                
                # Check for duplicate sequences
                seq_counts = defaultdict(int)
                for seq, _ in sequences:
                    seq_counts[seq] += 1
                
                duplicates = {seq: count for seq, count in seq_counts.items() if count > 1}
                if duplicates:
                    print(f"  ⚠️  Duplicate sequences found: {len(duplicates)}")
                    for seq, count in sorted(duplicates.items())[:5]:
                        print(f"    Sequence {seq}: {count} occurrences")
            else:
                print(f"  ❌ No valid sequence numbers found")
        
        # Summary
        print(f"\n" + "=" * 80)
        print("SEQUENCE COVERAGE SUMMARY")
        print("=" * 80)
        
        total_seasons = len([s for s in season_data.keys() if s in expected_counts])
        print(f"Seasons analyzed: {total_seasons}")
        print(f"Seasons with perfect coverage: {total_seasons - total_seasons_with_gaps}")
        print(f"Seasons with gaps: {total_seasons_with_gaps}")
        print(f"Total missing sequences: {total_gaps_found}")
        
        if total_gaps_found > 0:
            print(f"\n📋 RECOMMENDATIONS:")
            print("1. Investigate seasons with missing sequences")
            print("2. Check if missing game IDs exist on NBA.com")
            print("3. Verify expected game counts are accurate")
            print("4. Consider that some sequences may be intentionally skipped")
        
        # Additional analysis: check for non-sequential patterns
        print(f"\n" + "=" * 80)
        print("PATTERN ANALYSIS")
        print("=" * 80)
        
        # Check for seasons with unusual patterns
        for season in sorted(season_data.keys()):
            if season not in expected_counts:
                continue
                
            games = season_data[season]
            sequences = []
            
            for game in games:
                seq = extract_game_sequence(game['game_id'], game['game_type'])
                if seq is not None:
                    sequences.append(seq)
            
            if sequences:
                sequences.sort()
                expected_count = expected_counts[season]
                
                # Check if sequences start from 1
                if sequences[0] != 1:
                    print(f"{season}: Sequences start from {sequences[0]} (expected 1)")
                
                # Check if sequences end at expected count
                if sequences[-1] != expected_count:
                    print(f"{season}: Sequences end at {sequences[-1]} (expected {expected_count})")
                
                # Check for large gaps
                large_gaps = []
                for i in range(len(sequences) - 1):
                    gap = sequences[i + 1] - sequences[i]
                    if gap > 10:  # Gap of more than 10 sequences
                        large_gaps.append((sequences[i], sequences[i + 1], gap - 1))
                
                if large_gaps:
                    print(f"{season}: Large gaps found:")
                    for start, end, gap_size in large_gaps:
                        print(f"  Gap of {gap_size} between {start} and {end}")

if __name__ == "__main__":
    main()