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
    
    def __init__(self, database_url=None):
        if database_url:
            # Use provided database URL
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            self.engine = create_engine(database_url)
            Session = sessionmaker(bind=self.engine)
            self.db = Session()
        else:
            # Use default connection from get_db()
            self.db = next(get_db())
            self.engine = self.db.bind
        
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
            elif table_name == 'enhanced_games':
                insights.update(self._get_enhanced_games_insights())
            elif table_name == 'play_events':
                insights.update(self._get_play_events_insights())
            elif table_name == 'player_game_stats':
                insights.update(self._get_player_game_stats_insights())
            elif table_name == 'team_game_stats':
                insights.update(self._get_team_game_stats_insights())
            elif table_name == 'arenas':
                insights.update(self._get_arenas_insights())
            elif table_name == 'officials':
                insights.update(self._get_officials_insights())
                
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
            # Team statistics - handle both schemas
            try:
                # Try new schema first
                stats_result = self.db.execute(text("""
                    SELECT 
                        COUNT(*) as total_teams,
                        COUNT(DISTINCT team_city) as unique_cities
                    FROM teams
                """))
            except:
                # Fall back to old schema
                stats_result = self.db.execute(text("""
                    SELECT 
                        COUNT(*) as total_teams,
                        COUNT(DISTINCT city) as unique_cities
                    FROM teams
                """))
            stats_row = stats_result.fetchone()
            
            return {
                'team_summary': {
                    'total_teams': stats_row.total_teams,
                    'unique_cities': stats_row.unique_cities
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_enhanced_games_insights(self) -> Dict[str, Any]:
        """Get insights for enhanced_games table"""
        try:
            # Game statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(DISTINCT season) as unique_seasons,
                    COUNT(*) FILTER (WHERE game_status = 3) as final_games,
                    COUNT(*) FILTER (WHERE game_status = 2) as live_games,
                    COUNT(*) FILTER (WHERE game_status = 1) as scheduled_games,
                    AVG(attendance) as avg_attendance,
                    MIN(game_date) as earliest_game,
                    MAX(game_date) as latest_game
                FROM enhanced_games
            """))
            stats_row = stats_result.fetchone()
            
            return {
                'game_summary': {
                    'total_games': stats_row.total_games,
                    'unique_seasons': stats_row.unique_seasons,
                    'final_games': stats_row.final_games,
                    'live_games': stats_row.live_games,
                    'scheduled_games': stats_row.scheduled_games,
                    'avg_attendance': round(stats_row.avg_attendance or 0),
                    'date_range': {
                        'earliest': stats_row.earliest_game.isoformat() if stats_row.earliest_game else None,
                        'latest': stats_row.latest_game.isoformat() if stats_row.latest_game else None
                    }
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_play_events_insights(self) -> Dict[str, Any]:
        """Get insights for play_events table"""
        try:
            # Event statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT game_id) as unique_games,
                    COUNT(DISTINCT event_type) as unique_event_types,
                    COUNT(*) FILTER (WHERE shot_made = true) as made_shots,
                    COUNT(*) FILTER (WHERE shot_made = false) as missed_shots,
                    AVG(shot_distance) FILTER (WHERE shot_distance IS NOT NULL) as avg_shot_distance
                FROM play_events
            """))
            stats_row = stats_result.fetchone()
            
            # Event type distribution
            event_types_result = self.db.execute(text("""
                SELECT event_type, COUNT(*) as count
                FROM play_events
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
            """))
            
            return {
                'event_summary': {
                    'total_events': stats_row.total_events,
                    'unique_games': stats_row.unique_games,
                    'unique_event_types': stats_row.unique_event_types,
                    'made_shots': stats_row.made_shots,
                    'missed_shots': stats_row.missed_shots,
                    'avg_shot_distance': round(stats_row.avg_shot_distance or 0, 1),
                    'events_per_game': round(stats_row.total_events / max(stats_row.unique_games, 1), 1)
                },
                'top_event_types': [{'type': r.event_type, 'count': r.count} for r in event_types_result]
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_player_game_stats_insights(self) -> Dict[str, Any]:
        """Get insights for player_game_stats table"""
        try:
            # Player statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_player_games,
                    COUNT(DISTINCT player_id) as unique_players,
                    COUNT(DISTINCT game_id) as unique_games,
                    AVG(points) as avg_points,
                    MAX(points) as max_points,
                    AVG(rebounds_total) as avg_rebounds,
                    AVG(assists) as avg_assists,
                    COUNT(*) FILTER (WHERE starter = true) as starter_records
                FROM player_game_stats
            """))
            stats_row = stats_result.fetchone()
            
            return {
                'player_stats_summary': {
                    'total_player_games': stats_row.total_player_games,
                    'unique_players': stats_row.unique_players,
                    'unique_games': stats_row.unique_games,
                    'avg_points': round(stats_row.avg_points or 0, 1),
                    'max_points': stats_row.max_points,
                    'avg_rebounds': round(stats_row.avg_rebounds or 0, 1),
                    'avg_assists': round(stats_row.avg_assists or 0, 1),
                    'starter_records': stats_row.starter_records
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_team_game_stats_insights(self) -> Dict[str, Any]:
        """Get insights for team_game_stats table"""
        try:
            # Team statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_team_games,
                    COUNT(DISTINCT team_id) as unique_teams,
                    COUNT(DISTINCT game_id) as unique_games,
                    AVG(points) as avg_points,
                    MAX(points) as max_points,
                    AVG(field_goals_percentage) as avg_fg_pct,
                    AVG(three_pointers_percentage) as avg_3pt_pct
                FROM team_game_stats
            """))
            stats_row = stats_result.fetchone()
            
            return {
                'team_stats_summary': {
                    'total_team_games': stats_row.total_team_games,
                    'unique_teams': stats_row.unique_teams,
                    'unique_games': stats_row.unique_games,
                    'avg_points': round(stats_row.avg_points or 0, 1),
                    'max_points': stats_row.max_points,
                    'avg_fg_percentage': round(stats_row.avg_fg_pct or 0, 3),
                    'avg_3pt_percentage': round(stats_row.avg_3pt_pct or 0, 3)
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_arenas_insights(self) -> Dict[str, Any]:
        """Get insights for arenas table"""
        try:
            # Arena statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_arenas,
                    COUNT(DISTINCT arena_city) as unique_cities,
                    COUNT(DISTINCT arena_state) as unique_states,
                    AVG(capacity) as avg_capacity,
                    MAX(capacity) as max_capacity
                FROM arenas
            """))
            stats_row = stats_result.fetchone()
            
            return {
                'arena_summary': {
                    'total_arenas': stats_row.total_arenas,
                    'unique_cities': stats_row.unique_cities,
                    'unique_states': stats_row.unique_states,
                    'avg_capacity': round(stats_row.avg_capacity or 0),
                    'max_capacity': stats_row.max_capacity
                }
            }
        except Exception as e:
            return {'insights_error': str(e)}
    
    def _get_officials_insights(self) -> Dict[str, Any]:
        """Get insights for officials table"""
        try:
            # Officials statistics
            stats_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_officials
                FROM officials
            """))
            stats_row = stats_result.fetchone()
            
            return {
                'officials_summary': {
                    'total_officials': stats_row.total_officials
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
    
    def get_games_by_season_and_type(self) -> List[Dict[str, Any]]:
        """Get game counts by season and type (regular/playoff/playin)"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    -- Extract season from game_id positions 4-5 and convert to proper format
                    CASE 
                        WHEN SUBSTRING(game_id, 4, 2)::int >= 96 THEN 
                            CONCAT('19', SUBSTRING(game_id, 4, 2), '-', 
                                   CASE 
                                       WHEN SUBSTRING(game_id, 4, 2)::int = 99 THEN '00'
                                       ELSE LPAD(CAST(SUBSTRING(game_id, 4, 2)::int + 1 AS TEXT), 2, '0')
                                   END)
                        ELSE 
                            CONCAT('20', LPAD(SUBSTRING(game_id, 4, 2), 2, '0'), '-', 
                                   LPAD(CAST(SUBSTRING(game_id, 4, 2)::int + 1 AS TEXT), 2, '0'))
                    END as extracted_season,
                    CASE 
                        WHEN SUBSTRING(game_id, 3, 1) = '2' THEN 'regular'
                        WHEN SUBSTRING(game_id, 3, 1) = '4' THEN 'playoff'
                        WHEN SUBSTRING(game_id, 3, 1) = '5' THEN 'playin'
                        ELSE 'other'
                    END as game_type,
                    COUNT(*) as game_count
                FROM enhanced_games
                GROUP BY extracted_season, game_type
                ORDER BY extracted_season, game_type
            """))
            
            # Organize data by season
            seasons_data = {}
            for row in result:
                season = row.extracted_season  # Use the correctly extracted season
                if season not in seasons_data:
                    seasons_data[season] = {'regular': 0, 'playoff': 0, 'playin': 0, 'other': 0}
                seasons_data[season][row.game_type] = row.game_count
            
            # Convert to list format
            season_list = []
            for season in sorted(seasons_data.keys()):
                data = seasons_data[season]
                total = sum(data.values())
                season_list.append({
                    'season': season,
                    'regular': data['regular'],
                    'playoff': data['playoff'],
                    'playin': data['playin'],
                    'other': data['other'],
                    'total': total
                })
            
            return season_list

    def print_season_breakdown_table(self):
        """Print a formatted table of games by season and type"""
        print("=" * 80)
        print("NBA GAMES BY SEASON AND TYPE")
        print("=" * 80)
        
        season_data = self.get_games_by_season_and_type()
        
        # Print header
        print(f"{'Season':<12} {'Regular':<10} {'Playoff':<10} {'Play-In':<10} {'Other':<8} {'Total':<8}")
        print("-" * 80)
        
        # Print data rows
        total_regular = 0
        total_playoff = 0
        total_playin = 0
        total_other = 0
        total_all = 0
        
        for season_info in season_data:
            season = season_info['season']
            regular = season_info['regular']
            playoff = season_info['playoff']
            playin = season_info['playin']
            other = season_info['other']
            total = season_info['total']
            
            total_regular += regular
            total_playoff += playoff
            total_playin += playin
            total_other += other
            total_all += total
            
            print(f"{season:<12} {regular:<10} {playoff:<10} {playin:<10} {other:<8} {total:<8}")
        
        # Print totals
        print("-" * 80)
        print(f"{'TOTAL':<12} {total_regular:<10} {total_playoff:<10} {total_playin:<10} {total_other:<8} {total_all:<8}")
        print("=" * 80)

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


def run_database_stats(json_output=False, table_name=None, summary=True, by_season=False, database_url=None):
    """
    Run database stats programmatically (for module usage)
    
    Args:
        json_output (bool): If True, return full report as dict instead of printing
        table_name (str): If provided, return insights for specific table only
        summary (bool): If True, print summary report (only used when other options are False)
        by_season (bool): If True, print games by season and type table
        database_url (str): If provided, use this database URL instead of default
    
    Returns:
        dict: Database statistics (if json_output=True or table_name provided)
        None: If printing summary
    """
    stats = DatabaseStats(database_url=database_url)
    
    try:
        if table_name:
            return stats.get_table_insights(table_name)
        elif json_output:
            return stats.generate_full_report()
        elif by_season:
            stats.print_season_breakdown_table()
            return None
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
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='NBA Database Statistics Tool')
    parser.add_argument('--json', action='store_true', help='Output full report as JSON')
    parser.add_argument('--table', type=str, help='Get detailed insights for specific table')
    parser.add_argument('--summary', action='store_true', default=True, help='Show summary report (default)')
    parser.add_argument('--by-season', action='store_true', help='Show games by season and type (regular/playoff/playin)')
    
    # Database selection flags
    db_group = parser.add_mutually_exclusive_group()
    db_group.add_argument('--local', action='store_true', help='Use local PostgreSQL database')
    db_group.add_argument('--neon', action='store_true', help='Use Neon cloud database')
    
    args = parser.parse_args()
    
    # Determine database URL
    database_url = None
    if args.local:
        database_url = "postgresql://brendan@localhost:5432/nba_pbp"
        print("Using LOCAL PostgreSQL database...")
    elif args.neon:
        # Force use of Neon URL from .env file, ignore system env var
        neon_url = "postgresql://nba_pbp_owner:npg_3wBZK4JXYVIR@ep-nameless-morning-a88pbjet-pooler.eastus2.azure.neon.tech/nba_pbp?sslmode=require"
        database_url = neon_url
        print("Using NEON cloud database...")
    else:
        # Default behavior - use .env file setting
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            if 'localhost' in database_url:
                print("Using LOCAL PostgreSQL database (from .env)...")
            else:
                print("Using NEON cloud database (from .env)...")
        else:
            print("Using default database connection...")
    
    try:
        if args.table:
            # Show specific table insights
            result = run_database_stats(table_name=args.table, database_url=database_url)
            print(json.dumps(result, indent=2, default=str))
        elif args.json:
            # Full JSON report
            result = run_database_stats(json_output=True, database_url=database_url)
            print(json.dumps(result, indent=2, default=str))
        elif args.by_season:
            # Show games by season breakdown
            run_database_stats(by_season=True, database_url=database_url)
        else:
            # Human-readable summary
            run_database_stats(summary=True, database_url=database_url)
            
    except KeyboardInterrupt:
        print("\nReport generation interrupted by user")
    except Exception as e:
        print(f"Error generating report: {e}")


if __name__ == "__main__":
    main()

# Module execution support
if __name__ == "__main__" or __name__ == "src.database.database_stats":
    if len(sys.argv) == 1 and __name__ == "src.database.database_stats":
        # When run as module without args, show summary
        run_database_stats(summary=True)