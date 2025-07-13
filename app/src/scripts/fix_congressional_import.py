#!/usr/bin/env python3
"""
Congressional Data Import Recovery Script.

This script helps diagnose and fix issues with congressional data import,
including transaction rollback problems and data quality issues.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from core.database import get_sync_db_session
from core.logging import get_logger
from domains.congressional.ingestion import CongressionalDataIngester

logger = get_logger(__name__)

def check_database_state():
    """Check the current state of the database."""
    logger.info("Checking database state...")
    
    with get_sync_db_session() as session:
        try:
            # Check congressional_trades table
            result = session.execute("SELECT COUNT(*) FROM congressional_trades;")
            trade_count = result.scalar()
            logger.info(f"Current congressional trades count: {trade_count:,}")
            
            # Check latest trade dates
            result = session.execute("""
                SELECT 
                    MIN(transaction_date) as earliest_trade,
                    MAX(transaction_date) as latest_trade
                FROM congressional_trades 
                WHERE transaction_date IS NOT NULL;
            """)
            dates = result.fetchone()
            if dates:
                logger.info(f"Trade date range: {dates[0]} to {dates[1]}")
            
            # Check congress_members table
            result = session.execute("SELECT COUNT(*) FROM congress_members;")
            member_count = result.scalar()
            logger.info(f"Current congress members count: {member_count:,}")
            
            # Check for NULL tickers
            result = session.execute("SELECT COUNT(*) FROM congressional_trades WHERE ticker IS NULL;")
            null_ticker_count = result.scalar()
            logger.info(f"Trades with NULL ticker: {null_ticker_count:,}")
            
            # Check for failed/problematic data
            result = session.execute("""
                SELECT 
                    COUNT(*) as count,
                    EXTRACT(YEAR FROM transaction_date) as year
                FROM congressional_trades 
                WHERE transaction_date IS NOT NULL
                GROUP BY EXTRACT(YEAR FROM transaction_date)
                ORDER BY year;
            """)
            
            year_counts = result.fetchall()
            logger.info("Trades by year:")
            for count, year in year_counts:
                logger.info(f"  {int(year) if year else 'Unknown'}: {count:,} trades")
                
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False
    
    return True

def clear_failed_data():
    """Clear any failed/partial data from the database."""
    logger.info("Clearing failed data...")
    
    with get_sync_db_session() as session:
        try:
            # Clear trades with invalid data
            result = session.execute("""
                DELETE FROM congressional_trades 
                WHERE transaction_date IS NULL 
                   OR member_id IS NULL 
                   OR raw_asset_description IS NULL
                   OR raw_asset_description = '';
            """)
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} invalid trade records")
            
            session.commit()
            logger.info("Database cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            session.rollback()
            return False
    
    return True

def test_small_batch_import(data_directory: str, max_rows: int = 100):
    """Test import with a small batch to validate fixes."""
    logger.info(f"Testing import with {max_rows} rows...")
    
    data_path = Path(data_directory)
    if not data_path.exists():
        logger.error(f"Data directory does not exist: {data_directory}")
        return False
    
    # Find CSV files
    csv_files = list(data_path.glob("*FD.csv"))
    if not csv_files:
        logger.error("No CSV files found")
        return False
    
    # Test with the first file
    test_file = csv_files[0]
    logger.info(f"Testing with file: {test_file.name}")
    
    try:
        # Read and limit rows
        df = pd.read_csv(test_file)
        if len(df) > max_rows:
            df = df.head(max_rows)
            logger.info(f"Limited to {max_rows} rows for testing")
        
        with get_sync_db_session() as session:
            ingester = CongressionalDataIngester(session)
            
            # Test member extraction
            members_created = ingester._extract_and_create_members_sync(df)
            logger.info(f"Created {members_created} members")
            
            # Test trade import
            trades_created, trades_failed = ingester._import_trades_from_dataframe_sync(df, "TEST")
            logger.info(f"Import results: {trades_created} successful, {trades_failed} failed")
            
            if trades_failed > 0:
                logger.warning(f"Test import had {trades_failed} failures")
                return False
            
            logger.info("Test import completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Test import failed: {e}")
        return False

def main():
    """Main recovery function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Congressional data import recovery script')
    parser.add_argument('--check', action='store_true', help='Check database state')
    parser.add_argument('--clear', action='store_true', help='Clear failed data')
    parser.add_argument('--test', type=str, help='Test import with small batch (provide data directory)')
    parser.add_argument('--test-rows', type=int, default=100, help='Number of rows to test with')
    
    args = parser.parse_args()
    
    if args.check:
        success = check_database_state()
        if not success:
            return 1
    
    if args.clear:
        success = clear_failed_data()
        if not success:
            return 1
    
    if args.test:
        success = test_small_batch_import(args.test, args.test_rows)
        if not success:
            return 1
    
    if not any([args.check, args.clear, args.test]):
        logger.info("No action specified. Use --check, --clear, or --test")
        return 1
    
    logger.info("Recovery script completed successfully!")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 