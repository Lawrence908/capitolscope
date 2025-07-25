#!/usr/bin/env python3
"""
Congressional data import script for CapitolScope.

This script imports congressional trading data from existing CSV files or fetches
live data, creates member profiles, and stores everything in the database.

Usage:
    python scripts/import_congressional_data.py --csvs  # Import from existing CSVs
    python scripts/import_congressional_data.py --live  # Fetch live data (10-15 min)
    python scripts/import_congressional_data.py --hybrid # CSVs + latest live data
    
    
    docker exec -it capitolscope-dev python /app/src/scripts/import_congressional_data.py --csvs
    docker exec -it capitolscope-dev python /app/src/scripts/import_congressional_data.py --hybrid
    docker exec -it capitolscope-dev python /app/src/scripts/import_congressional_data.py --live
    docker exec -it capitolscope-dev python /app/src/scripts/import_congressional_data.py --live --years 2025
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

# Add the app/src directory to Python path so we can import modules
script_dir = Path(__file__).parent.resolve()
app_src_dir = script_dir.parent
project_root = app_src_dir.parent

# Add app/src to Python path
sys.path.insert(0, str(app_src_dir))

# Configure logging first
from core.logging import configure_logging
configure_logging()

from core.database import DatabaseManager, init_database, get_sync_db_session
import logging
logger = logging.getLogger(__name__)
from domains.congressional.ingestion import CongressionalDataIngestion

# Add a dedicated log file for this script
script_log_handler = logging.FileHandler("/app/logs/import_script.log")
script_log_handler.setLevel(logging.DEBUG)
script_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
script_log_handler.setFormatter(script_formatter)
logging.getLogger().addHandler(script_log_handler)


def resolve_data_path(input_path: str) -> Path:
    p = Path(input_path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def import_from_csvs(csv_directory: str) -> Dict[str, Any]:
    """Import congressional data from existing CSV files."""
    logger.info("🗂️  Importing congressional data from CSV files...")
    
    # Debug: Check what get_sync_db_session returns
    logger.info(f"DEBUG: get_sync_db_session type: {type(get_sync_db_session())}")
    logger.info(f"DEBUG: get_sync_db_session: {get_sync_db_session()}")
    
    with get_sync_db_session() as session:
        try:
            ingester = CongressionalDataIngestion(session=session)
            results = ingester.import_congressional_data_from_csvs_sync(csv_directory)
            logger.info(f"✅ CSV import completed: {results}")
            
            # Print error summary to console and log
            summary_lines = ["\n===== IMPORT ERROR SUMMARY ====="]
            for cat, count in ingester.error_counts.items():
                summary_lines.append(f"  {cat}: {count}")
            summary_lines.append("\nSample errors:")
            for cat, samples in ingester.error_samples.items():
                summary_lines.append(f"  {cat}:")
                for s in samples:
                    summary_lines.append(f"    - DocID: {s['doc_id']}, Member: {s['member_name']}, Msg: {s['message']}")
            summary = "\n".join(summary_lines)
            print(summary)
            logger.info(summary)

            ingester.export_failed_records()
            ingester.export_auto_created_members()
            return results
        except Exception as e:
            logger.error(f"❌ CSV import failed: {e}")
            raise


async def fetch_live_data(years: list = None) -> Dict[str, Any]:
    """Fetch live congressional data using Congress.gov API."""
    logger.info("🔄 Fetching live congressional data...")
    
    if years is None:
        years = list(range(2014, 2026))  # 2014-2025
    
    db_manager = DatabaseManager()
    await db_manager.initialize()

    if not db_manager.session_factory:
        raise RuntimeError("Database session factory not initialized")

    async with db_manager.session_factory() as session:
        try:
            # Use the Congress API service to fetch latest data
            from domains.congressional.services import CongressAPIService
            from domains.congressional.crud import CongressMemberRepository
            
            member_repo = CongressMemberRepository(session)
            api_service = CongressAPIService(member_repo)
            
            # Fetch members from Congress.gov API
            results = await api_service.sync_all_members()
            
            logger.info(f"✅ Live data fetch completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Live data fetch failed: {e}")
            raise


def enrich_members() -> Dict[str, Any]:
    """Enrich member profiles with additional data."""
    logger.info("👥 Enriching member profiles...")
    
    # Debug: Check what get_sync_db_session returns
    logger.info(f"DEBUG: get_sync_db_session type: {type(get_sync_db_session())}")
    logger.info(f"DEBUG: get_sync_db_session: {get_sync_db_session()}")
    
    with get_sync_db_session() as session:
        try:
            ingester = CongressionalDataIngestion(session=session)
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
        default='../../data/congress/csv',
        help='Directory containing CSV files (default: ../../data/congress/csv)'
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
        
        # Resolve data directory path
        csv_dir = resolve_data_path(args.csv_directory)
        if not csv_dir.exists():
            raise ValueError(f"Data directory does not exist: {csv_dir}")
        
        # Execute based on mode
        if args.csvs:
            results = import_from_csvs(csv_dir)
            mode = "CSV Import"
            
        elif args.live:
            results = await fetch_live_data(args.years)
            mode = "Live Fetch"
            
        elif args.hybrid:
            # First import existing CSVs
            logger.info("📁 Step 1: Importing existing CSV files...")
            csv_results = import_from_csvs(csv_dir)
            
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

        # Print error summary and export failed records
        if 'ingester' in locals():
            ingester.print_error_summary()
            ingester.export_failed_records()
        elif 'csv_results' in locals() and hasattr(csv_results, 'print_error_summary'):
            csv_results.print_error_summary()
            csv_results.export_failed_records()

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