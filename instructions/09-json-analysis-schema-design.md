# 09 - JSON Analysis and Schema Design

## Objective
Conduct comprehensive analysis of scraped NBA.com JSON data to understand structure, identify all data points, and design an optimized relational database schema that captures the complete dataset.

## Background
With raw JSON data collected from ~30,000 games, this phase focuses on understanding the data structure evolution, identifying all available data points, and designing a normalized database schema that preserves data integrity while enabling efficient querying.

## Scope
- **Data analysis**: Complete JSON structure mapping across all seasons
- **Schema design**: Normalized relational database structure
- **Data cataloging**: Comprehensive field documentation
- **Evolution tracking**: Changes in data structure over time

## Implementation Plan

### Phase 1: JSON Structure Analysis
1. **Sample selection strategy**
   - Representative games from each season (1996-2025)
   - Different game types (regular season, playoffs, special events)
   - Various teams and matchup types
   - High and low-scoring games for data variety

2. **Structure mapping methodology**
   ```python
   def analyze_json_structure(json_data):
       # Recursive structure analysis
       # Field type identification
       # Nested object mapping
       # Array structure analysis
   ```

3. **Evolution tracking**
   - Schema changes by season
   - New field additions over time
   - Deprecated field identification
   - Data format modifications

### Phase 2: Data Point Cataloging
1. **Core game entities identification**
   - Games metadata
   - Teams information
   - Players data
   - Play-by-play events
   - Box score statistics
   - Advanced analytics

2. **Comprehensive field inventory**
   ```
   Games:
   - Basic: game_id, date, home_team, away_team, season
   - Status: period, time_remaining, game_status
   - Scoring: home_score, away_score, period_scores
   
   Play-by-Play:
   - Event: action_type, description, time_elapsed
   - Players: player_id, player_name, team_id
   - Context: score_home, score_away, period, time_remaining
   - Details: shot_type, shot_distance, shot_result
   
   Box Score:
   - Traditional: points, rebounds, assists, steals, blocks
   - Advanced: plus_minus, efficiency_rating, usage_rate
   - Shooting: field_goals, three_pointers, free_throws
   ```

### Phase 3: Relationship Mapping
1. **Entity relationships**
   - Games → Teams (many-to-many)
   - Games → Players (many-to-many through plays)
   - Plays → Players (many-to-one)
   - Plays → Games (many-to-one)

2. **Data dependencies**
   - Play-by-play event ordering
   - Box score aggregation relationships
   - Team roster evolution over seasons

### Phase 4: Database Schema Design

#### Core Tables Structure
```sql
-- Games table
CREATE TABLE games (
    game_id VARCHAR(20) PRIMARY KEY,
    season VARCHAR(10) NOT NULL,
    game_date DATE NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    period INTEGER,
    game_status VARCHAR(20),
    attendance INTEGER,
    arena VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Teams table
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    team_code VARCHAR(3) UNIQUE NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    conference VARCHAR(10),
    division VARCHAR(20),
    active_from DATE,
    active_to DATE
);

-- Players table
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    jersey_number INTEGER,
    position VARCHAR(10),
    height_inches INTEGER,
    weight_lbs INTEGER,
    birth_date DATE,
    debut_season VARCHAR(10)
);

-- Play-by-play events
CREATE TABLE play_events (
    event_id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    period INTEGER NOT NULL,
    time_remaining VARCHAR(10),
    time_elapsed INTEGER, -- seconds from game start
    event_type VARCHAR(50) NOT NULL,
    description TEXT,
    home_score INTEGER,
    away_score INTEGER,
    player_id INTEGER,
    team_id INTEGER,
    event_order INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- Box score statistics
CREATE TABLE player_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    minutes_played INTEGER,
    points INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    fouls INTEGER,
    field_goals_made INTEGER,
    field_goals_attempted INTEGER,
    three_pointers_made INTEGER,
    three_pointers_attempted INTEGER,
    free_throws_made INTEGER,
    free_throws_attempted INTEGER,
    plus_minus INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

#### Advanced Analytics Tables
```sql
-- Shot chart data
CREATE TABLE shot_events (
    shot_id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    game_id VARCHAR(20) NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    shot_type VARCHAR(50),
    shot_zone VARCHAR(50),
    shot_distance DECIMAL(5,2),
    shot_x DECIMAL(8,2),
    shot_y DECIMAL(8,2),
    shot_made BOOLEAN,
    assisted_by_player_id INTEGER,
    FOREIGN KEY (event_id) REFERENCES play_events(event_id),
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

-- Team game statistics
CREATE TABLE team_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    team_id INTEGER NOT NULL,
    is_home_team BOOLEAN NOT NULL,
    points INTEGER,
    field_goals_made INTEGER,
    field_goals_attempted INTEGER,
    three_pointers_made INTEGER,
    three_pointers_attempted INTEGER,
    free_throws_made INTEGER,
    free_throws_attempted INTEGER,
    rebounds_offensive INTEGER,
    rebounds_defensive INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    fouls INTEGER,
    fast_break_points INTEGER,
    points_in_paint INTEGER,
    second_chance_points INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

### Phase 5: Data Quality Framework
1. **Validation rules**
   - Required field identification
   - Data type constraints
   - Range validations (scores, times, etc.)
   - Referential integrity rules

2. **Quality metrics**
   ```python
   class DataQualityMetrics:
       def completeness_score(self, record):
           # Calculate % of non-null required fields
       
       def consistency_score(self, game_data):
           # Validate internal consistency (scores, times)
       
       def accuracy_score(self, game_data):
           # Cross-validate with known facts
   ```

## Analysis Tools and Methodology

### JSON Analysis Scripts
1. **Structure analyzer**
   - Field discovery across all games
   - Data type analysis and consistency
   - Nested structure mapping
   - Evolution tracking by season

2. **Data profiling**
   - Field population rates
   - Value distribution analysis
   - Outlier detection
   - Missing data patterns

3. **Schema generator**
   - Automatic DDL generation
   - Index recommendation
   - Constraint identification
   - Migration script creation

### Quality Assurance Process
1. **Sample validation**
   - Manual verification of key games
   - Cross-reference with official NBA data
   - Statistical consistency checks
   - Historical accuracy validation

2. **Performance testing**
   - Query performance simulation
   - Index effectiveness analysis
   - Storage requirement estimation
   - Scaling projection

## Expected Outcomes

### Documentation Deliverables
1. **Complete data dictionary**
   - All fields with descriptions
   - Data types and constraints
   - Business rules and validations
   - Historical evolution notes

2. **Schema documentation**
   - ERD (Entity Relationship Diagram)
   - Table definitions with relationships
   - Index strategy documentation
   - Performance considerations

3. **Quality assessment report**
   - Data completeness by season
   - Quality metrics and trends
   - Recommendations for handling gaps
   - Validation rule specifications

### Technical Deliverables
1. **Production-ready schema**
   - Optimized table structures
   - Appropriate indexing strategy
   - Constraint definitions
   - Migration scripts

2. **ETL specification**
   - JSON to relational mapping
   - Data transformation rules
   - Error handling procedures
   - Performance optimization guidelines

## Success Criteria
- Complete mapping of all JSON fields across seasons
- Normalized schema design with 3NF compliance
- Comprehensive data quality framework
- Performance-optimized structure for API queries
- Documentation suitable for development team

## Timeline
- **Week 1**: JSON structure analysis and cataloging
- **Week 2**: Schema design and optimization
- **Week 3**: Quality framework development
- **Week 4**: Documentation and validation

## Dependencies
- Completed mass scraping (Plan 08)
- Sample data availability across all seasons
- Database design expertise
- Performance testing environment

## Next Steps
After completion:
1. Database schema implementation (Plan 10)
2. JSON to database migration development (Plan 11)
3. Performance testing and optimization
4. Schema validation with sample data