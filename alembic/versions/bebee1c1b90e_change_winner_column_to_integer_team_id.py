"""change winner column to integer team_id

Revision ID: bebee1c1b90e
Revises: 759dd870d75c
Create Date: 2025-09-04 16:46:38.396381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bebee1c1b90e'
down_revision: Union[str, None] = '759dd870d75c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop and recreate winner column with Integer type
    op.drop_column('game', 'winner')
    op.add_column('game', sa.Column('winner', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop and recreate winner column with VARCHAR type
    op.drop_column('game', 'winner')
    op.add_column('game', sa.Column('winner', sa.VARCHAR(length=1), nullable=True))
