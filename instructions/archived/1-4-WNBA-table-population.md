# WNBA Table Population Implementation Plan

## Overview
Plan to create a data processing pipeline that extracts structured data from the `raw_game_data` table's JSON column and populates the 8 new normalized tables (arena, team, game, person, person_game, team_game, play, boxscore).

## Current State
- 8 new tables created with proper schema and relationships
- Raw JSON game data stored in `raw_game_data.game_data` (JSONB column)
- Test data available in `/tests/test_data/` with 5 sample games

## Implementation Strategy

### Phase 1: Data Extraction Services
Create service classes to extract and transform JSON data into table records.

#### 1.1 Create JSON Data Extractors
**File**: `src/database/json_extractors.py`

**Classes to implement:**
- `ArenaExtractor` - Extract arena data from `.boxscore.arena`
- `TeamExtractor` - Extract team data from various teamId references
- `GameExtractor` - Extract game data from `.boxscore`
- `PersonExtractor` - Extract person data from players/officials
- `PlayExtractor` - Extract play-by-play from `.postGameData.postPlayByPlayData[].actions[]`
- `BoxscoreExtractor` - Extract stats from `.postGameData.postBoxscoreData`

#### 1.2 Create Population Services
**File**: `src/database/population_services.py`

**Services to implement:**
- `GamePopulationService` - Orchestrates the full game population process
- `BulkInsertService` - Handles efficient bulk insertions with conflict resolution
- `DataValidationService` - Validates extracted data before insertion

### Phase 2: Data Processing Pipeline

#### 2.1 Processing Order (Due to Foreign Key Dependencies)
1. **Arena** - Independent table, no dependencies
2. **Team** - Independent table, no dependencies  
3. **Person** - Independent table, no dependencies
4. **Game** - Depends on Arena (arena_id FK)
5. **TeamGame** - Depends on Game and Team
6. **PersonGame** - Depends on Game, Person, and Team
7. **Play** - Depends on Game, Person, and Team
8. **Boxscore** - Depends on Game, Person, and Team

#### 2.2 Data Deduplication Strategy
- **Arena**: Use `arena_id` as natural key
- **Team**: Use `team_id` as natural key, handle franchise changes
- **Person**: Use `person_id` as natural key
- **Game**: Use `game_id` as natural key
- **Junction tables**: Check for existing relationships before inserting

### Phase 3: Implementation Details

#### 3.1 Arena Population
**Source**: `.boxscore.arena`
```python
def extract_arena(game_json: dict) -> dict:
    arena_data = game_json['boxscore']['arena']
    return {
        'arena_id': arena_data['arenaId'],
        'arena_city': arena_data['arenaCity'],
        'arena_name': arena_data['arenaName'],
        'arena_state': arena_data['arenaState'],
        'arena_country': arena_data['arenaCountry'],
        'arena_timezone': arena_data['arenaTimezone'],
        'arena_postal_code': arena_data['arenaPostalCode'],
        'arena_street_address': arena_data['arenaStreetAddress']
    }
```

#### 3.2 Team Population
**Sources**: Multiple locations with `teamId` references
- `.boxscore.homeTeam.teamId` and `.boxscore.awayTeam.teamId`
- `.postGameData.postPlayByPlayData[].actions[].teamId`
- Team names/tricodes from existing team mapping or API calls

#### 3.3 Person Population  
**Sources**: Players and officials
- `.boxscore.homeTeam.players[]` and `.boxscore.awayTeam.players[]`
- `.boxscore.officials[]`
- `.postGameData.postPlayByPlayData[].actions[].personId` (when not 0)

#### 3.4 Game Population
**Source**: `.boxscore`
```python
def extract_game(game_json: dict) -> dict:
    boxscore = game_json['boxscore']
    return {
        'game_id': boxscore['gameId'],
        'game_code': boxscore.get('gameCode'),
        'arena_id': boxscore['arena']['arenaId'],
        'game_et': boxscore['gameEt'],
        'game_sellout': bool(boxscore.get('sellout', 0)),
        'home_team_id': boxscore['homeTeam']['teamId'],
        'home_team_wins': boxscore['homeTeam']['teamWins'],
        'home_team_losses': boxscore['homeTeam']['teamLosses'],
        'away_team_id': boxscore['awayTeam']['teamId'],
        'away_team_wins': boxscore['awayTeam']['teamWins'],
        'away_team_losses': boxscore['awayTeam']['teamLosses'],
        'game_duration': boxscore.get('duration'),
        'game_label': boxscore.get('gameLabel'),
        'game_attendance': boxscore.get('attendance')
    }
```

#### 3.5 Play Population
**Source**: `.postGameData.postPlayByPlayData[]`
- Iterate through each period's actions array
- Handle nullable `personId` (0 means no person)
- Parse clock format (PT10M00.00S)

#### 3.6 Boxscore Population
**Source**: `.postGameData.postBoxscoreData`
- Handle team-level stats (starters/bench) vs individual player stats
- Map long stat names to abbreviated columns
- Handle nullable `plusMinusPoints` (only for players)

### Phase 4: Error Handling & Data Quality

#### 4.1 Data Validation
- Verify all required foreign keys exist before insertion
- Handle missing/null values appropriately
- Validate data types and constraints
- Log data quality issues for review

#### 4.2 Conflict Resolution
- Use `ON CONFLICT DO NOTHING` for natural key conflicts
- Log when duplicate keys are encountered
- Provide option to update existing records vs skip

#### 4.3 Transaction Management
- Process each game in a separate transaction
- Rollback entire game if any table insertion fails
- Provide progress tracking and resume capability

### Phase 5: Testing & Validation

#### 5.1 Unit Tests
**File**: `tests/test_json_extraction.py`
- Test each extractor with sample JSON data
- Verify data transformation accuracy
- Test edge cases (missing fields, null values)

#### 5.2 Integration Tests
**File**: `tests/test_table_population.py`
- Test full game population pipeline
- Verify foreign key relationships
- Test rollback on errors

#### 5.3 Data Integrity Checks
- Count records in each table after population
- Verify referential integrity
- Compare totals with raw game count

### Phase 6: Execution Scripts

#### 6.1 Population Script
**File**: `src/scripts/populate_game_tables.py`
- Command-line interface for table population
- Options for specific games, date ranges, or full dataset
- Progress tracking and logging
- Resume capability for interrupted runs

#### 6.2 Data Validation Script  
**File**: `src/scripts/validate_populated_data.py`
- Comprehensive data quality checks
- Foreign key integrity validation
- Statistical summaries and data profiling

## Implementation Timeline

1. **Phase 1** (JSON Extractors): Create extraction logic for each table
2. **Phase 2** (Population Services): Build orchestration and bulk insert services
3. **Phase 3** (Pipeline Implementation): Implement full processing pipeline
4. **Phase 4** (Error Handling): Add robust error handling and validation
5. **Phase 5** (Testing): Create comprehensive test suite
6. **Phase 6** (Scripts)**: Build command-line tools for execution

## Success Criteria

- [ ] All 8 tables populated from raw JSON data
- [ ] No foreign key constraint violations
- [ ] Data counts match expected totals from raw games
- [ ] Processing pipeline handles errors gracefully
- [ ] Comprehensive test coverage (>90%)
- [ ] Documentation for running population scripts

## Key Considerations

- **Performance**: Use bulk insertions and batch processing for large datasets
- **Memory Management**: Process games in batches to avoid memory issues
- **Data Consistency**: Ensure all related records for a game are inserted together
- **Monitoring**: Provide detailed logging and progress tracking
- **Recovery**: Allow resuming interrupted population runs