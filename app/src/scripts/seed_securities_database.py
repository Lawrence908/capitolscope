#!/usr/bin/env python3
"""
Securities database seeding script for CapitolScope.

This script populates the securities database with stock data from major market indices
(S&P 500, NASDAQ-100, Dow Jones) and fetches historical price data.

Usage:
    python app/src/scripts/seed_securities_database.py
    python app/src/scripts/seed_securities_database.py --prices  # Also fetch price data
    python app/src/scripts/seed_securities_database.py --batch-size 100
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
from typing import Dict, Any
from sqlalchemy.exc import IntegrityError

from core.database import db_manager, init_database
import logging
logger = logging.getLogger(__name__)
from domains.securities.ingestion import (
    populate_securities_from_major_indices,
    ingest_price_data_for_all_securities,
    set_shutdown_flag,
    fetch_yfinance_data
)

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


def configure_rate_limiting(strategy: str):
    """Configure rate limiting based on strategy."""
    if strategy == "conservative":
        # Very conservative - longer delays
        logger.info("🛡️ Using conservative rate limiting (longer delays)")
        # This will be handled by modifying the fetch_yfinance_data function
        # For now, we'll just log the strategy
    elif strategy == "aggressive":
        # More aggressive - shorter delays
        logger.info("⚡ Using aggressive rate limiting (shorter delays)")
    else:
        # Normal - default delays
        logger.info("⚖️ Using normal rate limiting (default delays)")


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
    
    try:
        # Initialize database
        await init_database()
        
        # Get database session
        async with db_manager.get_session() as session:
            try:
                # Populate securities from major indices
                logger.info("📊 Populating securities from major market indices...")
                securities_stats = await populate_securities_from_major_indices(session)
                
                # Commit the securities data
                await session.commit()
                logger.info("✅ Securities data committed successfully")
                
                price_stats = {}
                if include_prices:
                    logger.info("📈 Fetching historical price data...")
                    try:
                        price_stats = await ingest_price_data_for_all_securities(session, batch_size)
                        await session.commit()
                        logger.info("✅ Price data committed successfully")
                    except Exception as e:
                        logger.error(f"❌ Price data ingestion failed: {e}")
                        await session.rollback()
                        price_stats = {"error": str(e)}
                
                return {
                    "securities": securities_stats,
                    "prices": price_stats,
                    "success": True
                }
                
            except IntegrityError as e:
                logger.error(f"❌ Database integrity error: {e}")
                await session.rollback()
                return {
                    "securities": {"error": "IntegrityError"},
                    "prices": {},
                    "success": False,
                    "error": str(e)
                }
            except Exception as e:
                logger.error(f"❌ Unexpected error during seeding: {e}")
                await session.rollback()
                return {
                    "securities": {"error": "UnexpectedError"},
                    "prices": {},
                    "success": False,
                    "error": str(e)
                }
                
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return {
            "securities": {"error": "DatabaseInitError"},
            "prices": {},
            "success": False,
            "error": str(e)
        }


def print_results_summary(results: Dict[str, Any]):
    """Print a summary of the seeding results."""
    print("\n" + "="*60)
    print("🌱 SECURITIES DATABASE SEEDING SUMMARY")
    print("="*60)
    
    if results.get("success"):
        print("✅ Seeding completed successfully!")
        
        # Securities summary
        securities = results.get("securities", {})
        if "error" not in securities:
            print(f"\n📊 Securities Created:")
            for index, count in securities.items():
                if isinstance(count, int):
                    print(f"   • {index}: {count} securities")
        else:
            print(f"\n❌ Securities Error: {securities['error']}")
        
        # Price data summary
        prices = results.get("prices", {})
        if "error" not in prices:
            print(f"\n📈 Price Data:")
            for key, value in prices.items():
                if isinstance(value, int):
                    print(f"   • {key}: {value}")
        else:
            print(f"\n❌ Price Data Error: {prices['error']}")
            
    else:
        print("❌ Seeding failed!")
        error = results.get("error", "Unknown error")
        print(f"Error: {error}")
    
    print("="*60)


async def main():
    """Main function with robust error handling."""
    global shutdown_requested
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Seed securities database")
        parser.add_argument("--prices", action="store_true", 
                          help="Also fetch historical price data")
        parser.add_argument("--batch-size", type=int, default=50,
                          help="Batch size for price data ingestion")
        parser.add_argument("--rate-limit", type=str, choices=["conservative", "normal", "aggressive"], 
                          default="normal", help="Rate limiting strategy (default: normal)")
        
        args = parser.parse_args()
        
        # Configure rate limiting
        configure_rate_limiting(args.rate_limit)
        
        # Check for shutdown request
        if shutdown_requested:
            logger.warning("Shutdown requested before starting. Exiting.")
            return
        
        # Run the seeding
        results = await seed_securities_database(
            include_prices=args.prices,
            batch_size=args.batch_size
        )
        
        # Print results
        print_results_summary(results)
        
        # Exit with appropriate code
        if results.get("success"):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("🛑 Seeding interrupted by user. Exiting gracefully.")
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