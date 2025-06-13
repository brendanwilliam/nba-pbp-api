# nba-pbp-api
Date: 2025-06-13
Author: Brendan Keane
Purpose: To create an API for NBA play-by-play data.

## Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database

### Development Setup
1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and configuration
   ```
5. Set up your PostgreSQL database (see Database section below)

### Project Goal
This project's goal is to scrape all NBA play-by-play data from the NBA's website and to save it in a PostgreSQL database. The API will then be used to query the database for specific play-by-play data.

### Current Status
- [x] Set up virtual environment
- [x] Set up local PostgreSQL database (titled `nba_pbp`)
- [x] Set up web scraping
- [x] Create tests for web scraping

## Scraping
All scraper scripts for this project are located in the `scrapers` directory. The procedure for scraping is as follows:

### 1. Search the NBA's game page for all games played on a specific date.
The NBA website allows users to look up games by date. The URL for this page is `https://www.nba.com/games?date={date}` where `{date}` is the date in the format `YYYY-MM-DD`. For example, all games played on June 11th, 2025 will be found at `https://www.nba.com/games?date=2025-06-11`.

The game URLs on this page are found in the `main` and have a URL structure of `https://www.nba.com/game/{awayTeamTricode}-{homeTeamTricode}-{gameId}` where `{awayTeamTricode}` is the away team's tricode, `{homeTeamTricode}` is the home team's tricode, and `{gameId}` is the game ID. For example, the game between the Boston Celtics and the Orlando Magic on April 9th, 2025 will be found at `https://www.nba.com/game/bos-vs-orl-0022401156`.

### 2. Process URLs for a given date.
There will be a number of links on the page with the URL structure of `https://www.nba.com/game/{awayTeamTricode}-{homeTeamTricode}-{gameId}` with suffixes like `?watchfullgame` or `/boxscore#boxscore`. We want to scrape a set of URLs that end in `{gameId}`. These will be added to our scraping queue.

The scraping queue will save the game ID, away team ID, home team ID, game date, and game URL to a table in the database. The scraping queue will also keep the status of whether the game has been scraped or not.

### 3. Scrape game URLs.
For each game in the scraping queue, we will scrape the game URL and save the full JSON at `#__NEXT_DATA__` to a table in the database. This JSON not only contains play-by-play data, but also box score and event metadata. We will use this data to populate our database tables.

### 4. Populate database tables.
For each game that has been scraped, we will populate our database tables with the data from the JSON at `#__NEXT_DATA__`. The database schema for this will depend on what data is present in these JSON files. We will create a strategy for this later.


## Database
We will use a PostgreSQL database to store the scraped data locally. Once we scrape all games from 1996 to 2025, we will have a complete dataset of NBA play-by-play data. We will then upload this database to the cloud and make it accessible via our API.

## API
The API will be used to query the database for specific play-by-play data. The goal is that we can query the API for plays by team, player, game, game time, date, shot clock, score difference, score totals, etc. All of this data is present in the JSON at `#__NEXT_DATA__` and more specifically play-by-play events.

## MCP
In addition to the API, we will also create a MCP server to serve users play-by-play data when they are working with a LLM. The MCP server will take in natural language queries and return play-by-play data in a format that is easy for the LLM to understand.
