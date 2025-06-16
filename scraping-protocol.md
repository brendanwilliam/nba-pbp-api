# NBA Mass Production Scraping Protocol

## Overview

This document outlines the protocol for executing the mass production scrape of approximately 30,000 NBA games from the 1996-97 season through 2024-25. The scraping process follows Plan 08 implementation and has been fully tested.

## Database Tables Population Order

### Phase 1: Queue Preparation (COMPLETED)
Tables populated in setup phase:

1. **`scraping_queue`** - Primary work queue
   - **Status**: ✅ POPULATED (4 test games transferred)
   - **Contents**: Game metadata, URLs, status tracking
   - **Purpose**: Atomic work distribution and progress tracking

2. **`season_progress`** - Season-level tracking  
   - **Status**: ✅ AUTO-POPULATED (via triggers)
   - **Contents**: Season completion percentages and statistics
   - **Purpose**: High-level progress monitoring

### Phase 2: Mass Scraping Execution (IN PROGRESS)
Tables populated during scraping operations:

3. **`scraping_sessions`** - Session management
   - **Population Order**: First (session start)
   - **Contents**: Session metadata, performance metrics
   - **Populated When**: At start of each scraping session
   - **Purpose**: Track individual scraping runs and their performance

4. **`raw_game_data`** - Primary data storage
   - **Population Order**: Second (per successful scrape)
   - **Contents**: Complete JSON data from NBA.com `__NEXT_DATA__`
   - **Populated When**: Each successful game scrape
   - **Purpose**: Store raw scraped data for later processing
   - **Expected Size**: ~350KB per game × 30,000 games = ~10.5GB

5. **`scraping_errors`** - Error tracking
   - **Population Order**: Third (per failure)
   - **Contents**: Detailed error logs, retry attempts, patterns
   - **Populated When**: Each failed scrape attempt
   - **Purpose**: Debug issues and optimize retry logic

### Phase 3: Status Updates (CONTINUOUS)
Tables updated throughout the process:

6. **`scraping_queue`** (updates)
   - **Updates**: Status changes (pending → in_progress → completed/failed)
   - **Frequency**: Continuous during scraping
   - **Fields Updated**: `status`, `response_time_ms`, `data_size_bytes`, `completed_at`

## Scraping Execution Protocol

### Pre-Scraping Checklist

1. **Database Preparation**
   ```sql
   -- Verify queue population
   SELECT COUNT(*) FROM scraping_queue WHERE status = 'pending';
   
   -- Reset any stale in-progress games
   UPDATE scraping_queue SET status = 'pending', started_at = NULL 
   WHERE status = 'in_progress' AND started_at < NOW() - INTERVAL '30 minutes';
   ```

2. **System Resources**
   - Database storage: Ensure 15GB+ available for raw JSON data
   - Network connectivity: Stable connection to NBA.com
   - Rate limiting: Configured for 0.5 requests/second (conservative)

3. **Queue Statistics Baseline**
   ```sql
   SELECT status, COUNT(*) FROM scraping_queue GROUP BY status;
   ```

### Scraping Command

```bash
source venv/bin/activate

# Production scraping command
python src/scripts/mass_game_scraper.py \
  --batch-size 100 \
  --max-workers 4 \
  --rate-limit 0.5 \
  --db-url postgresql://brendan@localhost:5432/nba_pbp
```

### Monitoring Command (Run in separate terminal)

```bash
source venv/bin/activate

# Real-time monitoring
python src/scripts/scraping_monitor.py --refresh 30
```

## Data Population Sequence

### 1. Session Initialization
- **Table**: `scraping_sessions`
- **Action**: INSERT new session record
- **Data**: Session UUID, start time, configuration

### 2. Batch Processing Loop
For each batch of games:

#### 2a. Queue Lock and Retrieve
- **Table**: `scraping_queue`  
- **Action**: SELECT FOR UPDATE to lock games
- **Status Change**: `pending` → `in_progress`

#### 2b. Concurrent Scraping
- **Rate Limiting**: Applied per request
- **Data Extraction**: JSON from `__NEXT_DATA__` script tags
- **Quality Assessment**: Completeness scoring

#### 2c. Result Processing
Per game completion:

**SUCCESS PATH:**
1. **Table**: `raw_game_data`
   - **Action**: INSERT JSON data
   - **Data**: game_id, game_url, raw_json, json_size
2. **Table**: `scraping_queue`
   - **Action**: UPDATE status to 'completed'
   - **Data**: response_time_ms, data_size_bytes, completed_at

**FAILURE PATH:**
1. **Table**: `scraping_errors`
   - **Action**: INSERT error details
   - **Data**: game_id, error_type, error_message, retry_number
2. **Table**: `scraping_queue`
   - **Action**: UPDATE for retry or permanent failure
   - **Logic**: Retry if attempts < max_retries, else mark 'failed'

### 3. Progress Tracking
- **Table**: `season_progress` (auto-updated via triggers)
- **Frequency**: After each game completion
- **Metrics**: completion_percentage, scraped_games, failed_games

### 4. Session Finalization
- **Table**: `scraping_sessions`
- **Action**: UPDATE with final statistics
- **Data**: ended_at, successful_games, failed_games, total_data_mb

## Expected Data Volumes

### Successful Completion (98% target)
- **Games Scraped**: ~29,400 games
- **Raw JSON Data**: ~10.3GB in `raw_game_data`
- **Queue Records**: 30,000 rows in `scraping_queue`
- **Session Records**: 1-10 rows in `scraping_sessions`
- **Error Records**: ~1,000-2,000 rows in `scraping_errors`

### Performance Estimates
- **Rate**: 500-1000 games per day (conservative estimate)
- **Duration**: 30-60 days for complete scrape
- **Peak Storage**: ~12GB total database size
- **Network**: ~300MB per day data transfer

## Success Criteria

### Quantitative Targets
- ✅ **Completion Rate**: 98%+ of queued games successfully scraped
- ✅ **Data Quality**: 95%+ games with complete JSON structures  
- ✅ **Error Rate**: <2% permanent failures
- ✅ **Performance**: 500+ games per day sustained rate

### Quality Indicators
- ✅ **JSON Validity**: All stored JSON is parseable
- ✅ **Data Completeness**: Game metadata present in 99%+ of records
- ✅ **Storage Integrity**: No database corruption or constraint violations
- ✅ **Progress Tracking**: Accurate session and season statistics

## Risk Mitigation

### Technical Risks
1. **NBA.com Rate Limiting**
   - Mitigation: Conservative 0.5 req/sec, exponential backoff
   - Monitoring: Track 429 responses, adjust rate dynamically

2. **Database Storage**
   - Mitigation: Monitor disk space, implement compression
   - Backup: Regular database backups during process

3. **Network Interruptions**  
   - Mitigation: Resume capability, stale game reset
   - Recovery: Session-based checkpointing

### Operational Risks
1. **Long Processing Time**
   - Mitigation: Parallel processing, progress monitoring
   - Optimization: Batch size tuning, worker thread adjustment

2. **Data Quality Issues**
   - Mitigation: Real-time quality scoring, validation
   - Recovery: Failed game requeue and manual review

## Monitoring and Alerting

### Key Metrics to Monitor
1. **Scraping Rate**: Games completed per hour
2. **Success Rate**: Percentage of successful scrapes
3. **Error Patterns**: Common failure types and frequencies
4. **Resource Usage**: Database size, memory, CPU
5. **Queue Status**: Pending vs completed game counts

### Dashboard Refresh
- **Frequency**: Every 30 seconds
- **Command**: `python src/scripts/scraping_monitor.py --refresh 30`

### Progress Reports
- **Daily**: Export detailed progress report
- **Command**: `python src/scripts/scraping_monitor.py --export daily_report_YYYYMMDD.json`

## Post-Completion Protocol

### Data Validation
1. **Count Verification**: Compare scraped vs expected game counts
2. **Quality Assessment**: Analyze data completeness scores
3. **Error Analysis**: Review failure patterns and causes

### Cleanup Tasks
1. **Reset Test Data**: Remove test session records
2. **Optimize Database**: VACUUM and ANALYZE tables
3. **Archive Logs**: Compress and store scraping logs

### Preparation for Next Phase
1. **JSON Analysis**: Ready for Plan 09 (JSON structure analysis)
2. **Schema Design**: Prepare for Plan 10 (database schema design)
3. **Documentation**: Update progress in CLAUDE.md

## Ready State Confirmation

✅ **Database Schema**: All required tables created and indexed  
✅ **Queue Population**: Games loaded and ready for processing  
✅ **System Testing**: All components tested and validated  
✅ **Monitoring Setup**: Dashboard and reporting tools operational  
✅ **Error Handling**: Retry logic and failure recovery tested  
✅ **Rate Limiting**: Conservative settings configured and tested  

**Status**: READY FOR MASS PRODUCTION SCRAPING

---

*This protocol ensures systematic, monitored, and recoverable mass scraping of NBA game data with comprehensive quality assurance and progress tracking.*