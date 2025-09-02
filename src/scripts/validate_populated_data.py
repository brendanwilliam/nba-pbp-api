#!/usr/bin/env python3
"""
Data validation script for populated WNBA game tables.
Performs comprehensive data quality checks and foreign key integrity validation.
"""

import argparse
import logging
import sys
from typing import Dict, List, Tuple
from collections import defaultdict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..database.services import DatabaseConnection
from ..database.models import Arena, Team, Person, Game, TeamGame, PersonGame, Play, Boxscore


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Comprehensive data validation for populated WNBA tables"""
    
    def __init__(self):
        self.db_connection = DatabaseConnection()
        self.engine = self.db_connection.get_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.issues = []
    
    def validate_all(self) -> Dict[str, any]:
        """
        Run all validation checks.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Starting comprehensive data validation...")
        
        results = {
            'table_counts': {},
            'foreign_key_issues': [],
            'data_quality_issues': [],
            'statistical_summary': {},
            'validation_passed': True
        }
        
        with self.Session() as session:
            # 1. Table counts
            results['table_counts'] = self._get_table_counts(session)
            
            # 2. Foreign key integrity
            results['foreign_key_issues'] = self._validate_foreign_keys(session)
            
            # 3. Data quality checks
            results['data_quality_issues'] = self._validate_data_quality(session)
            
            # 4. Statistical summaries
            results['statistical_summary'] = self._generate_statistics(session)
            
            # Determine overall validation status
            if results['foreign_key_issues'] or results['data_quality_issues']:
                results['validation_passed'] = False
        
        self._log_results(results)
        return results
    
    def _get_table_counts(self, session) -> Dict[str, int]:
        """Get record counts for all tables"""
        logger.info("Collecting table counts...")
        
        tables = [
            ('arena', Arena),
            ('team', Team),
            ('person', Person),
            ('game', Game),
            ('team_game', TeamGame),
            ('person_game', PersonGame),
            ('play', Play),
            ('boxscore', Boxscore)
        ]
        
        counts = {}
        for table_name, model_class in tables:
            count = session.query(model_class).count()
            counts[table_name] = count
            logger.info(f"  {table_name}: {count:,} records")
        
        return counts
    
    def _validate_foreign_keys(self, session) -> List[Dict[str, any]]:
        """Validate foreign key integrity"""
        logger.info("Validating foreign key integrity...")
        
        issues = []
        
        # Define foreign key checks
        fk_checks = [
            {
                'name': 'Game -> Arena',
                'query': '''
                    SELECT COUNT(*) FROM game g 
                    LEFT JOIN arena a ON g.arena_id = a.arena_id 
                    WHERE a.arena_id IS NULL
                ''',
                'description': 'Games referencing non-existent arenas'
            },
            {
                'name': 'TeamGame -> Game',
                'query': '''
                    SELECT COUNT(*) FROM team_game tg 
                    LEFT JOIN game g ON tg.game_id = g.game_id 
                    WHERE g.game_id IS NULL
                ''',
                'description': 'Team-game relationships referencing non-existent games'
            },
            {
                'name': 'TeamGame -> Team',
                'query': '''
                    SELECT COUNT(*) FROM team_game tg 
                    LEFT JOIN team t ON tg.team_id = t.id 
                    WHERE t.id IS NULL
                ''',
                'description': 'Team-game relationships referencing non-existent teams'
            },
            {
                'name': 'PersonGame -> Game',
                'query': '''
                    SELECT COUNT(*) FROM person_game pg 
                    LEFT JOIN game g ON pg.game_id = g.game_id 
                    WHERE g.game_id IS NULL
                ''',
                'description': 'Person-game relationships referencing non-existent games'
            },
            {
                'name': 'PersonGame -> Person',
                'query': '''
                    SELECT COUNT(*) FROM person_game pg 
                    LEFT JOIN person p ON pg.person_id = p.person_id 
                    WHERE p.person_id IS NULL
                ''',
                'description': 'Person-game relationships referencing non-existent persons'
            },
            {
                'name': 'Play -> Game',
                'query': '''
                    SELECT COUNT(*) FROM play p 
                    LEFT JOIN game g ON p.game_id = g.game_id 
                    WHERE g.game_id IS NULL
                ''',
                'description': 'Plays referencing non-existent games'
            },
            {
                'name': 'Play -> Person (non-null)',
                'query': '''
                    SELECT COUNT(*) FROM play p 
                    LEFT JOIN person pe ON p.person_id = pe.person_id 
                    WHERE p.person_id IS NOT NULL AND pe.person_id IS NULL
                ''',
                'description': 'Plays referencing non-existent persons'
            },
            {
                'name': 'Boxscore -> Game',
                'query': '''
                    SELECT COUNT(*) FROM boxscore b 
                    LEFT JOIN game g ON b.game_id = g.game_id 
                    WHERE g.game_id IS NULL
                ''',
                'description': 'Boxscore entries referencing non-existent games'
            },
            {
                'name': 'Boxscore -> Person (non-null)',
                'query': '''
                    SELECT COUNT(*) FROM boxscore b 
                    LEFT JOIN person pe ON b.person_id = pe.person_id 
                    WHERE b.person_id IS NOT NULL AND pe.person_id IS NULL
                ''',
                'description': 'Boxscore entries referencing non-existent persons'
            }
        ]
        
        for check in fk_checks:
            try:
                count = session.execute(text(check['query'])).scalar()
                if count > 0:
                    issue = {
                        'check': check['name'],
                        'description': check['description'],
                        'count': count,
                        'severity': 'ERROR'
                    }
                    issues.append(issue)
                    logger.error(f"  ❌ {check['name']}: {count} violations")
                else:
                    logger.info(f"  ✓ {check['name']}: No violations")
            except Exception as e:
                issue = {
                    'check': check['name'],
                    'description': f"Failed to execute check: {e}",
                    'count': None,
                    'severity': 'ERROR'
                }
                issues.append(issue)
                logger.error(f"  ❌ {check['name']}: Check failed - {e}")
        
        return issues
    
    def _validate_data_quality(self, session) -> List[Dict[str, any]]:
        """Validate data quality and consistency"""
        logger.info("Validating data quality...")
        
        issues = []
        
        # Data quality checks
        quality_checks = [
            {
                'name': 'Games with missing arena',
                'query': 'SELECT COUNT(*) FROM game WHERE arena_id IS NULL',
                'description': 'Games without arena information',
                'severity': 'ERROR'
            },
            {
                'name': 'Games with missing teams',
                'query': '''
                    SELECT COUNT(*) FROM game 
                    WHERE home_team_id IS NULL OR away_team_id IS NULL
                ''',
                'description': 'Games without complete team information',
                'severity': 'ERROR'
            },
            {
                'name': 'Plays without action type',
                'query': 'SELECT COUNT(*) FROM play WHERE action_type IS NULL',
                'description': 'Plays missing action type',
                'severity': 'WARNING'
            },
            {
                'name': 'Persons without names',
                'query': '''
                    SELECT COUNT(*) FROM person 
                    WHERE person_name IS NULL AND person_name_i IS NULL
                ''',
                'description': 'Persons without any name information',
                'severity': 'WARNING'
            },
            {
                'name': 'Boxscore entries without box type',
                'query': 'SELECT COUNT(*) FROM boxscore WHERE box_type IS NULL',
                'description': 'Boxscore entries missing box type',
                'severity': 'ERROR'
            },
            {
                'name': 'Invalid home/away team indicators',
                'query': '''
                    SELECT COUNT(*) FROM boxscore 
                    WHERE home_away_team NOT IN ('h', 'a')
                ''',
                'description': 'Invalid home/away team indicators',
                'severity': 'ERROR'
            },
            {
                'name': 'Negative statistics',
                'query': '''
                    SELECT COUNT(*) FROM boxscore 
                    WHERE pts < 0 OR reb < 0 OR ast < 0 OR fgm < 0 OR fga < 0
                ''',
                'description': 'Negative statistical values',
                'severity': 'WARNING'
            },
            {
                'name': 'Invalid field goal percentages',
                'query': '''
                    SELECT COUNT(*) FROM boxscore 
                    WHERE fgp IS NOT NULL AND (fgp < 0 OR fgp > 1)
                ''',
                'description': 'Field goal percentages outside valid range (0-1)',
                'severity': 'WARNING'
            }
        ]
        
        for check in quality_checks:
            try:
                count = session.execute(text(check['query'])).scalar()
                if count > 0:
                    issue = {
                        'check': check['name'],
                        'description': check['description'],
                        'count': count,
                        'severity': check['severity']
                    }
                    issues.append(issue)
                    
                    if check['severity'] == 'ERROR':
                        logger.error(f"  ❌ {check['name']}: {count} issues")
                    else:
                        logger.warning(f"  ⚠️  {check['name']}: {count} issues")
                else:
                    logger.info(f"  ✓ {check['name']}: No issues")
            except Exception as e:
                issue = {
                    'check': check['name'],
                    'description': f"Failed to execute check: {e}",
                    'count': None,
                    'severity': 'ERROR'
                }
                issues.append(issue)
                logger.error(f"  ❌ {check['name']}: Check failed - {e}")
        
        return issues
    
    def _generate_statistics(self, session) -> Dict[str, any]:
        """Generate statistical summary of the data"""
        logger.info("Generating statistical summary...")
        
        stats = {}
        
        try:
            # Game statistics
            game_stats = session.execute(text('''
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(DISTINCT arena_id) as unique_arenas,
                    COUNT(DISTINCT home_team_id) as unique_home_teams,
                    COUNT(DISTINCT away_team_id) as unique_away_teams,
                    MIN(game_et) as earliest_game,
                    MAX(game_et) as latest_game
                FROM game
            ''')).fetchone()
            
            stats['games'] = {
                'total_games': game_stats.total_games,
                'unique_arenas': game_stats.unique_arenas,
                'unique_teams': len(set([game_stats.unique_home_teams, game_stats.unique_away_teams])),
                'date_range': {
                    'earliest': str(game_stats.earliest_game) if game_stats.earliest_game else None,
                    'latest': str(game_stats.latest_game) if game_stats.latest_game else None
                }
            }
            
            # Play statistics
            play_stats = session.execute(text('''
                SELECT 
                    COUNT(*) as total_plays,
                    COUNT(DISTINCT game_id) as games_with_plays,
                    COUNT(DISTINCT action_type) as unique_action_types,
                    AVG(CAST(points_total AS FLOAT)) as avg_points_per_play
                FROM play
            ''')).fetchone()
            
            stats['plays'] = {
                'total_plays': play_stats.total_plays,
                'games_with_plays': play_stats.games_with_plays,
                'unique_action_types': play_stats.unique_action_types,
                'avg_points_per_play': round(play_stats.avg_points_per_play or 0, 2)
            }
            
            # Boxscore statistics
            boxscore_stats = session.execute(text('''
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(DISTINCT game_id) as games_with_boxscores,
                    COUNT(DISTINCT person_id) as unique_persons,
                    AVG(CAST(pts AS FLOAT)) as avg_points,
                    MAX(pts) as max_points
                FROM boxscore 
                WHERE box_type = 'player'
            ''')).fetchone()
            
            stats['boxscores'] = {
                'total_entries': boxscore_stats.total_entries,
                'games_with_boxscores': boxscore_stats.games_with_boxscores,
                'unique_players': boxscore_stats.unique_persons,
                'avg_player_points': round(boxscore_stats.avg_points or 0, 1),
                'max_player_points': boxscore_stats.max_points or 0
            }
            
            # Person statistics
            person_stats = session.execute(text('''
                SELECT 
                    COUNT(*) as total_persons,
                    COUNT(CASE WHEN person_name IS NOT NULL THEN 1 END) as persons_with_names
                FROM person
            ''')).fetchone()
            
            stats['persons'] = {
                'total_persons': person_stats.total_persons,
                'persons_with_names': person_stats.persons_with_names,
                'name_coverage': round(
                    (person_stats.persons_with_names / person_stats.total_persons * 100) 
                    if person_stats.total_persons > 0 else 0, 1
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def _log_results(self, results: Dict[str, any]):
        """Log validation results summary"""
        logger.info("\n" + "=" * 60)
        logger.info("DATA VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        # Table counts
        logger.info("\nTable Record Counts:")
        for table, count in results['table_counts'].items():
            logger.info(f"  {table}: {count:,}")
        
        # Foreign key issues
        fk_issues = results['foreign_key_issues']
        if fk_issues:
            logger.error(f"\n❌ Foreign Key Issues: {len(fk_issues)}")
            for issue in fk_issues:
                logger.error(f"  - {issue['check']}: {issue['count']} violations")
        else:
            logger.info("\n✓ No foreign key violations found")
        
        # Data quality issues
        dq_issues = results['data_quality_issues']
        if dq_issues:
            errors = [i for i in dq_issues if i['severity'] == 'ERROR']
            warnings = [i for i in dq_issues if i['severity'] == 'WARNING']
            
            if errors:
                logger.error(f"\n❌ Data Quality Errors: {len(errors)}")
                for issue in errors:
                    logger.error(f"  - {issue['check']}: {issue['count']} issues")
            
            if warnings:
                logger.warning(f"\n⚠️  Data Quality Warnings: {len(warnings)}")
                for issue in warnings:
                    logger.warning(f"  - {issue['check']}: {issue['count']} issues")
        else:
            logger.info("\n✓ No data quality issues found")
        
        # Statistics summary
        stats = results['statistical_summary']
        if 'games' in stats:
            logger.info(f"\nStatistical Summary:")
            logger.info(f"  Total games: {stats['games']['total_games']:,}")
            if 'plays' in stats:
                logger.info(f"  Total plays: {stats['plays']['total_plays']:,}")
            if 'boxscores' in stats:
                logger.info(f"  Total boxscore entries: {stats['boxscores']['total_entries']:,}")
        
        # Overall result
        if results['validation_passed']:
            logger.info("\n🎉 VALIDATION PASSED - All checks successful!")
        else:
            logger.error("\n💥 VALIDATION FAILED - Issues found that need attention")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate populated WNBA game table data"
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output validation report to file'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    try:
        validator = DataValidator()
        results = validator.validate_all()
        
        # Output results
        if args.output:
            import json
            with open(args.output, 'w') as f:
                if args.json:
                    json.dump(results, f, indent=2, default=str)
                else:
                    f.write(f"Validation Results\n{'=' * 50}\n\n")
                    f.write(f"Validation Passed: {results['validation_passed']}\n\n")
                    
                    f.write("Table Counts:\n")
                    for table, count in results['table_counts'].items():
                        f.write(f"  {table}: {count:,}\n")
                    
                    if results['foreign_key_issues']:
                        f.write(f"\nForeign Key Issues ({len(results['foreign_key_issues'])}):\n")
                        for issue in results['foreign_key_issues']:
                            f.write(f"  - {issue['check']}: {issue['count']} violations\n")
                    
                    if results['data_quality_issues']:
                        f.write(f"\nData Quality Issues ({len(results['data_quality_issues'])}):\n")
                        for issue in results['data_quality_issues']:
                            f.write(f"  - {issue['check']}: {issue['count']} issues ({issue['severity']})\n")
            
            logger.info(f"Validation report written to: {args.output}")
        
        # Exit with appropriate code
        if not results['validation_passed']:
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()