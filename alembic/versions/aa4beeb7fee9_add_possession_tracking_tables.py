"""add_possession_tracking_tables

Revision ID: aa4beeb7fee9
Revises: c58eec2abb7d
Create Date: 2025-07-02 12:30:10.837296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa4beeb7fee9'
down_revision: Union[str, None] = 'c58eec2abb7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create possession_events table
    op.create_table(
        'possession_events',
        sa.Column('possession_id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('game_id', sa.String(20), nullable=False, index=True),
        sa.Column('possession_number', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False, index=True),
        sa.Column('start_period', sa.Integer(), nullable=False),
        sa.Column('start_time_remaining', sa.String(20)),
        sa.Column('start_seconds_elapsed', sa.Integer()),
        sa.Column('end_period', sa.Integer()),
        sa.Column('end_time_remaining', sa.String(20)),
        sa.Column('end_seconds_elapsed', sa.Integer()),
        sa.Column('possession_outcome', sa.String(50)),
        sa.Column('points_scored', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Index('idx_possession_events_game', 'game_id'),
        sa.Index('idx_possession_events_team', 'team_id'),
        sa.Index('idx_possession_events_game_possession', 'game_id', 'possession_number'),
        sa.UniqueConstraint('game_id', 'possession_number', name='uq_game_possession_number')
    )
    
    # Create play_possession_events junction table
    op.create_table(
        'play_possession_events',
        sa.Column('play_possession_events_id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('possession_id', sa.Integer(), nullable=False),
        sa.Column('play_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['possession_id'], ['possession_events.possession_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['play_id'], ['play_events.event_id'], ondelete='CASCADE'),
        sa.Index('idx_play_possession_possession', 'possession_id'),
        sa.Index('idx_play_possession_play', 'play_id'),
        sa.UniqueConstraint('possession_id', 'play_id', name='uq_possession_play')
    )
    
    # Add possession_id column to play_events table
    op.add_column('play_events', sa.Column('possession_id', sa.Integer(), nullable=True, index=True))
    op.create_foreign_key(
        'fk_play_events_possession_id', 
        'play_events', 
        'possession_events', 
        ['possession_id'], 
        ['possession_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove possession_id from play_events
    op.drop_constraint('fk_play_events_possession_id', 'play_events', type_='foreignkey')
    op.drop_column('play_events', 'possession_id')
    
    # Drop junction table
    op.drop_table('play_possession_events')
    
    # Drop possession_events table
    op.drop_table('possession_events')
