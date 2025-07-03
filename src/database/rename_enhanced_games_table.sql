-- Rename enhanced_games table to games
-- This script safely renames the enhanced_games table to games and removes the old games table

-- Step 1: Drop the old games table (it's referenced by scrape_queue, so we need to handle that)
-- First, let's check if there are any critical references we need to preserve
-- The old games table is only referenced by scrape_queue, which can be updated

-- Step 2: Drop foreign key constraints from enhanced_games table temporarily
ALTER TABLE game_officials DROP CONSTRAINT IF EXISTS game_officials_game_id_fkey;
ALTER TABLE game_periods DROP CONSTRAINT IF EXISTS game_periods_game_id_fkey;
ALTER TABLE play_events DROP CONSTRAINT IF EXISTS play_events_game_id_fkey;
ALTER TABLE player_game_stats DROP CONSTRAINT IF EXISTS player_game_stats_game_id_fkey;
ALTER TABLE team_game_stats DROP CONSTRAINT IF EXISTS team_game_stats_game_id_fkey;

-- Step 3: Drop the old games table (after backing up any critical data if needed)
DROP TABLE IF EXISTS games CASCADE;

-- Step 4: Rename enhanced_games to games
ALTER TABLE enhanced_games RENAME TO games;

-- Step 5: Rename the primary key constraint
ALTER TABLE games RENAME CONSTRAINT enhanced_games_pkey TO games_pkey;

-- Step 6: Rename the indexes
ALTER INDEX idx_enhanced_games_date RENAME TO idx_games_date;
ALTER INDEX idx_enhanced_games_season RENAME TO idx_games_season;
ALTER INDEX idx_enhanced_games_status RENAME TO idx_games_status;

-- Step 7: Re-add the foreign key constraints with correct names
ALTER TABLE game_officials ADD CONSTRAINT game_officials_game_id_fkey 
    FOREIGN KEY (game_id) REFERENCES games(game_id);
ALTER TABLE game_periods ADD CONSTRAINT game_periods_game_id_fkey 
    FOREIGN KEY (game_id) REFERENCES games(game_id);
ALTER TABLE play_events ADD CONSTRAINT play_events_game_id_fkey 
    FOREIGN KEY (game_id) REFERENCES games(game_id);
ALTER TABLE player_game_stats ADD CONSTRAINT player_game_stats_game_id_fkey 
    FOREIGN KEY (game_id) REFERENCES games(game_id);
ALTER TABLE team_game_stats ADD CONSTRAINT team_game_stats_game_id_fkey 
    FOREIGN KEY (game_id) REFERENCES games(game_id);

-- Step 8: Add the missing constraints from the schema
ALTER TABLE games ADD CONSTRAINT chk_different_teams 
    CHECK (home_team_id != away_team_id);
ALTER TABLE games ADD CONSTRAINT chk_game_status 
    CHECK (game_status IN (1, 2, 3));

-- Step 9: Create the updated timestamp trigger
CREATE TRIGGER update_games_updated_at BEFORE UPDATE ON games
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Step 10: Update any views that reference the old table name
DROP VIEW IF EXISTS game_summary;
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