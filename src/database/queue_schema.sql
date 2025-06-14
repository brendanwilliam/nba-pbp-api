-- Enhanced Queue Management Schema for Systematic Scraping

-- Main scraping queue table
CREATE TABLE IF NOT EXISTS scraping_queue (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) UNIQUE NOT NULL,
    season VARCHAR(10) NOT NULL,
    game_date DATE NOT NULL,
    home_team VARCHAR(3) NOT NULL,
    away_team VARCHAR(3) NOT NULL,
    game_url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'invalid')),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    error_code INTEGER,
    response_time_ms INTEGER,
    data_size_bytes INTEGER
);

-- Indexes for efficient querying
CREATE INDEX idx_scraping_queue_status ON scraping_queue(status);
CREATE INDEX idx_scraping_queue_season ON scraping_queue(season);
CREATE INDEX idx_scraping_queue_game_date ON scraping_queue(game_date);
CREATE INDEX idx_scraping_queue_priority ON scraping_queue(priority DESC, game_date DESC);
CREATE INDEX idx_scraping_queue_retry ON scraping_queue(retry_count, status);

-- Scraping session tracking
CREATE TABLE IF NOT EXISTS scraping_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID DEFAULT gen_random_uuid(),
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    total_games INTEGER DEFAULT 0,
    successful_games INTEGER DEFAULT 0,
    failed_games INTEGER DEFAULT 0,
    average_response_time_ms INTEGER,
    total_data_size_mb DECIMAL(10, 2),
    error_summary JSONB,
    is_active BOOLEAN DEFAULT TRUE
);

-- Detailed error logging
CREATE TABLE IF NOT EXISTS scraping_errors (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    session_id UUID,
    error_type VARCHAR(50) NOT NULL,
    error_code INTEGER,
    error_message TEXT,
    stack_trace TEXT,
    occurred_at TIMESTAMP DEFAULT NOW(),
    retry_number INTEGER DEFAULT 0,
    FOREIGN KEY (game_id) REFERENCES scraping_queue(game_id)
);

-- Season progress tracking
CREATE TABLE IF NOT EXISTS season_progress (
    season VARCHAR(10) PRIMARY KEY,
    total_games INTEGER NOT NULL,
    scraped_games INTEGER DEFAULT 0,
    failed_games INTEGER DEFAULT 0,
    invalid_games INTEGER DEFAULT 0,
    progress_percentage DECIMAL(5, 2) DEFAULT 0.00,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_scraping_queue_updated_at BEFORE UPDATE
    ON scraping_queue FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Helper view for current queue status
CREATE VIEW queue_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(retry_count) as avg_retries,
    MAX(updated_at) as last_activity
FROM scraping_queue
GROUP BY status;

-- Helper view for season progress
CREATE VIEW season_progress_view AS
SELECT 
    sp.season,
    sp.total_games,
    sp.scraped_games,
    sp.failed_games,
    sp.progress_percentage,
    COUNT(CASE WHEN sq.status = 'in_progress' THEN 1 END) as in_progress,
    COUNT(CASE WHEN sq.status = 'pending' THEN 1 END) as pending
FROM season_progress sp
LEFT JOIN scraping_queue sq ON sp.season = sq.season
GROUP BY sp.season, sp.total_games, sp.scraped_games, sp.failed_games, sp.progress_percentage
ORDER BY sp.season;