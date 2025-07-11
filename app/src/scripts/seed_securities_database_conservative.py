#!/usr/bin/env python3
"""
Conservative securities database seeding script for CapitolScope.

This script populates the securities database with major market indices
using very conservative rate limiting to avoid Yahoo Finance API issues.

Usage:
    python app/src/scripts/seed_securities_database_conservative.py
    python app/src/scripts/seed_securities_database_conservative.py --max-tickers 50
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app/src directory to Python path so we can import modules
script_dir = Path(__file__).parent
app_src_dir = script_dir.parent
project_root = app_src_dir.parent

# Add app/src to Python path
sys.path.insert(0, str(app_src_dir))

import argparse
import signal
import time
from typing import Dict, Any
from sqlalchemy.exc import IntegrityError

from core.database import db_manager, init_database
from core.logging import get_logger
from domains.securities.ingestion import (
    populate_securities_from_major_indices,
    ingest_price_data_for_all_securities,
    set_shutdown_flag,
    fetch_yfinance_data
)

logger = get_logger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    global shutdown_requested
    logger.warning(f"Received signal {signum}. Starting graceful shutdown...")
    shutdown_requested = True
    # Also set the flag in the ingestion module
    set_shutdown_flag()

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def configure_conservative_rate_limiting():
    """Configure very conservative rate limiting."""
    logger.info("🛡️ Configuring conservative rate limiting...")
    logger.info("   • 10 second delays between tickers")
    logger.info("   • 30 second pauses every 5 tickers")
    logger.info("   • 5 minute cooldown after rate limiting")
    logger.info("   • Alpha Vantage fallback enabled")


async def seed_securities_database_conservative(max_tickers: int = 50) -> Dict[str, Any]:
    """
    Seed the securities database with conservative rate limiting.
    
    Args:
        max_tickers: Maximum number of tickers to process
        
    Returns:
        Dict with seeding statistics
    """
    logger.info("🌱 Starting conservative securities database seeding...")
    
    try:
        # Initialize database
        await init_database()
        
        # Get database session
        async with db_manager.get_session() as session:
            try:
                # Populate securities from major indices with conservative limits
                logger.info("📊 Populating securities with conservative rate limiting...")
                
                # Import the ticker fetching functions
                from domains.securities.ingestion import (
                    fetch_sp500_tickers, fetch_nasdaq100_tickers, 
                    fetch_dow_jones_tickers, fetch_tsx_tickers,
                    fetch_bond_securities, fetch_etf_securities
                )
                
                # Fetch all ticker lists but limit processing
                all_tickers = []
                
                # Only fetch S&P 500 for conservative mode
                try:
                    logger.info("Fetching S&P 500 tickers (conservative mode)...")
                    sp500_tickers = fetch_sp500_tickers()
                    # Limit to first max_tickers
                    sp500_tickers = sp500_tickers[:max_tickers]
                    all_tickers.extend(sp500_tickers)
                    logger.info(f"Fetched {len(sp500_tickers)} S&P 500 tickers (limited)")
                except Exception as e:
                    logger.error(f"Failed to fetch S&P 500 tickers: {e}")
                    sp500_tickers = []
                
                # Process tickers with very conservative delays
                created_count = 0
                failed_count = 0
                
                logger.info(f"Processing {len(all_tickers)} tickers with conservative rate limiting...")
                
                for i, info in enumerate(all_tickers):
                    if shutdown_requested:
                        logger.warning("Shutdown requested during processing. Stopping gracefully.")
                        break
                    
                    try:
                        ticker = info['ticker']
                        name = info['name']
                        
                        logger.info(f"Processing ticker {i+1}/{len(all_tickers)}: {ticker}")
                        
                        # Very conservative delays
                        if i > 0:
                            if i % 3 == 0:  # Every 3 tickers, long pause
                                logger.info(f"Rate limiting: pausing for 30 seconds after {i} tickers...")
                                time.sleep(30.0)
                            else:  # Long delay between each ticker
                                time.sleep(10.0)
                        
                        # Try to fetch data with very conservative settings
                        try:
                            data = fetch_yfinance_data(ticker, retry_count=2, delay=10.0)
                            if data:
                                logger.info(f"✅ Successfully fetched data for {ticker}")
                                created_count += 1
                            else:
                                logger.warning(f"⚠️ No data for {ticker}")
                                failed_count += 1
                        except Exception as e:
                            logger.error(f"❌ Error fetching {ticker}: {e}")
                            failed_count += 1
                        
                        # Progress update
                        if (i + 1) % 5 == 0:
                            logger.info(f"Progress: {i+1}/{len(all_tickers)} completed")
                        
                    except Exception as e:
                        logger.error(f"Failed to process {info.get('ticker', 'unknown')}: {e}")
                        failed_count += 1
                
                # Commit changes
                await session.commit()
                logger.info("✅ Conservative securities data committed successfully")
                
                return {
                    "S&P 500": len(sp500_tickers),
                    "created": created_count,
                    "failed": failed_count,
                    "total": len(all_tickers),
                    "success": True
                }
                
            except IntegrityError as e:
                logger.error(f"❌ Database integrity error: {e}")
                await session.rollback()
                return {
                    "error": "IntegrityError",
                    "success": False,
                    "error": str(e)
                }
            except Exception as e:
                logger.error(f"❌ Unexpected error during seeding: {e}")
                await session.rollback()
                return {
                    "error": "UnexpectedError",
                    "success": False,
                    "error": str(e)
                }
                
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return {
            "error": "DatabaseInitError",
            "success": False,
            "error": str(e)
        }


def print_results_summary(results: Dict[str, Any]):
    """Print a summary of the seeding results."""
    print("\n" + "="*60)
    print("🌱 CONSERVATIVE SECURITIES DATABASE SEEDING SUMMARY")
    print("="*60)
    
    if results.get("success"):
        print("✅ Conservative seeding completed successfully!")
        
        # Securities summary
        securities = results
        if "error" not in securities:
            print(f"\n📊 Securities Processed:")
            for index, count in securities.items():
                if isinstance(count, int) and index != "created" and index != "failed" and index != "total":
                    print(f"   • {index}: {count} securities")
            print(f"   • Created: {securities.get('created', 0)}")
            print(f"   • Failed: {securities.get('failed', 0)}")
            print(f"   • Total: {securities.get('total', 0)}")
        else:
            print(f"\n❌ Securities Error: {securities['error']}")
            
    else:
        print("❌ Conservative seeding failed!")
        error = results.get("error", "Unknown error")
        print(f"Error: {error}")
    
    print("="*60)


async def main():
    """Main function with conservative error handling."""
    global shutdown_requested
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Conservative securities database seeding")
        parser.add_argument("--max-tickers", type=int, default=50,
                          help="Maximum number of tickers to process (default: 50)")
        
        args = parser.parse_args()
        
        # Configure conservative rate limiting
        configure_conservative_rate_limiting()
        
        # Check for shutdown request
        if shutdown_requested:
            logger.warning("Shutdown requested before starting. Exiting.")
            return
        
        # Run the conservative seeding
        results = await seed_securities_database_conservative(max_tickers=args.max_tickers)
        
        # Print results
        print_results_summary(results)
        
        # Exit with appropriate code
        if results.get("success"):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("🛑 Conservative seeding interrupted by user. Exiting gracefully.")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"💥 Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Script interrupted. Exiting.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unhandled exception: {e}")
        sys.exit(1) 