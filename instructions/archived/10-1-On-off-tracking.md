# Plan 10-1: On/Off Player Tracking System

## Overview

This plan outlines the implementation of an on/off tracking system that can answer the question: "At any given moment in a game (game_id, period, game_clock), which 5 players were on the court for each team?" This forms the foundation for advanced basketball analytics including lineup efficiency, plus/minus statistics, and configuration-based performance analysis.

## Problem Statement

NBA games involve constant player substitutions throughout 4 periods (quarters) of play. To perform meaningful analytics on player combinations, we need to track:

1. **Starting lineups** for each team at the beginning of each period
2. **Substitution events** that change the on-court personnel
3. **Current lineup state** at any point in time during the game
4. **Historical lineup data** for retroactive analysis

## Data Analysis Findings

### JSON Data Structure Analysis

From analyzing NBA JSON data across multiple eras (1996-2024), the key data structures are:

#### Starting Lineups
```json
{
  "game": {
    "homeTeam": {
      "players": [
        {
          "personId": 1627734,
          "firstName": "Luka",
          "familyName": "Doncic", 
          "position": "G",  // Starting players have position
          "jerseyNum": "77"
        }
      ]
    }
  }
}
```

#### Substitution Events
```json
{
  "actionType": "Substitution",
  "description": "SUB: Brooks FOR Ward",
  "personId": 369,           // Player going OUT
  "playerName": "Ward",      // Player going OUT  
  "clock": "PT07M30.00S",    // 7:30 remaining in period
  "period": 1,
  "teamId": 1610612752
}
```

### Key Insights

1. **Player Identification**: `personId` is the primary unique identifier across all seasons
2. **Substitution Format**: Consistent "SUB: [PlayerIn] FOR [PlayerOut]" format for 27+ years
3. **Data Challenge**: JSON fields show player going OUT; incoming player must be parsed from description
4. **Time Format**: `PT07M30.00S` represents countdown clock (7:30 remaining)
5. **Starting Lineups**: Players with `position` field populated are the starting 5

## Implementation Strategy

### Database Schema Enhancement

Add new tables to track on/off status:

```sql
-- Track lineup state at any point in time
CREATE TABLE lineup_states (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    period INTEGER NOT NULL,
    clock_time VARCHAR(20) NOT NULL,  -- PT07M30.00S format
    seconds_elapsed INTEGER NOT NULL, -- For easy querying
    team_id BIGINT NOT NULL,
    player_1_id BIGINT NOT NULL,
    player_2_id BIGINT NOT NULL, 
    player_3_id BIGINT NOT NULL,
    player_4_id BIGINT NOT NULL,
    player_5_id BIGINT NOT NULL,
    lineup_hash VARCHAR(64) NOT NULL, -- MD5 of sorted player IDs
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track individual substitution events
CREATE TABLE substitution_events (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    action_number INTEGER NOT NULL,
    period INTEGER NOT NULL,
    clock_time VARCHAR(20) NOT NULL,
    seconds_elapsed INTEGER NOT NULL,
    team_id BIGINT NOT NULL,
    player_out_id BIGINT NOT NULL,
    player_out_name VARCHAR(100) NOT NULL,
    player_in_id BIGINT NOT NULL,
    player_in_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_lineup_states_game_period_time ON lineup_states(game_id, period, seconds_elapsed);
CREATE INDEX idx_lineup_states_team_time ON lineup_states(team_id, game_id, seconds_elapsed);
CREATE INDEX idx_substitution_events_game ON substitution_events(game_id, period, seconds_elapsed);
```

### Core Algorithm

#### 1. Initialization Phase
```python
def initialize_game_lineups(game_data):
    """Extract starting lineups from game JSON"""
    home_starters = []
    away_starters = []
    
    # Get starting 5 from each team (players with position field)
    for player in game_data['game']['homeTeam']['players']:
        if player.get('position'):  # Starting players have position
            home_starters.append(player['personId'])
    
    for player in game_data['game']['awayTeam']['players']:
        if player.get('position'):
            away_starters.append(player['personId'])
    
    return home_starters, away_starters
```

#### 2. Substitution Processing
```python
def process_substitution(event, current_lineups):
    """Process a substitution event and update lineups"""
    team_id = event['teamId']
    player_out_id = event['personId']
    
    # Parse player coming in from description
    description = event['description']  # "SUB: Brooks FOR Ward"
    player_in_name = description.split(':')[1].split('FOR')[0].strip()
    
    # Find player_in_id by matching name to roster
    player_in_id = find_player_id_by_name(player_in_name, team_id)
    
    # Update lineup
    current_lineups[team_id] = [
        player_in_id if p == player_out_id else p 
        for p in current_lineups[team_id]
    ]
    
    return current_lineups
```

#### 3. Timeline Construction
```python
def build_lineup_timeline(game_data):
    """Build complete timeline of lineup changes for a game"""
    timeline = []
    
    # Initialize with starting lineups
    home_starters, away_starters = initialize_game_lineups(game_data)
    current_lineups = {
        home_team_id: home_starters,
        away_team_id: away_starters
    }
    
    # Add starting lineup states (beginning of each period)
    for period in [1, 2, 3, 4]:  # Handle OT later
        timeline.append(create_lineup_state(
            period=period, 
            clock="PT12M00.00S",
            lineups=current_lineups
        ))
    
    # Process all substitution events chronologically
    substitutions = [
        event for event in game_data['game']['actions'] 
        if event.get('actionType') == 'Substitution'
    ]
    
    for sub_event in sorted(substitutions, key=lambda x: (x['period'], -parse_clock_seconds(x['clock']))):
        current_lineups = process_substitution(sub_event, current_lineups)
        timeline.append(create_lineup_state(
            period=sub_event['period'],
            clock=sub_event['clock'],
            lineups=current_lineups
        ))
    
    return timeline
```

### Query Interface

#### Primary Query Function
```python
def get_players_on_court(game_id, period, clock_time):
    """
    Get the 5 players on court for each team at a specific moment
    
    Args:
        game_id: NBA game ID (e.g., "0022300702")
        period: Quarter number (1-4, 5+ for OT)
        clock_time: Game clock (e.g., "PT07M30.00S" or seconds elapsed)
    
    Returns:
        {
            "home_team": [player_id1, player_id2, player_id3, player_id4, player_id5],
            "away_team": [player_id1, player_id2, player_id3, player_id4, player_id5],
            "home_team_id": 1610612742,
            "away_team_id": 1610612752
        }
    """
    seconds_elapsed = convert_clock_to_seconds(period, clock_time)
    
    # Query most recent lineup state before or at the requested time
    query = """
    SELECT DISTINCT ON (team_id) 
        team_id, player_1_id, player_2_id, player_3_id, player_4_id, player_5_id
    FROM lineup_states 
    WHERE game_id = %s 
        AND (period < %s OR (period = %s AND seconds_elapsed <= %s))
    ORDER BY team_id, period DESC, seconds_elapsed DESC
    """
    
    return execute_query(query, [game_id, period, period, seconds_elapsed])
```

### Data Validation & Quality Assurance

#### Validation Rules
1. **Lineup Completeness**: Each team must have exactly 5 players at all times
2. **Player Uniqueness**: No player can be on court for both teams simultaneously  
3. **Roster Validation**: All on-court players must be on the team roster
4. **Substitution Logic**: Player coming out must currently be on court
5. **Time Continuity**: No gaps in timeline coverage

#### Error Handling
```python
class LineupValidationError(Exception):
    pass

def validate_lineup_state(lineup_state):
    """Validate a lineup state for data quality"""
    for team_id, players in lineup_state.items():
        if len(players) != 5:
            raise LineupValidationError(f"Team {team_id} has {len(players)} players, expected 5")
        
        if len(set(players)) != 5:
            raise LineupValidationError(f"Team {team_id} has duplicate players: {players}")
```

## Edge Cases & Challenges

### 1. Name Parsing Challenges
- **Multiple name formats**: "G. Williams" vs "Grant Williams"
- **Special characters**: International names with accents
- **Nickname usage**: "Giannis" vs "Giannis Antetokounmpo"

**Solution**: Create name mapping table and fuzzy matching algorithm

### 2. Multiple Simultaneous Substitutions
- Teams often make multiple subs during timeouts
- Events may be recorded in quick succession

**Solution**: Process all substitutions with same timestamp as batch operation

### 3. Technical Fouls & Ejections
- Players can be removed from game without substitution event
- Must track ejections and technical foul accumulations

**Solution**: Monitor "Ejection" actionType and technical foul counts

### 4. Overtime Periods
- Games can have multiple overtime periods (5th, 6th+ periods)
- Lineup continuity must be maintained across periods

**Solution**: Handle periods > 4 as overtime extensions

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
1. Database schema creation and migration
2. Core lineup tracking classes and algorithms
3. JSON parsing for starting lineups and substitutions
4. Basic validation framework

### Phase 2: Data Processing Pipeline (Week 2)
1. Batch processing script for existing game data
2. Name resolution and player matching system
3. Timeline construction and state management
4. Error handling and data quality validation

### Phase 3: Query Interface (Week 3)
1. Primary query functions for on-court player lookup
2. Database indexing optimization
3. Caching layer for frequently accessed lineups
4. API endpoints for external access

### Phase 4: Advanced Features (Week 4)
1. Lineup efficiency calculations (plus/minus per lineup)
2. Configuration-based statistics aggregation
3. Historical trend analysis
4. Performance optimization and monitoring

## Success Metrics

1. **Data Coverage**: Successfully process 100% of available game files
2. **Query Performance**: Sub-100ms response for any game moment lookup
3. **Data Accuracy**: 99.9%+ accuracy validated against known starting lineups
4. **API Reliability**: Zero data inconsistencies in production queries

## Integration Points

### With Existing Systems
- **Enhanced Schema**: Integrates with existing games, players, teams tables
- **Scraping Pipeline**: Extends current JSON processing workflow
- **API Framework**: Will be consumed by planned REST API (Plan 13)
- **Analytics Engine**: Enables advanced statistics calculation (future plans)

### External Dependencies
- **Player Name Resolution**: May require external NBA player databases
- **Game State Validation**: Cross-reference with official NBA data when possible

## Risks & Mitigations

### Risk 1: Name Parsing Accuracy
**Impact**: Incorrect player identification leads to wrong lineup data
**Mitigation**: Comprehensive name mapping table + manual validation for edge cases

### Risk 2: Data Volume Performance
**Impact**: Slow queries as data grows to millions of lineup states
**Mitigation**: Proper indexing strategy + data archival for historical games

### Risk 3: JSON Format Changes
**Impact**: NBA.com structure changes could break parsing
**Mitigation**: Robust error handling + version detection in JSON processing

## Testing Strategy

1. **Unit Tests**: Individual functions for lineup initialization, substitution processing
2. **Integration Tests**: Full game processing with known outcomes
3. **Performance Tests**: Query response times under load
4. **Data Quality Tests**: Validation against manually verified games

## Conclusion

This on/off tracking system will provide the foundational data layer for advanced NBA analytics. By accurately tracking which players are on court at any moment, we enable sophisticated analysis of lineup efficiency, player combinations, and situational performance that forms the core value proposition of the NBA play-by-play API.

The implementation leverages the consistent structure found in NBA JSON data across 27+ years while handling the complexity of real-time lineup changes and edge cases that occur in professional basketball games.