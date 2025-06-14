# 10 - Implement Database Schema

## Objective
Implement the optimized database schema designed from JSON analysis, including table creation, indexes, constraints, and performance optimizations for the NBA play-by-play data.

## Background
Based on comprehensive JSON analysis, implement a production-ready PostgreSQL schema that efficiently stores and enables querying of NBA game data, play-by-play events, and statistics.

## Scope
- **Schema Implementation**: Create all tables, relationships, and constraints
- **Performance Optimization**: Indexes, partitioning, and query optimization
- **Data Integrity**: Foreign keys, check constraints, and validation rules
- **Migration Framework**: Alembic migration scripts for version control

## Implementation Plan

### Phase 1: Core Schema Implementation
1. **Table creation order**
   - Reference tables first (teams, players)
   - Core data tables (games, play_events)
   - Statistics tables (player_game_stats, team_game_stats)
   - Advanced analytics tables (shot_events)

2. **Alembic migration structure**
   ```
   migrations/
   ├── 001_create_teams_table.py
   ├── 002_create_players_table.py
   ├── 003_create_games_table.py
   ├── 004_create_play_events_table.py
   ├── 005_create_player_game_stats_table.py
   ├── 006_create_team_game_stats_table.py
   ├── 007_create_shot_events_table.py
   ├── 008_add_indexes.py
   ├── 009_add_constraints.py
   └── 010_add_triggers.py
   ```

### Phase 2: Performance Optimization
1. **Indexing strategy**
   ```sql
   -- Primary lookup indexes
   CREATE INDEX idx_games_date ON games(game_date);
   CREATE INDEX idx_games_season ON games(season);
   CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
   
   -- Play-by-play indexes
   CREATE INDEX idx_play_events_game ON play_events(game_id);
   CREATE INDEX idx_play_events_player ON play_events(player_id);
   CREATE INDEX idx_play_events_time ON play_events(game_id, period, event_order);
   
   -- Statistics indexes
   CREATE INDEX idx_player_stats_game_player ON player_game_stats(game_id, player_id);
   CREATE INDEX idx_player_stats_season ON player_game_stats(game_id) 
       WHERE game_id LIKE '0042%' OR game_id LIKE '0022%';
   
   -- Shot chart indexes
   CREATE INDEX idx_shot_events_player ON shot_events(player_id, game_id);
   CREATE INDEX idx_shot_events_location ON shot_events(shot_x, shot_y);
   ```

2. **Partitioning strategy**
   ```sql
   -- Partition play_events by season for better performance
   CREATE TABLE play_events_partitioned (
       LIKE play_events INCLUDING ALL
   ) PARTITION BY RANGE (game_id);
   
   -- Create partitions for each season
   CREATE TABLE play_events_2024 PARTITION OF play_events_partitioned
       FOR VALUES FROM ('0022400001') TO ('0022499999');
   ```

### Phase 3: Data Integrity and Constraints
1. **Foreign key constraints**
   ```sql
   ALTER TABLE games 
   ADD CONSTRAINT fk_games_home_team 
   FOREIGN KEY (home_team_id) REFERENCES teams(team_id);
   
   ALTER TABLE play_events 
   ADD CONSTRAINT fk_play_events_game 
   FOREIGN KEY (game_id) REFERENCES games(game_id);
   ```

2. **Check constraints**
   ```sql
   ALTER TABLE games 
   ADD CONSTRAINT chk_scores_non_negative 
   CHECK (home_score >= 0 AND away_score >= 0);
   
   ALTER TABLE play_events 
   ADD CONSTRAINT chk_period_valid 
   CHECK (period BETWEEN 1 AND 10);
   ```

3. **Data validation triggers**
   ```sql
   CREATE OR REPLACE FUNCTION validate_play_event()
   RETURNS TRIGGER AS $$
   BEGIN
       -- Validate time_elapsed is consistent with period and time_remaining
       -- Validate scores are monotonically increasing
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;
   ```

### Phase 4: Advanced Features
1. **Materialized views for common queries**
   ```sql
   CREATE MATERIALIZED VIEW season_player_stats AS
   SELECT 
       p.player_id,
       p.player_name,
       g.season,
       COUNT(*) as games_played,
       AVG(pgs.points) as avg_points,
       AVG(pgs.rebounds) as avg_rebounds,
       AVG(pgs.assists) as avg_assists
   FROM player_game_stats pgs
   JOIN games g ON pgs.game_id = g.game_id
   JOIN players p ON pgs.player_id = p.player_id
   GROUP BY p.player_id, p.player_name, g.season;
   ```

2. **Custom data types**
   ```sql
   CREATE TYPE shot_result AS ENUM ('made', 'missed', 'blocked');
   CREATE TYPE game_period AS (period_number INTEGER, period_type VARCHAR(20));
   ```

## Technical Implementation

### Migration Scripts Structure
```python
# Example migration: 003_create_games_table.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('games',
        sa.Column('game_id', sa.String(20), primary_key=True),
        sa.Column('season', sa.String(10), nullable=False),
        sa.Column('game_date', sa.Date, nullable=False),
        sa.Column('home_team_id', sa.Integer, nullable=False),
        sa.Column('away_team_id', sa.Integer, nullable=False),
        sa.Column('home_score', sa.Integer),
        sa.Column('away_score', sa.Integer),
        sa.Column('period', sa.Integer),
        sa.Column('game_status', sa.String(20)),
        sa.Column('attendance', sa.Integer),
        sa.Column('arena', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('games')
```

### Performance Testing Framework
1. **Query performance benchmarks**
   ```python
   def benchmark_common_queries():
       # Test game lookup by date range
       # Test player statistics aggregation
       # Test play-by-play event queries
       # Test shot chart data retrieval
   ```

2. **Load testing**
   - Simulate API query patterns
   - Test concurrent access scenarios
   - Measure query response times
   - Identify bottlenecks

### Schema Validation Tools
1. **Data consistency checks**
   ```sql
   -- Verify play-by-play event ordering
   SELECT game_id, COUNT(*) 
   FROM play_events 
   WHERE event_order IS NULL OR event_order < 1
   GROUP BY game_id;
   
   -- Check for orphaned records
   SELECT COUNT(*) FROM play_events pe
   LEFT JOIN games g ON pe.game_id = g.game_id
   WHERE g.game_id IS NULL;
   ```

2. **Performance monitoring**
   ```sql
   -- Monitor slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   WHERE mean_time > 1000 
   ORDER BY mean_time DESC;
   ```

## Quality Assurance

### Testing Strategy
1. **Unit tests for migrations**
   - Verify table creation
   - Test constraint enforcement
   - Validate index creation

2. **Integration tests**
   - End-to-end data flow testing
   - Query performance validation
   - Data integrity verification

3. **Load testing**
   - Concurrent query simulation
   - Large dataset performance
   - Memory usage analysis

### Rollback Procedures
1. **Migration rollback testing**
   - Verify all migrations are reversible
   - Test data preservation during rollbacks
   - Validate constraint removal

2. **Backup strategies**
   - Pre-migration database snapshots
   - Point-in-time recovery setup
   - Data export procedures

## Expected Outcomes

### Schema Metrics
- **Tables**: 8 core tables + materialized views
- **Indexes**: 20+ optimized indexes
- **Constraints**: Complete referential integrity
- **Performance**: Sub-second response for common queries

### Capacity Planning
- **Storage**: ~50GB for complete dataset
- **Memory**: 8GB+ recommended for optimal performance
- **Connections**: Support for 100+ concurrent connections
- **Growth**: 10% annual growth accommodation

## Success Criteria
- All tables created with proper relationships
- Indexes provide optimal query performance
- Data integrity constraints prevent invalid data
- Schema supports all identified use cases
- Performance meets API response time requirements

## Timeline
- **Week 1**: Core table implementation and basic indexes
- **Week 2**: Advanced features and optimization
- **Week 3**: Testing and performance tuning
- **Week 4**: Documentation and validation

## Dependencies
- Completed JSON analysis and schema design (Plan 09)
- PostgreSQL database instance
- Alembic migration framework
- Performance testing tools

## Next Steps
After completion:
1. JSON to database migration implementation (Plan 11)
2. Performance baseline establishment
3. API development preparation
4. Production deployment planning