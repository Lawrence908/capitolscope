#!/usr/bin/env python3
"""
Demonstration script for the improved congressional trade ingestion system.

This script showcases all the data quality improvements including:
- Enhanced ticker extraction
- Security enrichment  
- Trade backfill
- Manual review generation
- Comprehensive reporting

Usage:
    python app/src/scripts/run_improved_import.py --csvs path/to/csv/directory
    python app/src/scripts/run_improved_import.py --demo  # Run with demo data
"""

import asyncio
import sys
import argparse
import tempfile
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the app/src directory to Python path
script_dir = Path(__file__).parent.resolve()
app_src_dir = script_dir.parent
sys.path.insert(0, str(app_src_dir))

from core.database import DatabaseManager, init_database, db_manager
from core.logging import get_logger
from domains.congressional.ingestion import CongressionalDataIngester
from domains.congressional.models import CongressMember, CongressionalTrade
from domains.securities.models import Security

logger = get_logger(__name__)


def create_demo_csv_data():
    """Create demonstration CSV data."""
    return [
        ['Member', 'DocID', 'Owner', 'Asset', 'Ticker', 'Transaction Type', 'Transaction Date', 'Notification Date', 'Amount', 'Filing Status', 'Description'],
        ['Pelosi', '20230001', 'SP', 'Apple Inc.', 'AAPL', 'P', '01/15/2023', '01/30/2023', '$1,001 - $15,000', 'N', 'Apple stock purchase'],
        ['McConnell', '20230002', 'C', 'Microsoft Corporation (MSFT)', '', 'S', '02/01/2023', '02/15/2023', '$15,001 - $50,000', 'N', 'Microsoft sale'],
        ['Schumer', '20230003', 'JT', 'Alphabet Inc. Class C', 'GOOGL', 'P', '02/10/2023', '02/25/2023', '$50,001 - $100,000', 'N', 'Google investment'],
        ['McCarthy', '20230004', 'C', 'Tesla Inc - TSLA', 'X', 'S', '03/01/2023', '03/15/2023', '$25,001 - $50,000', 'N', 'Tesla divestment'],
        ['AOC', '20230005', 'C', 'Walt Disney Company', '', 'P', '03/10/2023', '03/25/2023', '$5,001 - $15,000', 'N', 'Disney stock'],
        ['Cruz', '20230006', 'SP', 'BlackRock Liq FDS FedFund', 'CS', 'P', '04/01/2023', '04/15/2023', '$250,001 - $500,000', 'N', 'Cash sweep'],
        ['Warren', '20230007', 'C', 'US Treasury Bill Due 12/31/23', '', 'P', '04/10/2023', '04/25/2023', '$100,001 - $250,000', 'N', 'Treasury investment'],
        ['Graham', '20230008', 'JT', 'SPDR S&P 500 ETF Trust', 'SPY', 'P', '05/01/2023', '05/15/2023', '$15,001 - $50,000', 'N', 'S&P 500 ETF'],
        ['Sanders', '20230009', 'C', 'Unknown Biotech Corp XYZ', 'XYZ99', 'P', '05/10/2023', '05/25/2023', '$1,001 - $15,000', 'N', 'Speculative biotech'],
        ['Romney', '20230010', 'SP', 'Invalid Asset Name', '', 'S', '06/01/2023', '06/15/2023', '$0', 'N', 'Problematic entry'],
    ]


def write_demo_csv(csv_path: Path):
    """Write demonstration CSV data to file."""
    import csv
    
    demo_data = create_demo_csv_data()
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(demo_data)
    
    logger.info(f"Created demo CSV file with {len(demo_data)-1} trade records at {csv_path}")


def print_banner(title: str):
    """Print a formatted banner."""
    width = 80
    print("\n" + "="*width)
    print(f" {title.center(width-2)} ")
    print("="*width)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n📊 {title}")
    print("-" * (len(title) + 4))


def format_number(num):
    """Format a number with commas."""
    if isinstance(num, (int, float)):
        return f"{num:,}"
    return str(num)


def format_percentage(num, total):
    """Format a percentage."""
    if total > 0:
        return f"{(num / total) * 100:.1f}%"
    return "0.0%"


def print_comprehensive_report(results: Dict[str, Any]):
    """Print a comprehensive results report."""
    
    print_banner("📈 CONGRESSIONAL TRADE INGESTION RESULTS")
    
    # Overview Section
    print_section("Overview")
    print(f"• Processing Time: {results.get('processing_time', 0):.2f} seconds")
    print(f"• Files Processed: {format_number(results.get('csv_files_processed', 0))}")
    print(f"• Years Covered: {results.get('years_processed', 0)}")
    print(f"• Total Rows: {format_number(results.get('total_rows_processed', 0))}")
    if results.get('total_rows_processed', 0) > 0:
        print(f"• Processing Speed: {results.get('total_rows_processed', 0) / max(results.get('processing_time', 1), 0.1):.1f} rows/second")
    
    # Members Section
    print_section("Congress Members")
    print(f"• Members Created: {format_number(results.get('members_created', 0))}")
    print(f"• Members Updated: {format_number(results.get('members_updated', 0))}")
    
    # Trades Section
    print_section("Congressional Trades")
    total_trades = results.get('total_trades', 0)
    trades_with_security = results.get('trades_with_security', 0)
    trades_without_security = results.get('trades_without_security', 0)
    
    print(f"• Total Trades Created: {format_number(total_trades)}")
    print(f"• Trades Linked to Securities: {format_number(trades_with_security)} ({format_percentage(trades_with_security, total_trades)})")
    print(f"• Trades Without Securities: {format_number(trades_without_security)} ({format_percentage(trades_without_security, total_trades)})")
    print(f"• Trades Backfilled: {format_number(results.get('trades_backfilled', 0))}")
    
    # Ticker Extraction Section
    print_section("Ticker Extraction Performance")
    total_rows = results.get('total_rows_processed', 0)
    tickers_extracted = results.get('tickers_extracted', 0)
    
    print(f"• Tickers Successfully Extracted: {format_number(tickers_extracted)} ({format_percentage(tickers_extracted, total_rows)})")
    print(f"  ├─ From Ticker Field: {format_number(results.get('tickers_from_ticker_field', 0))}")
    print(f"  ├─ From Asset Description: {format_number(results.get('tickers_from_asset_description', 0))}")
    print(f"  └─ From Fuzzy Matching: {format_number(results.get('tickers_from_fuzzy_matching', 0))}")
    print(f"• Failed Extractions: {format_number(results.get('tickers_failed_extraction', 0))}")
    
    # Security Enrichment Section
    print_section("Security Enrichment")
    print(f"• Securities Enriched: {format_number(results.get('securities_enriched', 0))}")
    print(f"• Missing Exchange Info: {format_number(results.get('securities_with_missing_exchange', 0))}")
    print(f"• Missing Sector Info: {format_number(results.get('securities_with_missing_sector', 0))}")
    print(f"• Missing Asset Type Info: {format_number(results.get('securities_with_missing_asset_type', 0))}")
    
    # Error Analysis Section
    print_section("Error Analysis")
    print(f"• Failed Trades: {format_number(results.get('failed_trades', 0))}")
    print(f"• Parsing Errors: {format_number(results.get('parsing_errors', 0))}")
    print(f"• Validation Errors: {format_number(results.get('validation_errors', 0))}")
    
    # Manual Review Section
    print_section("Manual Review Items")
    print(f"• Total Items Generated: {format_number(results.get('manual_review_items_count', 0))}")
    
    # Top Unmatched Items
    top_unmatched_tickers = results.get('top_unmatched_tickers', {})
    if top_unmatched_tickers:
        print(f"\n🔍 Top Unmatched Tickers:")
        for ticker, count in list(top_unmatched_tickers.items())[:5]:
            print(f"  • {ticker}: {count} occurrences")
    
    top_unmatched_assets = results.get('top_unmatched_assets', {})
    if top_unmatched_assets:
        print(f"\n🔍 Top Unmatched Assets:")
        for asset, count in list(top_unmatched_assets.items())[:3]:
            asset_short = asset[:50] + "..." if len(asset) > 50 else asset
            print(f"  • {asset_short}: {count} occurrences")
    
    # Extraction Patterns
    print_section("Ticker Extraction Patterns")
    patterns = results.get('ticker_extraction_patterns', {})
    for pattern, count in patterns.items():
        print(f"• {pattern}: {format_number(count)} uses")
    
    # Quality Score
    print_section("Overall Quality Score")
    
    # Calculate quality metrics
    extraction_rate = (tickers_extracted / max(total_rows, 1)) * 100
    linking_rate = (trades_with_security / max(total_trades, 1)) * 100
    success_rate = ((total_trades - results.get('failed_trades', 0)) / max(total_trades, 1)) * 100
    
    overall_score = (extraction_rate * 0.4 + linking_rate * 0.4 + success_rate * 0.2)
    
    print(f"• Ticker Extraction Rate: {extraction_rate:.1f}%")
    print(f"• Trade Linking Rate: {linking_rate:.1f}%")
    print(f"• Processing Success Rate: {success_rate:.1f}%")
    print(f"• Overall Quality Score: {overall_score:.1f}%")
    
    # Quality Assessment
    if overall_score >= 90:
        quality_level = "🟢 EXCELLENT"
    elif overall_score >= 80:
        quality_level = "🟡 GOOD"
    elif overall_score >= 70:
        quality_level = "🟠 FAIR"
    else:
        quality_level = "🔴 NEEDS IMPROVEMENT"
    
    print(f"• Quality Assessment: {quality_level}")


def print_next_steps():
    """Print recommended next steps."""
    print_section("Recommended Next Steps")
    print("1. 📊 Review the manual_review_items.csv file for unmatched data")
    print("2. 🔧 Update company-to-ticker mappings based on findings")
    print("3. 🧪 Run the test suite to validate improvements:")
    print("   python app/src/scripts/test_data_quality_improvements.py")
    print("4. 🌱 Seed the securities database with additional data:")
    print("   python app/src/scripts/seed_securities_database.py --prices")
    print("5. 🚀 Start the API server to explore the data:")
    print("   cd app && python -m uvicorn main:app --reload")
    print("6. 📈 Generate analytics reports on the improved data quality")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run improved congressional trade ingestion")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--csvs', type=str, help='Path to directory containing CSV files')
    group.add_argument('--demo', action='store_true', help='Run with demonstration data')
    
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    parser.add_argument('--skip-enrichment', action='store_true', help='Skip security enrichment')
    parser.add_argument('--skip-backfill', action='store_true', help='Skip trade backfill')
    parser.add_argument('--strict-mode', action='store_true', help='Enable strict mode (fail on errors)')
    
    args = parser.parse_args()
    
    try:
        print_banner("🏛️ CAPITOLSCOPE IMPROVED CONGRESSIONAL TRADE INGESTION")
        
        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        
        # Setup CSV directory
        if args.demo:
            # Create temporary demo data
            temp_dir = Path(tempfile.mkdtemp())
            demo_csv = temp_dir / "demo_trades_2023.csv"
            write_demo_csv(demo_csv)
            csv_directory = str(temp_dir)
            logger.info(f"Using demo data in {csv_directory}")
        else:
            csv_directory = args.csvs
            if not Path(csv_directory).exists():
                raise ValueError(f"CSV directory does not exist: {csv_directory}")
        
        # Run ingestion with improved system
        logger.info("Starting improved congressional trade ingestion...")
        start_time = datetime.now()
        
        with db_manager.get_session() as session:
            # Initialize enhanced ingester
            ingester = CongressionalDataIngester(session)
            
            # Configure ingester
            ingester.auto_create_securities = True
            ingester.auto_enrich_securities = not args.skip_enrichment
            ingester.skip_invalid_trades = not args.strict_mode
            ingester.batch_size = args.batch_size
            
            logger.info(f"Configuration:")
            logger.info(f"  - Auto-create securities: {ingester.auto_create_securities}")
            logger.info(f"  - Auto-enrich securities: {ingester.auto_enrich_securities}")
            logger.info(f"  - Skip invalid trades: {ingester.skip_invalid_trades}")
            logger.info(f"  - Batch size: {ingester.batch_size}")
            
            # Run the import
            results = ingester.import_congressional_data_from_csvs_sync(csv_directory)
            
            # Run backfill if not skipped
            if not args.skip_backfill:
                logger.info("Running trade backfill...")
                backfill_stats = ingester.trade_backfiller.backfill_trades()
                results.update(backfill_stats)
        
        # Print comprehensive results
        print_comprehensive_report(results)
        
        # Print next steps
        print_next_steps()
        
        # Show database stats
        with db_manager.get_session() as session:
            trade_count = session.query(CongressionalTrade).count()
            member_count = session.query(CongressMember).count() 
            security_count = session.query(Security).count()
            
            print_section("Database Summary")
            print(f"• Total Congressional Trades: {format_number(trade_count)}")
            print(f"• Total Congress Members: {format_number(member_count)}")
            print(f"• Total Securities: {format_number(security_count)}")
        
        # Success message
        overall_success = (
            results.get('total_trades', 0) > 0 and
            results.get('failed_trades', 0) / max(results.get('total_trades', 1), 1) < 0.1
        )
        
        if overall_success:
            print_banner("✅ INGESTION COMPLETED SUCCESSFULLY")
            print("🎉 Congressional trade data has been successfully imported with enhanced quality!")
            print("📊 Review the detailed statistics above and check manual_review_items.csv")
            print("🚀 Your data is now ready for analysis and API access.")
        else:
            print_banner("⚠️ INGESTION COMPLETED WITH WARNINGS")
            print("📋 Please review the errors and manual review items.")
            print("🔧 Consider updating ticker mappings and re-running the import.")
        
        # Cleanup demo data
        if args.demo:
            import shutil
            shutil.rmtree(temp_dir)
            logger.info("Cleaned up demo data")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("🛑 Import interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Import failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)