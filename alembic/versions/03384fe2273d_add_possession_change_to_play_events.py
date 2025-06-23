"""add_possession_change_to_play_events

Revision ID: 03384fe2273d
Revises: add_lineup_tracking
Create Date: 2025-06-22 13:43:54.585280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03384fe2273d'
down_revision: Union[str, None] = 'add_lineup_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add possession_change column to play_events table with default value
    # This approach is more efficient for large tables
    op.add_column('play_events', sa.Column('possession_change', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove possession_change column
    op.drop_column('play_events', 'possession_change')
