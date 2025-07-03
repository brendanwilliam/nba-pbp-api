-- Possession Analysis Views
-- Views to simplify common possession-based queries

-- =============================================================================
-- POSSESSION SUMMARY VIEWS
-- =============================================================================

-- Possession summary with team information
CREATE OR REPLACE VIEW possession_summary AS
SELECT 
    pe.possession_id,
    pe.game_id,
    pe.possession_number,
    pe.team_id,
    t.team_name,
    t.team_tricode,
    pe.start_period,
    pe.start_time_remaining,
    pe.start_seconds_elapsed,
    pe.end_period,
    pe.end_time_remaining,
    pe.end_seconds_elapsed,
    pe.possession_outcome,
    pe.points_scored,
    -- Calculate possession duration in seconds
    COALESCE(pe.end_seconds_elapsed, 0) - pe.start_seconds_elapsed as duration_seconds,
    pe.created_at
FROM possession_events pe
LEFT JOIN teams t ON pe.team_id = t.team_id;

-- Game possession statistics
CREATE OR REPLACE VIEW game_possession_stats AS
SELECT 
    pe.game_id,
    g.game_date,
    g.season,
    
    -- Home team stats
    ht.team_name as home_team_name,
    ht.team_tricode as home_team_code,
    COUNT(CASE WHEN pe.team_id = g.home_team_id THEN 1 END) as home_possessions,
    SUM(CASE WHEN pe.team_id = g.home_team_id THEN pe.points_scored ELSE 0 END) as home_points,
    ROUND(
        CASE 
            WHEN COUNT(CASE WHEN pe.team_id = g.home_team_id THEN 1 END) > 0 
            THEN SUM(CASE WHEN pe.team_id = g.home_team_id THEN pe.points_scored ELSE 0 END)::DECIMAL / 
                 COUNT(CASE WHEN pe.team_id = g.home_team_id THEN 1 END)
            ELSE 0 
        END, 3
    ) as home_points_per_possession,
    
    -- Away team stats
    at.team_name as away_team_name,
    at.team_tricode as away_team_code,
    COUNT(CASE WHEN pe.team_id = g.away_team_id THEN 1 END) as away_possessions,
    SUM(CASE WHEN pe.team_id = g.away_team_id THEN pe.points_scored ELSE 0 END) as away_points,
    ROUND(
        CASE 
            WHEN COUNT(CASE WHEN pe.team_id = g.away_team_id THEN 1 END) > 0 
            THEN SUM(CASE WHEN pe.team_id = g.away_team_id THEN pe.points_scored ELSE 0 END)::DECIMAL / 
                 COUNT(CASE WHEN pe.team_id = g.away_team_id THEN 1 END)
            ELSE 0 
        END, 3
    ) as away_points_per_possession,
    
    -- Total game stats
    COUNT(*) as total_possessions,
    SUM(pe.points_scored) as total_points
    
FROM possession_events pe
JOIN games g ON pe.game_id = g.game_id
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
GROUP BY pe.game_id, g.game_date, g.season, g.home_team_id, g.away_team_id,
         ht.team_name, ht.team_tricode, at.team_name, at.team_tricode;

-- =============================================================================
-- POSSESSION OUTCOME ANALYSIS
-- =============================================================================

-- Possession outcomes by team
CREATE OR REPLACE VIEW team_possession_outcomes AS
SELECT 
    pe.team_id,
    t.team_name,
    t.team_tricode,
    pe.possession_outcome,
    COUNT(*) as possession_count,
    SUM(pe.points_scored) as total_points,
    ROUND(AVG(pe.points_scored), 3) as avg_points_per_possession,
    ROUND(COUNT(*)::DECIMAL * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY pe.team_id), 2) as outcome_percentage
FROM possession_events pe
LEFT JOIN teams t ON pe.team_id = t.team_id
WHERE pe.possession_outcome IS NOT NULL
GROUP BY pe.team_id, t.team_name, t.team_tricode, pe.possession_outcome
ORDER BY pe.team_id, possession_count DESC;

-- =============================================================================
-- PLAY EVENT POSSESSION CONTEXT
-- =============================================================================

-- Play events with possession context
CREATE OR REPLACE VIEW play_events_with_possession AS
SELECT 
    pe.*,
    pev.possession_number,
    pev.team_id as possession_team_id,
    pev.possession_outcome,
    pev.points_scored as possession_points,
    t.team_name as possession_team_name,
    t.team_tricode as possession_team_code
FROM play_events pe
LEFT JOIN possession_events pev ON pe.possession_id = pev.possession_id
LEFT JOIN teams t ON pev.team_id = t.team_id;

-- =============================================================================
-- POSSESSION EFFICIENCY METRICS
-- =============================================================================

-- Team possession efficiency by season
CREATE OR REPLACE VIEW team_season_possession_efficiency AS
SELECT 
    pe.team_id,
    t.team_name,
    t.team_tricode,
    g.season,
    COUNT(*) as total_possessions,
    SUM(pe.points_scored) as total_points,
    ROUND(AVG(pe.points_scored), 3) as points_per_possession,
    
    -- Outcome breakdown
    COUNT(CASE WHEN pe.possession_outcome = 'made_shot' THEN 1 END) as made_shots,
    COUNT(CASE WHEN pe.possession_outcome = 'turnover' THEN 1 END) as turnovers,
    COUNT(CASE WHEN pe.possession_outcome = 'defensive_rebound' THEN 1 END) as defensive_rebounds_against,
    
    -- Efficiency percentages
    ROUND(COUNT(CASE WHEN pe.possession_outcome = 'made_shot' THEN 1 END)::DECIMAL * 100.0 / COUNT(*), 2) as made_shot_percentage,
    ROUND(COUNT(CASE WHEN pe.possession_outcome = 'turnover' THEN 1 END)::DECIMAL * 100.0 / COUNT(*), 2) as turnover_percentage,
    
    -- Games played
    COUNT(DISTINCT pe.game_id) as games_played

FROM possession_events pe
LEFT JOIN teams t ON pe.team_id = t.team_id
LEFT JOIN games g ON pe.game_id = g.game_id
GROUP BY pe.team_id, t.team_name, t.team_tricode, g.season
ORDER BY g.season DESC, points_per_possession DESC;

-- =============================================================================
-- POSSESSION PLAY BREAKDOWN
-- =============================================================================

-- Count of plays per possession
CREATE OR REPLACE VIEW possession_play_counts AS
SELECT 
    pe.possession_id,
    pe.game_id,
    pe.possession_number,
    pe.team_id,
    t.team_tricode,
    pe.possession_outcome,
    pe.points_scored,
    COUNT(ppe.play_id) as play_count,
    STRING_AGG(pl.event_type, ', ' ORDER BY pl.event_order) as play_sequence
FROM possession_events pe
LEFT JOIN play_possession_events ppe ON pe.possession_id = ppe.possession_id
LEFT JOIN play_events pl ON ppe.play_id = pl.event_id
LEFT JOIN teams t ON pe.team_id = t.team_id
GROUP BY pe.possession_id, pe.game_id, pe.possession_number, pe.team_id, 
         t.team_tricode, pe.possession_outcome, pe.points_scored
ORDER BY pe.game_id, pe.possession_number;

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Additional indexes for view performance
CREATE INDEX IF NOT EXISTS idx_possession_events_team_outcome ON possession_events(team_id, possession_outcome);
CREATE INDEX IF NOT EXISTS idx_possession_events_game_team ON possession_events(game_id, team_id);
CREATE INDEX IF NOT EXISTS idx_play_possession_events_possession ON play_possession_events(possession_id);

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON VIEW possession_summary IS 'Complete possession information with team details and duration calculations';
COMMENT ON VIEW game_possession_stats IS 'Per-game possession statistics for both teams including efficiency metrics';
COMMENT ON VIEW team_possession_outcomes IS 'Breakdown of possession outcomes by team with percentages';
COMMENT ON VIEW play_events_with_possession IS 'Play events enriched with possession context information';
COMMENT ON VIEW team_season_possession_efficiency IS 'Season-level possession efficiency metrics by team';
COMMENT ON VIEW possession_play_counts IS 'Number of plays per possession with sequence information';