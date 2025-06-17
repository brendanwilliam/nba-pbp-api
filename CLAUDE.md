# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an NBA play-by-play data API project that scrapes game data from the official NBA website, stores it in PostgreSQL, and provides both REST API and MCP server interfaces for querying the data.

## Running Scripts/Code
Make sure to activate the virtual environment before running any scripts. You can do this by running `source venv/bin/activate` in the root directory of the project.

## Claude Code Guidelines
- Before writing code, write your plan to `instructions/` as a markdown file. After writing the plan, write your code to a branch that has the same name as the plan.
- After writing your code, write a summary of what you did to `instructions/` as a markdown file.
- After writing your code, push your code to GitHub and create a pull request to the main branch.
- After the pull request is merged, delete the branch.
- Once the branch is deleted, move the instructions to `instructions/archived/`.

## Architecture

The project follows a modular architecture with completed and planned components:

### Completed Components ✅

- **src/scrapers/**: Web scraping logic for NBA.com game data
  - `team_mapping.py`: NBA team abbreviation mapping with historical changes (relocations, name changes)
  - `game_url_generator.py`: URL discovery and generation system for all seasons 1996-2025
  - `url_validator.py`: URL accessibility and content validation with concurrent processing
  - `game_data_scraper.py`: JSON data extraction from `#__NEXT_DATA__` script tags
  - `scraping_manager.py`: Coordinated scraping operations with queue management

- **src/core/**: Core business logic and data models
  - `database.py`: Database connection and session management
  - `models.py`: SQLAlchemy models for teams, games, players, queue management

- **src/database/**: Database schema and queue management
  - `queue_schema.sql`: Enhanced scraping queue structure with comprehensive indexing
  - `queue_manager.py`: Queue operations, status tracking, and progress monitoring

- **src/scripts/**: Execution scripts and utilities
  - `build_game_url_queue.py`: Main script for URL queue generation and management
  - `test_queue_offline.py`: Comprehensive testing framework for all components
  - `comprehensive_coverage_report.py`: Gap analysis across all game types and eras
  - `verify_game_id_sequences.py`: Regular season sequence coverage verification
  - `verify_playoff_sequences.py`: Playoff tournament structure validation
  - `retrieve_identified_gaps.py`: Active retrieval of missing games from gap analysis

### Planned Components 📋

- **src/api/**: RESTful API endpoints for querying scraped data
  - Query plays by team, player, game, time, date, shot clock, score

- **src/analytics/**: Data analysis and insights generation

### Database Infrastructure ✅

- **PostgreSQL**: Enhanced schema for storing games, play-by-play events, box scores, and metadata
- **Tables**: `teams`, `games`, `players`, `game_url_queue`, `raw_game_data`, `scrape_queue`
- **Indexing**: Optimized for status, season, date, and priority-based queries
- **Migration System**: Alembic-based schema versioning

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

#### Completed Objectives ✅
- [x] Create plans for all objectives
- [x] Start small batch test scraping of NBA.com game pages (December 2024) to ensure functionality
- [x] Create a systematic plan to scrape all games from the 1996-97 season to the 2024-25 season
- [x] **Build comprehensive game URL queue system (~30,000 games)**
- [x] **Implement team mapping with historical changes (relocations, name changes)**
- [x] **Create URL validation and accessibility testing framework**
- [x] **Set up enhanced database schema with proper indexing**
- [x] **Comprehensive gap analysis and coverage verification system**
- [x] **Automated missing game retrieval and queue completion**

#### In Progress 🔄
- [ ] Execute mass game scraping from populated URL queue (Plan 08)
- [ ] Analyze JSON data and design comprehensive database schema (Plan 09)
- [ ] Implement complete database schema for parsed data (Plan 10)

#### Planned 📋
- [ ] Use JSON data to populate normalized database tables (Plan 11)
- [ ] Migrate database to cloud infrastructure (Plan 12)
- [ ] Create REST API endpoints for querying the database (Plan 13)
- [ ] Create MCP server for LLM integration (Plan 14)
- [ ] Create documentation for the API and MCP server (Plan 15)
- [ ] Create a website for testing the API and MCP server (Plan 16)
- [ ] Plan how to create a userbase for the API and MCP servers (Plan 17)
- [ ] Plan how to make money from the API and MCP servers (Plan 18)
- [ ] Plan how to scale the API and MCP servers (Plan 19)
- [ ] Plan how to maintain the API and MCP servers (Plan 20)
- [ ] Plan how to update the API and MCP servers (Plan 21)

