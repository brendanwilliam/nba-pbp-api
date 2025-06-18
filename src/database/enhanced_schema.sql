-- Enhanced NBA Database Schema
-- Based on comprehensive JSON analysis of NBA.com game data (1996-2025)
-- Generated from analysis of 58 files across 26 seasons

-- Enable UUID extension for unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Teams table with historical changes support
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY,
    team_code VARCHAR(3) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    team_city VARCHAR(100) NOT NULL,
    team_slug VARCHAR(50) NOT NULL,
    team_tricode VARCHAR(3) NOT NULL,
    conference VARCHAR(10),
    division VARCHAR(20),
    active_from DATE,
    active_to DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_code, active_from)
);

-- Arenas table
CREATE TABLE arenas (
    arena_id INTEGER PRIMARY KEY,
    arena_name VARCHAR(100) NOT NULL,
    arena_city VARCHAR(100) NOT NULL,
    arena_state VARCHAR(10),
    arena_country VARCHAR(3) DEFAULT 'US',
    arena_timezone VARCHAR(50),
    arena_street_address TEXT,
    arena_postal_code VARCHAR(20),
    capacity INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Players table
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    name_i VARCHAR(50), -- Short name format (e.g., "L. James")
    first_name VARCHAR(50),
    family_name VARCHAR(50),
    jersey_number INTEGER,
    position VARCHAR(10),
    height_inches INTEGER,
    weight_lbs INTEGER,
    birth_date DATE,
    debut_season VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Officials table
CREATE TABLE officials (
    official_id INTEGER PRIMARY KEY,
    official_name VARCHAR(100) NOT NULL,
    name_i VARCHAR(50),
    first_name VARCHAR(50),
    family_name VARCHAR(50),
    jersey_num VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- GAME CORE TABLES
-- =============================================================================

-- Games table - core game information
CREATE TABLE games (
    game_id VARCHAR(20) PRIMARY KEY,
    game_code VARCHAR(50) NOT NULL, -- format: YYYYMMDD/TEAMTEAM
    game_status INTEGER NOT NULL, -- 1=scheduled, 2=live, 3=final
    game_status_text VARCHAR(20),
    season VARCHAR(10) NOT NULL, -- format: YYYY-YY
    game_date DATE NOT NULL,
    game_time_utc TIMESTAMP,
    game_time_et TIMESTAMP,
    
    -- Teams
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    
    -- Scores
    home_score INTEGER,
    away_score INTEGER,
    
    -- Game info
    period INTEGER,
    game_clock VARCHAR(20), -- format: PT12M34.56S
    duration VARCHAR(10), -- format: H:MM
    attendance INTEGER,
    sellout BOOLEAN DEFAULT FALSE,
    
    -- Series info (for playoffs)
    series_game_number VARCHAR(10),
    game_label VARCHAR(100),
    game_sub_label VARCHAR(100),
    series_text VARCHAR(100),
    if_necessary BOOLEAN DEFAULT FALSE,
    
    -- Location
    arena_id INTEGER,
    is_neutral BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (arena_id) REFERENCES arenas(arena_id)
);

-- Game periods (quarters/overtimes with scores)
CREATE TABLE game_periods (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    period_number INTEGER NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- 'quarter', 'overtime'
    home_score INTEGER,
    away_score INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    UNIQUE(game_id, period_number)
);

-- Game officials assignments
CREATE TABLE game_officials (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    official_id INTEGER NOT NULL,
    assignment VARCHAR(50), -- crew chief, referee, umpire
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (official_id) REFERENCES officials(official_id)
);

-- =============================================================================
-- TEAM GAME STATISTICS
-- =============================================================================

-- Team game statistics (both team totals and starter/bench splits)
CREATE TABLE team_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    team_id INTEGER NOT NULL,
    is_home_team BOOLEAN NOT NULL,
    stat_type VARCHAR(20) NOT NULL DEFAULT 'team', -- 'team', 'starters', 'bench'
    
    -- Game context
    wins INTEGER,
    losses INTEGER,
    in_bonus BOOLEAN,
    timeouts_remaining INTEGER,
    seed INTEGER, -- playoff seed
    
    -- Basic stats
    minutes INTEGER,
    field_goals_made INTEGER,
    field_goals_attempted INTEGER,
    field_goals_percentage DECIMAL(5,3),
    three_pointers_made INTEGER,
    three_pointers_attempted INTEGER,
    three_pointers_percentage DECIMAL(5,3),
    free_throws_made INTEGER,
    free_throws_attempted INTEGER,
    free_throws_percentage DECIMAL(5,3),
    
    -- Rebounds
    rebounds_offensive INTEGER,
    rebounds_defensive INTEGER,
    rebounds_total INTEGER,
    
    -- Other stats
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    fouls_personal INTEGER,
    points INTEGER,
    plus_minus_points INTEGER,
    
    -- Advanced stats (when available)
    points_fast_break INTEGER,
    points_in_paint INTEGER,
    points_second_chance INTEGER,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(game_id, team_id, stat_type)
);

-- =============================================================================
-- PLAYER GAME STATISTICS
-- =============================================================================

-- Player game statistics
CREATE TABLE player_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    
    -- Player info for this game
    jersey_number VARCHAR(10),
    position VARCHAR(10),
    starter BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE, -- false if inactive/dnp
    dnp_reason VARCHAR(100), -- injury, coaches decision, etc.
    
    -- Basic stats
    minutes_played INTEGER,
    field_goals_made INTEGER,
    field_goals_attempted INTEGER,
    field_goals_percentage DECIMAL(5,3),
    three_pointers_made INTEGER,
    three_pointers_attempted INTEGER,
    three_pointers_percentage DECIMAL(5,3),
    free_throws_made INTEGER,
    free_throws_attempted INTEGER,
    free_throws_percentage DECIMAL(5,3),
    
    -- Rebounds
    rebounds_offensive INTEGER,
    rebounds_defensive INTEGER,
    rebounds_total INTEGER,
    
    -- Other stats
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    fouls_personal INTEGER,
    points INTEGER,
    plus_minus INTEGER,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(game_id, player_id)
);

-- =============================================================================
-- PLAY-BY-PLAY DATA
-- =============================================================================

-- Play-by-play events
CREATE TABLE play_events (
    event_id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    
    -- Timing
    period INTEGER NOT NULL,
    time_remaining VARCHAR(20), -- format: PT12M34.56S
    time_elapsed_seconds INTEGER, -- calculated seconds from game start
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,
    event_action_type VARCHAR(50),
    event_sub_type VARCHAR(50),
    description TEXT,
    
    -- Score context
    home_score INTEGER,
    away_score INTEGER,
    score_margin INTEGER, -- home_score - away_score
    
    -- Player and team
    player_id INTEGER,
    team_id INTEGER,
    
    -- Additional context
    shot_distance DECIMAL(5,2),
    shot_made BOOLEAN,
    shot_type VARCHAR(50),
    shot_zone VARCHAR(50),
    shot_x DECIMAL(8,2),
    shot_y DECIMAL(8,2),
    
    -- Assists
    assist_player_id INTEGER,
    
    -- Event order
    event_order INTEGER,
    
    -- Video/highlights
    video_available BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (assist_player_id) REFERENCES players(player_id)
);

-- =============================================================================
-- BROADCASTING AND MEDIA
-- =============================================================================

-- Broadcasters table
CREATE TABLE broadcasters (
    broadcaster_id INTEGER PRIMARY KEY,
    broadcast_display VARCHAR(20),
    broadcaster_display VARCHAR(100),
    broadcaster_type VARCHAR(20), -- 'tv', 'radio', 'ott'
    broadcaster_scope VARCHAR(20), -- 'national', 'home', 'away'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Game broadcasters assignments
CREATE TABLE game_broadcasters (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    broadcaster_id INTEGER NOT NULL,
    team_id INTEGER, -- null for national broadcasts
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (broadcaster_id) REFERENCES broadcasters(broadcaster_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- =============================================================================
-- HISTORICAL AND PREGAME DATA
-- =============================================================================

-- Team historical meetings
CREATE TABLE team_meetings (
    id SERIAL PRIMARY KEY,
    team1_id INTEGER NOT NULL,
    team2_id INTEGER NOT NULL,
    meeting_date DATE NOT NULL,
    game_id VARCHAR(20),
    team1_score INTEGER,
    team2_score INTEGER,
    winner_team_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (team1_id) REFERENCES teams(team_id),
    FOREIGN KEY (team2_id) REFERENCES teams(team_id),
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (winner_team_id) REFERENCES teams(team_id)
);

-- Pregame team statistics (season averages at time of game)
CREATE TABLE pregame_team_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    team_id INTEGER NOT NULL,
    
    -- Season stats at time of game
    points_per_game DECIMAL(5,2),
    rebounds_per_game DECIMAL(5,2),
    assists_per_game DECIMAL(5,2),
    steals_per_game DECIMAL(5,2),
    blocks_per_game DECIMAL(5,2),
    turnovers_per_game DECIMAL(5,2),
    field_goal_percentage DECIMAL(5,3),
    three_point_percentage DECIMAL(5,3),
    free_throw_percentage DECIMAL(5,3),
    
    -- Advanced stats
    points_fast_break DECIMAL(5,2),
    points_second_chance DECIMAL(5,2),
    
    -- Leaders
    player_pts_leader_id INTEGER,
    player_pts_leader_pts DECIMAL(5,2),
    player_reb_leader_id INTEGER,
    player_reb_leader_reb DECIMAL(5,2),
    player_ast_leader_id INTEGER,
    player_ast_leader_ast DECIMAL(5,2),
    player_blk_leader_id INTEGER,
    player_blk_leader_blk DECIMAL(5,2),
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_pts_leader_id) REFERENCES players(player_id),
    FOREIGN KEY (player_reb_leader_id) REFERENCES players(player_id),
    FOREIGN KEY (player_ast_leader_id) REFERENCES players(player_id),
    FOREIGN KEY (player_blk_leader_id) REFERENCES players(player_id),
    UNIQUE(game_id, team_id)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Primary lookup indexes
CREATE INDEX idx_games_season ON games(season);
CREATE INDEX idx_games_date ON games(game_date);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX idx_games_status ON games(game_status);

-- Player stats indexes
CREATE INDEX idx_player_stats_game ON player_game_stats(game_id);
CREATE INDEX idx_player_stats_player ON player_game_stats(player_id);
CREATE INDEX idx_player_stats_team ON player_game_stats(team_id);

-- Team stats indexes
CREATE INDEX idx_team_stats_game ON team_game_stats(game_id);
CREATE INDEX idx_team_stats_team ON team_game_stats(team_id);

-- Play-by-play indexes
CREATE INDEX idx_play_events_game ON play_events(game_id);
CREATE INDEX idx_play_events_player ON play_events(player_id);
CREATE INDEX idx_play_events_team ON play_events(team_id);
CREATE INDEX idx_play_events_type ON play_events(event_type);
CREATE INDEX idx_play_events_period ON play_events(period);
CREATE INDEX idx_play_events_order ON play_events(game_id, event_order);

-- Time-based queries
CREATE INDEX idx_play_events_time ON play_events(game_id, period, time_elapsed_seconds);

-- Shot chart queries
CREATE INDEX idx_play_events_shots ON play_events(game_id, shot_made) WHERE shot_x IS NOT NULL;

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Game summary view
CREATE VIEW game_summary AS
SELECT 
    g.game_id,
    g.game_code,
    g.game_date,
    g.season,
    ht.team_name as home_team_name,
    ht.team_tricode as home_team_code,
    at.team_name as away_team_name,
    at.team_tricode as away_team_code,
    g.home_score,
    g.away_score,
    g.game_status_text,
    a.arena_name,
    a.arena_city,
    g.attendance
FROM games g
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
LEFT JOIN arenas a ON g.arena_id = a.arena_id;

-- Player game stats with team info
CREATE VIEW player_game_summary AS
SELECT 
    pgs.*,
    p.player_name,
    t.team_name,
    t.team_tricode,
    g.game_date,
    g.season
FROM player_game_stats pgs
JOIN players p ON pgs.player_id = p.player_id
JOIN teams t ON pgs.team_id = t.team_id
JOIN games g ON pgs.game_id = g.game_id;

-- =============================================================================
-- CONSTRAINTS AND TRIGGERS
-- =============================================================================

-- Ensure home/away teams are different
ALTER TABLE games ADD CONSTRAINT chk_different_teams 
    CHECK (home_team_id != away_team_id);

-- Ensure valid game status
ALTER TABLE games ADD CONSTRAINT chk_game_status 
    CHECK (game_status IN (1, 2, 3));

-- Ensure valid period numbers
ALTER TABLE play_events ADD CONSTRAINT chk_period 
    CHECK (period > 0 AND period <= 10); -- up to 6 overtimes

-- Update timestamps trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to relevant tables
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_games_updated_at BEFORE UPDATE ON games
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();