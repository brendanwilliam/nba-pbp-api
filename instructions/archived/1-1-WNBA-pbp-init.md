# WNBA Play-by-Play Database Initialization Plan
## Plan: 1-1-WNBA-pbp-init

### Overview
Transform the current NBA play-by-play API project into a WNBA-focused scraping and database system by removing API/MCP components and non-essential analytics, keeping only core scraping infrastructure and essential tracking systems.

### Components to Keep ✅
- **Core Infrastructure**: `src/core/` (database, models, config, query_builder)
- **Scraping System**: `src/scrapers/` (all scraping logic and utilities)
- **Database Management**: `src/database/` (schema, parsers, sync tools, queue management)
- **Essential Analytics**: `src/analytics/` (possession tracking, lineup tracking ONLY)
- **Data Quality**: `src/data_quality/` (validation framework)
- **Scripts**: `src/scripts/` (build tools, population scripts, testing)

### Components to Remove ❌
- **API System**: Entire `src/api/` directory and all REST API functionality
- **MCP System**: Entire `src/mcp/` directory and all MCP server functionality
- **Advanced Analytics**: Remove all analytics beyond possession and lineup tracking

### Step-by-Step Implementation Plan

#### Step 1: Environment Setup and Code Cleanup ✅ COMPLETED
1.1. **Remove API and MCP directories** ✅
   - ✅ Delete `src/api/` directory entirely
   - ✅ Delete `src/mcp/` directory entirely
   - ✅ Clean up any imports/references to these modules

1.2. **Clean up analytics directory** ✅
   - ✅ Keep only `possession_tracker.py` and `lineup_tracker.py` in `src/analytics/`
   - ✅ Remove any other analytics files and advanced statistical analysis tools
   - ✅ Update README to reflect simplified analytics scope

1.3. **Update project configuration** ✅ COMPLETED
   - ✅ Modify `src/core/config.py` to remove API and MCP configurations
   - ✅ Remove analytics-related configurations beyond possession/lineup tracking
   - ✅ Update database configuration to use 'wnba_pbp' database
   - ✅ Update application names and references from NBA to WNBA

1.4. **Clean up root-level files** ✅
   - ✅ Remove API/MCP related scripts and configurations
   - ✅ Update requirements.txt to remove API/MCP dependencies
   - ✅ Remove dependencies for advanced analytics not needed

#### Step 2: Database Infrastructure Setup ✅ COMPLETED
2.1. **Create WNBA database** ✅
   - ✅ Create new PostgreSQL database named 'wnba_pbp'
   - ✅ Set up with username 'brendan' and password 'postgres'
   - ✅ Apply the same enhanced schema as NBA database

2.2. **Adapt database configuration** ✅
   - ✅ Update database connection settings for WNBA database
   - ✅ Modify all database management tools to work with WNBA schema
   - ✅ Update sync tools for WNBA-specific operations
   - ✅ Remove database views/tables related to advanced analytics if any

#### Step 3: WNBA-Specific Adaptations ✅ COMPLETED
3.1. **Update team mapping system** ✅
   - ✅ Modify `src/scrapers/team_mapping.py` for WNBA teams
   - ✅ Research and implement WNBA team abbreviations and historical changes
   - ✅ Update team data structures in `src/core/models.py`

3.2. **Adapt URL generation system** ✅
   - ✅ Modify `src/scrapers/game_url_generator.py` for WNBA URLs
   - ✅ Update game ID patterns and URL structures for WNBA.com
   - ✅ Adapt date ranges for WNBA seasons (typically May-October)

3.3. **Update scraping configuration** ✅
   - ✅ Modify user agents and rate limiting for WNBA.com
   - ✅ Update scraping targets and validation rules
   - ✅ Adapt queue management for WNBA game structures

#### Step 4: Data Models and Schema Updates ✅ COMPLETED
4.1. **Update core models** ✅
   - ✅ Modify `src/core/models.py` for WNBA-specific data types
   - ✅ Update team models for WNBA team structure
   - ✅ Adapt player models for WNBA roster formats
   - ✅ Remove model fields related to advanced analytics beyond possession/lineup

4.2. **Schema adaptations** ✅
   - ✅ Update database schema comments and references
   - ✅ Modify validation rules for WNBA data structures
   - ✅ Keep only essential analytics models (possession, lineup tracking)
   - ✅ Remove advanced statistical tables/views

#### Step 5: Scraping System Configuration ✅ COMPLETED
5.1. **Update scraping scripts** ✅
   - ✅ Modify `src/scripts/build_game_url_queue.py` for WNBA seasons
   - ✅ Update mass scraping tools for WNBA data volumes
   - ✅ Adapt testing scripts for WNBA game samples
   - ✅ Remove scripts related to advanced analytics processing

5.2. **Update validation and quality systems** ✅
   - ✅ Modify `src/data_quality/validation_framework.py` for WNBA data
   - ✅ Focus validation on core data quality, possession, and lineup tracking
   - ✅ Remove validation for advanced analytics features

#### Step 6: Testing and Validation ✅ COMPLETED
6.1. **Test database setup** ✅
   - ✅ Verify WNBA database creation and schema application
   - ✅ Test connection and basic operations
   - ✅ Validate database management tools

6.2. **Test scraping system** ✅
   - ✅ Test WNBA URL generation and validation
   - ✅ Perform sample scraping of recent WNBA games
   - ✅ Validate data parsing and database population

6.3. **Integration testing** ✅
   - ✅ Test complete scraping workflow
   - ✅ Validate essential analytics (possession and lineup tracking only)
   - ✅ Test database management and sync tools

#### Step 7: Documentation Updates ✅ COMPLETED
7.1. **Update project documentation** ✅
   - ✅ Modify CLAUDE.md for WNBA-specific instructions
   - ✅ Update README files to reflect simplified scope
   - ✅ Update configuration documentation
   - ✅ Remove references to removed analytics features

7.2. **Create WNBA-specific guides** ✅
   - ✅ Document WNBA season structures and data patterns
   - ✅ Create setup guide for WNBA database
   - ✅ Document team mapping and URL patterns
   - ✅ Focus on core scraping and essential analytics only

### Expected Outcomes
- Streamlined codebase focused solely on WNBA data scraping and database management
- Essential analytics limited to possession and lineup tracking only
- New 'wnba_pbp' PostgreSQL database with simplified schema
- Fully functional WNBA scraping system ready for data collection
- Minimal but effective analytics infrastructure
- Updated documentation for simplified WNBA operations

### File Structure After Completion
```
src/
├── analytics/          # WNBA essential analytics (possession, lineup tracking ONLY)
├── core/              # Core infrastructure (database, models, config)
├── data_quality/      # WNBA data validation
├── database/          # Schema and management tools for WNBA
├── scrapers/          # WNBA web scraping system
└── scripts/           # WNBA-specific execution scripts (simplified)
```

### Implementation Notes
- WNBA website structure is identical to NBA (same JSON structure in `#__NEXT_DATA__`)
- Only URLs and game_id codes differ between NBA and WNBA
- Database schema remains the same, just adapted for WNBA team/player data
- Focus on lean, efficient system for WNBA data collection and basic analytics

This plan creates a lean, focused WNBA scraping system with only the essential components for data collection and basic tracking.