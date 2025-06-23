"""Add lineup tracking tables

Revision ID: add_lineup_tracking
Revises: add_enhanced_tables
Create Date: 2025-01-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_lineup_tracking'
down_revision = 'bd17b6278284'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create substitution_events table
    op.create_table(
        'substitution_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('action_number', sa.Integer, nullable=False),
        sa.Column('period', sa.Integer, nullable=False),
        sa.Column('clock_time', sa.String(20), nullable=False),
        sa.Column('seconds_elapsed', sa.Integer, nullable=False),
        sa.Column('team_id', sa.BigInteger, nullable=False),
        sa.Column('player_out_id', sa.BigInteger, nullable=False),
        sa.Column('player_out_name', sa.String(100), nullable=False),
        sa.Column('player_in_id', sa.BigInteger, nullable=False),
        sa.Column('player_in_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Create lineup_states table
    op.create_table(
        'lineup_states',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('game_id', sa.String(20), nullable=False),
        sa.Column('period', sa.Integer, nullable=False),
        sa.Column('clock_time', sa.String(20), nullable=False),
        sa.Column('seconds_elapsed', sa.Integer, nullable=False),
        sa.Column('team_id', sa.BigInteger, nullable=False),
        sa.Column('player_1_id', sa.BigInteger, nullable=False),
        sa.Column('player_2_id', sa.BigInteger, nullable=False),
        sa.Column('player_3_id', sa.BigInteger, nullable=False),
        sa.Column('player_4_id', sa.BigInteger, nullable=False),
        sa.Column('player_5_id', sa.BigInteger, nullable=False),
        sa.Column('lineup_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Create indexes for performance
    op.create_index('idx_substitution_events_game', 'substitution_events', ['game_id', 'period', 'seconds_elapsed'])
    op.create_index('idx_substitution_events_team', 'substitution_events', ['team_id', 'game_id'])
    op.create_index('idx_substitution_events_player_out', 'substitution_events', ['player_out_id'])
    op.create_index('idx_substitution_events_player_in', 'substitution_events', ['player_in_id'])
    
    op.create_index('idx_lineup_states_game_period_time', 'lineup_states', ['game_id', 'period', 'seconds_elapsed'])
    op.create_index('idx_lineup_states_team_time', 'lineup_states', ['team_id', 'game_id', 'seconds_elapsed'])
    op.create_index('idx_lineup_states_hash', 'lineup_states', ['lineup_hash'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_lineup_states_hash', table_name='lineup_states')
    op.drop_index('idx_lineup_states_team_time', table_name='lineup_states')
    op.drop_index('idx_lineup_states_game_period_time', table_name='lineup_states')
    
    op.drop_index('idx_substitution_events_player_in', table_name='substitution_events')
    op.drop_index('idx_substitution_events_player_out', table_name='substitution_events')
    op.drop_index('idx_substitution_events_team', table_name='substitution_events')
    op.drop_index('idx_substitution_events_game', table_name='substitution_events')
    
    # Drop tables
    op.drop_table('lineup_states')
    op.drop_table('substitution_events')