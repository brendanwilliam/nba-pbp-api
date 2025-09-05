#!/usr/bin/env python3
"""
Backfill script to calculate and populate efg and tsp columns for existing boxscore records.

This script calculates:
- efg (Effective FG%): (fgm + 0.5 * tpm) / fga
- tsp (True Shooting %): pts / (2 * (fga + 0.44 * fta))

Usage:
    python -m src.scripts.backfill_efg_tsp [--dry-run] [--verbose] [--batch-size 1000]
"""

import argparse
import logging
import sys
from typing import List, Tuple

from src.database.services import DatabaseService
from src.database.models import Boxscore


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def calculate_efg_tsp(fgm: int, tpm: int, fga: int, pts: int, fta: int) -> Tuple[float, float]:
    """
    Calculate effective FG% and true shooting %.
    
    Args:
        fgm: Field goals made
        tpm: Three-pointers made
        fga: Field goals attempted
        pts: Points scored
        fta: Free throws attempted
        
    Returns:
        tuple: (efg, tsp) or (None, None) if calculation impossible
    """
    efg = None
    tsp = None
    
    # Calculate effective FG% - (fgm + 0.5 * tpm) / fga
    if fga and fga > 0:
        efg = (fgm + 0.5 * tpm) / fga
    
    # Calculate true shooting % - pts / (2 * (fga + 0.44 * fta))
    denominator = 2 * (fga + 0.44 * fta)
    if denominator > 0:
        tsp = pts / denominator
    
    return efg, tsp


def backfill_efg_tsp(dry_run: bool = False, verbose: bool = False, batch_size: int = 1000) -> Tuple[int, int, List[str]]:
    """
    Backfill efg and tsp columns for existing boxscore records.
    
    Args:
        dry_run: If True, don't actually update the database
        verbose: Enable verbose logging
        batch_size: Number of records to process in each batch
        
    Returns:
        tuple: (total_records, updated_records, errors)
    """
    logger = logging.getLogger(__name__)
    
    with DatabaseService() as db:
        session = db.get_session()
        
        # Get all boxscore records that need to be updated (where efg or tsp is None)
        records_to_update = session.query(Boxscore).filter(
            (Boxscore.efg.is_(None)) | (Boxscore.tsp.is_(None))
        ).all()
        
        total_records = len(records_to_update)
        updated_records = 0
        errors = []
        
        logger.info(f"Found {total_records} boxscore records to update")
        
        if dry_run:
            logger.info("DRY RUN MODE - No database changes will be made")
        
        # Process records in batches
        for i in range(0, total_records, batch_size):
            batch = records_to_update[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} records)")
            
            for record in batch:
                try:
                    # Get current values, handling None cases
                    fgm = record.fgm or 0
                    tpm = record.tpm or 0
                    fga = record.fga or 0
                    pts = record.pts or 0
                    fta = record.fta or 0
                    
                    # Calculate efg and tsp
                    efg, tsp = calculate_efg_tsp(fgm, tpm, fga, pts, fta)
                    
                    # Update record if calculations were successful
                    updated = False
                    if record.efg is None and efg is not None:
                        record.efg = efg
                        updated = True
                        
                    if record.tsp is None and tsp is not None:
                        record.tsp = tsp
                        updated = True
                    
                    if updated:
                        updated_records += 1
                        if verbose:
                            efg_str = f"{efg:.3f}" if efg is not None else "None"
                            tsp_str = f"{tsp:.3f}" if tsp is not None else "None"
                            logger.debug(f"Updated boxscore {record.boxscore_id}: efg={efg_str}, tsp={tsp_str}")
                    
                except Exception as e:
                    error_msg = f"Error processing boxscore {record.boxscore_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Commit batch changes
            if not dry_run:
                try:
                    session.commit()
                    logger.info(f"Committed batch {i // batch_size + 1}")
                except Exception as e:
                    session.rollback()
                    error_msg = f"Error committing batch {i // batch_size + 1}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"Backfill completed: {updated_records}/{total_records} records updated")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during processing")
        
        return total_records, updated_records, errors


def main():
    """Main entry point for the backfill script"""
    parser = argparse.ArgumentParser(
        description="Backfill efg and tsp columns in boxscore table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m src.scripts.backfill_efg_tsp                    # Run the backfill
    python -m src.scripts.backfill_efg_tsp --dry-run         # Preview changes
    python -m src.scripts.backfill_efg_tsp --verbose         # Detailed logging
    python -m src.scripts.backfill_efg_tsp --batch-size 500  # Smaller batches
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating database'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of records to process in each batch (default: 1000)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        total, updated, errors = backfill_efg_tsp(
            dry_run=args.dry_run,
            verbose=args.verbose,
            batch_size=args.batch_size
        )
        
        print(f"\nBackfill Summary:")
        print(f"  Total records: {total}")
        print(f"  Updated records: {updated}")
        print(f"  Errors: {len(errors)}")
        
        if errors:
            print(f"\nFirst few errors:")
            for error in errors[:5]:
                print(f"  - {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
        if args.dry_run:
            print("\nDRY RUN MODE - No changes were made to the database")
        
        return 0 if len(errors) == 0 else 1
        
    except Exception as e:
        logger.error(f"Backfill script failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())