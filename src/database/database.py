
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import os
from alembic.config import Config
from alembic import command
import logging

load_dotenv()

# Set up logging for Alembic
logging.basicConfig()
logging.getLogger('alembic').setLevel(logging.INFO)

def create_database_if_not_exists():
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    
    try:
        conn = psycopg2.connect(
            database="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False
        
    return True

def get_alembic_config():
    """Get Alembic configuration object"""
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alembic_cfg_path = os.path.join(current_dir, "alembic.ini")
    
    if not os.path.exists(alembic_cfg_path):
        raise FileNotFoundError(f"Alembic configuration file not found at: {alembic_cfg_path}")
        
    return Config(alembic_cfg_path)

def get_migration_status():
    """Get current migration status"""
    try:
        alembic_cfg = get_alembic_config()
        
        # Get current revision
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
        
        db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        engine = create_engine(db_url)
        
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            
        # Get head revision
        from alembic.script import ScriptDirectory
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script_dir.get_current_head()
        
        return {
            'current': current_rev,
            'head': head_rev,
            'up_to_date': current_rev == head_rev
        }
        
    except Exception as e:
        print(f"Error getting migration status: {e}")
        return None

def run_migrations():
    """Run Alembic migrations to upgrade the database to the latest version"""
    try:
        alembic_cfg = get_alembic_config()
        
        # Check current status first
        status = get_migration_status()
        if status and status['up_to_date']:
            print("Database is already up to date")
            return True
            
        # Run migrations
        print("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully")
        return True
        
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False

def verify_database_structure():
    """Verify all required tables exist with proper structure"""
    expected_tables = [
        'raw_game_data', 'scraping_sessions', 'database_versions',
        'arena', 'team', 'game', 'person', 'person_game', 'team_game', 
        'play', 'boxscore', 'alembic_version'
    ]
    
    try:
        from src.database.services import DatabaseConnection
        from sqlalchemy import text
        
        db_conn = DatabaseConnection()
        with db_conn.get_session() as session:
            result = session.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
            ))
            existing_tables = [row[0] for row in result]
            
            missing_tables = [table for table in expected_tables if table not in existing_tables]
            
            if missing_tables:
                print(f"❌ Missing tables: {', '.join(missing_tables)}")
                return False
            else:
                print(f"✅ All {len(expected_tables)} required tables exist")
                
            # Check key table structures
            print("\n📋 Table verification:")
            for table in ['arena', 'person', 'team']:
                result = session.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'id';"))
                has_id = result.fetchone() is not None
                print(f"  {table}: {'✅' if has_id else '❌'} has 'id' primary key")
                
            return True
            
    except Exception as e:
        print(f"❌ Error verifying database structure: {e}")
        return False

def full_database_setup():
    """Complete database setup for new developers"""
    print("🚀 Starting complete database setup...")
    
    # Step 1: Create database
    print("\n1️⃣ Creating database...")
    if not create_database_if_not_exists():
        print("❌ Database creation failed")
        return False
    
    # Step 2: Run migrations
    print("\n2️⃣ Running migrations...")
    if not run_migrations():
        print("❌ Migration failed")
        return False
    
    # Step 3: Verify structure
    print("\n3️⃣ Verifying database structure...")
    if not verify_database_structure():
        print("❌ Database verification failed")
        return False
    
    # Step 4: Test connection
    print("\n4️⃣ Testing database connection...")
    try:
        conn = psycopg2.connect(
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    print("\n🎉 Database setup completed successfully!")
    print("Your WNBA scraping database is ready to use.")
    return True

def main():
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            # Show migration status
            status = get_migration_status()
            if status:
                print(f"Current revision: {status['current']}")
                print(f"Head revision: {status['head']}")
                print(f"Up to date: {status['up_to_date']}")
            else:
                print("Could not get migration status")
            return
            
        elif command == "migrate":
            # Run migrations only
            if create_database_if_not_exists():
                run_migrations()
            return
            
        elif command == "create":
            # Create database only
            create_database_if_not_exists()
            return
            
        elif command == "verify":
            # Verify database structure
            verify_database_structure()
            return
            
        elif command == "setup":
            # Full setup for new developers
            full_database_setup()
            return
            
        elif command == "help":
            print("Usage: python -m src.database.database [command]")
            print("Commands:")
            print("  (no args)  - Create database, run migrations, and test connection")
            print("  setup      - Complete setup with verification (recommended for new developers)")
            print("  status     - Show current migration status")
            print("  migrate    - Create database and run migrations")
            print("  create     - Create database only")
            print("  verify     - Verify all required tables exist")
            print("  help       - Show this help message")
            return
    
    # Default behavior: full setup
    full_database_setup()


if __name__ == "__main__":
    main()