#!/usr/bin/env python3
"""
NBA Mass Scraping Monitor
Real-time monitoring and reporting for scraping progress
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import logging

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scrapers.mass_scraping_queue import GameScrapingQueue
from core.database import get_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrapingMonitor:
    """Real-time monitoring for mass scraping operations"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.queue_manager = GameScrapingQueue(db_url)
        
    async def initialize(self):
        """Initialize the monitor"""
        await self.queue_manager.initialize()
        
    async def close(self):
        """Close the monitor"""
        await self.queue_manager.close()
        
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        # Get queue statistics
        queue_stats = await self.queue_manager.get_queue_statistics()
        
        # Get season progress
        season_progress = await self.queue_manager.get_season_progress()
        
        # Get recent failed games for analysis
        failed_games = await self.queue_manager.get_failed_games_analysis(50)
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(queue_stats, season_progress)
        
        # Get error analysis
        error_analysis = self._analyze_errors(failed_games)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'queue_statistics': queue_stats,
            'season_progress': season_progress,
            'performance_metrics': performance_metrics,
            'error_analysis': error_analysis,
            'recent_failures': failed_games[:10]  # Just top 10 for display
        }
        
    async def display_dashboard(self):
        """Display real-time dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        data = await self.get_dashboard_data()
        
        print("=" * 80)
        print("🏀 NBA MASS SCRAPING MONITOR")
        print("=" * 80)
        print(f"Updated: {data['timestamp']}")
        print()
        
        # Queue Status
        queue_counts = data['queue_statistics']['queue_counts']
        total = queue_counts['total']
        
        print("📊 QUEUE STATUS")
        print("-" * 40)
        print(f"Total Games:       {total:,}")
        print(f"✅ Completed:       {queue_counts['completed']:,} ({queue_counts['completed']/max(total,1)*100:.1f}%)")
        print(f"⏳ Pending:         {queue_counts['pending']:,} ({queue_counts['pending']/max(total,1)*100:.1f}%)")
        print(f"🔄 In Progress:     {queue_counts['in_progress']:,}")
        print(f"❌ Failed:          {queue_counts['failed']:,} ({queue_counts['failed']/max(total,1)*100:.1f}%)")
        print(f"🚫 Invalid:         {queue_counts['invalid']:,} ({queue_counts['invalid']/max(total,1)*100:.1f}%)")
        print()
        
        # Performance Metrics
        perf = data['performance_metrics']
        print("🚀 PERFORMANCE")
        print("-" * 40)
        print(f"Completion Rate:   {perf['completion_percentage']:.1f}%")
        if perf['estimated_completion']:
            print(f"Est. Completion:   {perf['estimated_completion']}")
        if perf['current_rate_per_hour'] > 0:
            print(f"Current Rate:      {perf['current_rate_per_hour']:.0f} games/hour")
        if data['queue_statistics']['performance'].get('avg_response_time_ms'):
            avg_time = data['queue_statistics']['performance']['avg_response_time_ms']
            print(f"Avg Response:      {avg_time:.0f}ms")
        if data['queue_statistics']['performance'].get('total_data_mb'):
            total_mb = data['queue_statistics']['performance']['total_data_mb']
            print(f"Data Collected:    {total_mb:.1f} MB")
        print()
        
        # Season Progress (top 5 seasons by progress)
        print("📅 SEASON PROGRESS (Top 5)")
        print("-" * 40)
        seasons = sorted(data['season_progress'], 
                        key=lambda x: x['completion_percentage'], 
                        reverse=True)[:5]
        
        for season in seasons:
            progress = season['completion_percentage']
            completed = season['completed']
            total_games = season['total_games']
            print(f"{season['season']:>8}: {progress:>5.1f}% ({completed:>4}/{total_games:>4})")
        print()
        
        # Error Analysis
        if data['error_analysis']['error_types']:
            print("⚠️  ERROR ANALYSIS")
            print("-" * 40)
            for error_type, count in list(data['error_analysis']['error_types'].items())[:5]:
                print(f"{error_type:>20}: {count:>3}")
            print()
        
        # Recent Failures
        if data['recent_failures']:
            print("🔍 RECENT FAILURES")
            print("-" * 40)
            for failure in data['recent_failures'][:5]:
                game_id = failure['game_id']
                season = failure['season']
                error = failure['error_message'][:40] + "..." if len(failure['error_message']) > 40 else failure['error_message']
                print(f"{game_id} ({season}): {error}")
            print()
        
        print("Press Ctrl+C to exit")
        
    async def continuous_monitor(self, refresh_seconds: int = 30):
        """Run continuous monitoring with auto-refresh"""
        try:
            while True:
                await self.display_dashboard()
                await asyncio.sleep(refresh_seconds)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            
    async def export_report(self, filename: str = None):
        """Export detailed report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraping_report_{timestamp}.json"
            
        data = await self.get_dashboard_data()
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        print(f"Report exported to: {filename}")
        
    def _calculate_performance_metrics(self, queue_stats: Dict, season_progress: List[Dict]) -> Dict[str, Any]:
        """Calculate performance metrics"""
        queue_counts = queue_stats['queue_counts']
        total = queue_counts['total']
        completed = queue_counts['completed']
        
        completion_percentage = (completed / max(total, 1)) * 100
        
        # Calculate current rate from recent completions
        rate_data = queue_stats.get('rate', {})
        completed_last_hour = rate_data.get('completed_last_hour', 0)
        completed_last_day = rate_data.get('completed_last_day', 0)
        
        current_rate_per_hour = completed_last_hour
        
        # Estimate completion time
        remaining = queue_counts['pending'] + queue_counts['in_progress']
        estimated_completion = None
        
        if current_rate_per_hour > 0 and remaining > 0:
            hours_remaining = remaining / current_rate_per_hour
            estimated_completion = (datetime.now() + timedelta(hours=hours_remaining)).strftime("%Y-%m-%d %H:%M")
        
        return {
            'completion_percentage': completion_percentage,
            'current_rate_per_hour': current_rate_per_hour,
            'estimated_completion': estimated_completion,
            'completed_last_hour': completed_last_hour,
            'completed_last_day': completed_last_day
        }
        
    def _analyze_errors(self, failed_games: List[Dict]) -> Dict[str, Any]:
        """Analyze error patterns"""
        error_types = {}
        error_codes = {}
        
        for game in failed_games:
            # Count error messages
            error_msg = game.get('error_message', 'Unknown')
            if error_msg in error_types:
                error_types[error_msg] += 1
            else:
                error_types[error_msg] = 1
                
            # Count error codes
            error_code = game.get('error_code')
            if error_code:
                if error_code in error_codes:
                    error_codes[error_code] += 1
                else:
                    error_codes[error_code] = 1
        
        # Sort by frequency
        error_types = dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True))
        error_codes = dict(sorted(error_codes.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'error_types': error_types,
            'error_codes': error_codes,
            'total_failed_analyzed': len(failed_games)
        }


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NBA Scraping Monitor')
    parser.add_argument('--refresh', type=int, default=30, help='Refresh interval in seconds')
    parser.add_argument('--once', action='store_true', help='Show dashboard once and exit')
    parser.add_argument('--export', type=str, help='Export report to JSON file')
    parser.add_argument('--db-url', type=str, help='Database URL (overrides environment)')
    
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or get_database_url()
    if not db_url:
        logger.error("Database URL not provided and not found in environment")
        sys.exit(1)
    
    # Create monitor
    monitor = ScrapingMonitor(db_url)
    
    try:
        await monitor.initialize()
        
        if args.export:
            await monitor.export_report(args.export)
        elif args.once:
            await monitor.display_dashboard()
        else:
            await monitor.continuous_monitor(args.refresh)
            
    except Exception as e:
        logger.error(f"Error in monitoring: {e}")
        sys.exit(1)
        
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())