#!/usr/bin/env python3
"""
NBA Games Database Audit Script
Provides comprehensive analysis of scraped NBA games data including:
- Total games scraped by season (1996-97 through 2024-25)
- Breakdown by game type (regular season vs playoffs)
- Summary statistics showing completion rates
- Gap identification and anomaly detection
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.database import get_db
    from sqlalchemy import text
    import pandas as pd
    from tabulate import tabulate
except ImportError as e:
    print(f"Import error: {e}")
    print("This module requires the NBA PBP API dependencies to be installed.")
    print("Make sure you're running from the project root with the virtual environment activated.")
    sys.exit(1)


class NBAGamesAuditor:
    """Comprehensive auditor for NBA games database"""
    
    def __init__(self):
        self.db = next(get_db())
        
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def get_database_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        try:
            result = self.db.execute(text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            return [row.tablename for row in result]
        except Exception as e:
            print(f"Error getting database tables: {e}")
            return []
    
    def audit_scraped_games_by_season(self) -> Dict[str, Any]:
        """Get comprehensive breakdown of scraped games by season and type"""
        results = {}
        
        # Check which tables exist to determine data structure
        tables = self.get_database_tables()
        
        # Try different table configurations based on what exists
        if 'raw_game_data' in tables:
            results['raw_data'] = self._audit_raw_game_data()
        
        if 'game_url_queue' in tables:
            results['queue_status'] = self._audit_game_url_queue()
        
        if 'enhanced_games' in tables:
            results['enhanced_games'] = self._audit_enhanced_games()
        
        if 'games' in tables:
            results['games_table'] = self._audit_games_table()
        
        # Combine and analyze
        results['summary'] = self._generate_summary(results)
        results['gaps_and_anomalies'] = self._identify_gaps_and_anomalies(results)
        
        return results
    
    def _audit_raw_game_data(self) -> Dict[str, Any]:
        """Audit the raw_game_data table"""
        try:
            # Get scraped games by extracting season from game_id pattern
            result = self.db.execute(text("""
                SELECT 
                    game_id,
                    scraped_at,
                    json_size,
                    processing_status
                FROM raw_game_data
                ORDER BY game_id
            """))
            
            games = []
            for row in result:
                # Extract season from game_id (format: 0022300001 where 0022300001 = 2023-24 season)
                game_id = row.game_id
                if len(game_id) >= 10:
                    season_code = game_id[3:5]  # Extract year part
                    try:
                        year = int(season_code)
                        if year >= 96:  # 1996-97 season
                            season = f"19{year}-{year+1:02d}" if year < 100 else f"20{year-100:02d}-{year-99:02d}"
                        else:
                            season = f"20{year:02d}-{year+1:02d}"
                    except:
                        season = "Unknown"
                else:
                    season = "Unknown"
                
                # Determine game type from game_id
                if len(game_id) >= 10:
                    game_type_code = game_id[2:4]
                    if game_type_code == "22":
                        game_type = "Regular Season"
                    elif game_type_code == "42":
                        game_type = "Playoffs"
                    else:
                        game_type = "Other"
                else:
                    game_type = "Unknown"
                
                games.append({
                    'game_id': game_id,
                    'season': season,
                    'game_type': game_type,
                    'scraped_at': row.scraped_at,
                    'json_size': row.json_size,
                    'processing_status': row.processing_status
                })
            
            # Aggregate by season and game type
            season_stats = {}
            for game in games:
                season = game['season']
                game_type = game['game_type']
                
                if season not in season_stats:
                    season_stats[season] = {
                        'Regular Season': 0,
                        'Playoffs': 0,
                        'Other': 0,
                        'total': 0,
                        'avg_json_size': 0,
                        'processing_statuses': {}
                    }
                
                season_stats[season][game_type] += 1
                season_stats[season]['total'] += 1
                
                # Track processing statuses
                status = game['processing_status']
                if status not in season_stats[season]['processing_statuses']:
                    season_stats[season]['processing_statuses'][status] = 0
                season_stats[season]['processing_statuses'][status] += 1
            
            # Calculate averages
            for season in season_stats:
                total_size = sum(g['json_size'] or 0 for g in games if g['season'] == season)
                count = season_stats[season]['total']
                season_stats[season]['avg_json_size'] = total_size / count if count > 0 else 0
            
            return {
                'total_games': len(games),
                'season_breakdown': season_stats,
                'earliest_scrape': min(g['scraped_at'] for g in games if g['scraped_at']),
                'latest_scrape': max(g['scraped_at'] for g in games if g['scraped_at']),
                'table_name': 'raw_game_data'
            }
        
        except Exception as e:
            return {'error': f"Error auditing raw_game_data: {e}"}
    
    def _audit_game_url_queue(self) -> Dict[str, Any]:
        """Audit the game_url_queue table"""
        try:
            # Get queue status with season and game type breakdown
            result = self.db.execute(text("""
                SELECT 
                    season,
                    game_type,
                    status,
                    COUNT(*) as count,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(data_size_bytes) as avg_data_size
                FROM game_url_queue
                GROUP BY season, game_type, status
                ORDER BY season, game_type, status
            """))
            
            queue_stats = {}
            for row in result:
                season = row.season
                game_type = row.game_type or 'Unknown'
                status = row.status
                
                if season not in queue_stats:
                    queue_stats[season] = {}
                
                if game_type not in queue_stats[season]:
                    queue_stats[season][game_type] = {
                        'pending': 0,
                        'in_progress': 0,
                        'completed': 0,
                        'validated': 0,
                        'failed': 0,
                        'invalid': 0,
                        'total': 0,
                        'avg_response_time': 0,
                        'avg_data_size': 0
                    }
                
                queue_stats[season][game_type][status] = row.count
                queue_stats[season][game_type]['total'] += row.count
                
                if row.avg_response_time:
                    queue_stats[season][game_type]['avg_response_time'] = row.avg_response_time
                if row.avg_data_size:
                    queue_stats[season][game_type]['avg_data_size'] = row.avg_data_size
            
            # Get overall statistics
            overall_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'validated') as validated,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'invalid') as invalid,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress
                FROM game_url_queue
            """))
            overall_row = overall_result.fetchone()
            
            completion_rate = (overall_row.completed / overall_row.total_games * 100) if overall_row.total_games > 0 else 0
            
            return {
                'season_breakdown': queue_stats,
                'overall_stats': {
                    'total_games': overall_row.total_games,
                    'completed': overall_row.completed,
                    'validated': overall_row.validated,
                    'pending': overall_row.pending,
                    'failed': overall_row.failed,
                    'invalid': overall_row.invalid,
                    'in_progress': overall_row.in_progress,
                    'completion_rate_percent': round(completion_rate, 2)
                },
                'table_name': 'game_url_queue'
            }
        
        except Exception as e:
            return {'error': f"Error auditing game_url_queue: {e}"}
    
    def _audit_enhanced_games(self) -> Dict[str, Any]:
        """Audit the enhanced_games table"""
        try:
            # Get game stats by season and type
            result = self.db.execute(text("""
                SELECT 
                    season,
                    CASE 
                        WHEN game_label LIKE '%Playoff%' OR series_game_number IS NOT NULL THEN 'Playoffs'
                        ELSE 'Regular Season'
                    END as game_type,
                    COUNT(*) as count,
                    AVG(attendance) as avg_attendance,
                    COUNT(*) FILTER (WHERE game_status = 3) as final_games,
                    COUNT(*) FILTER (WHERE game_status = 2) as live_games,
                    COUNT(*) FILTER (WHERE game_status = 1) as scheduled_games
                FROM enhanced_games
                GROUP BY season, game_type
                ORDER BY season, game_type
            """))
            
            enhanced_stats = {}
            for row in result:
                season = row.season
                game_type = row.game_type
                
                if season not in enhanced_stats:
                    enhanced_stats[season] = {}
                
                enhanced_stats[season][game_type] = {
                    'count': row.count,
                    'avg_attendance': round(row.avg_attendance or 0),
                    'final_games': row.final_games,
                    'live_games': row.live_games,
                    'scheduled_games': row.scheduled_games
                }
            
            # Get overall stats
            overall_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(DISTINCT season) as unique_seasons,
                    MIN(game_date) as earliest_game,
                    MAX(game_date) as latest_game,
                    AVG(attendance) as overall_avg_attendance
                FROM enhanced_games
            """))
            overall_row = overall_result.fetchone()
            
            return {
                'season_breakdown': enhanced_stats,
                'overall_stats': {
                    'total_games': overall_row.total_games,
                    'unique_seasons': overall_row.unique_seasons,
                    'earliest_game': overall_row.earliest_game.isoformat() if overall_row.earliest_game else None,
                    'latest_game': overall_row.latest_game.isoformat() if overall_row.latest_game else None,
                    'overall_avg_attendance': round(overall_row.overall_avg_attendance or 0)
                },
                'table_name': 'enhanced_games'
            }
        
        except Exception as e:
            return {'error': f"Error auditing enhanced_games: {e}"}
    
    def _audit_games_table(self) -> Dict[str, Any]:
        """Audit the games table"""
        try:
            # Get game stats by season and type
            result = self.db.execute(text("""
                SELECT 
                    season,
                    game_type,
                    COUNT(*) as count,
                    AVG(attendance) as avg_attendance,
                    COUNT(*) FILTER (WHERE game_status = 3) as final_games,
                    COUNT(*) FILTER (WHERE game_status = 2) as live_games,
                    COUNT(*) FILTER (WHERE game_status = 1) as scheduled_games
                FROM games
                GROUP BY season, game_type
                ORDER BY season, game_type
            """))
            
            games_stats = {}
            for row in result:
                season = row.season
                game_type = row.game_type
                
                if season not in games_stats:
                    games_stats[season] = {}
                
                games_stats[season][game_type] = {
                    'count': row.count,
                    'avg_attendance': round(row.avg_attendance or 0),
                    'final_games': row.final_games,
                    'live_games': row.live_games,
                    'scheduled_games': row.scheduled_games
                }
            
            # Get overall stats
            overall_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(DISTINCT season) as unique_seasons,
                    MIN(game_date) as earliest_game,
                    MAX(game_date) as latest_game
                FROM games
            """))
            overall_row = overall_result.fetchone()
            
            return {
                'season_breakdown': games_stats,
                'overall_stats': {
                    'total_games': overall_row.total_games,
                    'unique_seasons': overall_row.unique_seasons,
                    'earliest_game': overall_row.earliest_game.isoformat() if overall_row.earliest_game else None,
                    'latest_game': overall_row.latest_game.isoformat() if overall_row.latest_game else None
                },
                'table_name': 'games'
            }
        
        except Exception as e:
            return {'error': f"Error auditing games table: {e}"}
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from all audit results"""
        summary = {
            'audit_timestamp': datetime.now().isoformat(),
            'tables_analyzed': list(results.keys()),
            'season_coverage': {},
            'completion_rates': {},
            'data_quality': {}
        }
        
        # Determine primary data source
        primary_source = None
        if 'enhanced_games' in results and 'error' not in results['enhanced_games']:
            primary_source = 'enhanced_games'
        elif 'games_table' in results and 'error' not in results['games_table']:
            primary_source = 'games_table'
        elif 'raw_data' in results and 'error' not in results['raw_data']:
            primary_source = 'raw_data'
        elif 'queue_status' in results and 'error' not in results['queue_status']:
            primary_source = 'queue_status'
        
        if primary_source and primary_source in results:
            data = results[primary_source]
            
            # Season coverage
            if 'season_breakdown' in data:
                seasons = list(data['season_breakdown'].keys())
                seasons = [s for s in seasons if s != 'Unknown']
                seasons.sort()
                
                summary['season_coverage'] = {
                    'earliest_season': seasons[0] if seasons else None,
                    'latest_season': seasons[-1] if seasons else None,
                    'total_seasons': len(seasons),
                    'seasons_list': seasons
                }
            
            # Completion rates from queue data
            if 'queue_status' in results and 'overall_stats' in results['queue_status']:
                queue_stats = results['queue_status']['overall_stats']
                summary['completion_rates'] = {
                    'total_games_in_queue': queue_stats.get('total_games', 0),
                    'completed_games': queue_stats.get('completed', 0),
                    'completion_rate_percent': queue_stats.get('completion_rate_percent', 0),
                    'failed_games': queue_stats.get('failed', 0),
                    'pending_games': queue_stats.get('pending', 0)
                }
        
        return summary
    
    def _identify_gaps_and_anomalies(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Identify gaps and anomalies in the scraped data"""
        gaps = {
            'missing_seasons': [],
            'incomplete_seasons': [],
            'anomalous_seasons': [],
            'data_quality_issues': []
        }
        
        # Expected season range
        expected_seasons = []
        for year in range(1996, 2025):
            next_year = year + 1
            season = f"{year}-{next_year:02d}"
            expected_seasons.append(season)
        
        # Check for missing seasons
        if 'summary' in results and 'season_coverage' in results['summary']:
            actual_seasons = results['summary']['season_coverage'].get('seasons_list', [])
            gaps['missing_seasons'] = [s for s in expected_seasons if s not in actual_seasons]
        
        # Check for incomplete seasons (using queue data if available)
        if 'queue_status' in results and 'season_breakdown' in results['queue_status']:
            queue_data = results['queue_status']['season_breakdown']
            for season, types in queue_data.items():
                if season == 'Unknown':
                    continue
                
                # Check if regular season has reasonable number of games (should be around 1230 total)
                regular_season_total = 0
                playoffs_total = 0
                
                for game_type, stats in types.items():
                    if 'Regular Season' in game_type:
                        regular_season_total += stats.get('total', 0)
                    elif 'Playoffs' in game_type:
                        playoffs_total += stats.get('total', 0)
                
                # Flag seasons with suspicious numbers
                if regular_season_total < 1000:  # Too few regular season games
                    gaps['incomplete_seasons'].append({
                        'season': season,
                        'issue': 'Low regular season game count',
                        'regular_season_games': regular_season_total
                    })
                
                if regular_season_total > 1400:  # Too many regular season games
                    gaps['anomalous_seasons'].append({
                        'season': season,
                        'issue': 'High regular season game count',
                        'regular_season_games': regular_season_total
                    })
        
        # Check for data quality issues
        if 'raw_data' in results and 'season_breakdown' in results['raw_data']:
            raw_data = results['raw_data']['season_breakdown']
            for season, stats in raw_data.items():
                if season == 'Unknown':
                    gaps['data_quality_issues'].append({
                        'issue': 'Games with unknown season',
                        'count': stats.get('total', 0)
                    })
                
                # Check processing status issues
                statuses = stats.get('processing_statuses', {})
                failed_count = statuses.get('failed', 0)
                total_count = stats.get('total', 0)
                
                if failed_count > 0 and total_count > 0:
                    failure_rate = (failed_count / total_count) * 100
                    if failure_rate > 10:  # More than 10% failure rate
                        gaps['data_quality_issues'].append({
                            'season': season,
                            'issue': 'High processing failure rate',
                            'failure_rate_percent': round(failure_rate, 2),
                            'failed_count': failed_count,
                            'total_count': total_count
                        })
        
        return gaps
    
    def print_audit_report(self):
        """Print a comprehensive human-readable audit report"""
        print("=" * 100)
        print("NBA GAMES DATABASE AUDIT REPORT")
        print("=" * 100)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get audit data
        audit_data = self.audit_scraped_games_by_season()
        
        # Database tables overview
        tables = self.get_database_tables()
        print(f"\nDATABASE TABLES ({len(tables)} tables found):")
        relevant_tables = [t for t in tables if any(keyword in t for keyword in ['game', 'raw', 'queue', 'enhanced'])]
        for table in relevant_tables:
            print(f"  • {table}")
        
        # Summary statistics
        if 'summary' in audit_data:
            summary = audit_data['summary']
            print(f"\nSUMMARY STATISTICS:")
            
            if 'season_coverage' in summary:
                coverage = summary['season_coverage']
                print(f"  Season Range: {coverage.get('earliest_season', 'Unknown')} to {coverage.get('latest_season', 'Unknown')}")
                print(f"  Total Seasons: {coverage.get('total_seasons', 0)}")
            
            if 'completion_rates' in summary:
                rates = summary['completion_rates']
                print(f"  Total Games in Queue: {rates.get('total_games_in_queue', 0):,}")
                print(f"  Completed Games: {rates.get('completed_games', 0):,}")
                print(f"  Completion Rate: {rates.get('completion_rate_percent', 0)}%")
                print(f"  Failed Games: {rates.get('failed_games', 0):,}")
                print(f"  Pending Games: {rates.get('pending_games', 0):,}")
        
        # Detailed breakdown by source
        for source_name, source_data in audit_data.items():
            if source_name in ['summary', 'gaps_and_anomalies'] or 'error' in source_data:
                continue
            
            print(f"\n{source_name.upper().replace('_', ' ')} BREAKDOWN:")
            print("-" * 80)
            
            if 'season_breakdown' in source_data:
                # Create table for season breakdown
                table_data = []
                season_breakdown = source_data['season_breakdown']
                
                for season in sorted(season_breakdown.keys()):
                    if season == 'Unknown':
                        continue
                    
                    season_data = season_breakdown[season]
                    
                    if source_name == 'queue_status':
                        # Queue status breakdown
                        for game_type, stats in season_data.items():
                            row = [
                                season,
                                game_type,
                                stats.get('total', 0),
                                stats.get('completed', 0),
                                stats.get('pending', 0),
                                stats.get('failed', 0),
                                f"{(stats.get('completed', 0) / max(stats.get('total', 1), 1) * 100):.1f}%"
                            ]
                            table_data.append(row)
                        
                        if table_data:
                            headers = ['Season', 'Type', 'Total', 'Completed', 'Pending', 'Failed', 'Complete %']
                            print(tabulate(table_data, headers=headers, tablefmt='simple'))
                    
                    elif source_name == 'raw_data':
                        # Raw data breakdown
                        row = [
                            season,
                            season_data.get('Regular Season', 0),
                            season_data.get('Playoffs', 0),
                            season_data.get('total', 0),
                            f"{season_data.get('avg_json_size', 0) / 1024:.1f} KB"
                        ]
                        table_data.append(row)
                
                if source_name == 'raw_data' and table_data:
                    headers = ['Season', 'Regular Season', 'Playoffs', 'Total', 'Avg Size']
                    print(tabulate(table_data, headers=headers, tablefmt='simple'))
        
        # Gaps and anomalies
        if 'gaps_and_anomalies' in audit_data:
            gaps = audit_data['gaps_and_anomalies']
            print(f"\nGAPS AND ANOMALIES:")
            print("-" * 80)
            
            if gaps.get('missing_seasons'):
                print(f"Missing Seasons ({len(gaps['missing_seasons'])}): {', '.join(gaps['missing_seasons'])}")
            
            if gaps.get('incomplete_seasons'):
                print(f"\nIncomplete Seasons:")
                for issue in gaps['incomplete_seasons']:
                    print(f"  • {issue['season']}: {issue['issue']} ({issue.get('regular_season_games', 0)} games)")
            
            if gaps.get('anomalous_seasons'):
                print(f"\nAnomalous Seasons:")
                for issue in gaps['anomalous_seasons']:
                    print(f"  • {issue['season']}: {issue['issue']} ({issue.get('regular_season_games', 0)} games)")
            
            if gaps.get('data_quality_issues'):
                print(f"\nData Quality Issues:")
                for issue in gaps['data_quality_issues']:
                    if 'season' in issue:
                        print(f"  • {issue['season']}: {issue['issue']} ({issue.get('failure_rate_percent', 0)}%)")
                    else:
                        print(f"  • {issue['issue']} ({issue.get('count', 0)} games)")
        
        print("=" * 100)
    
    def get_audit_json(self) -> Dict[str, Any]:
        """Get audit results as JSON for programmatic use"""
        return self.audit_scraped_games_by_season()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NBA Games Database Audit Tool')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--output', type=str, help='Output file path (optional)')
    
    args = parser.parse_args()
    
    auditor = NBAGamesAuditor()
    
    try:
        if args.json:
            # JSON output
            results = auditor.get_audit_json()
            json_output = json.dumps(results, indent=2, default=str)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(json_output)
                print(f"Audit results saved to {args.output}")
            else:
                print(json_output)
        else:
            # Human-readable report
            auditor.print_audit_report()
            
            if args.output:
                # Also save JSON version
                results = auditor.get_audit_json()
                json_path = args.output.replace('.txt', '.json') if args.output.endswith('.txt') else f"{args.output}.json"
                with open(json_path, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"\nDetailed JSON results also saved to {json_path}")
                
    except KeyboardInterrupt:
        print("\nAudit interrupted by user")
    except Exception as e:
        print(f"Error during audit: {e}")
        import traceback
        traceback.print_exc()
    finally:
        auditor.close()


if __name__ == "__main__":
    main()