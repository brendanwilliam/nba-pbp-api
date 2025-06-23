"""Add enhanced NBA database tables without conflicts

Revision ID: add_enhanced_tables
Revises: game_url_queue_001
Create Date: 2025-01-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_enhanced_tables'
down_revision = 'game_url_queue_001'
branch_labels = None
depends_on = None


def upgrade():
    # Only create tables that don't exist yet
    
    # Create arenas table (new)
    op.create_table('arenas',
        sa.Column('arena_id', sa.Integer(), nullable=False),
        sa.Column('arena_name', sa.String(100), nullable=False),
        sa.Column('arena_city', sa.String(100), nullable=False),
        sa.Column('arena_state', sa.String(10), nullable=True),
        sa.Column('arena_country', sa.String(3), server_default='US', nullable=True),
        sa.Column('arena_timezone', sa.String(50), nullable=True),
        sa.Column('arena_street_address', sa.Text(), nullable=True),
        sa.Column('arena_postal_code', sa.String(20), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('arena_id')
    )
    
    # Create officials table (new)
    op.create_table('officials',
        sa.Column('official_id', sa.Integer(), nullable=False),
        sa.Column('official_name', sa.String(100), nullable=False),
        sa.Column('name_i', sa.String(50), nullable=True),
        sa.Column('first_name', sa.String(50), nullable=True),
        sa.Column('family_name', sa.String(50), nullable=True),
        sa.Column('jersey_num', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('official_id')
    )
    
    # Create enhanced_games table (different from existing games table)
    op.create_table('enhanced_games',
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('game_code', sa.String(50), nullable=False),
        sa.Column('game_status', sa.Integer(), nullable=False),
        sa.Column('game_status_text', sa.String(20), nullable=True),
        sa.Column('season', sa.String(10), nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('game_time_utc', sa.DateTime(timezone=True), nullable=True),
        sa.Column('game_time_et', sa.DateTime(timezone=True), nullable=True),
        sa.Column('home_team_id', sa.Integer(), nullable=False),
        sa.Column('away_team_id', sa.Integer(), nullable=False),
        sa.Column('home_score', sa.Integer(), nullable=True),
        sa.Column('away_score', sa.Integer(), nullable=True),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.Column('game_clock', sa.String(20), nullable=True),
        sa.Column('duration', sa.String(10), nullable=True),
        sa.Column('attendance', sa.Integer(), nullable=True),
        sa.Column('sellout', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('series_game_number', sa.String(10), nullable=True),
        sa.Column('game_label', sa.String(100), nullable=True),
        sa.Column('game_sub_label', sa.String(100), nullable=True),
        sa.Column('series_text', sa.String(100), nullable=True),
        sa.Column('if_necessary', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('arena_id', sa.Integer(), nullable=True),
        sa.Column('is_neutral', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['arena_id'], ['arenas.arena_id'], ),
        sa.PrimaryKeyConstraint('game_id')
    )
    
    # Create game periods table (new)
    op.create_table('game_periods',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('period_number', sa.Integer(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('home_score', sa.Integer(), nullable=True),
        sa.Column('away_score', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['enhanced_games.game_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'period_number')
    )
    
    # Create game officials assignments table (new)
    op.create_table('game_officials',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('official_id', sa.Integer(), nullable=False),
        sa.Column('assignment', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['enhanced_games.game_id'], ),
        sa.ForeignKeyConstraint(['official_id'], ['officials.official_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create team game statistics table (new)
    op.create_table('team_game_stats',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('is_home_team', sa.Boolean(), nullable=False),
        sa.Column('stat_type', sa.String(20), nullable=False, server_default='team'),
        sa.Column('wins', sa.Integer(), nullable=True),
        sa.Column('losses', sa.Integer(), nullable=True),
        sa.Column('in_bonus', sa.Boolean(), nullable=True),
        sa.Column('timeouts_remaining', sa.Integer(), nullable=True),
        sa.Column('seed', sa.Integer(), nullable=True),
        sa.Column('minutes', sa.Integer(), nullable=True),
        sa.Column('field_goals_made', sa.Integer(), nullable=True),
        sa.Column('field_goals_attempted', sa.Integer(), nullable=True),
        sa.Column('field_goals_percentage', sa.Numeric(5, 3), nullable=True),
        sa.Column('three_pointers_made', sa.Integer(), nullable=True),
        sa.Column('three_pointers_attempted', sa.Integer(), nullable=True),
        sa.Column('three_pointers_percentage', sa.Numeric(5, 3), nullable=True),
        sa.Column('free_throws_made', sa.Integer(), nullable=True),
        sa.Column('free_throws_attempted', sa.Integer(), nullable=True),
        sa.Column('free_throws_percentage', sa.Numeric(5, 3), nullable=True),
        sa.Column('rebounds_offensive', sa.Integer(), nullable=True),
        sa.Column('rebounds_defensive', sa.Integer(), nullable=True),
        sa.Column('rebounds_total', sa.Integer(), nullable=True),
        sa.Column('assists', sa.Integer(), nullable=True),
        sa.Column('steals', sa.Integer(), nullable=True),
        sa.Column('blocks', sa.Integer(), nullable=True),
        sa.Column('turnovers', sa.Integer(), nullable=True),
        sa.Column('fouls_personal', sa.Integer(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('plus_minus_points', sa.Integer(), nullable=True),
        sa.Column('points_fast_break', sa.Integer(), nullable=True),
        sa.Column('points_in_paint', sa.Integer(), nullable=True),
        sa.Column('points_second_chance', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['enhanced_games.game_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'team_id', 'stat_type')
    )
    
    # Create player game statistics table (new)
    op.create_table('player_game_stats',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('jersey_number', sa.String(10), nullable=True),
        sa.Column('position', sa.String(10), nullable=True),
        sa.Column('starter', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=True),
        sa.Column('dnp_reason', sa.String(100), nullable=True),
        sa.Column('minutes_played', sa.Integer(), nullable=True),
        sa.Column('field_goals_made', sa.Integer(), nullable=True),
        sa.Column('field_goals_attempted', sa.Integer(), nullable=True),
        sa.Column('field_goals_percentage', sa.Numeric(5, 3), nullable=True),
        sa.Column('three_pointers_made', sa.Integer(), nullable=True),
        sa.Column('three_pointers_attempted', sa.Integer(), nullable=True),
        sa.Column('three_pointers_percentage', sa.Numeric(5, 3), nullable=True),
        sa.Column('free_throws_made', sa.Integer(), nullable=True),
        sa.Column('free_throws_attempted', sa.Integer(), nullable=True),
        sa.Column('free_throws_percentage', sa.Numeric(5, 3), nullable=True),
        sa.Column('rebounds_offensive', sa.Integer(), nullable=True),
        sa.Column('rebounds_defensive', sa.Integer(), nullable=True),
        sa.Column('rebounds_total', sa.Integer(), nullable=True),
        sa.Column('assists', sa.Integer(), nullable=True),
        sa.Column('steals', sa.Integer(), nullable=True),
        sa.Column('blocks', sa.Integer(), nullable=True),
        sa.Column('turnovers', sa.Integer(), nullable=True),
        sa.Column('fouls_personal', sa.Integer(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('plus_minus', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['enhanced_games.game_id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),  # Use existing players table
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'player_id')
    )
    
    # Create play-by-play events table (new)
    op.create_table('play_events',
        sa.Column('event_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('time_remaining', sa.String(20), nullable=True),
        sa.Column('time_elapsed_seconds', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_action_type', sa.String(50), nullable=True),
        sa.Column('event_sub_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('home_score', sa.Integer(), nullable=True),
        sa.Column('away_score', sa.Integer(), nullable=True),
        sa.Column('score_margin', sa.Integer(), nullable=True),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('shot_distance', sa.Numeric(5, 2), nullable=True),
        sa.Column('shot_made', sa.Boolean(), nullable=True),
        sa.Column('shot_type', sa.String(50), nullable=True),
        sa.Column('shot_zone', sa.String(50), nullable=True),
        sa.Column('shot_x', sa.Numeric(8, 2), nullable=True),
        sa.Column('shot_y', sa.Numeric(8, 2), nullable=True),
        sa.Column('assist_player_id', sa.Integer(), nullable=True),
        sa.Column('event_order', sa.Integer(), nullable=True),
        sa.Column('video_available', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.ForeignKeyConstraint(['assist_player_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['game_id'], ['enhanced_games.game_id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.PrimaryKeyConstraint('event_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_enhanced_games_season', 'enhanced_games', ['season'])
    op.create_index('idx_enhanced_games_date', 'enhanced_games', ['game_date'])
    op.create_index('idx_enhanced_games_status', 'enhanced_games', ['game_status'])
    
    op.create_index('idx_player_game_stats_game', 'player_game_stats', ['game_id'])
    op.create_index('idx_player_game_stats_player', 'player_game_stats', ['player_id'])
    op.create_index('idx_player_game_stats_team', 'player_game_stats', ['team_id'])
    
    op.create_index('idx_team_game_stats_game', 'team_game_stats', ['game_id'])
    op.create_index('idx_team_game_stats_team', 'team_game_stats', ['team_id'])
    
    op.create_index('idx_play_events_game', 'play_events', ['game_id'])
    op.create_index('idx_play_events_player', 'play_events', ['player_id'])
    op.create_index('idx_play_events_team', 'play_events', ['team_id'])
    op.create_index('idx_play_events_type', 'play_events', ['event_type'])
    op.create_index('idx_play_events_period', 'play_events', ['period'])
    op.create_index('idx_play_events_order', 'play_events', ['game_id', 'event_order'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_play_events_order', table_name='play_events')
    op.drop_index('idx_play_events_period', table_name='play_events')
    op.drop_index('idx_play_events_type', table_name='play_events')
    op.drop_index('idx_play_events_team', table_name='play_events')
    op.drop_index('idx_play_events_player', table_name='play_events')
    op.drop_index('idx_play_events_game', table_name='play_events')
    
    op.drop_index('idx_team_game_stats_team', table_name='team_game_stats')
    op.drop_index('idx_team_game_stats_game', table_name='team_game_stats')
    
    op.drop_index('idx_player_game_stats_team', table_name='player_game_stats')
    op.drop_index('idx_player_game_stats_player', table_name='player_game_stats')
    op.drop_index('idx_player_game_stats_game', table_name='player_game_stats')
    
    op.drop_index('idx_enhanced_games_status', table_name='enhanced_games')
    op.drop_index('idx_enhanced_games_date', table_name='enhanced_games')
    op.drop_index('idx_enhanced_games_season', table_name='enhanced_games')
    
    # Drop tables in reverse order
    op.drop_table('play_events')
    op.drop_table('player_game_stats')
    op.drop_table('team_game_stats')
    op.drop_table('game_officials')
    op.drop_table('game_periods')
    op.drop_table('enhanced_games')
    op.drop_table('officials')
    op.drop_table('arenas')