#!/usr/bin/env python3
"""
Database Statistics and Insights Tool
Provides comprehensive overview of all database tables with meaningful insights
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.database import get_db
    from sqlalchemy import text
    import json
except ImportError as e:
    print(f"Import error: {e}")
    print("This module requires the NBA PBP API dependencies to be installed.")
    print("Make sure you're running from the project root with the virtual environment activated.")
    sys.exit(1)


class DatabaseStats:
    """Generate comprehensive database statistics and insights"""
    
    def __init__(self):
        self.db = next(get_db())
        
    def close(self):
        """Close database connection"""
        self.db.close()
        
    def get_database_overview(self) -> Dict[str, Any]:
        """Get high-level database information"""
        try:
            # Database size and name
            result = self.db.execute(text("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as database_size,
                    current_database() as database_name,
                    pg_database_size(current_database()) as size_bytes
            """))
            row = result.fetchone()
            
            # Connection info
            conn_result = self.db.execute(text("""
                SELECT 
                    count(*) as active_connections,
                    current_setting('max_connections') as max_connections
                FROM pg_stat_activity 
                WHERE state = 'active'
            """))
            conn_row = conn_result.fetchone()
            
            return {
                'database_name': row.database_name,
                'database_size': row.database_size,
                'size_bytes': row.size_bytes,
                'active_connections': conn_row.active_connections,
                'max_connections': int(conn_row.max_connections),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': f"Failed to get database overview: {e}"}
    
    def get_all_tables_info(self) -> List[Dict[str, Any]]:
        """Get information about all tables in the database"""
        try:
            result = self.db.execute(text("""
                SELECT 
                    t.tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    c.reltuples::bigint as estimated_rows
                FROM pg_tables t
                JOIN pg_class c ON c.relname = t.tablename
                WHERE t.schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """))
            
            tables = []
            for row in result:
                table_info = {
                    'table_name': row.tablename,
                    'size': row.size,
                    'size_bytes': row.size_bytes,
                    'estimated_rows': row.estimated_rows
                }
                
                # Get exact row count for all tables
                try:
                    count_result = self.db.execute(text(f"SELECT COUNT(*) FROM {row.tablename}"))
                    table_info['exact_rows'] = count_result.scalar()
                except:
                    table_info['exact_rows'] = row.estimated_rows
                
                tables.append(table_info)
            
            return tables
        except Exception as e:
            return [{'error': f"Failed to get tables info: {e}"}]
    
    def get_table_insights(self, table_name: str) -> Dict[str, Any]:
        """Get detailed insights for a specific table"""
        insights = {'table_name': table_name}
        
        try:
            # Get column information
            col_result = self.db.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            
            insights['columns'] = [
                {
                    'name': row.column_name,
                    'type': row.data_type,
                    'nullable': row.is_nullable == 'YES',
                    'default': row.column_default
                }
                for row in col_result
            ]
            
            # Get indexes
            idx_result = self.db.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE tablename = :table_name
            """), {"table_name": table_name})
            
            insights['indexes'] = [
                {'name': row.indexname, 'definition': row.indexdef}
                for row in idx_result
            ]
            
            # Table-specific insights
            if table_name == 'game_url_queue':
                insights.update(self._get_game_url_queue_insights())
            elif table_name == 'raw_game_data':
                insights.update(self._get_raw_game_data_insights())
            elif table_name == 'scraping_sessions':
                insights.update(self._get_scraping_sessions_insights())
            elif table_name == 'scraping_errors':
                insights.update(self._get_scraping_errors_insights())
            elif table_name == 'teams':
                insights.update(self._get_teams_insights())
                
        except Exception as e:
            insights['error'] = f"Failed to get insights for {table_name}: {e}"
            
        return insights
    
    def _get_game_url_queue_insights(self) -> Dict[str, Any]:
        """Get specific insights for game_url_queue table"""
        try:
            # Status distribution
            status_result = self.db.execute(text("""
                SELECT status, COUNT(*) as count
                FROM game_url_queue
                GROUP BY status
                ORDER BY count DESC
            """))
            
            # Season distribution
            season_result = self.db.execute(text("""
                SELECT season, COUNT(*) as count
                FROM game_url_queue
                GROUP BY season
                ORDER BY season
            """))
            
            # Game type distribution
            type_result = self.db.execute(text("""
                SELECT game_type, COUNT(*) as count
                FROM game_url_queue
                GROUP BY game_type
                ORDER BY count DESC
            """))
            
            # Date range
            date_result = self.db.execute(text("""
                SELECT 
                    MIN(game_date) as earliest_game,
                    MAX(game_date) as latest_game,
                    MAX(created_at) as last_updated
                FROM game_url_queue
            """))
            date_row = date_result.fetchone()
            
            # Progress metrics
            progress_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'validated') as validated,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'invalid') as invalid,
                    COUNT(*) as total,
                    AVG(response_time_ms) FILTER (WHERE response_time_ms IS NOT NULL) as avg_response_time,
                    SUM(data_size_bytes) FILTER (WHERE data_size_bytes IS NOT NULL) as total_data_bytes
                FROM game_url_queue
            """))
            progress_row = progress_result.fetchone()
            
            completion_rate = (progress_row.completed / progress_row.total * 100) if progress_row.total > 0 else 0
            
            return {
                'status_distribution': [{'status': r.status, 'count': r.count} for r in status_result],
                'season_distribution': [{'season': r.season, 'count': r.count} for r in season_result],
                'game_type_distribution': [{'type': r.game_type, 'count': r.count} for r in type_result],
                'date_range': {
                    'earliest_game': date_row.earliest_game.isoformat() if date_row.earliest_game else None,
                    'latest_game': date_row.latest_game.isoformat() if date_row.latest_game else None,
                    'last_updated': date_row.last_updated.isoformat() if date_row.last_updated else None
                },
                'progress_metrics': {
                    'total_games': progress_row.total,
                    'completed': progress_row.completed,
                    'validated': progress_row.validated,
                    'pending': progress_row.pending,
                    'failed': progress_row.failed,
                    'invalid': progress_row.invalid,
                    'completion_rate_percent': round(completion_rate, 2),
                    'avg_response_time_ms': float(progress_row.avg_response_time) if progress_row.avg_response_time else None,
                    'total_data_mb': round(progress_row.total_data_bytes / (1024*1024), 2) if progress_row.total_data_bytes else 0
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_raw_game_data_insights(self) -> Dict[str, Any]:
        """Get specific insights for raw_game_data table"""
        try:
            # JSON data statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_games,
                    AVG(json_size) as avg_json_size,
                    MIN(json_size) as min_json_size,
                    MAX(json_size) as max_json_size,
                    SUM(json_size) as total_json_size,
                    MIN(scraped_at) as first_scraped,
                    MAX(scraped_at) as last_scraped
                FROM raw_game_data
            """))
            stats_row = stats_result.fetchone()
            
            # Processing status distribution
            processing_result = self.db.execute(text("""
                SELECT processing_status, COUNT(*) as count
                FROM raw_game_data
                GROUP BY processing_status
            """))
            
            # Recent scraping activity
            recent_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE scraped_at > NOW() - INTERVAL '1 hour') as last_hour,
                    COUNT(*) FILTER (WHERE scraped_at > NOW() - INTERVAL '1 day') as last_day,
                    COUNT(*) FILTER (WHERE scraped_at > NOW() - INTERVAL '1 week') as last_week
                FROM raw_game_data
            """))
            recent_row = recent_result.fetchone()
            
            return {
                'json_statistics': {
                    'total_games': stats_row.total_games,
                    'avg_size_kb': round(stats_row.avg_json_size / 1024, 2) if stats_row.avg_json_size else 0,
                    'min_size_kb': round(stats_row.min_json_size / 1024, 2) if stats_row.min_json_size else 0,
                    'max_size_kb': round(stats_row.max_json_size / 1024, 2) if stats_row.max_json_size else 0,
                    'total_size_mb': round(stats_row.total_json_size / (1024*1024), 2) if stats_row.total_json_size else 0
                },
                'processing_status': [{'status': r.processing_status, 'count': r.count} for r in processing_result],
                'scraping_timeline': {
                    'first_scraped': stats_row.first_scraped.isoformat() if stats_row.first_scraped else None,
                    'last_scraped': stats_row.last_scraped.isoformat() if stats_row.last_scraped else None
                },
                'recent_activity': {
                    'scraped_last_hour': recent_row.last_hour,
                    'scraped_last_day': recent_row.last_day,
                    'scraped_last_week': recent_row.last_week
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_scraping_sessions_insights(self) -> Dict[str, Any]:
        """Get insights for scraping_sessions table"""
        try:
            # Session statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(*) FILTER (WHERE is_active = true) as active_sessions,
                    AVG(successful_games) as avg_successful,
                    SUM(successful_games) as total_successful,
                    SUM(failed_games) as total_failed,
                    AVG(average_response_time_ms) as avg_response_time,
                    MAX(started_at) as last_session_start
                FROM scraping_sessions
            """))
            stats_row = stats_result.fetchone()
            
            return {
                'session_summary': {
                    'total_sessions': stats_row.total_sessions,
                    'active_sessions': stats_row.active_sessions,
                    'total_successful_games': stats_row.total_successful or 0,
                    'total_failed_games': stats_row.total_failed or 0,
                    'avg_successful_per_session': round(stats_row.avg_successful or 0, 1),
                    'avg_response_time_ms': round(stats_row.avg_response_time or 0, 1),
                    'last_session': stats_row.last_session_start.isoformat() if stats_row.last_session_start else None
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_scraping_errors_insights(self) -> Dict[str, Any]:
        """Get insights for scraping_errors table"""
        try:
            # Error statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_errors,
                    COUNT(DISTINCT game_id) as unique_games_with_errors,
                    COUNT(DISTINCT error_type) as unique_error_types
                FROM scraping_errors
            """))
            stats_row = stats_result.fetchone()
            
            # Error type distribution
            type_result = self.db.execute(text("""
                SELECT error_type, COUNT(*) as count
                FROM scraping_errors
                GROUP BY error_type
                ORDER BY count DESC
                LIMIT 10
            """))
            
            return {
                'error_summary': {
                    'total_errors': stats_row.total_errors,
                    'unique_games_affected': stats_row.unique_games_with_errors,
                    'unique_error_types': stats_row.unique_error_types
                },
                'top_error_types': [{'type': r.error_type, 'count': r.count} for r in type_result]
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_teams_insights(self) -> Dict[str, Any]:
        """Get insights for teams table"""
        try:
            # Team statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_teams,
                    COUNT(DISTINCT city) as unique_cities,
                    COUNT(*) FILTER (WHERE active = true) as active_teams
                FROM teams
            """))
            stats_row = stats_result.fetchone()
            
            return {
                'team_summary': {
                    'total_teams': stats_row.total_teams,
                    'unique_cities': stats_row.unique_cities,
                    'active_teams': stats_row.active_teams
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def generate_full_report(self) -> Dict[str, Any]:
        """Generate a comprehensive database report"""
        print("Generating comprehensive database report...")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'database_overview': self.get_database_overview(),
            'tables': []
        }
        
        # Get all tables info
        tables_info = self.get_all_tables_info()
        
        for table_info in tables_info:
            if 'error' in table_info:
                continue
                
            table_name = table_info['table_name']
            print(f"  Analyzing {table_name}...")
            
            # Get detailed insights
            insights = self.get_table_insights(table_name)
            
            # Combine basic info with insights
            complete_table_info = {**table_info, **insights}
            report['tables'].append(complete_table_info)
        
        return report
    
    def print_summary_report(self):
        """Print a human-readable summary of the database"""
        print("=" * 80)
        print("NBA PLAY-BY-PLAY DATABASE REPORT")
        print("=" * 80)
        
        # Database overview
        overview = self.get_database_overview()
        print(f"\nDATABASE OVERVIEW")
        print(f"   Database: {overview.get('database_name', 'Unknown')}")
        print(f"   Total Size: {overview.get('database_size', 'Unknown')}")
        print(f"   Active Connections: {overview.get('active_connections', 'Unknown')}")
        
        # Tables summary
        tables = self.get_all_tables_info()
        print(f"\nTABLES SUMMARY ({len(tables)} tables)")
        print("-" * 80)
        print(f"{'Table Name':<20} {'Size':<12} {'Rows':<15} {'Key Insights'}")
        print("-" * 80)
        
        for table in tables:
            if 'error' in table:
                continue
                
            table_name = table['table_name']
            size = table['size']
            row_count = table.get('exact_rows', table.get('estimated_rows', 0))
            if row_count is None or row_count == 0:
                rows = "0"
            else:
                rows = f"{int(row_count):,}"
            
            # Get key insight
            if table_name == 'game_url_queue':
                insights = self._get_game_url_queue_insights()
                progress = insights.get('progress_metrics', {})
                key_insight = f"{progress.get('completion_rate_percent', 0)}% scraped"
            elif table_name == 'raw_game_data':
                insights = self._get_raw_game_data_insights()
                stats = insights.get('json_statistics', {})
                key_insight = f"{stats.get('total_games', 0)} games, {stats.get('avg_size_kb', 0)} KB avg"
            elif table_name == 'scraping_sessions':
                insights = self._get_scraping_sessions_insights()
                summary = insights.get('session_summary', {})
                key_insight = f"{summary.get('total_sessions', 0)} sessions"
            else:
                key_insight = ""
            
            print(f"{table_name:<20} {size:<12} {rows:<15} {key_insight}")
        
        # Key metrics
        print(f"\nKEY METRICS")
        queue_insights = self._get_game_url_queue_insights()
        json_insights = self._get_raw_game_data_insights()
        
        if 'progress_metrics' in queue_insights:
            progress = queue_insights['progress_metrics']
            print(f"   Total Games in Queue: {progress.get('total_games', 0):,}")
            print(f"   Games Completed: {progress.get('completed', 0):,}")
            print(f"   Completion Rate: {progress.get('completion_rate_percent', 0)}%")
            print(f"   Games Ready to Scrape: {progress.get('validated', 0):,}")
        
        if 'json_statistics' in json_insights:
            json_stats = json_insights['json_statistics']
            print(f"   JSON Data Stored: {json_stats.get('total_size_mb', 0)} MB")
            print(f"   Average Game Size: {json_stats.get('avg_size_kb', 0)} KB")
        
        print("=" * 80)


def run_database_stats(json_output=False, table_name=None, summary=True):
    """
    Run database stats programmatically (for module usage)
    
    Args:
        json_output (bool): If True, return full report as dict instead of printing
        table_name (str): If provided, return insights for specific table only
        summary (bool): If True, print summary report (only used when other options are False)
    
    Returns:
        dict: Database statistics (if json_output=True or table_name provided)
        None: If printing summary
    """
    stats = DatabaseStats()
    
    try:
        if table_name:
            return stats.get_table_insights(table_name)
        elif json_output:
            return stats.generate_full_report()
        elif summary:
            stats.print_summary_report()
            return None
        else:
            # Default to summary if no other option specified
            stats.print_summary_report()
            return None
            
    except Exception as e:
        print(f"Error generating report: {e}")
        return {"error": str(e)}
    finally:
        stats.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NBA Database Statistics Tool')
    parser.add_argument('--json', action='store_true', help='Output full report as JSON')
    parser.add_argument('--table', type=str, help='Get detailed insights for specific table')
    parser.add_argument('--summary', action='store_true', default=True, help='Show summary report (default)')
    
    args = parser.parse_args()
    
    try:
        if args.table:
            # Show specific table insights
            result = run_database_stats(table_name=args.table)
            print(json.dumps(result, indent=2, default=str))
        elif args.json:
            # Full JSON report
            result = run_database_stats(json_output=True)
            print(json.dumps(result, indent=2, default=str))
        else:
            # Human-readable summary
            run_database_stats(summary=True)
            
    except KeyboardInterrupt:
        print("\nReport generation interrupted by user")
    except Exception as e:
        print(f"Error generating report: {e}")


if __name__ == "__main__":
    main()