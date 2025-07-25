#!/usr/bin/env python3
"""
Securities database seeding script for CapitolScope.

This script populates the securities database with stock data from major market indices
(S&P 500, NASDAQ-100, Dow Jones) and fetches historical price data.

Usage:
    python scripts/seed_securities_database.py
    python scripts/seed_securities_database.py --prices  # Also fetch price data
    python scripts/seed_securities_database.py --batch-size 100
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add src directory to path
src_path = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(src_path))

from core.database import db_manager, init_database
import logging
logger = logging.getLogger(__name__)
from domains.securities.ingestion import (
    populate_securities_from_major_indices,
    ingest_price_data_for_all_securities
)


async def seed_securities_database(include_prices: bool = False, 
                                 batch_size: int = 50) -> Dict[str, Any]:
    """
    Seed the securities database with major market data.
    
    Args:
        include_prices: Whether to also fetch historical price data
        batch_size: Batch size for price data ingestion
        
    Returns:
        Dict with seeding statistics
    """
    logger.info("🌱 Starting securities database seeding...")
    
    # Initialize database connection
    await init_database()
    
    results = {}
    
    async with db_manager.session_scope() as session:
        try:
            # Step 1: Populate securities from major indices
            logger.info("📈 Populating securities from major market indices...")
            securities_result = await populate_securities_from_major_indices(session)
            results["securities"] = securities_result
            
            logger.info(f"✅ Securities populated: {securities_result}")
            
            # Step 2: Fetch price data (optional)
            if include_prices:
                logger.info("💰 Fetching historical price data for all securities...")
                logger.info(f"⚠️  This may take a while for {securities_result.get('created', 0)} securities...")
                
                prices_result = await ingest_price_data_for_all_securities(
                    session, batch_size=batch_size
                )
                results["prices"] = prices_result
                
                logger.info(f"✅ Price data ingested: {prices_result}")
            
            logger.info("🎉 Securities database seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Securities seeding failed: {e}")
            raise
    
    return results


def print_results_summary(results: Dict[str, Any]):
    """Print a formatted summary of the seeding results."""
    print("\n" + "="*60)
    print("📊 SECURITIES DATABASE SEEDING SUMMARY")
    print("="*60)
    
    if "securities" in results:
        sec_data = results["securities"]
        print(f"🏢 Securities Created:    {sec_data.get('created', 0):,}")
        print(f"❌ Securities Failed:     {sec_data.get('failed', 0):,}")
        print(f"📊 Total Tickers:        {sec_data.get('total_tickers', 0):,}")
    
    if "prices" in results:
        price_data = results["prices"]
        print(f"📈 Securities Processed:  {price_data.get('total_securities', 0):,}")
        print(f"💰 Price Records:        {price_data.get('total_price_records', 0):,}")
        print(f"❌ Failed Securities:    {price_data.get('failed_securities', 0):,}")
    
    print("="*60)


async def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Seed the securities database with stock data'
    )
    parser.add_argument(
        '--prices', 
        action='store_true',
        help='Also fetch historical price data (slow)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Batch size for price data processing (default: 50)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    try:
        # Show what we're about to do
        print("🚀 CapitolScope Securities Database Seeding")
        print("-" * 50)
        print(f"📊 Fetching major market indices (S&P 500, NASDAQ-100, Dow Jones)")
        if args.prices:
            print(f"💰 Will also fetch historical price data (batch size: {args.batch_size})")
            print(f"⏱️  Expected time: 30-60 minutes depending on network speed")
        else:
            print(f"⚡ Securities only (use --prices for historical data)")
            print(f"⏱️  Expected time: 2-5 minutes")
        print()
        
        # Run the seeding
        results = await seed_securities_database(
            include_prices=args.prices,
            batch_size=args.batch_size
        )
        
        # Print summary
        print_results_summary(results)
        
        # Next steps
        print("\n🎯 NEXT STEPS:")
        if not args.prices:
            print("1. Run with --prices to fetch historical data")
            print("   python scripts/seed_securities_database.py --prices")
        print("2. Import congressional trading data:")
        print("   python scripts/import_congressional_data.py")
        print("3. Start the API server:")
        print("   cd app && python -m uvicorn main:app --reload")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Seeding interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 