"""
WNBA Game URL Generator
Generates comprehensive queue of all WNBA game URLs from 1997-2025
"""
import os
import json
import asyncio
import aiohttp
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import json

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Get the absolute path to the directory containing the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class GameURLInfo:
    """Information about a game URL for the queue."""
    game_id: str
    season: str
    game_url: str
    game_type: str = 'regular'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database insertion."""
        return asdict(self)


class GameURLGenerator:
    """Generates WNBA game URLs for systematic scraping."""

    BASE_URL = "https://www.wnba.com"

    GAMES_REGULAR_FP = os.path.join(SCRIPT_DIR, "wnba-games-regular.csv")
    GAMES_PLAYOFF_FP = os.path.join(SCRIPT_DIR, "wnba-games-playoff.csv")

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize generator with database session."""
        self.regular_season_df = pd.read_csv(self.GAMES_REGULAR_FP)
        self.playoff_df = pd.read_csv(self.GAMES_PLAYOFF_FP)

    def generate_game_url(self, game_id: str) -> str:
        """Generate WNBA.com game URL from team codes and game ID."""
        return f"{self.BASE_URL}/game/{game_id}/playbyplay"

    def generate_game_ids(self, type: str, season: int) -> List[str]:
        """Generate game IDs for regular season or playoffs based on a season."""
        if type == "regular":
            return self.generate_regular_season_ids(season)
        elif type == "playoff":
            return self.generate_playoff_ids(season)
        return []

    def generate_regular_season_ids(self, season: int) -> List[str]:
        """Generate game IDs for regular season based on a season."""
        total_games = self.regular_season_df[self.regular_season_df['season'] == season]['total_regular_games'].values[0]
        id_prefix = str(self.regular_season_df[self.regular_season_df['season'] == season]['id_prefix'].values[0])
        game_ids = []
        for i in range(1, total_games + 1):
            if season == 2020:
                # Game ID will be a 5 digit number starting with 1
                game_ids.append(id_prefix + "01" + str(i).zfill(3))
            else:
                game_ids.append(id_prefix + str(i).zfill(5))
        return game_ids

    def generate_playoff_ids(self, season: int) -> List[str]:
        """Generate game IDs for playoffs based on a season."""
        # Key data
        df_row = self.playoff_df[self.playoff_df['season'] == season]
        best_of = df_row['best_of'].values[0].split(",")
        id_prefix = str(df_row['id_prefix'].values[0])
        game_ids = []

        # Big split between game IDs from 1997-2001, and 2002-Present
        if season < 2002:
            id_range_by_season = {
                1997: "3",
                1998: "9",
                1999: "11",
                2000: "21",
                2001: "21",
            }
            for i in range(1, id_range_by_season[season] + 1):
                game_ids.append(id_prefix + str(i).zfill(5))

            return game_ids
        else:
            best_of = df_row['best_of'].values[0].split(",")
            num_series = df_row['num_series'].values[0].split(",")
            num_rounds = len(best_of)

            # Generate game IDs
            for i in range(1, num_rounds + 1): # Round (base-1)
                for j in range(int(num_series[i-1])): # Series (base-0)
                    for k in range(1, int(best_of[i-1]) + 1): # Game (base-1)
                        game_ids.append(id_prefix + str(i).zfill(3) + str(j) + str(k))

            return game_ids

    def generate_regular_season_game_urls(self, season: int = None):
        """Generate game URLs for regular season based on a season."""
        # Get all seasons from the CSV
        if not season:
            seasons = self.regular_season_df['season'].unique()
        else:
            seasons = [season]

        game_urls = []
        for season in seasons:
            game_ids = self.generate_regular_season_ids(season)
            for game_id in game_ids:
                game_urls.append(self.generate_game_url(game_id))
        return game_urls

    def generate_playoff_game_urls(self, season: int = None):
        """Generate game URLs for playoffs based on a season."""
        # Get all seasons from the CSV
        if not season:
            seasons = self.playoff_df['season'].unique()
        else:
            seasons = [season]
        game_urls = []
        for season in seasons:
            game_ids = self.generate_playoff_ids(season)
            for game_id in game_ids:
                game_urls.append(self.generate_game_url(game_id))
        return game_urls

    def generate_all_urls(self):
        """Generate URLs for all seasons."""
        return self.generate_regular_season_game_urls() + self.generate_playoff_game_urls()

    def generate_all_ids(self):
        """Generate IDs for all seasons."""
        ids = []
        for season in self.regular_season_df['season'].unique():
            ids.extend(self.generate_regular_season_ids(season))
        for season in self.playoff_df['season'].unique():
            ids.extend(self.generate_playoff_ids(season))

        print(len(ids))
        return ids

    def validate_game_url(self, game_url: str):
        """Validate a game URL."""
        try:
            response = requests.get(game_url)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating game URL {game_url}: {e}")
            return False

    def validate_play_by_play(self, game_url: str):
        """Validate a play by play URL."""
        try:
            response = requests.get(game_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Check if the page contains the play by play data in __NEXT_DATA__
            if soup.find('script', {'id': '__NEXT_DATA__'}) is None:
                return False
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating play by play URL {game_url}: {e}")
            return False

    def get_game_data(self, game_url: str):
        """Get game data from a game URL."""
        response = requests.get(game_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        data = soup.find('script', {'id': '__NEXT_DATA__'})
        game_json = json.loads(data.text)
        game_data = game_json['props']['pageProps']

        return game_data

    def save_game_data(self, game_url: str, fp: str):
        """Save game data to a file."""
        game_data = self.get_game_data(game_url)
        with open(fp, "w") as f:
            json.dump(game_data, f, indent=2)

def main():  # pragma: no cover
    """Example usage of the GameURLGenerator."""
    generator = GameURLGenerator()

    try:

        # Test with a single season first
        games = generator.generate_game_ids("regular", 2025)
        print(f"Sample game ID: {games[0]}, {games[-1]}")

        # Generate game URLs
        game_urls = generator.generate_regular_season_game_urls(2025)

        # Expect 286 game URLs
        print(f"Sample game URL: {game_urls[0]}, {game_urls[-1]}")

        # Expect 6166 game URLs (1997-2025)
        regular_season_game_urls = generator.generate_regular_season_game_urls()
        print(f"Total regular season game URLs: {len(regular_season_game_urls)}")
        print(f"Sample regular season game URL: {regular_season_game_urls[0]}, {regular_season_game_urls[-1]}")

        # Generate playoff game URLs
        playoff_game_urls = generator.generate_playoff_game_urls()
        print(f"Total playoff game URLs: {len(playoff_game_urls)}")
        print(f"Sample playoff game URL: {playoff_game_urls[0]}, {playoff_game_urls[-1]}")

        test_urls = []

        print(f"Regular season game URLs: {regular_season_game_urls[0]}")

        test_urls.append(regular_season_game_urls[0])
        test_urls.append(regular_season_game_urls[-1])
        test_urls.append(playoff_game_urls[0])
        test_urls.append(playoff_game_urls[7]) # Invalid URL test
        test_urls.append(playoff_game_urls[-1])

        num_valid = 0
        num_invalid = 0
        for url in test_urls:
            if generator.validate_game_url(url) and generator.validate_play_by_play(url):
                num_valid += 1
                save_path = f"game_data_{url.split('/')[-2]}.json"
                game_data = generator.save_game_data(url, save_path)
                print(f"Saved game data to {save_path}")

            else:
                num_invalid += 1
                print(f"Invalid game URL: {url}")

        print(f"Valid game URLs: {num_valid}")
        print(f"Invalid game URLs: {num_invalid}")

        # Generate regular season, playoff, and all game IDs
        regular_season_game_urls = generator.generate_regular_season_game_urls()
        playoff_game_urls = generator.generate_playoff_game_urls()
        all_game_urls = generator.generate_all_ids()
        print(f"Total regular season game IDs: {len(regular_season_game_urls)}")
        print(f"Total playoff game IDs: {len(playoff_game_urls)}")
        print(f"Total game IDs: {len(all_game_urls)}")
        print(f"Sample game ID: {all_game_urls[0]}, {all_game_urls[-1]}")

    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()