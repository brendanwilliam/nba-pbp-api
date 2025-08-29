# WNBA JSON Processing Database Plan

## Overview
Plan to add 6 new tables (arena, game, person_game, play, person, boxscore) to the existing WNBA database for processing structured game data from the raw JSON files.

## Current Database Structure
The existing database has 3 tables:
- `database_versions`: Track schema migrations
- `scraping_sessions`: Track scraping operations  
- `raw_game_data`: Store raw JSON game data with JSONB column

## New Tables to Add

### 1. Arena Table
**Source**: `.boxscore.arena`
**Columns**:
- `arena_id` (Integer, Primary Key) - from arenaId
- `arena_city` (String) - from arenaCity
- `arena_name` (String) - from arenaName  
- `arena_state` (String) - from arenaState
- `arena_country` (String) - from arenaCountry
- `arena_timezone` (String) - from arenaTimezone
- `arena_postal_code` (String) - from arenaPostalCode
- `arena_street_address` (String) - from arenaStreetAddress

### 2. Game Table
**Source**: `.boxscore`
**Columns**:
- `game_id` (Integer, Primary Key) - from gameId
- `game_code` (String) - from gameCode  
- `arena_id` (Integer, Foreign Key) - references arena.arena_id
- `game_et` (DateTime) - from gameEt
- `home_team_id` (Integer) - from homeTeam.teamId
- `home_team_wins` (Integer) - from homeTeam.teamWins
- `home_team_losses` (Integer) - from homeTeam.teamLosses
- `away_team_id` (Integer) - from awayTeam.teamId  
- `away_team_wins` (Integer) - from awayTeam.teamWins
- `away_team_losses` (Integer) - from awayTeam.teamLosses
- `game_duration` (String) - from duration
- `game_label` (String) - from gameLabel
- `game_sellout` (Boolean) - from sellout
- `game_attendance` (Integer) - from attendance

### 3. Person Table
**Source**: Extracted from players and officials in boxscore data and actions
**Columns**:
- `person_id` (Integer, Primary Key) - from personId
- `person_name` (String) - from name
- `person_name_i` (String) - from nameI (abbreviated name)
- `person_name_first` (String) - from firstName
- `person_name_family` (String) - from familyName

### 4. PersonGame Table (Junction Table)
**Source**: Relationship between games and persons
**Columns**:
- `person_game_id` (Integer, Primary Key, Auto-generated)
- `game_id` (Integer, Foreign Key) - references game.game_id
- `person_id` (Integer, Foreign Key) - references person.person_id
- `team_id` (Integer, Foreign Key) - from teamId, references team.id

### 5. TeamGame Table (Junction Table)
**Source**: Relationship between games and teams
**Columns**:
- `team_game_id` (Integer, Primary Key, Auto-generated)
- `game_id` (Integer, Foreign Key) - references game.game_id
- `team_id` (Integer, Foreign Key) - references team.id

### 6. Team Table
**Source**: Extracted from teamId in boxscore data and actions (Table added to deal with multiple franchies using the same teamId as league franchises are added, rebranded, and removed)
**Columns**:
- `id` (Integer, Primary Key, Auto-generated)
- `team_id` (Integer) - from teamId
- `team_city` (String) - from teamCity
- `team_name` (String) - from teamName
- `team_tricode` (String) - from teamTricode

### 7. Play Table
**Source**: `.postGameData.postPlayByPlayData[].actions[]`
**Columns**:
- `play_id` (Integer, Primary Key, Auto-generated)
- `game_id` (Integer, Foreign Key) - references game.game_id
- `person_id` (Integer, Foreign Key) - from personId, references person.person_id
- `team_id` (Integer, Foreign Key) - from teamId, references team.id
- `action_id` (Integer) - from actionId
- `action_type` (String) - from actionType
- `sub_type` (String) - from subType
- `period` (Integer) - from period
- `clock` (String) - from clock (format: PT10M00.00S)
- `x_legacy` (Integer) - from xLegacy
- `y_legacy` (Integer) - from yLegacy
- `location` (String) - from location
- `score_away` (String) - from scoreAway
- `score_home` (String) - from scoreHome
- `shot_value` (Integer) - from shotValue
- `shot_result` (String) - from shotResult
- `description` (String) - from description
- `is_field_goal` (Boolean) - from isFieldGoal
- `points_total` (Integer) - from pointsTotal
- `action_number` (Integer) - from actionNumber
- `shot_distance` (Float) - from shotDistance

### 8. Boxscore Table
**Source**: `.postGameData.postBoxscoreData`
**Columns**:
- `boxscore_id` (Integer, Primary Key, Auto-generated)
- `game_id` (Integer, Foreign Key) - references game.game_id
- `team_id` (Integer, Foreign Key) - from teamId references team.id
- `person_id` (Integer, Foreign Key, nullable) - from personId, only for "player" boxType references person.person_id
- `home_away_team` (String) - "h" for home, "a" for away
- `box_type` (String) - "starters", "bench", or "player"
- `min` (String) - from minutes
- `pts` (Integer) - from points
- `reb` (Integer) - from reboundsTotal
- `ast` (Integer) - from assists
- `stl` (Integer) - from steals
- `blk` (Integer) - from blocks
- `pm` (Integer, nullable) - from plusMinusPoints, only for "player" boxType
- `fgm` (Integer) - from fieldGoalsMade
- `fga` (Integer) - from fieldGoalsAttempted
- `fgp` (Float) - from fieldGoalsPercentage
- `3pm` (Integer) - from threePointersMade
- `3pa` (Integer) - from threePointersAttempted
- `3pp` (Float) - from threePointersPercentage
- `ftm` (Integer) - from freeThrowsMade
- `fta` (Integer) - from freeThrowsAttempted
- `ftp` (Float) - from freeThrowsPercentage
- `to` (Integer) - from turnovers
- `pf` (Integer) - from foulsPersonal
- `orebs` (Integer) - from reboundsOffensive
- `drebs` (Integer) - from reboundsDefensive

## Implementation Strategy

1. **Create SQLAlchemy Models**: Add the 6 new table models to `src/database/models.py`
2. **Generate Migration**: Use Alembic to auto-generate migration for new tables
3. **Test Migration**: Verify tables are created correctly and relationships work

## Key Considerations

- Use proper foreign key relationships between tables
- Add appropriate indexes for performance (game_id, person_id, etc.)
- Handle nullable fields appropriately (person_id in boxscore, plus_minus_points)
- Preserve existing raw_game_data table for backup/reference
- Follow existing naming conventions (snake_case for column names)