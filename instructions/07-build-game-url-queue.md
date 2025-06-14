# 07 - Build Game URL Queue

## Objective
Generate and populate a comprehensive queue of all NBA game URLs from 1996-97 to 2024-25 seasons, creating the foundation for systematic data scraping.

## Background
Before mass scraping can begin, we need to identify and queue all game URLs. This involves understanding NBA.com URL patterns, collecting schedule data, and building a robust queuing system for ~30,000 games.

## Scope
- **URL Generation**: All games from 1996-97 through 2024-25
- **Queue Population**: Database table with game metadata and URLs
- **Validation**: URL accessibility and format verification
- **Organization**: Chronological ordering with season grouping

## Implementation Plan

### Phase 1: URL Pattern Analysis
1. **Current URL format research**
   - Pattern: `nba.com/game/{away_team}-vs-{home_team}-{game_id}`
   - Game ID format analysis across seasons
   - Team abbreviation mapping (3-letter codes)

2. **Historical format investigation**
   - URL format changes over time
   - Legacy game ID patterns
   - Archive URL accessibility

### Phase 2: Schedule Data Collection
1. **Data sources identification**
   - NBA.com official schedules
   - Basketball-reference.com historical data
   - ESPN historical schedules
   - API endpoints (if available)

2. **Game metadata extraction**
   - Game date and time
   - Home and away teams
   - Game ID or unique identifier
   - Season and playoff information
   - Game status (completed/postponed)

### Phase 3: Team Abbreviation Mapping
1. **Current team abbreviations**
   - All 30 current NBA teams
   - 3-letter codes used in URLs

2. **Historical team mapping**
   - Relocated teams (e.g., Seattle SuperSonics → OKC Thunder)
   - Name changes and abbreviation evolution
   - Expansion teams by season

### Phase 4: URL Generation Algorithm
1. **URL construction logic**
   ```python
   def generate_game_url(away_team, home_team, game_id, date):
       base_url = "https://www.nba.com/game/"
       return f"{base_url}{away_team.lower()}-vs-{home_team.lower()}-{game_id}"
   ```

2. **Game ID pattern recognition**
   - Format variations by season
   - Playoff vs regular season differences
   - Special event games (All-Star, etc.)

### Phase 5: Queue Database Implementation
1. **Enhanced queue table schema**
   ```sql
   CREATE TABLE game_url_queue (
       id SERIAL PRIMARY KEY,
       game_id VARCHAR(20) UNIQUE NOT NULL,
       season VARCHAR(10) NOT NULL,
       game_date DATE NOT NULL,
       home_team VARCHAR(3) NOT NULL,
       away_team VARCHAR(3) NOT NULL,
       game_url TEXT NOT NULL,
       game_type VARCHAR(20) DEFAULT 'regular', -- regular, playoff, allstar
       status VARCHAR(20) DEFAULT 'pending',
       priority INTEGER DEFAULT 100,
       url_validated BOOLEAN DEFAULT FALSE,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. **Indexing strategy**
   - Season-based indexing for batch processing
   - Date indexing for chronological access
   - Status indexing for queue management

### Phase 6: URL Validation Process
1. **Accessibility testing**
   - HTTP HEAD requests to verify URL exists
   - Response code validation (200, 404, etc.)
   - Rate-limited validation to avoid blocking

2. **Content verification**
   - Presence of `#__NEXT_DATA__` script tag
   - Basic JSON structure validation
   - Game data availability confirmation

## Technical Implementation

### Data Collection Scripts
1. **Schedule scraper**
   - Multi-source data collection
   - Data validation and cross-referencing
   - Duplicate detection and merging

2. **URL generator**
   - Batch URL creation by season
   - Validation integration
   - Error handling and logging

3. **Queue populator**
   - Database insertion with conflict handling
   - Progress tracking and reporting
   - Rollback capabilities for failed batches

### Quality Assurance
1. **Data completeness checks**
   - Games per season validation
   - Missing game detection
   - Playoff bracket completeness

2. **URL format verification**
   - Pattern consistency across seasons
   - Team abbreviation accuracy
   - Game ID uniqueness

## Expected Outcomes

### Queue Statistics
- **Total games**: ~30,000 URLs
- **Seasons covered**: 1996-97 through 2024-25
- **Regular season**: ~25,000 games
- **Playoff games**: ~5,000 games
- **Validation rate**: 95%+ accessible URLs

### Data Quality Metrics
- URL format consistency: 99%+
- Game metadata accuracy: 99%+
- Duplicate elimination: 100%
- Chronological ordering: 100%

## Risk Management

### Data Collection Risks
- Schedule data availability for older seasons
- URL format changes requiring pattern updates
- Team abbreviation inconsistencies

### Technical Risks
- Large-scale URL validation rate limiting
- Database performance with 30k+ records
- Memory usage during batch processing

## Success Criteria
- Complete queue of all NBA games 1996-2025
- 95%+ URL validation success rate
- Organized by season with proper metadata
- Ready for systematic scraping execution
- Comprehensive error logging and recovery

## Timeline
- **Week 1**: Schedule data collection and analysis
- **Week 2**: URL generation and validation
- **Week 3**: Queue population and verification
- **Week 4**: Quality assurance and optimization

## Dependencies
- Completion of systematic scraping plan (Plan 06)
- Database infrastructure readiness
- Network access for URL validation
- Historical schedule data availability

## Next Steps
After completion:
1. Begin mass game scraping (Plan 08)
2. Monitor queue processing efficiency
3. Implement queue management tools