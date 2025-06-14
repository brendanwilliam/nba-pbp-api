# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an NBA play-by-play data API project that scrapes game data from the official NBA website, stores it in PostgreSQL, and provides both REST API and MCP server interfaces for querying the data.

## Claude Code Guidelines
- Before writing code, write your plan to `instructions/` as a markdown file. After writing the plan, write your code to a branch that has the same name as the plan.
- After writing your code, write a summary of what you did to `instructions/` as a markdown file.
- After writing your code, push your code to GitHub and create a pull request to the main branch.
- After the pull request is merged, delete the branch.
- Once the branch is deleted, move the instructions to `instructions/archived/`.

## Architecture

The project follows a modular architecture:

- **src/scrapers/**: Web scraping logic for NBA.com game data
  - Scrapes from `nba.com/games?date={YYYY-MM-DD}` to find game URLs
  - Extracts data from `#__NEXT_DATA__` JSON in game pages
  - Manages scraping queue with status tracking

- **src/core/**: Core business logic and data models

- **src/api/**: RESTful API endpoints for querying scraped data
  - Query plays by team, player, game, time, date, shot clock, score

- **src/analytics/**: Data analysis and insights generation

- **Database**: PostgreSQL for storing games, play-by-play events, box scores, and metadata

## Development Setup

This is a Python project. When setting up:

1. Create and activate a virtual environment before any Python operations
2. Database configuration will be needed for PostgreSQL connection
3. The project will require web scraping libraries for NBA.com data extraction

## Key Implementation Details

- The NBA.com game pages contain play-by-play data in a `#__NEXT_DATA__` script tag as JSON
- Game URLs follow the pattern: `nba.com/game/{away_team}-vs-{home_team}-{game_id}`
- The scraper needs to handle a queue system to track scraping status and manage the large volume of games (1996-2025)
- The MCP server will translate natural language queries to database queries for LLM integration

## Current Status
Please use this section to keep track of high-level objectives and their status. Copy the contents over to `README.md` whenever you update this section.

### Objectives
- [x] Create plans for all objectives
- [ ] Start small batch test scraping of NBA.com game pages (December, 2024) to ensure functionality
- [ ] Create a systematic plan to scrape all games from the 1996-97 season to the 2024-25 season
- [ ] Scrape all game URLs and add them to the scraping queue
- [ ] Scrape all games in the scraping queue and save the JSON at `#__NEXT_DATA__` to the database
- [ ] Analyze the JSON data and design database schema that captures all endpoints from the JSON
- [ ] Implement the database schema
- [ ] Use JSON data to populate the tables in the database
- [ ] Migrate the database to the cloud
- [ ] Create REST API endpoints for querying the database
- [ ] Create MCP server for LLM integration
- [ ] Create documentation for the API and MCP server
- [ ] Create a website for testing the API and MCP server
- [ ] Plan how to create a userbase for the API and MCP servers
- [ ] Plan how to make money from the API and MCP servers
- [ ] Plan how to scale the API and MCP servers
- [ ] Plan how to maintain the API and MCP servers
- [ ] Plan how to update the API and MCP servers

