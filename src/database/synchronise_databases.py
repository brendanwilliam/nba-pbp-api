#!/usr/bin/env python3
"""
Database Synchronization Tool
Synchronizes local database changes to Neon cloud database
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import argparse
import os
import subprocess
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
    import json
except ImportError as e:
    print(f"Import error: {e}")
    print("This module requires psycopg2 to be installed.")
    print("Make sure you're running from the project root with the virtual environment activated.")
    sys.exit(1)

load_dotenv()


class DatabaseSynchronizer:
    """Synchronize local database to Neon cloud database"""
    
    def __init__(self, local_url: str = None, neon_url: str = None, dry_run: bool = False):
        """Initialize with database URLs"""
        self.local_url = local_url or "postgresql://brendan@localhost:5432/nba_pbp"
        self.neon_url = neon_url or "postgresql://nba_pbp_owner:npg_3wBZK4JXYVIR@ep-nameless-morning-a88pbjet-pooler.eastus2.azure.neon.tech/nba_pbp?sslmode=require"
        self.dry_run = dry_run
        
        # Tables to exclude from synchronization (system/backup tables)
        self.excluded_tables = {
            'alembic_version',  # Handle separately
            'players_backup',
            'teams_backup'
        }
    
    def connect_to_database(self, url: str) -> psycopg2.extensions.connection:
        """Create connection to database"""
        try:
            return psycopg2.connect(url)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    def run_alembic_migrations(self) -> bool:
        """Run alembic migrations on Neon database"""
        print("🔄 Running Alembic migrations on Neon database...")
        
        if self.dry_run:
            print("   [DRY RUN] Would run: alembic upgrade head")
            return True
        
        try:
            # Temporarily set DATABASE_URL to Neon for alembic
            original_env = os.environ.get('DATABASE_URL')
            os.environ['DATABASE_URL'] = self.neon_url
            
            # Run alembic upgrade
            result = subprocess.run(
                ['alembic', 'upgrade', 'head'],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent  # Project root
            )
            
            # Restore original DATABASE_URL
            if original_env:
                os.environ['DATABASE_URL'] = original_env
            else:
                os.environ.pop('DATABASE_URL', None)
            
            if result.returncode == 0:
                print("   ✅ Migrations completed successfully")
                if result.stdout:
                    print(f"   Output: {result.stdout.strip()}")
                return True
            else:
                print(f"   ❌ Migration failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error running migrations: {e}")
            return False
    
    def get_table_list(self, conn: psycopg2.extensions.connection) -> List[str]:
        """Get list of tables to synchronize"""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename
            """)
            
            all_tables = [row[0] for row in cur.fetchall()]
            tables_to_sync = [t for t in all_tables if t not in self.excluded_tables]
            
            return tables_to_sync
    
    def get_table_schema(self, conn: psycopg2.extensions.connection, table_name: str) -> List[Dict]:
        """Get table schema information"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            return [dict(row) for row in cur.fetchall()]
    
    def truncate_table(self, conn: psycopg2.extensions.connection, table_name: str):
        """Truncate table (with CASCADE for foreign key constraints)"""
        with conn.cursor() as cur:
            if self.dry_run:
                print(f"   [DRY RUN] Would truncate table: {table_name}")
                return
            
            try:
                # Disable triggers and constraints temporarily for faster truncation
                cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
                print(f"   ✅ Truncated {table_name}")
            except Exception as e:
                print(f"   ⚠️  Could not truncate {table_name}: {e}")
                # Try DELETE instead
                cur.execute(f"DELETE FROM {table_name}")
                print(f"   ✅ Deleted all rows from {table_name}")
    
    def copy_table_data(self, local_conn: psycopg2.extensions.connection, 
                       neon_conn: psycopg2.extensions.connection, table_name: str) -> int:
        """Copy data from local table to Neon table"""
        
        # Get row count first
        with local_conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cur.fetchone()[0]
        
        if total_rows == 0:
            print(f"   📋 {table_name}: 0 rows (empty table)")
            return 0
        
        if self.dry_run:
            print(f"   [DRY RUN] Would copy {total_rows:,} rows to {table_name}")
            return total_rows
        
        # Get table schema to build column list
        schema = self.get_table_schema(local_conn, table_name)
        columns = [col['column_name'] for col in schema]
        column_list = ', '.join(columns)
        
        # Copy data in batches for large tables
        batch_size = 10000 if total_rows > 100000 else total_rows
        copied_rows = 0
        
        try:
            with local_conn.cursor(cursor_factory=RealDictCursor) as local_cur:
                with neon_conn.cursor() as neon_cur:
                    # Fetch and insert in batches
                    local_cur.execute(f"SELECT {column_list} FROM {table_name}")
                    
                    while True:
                        batch = local_cur.fetchmany(batch_size)
                        if not batch:
                            break
                        
                        # Convert to list of tuples for execute_values
                        batch_data = [tuple(row[col] for col in columns) for row in batch]
                        
                        # Build INSERT query
                        placeholders = ', '.join(['%s'] * len(columns))
                        insert_query = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
                        
                        # Use execute_values for efficient batch insert
                        execute_values(
                            neon_cur, 
                            insert_query, 
                            batch_data,
                            template=None,
                            page_size=1000
                        )
                        
                        copied_rows += len(batch)
                        
                        if total_rows > 10000:
                            print(f"   📋 {table_name}: {copied_rows:,}/{total_rows:,} rows copied...")
            
            neon_conn.commit()
            print(f"   ✅ {table_name}: {copied_rows:,} rows copied successfully")
            return copied_rows
            
        except Exception as e:
            neon_conn.rollback()
            print(f"   ❌ Failed to copy {table_name}: {e}")
            return 0
    
    def update_sequences(self, neon_conn: psycopg2.extensions.connection, table_name: str):
        """Update sequence values after data copy"""
        if self.dry_run:
            return
            
        with neon_conn.cursor() as cur:
            try:
                # Find sequences associated with this table
                cur.execute("""
                    SELECT column_name, column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    AND column_default LIKE 'nextval%%'
                """, (table_name,))
                
                for row in cur.fetchall():
                    column_name, default_val = row
                    if 'nextval' in default_val:
                        # Extract sequence name
                        sequence_name = default_val.split("'")[1].split("'")[0]
                        
                        # Update sequence to max value + 1
                        cur.execute(f"""
                            SELECT setval('{sequence_name}', 
                                         COALESCE((SELECT MAX({column_name}) FROM {table_name}), 1))
                        """)
                        
                neon_conn.commit()
                
            except Exception as e:
                print(f"   ⚠️  Could not update sequences for {table_name}: {e}")
    
    def synchronize_databases(self) -> Dict[str, Any]:
        """Main synchronization process"""
        start_time = datetime.now()
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        
        print("🔄 Starting database synchronization...")
        print(f"   Source: LOCAL database")
        print(f"   Target: NEON database")
        
        # Step 1: Run migrations
        if not self.run_alembic_migrations():
            return {"error": "Migration failed", "success": False}
        
        # Step 2: Connect to databases
        print("\n🔍 Connecting to databases...")
        
        try:
            local_conn = self.connect_to_database(self.local_url)
            print("   ✅ Connected to LOCAL database")
        except Exception as e:
            return {"error": f"Local connection failed: {e}", "success": False}
        
        try:
            neon_conn = self.connect_to_database(self.neon_url)
            print("   ✅ Connected to NEON database")
        except Exception as e:
            local_conn.close()
            return {"error": f"Neon connection failed: {e}", "success": False}
        
        try:
            # Step 3: Get tables to synchronize
            tables_to_sync = self.get_table_list(local_conn)
            print(f"\n📋 Found {len(tables_to_sync)} tables to synchronize")
            print(f"   Excluded tables: {list(self.excluded_tables)}")
            
            # Step 4: Synchronize each table
            results = {}
            total_rows_copied = 0
            
            print(f"\n🔄 Synchronizing tables...")
            
            for i, table_name in enumerate(tables_to_sync, 1):
                print(f"\n[{i}/{len(tables_to_sync)}] Synchronizing {table_name}...")
                
                try:
                    # Truncate target table
                    self.truncate_table(neon_conn, table_name)
                    
                    # Copy data
                    rows_copied = self.copy_table_data(local_conn, neon_conn, table_name)
                    
                    # Update sequences
                    if rows_copied > 0:
                        self.update_sequences(neon_conn, table_name)
                    
                    results[table_name] = {
                        "rows_copied": rows_copied,
                        "status": "success"
                    }
                    total_rows_copied += rows_copied
                    
                except Exception as e:
                    print(f"   ❌ Failed to synchronize {table_name}: {e}")
                    results[table_name] = {
                        "rows_copied": 0,
                        "status": "failed",
                        "error": str(e)
                    }
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Summary
            successful_tables = len([r for r in results.values() if r["status"] == "success"])
            failed_tables = len([r for r in results.values() if r["status"] == "failed"])
            
            print(f"\n🎯 SYNCHRONIZATION COMPLETE")
            print(f"   Duration: {duration}")
            print(f"   Tables processed: {len(tables_to_sync)}")
            print(f"   Successful: {successful_tables}")
            print(f"   Failed: {failed_tables}")
            print(f"   Total rows copied: {total_rows_copied:,}")
            
            if self.dry_run:
                print(f"   [DRY RUN] No actual changes were made")
            
            return {
                "success": True,
                "duration": str(duration),
                "tables_processed": len(tables_to_sync),
                "successful_tables": successful_tables,
                "failed_tables": failed_tables,
                "total_rows_copied": total_rows_copied,
                "results": results,
                "dry_run": self.dry_run
            }
            
        finally:
            local_conn.close()
            neon_conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NBA Database Synchronization Tool')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--local-url', type=str, help='Local database URL (default: postgresql://brendan@localhost:5432/nba_pbp)')
    parser.add_argument('--neon-url', type=str, help='Neon database URL (default: from DATABASE_URL env var)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--tables', type=str, nargs='+', help='Sync only specific tables (default: all)')
    
    args = parser.parse_args()
    
    try:
        # Confirm if not dry run
        if not args.dry_run:
            print("⚠️  WARNING: This will OVERWRITE all data in the Neon database!")
            print("   All existing data in Neon will be replaced with data from Local.")
            
            confirm = input("\nDo you want to continue? (yes/no): ").lower().strip()
            if confirm not in ['yes', 'y']:
                print("Synchronization cancelled.")
                return
        
        # Initialize synchronizer
        synchronizer = DatabaseSynchronizer(
            local_url=args.local_url,
            neon_url=args.neon_url,
            dry_run=args.dry_run
        )
        
        # Run synchronization
        result = synchronizer.synchronize_databases()
        
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        elif not result.get("success"):
            print(f"❌ Synchronization failed: {result.get('error')}")
            sys.exit(1)
        else:
            print("\n✅ Database synchronization completed successfully!")
            
    except KeyboardInterrupt:
        print("\nSynchronization interrupted by user")
    except Exception as e:
        print(f"Error during synchronization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Module execution support
if __name__ == "__main__" or __name__ == "src.database.synchronise_databases":
    if len(sys.argv) == 1 and __name__ == "src.database.synchronise_databases":
        # When run as module without args, show help
        print("Database Synchronization Tool")
        print("Usage: python -m src.database.synchronise_databases [options]")
        print("Use --help for detailed options")
        print("Warning: This will overwrite Neon database with local data!")
    else:
        main()