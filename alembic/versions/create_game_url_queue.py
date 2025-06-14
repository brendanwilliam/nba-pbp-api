"""Create game URL queue table

Revision ID: game_url_queue_001
Revises: e194f204963a
Create Date: 2024-12-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'game_url_queue_001'
down_revision = 'e194f204963a'
branch_labels = None
depends_on = None


def upgrade():
    # Create the enhanced game_url_queue table
    op.create_table('game_url_queue',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('game_id', sa.VARCHAR(length=20), nullable=False),
        sa.Column('season', sa.VARCHAR(length=10), nullable=False),
        sa.Column('game_date', sa.DATE(), nullable=False),
        sa.Column('home_team', sa.VARCHAR(length=3), nullable=False),
        sa.Column('away_team', sa.VARCHAR(length=3), nullable=False),
        sa.Column('game_url', sa.TEXT(), nullable=False),
        sa.Column('game_type', sa.VARCHAR(length=20), nullable=True, server_default='regular'),
        sa.Column('status', sa.VARCHAR(length=20), nullable=True, server_default='pending'),
        sa.Column('priority', sa.INTEGER(), nullable=True, server_default='100'),
        sa.Column('url_validated', sa.BOOLEAN(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_game_url_queue_season', 'game_url_queue', ['season'])
    op.create_index('idx_game_url_queue_game_date', 'game_url_queue', ['game_date'])
    op.create_index('idx_game_url_queue_status', 'game_url_queue', ['status'])
    op.create_index('idx_game_url_queue_priority', 'game_url_queue', ['priority', 'game_date'], postgresql_ops={'priority': 'DESC', 'game_date': 'DESC'})
    op.create_index('idx_game_url_queue_validation', 'game_url_queue', ['url_validated', 'status'])
    op.create_index('idx_game_url_queue_type', 'game_url_queue', ['game_type'])
    
    # Create update trigger function if it doesn't exist
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create trigger for automatic updated_at
    op.execute("""
        CREATE TRIGGER update_game_url_queue_updated_at 
        BEFORE UPDATE ON game_url_queue 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create status check constraint
    op.execute("""
        ALTER TABLE game_url_queue 
        ADD CONSTRAINT check_status 
        CHECK (status IN ('pending', 'validated', 'invalid', 'scraped', 'failed'));
    """)
    
    # Create game_type check constraint
    op.execute("""
        ALTER TABLE game_url_queue 
        ADD CONSTRAINT check_game_type 
        CHECK (game_type IN ('regular', 'playoff', 'allstar', 'preseason'));
    """)


def downgrade():
    # Drop constraints
    op.execute("ALTER TABLE game_url_queue DROP CONSTRAINT IF EXISTS check_game_type;")
    op.execute("ALTER TABLE game_url_queue DROP CONSTRAINT IF EXISTS check_status;")
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_game_url_queue_updated_at ON game_url_queue;")
    
    # Drop indexes
    op.drop_index('idx_game_url_queue_type', table_name='game_url_queue')
    op.drop_index('idx_game_url_queue_validation', table_name='game_url_queue')
    op.drop_index('idx_game_url_queue_priority', table_name='game_url_queue')
    op.drop_index('idx_game_url_queue_status', table_name='game_url_queue')
    op.drop_index('idx_game_url_queue_game_date', table_name='game_url_queue')
    op.drop_index('idx_game_url_queue_season', table_name='game_url_queue')
    
    # Drop table
    op.drop_table('game_url_queue')