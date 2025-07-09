#!/usr/bin/env python3
"""
Congressional data import script for CapitolScope.

This script imports congressional trading data from existing CSV files or fetches
live data, creates member profiles, and stores everything in the database.

Usage:
    python scripts/import_congressional_data.py --csvs  # Import from existing CSVs
    python scripts/import_congressional_data.py --live  # Fetch live data (10-15 min)
    python scripts/import_congressional_data.py --hybrid # CSVs + latest live data
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add src directory to path
src_path = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(src_path))

from core.database import db_manager, init_database, get_sync_db_session
from core.logging import get_logger
from domains.congressional.ingestion import (
    import_congressional_data_from_csvs,
    import_congressional_data_from_sqlite,
    enrich_member_profiles
)

logger = get_logger(__name__)


def import_from_csvs(csv_directory: str) -> Dict[str, Any]:
    """Import congressional data from existing CSV files."""
    logger.info("🗂️  Importing congressional data from CSV files...")
    
    with get_sync_db_session() as session:
        try:
            # Create synchronous ingester
            from domains.congressional.ingestion import CongressionalDataIngester
            ingester = CongressionalDataIngester(session)
            results = ingester.import_congressional_data_from_csvs_sync(csv_directory)
            logger.info(f"✅ CSV import completed: {results}")
            return results
        except Exception as e:
            logger.error(f"❌ CSV import failed: {e}")
            raise


async def fetch_live_data(years: list = None) -> Dict[str, Any]:
    """Fetch live congressional data using the existing fetch script."""
    logger.info("🔄 Fetching live congressional data...")
    
    if years is None:
        years = list(range(2014, 2026))  # 2014-2025
    
    results = {
        "years_processed": len(years),
        "total_records": 0,
        "total_members": 0
    }
    
    # Import the existing fetch script
    try:
        legacy_path = Path(__file__).parent.parent / "legacy" / "ingestion"
        sys.path.insert(0, str(legacy_path))
        
        from fetch_congress_data import CongressTrades
        
        for year in years:
            logger.info(f"📅 Processing year {year}...")
            try:
                congress_trades = CongressTrades(year=year)
                trades_df = congress_trades.trades
                
                if not trades_df.empty:
                    results["total_records"] += len(trades_df)
                    results["total_members"] += trades_df['Member'].nunique()
                    logger.info(f"✅ Year {year}: {len(trades_df)} trades from {trades_df['Member'].nunique()} members")
                else:
                    logger.warning(f"⚠️  No data found for year {year}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to fetch data for year {year}: {e}")
                continue
        
        # Now import the generated CSV files using synchronous session
        csv_directory = Path(__file__).parent.parent / "data" / "congress" / "csv"
        with get_sync_db_session() as session:
            from domains.congressional.ingestion import CongressionalDataIngester
            ingester = CongressionalDataIngester(session)
            import_results = ingester.import_congressional_data_from_csvs_sync(str(csv_directory))
            results.update(import_results)
        
        logger.info(f"✅ Live data fetch completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Live data fetch failed: {e}")
        raise


def enrich_members() -> Dict[str, Any]:
    """Enrich member profiles with additional data."""
    logger.info("👥 Enriching member profiles...")
    
    with get_sync_db_session() as session:
        try:
            from domains.congressional.ingestion import CongressionalDataIngester
            ingester = CongressionalDataIngester(session)
            results = ingester.enrich_member_data_sync()
            logger.info(f"✅ Member enrichment completed: {results}")
            return results
        except Exception as e:
            logger.error(f"❌ Member enrichment failed: {e}")
            raise


def print_results_summary(results: Dict[str, Any], mode: str):
    """Print a formatted summary of the import results."""
    print("\n" + "="*60)
    print(f"📊 CONGRESSIONAL DATA IMPORT SUMMARY ({mode.upper()})")
    print("="*60)
    
    if "csv_files_processed" in results:
        print(f"📁 CSV Files Processed:   {results.get('csv_files_processed', 0):,}")
    if "years_processed" in results:
        print(f"📅 Years Processed:       {results.get('years_processed', 0):,}")
    
    print(f"👥 Members Created:       {results.get('total_members', 0):,}")
    print(f"💼 Trades Imported:       {results.get('total_trades', 0):,}")
    print(f"❌ Failed Trades:         {results.get('failed_trades', 0):,}")
    
    if results.get('failed_trades', 0) > 0:
        success_rate = (results.get('total_trades', 0) / (results.get('total_trades', 0) + results.get('failed_trades', 0))) * 100
        print(f"✅ Success Rate:          {success_rate:.1f}%")
    
    print("="*60)


async def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Import congressional trading data into CapitolScope database'
    )
    
    # Import mode options
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--csvs', 
        action='store_true',
        help='Import from existing CSV files (fast)'
    )
    mode_group.add_argument(
        '--live', 
        action='store_true',
        help='Fetch live data from congress.gov (10-15 minutes)'
    )
    mode_group.add_argument(
        '--hybrid',
        action='store_true', 
        help='Import CSVs + fetch latest live data'
    )
    
    # Additional options
    parser.add_argument(
        '--csv-directory',
        type=str,
        default='data/congress/csv',
        help='Directory containing CSV files (default: data/congress/csv)'
    )
    parser.add_argument(
        '--years',
        nargs='+',
        type=int,
        help='Specific years to fetch (for --live mode)'
    )
    parser.add_argument(
        '--skip-enrichment',
        action='store_true',
        help='Skip member profile enrichment'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    import logging
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    try:
        # Show what we're about to do
        print("🏛️  CapitolScope Congressional Data Import")
        print("-" * 50)
        
        if args.csvs:
            print(f"📁 Mode: Import from CSV files")
            print(f"📂 Directory: {args.csv_directory}")
            print(f"⏱️  Expected time: 2-5 minutes")
        elif args.live:
            years_str = f"({', '.join(map(str, args.years))})" if args.years else "(2014-2025)"
            print(f"🔄 Mode: Fetch live data {years_str}")
            print(f"⏱️  Expected time: 10-15 minutes")
        elif args.hybrid:
            print(f"🔄 Mode: Hybrid (CSVs + latest live data)")
            print(f"⏱️  Expected time: 12-20 minutes")
        
        if not args.skip_enrichment:
            print(f"👥 Will enrich member profiles with additional data")
        print()
        
        # Initialize database
        await init_database()
        
        # Execute based on mode
        if args.csvs:
            results = import_from_csvs(args.csv_directory)
            mode = "CSV Import"
            
        elif args.live:
            results = await fetch_live_data(args.years)
            mode = "Live Fetch"
            
        elif args.hybrid:
            # First import existing CSVs
            logger.info("📁 Step 1: Importing existing CSV files...")
            csv_results = import_from_csvs(args.csv_directory)
            
            # Then fetch latest data (just 2025)
            logger.info("🔄 Step 2: Fetching latest live data...")
            live_results = await fetch_live_data([2025])
            
            # Combine results
            results = {
                "csv_files_processed": csv_results.get("csv_files_processed", 0),
                "years_processed": 1,  # Just 2025
                "total_members": csv_results.get("total_members", 0) + live_results.get("total_members", 0),
                "total_trades": csv_results.get("total_trades", 0) + live_results.get("total_trades", 0),
                "failed_trades": csv_results.get("failed_trades", 0) + live_results.get("failed_trades", 0)
            }
            mode = "Hybrid Import"
        
        # Enrich member profiles (unless skipped)
        if not args.skip_enrichment:
            enrich_results = enrich_members()
            results["members_enriched"] = enrich_results.get("members_enriched", 0)
        
        # Print summary
        print_results_summary(results, mode)
        
        # Next steps
        print("\n🎯 NEXT STEPS:")
        print("1. Start the API server:")
        print("   cd app && python -m uvicorn main:app --reload")
        print("2. View transactions in database:")
        print("   psql -d capitolscope -c 'SELECT COUNT(*) FROM congressional_trades;'")
        print("3. Check member profiles:")
        print("   psql -d capitolscope -c 'SELECT COUNT(*) FROM congress_members;'")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Import interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 