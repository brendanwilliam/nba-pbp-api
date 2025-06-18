#!/usr/bin/env python3
"""
JSON Sample Extractor for Schema Analysis
Randomly extracts sample games from each season for JSON structure analysis
"""

import os
import sys
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.database import get_db
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    print("This script requires the NBA PBP API dependencies to be installed.")
    print("Make sure you're running from the project root with the virtual environment activated.")
    sys.exit(1)


class JSONSampleExtractor:
    """Extract representative JSON samples for schema analysis"""
    
    def __init__(self, output_dir: str = "tests/data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db = next(get_db())
        
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def get_available_seasons(self) -> List[str]:
        """Get all seasons that have JSON data available"""
        try:
            result = self.db.execute(text("""
                SELECT DISTINCT guq.season, COUNT(*) as game_count
                FROM game_url_queue guq
                JOIN raw_game_data rgd ON guq.game_id = rgd.game_id
                WHERE rgd.raw_json IS NOT NULL
                  AND guq.season != '2024-25'  -- Exclude current season in progress
                GROUP BY guq.season
                ORDER BY guq.season
            """))
            
            seasons = []
            for row in result:
                seasons.append(row.season)
                print(f"  {row.season}: {row.game_count:,} games available")
            
            return seasons
        except Exception as e:
            print(f"Error getting available seasons: {e}")
            return []
    
    def sample_games_for_season(self, season: str, regular_season_count: int = 2, playoff_count: int = 1) -> List[Dict]:
        """Sample representative games from a specific season"""
        games = []
        
        # Sample regular season games
        regular_games = self._sample_games_by_type(season, 'regular', regular_season_count)
        games.extend(regular_games)
        
        # Sample playoff games (if available)
        playoff_games = self._sample_games_by_type(season, 'playoff', playoff_count)
        games.extend(playoff_games)
        
        return games
    
    def _sample_games_by_type(self, season: str, game_type: str, count: int) -> List[Dict]:
        """Sample games of specific type from a season"""
        try:
            # Get available games of this type
            result = self.db.execute(text("""
                SELECT 
                    guq.game_id,
                    guq.season,
                    guq.game_type,
                    guq.game_date,
                    guq.home_team,
                    guq.away_team,
                    rgd.raw_json,
                    LENGTH(rgd.raw_json::text) as json_size
                FROM game_url_queue guq
                JOIN raw_game_data rgd ON guq.game_id = rgd.game_id
                WHERE guq.season = :season 
                  AND guq.game_type = :game_type
                  AND rgd.raw_json IS NOT NULL
                ORDER BY RANDOM()
                LIMIT :count
            """), {
                "season": season,
                "game_type": game_type,
                "count": count
            })
            
            games = []
            for row in result:
                games.append({
                    'game_id': row.game_id,
                    'season': row.season,
                    'game_type': row.game_type,
                    'game_date': row.game_date,
                    'home_team': row.home_team,
                    'away_team': row.away_team,
                    'raw_json': row.raw_json,
                    'json_size': row.json_size
                })
            
            if len(games) < count:
                print(f"    Warning: Only found {len(games)} {game_type} games for {season}, requested {count}")
            
            return games
            
        except Exception as e:
            print(f"    Error sampling {game_type} games for {season}: {e}")
            return []
    
    def generate_filename(self, game: Dict) -> str:
        """Generate a descriptive filename for the JSON sample"""
        season_short = game['season'].replace('-', '')  # 1996-97 -> 199697
        game_type_short = game['game_type'][:3]  # regular -> reg, playoff -> pla
        
        # Format date as MMDD
        game_date = game['game_date']
        if isinstance(game_date, str):
            # Parse date string if needed
            from datetime import datetime
            game_date = datetime.strptime(game_date, '%Y-%m-%d').date()
        
        date_str = f"{game_date.month:02d}{game_date.day:02d}"
        
        # Create filename: season_type_teams_date_gameid.json
        filename = f"{season_short}_{game_type_short}_{game['away_team']}-vs-{game['home_team']}_{date_str}_{game['game_id']}.json"
        
        return filename
    
    def save_json_sample(self, game: Dict) -> bool:
        """Save a game's JSON data to file"""
        try:
            filename = self.generate_filename(game)
            filepath = self.output_dir / filename
            
            # Parse JSON to ensure it's valid and pretty-print it
            json_data = game['raw_json']
            if isinstance(json_data, str):
                json_data = json.loads(json_data)
            
            # Save with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            # Print file info
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"    ✓ Saved: {filename} ({file_size_mb:.2f} MB)")
            
            return True
            
        except Exception as e:
            print(f"    ✗ Error saving {game['game_id']}: {e}")
            return False
    
    def extract_samples_for_analysis(self, regular_season_per_season: int = 2, playoff_per_season: int = 1):
        """Extract JSON samples from all available seasons"""
        print("NBA JSON Sample Extractor for Schema Analysis")
        print("=" * 80)
        
        # Get available seasons
        print("\nGetting available seasons...")
        seasons = self.get_available_seasons()
        
        if not seasons:
            print("No seasons with JSON data found!")
            return
        
        print(f"\nFound {len(seasons)} seasons with JSON data")
        print(f"Extracting {regular_season_per_season} regular season + {playoff_per_season} playoff games per season")
        print(f"Output directory: {self.output_dir.absolute()}")
        
        total_extracted = 0
        successful_seasons = 0
        
        for season in seasons:
            print(f"\n📅 Processing {season}...")
            
            # Sample games for this season
            games = self.sample_games_for_season(season, regular_season_per_season, playoff_per_season)
            
            if not games:
                print(f"    ⚠️  No games found for {season}")
                continue
            
            # Save each game's JSON
            season_extracted = 0
            for game in games:
                if self.save_json_sample(game):
                    season_extracted += 1
                    total_extracted += 1
            
            if season_extracted > 0:
                successful_seasons += 1
                print(f"    ✅ {season}: {season_extracted} games extracted")
            else:
                print(f"    ❌ {season}: Failed to extract any games")
        
        # Summary
        print(f"\n" + "=" * 80)
        print("EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Seasons processed: {len(seasons)}")
        print(f"Seasons with successful extractions: {successful_seasons}")
        print(f"Total JSON files created: {total_extracted}")
        print(f"Average files per season: {total_extracted / max(successful_seasons, 1):.1f}")
        
        if total_extracted > 0:
            print(f"\n📁 Sample files saved to: {self.output_dir.absolute()}")
            print("\nThese samples can now be used for:")
            print("  • JSON structure analysis")
            print("  • Schema design and evolution tracking")
            print("  • Data type identification")
            print("  • Field completeness assessment")
            print("  • Cross-season comparison")
        else:
            print(f"\n❌ No files were successfully extracted")
    
    def analyze_sample_distribution(self):
        """Analyze the distribution of extracted samples"""
        json_files = list(self.output_dir.glob("*.json"))
        
        if not json_files:
            print("No JSON sample files found for analysis")
            return
        
        print(f"\nSample Distribution Analysis")
        print("-" * 50)
        
        # Group by season and type
        by_season = {}
        by_type = {'reg': 0, 'pla': 0}
        
        for file in json_files:
            parts = file.stem.split('_')
            if len(parts) >= 2:
                season = parts[0]  # 199697
                game_type = parts[1]  # reg, pla
                
                if season not in by_season:
                    by_season[season] = {'reg': 0, 'pla': 0}
                
                by_season[season][game_type] = by_season[season].get(game_type, 0) + 1
                by_type[game_type] = by_type.get(game_type, 0) + 1
        
        print(f"Total files: {len(json_files)}")
        print(f"Regular season: {by_type.get('reg', 0)}")
        print(f"Playoff: {by_type.get('pla', 0)}")
        print(f"Seasons covered: {len(by_season)}")
        
        # Show per-season breakdown
        print(f"\nPer-season breakdown:")
        for season_code in sorted(by_season.keys()):
            reg_count = by_season[season_code].get('reg', 0)
            pla_count = by_season[season_code].get('pla', 0)
            print(f"  {season_code}: {reg_count} regular, {pla_count} playoff")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract JSON samples for schema analysis')
    parser.add_argument('--regular-games', type=int, default=2, 
                       help='Number of regular season games per season (default: 2)')
    parser.add_argument('--playoff-games', type=int, default=1,
                       help='Number of playoff games per season (default: 1)')
    parser.add_argument('--output-dir', type=str, default='tests/data',
                       help='Output directory for JSON files (default: tests/data)')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze existing samples, don\'t extract new ones')
    
    args = parser.parse_args()
    
    extractor = JSONSampleExtractor(args.output_dir)
    
    try:
        if args.analyze_only:
            extractor.analyze_sample_distribution()
        else:
            extractor.extract_samples_for_analysis(
                regular_season_per_season=args.regular_games,
                playoff_per_season=args.playoff_games
            )
            extractor.analyze_sample_distribution()
            
    except KeyboardInterrupt:
        print("\nExtraction interrupted by user")
    except Exception as e:
        print(f"Error during extraction: {e}")
    finally:
        extractor.close()


if __name__ == "__main__":
    main()