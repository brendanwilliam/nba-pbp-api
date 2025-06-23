#!/usr/bin/env python3
"""
Database Comparison Tool
Compares schema, table counts, and data between local and Neon databases
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import argparse
import os
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import json
except ImportError as e:
    print(f"Import error: {e}")
    print("This module requires psycopg2 to be installed.")
    print("Make sure you're running from the project root with the virtual environment activated.")
    sys.exit(1)

load_dotenv()


class DatabaseComparison:
    """Compare two PostgreSQL databases for schema and data differences"""
    
    def __init__(self, local_url: str = None, neon_url: str = None):
        """Initialize with database URLs"""
        self.local_url = local_url or "postgresql://brendan@localhost:5432/nba_pbp"
        self.neon_url = neon_url or "postgresql://nba_pbp_owner:npg_3wBZK4JXYVIR@ep-nameless-morning-a88pbjet-pooler.eastus2.azure.neon.tech/nba_pbp?sslmode=require"
    
    def connect_to_database(self, url: str) -> psycopg2.extensions.connection:
        """Create connection to database"""
        try:
            return psycopg2.connect(url)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    def get_database_info(self, conn: psycopg2.extensions.connection) -> Dict[str, Any]:
        """Get basic database information"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Database name and size
            cur.execute("""
                SELECT 
                    current_database() as database_name,
                    pg_size_pretty(pg_database_size(current_database())) as database_size,
                    pg_database_size(current_database()) as size_bytes
            """)
            db_info = cur.fetchone()
            
            # Table count
            cur.execute("""
                SELECT COUNT(*) as table_count
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_count = cur.fetchone()['table_count']
            
            return {
                'database_name': db_info['database_name'],
                'database_size': db_info['database_size'],
                'size_bytes': db_info['size_bytes'],
                'table_count': table_count
            }
    
    def get_tables_info(self, conn: psycopg2.extensions.connection) -> Dict[str, Dict[str, Any]]:
        """Get information about all tables"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get table names and basic info
            cur.execute("""
                SELECT 
                    t.tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    c.reltuples::bigint as estimated_rows
                FROM pg_tables t
                JOIN pg_class c ON c.relname = t.tablename
                WHERE t.schemaname = 'public'
                ORDER BY t.tablename
            """)
            
            table_rows = cur.fetchall()
            tables = {}
            
            for row in table_rows:
                table_name = row['tablename']
                
                # Create new cursor for each table to avoid interference
                with conn.cursor(cursor_factory=RealDictCursor) as table_cur:
                    # Get exact row count
                    try:
                        table_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                        exact_rows = table_cur.fetchone()['count']
                    except:
                        exact_rows = row['estimated_rows']
                    
                    # Get column information
                    table_cur.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    
                    column_rows = table_cur.fetchall()
                    columns = [
                        {
                            'name': col['column_name'],
                            'type': col['data_type'],
                            'nullable': col['is_nullable'] == 'YES',
                            'default': col['column_default']
                        }
                        for col in column_rows
                    ]
                    
                    # Get indexes
                    table_cur.execute("""
                        SELECT indexname, indexdef
                        FROM pg_indexes 
                        WHERE tablename = %s
                    """, (table_name,))
                    
                    index_rows = table_cur.fetchall()
                    indexes = [
                        {'name': idx['indexname'], 'definition': idx['indexdef']}
                        for idx in index_rows
                    ]
                    
                    tables[table_name] = {
                        'size': row['size'],
                        'size_bytes': row['size_bytes'],
                        'estimated_rows': row['estimated_rows'],
                        'exact_rows': exact_rows,
                        'columns': columns,
                        'indexes': indexes,
                        'column_count': len(columns),
                        'index_count': len(indexes)
                    }
            
            return tables
    
    def compare_databases(self) -> Dict[str, Any]:
        """Compare local and Neon databases"""
        print("🔍 Connecting to databases...")
        
        # Connect to both databases
        try:
            local_conn = self.connect_to_database(self.local_url)
            print("✅ Connected to LOCAL database")
        except Exception as e:
            print(f"❌ Failed to connect to LOCAL database: {e}")
            return {"error": f"Local connection failed: {e}"}
        
        try:
            neon_conn = self.connect_to_database(self.neon_url)
            print("✅ Connected to NEON database")
        except Exception as e:
            print(f"❌ Failed to connect to NEON database: {e}")
            local_conn.close()
            return {"error": f"Neon connection failed: {e}"}
        
        print("\n📊 Analyzing databases...")
        
        try:
            # Get database information
            local_info = self.get_database_info(local_conn)
            neon_info = self.get_database_info(neon_conn)
            
            # Get table information
            print("   Analyzing LOCAL tables...")
            local_tables = self.get_tables_info(local_conn)
            
            print("   Analyzing NEON tables...")
            neon_tables = self.get_tables_info(neon_conn)
            
            # Compare the databases
            comparison = self._analyze_differences(local_info, neon_info, local_tables, neon_tables)
            
            return {
                'generated_at': datetime.now().isoformat(),
                'local_database': local_info,
                'neon_database': neon_info,
                'local_tables': local_tables,
                'neon_tables': neon_tables,
                'comparison': comparison
            }
            
        finally:
            local_conn.close()
            neon_conn.close()
    
    def _analyze_differences(self, local_info: Dict, neon_info: Dict, 
                           local_tables: Dict, neon_tables: Dict) -> Dict[str, Any]:
        """Analyze differences between databases"""
        
        # Database-level differences
        db_differences = {
            'table_count_difference': local_info['table_count'] - neon_info['table_count'],
            'size_difference_bytes': local_info['size_bytes'] - neon_info['size_bytes'],
            'size_difference_readable': f"{(local_info['size_bytes'] - neon_info['size_bytes']) / (1024*1024*1024):.2f} GB"
        }
        
        # Table differences
        local_table_names = set(local_tables.keys())
        neon_table_names = set(neon_tables.keys())
        
        tables_only_in_local = local_table_names - neon_table_names
        tables_only_in_neon = neon_table_names - local_table_names
        common_tables = local_table_names & neon_table_names
        
        # Analyze common tables
        table_differences = {}
        schema_mismatches = []
        row_count_differences = {}
        
        for table_name in common_tables:
            local_table = local_tables[table_name]
            neon_table = neon_tables[table_name]
            
            # Compare schemas
            local_cols = {col['name']: col for col in local_table['columns']}
            neon_cols = {col['name']: col for col in neon_table['columns']}
            
            schema_diff = {
                'columns_only_in_local': list(set(local_cols.keys()) - set(neon_cols.keys())),
                'columns_only_in_neon': list(set(neon_cols.keys()) - set(local_cols.keys())),
                'column_count_difference': len(local_cols) - len(neon_cols),
                'index_count_difference': local_table['index_count'] - neon_table['index_count']
            }
            
            # Check for column type differences in common columns
            common_columns = set(local_cols.keys()) & set(neon_cols.keys())
            type_differences = []
            for col_name in common_columns:
                if local_cols[col_name]['type'] != neon_cols[col_name]['type']:
                    type_differences.append({
                        'column': col_name,
                        'local_type': local_cols[col_name]['type'],
                        'neon_type': neon_cols[col_name]['type']
                    })
            
            schema_diff['column_type_differences'] = type_differences
            
            if (schema_diff['columns_only_in_local'] or 
                schema_diff['columns_only_in_neon'] or 
                schema_diff['column_type_differences']):
                schema_mismatches.append({
                    'table': table_name,
                    'differences': schema_diff
                })
            
            # Compare row counts
            row_diff = local_table['exact_rows'] - neon_table['exact_rows']
            if row_diff != 0:
                row_count_differences[table_name] = {
                    'local_rows': local_table['exact_rows'],
                    'neon_rows': neon_table['exact_rows'],
                    'difference': row_diff
                }
            
            table_differences[table_name] = schema_diff
        
        return {
            'database_differences': db_differences,
            'table_summary': {
                'total_local_tables': len(local_table_names),
                'total_neon_tables': len(neon_table_names),
                'common_tables': len(common_tables),
                'tables_only_in_local': list(tables_only_in_local),
                'tables_only_in_neon': list(tables_only_in_neon)
            },
            'schema_mismatches': schema_mismatches,
            'row_count_differences': row_count_differences,
            'summary': {
                'databases_identical': (
                    len(tables_only_in_local) == 0 and 
                    len(tables_only_in_neon) == 0 and 
                    len(schema_mismatches) == 0 and 
                    len(row_count_differences) == 0
                ),
                'schema_differences_count': len(schema_mismatches),
                'row_differences_count': len(row_count_differences),
                'missing_tables_count': len(tables_only_in_local) + len(tables_only_in_neon)
            }
        }
    
    def print_summary_report(self, comparison_data: Dict[str, Any]):
        """Print a human-readable summary of the comparison"""
        print("=" * 80)
        print("DATABASE COMPARISON REPORT")
        print("=" * 80)
        
        local_info = comparison_data['local_database']
        neon_info = comparison_data['neon_database']
        comp = comparison_data['comparison']
        
        # Database overview
        print(f"\nDATABASE OVERVIEW")
        print(f"   LOCAL:  {local_info['database_name']} ({local_info['database_size']}, {local_info['table_count']} tables)")
        print(f"   NEON:   {neon_info['database_name']} ({neon_info['database_size']}, {neon_info['table_count']} tables)")
        
        # Summary
        summary = comp['summary']
        if summary['databases_identical']:
            print(f"\n✅ DATABASES ARE IDENTICAL")
            print(f"   All tables, schemas, and row counts match!")
        else:
            print(f"\n⚠️  DATABASES HAVE DIFFERENCES")
            print(f"   Schema differences: {summary['schema_differences_count']}")
            print(f"   Row count differences: {summary['row_differences_count']}")
            print(f"   Missing tables: {summary['missing_tables_count']}")
        
        # Table summary
        table_summary = comp['table_summary']
        print(f"\nTABLE SUMMARY")
        print(f"   Common tables: {table_summary['common_tables']}")
        
        if table_summary['tables_only_in_local']:
            print(f"   Tables only in LOCAL: {table_summary['tables_only_in_local']}")
        
        if table_summary['tables_only_in_neon']:
            print(f"   Tables only in NEON: {table_summary['tables_only_in_neon']}")
        
        # Schema differences
        if comp['schema_mismatches']:
            print(f"\nSCHEMA DIFFERENCES")
            print("-" * 50)
            for mismatch in comp['schema_mismatches']:
                table = mismatch['table']
                diff = mismatch['differences']
                print(f"   {table}:")
                
                if diff['columns_only_in_local']:
                    print(f"     Columns only in LOCAL: {diff['columns_only_in_local']}")
                
                if diff['columns_only_in_neon']:
                    print(f"     Columns only in NEON: {diff['columns_only_in_neon']}")
                
                if diff['column_type_differences']:
                    print(f"     Column type differences:")
                    for type_diff in diff['column_type_differences']:
                        print(f"       {type_diff['column']}: LOCAL={type_diff['local_type']}, NEON={type_diff['neon_type']}")
        
        # Row count differences
        if comp['row_count_differences']:
            print(f"\nROW COUNT DIFFERENCES")
            print("-" * 50)
            print(f"{'Table':<20} {'Local Rows':<12} {'Neon Rows':<12} {'Difference'}")
            print("-" * 50)
            
            for table, diff in comp['row_count_differences'].items():
                local_rows = f"{diff['local_rows']:,}"
                neon_rows = f"{diff['neon_rows']:,}"
                difference = f"{diff['difference']:+,}"
                print(f"{table:<20} {local_rows:<12} {neon_rows:<12} {difference}")
        
        print("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NBA Database Comparison Tool')
    parser.add_argument('--json', action='store_true', help='Output full comparison as JSON')
    parser.add_argument('--local-url', type=str, help='Local database URL (default: postgresql://brendan@localhost:5432/nba_pbp)')
    parser.add_argument('--neon-url', type=str, help='Neon database URL (default: from DATABASE_URL env var)')
    parser.add_argument('--summary', action='store_true', default=True, help='Show summary report (default)')
    
    args = parser.parse_args()
    
    try:
        # Initialize comparison tool
        comparator = DatabaseComparison(
            local_url=args.local_url,
            neon_url=args.neon_url
        )
        
        # Run comparison
        result = comparator.compare_databases()
        
        if 'error' in result:
            print(f"❌ Comparison failed: {result['error']}")
            sys.exit(1)
        
        if args.json:
            # Output JSON
            print(json.dumps(result, indent=2, default=str))
        else:
            # Print summary report
            comparator.print_summary_report(result)
            
    except KeyboardInterrupt:
        print("\nComparison interrupted by user")
    except Exception as e:
        print(f"Error during comparison: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Module execution support
if __name__ == "__main__" or __name__ == "src.database.database_comparison":
    if len(sys.argv) == 1 and __name__ == "src.database.database_comparison":
        # When run as module without args, show summary
        main()