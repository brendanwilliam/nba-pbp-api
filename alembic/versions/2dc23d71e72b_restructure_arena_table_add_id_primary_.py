"""Restructure arena table: add id primary key, make arena_id non-primary

Revision ID: 2dc23d71e72b
Revises: f715ddd61071
Create Date: 2025-08-29 11:41:15.362970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2dc23d71e72b'
down_revision: Union[str, None] = 'f715ddd61071'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Drop existing foreign key constraint from game table
    op.drop_constraint('game_arena_id_fkey', 'game', type_='foreignkey')
    
    # Step 2: Drop the primary key constraint on arena_id
    op.drop_constraint('arena_pkey', 'arena', type_='primary')
    
    # Step 3: Add new id column as SERIAL primary key
    op.add_column('arena', sa.Column('id', sa.Integer(), nullable=False, autoincrement=True))
    op.create_primary_key('arena_pkey', 'arena', ['id'])
    
    # Step 4: Make arena_id nullable (since it comes from external data)
    op.alter_column('arena', 'arena_id', nullable=True)
    
    # Step 5: Rename game.arena_id to game.arena_internal_id for clarity and add foreign key
    op.add_column('game', sa.Column('arena_internal_id', sa.Integer(), nullable=True))
    op.create_foreign_key('game_arena_internal_id_fkey', 'game', 'arena', ['arena_internal_id'], ['id'])
    
    # Note: game.arena_id can remain as the WNBA-provided arena ID for reference


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the changes
    op.drop_constraint('game_arena_internal_id_fkey', 'game', type_='foreignkey')
    op.drop_column('game', 'arena_internal_id')
    op.drop_constraint('arena_pkey', 'arena', type_='primary')
    op.drop_column('arena', 'id')
    op.alter_column('arena', 'arena_id', nullable=False)
    op.create_primary_key('arena_pkey', 'arena', ['arena_id'])
    op.create_foreign_key('game_arena_id_fkey', 'game', 'arena', ['arena_id'], ['arena_id'])
