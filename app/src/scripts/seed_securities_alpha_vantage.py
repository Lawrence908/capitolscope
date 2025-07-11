#!/usr/bin/env python3
"""
Alpha Vantage securities database seeding script for CapitolScope.

This script populates the securities database using only Alpha Vantage API
to avoid the widespread Yahoo Finance rate limiting issues.

Usage:
    python app/src/scripts/seed_securities_alpha_vantage.py
    python app/src/scripts/seed_securities_alpha_vantage.py --max-tickers 100
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
    fetch_security_data_alpha_vantage_only,
    fetch_sp500_tickers, fetch_nasdaq100_tickers, 
    fetch_dow_jones_tickers, fetch_tsx_tickers,
    fetch_bond_securities, fetch_etf_securities,
    set_shutdown_flag
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


def check_alpha_vantage_key():
    """Check if Alpha Vantage API key is set."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.error("❌ ALPHA_VANTAGE_API_KEY environment variable not set!")
        logger.error("Please set your Alpha Vantage API key:")
        logger.error("export ALPHA_VANTAGE_API_KEY=your_api_key_here")
        return False
    
    logger.info("✅ Alpha Vantage API key found")
    return True


async def seed_securities_alpha_vantage_only(max_tickers: int = 100) -> Dict[str, Any]:
    """
    Seed the securities database using only Alpha Vantage API.
    
    Args:
        max_tickers: Maximum number of tickers to process
        
    Returns:
        Dict with seeding statistics
    """
    logger.info("🌱 Starting Alpha Vantage securities database seeding...")
    
    # Check API key first
    if not check_alpha_vantage_key():
        return {
            "error": "NoAlphaVantageKey",
            "success": False,
            "error": "Alpha Vantage API key not set"
        }
    
    try:
        # Initialize database
        await init_database()
        
        # Get database session
        async with db_manager.get_session() as session:
            try:
                # Import database models
                from domains.securities.models import Security, AssetType, Exchange, Sector
                from domains.securities.ingestion import get_or_create_asset_type, get_or_create_exchange, get_or_create_sector
                
                # Create reference data
                stock_asset_type = await get_or_create_asset_type(session, "STK", "Common Stock")
                bond_asset_type = await get_or_create_asset_type(session, "BND", "Bond")
                etf_asset_type = await get_or_create_asset_type(session, "ETF", "Exchange Traded Fund")
                
                nyse_exchange = await get_or_create_exchange(session, "NYSE", "New York Stock Exchange", "USA")
                nasdaq_exchange = await get_or_create_exchange(session, "NASDAQ", "NASDAQ Stock Market", "USA")
                tsx_exchange = await get_or_create_exchange(session, "TSX", "Toronto Stock Exchange", "CAN")
                
                # Create sectors
                tech_sector = await get_or_create_sector(session, "Technology", "45")
                financial_sector = await get_or_create_sector(session, "Financials", "40")
                healthcare_sector = await get_or_create_sector(session, "Health Care", "35")
                consumer_discretionary_sector = await get_or_create_sector(session, "Consumer Discretionary", "25")
                consumer_staples_sector = await get_or_create_sector(session, "Consumer Staples", "30")
                industrials_sector = await get_or_create_sector(session, "Industrials", "20")
                energy_sector = await get_or_create_sector(session, "Energy", "10")
                materials_sector = await get_or_create_sector(session, "Materials", "15")
                utilities_sector = await get_or_create_sector(session, "Utilities", "55")
                real_estate_sector = await get_or_create_sector(session, "Real Estate", "60")
                communication_sector = await get_or_create_sector(session, "Communication Services", "50")
                
                # Sector mapping
                sector_map = {
                    'Technology': tech_sector.gics_code,
                    'Financials': financial_sector.gics_code,
                    'Health Care': healthcare_sector.gics_code,
                    'Consumer Discretionary': consumer_discretionary_sector.gics_code,
                    'Consumer Staples': consumer_staples_sector.gics_code,
                    'Industrials': industrials_sector.gics_code,
                    'Energy': energy_sector.gics_code,
                    'Materials': materials_sector.gics_code,
                    'Utilities': utilities_sector.gics_code,
                    'Real Estate': real_estate_sector.gics_code,
                    'Communication Services': communication_sector.gics_code,
                }
                
                # Fetch ticker lists
                all_tickers = []
                
                # Only fetch S&P 500 for now (can be expanded)
                try:
                    logger.info("Fetching S&P 500 tickers...")
                    sp500_tickers = fetch_sp500_tickers()
                    # Limit to first max_tickers
                    sp500_tickers = sp500_tickers[:max_tickers]
                    all_tickers.extend(sp500_tickers)
                    logger.info(f"Fetched {len(sp500_tickers)} S&P 500 tickers (limited)")
                except Exception as e:
                    logger.error(f"Failed to fetch S&P 500 tickers: {e}")
                    sp500_tickers = []
                
                # Process tickers with Alpha Vantage only
                created_count = 0
                failed_count = 0
                
                logger.info(f"Processing {len(all_tickers)} tickers with Alpha Vantage...")
                
                for i, info in enumerate(all_tickers):
                    if shutdown_requested:
                        logger.warning("Shutdown requested during processing. Stopping gracefully.")
                        break
                    
                    try:
                        ticker = info['ticker']
                        name = info['name']
                        
                        logger.info(f"Processing ticker {i+1}/{len(all_tickers)}: {ticker}")
                        
                        # Add delay between requests to respect Alpha Vantage rate limits
                        if i > 0:
                            time.sleep(2.0)  # 2 second delay between requests
                        
                        # Fetch data using Alpha Vantage only
                        data = fetch_security_data_alpha_vantage_only(ticker)
                        
                        if data:
                            # Determine exchange and asset type
                            if any(x in info['index'] for x in ['NASDAQ', 'Tech']):
                                exchange_code = nasdaq_exchange.code
                            elif any(x in info['index'] for x in ['TSX']):
                                exchange_code = tsx_exchange.code
                            else:
                                exchange_code = nyse_exchange.code
                            
                            # Get sector GICS code
                            sector_gics_code = sector_map.get(info.get('sector'), tech_sector.gics_code)
                            
                            # Determine asset type
                            if info['index'] == 'Bonds':
                                asset_type_code = bond_asset_type.code
                            elif info['index'] == 'ETFs':
                                asset_type_code = etf_asset_type.code
                            else:
                                asset_type_code = stock_asset_type.code
                            
                            # Create security record
                            from domains.securities.models import Security
                            
                            # Check if security already exists
                            from sqlalchemy import select
                            result = await session.execute(
                                select(Security).where(Security.ticker == ticker.upper())
                            )
                            existing_security = result.scalar_one_or_none()
                            
                            if not existing_security:
                                # Convert market cap to cents
                                market_cap_cents = None
                                if data.get('market_cap'):
                                    market_cap_cents = int(data['market_cap'] * 100)
                                
                                # Create new security
                                security = Security(
                                    ticker=ticker.upper(),
                                    name=name,
                                    asset_type_code=asset_type_code,
                                    sector_gics_code=sector_gics_code,
                                    exchange_code=exchange_code,
                                    currency=data.get('currency', 'USD'),
                                    market_cap=market_cap_cents,
                                    shares_outstanding=data.get('shares_outstanding'),
                                    isin=None,
                                    cusip=None,
                                    figi=None,
                                    business_summary=data.get('business_summary'),
                                    industry=data.get('industry'),
                                    website=data.get('website'),
                                    employees=data.get('employees'),
                                    is_active=True
                                )
                                session.add(security)
                                created_count += 1
                                logger.info(f"✅ Created security: {ticker}")
                            else:
                                logger.info(f"⏭️ Security already exists: {ticker}")
                                
                        else:
                            logger.warning(f"⚠️ No data for {ticker}")
                            failed_count += 1
                        
                        # Progress update
                        if (i + 1) % 10 == 0:
                            logger.info(f"Progress: {i+1}/{len(all_tickers)} completed")
                        
                    except Exception as e:
                        logger.error(f"Failed to process {info.get('ticker', 'unknown')}: {e}")
                        failed_count += 1
                
                # Commit changes
                await session.commit()
                logger.info("✅ Alpha Vantage securities data committed successfully")
                
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
    print("🌱 ALPHA VANTAGE SECURITIES DATABASE SEEDING SUMMARY")
    print("="*60)
    
    if results.get("success"):
        print("✅ Alpha Vantage seeding completed successfully!")
        
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
        print("❌ Alpha Vantage seeding failed!")
        error = results.get("error", "Unknown error")
        print(f"Error: {error}")
    
    print("="*60)


async def main():
    """Main function with Alpha Vantage error handling."""
    global shutdown_requested
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Alpha Vantage securities database seeding")
        parser.add_argument("--max-tickers", type=int, default=100,
                          help="Maximum number of tickers to process (default: 100)")
        
        args = parser.parse_args()
        
        # Check for shutdown request
        if shutdown_requested:
            logger.warning("Shutdown requested before starting. Exiting.")
            return
        
        # Run the Alpha Vantage seeding
        results = await seed_securities_alpha_vantage_only(max_tickers=args.max_tickers)
        
        # Print results
        print_results_summary(results)
        
        # Exit with appropriate code
        if results.get("success"):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("🛑 Alpha Vantage seeding interrupted by user. Exiting gracefully.")
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