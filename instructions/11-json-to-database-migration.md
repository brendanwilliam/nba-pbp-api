# 11 - JSON to Database Migration

## Objective
Develop and execute a comprehensive ETL (Extract, Transform, Load) process to migrate all scraped NBA JSON data from raw storage into the structured relational database schema.

## Background
With raw JSON data collected and the database schema implemented, this phase focuses on transforming and loading approximately 30,000 games worth of data into the relational structure while maintaining data quality and performance.

## Scope
- **Data Transformation**: Convert JSON to relational format
- **ETL Pipeline**: Batch processing with error handling
- **Data Validation**: Quality assurance during migration
- **Performance Optimization**: Efficient bulk loading strategies

## Implementation Plan

### Phase 1: ETL Architecture Design
1. **Processing pipeline structure**
   ```
   Raw JSON → Data Extraction → Transformation → Validation → Database Load
   ```

2. **Component architecture**
   ```python
   class ETLPipeline:
       def __init__(self):
           self.extractor = JSONDataExtractor()
           self.transformer = DataTransformer()
           self.validator = DataValidator()
           self.loader = DatabaseLoader()
       
       def process_batch(self, game_ids):
           # Process games in batches for memory efficiency
   ```

### Phase 2: Data Extraction Components
1. **JSON data extractor**
   ```python
   class JSONDataExtractor:
       def extract_game_metadata(self, json_data):
           # Extract basic game information
           return {
               'game_id': json_data['props']['pageProps']['game']['gameId'],
               'season': self._extract_season(json_data),
               'game_date': json_data['props']['pageProps']['game']['gameTimeLocal'],
               'home_team': json_data['props']['pageProps']['game']['homeTeam'],
               'away_team': json_data['props']['pageProps']['game']['awayTeam']
           }
       
       def extract_play_by_play(self, json_data):
           # Extract all play-by-play events
           actions = json_data['props']['pageProps']['game']['actions']
           return [self._transform_action(action) for action in actions]
       
       def extract_box_score(self, json_data):
           # Extract player and team statistics
           return {
               'players': self._extract_player_stats(json_data),
               'teams': self._extract_team_stats(json_data)
           }
   ```

2. **Data structure mapping**
   ```python
   JSON_TO_DB_MAPPING = {
       'game': {
           'gameId': 'game_id',
           'gameTimeLocal': 'game_date',
           'homeTeam.teamId': 'home_team_id',
           'awayTeam.teamId': 'away_team_id',
           'homeTeam.score': 'home_score',
           'awayTeam.score': 'away_score'
       },
       'play_event': {
           'actionNumber': 'event_order',
           'period': 'period',
           'timeRemaining': 'time_remaining',
           'description': 'description',
           'actionType': 'event_type',
           'personId': 'player_id',
           'teamId': 'team_id'
       }
   }
   ```

### Phase 3: Data Transformation Engine
1. **Data type conversions**
   ```python
   class DataTransformer:
       def transform_time_format(self, time_string):
           # Convert "PT12M34.50S" to seconds
           
       def transform_coordinates(self, x, y):
           # Convert shot coordinates to standard format
           
       def normalize_player_names(self, name):
           # Standardize player name formats
           
       def calculate_time_elapsed(self, period, time_remaining):
           # Calculate seconds from game start
   ```

2. **Data enrichment**
   ```python
   def enrich_play_events(self, events, game_metadata):
       for event in events:
           event['game_id'] = game_metadata['game_id']
           event['time_elapsed'] = self._calculate_time_elapsed(
               event['period'], event['time_remaining']
           )
           event['home_score'], event['away_score'] = self._calculate_running_score(events, event)
   ```

### Phase 4: Data Validation Framework
1. **Quality checks**
   ```python
   class DataValidator:
       def validate_game_data(self, game_data):
           checks = [
               self._check_required_fields(game_data),
               self._check_score_consistency(game_data),
               self._check_time_consistency(game_data),
               self._check_player_references(game_data)
           ]
           return all(checks)
       
       def _check_score_consistency(self, game_data):
           # Verify final scores match play-by-play
           
       def _check_time_consistency(self, events):
           # Verify event timing makes sense
   ```

2. **Data completeness scoring**
   ```python
   def calculate_completeness_score(self, game_data):
       total_fields = len(REQUIRED_FIELDS)
       populated_fields = sum(1 for field in REQUIRED_FIELDS 
                            if self._is_populated(game_data.get(field)))
       return populated_fields / total_fields
   ```

### Phase 5: Database Loading Strategy
1. **Bulk loading optimization**
   ```python
   class DatabaseLoader:
       def load_games_batch(self, games_data):
           # Use COPY for bulk inserts
           with self.connection.cursor() as cursor:
               cursor.copy_from(games_buffer, 'games', columns=GAME_COLUMNS)
       
       def load_play_events_batch(self, events_data):
           # Batch insert play-by-play events
           execute_values(cursor, INSERT_EVENTS_SQL, events_data, page_size=1000)
   ```

2. **Transaction management**
   ```python
   def process_game_transaction(self, game_data):
       with self.connection.begin():
           try:
               self._load_game(game_data['game'])
               self._load_players(game_data['players'])
               self._load_play_events(game_data['events'])
               self._load_statistics(game_data['stats'])
           except Exception as e:
               # Transaction will auto-rollback
               self._log_error(game_data['game_id'], e)
               raise
   ```

## Processing Strategy

### Batch Processing Design
1. **Batch size optimization**
   - Process 100-500 games per batch
   - Memory usage monitoring
   - Progress checkpointing

2. **Parallel processing**
   ```python
   def process_season_parallel(self, season, num_workers=4):
       games = self._get_season_games(season)
       batches = self._create_batches(games, batch_size=100)
       
       with ProcessPoolExecutor(max_workers=num_workers) as executor:
           futures = [executor.submit(self._process_batch, batch) 
                     for batch in batches]
           return [future.result() for future in futures]
   ```

### Error Handling and Recovery
1. **Error categorization**
   - Data quality issues (incomplete JSON)
   - Transformation errors (invalid data types)
   - Database constraint violations
   - System errors (memory, disk space)

2. **Recovery strategies**
   ```python
   class ErrorHandler:
       def handle_transformation_error(self, game_id, error):
           self._log_detailed_error(game_id, error)
           self._queue_for_manual_review(game_id)
           
       def handle_constraint_violation(self, game_id, error):
           self._attempt_data_cleanup(game_id)
           self._retry_with_relaxed_constraints(game_id)
   ```

## Quality Assurance

### Data Validation Pipeline
1. **Pre-load validation**
   - JSON structure verification
   - Required field presence
   - Data type consistency
   - Value range validation

2. **Post-load validation**
   ```sql
   -- Verify data integrity
   SELECT COUNT(*) FROM games WHERE home_score IS NULL AND game_status = 'Final';
   
   -- Check play-by-play completeness
   SELECT game_id, COUNT(*) as event_count 
   FROM play_events 
   GROUP BY game_id 
   HAVING COUNT(*) < 50; -- Flag games with suspiciously few events
   
   -- Validate statistical consistency
   SELECT g.game_id, g.home_score, SUM(CASE WHEN pgs.team_id = g.home_team_id THEN pgs.points ELSE 0 END) as calculated_score
   FROM games g
   JOIN player_game_stats pgs ON g.game_id = pgs.game_id
   GROUP BY g.game_id, g.home_score, g.home_team_id
   HAVING g.home_score != SUM(CASE WHEN pgs.team_id = g.home_team_id THEN pgs.points ELSE 0 END);
   ```

### Performance Monitoring
1. **Processing metrics**
   - Games processed per hour
   - Error rates by category
   - Memory usage patterns
   - Database load times

2. **Quality metrics**
   - Data completeness scores
   - Validation pass rates
   - Statistical consistency checks

## Expected Outcomes

### Migration Statistics
- **Games processed**: 30,000+ NBA games
- **Play-by-play events**: ~10 million events
- **Player statistics**: ~1 million player-game records
- **Processing time**: 2-5 days for complete migration
- **Success rate**: 98%+ successful migrations

### Data Quality Results
- **Completeness**: 95%+ for core fields
- **Accuracy**: 99%+ statistical consistency
- **Integrity**: 100% referential integrity
- **Coverage**: All seasons 1996-2025

## Success Criteria
- All games successfully migrated with <2% failure rate
- Complete play-by-play data for 98%+ of games
- Statistical consistency validation passes
- Performance meets processing time targets
- Comprehensive error logging and recovery

## Timeline
- **Week 1**: ETL pipeline development and testing
- **Week 2**: Batch processing implementation
- **Week 3**: Historical data migration (1996-2015)
- **Week 4**: Modern data migration (2015-2025) and validation

## Dependencies
- Completed database schema implementation (Plan 10)
- Raw JSON data availability
- Sufficient processing capacity
- Database performance optimization

## Next Steps
After completion:
1. Data quality assessment and optimization
2. Database performance tuning
3. API development preparation (Plan 13)
4. Cloud migration planning (Plan 12)