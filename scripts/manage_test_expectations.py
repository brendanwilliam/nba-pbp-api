#!/usr/bin/env python3
"""
Utility for managing database population test expectations.

This script helps update test thresholds and provides reporting on current
database population status relative to CSV expectations.
"""

import os
import sys
import argparse
import pandas as pd
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.services import DatabaseConnection
from database.models import RawGameData


def load_csv_data():
    """Load CSV reference data."""
    base_path = Path(__file__).parent.parent / "src" / "scrapers"
    
    regular_csv = pd.read_csv(base_path / "wnba-games-regular.csv")
    playoff_csv = pd.read_csv(base_path / "wnba-games-playoff.csv")
    
    return {"regular": regular_csv, "playoff": playoff_csv}


def get_expected_counts(csv_data):
    """Extract expected game counts from CSV data."""
    expected_counts = {}
    
    # Regular season games
    for _, row in csv_data["regular"].iterrows():
        season = int(row["season"])
        total_games = int(row["total_regular_games"])
        expected_counts[(season, "regular")] = total_games
    
    # Playoff games
    for _, row in csv_data["playoff"].iterrows():
        season = int(row["season"])
        total_games = int(row["total_games"])
        expected_counts[(season, "playoff")] = total_games
    
    return expected_counts


def get_actual_counts():
    """Get actual game counts from database."""
    db_conn = DatabaseConnection()
    with db_conn.get_session() as session:
        query = session.query(
            RawGameData.season,
            RawGameData.game_type,
            RawGameData.game_id
        ).distinct()
        
        results = query.all()
        
        actual_counts = {}
        for season, game_type, game_id in results:
            key = (int(season), game_type.lower())
            actual_counts[key] = actual_counts.get(key, 0) + 1
    
    return actual_counts


def generate_report():
    """Generate detailed population report."""
    print("=== Database Population Report ===\n")
    
    csv_data = load_csv_data()
    expected_counts = get_expected_counts(csv_data)
    actual_counts = get_actual_counts()
    
    # Calculate overall statistics
    total_expected = sum(expected_counts.values())
    total_actual = sum(actual_counts.values())
    overall_completeness = (total_actual / total_expected * 100) if total_expected > 0 else 0
    
    print(f"Overall: {total_actual}/{total_expected} games ({overall_completeness:.1f}%)\n")
    
    # Detailed breakdown
    print("Season/Type Breakdown:")
    print("-" * 50)
    
    for (season, game_type), expected in sorted(expected_counts.items()):
        actual = actual_counts.get((season, game_type), 0)
        completeness = (actual / expected * 100) if expected > 0 else 0
        status = "✓" if completeness >= 95 else "○" if completeness >= 50 else "✗"
        
        print(f"{status} {season} {game_type:8s}: {actual:3d}/{expected:3d} ({completeness:5.1f}%)")
    
    return overall_completeness


def suggest_thresholds():
    """Suggest appropriate test thresholds based on current data."""
    csv_data = load_csv_data()
    expected_counts = get_expected_counts(csv_data)
    actual_counts = get_actual_counts()
    
    completeness_values = []
    for (season, game_type), expected in expected_counts.items():
        actual = actual_counts.get((season, game_type), 0)
        if expected > 0:
            completeness_values.append((actual / expected) * 100)
    
    if not completeness_values:
        print("No data to analyze for threshold suggestions.")
        return
    
    min_completeness = min(completeness_values)
    max_completeness = max(completeness_values)
    median_completeness = sorted(completeness_values)[len(completeness_values) // 2]
    
    print("\n=== Threshold Suggestions ===")
    print(f"Current range: {min_completeness:.1f}% - {max_completeness:.1f}%")
    print(f"Median: {median_completeness:.1f}%")
    
    # Conservative suggestion (allow current minimum)
    suggested_min = max(0, min_completeness - 5)  # 5% buffer below current min
    suggested_max = max_completeness + 10  # 10% buffer above current max
    
    print(f"\nSuggested thresholds:")
    print(f"  Export DB_TEST_MIN_COMPLETENESS={suggested_min:.1f}")
    print(f"  Export DB_TEST_MAX_COMPLETENESS={suggested_max:.1f}")
    
    # Provide different scenarios
    print(f"\nAlternative configurations:")
    print(f"  Development (lenient): MIN=0.0, MAX=200.0")
    print(f"  CI/Testing (moderate): MIN={median_completeness * 0.8:.1f}, MAX={max_completeness + 5:.1f}")
    print(f"  Production (strict): MIN=95.0, MAX=105.0")


def update_env_file(min_threshold, max_threshold):
    """Update .env file with new thresholds."""
    env_file = Path(__file__).parent.parent / ".env"
    
    lines = []
    updated_min = False
    updated_max = False
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
    
    # Update existing lines or track what needs to be added
    for i, line in enumerate(lines):
        if line.startswith('DB_TEST_MIN_COMPLETENESS='):
            lines[i] = f'DB_TEST_MIN_COMPLETENESS={min_threshold}\n'
            updated_min = True
        elif line.startswith('DB_TEST_MAX_COMPLETENESS='):
            lines[i] = f'DB_TEST_MAX_COMPLETENESS={max_threshold}\n'
            updated_max = True
    
    # Add missing variables
    if not updated_min:
        lines.append(f'DB_TEST_MIN_COMPLETENESS={min_threshold}\n')
    if not updated_max:
        lines.append(f'DB_TEST_MAX_COMPLETENESS={max_threshold}\n')
    
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"Updated {env_file} with thresholds: {min_threshold}% - {max_threshold}%")


def main():
    parser = argparse.ArgumentParser(description="Manage database population test expectations")
    parser.add_argument('action', choices=['report', 'suggest', 'update'], 
                       help='Action to perform')
    parser.add_argument('--min-threshold', type=float, 
                       help='Minimum completeness threshold (for update action)')
    parser.add_argument('--max-threshold', type=float, 
                       help='Maximum completeness threshold (for update action)')
    
    args = parser.parse_args()
    
    try:
        if args.action == 'report':
            generate_report()
        elif args.action == 'suggest':
            generate_report()
            suggest_thresholds()
        elif args.action == 'update':
            if args.min_threshold is None or args.max_threshold is None:
                parser.error("--min-threshold and --max-threshold required for update action")
            update_env_file(args.min_threshold, args.max_threshold)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()