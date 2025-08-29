#!/usr/bin/env python3
"""
Tests for database population validation against CSV data.

This module tests that the database contains the correct number of unique game_ids
for each season and game_type according to the CSV reference data.
"""

import pytest
import pandas as pd
import os
from pathlib import Path
from typing import Dict, Tuple

from src.database.services import DatabaseConnection
from src.database.models import RawGameData

# Configuration for test thresholds
MIN_COMPLETENESS_THRESHOLD = float(os.getenv('DB_TEST_MIN_COMPLETENESS', '0.0'))  # 0% = any data ok
MAX_COMPLETENESS_THRESHOLD = float(os.getenv('DB_TEST_MAX_COMPLETENESS', '110.0'))  # 110% = allow some over


@pytest.mark.skip(reason="Requires populated WNBA database - integration test, not unit test")
class TestDatabasePopulation:
    """Test database population against CSV reference data."""

    @pytest.fixture(scope="class")
    def csv_data(self):
        """Load CSV reference data for validation."""
        base_path = Path(__file__).parent.parent / "src" / "scrapers"
        
        regular_csv = pd.read_csv(base_path / "wnba-games-regular.csv")
        playoff_csv = pd.read_csv(base_path / "wnba-games-playoff.csv")
        
        return {
            "regular": regular_csv,
            "playoff": playoff_csv
        }

    @pytest.fixture(scope="class")
    def db_connection(self):
        """Database connection for tests."""
        return DatabaseConnection()

    def get_expected_counts_from_csv(self, csv_data: Dict[str, pd.DataFrame]) -> Dict[Tuple[int, str], int]:
        """Extract expected game counts by season and type from CSV data."""
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

    def get_actual_counts_from_db(self, db_connection: DatabaseConnection) -> Dict[Tuple[int, str], int]:
        """Get actual game counts by season and type from database."""
        with db_connection.get_session() as session:
            # Query for unique game_ids grouped by season and game_type
            query = session.query(
                RawGameData.season,
                RawGameData.game_type,
                RawGameData.game_id
            ).distinct()
            
            results = query.all()
            
            # Count unique game_ids per season/type combination
            actual_counts = {}
            for season, game_type, game_id in results:
                key = (int(season), game_type.lower())
                actual_counts[key] = actual_counts.get(key, 0) + 1
        
        return actual_counts

    def test_database_population_within_thresholds(self, csv_data, db_connection):
        """Test that database game counts are within acceptable thresholds."""
        expected_counts = self.get_expected_counts_from_csv(csv_data)
        actual_counts = self.get_actual_counts_from_db(db_connection)
        
        # Check each expected season/type combination
        below_threshold = []
        above_threshold = []
        completeness_report = []
        
        for (season, game_type), expected_count in expected_counts.items():
            actual_count = actual_counts.get((season, game_type), 0)
            completeness_pct = (actual_count / expected_count) * 100 if expected_count > 0 else 0
            
            completeness_report.append(f"{season} {game_type}: {actual_count}/{expected_count} ({completeness_pct:.1f}%)")
            
            if completeness_pct < MIN_COMPLETENESS_THRESHOLD:
                below_threshold.append(f"{season} {game_type}: {completeness_pct:.1f}% < {MIN_COMPLETENESS_THRESHOLD}%")
            elif completeness_pct > MAX_COMPLETENESS_THRESHOLD:
                above_threshold.append(f"{season} {game_type}: {completeness_pct:.1f}% > {MAX_COMPLETENESS_THRESHOLD}%")
        
        # Print completeness report for visibility
        print(f"\n=== Database Completeness Report ===")
        print(f"Thresholds: {MIN_COMPLETENESS_THRESHOLD}% - {MAX_COMPLETENESS_THRESHOLD}%")
        for report in sorted(completeness_report):
            print(report)
        
        # Report threshold violations
        if below_threshold:
            pytest.fail(f"Below minimum threshold: {'; '.join(below_threshold)}")
        
        if above_threshold:
            pytest.fail(f"Above maximum threshold: {'; '.join(above_threshold)}")

    def test_database_population_exact_match(self, csv_data, db_connection):
        """Test for exact match - only run when environment configured for strict validation."""
        if os.getenv('DB_TEST_STRICT_MODE', 'false').lower() != 'true':
            pytest.skip("Strict mode not enabled (set DB_TEST_STRICT_MODE=true)")
        
        expected_counts = self.get_expected_counts_from_csv(csv_data)
        actual_counts = self.get_actual_counts_from_db(db_connection)
        
        mismatches = []
        for (season, game_type), expected_count in expected_counts.items():
            actual_count = actual_counts.get((season, game_type), 0)
            if actual_count != expected_count:
                mismatches.append(f"{season} {game_type}: expected {expected_count}, got {actual_count}")
        
        if mismatches:
            pytest.fail(f"Exact count mismatches: {'; '.join(mismatches)}")

    def test_no_extra_games_in_database(self, csv_data, db_connection):
        """Test that database doesn't contain games not accounted for in CSV."""
        expected_counts = self.get_expected_counts_from_csv(csv_data)
        actual_counts = self.get_actual_counts_from_db(db_connection)
        
        # Check for any season/type combinations in DB that aren't in CSV
        extra_combinations = []
        for (season, game_type), actual_count in actual_counts.items():
            if (season, game_type) not in expected_counts:
                extra_combinations.append(f"{season} {game_type}: {actual_count} games")
        
        if extra_combinations:
            pytest.fail(f"Extra game combinations in database: {'; '.join(extra_combinations)}")

    def test_unique_game_ids_per_season_type(self, db_connection):
        """Test that all game_ids are unique within each season/type combination."""
        with db_connection.get_session() as session:
            # Query for potential duplicates
            query = session.query(
                RawGameData.season,
                RawGameData.game_type,
                RawGameData.game_id
            )
            
            results = query.all()
            
            # Track game_ids per season/type
            seen_games = {}
            duplicates = []
            
            for season, game_type, game_id in results:
                key = (int(season), game_type.lower())
                if key not in seen_games:
                    seen_games[key] = set()
                
                if game_id in seen_games[key]:
                    duplicates.append(f"{season} {game_type}: duplicate game_id {game_id}")
                else:
                    seen_games[key].add(game_id)
            
            if duplicates:
                pytest.fail(f"Duplicate game_ids found: {'; '.join(duplicates)}")

    def test_season_coverage_completeness(self, csv_data, db_connection):
        """Test that all seasons from CSV are represented in database."""
        expected_seasons = set()
        
        # Collect all seasons from CSV files
        for _, row in csv_data["regular"].iterrows():
            expected_seasons.add(int(row["season"]))
        
        for _, row in csv_data["playoff"].iterrows():
            expected_seasons.add(int(row["season"]))
        
        # Get actual seasons from database
        with db_connection.get_session() as session:
            actual_seasons = set()
            results = session.query(RawGameData.season).distinct().all()
            for (season,) in results:
                actual_seasons.add(int(season))
        
        missing_seasons = expected_seasons - actual_seasons
        
        if missing_seasons:
            pytest.fail(f"Missing seasons in database: {sorted(missing_seasons)}")

    @pytest.mark.parametrize("game_type", ["regular", "playoff"])
    def test_game_type_consistency(self, game_type, db_connection):
        """Test that game_type values are consistent (no mixed case, typos, etc.)."""
        with db_connection.get_session() as session:
            # Get all distinct game_type values for this type
            results = session.query(RawGameData.game_type).filter(
                RawGameData.game_type.ilike(f"%{game_type}%")
            ).distinct().all()
            
            game_types = [result[0] for result in results]
            
            # Check for consistency
            expected_value = game_type.lower()
            inconsistent_values = [gt for gt in game_types if gt.lower() != expected_value]
            
            if inconsistent_values:
                pytest.fail(
                    f"Inconsistent {game_type} game_type values: {inconsistent_values}. "
                    f"Expected: '{expected_value}'"
                )


@pytest.mark.skip(reason="Requires populated WNBA database - integration test, not unit test")  
class TestDatabasePopulationReporting:
    """Additional tests for reporting database population statistics."""

    @pytest.fixture(scope="class")
    def db_connection(self):
        """Database connection for tests."""
        return DatabaseConnection()

    def test_print_population_summary(self, db_connection):
        """Print a summary of current database population for manual review."""
        with db_connection.get_session() as session:
            # Get counts by season and type
            query = session.query(
                RawGameData.season,
                RawGameData.game_type,
                RawGameData.game_id
            ).distinct()
            
            results = query.all()
            
            # Organize data
            summary = {}
            for season, game_type, game_id in results:
                key = (int(season), game_type.lower())
                summary[key] = summary.get(key, 0) + 1
            
            # Print summary
            print("\n=== Database Population Summary ===")
            for (season, game_type), count in sorted(summary.items()):
                print(f"{season} {game_type}: {count} games")
            
            total_games = sum(summary.values())
            print(f"\nTotal unique games: {total_games}")
            
            # This test always passes - it's just for reporting
            assert True