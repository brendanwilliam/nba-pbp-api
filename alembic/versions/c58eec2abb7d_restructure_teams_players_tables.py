"""restructure_teams_players_tables

Revision ID: c58eec2abb7d
Revises: 03384fe2273d
Create Date: 2025-06-22 21:01:28.642113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c58eec2abb7d'
down_revision: Union[str, None] = '03384fe2273d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create backup tables first
    op.execute('CREATE TABLE teams_backup AS SELECT * FROM teams')
    op.execute('CREATE TABLE players_backup AS SELECT * FROM players')
    
    # Add new columns to teams table
    op.add_column('teams', sa.Column('team_id', sa.Integer(), nullable=True))
    op.add_column('teams', sa.Column('team_tricode', sa.String(3), nullable=True))
    op.add_column('teams', sa.Column('full_name', sa.String(100), nullable=True))
    op.add_column('teams', sa.Column('nickname', sa.String(50), nullable=True))
    op.add_column('teams', sa.Column('founded', sa.Integer(), nullable=True))
    op.add_column('teams', sa.Column('arena', sa.String(100), nullable=True))
    op.add_column('teams', sa.Column('arena_capacity', sa.Integer(), nullable=True))
    op.add_column('teams', sa.Column('owner', sa.String(200), nullable=True))
    op.add_column('teams', sa.Column('general_manager', sa.String(100), nullable=True))
    op.add_column('teams', sa.Column('head_coach', sa.String(100), nullable=True))
    op.add_column('teams', sa.Column('d_league_affiliate', sa.String(100), nullable=True))
    op.add_column('teams', sa.Column('conference', sa.String(10), nullable=True))
    op.add_column('teams', sa.Column('division', sa.String(20), nullable=True))
    op.add_column('teams', sa.Column('wikipedia_url', sa.String(200), nullable=True))
    op.add_column('teams', sa.Column('basketball_ref_url', sa.String(200), nullable=True))
    
    # Copy existing tricode to team_tricode
    op.execute('UPDATE teams SET team_tricode = tricode')
    
    # Create player_team junction table
    op.create_table('player_team',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.String(20), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('jersey_number', sa.String(3), nullable=True),
        sa.Column('position', sa.String(10), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_player_team_person_id', 'player_team', ['person_id'])
    op.create_index('idx_player_team_team_id', 'player_team', ['team_id'])
    op.create_index('idx_player_team_active', 'player_team', ['is_active'])
    
    # Add new columns to players table
    op.add_column('players', sa.Column('person_id', sa.String(20), nullable=True))
    op.add_column('players', sa.Column('player_name', sa.String(100), nullable=True))
    op.add_column('players', sa.Column('player_name_i', sa.String(100), nullable=True))
    
    # Copy existing data to new columns
    op.execute('UPDATE players SET person_id = nba_id')
    op.execute("UPDATE players SET player_name = first_name || ' ' || last_name")
    op.execute("UPDATE players SET player_name_i = last_name || ', ' || first_name")
    
    # Migrate player-team relationships to junction table
    op.execute("""
        INSERT INTO player_team (person_id, team_id, jersey_number, position, is_active)
        SELECT p.person_id, p.team_id, p.jersey_number, p.position, true
        FROM players p
        WHERE p.team_id IS NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove new columns from teams
    op.drop_column('teams', 'team_id')
    op.drop_column('teams', 'team_tricode')
    op.drop_column('teams', 'full_name')
    op.drop_column('teams', 'nickname')
    op.drop_column('teams', 'founded')
    op.drop_column('teams', 'arena')
    op.drop_column('teams', 'arena_capacity')
    op.drop_column('teams', 'owner')
    op.drop_column('teams', 'general_manager')
    op.drop_column('teams', 'head_coach')
    op.drop_column('teams', 'd_league_affiliate')
    op.drop_column('teams', 'conference')
    op.drop_column('teams', 'division')
    op.drop_column('teams', 'wikipedia_url')
    op.drop_column('teams', 'basketball_ref_url')
    
    # Remove new columns from players
    op.drop_column('players', 'person_id')
    op.drop_column('players', 'player_name')
    op.drop_column('players', 'player_name_i')
    
    # Drop player_team table
    op.drop_index('idx_player_team_person_id', 'player_team')
    op.drop_index('idx_player_team_team_id', 'player_team')
    op.drop_index('idx_player_team_active', 'player_team')
    op.drop_table('player_team')
    
    # Drop backup tables
    op.execute('DROP TABLE IF EXISTS teams_backup')
    op.execute('DROP TABLE IF EXISTS players_backup')
