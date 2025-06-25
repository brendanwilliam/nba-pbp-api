#!/usr/bin/env python3
"""
Selective Database Synchronization Tool
Synchronizes only tables with differences between local and Neon databases
Supports table-by-table sync with difference detection

DOCUMENTATION:
- Complete guide: docs/database-management.md
- Quick reference: docs/selective-sync-quick-reference.md
- Usage examples: See --help or run --analyze for examples

COMMON USAGE:
- Daily check: python -m src.database.selective_sync --analyze --ignore-size
- Auto-sync: python -m src.database.selective_sync --sync --ignore-size
- Preview: python -m src.database.selective_sync --sync --dry-run
"""

import asyncio
import asyncpg
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


class SelectiveDatabaseSync:
    """Advanced database synchronization with selective table updates"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.local_url = 'postgresql://brendan@localhost:5432/nba_pbp'
        self.neon_url = os.getenv('DATABASE_URL')
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Tables to exclude from synchronization
        self.excluded_tables = {
            'alembic_version',
            'teams_backup',
            'teams_backup_sync', 
            'teams_backup_historical',
            'players_backup'
        }
        
        if not self.neon_url:
            raise ValueError("DATABASE_URL environment variable not found")
    
    async def connect_databases(self) -> Tuple[asyncpg.Connection, asyncpg.Connection]:
        """Connect to both databases"""
        try:
            local_conn = await asyncpg.connect(self.local_url)
            neon_conn = await asyncpg.connect(self.neon_url)
            return local_conn, neon_conn
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise
    
    async def get_table_info(self, conn: asyncpg.Connection, table_name: str) -> Dict[str, Any]:
        """Get comprehensive table information including schema and row count"""
        
        # Get column information
        columns = await conn.fetch("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
        """, table_name)
        
        # Get row count
        try:
            row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
        except Exception:
            row_count = 0
        
        # Get table size (approximate)
        table_size = await conn.fetchval("""
        SELECT pg_total_relation_size(schemaname||'.'||tablename)::bigint
        FROM pg_tables 
        WHERE tablename = $1 AND schemaname = 'public'
        """, table_name)
        
        return {
            'columns': {col['column_name']: {
                'data_type': col['data_type'],
                'is_nullable': col['is_nullable'],
                'column_default': col['column_default']
            } for col in columns},
            'row_count': row_count,
            'table_size': table_size or 0
        }
    
    async def get_all_tables(self, conn: asyncpg.Connection) -> Set[str]:
        """Get all table names from database"""
        tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        return {table['table_name'] for table in tables}
    
    async def compare_tables(self, table_name: str, local_info: Dict, neon_info: Dict) -> Dict[str, Any]:
        """Compare two table structures and data"""
        
        differences = {
            'schema_different': False,
            'row_count_different': False,
            'size_different': False,
            'missing_columns': [],
            'extra_columns': [],
            'different_columns': [],
            'row_diff': 0,
            'size_diff': 0,
            'needs_sync': False
        }
        
        # Compare schemas
        local_cols = set(local_info['columns'].keys())
        neon_cols = set(neon_info['columns'].keys())
        
        differences['missing_columns'] = list(local_cols - neon_cols)
        differences['extra_columns'] = list(neon_cols - local_cols)
        
        # Check for different column definitions
        common_cols = local_cols & neon_cols
        for col in common_cols:
            if local_info['columns'][col] != neon_info['columns'][col]:
                differences['different_columns'].append(col)
        
        differences['schema_different'] = bool(
            differences['missing_columns'] or 
            differences['extra_columns'] or 
            differences['different_columns']
        )
        
        # Compare row counts
        local_rows = local_info['row_count']
        neon_rows = neon_info['row_count']
        differences['row_count_different'] = local_rows != neon_rows
        differences['row_diff'] = local_rows - neon_rows
        
        # Compare sizes (only significant differences matter)
        local_size = local_info['table_size']
        neon_size = neon_info['table_size']
        size_diff = abs(local_size - neon_size)
        min_size = min(local_size, neon_size) if min(local_size, neon_size) > 0 else max(local_size, neon_size)
        
        # Only consider it different if >50% size difference AND >1MB difference
        differences['size_different'] = (
            size_diff > (min_size * 0.5) and size_diff > (1024 * 1024)
        ) if min_size > 0 else size_diff > (1024 * 1024)
        
        differences['size_diff'] = local_size - neon_size
        
        # Determine if sync is needed
        differences['needs_sync'] = (
            differences['schema_different'] or 
            differences['row_count_different'] or
            differences['size_different']
        )
        
        return differences
    
    async def sync_table_schema(self, neon_conn: asyncpg.Connection, table_name: str, local_info: Dict) -> bool:
        """Sync table schema from local to Neon"""
        try:
            print(f"  🏗️  Updating schema for {table_name}...")
            
            if not self.dry_run:
                # Backup existing table
                backup_name = f"{table_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await neon_conn.execute(f"DROP TABLE IF EXISTS {backup_name}")
                await neon_conn.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
                
                # Drop and recreate table (this is a simplified approach)
                # In production, you might want more sophisticated schema migration
                await neon_conn.execute(f"DROP TABLE {table_name} CASCADE")
                
                # Get CREATE TABLE statement from local database
                # This is a simplified version - you might want to use pg_dump for complex cases
                print(f"     ⚠️  Schema sync for {table_name} requires manual intervention")
                print(f"     Created backup: {backup_name}")
                return False
            else:
                print(f"     [DRY RUN] Would update schema for {table_name}")
                return True
                
        except Exception as e:
            print(f"  ❌ Schema sync failed for {table_name}: {e}")
            return False
    
    async def sync_table_data(self, local_conn: asyncpg.Connection, neon_conn: asyncpg.Connection, 
                            table_name: str, local_info: Dict, force: bool = False) -> bool:
        """Sync table data from local to Neon"""
        try:
            row_count = local_info['row_count']
            
            if row_count == 0:
                print(f"  📋 {table_name}: Empty table, skipping data sync")
                return True
            
            if row_count > 1000000 and not force:
                print(f"  ⚠️  {table_name}: Large table ({row_count:,} rows) - use --force to sync")
                return False
            
            print(f"  📝 Syncing {row_count:,} rows to {table_name}...")
            
            if not self.dry_run:
                # Clear target table
                await neon_conn.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")
                
                # Copy data in batches
                batch_size = 10000
                offset = 0
                
                while offset < row_count:
                    # Fetch batch from local
                    data = await local_conn.fetch(
                        f"SELECT * FROM {table_name} ORDER BY 1 LIMIT {batch_size} OFFSET {offset}"
                    )
                    
                    if not data:
                        break
                    
                    # Insert batch to Neon
                    if data:
                        columns = list(data[0].keys())
                        placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                        column_names = ', '.join(columns)
                        
                        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                        
                        for row in data:
                            values = [row[col] for col in columns]
                            await neon_conn.execute(insert_sql, *values)
                    
                    offset += batch_size
                    
                    if self.verbose:
                        progress = min(offset, row_count)
                        print(f"     Progress: {progress:,}/{row_count:,} ({progress/row_count*100:.1f}%)")
            
            else:
                print(f"     [DRY RUN] Would sync {row_count:,} rows to {table_name}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Data sync failed for {table_name}: {e}")
            return False
    
    async def analyze_differences(self, tables_to_check: Optional[List[str]] = None, 
                                ignore_size_only: bool = False) -> Dict[str, Any]:
        """Analyze differences between local and Neon databases"""
        
        local_conn, neon_conn = await self.connect_databases()
        
        try:
            print("🔍 Analyzing database differences...")
            
            # Get all tables from both databases
            local_tables = await self.get_all_tables(local_conn)
            neon_tables = await self.get_all_tables(neon_conn)
            
            # Filter out excluded tables
            local_tables -= self.excluded_tables
            neon_tables -= self.excluded_tables
            
            # If specific tables requested, filter to those
            if tables_to_check:
                tables_to_check_set = set(tables_to_check)
                local_tables &= tables_to_check_set
                neon_tables &= tables_to_check_set
            
            common_tables = local_tables & neon_tables
            local_only = local_tables - neon_tables
            neon_only = neon_tables - local_tables
            
            results = {
                'common_tables': {},
                'local_only': list(local_only),
                'neon_only': list(neon_only),
                'tables_needing_sync': [],
                'total_differences': 0
            }
            
            print(f"   📊 Found {len(common_tables)} common tables to analyze")
            
            # Analyze common tables
            for table_name in sorted(common_tables):
                if self.verbose:
                    print(f"   🔍 Analyzing {table_name}...")
                
                local_info = await self.get_table_info(local_conn, table_name)
                neon_info = await self.get_table_info(neon_conn, table_name)
                
                differences = await self.compare_tables(table_name, local_info, neon_info)
                
                results['common_tables'][table_name] = {
                    'local_info': local_info,
                    'neon_info': neon_info,
                    'differences': differences
                }
                
                # Apply ignore_size_only filter
                needs_sync = differences['needs_sync']
                if ignore_size_only and needs_sync:
                    # Only sync if there are schema or row count differences, not just size
                    needs_sync = (
                        differences['schema_different'] or 
                        differences['row_count_different']
                    )
                
                if needs_sync:
                    results['tables_needing_sync'].append(table_name)
                    results['total_differences'] += 1
            
            return results
            
        finally:
            await local_conn.close()
            await neon_conn.close()
    
    async def sync_tables(self, table_names: List[str], force_large: bool = False, 
                         schema_only: bool = False, data_only: bool = False) -> Dict[str, bool]:
        """Sync specific tables from local to Neon"""
        
        local_conn, neon_conn = await self.connect_databases()
        results = {}
        
        try:
            for table_name in table_names:
                print(f"\n🔄 Syncing table: {table_name}")
                
                try:
                    # Get table info
                    local_info = await self.get_table_info(local_conn, table_name)
                    neon_info = await self.get_table_info(neon_conn, table_name)
                    
                    # Check if table exists in both databases
                    if local_info['row_count'] is None:
                        print(f"  ❌ Table {table_name} not found in local database")
                        results[table_name] = False
                        continue
                    
                    differences = await self.compare_tables(table_name, local_info, neon_info)
                    
                    success = True
                    
                    # Sync schema if needed and requested
                    if differences['schema_different'] and not data_only:
                        if not schema_only:
                            print(f"  ⚠️  Schema differences detected for {table_name}")
                            print(f"      Missing columns: {differences['missing_columns']}")
                            print(f"      Extra columns: {differences['extra_columns']}")
                            print(f"      Different columns: {differences['different_columns']}")
                            print(f"      Use --schema-only flag to update schema first")
                            success = False
                        else:
                            success &= await self.sync_table_schema(neon_conn, table_name, local_info)
                    
                    # Sync data if needed and requested
                    if differences['row_count_different'] and not schema_only and success:
                        print(f"  📊 Row count difference: Local={local_info['row_count']:,}, Neon={neon_info['row_count']:,}")
                        success &= await self.sync_table_data(local_conn, neon_conn, table_name, local_info, force_large)
                    
                    if not differences['needs_sync']:
                        print(f"  ✅ {table_name}: No differences detected")
                        success = True
                    
                    results[table_name] = success
                    
                except Exception as e:
                    print(f"  ❌ Error syncing {table_name}: {e}")
                    results[table_name] = False
            
            return results
            
        finally:
            await local_conn.close()
            await neon_conn.close()
    
    def print_analysis_report(self, results: Dict[str, Any]):
        """Print a comprehensive analysis report"""
        
        print("\n" + "="*80)
        print("DATABASE DIFFERENCE ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Common tables analyzed: {len(results['common_tables'])}")
        print(f"   Tables needing sync: {len(results['tables_needing_sync'])}")
        print(f"   Tables only in LOCAL: {len(results['local_only'])}")
        print(f"   Tables only in NEON: {len(results['neon_only'])}")
        
        if results['tables_needing_sync']:
            print(f"\n⚠️  TABLES REQUIRING SYNCHRONIZATION:")
            print("-" * 50)
            
            for table_name in results['tables_needing_sync']:
                table_data = results['common_tables'][table_name]
                diff = table_data['differences']
                local_rows = table_data['local_info']['row_count']
                neon_rows = table_data['neon_info']['row_count']
                
                print(f"\n📋 {table_name}:")
                print(f"   Rows: Local={local_rows:,}, Neon={neon_rows:,} (diff: {diff['row_diff']:+,})")
                
                if diff['schema_different']:
                    print(f"   ⚠️  Schema differences:")
                    if diff['missing_columns']:
                        print(f"      Missing in Neon: {diff['missing_columns']}")
                    if diff['extra_columns']:
                        print(f"      Extra in Neon: {diff['extra_columns']}")
                    if diff['different_columns']:
                        print(f"      Different definitions: {diff['different_columns']}")
                
                if diff['row_count_different']:
                    print(f"   📊 Row count difference: {diff['row_diff']:+,}")
                
                if diff['size_different']:
                    size_mb = diff['size_diff'] / (1024*1024)
                    print(f"   💾 Size difference: {size_mb:+.1f} MB")
        
        if results['local_only']:
            print(f"\n📍 TABLES ONLY IN LOCAL:")
            for table in sorted(results['local_only']):
                print(f"   - {table}")
        
        if results['neon_only']:
            print(f"\n☁️  TABLES ONLY IN NEON:")
            for table in sorted(results['neon_only']):
                print(f"   - {table}")
        
        if not results['tables_needing_sync']:
            print(f"\n✅ All analyzed tables are synchronized!")
        else:
            print(f"\n💡 USAGE EXAMPLES:")
            print(f"   # Analyze only important differences:")
            print(f"   python -m src.database.selective_sync --analyze --ignore-size")
            print(f"   ")
            print(f"   # Sync specific table:")
            print(f"   python -m src.database.selective_sync --sync {results['tables_needing_sync'][0]}")
            print(f"   ")
            print(f"   # Sync all different tables (auto-detect):")
            print(f"   python -m src.database.selective_sync --sync --ignore-size")
            print(f"   ")
            print(f"   # Dry run first:")
            print(f"   python -m src.database.selective_sync --sync --dry-run --ignore-size")
        
        print("\n" + "="*80)


async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Selective Database Synchronization Tool")
    
    parser.add_argument('--analyze', action='store_true', 
                       help='Analyze differences between databases')
    parser.add_argument('--sync', nargs='*', metavar='TABLE',
                       help='Sync specific tables (or all different tables if no tables specified)')
    parser.add_argument('--tables', nargs='+', metavar='TABLE',
                       help='Specific tables to analyze or sync')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--force', action='store_true',
                       help='Force sync of large tables (>1M rows)')
    parser.add_argument('--schema-only', action='store_true',
                       help='Only sync schema, not data')
    parser.add_argument('--data-only', action='store_true',
                       help='Only sync data, not schema')
    parser.add_argument('--ignore-size', action='store_true',
                       help='Ignore size-only differences when analyzing')
    
    args = parser.parse_args()
    
    # Initialize synchronizer
    sync = SelectiveDatabaseSync(dry_run=args.dry_run, verbose=args.verbose)
    
    try:
        if args.analyze or (not args.sync and not args.tables):
            # Analyze mode
            print("🔍 ANALYZE MODE")
            if args.dry_run:
                print("🔍 DRY RUN - Analysis only")
            
            results = await sync.analyze_differences(args.tables, ignore_size_only=args.ignore_size)
            sync.print_analysis_report(results)
            
            if results['tables_needing_sync']:
                print(f"\n💡 To sync tables, use:")
                print(f"   python -m src.database.selective_sync --sync {' '.join(results['tables_needing_sync'])}")
            
        elif args.sync is not None:
            # Sync mode
            if args.dry_run:
                print("🔍 DRY RUN MODE - No changes will be made")
            
            if len(args.sync) == 0:
                # Sync all tables that need it
                print("🔄 AUTO-SYNC MODE: Finding tables that need synchronization...")
                results = await sync.analyze_differences(args.tables, ignore_size_only=args.ignore_size)
                tables_to_sync = results['tables_needing_sync']
                
                if not tables_to_sync:
                    print("✅ No tables need synchronization!")
                    return
                
                print(f"📋 Found {len(tables_to_sync)} tables to sync: {', '.join(tables_to_sync)}")
            else:
                # Sync specific tables
                tables_to_sync = args.sync
                print(f"🔄 MANUAL SYNC MODE: Syncing specified tables: {', '.join(tables_to_sync)}")
            
            # Perform sync
            results = await sync.sync_tables(
                tables_to_sync, 
                force_large=args.force,
                schema_only=args.schema_only,
                data_only=args.data_only
            )
            
            # Print results
            print(f"\n📊 SYNC RESULTS:")
            successful = [t for t, success in results.items() if success]
            failed = [t for t, success in results.items() if not success]
            
            if successful:
                print(f"✅ Successfully synced: {', '.join(successful)}")
            if failed:
                print(f"❌ Failed to sync: {', '.join(failed)}")
            
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))