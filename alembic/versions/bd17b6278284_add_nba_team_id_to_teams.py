"""add_nba_team_id_to_teams

Revision ID: bd17b6278284
Revises: add_enhanced_tables
Create Date: 2025-06-19 10:02:59.044433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd17b6278284'
down_revision: Union[str, None] = 'add_enhanced_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nba_team_id column to teams table."""
    # Add nba_team_id column to teams table
    op.add_column('teams', sa.Column('nba_team_id', sa.String(20), nullable=True))
    
    # Add unique constraint on nba_team_id
    op.create_unique_constraint('uq_teams_nba_team_id', 'teams', ['nba_team_id'])
    
    # Add index for fast lookups
    op.create_index('idx_teams_nba_team_id', 'teams', ['nba_team_id'])


def downgrade() -> None:
    """Remove nba_team_id column from teams table."""
    # Remove index and constraint
    op.drop_index('idx_teams_nba_team_id', table_name='teams')
    op.drop_constraint('uq_teams_nba_team_id', 'teams', type_='unique')
    
    # Remove column
    op.drop_column('teams', 'nba_team_id')
