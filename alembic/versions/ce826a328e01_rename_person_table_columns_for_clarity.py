"""Rename person table columns for clarity

Revision ID: ce826a328e01
Revises: 4a14fd7e5fef
Create Date: 2025-09-02 17:10:01.283781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce826a328e01'
down_revision: Union[str, None] = '4a14fd7e5fef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename person table columns for clarity
    op.alter_column('person', 'person_name_i', new_column_name='person_iname')
    op.alter_column('person', 'person_name_first', new_column_name='person_fname')
    op.alter_column('person', 'person_name_family', new_column_name='person_lname')


def downgrade() -> None:
    """Downgrade schema."""
    # Revert person table column renames
    op.alter_column('person', 'person_iname', new_column_name='person_name_i')
    op.alter_column('person', 'person_fname', new_column_name='person_name_first')
    op.alter_column('person', 'person_lname', new_column_name='person_name_family')
