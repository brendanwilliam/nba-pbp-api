#!/usr/bin/env python3
"""
Data Quality Validation Framework for WNBA Game Data
Based on comprehensive JSON structure analysis findings
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, date
import re
from pathlib import Path


@dataclass
class ValidationResult:
    """Container for validation results"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    score: float  # 0-100 quality score


@dataclass
class FieldValidation:
    """Configuration for individual field validation"""
    field_path: str
    required: bool = False
    data_type: Optional[type] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    allowed_values: Optional[Set[str]] = None


class DataQualityValidator:
    """Comprehensive data quality validation for NBA game JSON data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._initialize_validation_rules()

    # TODO: Adjust validation rules for WNBA data values

    def _initialize_validation_rules(self) -> Dict[str, FieldValidation]:
        """Initialize validation rules based on JSON analysis findings"""
        return {
            # Core game fields (required)
            'props.pageProps.game.gameId': FieldValidation(
                'props.pageProps.game.gameId',
                required=True,
                data_type=str,
                pattern=r'^\d{10}$'  # 10-digit game ID
            ),
            'props.pageProps.game.gameCode': FieldValidation(
                'props.pageProps.game.gameCode',
                required=True,
                data_type=str,
                pattern=r'^\d{8}/[A-Z]{6}$'  # YYYYMMDD/TEAMTEAM
            ),
            'props.pageProps.game.gameStatus': FieldValidation(
                'props.pageProps.game.gameStatus',
                required=True,
                data_type=int,
                allowed_values={1, 2, 3}  # scheduled, live, final
            ),
            'props.pageProps.game.homeTeamId': FieldValidation(
                'props.pageProps.game.homeTeamId',
                required=True,
                data_type=int,
                min_value=1610612737,  # minimum NBA team ID
                max_value=1610612766   # maximum NBA team ID (approximate)
            ),
            'props.pageProps.game.awayTeamId': FieldValidation(
                'props.pageProps.game.awayTeamId',
                required=True,
                data_type=int,
                min_value=1610612737,
                max_value=1610612766
            ),

            # Score fields (required for finished games)
            'props.pageProps.game.homeTeam.score': FieldValidation(
                'props.pageProps.game.homeTeam.score',
                required=False,  # Only for finished games
                data_type=int,
                min_value=0,
                max_value=300  # Reasonable upper bound
            ),
            'props.pageProps.game.awayTeam.score': FieldValidation(
                'props.pageProps.game.awayTeam.score',
                required=False,
                data_type=int,
                min_value=0,
                max_value=300
            ),

            # Team information
            'props.pageProps.game.homeTeam.teamTricode': FieldValidation(
                'props.pageProps.game.homeTeam.teamTricode',
                required=True,
                data_type=str,
                pattern=r'^[A-Z]{3}$'
            ),
            'props.pageProps.game.awayTeam.teamTricode': FieldValidation(
                'props.pageProps.game.awayTeam.teamTricode',
                required=True,
                data_type=str,
                pattern=r'^[A-Z]{3}$'
            ),

            # Arena information
            'props.pageProps.game.arena.arenaId': FieldValidation(
                'props.pageProps.game.arena.arenaId',
                required=True,
                data_type=int,
                min_value=1
            ),
            'props.pageProps.game.arena.arenaName': FieldValidation(
                'props.pageProps.game.arena.arenaName',
                required=True,
                data_type=str
            ),

            # Game timing
            'props.pageProps.game.gameTimeUTC': FieldValidation(
                'props.pageProps.game.gameTimeUTC',
                required=True,
                data_type=str,
                pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
            ),
            'props.pageProps.game.period': FieldValidation(
                'props.pageProps.game.period',
                required=False,
                data_type=int,
                min_value=0,
                max_value=10  # Including overtimes
            ),

            # Attendance
            'props.pageProps.game.attendance': FieldValidation(
                'props.pageProps.game.attendance',
                required=False,
                data_type=int,
                min_value=0,
                max_value=30000  # Reasonable upper bound
            ),
        }

    def validate_game_data(self, game_data: Dict[str, Any]) -> ValidationResult:
        """Validate a complete game JSON data structure"""
        errors = []
        warnings = []

        # Check if basic structure exists
        if not self._has_basic_structure(game_data):
            return ValidationResult(
                is_valid=False,
                errors=["Invalid JSON structure: missing props.pageProps.game"],
                warnings=[],
                score=0.0
            )

        # Validate individual fields
        field_errors, field_warnings = self._validate_fields(game_data)
        errors.extend(field_errors)
        warnings.extend(field_warnings)

        # Validate business logic
        logic_errors, logic_warnings = self._validate_business_logic(game_data)
        errors.extend(logic_errors)
        warnings.extend(logic_warnings)

        # Calculate quality score
        quality_score = self._calculate_quality_score(game_data, errors, warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=quality_score
        )

    def _has_basic_structure(self, data: Dict[str, Any]) -> bool:
        """Check if data has the basic NBA.com JSON structure"""
        try:
            return (
                'props' in data and
                'pageProps' in data['props'] and
                'game' in data['props']['pageProps']
            )
        except (KeyError, TypeError):
            return False

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Tuple[Any, bool]:
        """Get value from nested dictionary using dot notation"""
        try:
            keys = path.split('.')
            current = data
            for key in keys:
                current = current[key]
            return current, True
        except (KeyError, TypeError):
            return None, False

    def _validate_fields(self, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate individual fields based on rules"""
        errors = []
        warnings = []

        for field_path, rule in self.validation_rules.items():
            value, exists = self._get_nested_value(data, field_path)

            # Check if required field exists
            if rule.required and not exists:
                errors.append(f"Required field missing: {field_path}")
                continue

            # Skip validation if field doesn't exist and isn't required
            if not exists:
                continue

            # Validate data type
            if rule.data_type and not isinstance(value, rule.data_type):
                # Special handling for numeric types that might be stored as strings
                if rule.data_type in (int, float) and isinstance(value, str):
                    try:
                        if rule.data_type == int:
                            value = int(value)
                        else:
                            value = float(value)
                        warnings.append(f"Field {field_path} converted from string to {rule.data_type.__name__}")
                    except ValueError:
                        errors.append(f"Field {field_path} has invalid type: expected {rule.data_type.__name__}, got {type(value).__name__}")
                        continue
                else:
                    errors.append(f"Field {field_path} has invalid type: expected {rule.data_type.__name__}, got {type(value).__name__}")
                    continue

            # Validate numeric ranges
            if rule.min_value is not None and isinstance(value, (int, float)):
                if value < rule.min_value:
                    errors.append(f"Field {field_path} below minimum: {value} < {rule.min_value}")

            if rule.max_value is not None and isinstance(value, (int, float)):
                if value > rule.max_value:
                    errors.append(f"Field {field_path} above maximum: {value} > {rule.max_value}")

            # Validate patterns
            if rule.pattern and isinstance(value, str):
                if not re.match(rule.pattern, value):
                    errors.append(f"Field {field_path} doesn't match pattern: {value}")

            # Validate allowed values
            if rule.allowed_values and value not in rule.allowed_values:
                errors.append(f"Field {field_path} has invalid value: {value} not in {rule.allowed_values}")

        return errors, warnings

    def _validate_business_logic(self, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate business logic rules"""
        errors = []
        warnings = []

        game = data.get('props', {}).get('pageProps', {}).get('game', {})

        # Validate team IDs are different
        home_team_id, _ = self._get_nested_value(data, 'props.pageProps.game.homeTeamId')
        away_team_id, _ = self._get_nested_value(data, 'props.pageProps.game.awayTeamId')

        if home_team_id and away_team_id and home_team_id == away_team_id:
            errors.append("Home and away teams cannot be the same")

        # Validate scores for finished games
        game_status, _ = self._get_nested_value(data, 'props.pageProps.game.gameStatus')
        if game_status == 3:  # Final game
            home_score, home_exists = self._get_nested_value(data, 'props.pageProps.game.homeTeam.score')
            away_score, away_exists = self._get_nested_value(data, 'props.pageProps.game.awayTeam.score')
            
            if not home_exists or not away_exists:
                errors.append("Final games must have scores for both teams")
            elif home_score == away_score:
                warnings.append("Tied game detected - verify if this includes overtime")

        # Validate player statistics consistency
        self._validate_player_stats_consistency(data, errors, warnings)

        # Validate team statistics consistency
        self._validate_team_stats_consistency(data, errors, warnings)

        return errors, warnings

    def _validate_player_stats_consistency(self, data: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate consistency in player statistics"""
        game = data.get('props', {}).get('pageProps', {}).get('game', {})

        for team_type in ['homeTeam', 'awayTeam']:
            team_data = game.get(team_type, {})
            players = team_data.get('players', [])

            for i, player in enumerate(players):
                # Validate field goal consistency
                fgm = player.get('statistics', {}).get('fieldGoalsMade', 0)
                fga = player.get('statistics', {}).get('fieldGoalsAttempted', 0)

                if fgm > fga:
                    errors.append(f"{team_type} player {i}: FGM ({fgm}) cannot exceed FGA ({fga})")

                # Validate three-pointer consistency
                fg3m = player.get('statistics', {}).get('threePointersMade', 0)
                fg3a = player.get('statistics', {}).get('threePointersAttempted', 0)

                if fg3m > fg3a:
                    errors.append(f"{team_type} player {i}: 3PM ({fg3m}) cannot exceed 3PA ({fg3a})")

                if fg3m > fgm:
                    errors.append(f"{team_type} player {i}: 3PM ({fg3m}) cannot exceed FGM ({fgm})")

                # Validate free throw consistency
                ftm = player.get('statistics', {}).get('freeThrowsMade', 0)
                fta = player.get('statistics', {}).get('freeThrowsAttempted', 0)

                if ftm > fta:
                    errors.append(f"{team_type} player {i}: FTM ({ftm}) cannot exceed FTA ({fta})")

                # Validate rebound consistency
                oreb = player.get('statistics', {}).get('reboundsOffensive', 0)
                dreb = player.get('statistics', {}).get('reboundsDefensive', 0)
                total_reb = player.get('statistics', {}).get('reboundsTotal', 0)

                if oreb + dreb != total_reb and total_reb != 0:
                    warnings.append(f"{team_type} player {i}: Rebound total inconsistency")

    def _validate_team_stats_consistency(self, data: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate consistency in team statistics"""
        game = data.get('props', {}).get('pageProps', {}).get('game', {})

        for team_type in ['homeTeam', 'awayTeam']:
            team_data = game.get(team_type, {})

            # Validate starter + bench = team totals
            team_stats = team_data.get('statistics', {})
            starter_stats = team_data.get('starters', {})
            bench_stats = team_data.get('bench', {})

            # Check points consistency
            team_points = team_stats.get('points', 0)
            starter_points = starter_stats.get('points', 0)
            bench_points = bench_stats.get('points', 0)

            if team_points != starter_points + bench_points and all([team_points, starter_points, bench_points]):
                warnings.append(f"{team_type}: Points don't match (team: {team_points}, starters+bench: {starter_points + bench_points})")

    def _calculate_quality_score(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """Calculate overall data quality score (0-100)"""
        # Start with perfect score
        score = 100.0

        # Deduct points for errors (more severe)
        score -= len(errors) * 10

        # Deduct points for warnings (less severe)
        score -= len(warnings) * 2

        # Check completeness of optional fields
        optional_fields = [
            'props.pageProps.game.attendance',
            'props.pageProps.game.duration',
            'props.pageProps.game.homeTeam.players',
            'props.pageProps.game.awayTeam.players'
        ]

        missing_optional = sum(1 for field in optional_fields 
                             if not self._get_nested_value(data, field)[1])
        score -= missing_optional * 1

        # Ensure score doesn't go below 0
        return max(0.0, score)

    def validate_batch(self, data_files: List[Path]) -> Dict[str, ValidationResult]:
        """Validate a batch of JSON files"""
        results = {}

        for file_path in data_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                result = self.validate_game_data(data)
                results[str(file_path)] = result

            except Exception as e:
                results[str(file_path)] = ValidationResult(
                    is_valid=False,
                    errors=[f"Failed to process file: {str(e)}"],
                    warnings=[],
                    score=0.0
                )

        return results

    def generate_quality_report(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Generate a comprehensive quality report"""
        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r.is_valid)

        all_errors = []
        all_warnings = []
        all_scores = []

        for result in results.values():
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_scores.append(result.score)

        # Count error types
        error_types = {}
        for error in all_errors:
            error_type = error.split(':')[0] if ':' in error else error
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            'summary': {
                'total_files': total_files,
                'valid_files': valid_files,
                'invalid_files': total_files - valid_files,
                'validation_rate': valid_files / total_files if total_files > 0 else 0.0,
                'average_quality_score': sum(all_scores) / len(all_scores) if all_scores else 0.0
            },
            'error_analysis': {
                'total_errors': len(all_errors),
                'total_warnings': len(all_warnings),
                'common_error_types': sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            'quality_distribution': {
                'excellent': sum(1 for s in all_scores if s >= 95),
                'good': sum(1 for s in all_scores if 80 <= s < 95),
                'fair': sum(1 for s in all_scores if 60 <= s < 80),
                'poor': sum(1 for s in all_scores if s < 60)
            }
        }


def main():
    """Command-line interface for validation framework"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate NBA game JSON data quality')
    parser.add_argument('--data-dir', type=str, default='tests/data',
                       help='Directory containing JSON files to validate')
    parser.add_argument('--output-file', type=str,
                       help='Save validation report to JSON file')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed validation results')

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    validator = DataQualityValidator()
    data_dir = Path(args.data_dir)

    # Find all JSON files
    json_files = list(data_dir.glob('*.json'))
    # Filter to NBA game files (exclude analysis reports)
    game_files = [f for f in json_files if re.match(r'\d{6}_(reg|pla)_', f.name)]

    print(f"🔍 Validating {len(game_files)} NBA game files...")

    # Validate all files
    results = validator.validate_batch(game_files)

    # Generate report
    quality_report = validator.generate_quality_report(results)

    # Print summary
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 80)
    summary = quality_report['summary']
    print(f"Files processed: {summary['total_files']}")
    print(f"Valid files: {summary['valid_files']} ({summary['validation_rate']:.1%})")
    print(f"Average quality score: {summary['average_quality_score']:.1f}/100")

    # Print error analysis
    error_analysis = quality_report['error_analysis']
    print(f"\nTotal errors: {error_analysis['total_errors']}")
    print(f"Total warnings: {error_analysis['total_warnings']}")

    if error_analysis['common_error_types']:
        print("\nMost common error types:")
        for error_type, count in error_analysis['common_error_types'][:5]:
            print(f"  {error_type}: {count}")

    # Print quality distribution
    quality_dist = quality_report['quality_distribution']
    print(f"\nQuality distribution:")
    print(f"  Excellent (95-100): {quality_dist['excellent']}")
    print(f"  Good (80-94): {quality_dist['good']}")
    print(f"  Fair (60-79): {quality_dist['fair']}")
    print(f"  Poor (0-59): {quality_dist['poor']}")

    # Show detailed results if verbose
    if args.verbose:
        print("\n📋 DETAILED RESULTS")
        print("=" * 80)
        for file_path, result in results.items():
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            print(f"{status} {Path(file_path).name} (score: {result.score:.1f})")

            if result.errors:
                for error in result.errors:
                    print(f"  ERROR: {error}")

            if result.warnings:
                for warning in result.warnings:
                    print(f"  WARNING: {warning}")

    # Save detailed report if requested
    if args.output_file:
        detailed_report = {
            'validation_metadata': {
                'validated_at': datetime.now().isoformat(),
                'validator_version': '1.0.0',
                'files_processed': len(game_files)
            },
            'quality_report': quality_report,
            'detailed_results': {
                str(file_path): {
                    'is_valid': result.is_valid,
                    'score': result.score,
                    'errors': result.errors,
                    'warnings': result.warnings
                }
                for file_path, result in results.items()
            }
        }

        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, indent=2)

        print(f"\n💾 Detailed validation report saved to: {args.output_file}")


if __name__ == "__main__":
    main()