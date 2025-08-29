"""Restructure person table: add id primary key, make person_id non-primary

Revision ID: 5869dcf524f5
Revises: 2dc23d71e72b
Create Date: 2025-08-29 11:45:00.420638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5869dcf524f5'
down_revision: Union[str, None] = '2dc23d71e72b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Drop existing foreign key constraints from tables that reference person
    op.drop_constraint('boxscore_person_id_fkey', 'boxscore', type_='foreignkey')
    op.drop_constraint('person_game_person_id_fkey', 'person_game', type_='foreignkey')
    op.drop_constraint('play_person_id_fkey', 'play', type_='foreignkey')
    
    # Step 2: Drop the primary key constraint on person_id
    op.drop_constraint('person_pkey', 'person', type_='primary')
    
    # Step 3: Add new id column as SERIAL primary key
    op.add_column('person', sa.Column('id', sa.Integer(), nullable=False, autoincrement=True))
    op.create_primary_key('person_pkey', 'person', ['id'])
    
    # Step 4: Make person_id nullable (since it comes from external data)
    op.alter_column('person', 'person_id', nullable=True)
    
    # Step 5: Add person_internal_id columns to referencing tables and create foreign keys
    op.add_column('boxscore', sa.Column('person_internal_id', sa.Integer(), nullable=True))
    op.add_column('person_game', sa.Column('person_internal_id', sa.Integer(), nullable=True))
    op.add_column('play', sa.Column('person_internal_id', sa.Integer(), nullable=True))
    
    op.create_foreign_key('boxscore_person_internal_id_fkey', 'boxscore', 'person', ['person_internal_id'], ['id'])
    op.create_foreign_key('person_game_person_internal_id_fkey', 'person_game', 'person', ['person_internal_id'], ['id'])
    op.create_foreign_key('play_person_internal_id_fkey', 'play', 'person', ['person_internal_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the changes
    op.drop_constraint('boxscore_person_internal_id_fkey', 'boxscore', type_='foreignkey')
    op.drop_constraint('person_game_person_internal_id_fkey', 'person_game', type_='foreignkey')
    op.drop_constraint('play_person_internal_id_fkey', 'play', type_='foreignkey')
    
    op.drop_column('boxscore', 'person_internal_id')
    op.drop_column('person_game', 'person_internal_id')
    op.drop_column('play', 'person_internal_id')
    
    op.drop_constraint('person_pkey', 'person', type_='primary')
    op.drop_column('person', 'id')
    op.alter_column('person', 'person_id', nullable=False)
    op.create_primary_key('person_pkey', 'person', ['person_id'])
    
    op.create_foreign_key('boxscore_person_id_fkey', 'boxscore', 'person', ['person_id'], ['person_id'])
    op.create_foreign_key('person_game_person_id_fkey', 'person_game', 'person', ['person_id'], ['person_id'])
    op.create_foreign_key('play_person_id_fkey', 'play', 'person', ['person_id'], ['person_id'])
