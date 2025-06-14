"""
Progress Monitoring for Systematic NBA Scraping
Provides real-time monitoring and reporting of scraping progress
"""

import asyncio
import asyncpg
from datetime import datetime
from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import logging

logger = logging.getLogger(__name__)


class ScrapingMonitor:
    """Monitor and display scraping progress"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.console = Console()
        self.pool = None
        
    async def initialize(self):
        """Initialize database connection"""
        self.pool = await asyncpg.create_pool(self.db_url)
        
    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            
    async def get_overall_stats(self) -> Dict:
        """Get overall scraping statistics"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'invalid') as invalid,
                    ROUND(COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / NULLIF(COUNT(*), 0), 2) as completion_rate,
                    AVG(response_time_ms) FILTER (WHERE status = 'completed') as avg_response_time,
                    SUM(data_size_bytes) FILTER (WHERE status = 'completed') / 1024.0 / 1024.0 / 1024.0 as total_gb,
                    MIN(created_at) as started_at,
                    MAX(completed_at) FILTER (WHERE status = 'completed') as last_completed
                FROM scraping_queue
            """)
            
            return dict(stats)
            
    async def get_season_progress(self) -> List[Dict]:
        """Get progress by season"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    season,
                    total_games,
                    scraped_games,
                    failed_games,
                    invalid_games,
                    pending,
                    in_progress,
                    progress_percentage,
                    started_at,
                    completed_at
                FROM season_progress_view
                ORDER BY season
            """)
            
            return [dict(r) for r in results]
            
    async def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recently completed games"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    game_id,
                    season,
                    game_date,
                    home_team || ' vs ' || away_team as matchup,
                    completed_at,
                    response_time_ms,
                    data_size_bytes / 1024.0 as size_kb
                FROM scraping_queue
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT $1
            """, limit)
            
            return [dict(r) for r in results]
            
    async def get_error_summary(self) -> List[Dict]:
        """Get summary of errors"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    error_type,
                    COUNT(*) as count,
                    MAX(occurred_at) as last_occurred
                FROM scraping_errors
                GROUP BY error_type
                ORDER BY count DESC
                LIMIT 10
            """)
            
            return [dict(r) for r in results]
            
    async def get_current_rate(self, minutes: int = 60) -> Dict:
        """Get current scraping rate"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as games_completed,
                    COUNT(*) * 60.0 / $1 as games_per_hour,
                    AVG(response_time_ms) as avg_response_time
                FROM scraping_queue
                WHERE status = 'completed'
                AND completed_at > NOW() - INTERVAL '%s minutes'
            """ % minutes, minutes)
            
            return dict(result)
            
    def create_dashboard_table(self, stats: Dict, season_progress: List[Dict]) -> Table:
        """Create a rich table for the dashboard"""
        table = Table(title="NBA Scraping Progress Dashboard", show_header=True)
        
        # Overall stats section
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        # Add overall stats
        table.add_row("Total Games", f"{stats['total_games']:,}")
        table.add_row("Completed", f"{stats['completed']:,} ({stats['completion_rate']:.1f}%)")
        table.add_row("Pending", f"{stats['pending']:,}")
        table.add_row("In Progress", f"{stats['in_progress']:,}")
        table.add_row("Failed", f"{stats['failed']:,}")
        table.add_row("Invalid", f"{stats['invalid']:,}")
        table.add_row("Avg Response Time", f"{stats['avg_response_time']:.0f}ms" if stats['avg_response_time'] else "N/A")
        table.add_row("Total Data", f"{stats['total_gb']:.2f} GB" if stats['total_gb'] else "0 GB")
        
        return table
        
    def create_season_table(self, season_progress: List[Dict]) -> Table:
        """Create a table showing season-by-season progress"""
        table = Table(title="Season Progress", show_header=True)
        
        table.add_column("Season", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Completed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Progress", justify="right")
        
        for season in season_progress:
            progress_pct = season['progress_percentage'] or 0
            progress_bar = self._create_progress_bar(progress_pct)
            
            table.add_row(
                season['season'],
                str(season['total_games']),
                str(season['scraped_games']),
                str(season['failed_games']),
                f"{progress_bar} {progress_pct:.1f}%"
            )
            
        return table
        
    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a text-based progress bar"""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"
        
    async def display_live_dashboard(self, refresh_interval: int = 5):
        """Display a live updating dashboard"""
        with Live(console=self.console, refresh_per_second=1) as live:
            while True:
                try:
                    # Get latest stats
                    stats = await self.get_overall_stats()
                    season_progress = await self.get_season_progress()
                    current_rate = await self.get_current_rate()
                    recent_activity = await self.get_recent_activity(5)
                    
                    # Create tables
                    main_table = self.create_dashboard_table(stats, season_progress)
                    season_table = self.create_season_table(season_progress)
                    
                    # Create rate panel
                    rate_text = (
                        f"Current Rate: {current_rate['games_per_hour']:.1f} games/hour\n"
                        f"Games in last hour: {current_rate['games_completed']}"
                    )
                    rate_panel = Panel(rate_text, title="Performance", border_style="green")
                    
                    # Update display
                    live.update(
                        Panel.fit(
                            f"{main_table}\n\n{season_table}\n\n{rate_panel}",
                            title=f"NBA Scraping Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            border_style="blue"
                        )
                    )
                    
                    await asyncio.sleep(refresh_interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Dashboard error: {e}")
                    await asyncio.sleep(refresh_interval)
                    
    async def generate_report(self, output_file: str = "scraping_report.txt"):
        """Generate a detailed scraping report"""
        stats = await self.get_overall_stats()
        season_progress = await self.get_season_progress()
        errors = await self.get_error_summary()
        
        report_lines = [
            "NBA Scraping Progress Report",
            "=" * 50,
            f"Generated: {datetime.now()}",
            "",
            "Overall Statistics:",
            f"  Total Games: {stats['total_games']:,}",
            f"  Completed: {stats['completed']:,} ({stats['completion_rate']:.1f}%)",
            f"  Failed: {stats['failed']:,}",
            f"  Invalid: {stats['invalid']:,}",
            f"  Data Collected: {stats['total_gb']:.2f} GB",
            "",
            "Season Breakdown:",
        ]
        
        for season in season_progress:
            report_lines.append(
                f"  {season['season']}: {season['scraped_games']}/{season['total_games']} "
                f"({season['progress_percentage']:.1f}%) - "
                f"Failed: {season['failed_games']}, Invalid: {season['invalid_games']}"
            )
            
        if errors:
            report_lines.extend([
                "",
                "Error Summary:",
            ])
            for error in errors:
                report_lines.append(f"  {error['error_type']}: {error['count']} occurrences")
                
        report_content = "\n".join(report_lines)
        
        with open(output_file, 'w') as f:
            f.write(report_content)
            
        self.console.print(f"Report saved to {output_file}")
        return report_content


async def main():
    """Run the monitoring dashboard"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/nba_pbp')
    
    monitor = ScrapingMonitor(db_url)
    await monitor.initialize()
    
    try:
        # Display live dashboard
        await monitor.display_live_dashboard()
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())