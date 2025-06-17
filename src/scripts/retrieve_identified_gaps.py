#!/usr/bin/env python3
"""
Retrieve specific missing game sequences identified in gap analysis
"""

import os
import requests
import time
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

def construct_game_id(season, sequence):
    """Construct game ID from season and sequence number"""
    year_code = season.split('-')[1]
    return f"00{year_code}2{sequence:04d}"

def validate_nba_url(url):
    """Validate if NBA URL exists and contains game data"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        
        if response.status_code == 200:
            content = response.text.lower()
            if any(indicator in content for indicator in [
                '__next_data__', 'gamedata', 'boxscore', 'play-by-play', 'game_id'
            ]):
                return True, "Valid game page with data"
            else:
                return False, "Page exists but no game data found"
        elif response.status_code == 404:
            return False, "Game not found (404)"
        else:
            return False, f"HTTP {response.status_code}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"

def get_nba_teams():
    """Get NBA team abbreviations"""
    return [
        'ATL', 'BOS', 'BRK', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
        'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
        'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
    ]

def discover_teams_for_game_id(game_id, max_attempts=15):
    """Try to discover which teams played for a given game ID"""
    teams = get_nba_teams()
    
    print(f"    Discovering teams for {game_id}...")
    attempts = 0
    
    # Try common matchups first, then random combinations
    common_pairs = [
        ('LAL', 'BOS'), ('GSW', 'LAL'), ('MIA', 'BOS'), ('CHI', 'DET'),
        ('NYK', 'BRK'), ('LAL', 'LAC'), ('MIA', 'NYK'), ('BOS', 'PHI'),
        ('GSW', 'LAC'), ('SAS', 'LAL'), ('TOR', 'BOS'), ('PHI', 'NYK'),
        ('DEN', 'LAL'), ('MIL', 'BOS'), ('PHX', 'LAL')
    ]
    
    # First try common matchups
    for away, home in common_pairs:
        if attempts >= max_attempts:
            break
            
        url = f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{game_id}"
        is_valid, message = validate_nba_url(url)
        attempts += 1
        
        if is_valid:
            print(f"    ✓ Found: {away} @ {home}")
            return {'home_team': home, 'away_team': away, 'url': url}
        
        time.sleep(0.2)
    
    # Try reverse of common matchups
    for home, away in common_pairs:
        if attempts >= max_attempts:
            break
            
        url = f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{game_id}"
        is_valid, message = validate_nba_url(url)
        attempts += 1
        
        if is_valid:
            print(f"    ✓ Found: {away} @ {home}")
            return {'home_team': home, 'away_team': away, 'url': url}
        
        time.sleep(0.2)
    
    print(f"    ✗ No valid teams found after {attempts} attempts")
    return None

def main():
    print("Retrieving Identified Regular Season Gaps")
    print("=" * 80)
    
    # Exact missing sequences identified from gap analysis
    gap_data = {
        '1997-98': {
            'missing_sequences': list(range(6, 15)),  # 6-14 (we already have 1-5)
            'priority': 'high'
        },
        '2006-07': {
            'missing_sequences': list(range(151, 158)),  # 151-157
            'priority': 'medium'
        },
        '2012-13': {
            'missing_sequences': list(range(535, 541)) + [1214],  # 535-540, 1214 (we have 530-534)
            'priority': 'critical'
        },
        '2014-15': {
            'missing_sequences': list(range(765, 774)),  # 765-773
            'priority': 'medium'
        },
        '2016-17': {
            'missing_sequences': list(range(1222, 1231)),  # 1222-1230 (we have 1217-1221)
            'priority': 'medium'
        },
        '2017-18': {
            'missing_sequences': list(range(701, 710)),  # 701-709
            'priority': 'medium'
        }
    }
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://brendan@localhost:5432/nba_pbp')
    engine = create_engine(db_url)
    
    total_attempted = 0
    total_found = 0
    total_added = 0
    
    # Sort by priority
    priority_order = {'critical': 1, 'high': 2, 'medium': 3}
    sorted_seasons = sorted(gap_data.items(), key=lambda x: priority_order[x[1]['priority']])
    
    with engine.connect() as conn:
        for season, data in sorted_seasons:
            sequences = data['missing_sequences']
            priority = data['priority']
            
            print(f"\n{'🚨' if priority == 'critical' else '⚠️'} {season} ({priority.upper()} PRIORITY)")
            print(f"Missing sequences: {len(sequences)}")
            print("-" * 60)
            
            for i, sequence in enumerate(sequences):
                game_id = construct_game_id(season, sequence)
                print(f"\n  {i+1}/{len(sequences)}. Sequence {sequence} → Game ID: {game_id}")
                
                # Check if already exists
                result = conn.execute(text("""
                    SELECT COUNT(*) as existing 
                    FROM game_url_queue 
                    WHERE game_id = :game_id
                """), {"game_id": game_id})
                
                if result.fetchone().existing > 0:
                    print(f"    ✓ Already in database")
                    continue
                
                total_attempted += 1
                
                # Try to discover the teams
                game_info = discover_teams_for_game_id(game_id)
                
                if game_info:
                    total_found += 1
                    
                    # Estimate game date based on sequence and season
                    season_start_year = int(season.split('-')[0])
                    
                    # More accurate date estimation based on sequence position
                    # Regular season ~1230 games from October to April (6 months = ~180 days)
                    base_date = datetime(season_start_year, 10, 15)
                    days_offset = int((sequence / 1230) * 180)
                    estimated_date = base_date + timedelta(days=days_offset)
                    
                    print(f"    Adding to database (estimated date: {estimated_date.date()})...")
                    
                    try:
                        conn.execute(text("""
                            INSERT INTO game_url_queue (
                                game_id, season, game_date, home_team, away_team,
                                game_type, game_url, status, created_at, updated_at
                            ) VALUES (
                                :game_id, :season, :game_date, :home_team, :away_team,
                                'regular', :game_url, 'pending', NOW(), NOW()
                            )
                            ON CONFLICT (game_id) DO NOTHING
                        """), {
                            "game_id": game_id,
                            "season": season,
                            "game_date": estimated_date.date(),
                            "home_team": game_info['home_team'],
                            "away_team": game_info['away_team'],
                            "game_url": game_info['url']
                        })
                        
                        conn.commit()
                        total_added += 1
                        print(f"    ✅ Successfully added")
                        
                    except Exception as e:
                        print(f"    ❌ Error adding to database: {e}")
                        conn.rollback()
                else:
                    print(f"    ❌ Could not find valid game")
                
                # Rate limiting
                time.sleep(0.8)
                
                # Continue with all sequences
                # Removed testing limit - now processing all missing sequences
    
    print(f"\n" + "=" * 80)
    print("GAP RETRIEVAL SUMMARY")
    print("=" * 80)
    print(f"Game IDs attempted: {total_attempted}")
    print(f"Valid games found: {total_found}")
    print(f"Games added to database: {total_added}")
    
    if total_added > 0:
        print(f"\n✅ SUCCESS: Added {total_added} missing games!")
        print("\nNext steps:")
        print("1. Re-run sequence verification to see updated gaps")
        print("2. Remove the testing limit to retrieve all missing games") 
        print("3. Validate the newly added URLs")
        print("4. Run mass scraping on these games")
    else:
        print(f"\n❌ No games were successfully added.")
        print("This suggests these sequence numbers may not correspond to real games.")
    
    # Show what gaps remain
    print(f"\n📊 REMAINING WORK:")
    for season, data in gap_data.items():
        remaining = len(data['missing_sequences']) - 3  # We only tried 3 per season
        if remaining > 0:
            print(f"   {season}: {remaining} more sequences to try")

if __name__ == "__main__":
    main()