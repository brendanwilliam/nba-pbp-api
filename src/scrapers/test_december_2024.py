#!/usr/bin/env python3
"""
Test script for December 2024 NBA game scraping.
Tests scraping functionality on a small batch of games before full-scale operation.
"""

import logging
from datetime import datetime, timedelta
import time
import json
from typing import List, Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.scrapers.scraping_manager import ScrapingManager
from src.scrapers.game_url_scraper import GameURLScraper
from src.scrapers.game_data_scraper import GameDataScraper
from src.core.database import SessionLocal
from src.core.models import Game, ScrapeQueue, RawGameData, Team
from sqlalchemy import func

# Configure logging for detailed analysis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('december_2024_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class December2024TestScraper:
    """Manages test scraping for December 2024 games."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.manager = ScrapingManager(self.session)
        self.url_scraper = GameURLScraper()
        self.data_scraper = GameDataScraper()
        
        # Performance metrics
        self.metrics = {
            'total_games': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'total_time': 0,
            'avg_time_per_game': 0,
            'errors': []
        }
    
    def get_december_dates(self) -> List[str]:
        """Get dates from December 1-15, 2024."""
        start_date = datetime(2024, 12, 1)
        end_date = datetime(2024, 12, 15)
        
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        return dates
    
    def _get_or_create_team(self, tricode: str) -> Team:
        """Get or create a team by tricode."""
        team = self.session.query(Team).filter_by(tricode=tricode).first()
        if not team:
            # Create basic team record - can be enhanced later
            team = Team(
                tricode=tricode,
                name=f"{tricode} Team",  # Placeholder name
                city=tricode  # Placeholder city
            )
            self.session.add(team)
            self.session.flush()
        return team
    
    def collect_test_game_urls(self, limit: int = 30) -> List[Dict[str, str]]:
        """Collect URLs for test games from December 2024."""
        logger.info("Starting URL collection for December 2024 games")
        
        dates = self.get_december_dates()
        all_games = []
        
        for date_str in dates:
            try:
                logger.info(f"Scraping games for {date_str}")
                # Convert string date to date object
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                games = self.url_scraper.get_games_for_date(date_obj)
                all_games.extend(games)
                
                # Add small delay to be respectful
                time.sleep(1)
                
                if len(all_games) >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"Error scraping date {date_str}: {e}")
                self.metrics['errors'].append({
                    'phase': 'url_collection',
                    'date': date_str,
                    'error': str(e)
                })
        
        # Return only the requested number of games
        return all_games[:limit]
    
    def execute_test_scraping(self, games: List[Dict[str, str]]) -> None:
        """Execute scraping on test games with performance monitoring."""
        logger.info(f"Starting test scraping for {len(games)} games")
        
        # First, add games to the database and queue
        # Need to use the manager's method or create our own
        for game_info in games:
            try:
                # Create or get teams first
                home_team = self._get_or_create_team(game_info['home_team_tricode'])
                away_team = self._get_or_create_team(game_info['away_team_tricode'])
                
                # Check if game exists
                existing_game = self.session.query(Game).filter_by(
                    nba_game_id=game_info['nba_game_id']
                ).first()
                
                if not existing_game:
                    # Create game record
                    game = Game(
                        nba_game_id=game_info['nba_game_id'],
                        game_date=datetime.strptime(game_info['game_date'], '%Y-%m-%d').date(),
                        home_team_id=home_team.id,
                        away_team_id=away_team.id,
                        season='2024-25',
                        game_type='Regular Season',
                        game_url=game_info['game_url']
                    )
                    self.session.add(game)
                    self.session.flush()
                    
                    # Add to scrape queue
                    scrape_item = ScrapeQueue(
                        game_id=game.id,
                        status='pending'
                    )
                    self.session.add(scrape_item)
                
                self.session.commit()
                
            except Exception as e:
                logger.error(f"Error adding game to queue: {e}")
                self.session.rollback()
        
        # Get pending games from queue
        limit = len(games) if games else 30  # Default to 30 if no games provided
        pending_games = self.session.query(ScrapeQueue).filter_by(
            status='pending'
        ).limit(limit).all()
        
        self.metrics['total_games'] = len(pending_games)
        
        # Scrape each game with timing
        for queue_item in pending_games:
            start_time = time.time()
            
            try:
                logger.info(f"Scraping game {queue_item.game_id}")
                
                # Update status to in_progress
                queue_item.status = 'in_progress'
                self.session.commit()
                
                # Scrape the game
                # Get the game URL from the related game object
                game = self.session.query(Game).filter_by(id=queue_item.game_id).first()
                game_data = self.data_scraper.scrape_game_data(game.game_url)
                
                if game_data:
                    # Save raw data
                    raw_data = RawGameData(
                        game_id=queue_item.game_id,
                        raw_json=game_data
                    )
                    self.session.add(raw_data)
                    
                    # Update queue status
                    queue_item.status = 'completed'
                    self.metrics['successful_scrapes'] += 1
                else:
                    queue_item.status = 'failed'
                    queue_item.error_message = 'No data returned'
                    self.metrics['failed_scrapes'] += 1
                
                self.session.commit()
                
                # Track timing
                elapsed_time = time.time() - start_time
                self.metrics['total_time'] += elapsed_time
                
                logger.info(f"Game {queue_item.game_id} scraped in {elapsed_time:.2f}s")
                
                # Respectful delay
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping game {queue_item.game_id}: {e}")
                
                queue_item.status = 'failed'
                queue_item.error_message = str(e)
                queue_item.attempts += 1
                self.session.commit()
                
                self.metrics['failed_scrapes'] += 1
                self.metrics['errors'].append({
                    'phase': 'data_scraping',
                    'game_id': queue_item.game_id,
                    'error': str(e)
                })
    
    def validate_scraped_data(self) -> Dict[str, Any]:
        """Validate the quality and completeness of scraped data."""
        logger.info("Starting data validation")
        
        validation_results = {
            'total_raw_data_records': 0,
            'json_structure_consistency': True,
            'play_by_play_completeness': [],
            'data_issues': []
        }
        
        # Get all raw data from the test run
        raw_data_records = self.session.query(RawGameData).all()
        validation_results['total_raw_data_records'] = len(raw_data_records)
        
        json_keys_sets = []
        
        for record in raw_data_records:
            try:
                # Check JSON structure
                if isinstance(record.raw_json, str):
                    data = json.loads(record.raw_json)
                else:
                    data = record.raw_json
                
                # Collect top-level keys for consistency check
                json_keys_sets.append(set(data.keys()))
                
                # Check for play-by-play data
                pbp_found = False
                if 'props' in data and 'pageProps' in data['props']:
                    page_props = data['props']['pageProps']
                    if 'playByPlay' in page_props or 'gameData' in page_props:
                        pbp_found = True
                
                validation_results['play_by_play_completeness'].append({
                    'game_id': record.game_id,
                    'has_play_by_play': pbp_found,
                    'json_size': len(str(record.raw_json))
                })
                
            except Exception as e:
                validation_results['data_issues'].append({
                    'game_id': record.game_id,
                    'issue': f'JSON parsing error: {str(e)}'
                })
        
        # Check JSON structure consistency
        if json_keys_sets:
            first_keys = json_keys_sets[0]
            for keys in json_keys_sets[1:]:
                if keys != first_keys:
                    validation_results['json_structure_consistency'] = False
                    break
        
        return validation_results
    
    def generate_summary_report(self) -> str:
        """Generate a comprehensive summary report of the test run."""
        if self.metrics['successful_scrapes'] > 0:
            self.metrics['avg_time_per_game'] = (
                self.metrics['total_time'] / self.metrics['successful_scrapes']
            )
        
        # Get validation results
        validation = self.validate_scraped_data()
        
        # Calculate success rate
        success_rate = 0
        if self.metrics['total_games'] > 0:
            success_rate = (
                self.metrics['successful_scrapes'] / self.metrics['total_games'] * 100
            )
        
        report = f"""
# December 2024 Test Scraping Summary Report

## Overview
- Test Period: December 1-15, 2024
- Total Games Attempted: {self.metrics['total_games']}
- Successful Scrapes: {self.metrics['successful_scrapes']}
- Failed Scrapes: {self.metrics['failed_scrapes']}
- Success Rate: {success_rate:.1f}%

## Performance Metrics
- Total Scraping Time: {self.metrics['total_time']:.2f} seconds
- Average Time per Game: {self.metrics['avg_time_per_game']:.2f} seconds
- Estimated Time for 1000 Games: {(self.metrics['avg_time_per_game'] * 1000 / 3600):.2f} hours

## Data Quality
- Total Raw Data Records: {validation['total_raw_data_records']}
- JSON Structure Consistent: {'Yes' if validation['json_structure_consistency'] else 'No'}
- Games with Play-by-Play Data: {sum(1 for g in validation['play_by_play_completeness'] if g['has_play_by_play'])}
- Data Issues Found: {len(validation['data_issues'])}

## Error Analysis
- URL Collection Errors: {len([e for e in self.metrics['errors'] if e['phase'] == 'url_collection'])}
- Data Scraping Errors: {len([e for e in self.metrics['errors'] if e['phase'] == 'data_scraping'])}

## Recommendations
"""
        
        # Add recommendations based on results
        if success_rate >= 95:
            report += "- ✅ Success rate exceeds 95% target. Ready for full-scale scraping.\n"
        else:
            report += "- ⚠️ Success rate below 95% target. Investigation needed before scaling.\n"
        
        if self.metrics['avg_time_per_game'] < 5:
            report += "- ✅ Performance is excellent. Current rate limiting is appropriate.\n"
        else:
            report += "- ⚠️ Scraping speed is slower than expected. Consider optimization.\n"
        
        if validation['json_structure_consistency']:
            report += "- ✅ JSON structure is consistent across games.\n"
        else:
            report += "- ⚠️ JSON structure varies between games. Schema design needs flexibility.\n"
        
        # Add detailed error information if any
        if self.metrics['errors']:
            report += "\n## Detailed Errors\n"
            for error in self.metrics['errors'][:10]:  # Show first 10 errors
                report += f"- {error['phase']}: {error.get('game_id', error.get('date', 'N/A'))} - {error['error']}\n"
        
        return report
    
    def run_test(self):
        """Execute the complete test scraping process."""
        logger.info("Starting December 2024 test scraping")
        
        try:
            # Phase 1: Collect URLs
            logger.info("Phase 1: Collecting game URLs")
            games = self.collect_test_game_urls(limit=30)
            logger.info(f"Collected {len(games)} game URLs")
            
            # Phase 2: Execute scraping
            logger.info("Phase 2: Executing scraping")
            self.execute_test_scraping(games)
            
            # Phase 3: Generate report
            logger.info("Phase 3: Generating summary report")
            report = self.generate_summary_report()
            
            # Save report
            with open('december_2024_test_report.md', 'w') as f:
                f.write(report)
            
            logger.info("Test scraping completed. Report saved to december_2024_test_report.md")
            print(report)
            
        except Exception as e:
            logger.error(f"Fatal error during test scraping: {e}")
            raise
        finally:
            self.session.close()


if __name__ == "__main__":
    scraper = December2024TestScraper()
    scraper.run_test()