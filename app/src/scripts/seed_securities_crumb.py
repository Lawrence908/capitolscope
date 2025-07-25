#!/usr/bin/env python3
"""
Securities database seeding script using Yahoo Finance crumb/cookie authentication.

This script populates the securities database with stock data from major market indices
using manual crumb/cookie authentication to bypass Yahoo Finance rate limiting.

Usage:
    python app/src/scripts/seed_securities_crumb.py
    python app/src/scripts/seed_securities_crumb.py --max-tickers 100
    python app/src/scripts/seed_securities_crumb.py --save-results
"""

import asyncio
import sys
import os
import signal
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Add the app/src directory to Python path so we can import modules
script_dir = Path(__file__).parent
app_src_dir = script_dir.parent
project_root = app_src_dir.parent

# Add app/src to Python path
sys.path.insert(0, str(app_src_dir))

import argparse
import requests
import logging
from core.database import db_manager, init_database
from domains.securities.models import Security, AssetType, Exchange, Sector
from domains.securities.ingestion import (
    fetch_sp500_tickers, fetch_nasdaq100_tickers, fetch_dow_jones_tickers,
    fetch_tsx_tickers, fetch_bond_securities, fetch_etf_securities
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    global shutdown_requested
    logger.warning(f"Received signal {signum}. Starting graceful shutdown...")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Paste your crumb and cookie string here
crumb = "2nB76X9CaeX"
cookie_string = """GUC=AQEACAJocJ9onEIc_ARA&s=AQAAABXFrXOF&g=aG9cBA; A1=d=AQABBMhVaGgCEEN8VmdbQsv6vZfgLtK8HA8FEgEACAKfcGicaCXUxyMA_eMDAAcIyFVoaNK8HA8ID7OJc9wpGN9vjIl-HOGE1gkBBwoBjQ&S=AQAAAqqZSZELX-ytGf09ZZF2cLI; A3=d=AQABBMhVaGgCEEN8VmdbQsv6vZfgLtK8HA8FEgEACAKfcGicaCXUxyMA_eMDAAcIyFVoaNK8HA8ID7OJc9wpGN9vjIl-HOGE1gkBBwoBjQ&S=AQAAAqqZSZELX-ytGf09ZZF2cLI; A1S=d=AQABBMhVaGgCEEN8VmdbQsv6vZfgLtK8HA8FEgEACAKfcGicaCXUxyMA_eMDAAcIyFVoaNK8HA8ID7OJc9wpGN9vjIl-HOGE1gkBBwoBjQ&S=AQAAAqqZSZELX-ytGf09ZZF2cLI; axids=gam=y-N2oHymhG2uLfmGQ7GEFGMsDJ9JDwfLjTIT.0mJ0vOJQr40f48g---A&dv360=eS1iQUNkdV9sRTJ1SEVUelJzbEZoRjFRN0hfTEJkczVRdDR3WTAzNktaRUY2Ry56T0Q4T0FIMFNvbThFN1o4TVpTQlZmTH5B&ydsp=y-w2K9qlNE2uIl_6k33oqA3YSpJW7fiDQLqhcefxJnVTczjjRAf.dr.sHbPeeufQAHgD0n~A"""

                    
# Convert cookie string to dict
cookies = dict(item.split('=', 1) for item in cookie_string.split('; '))


def fetch_yahoo_finance_with_crumb(symbol: str) -> Dict[str, Any]:
    """
    Fetch Yahoo Finance data using crumb/cookie authentication.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Dict containing Yahoo Finance data or error information
    """
    url = (
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        "?modules=financialData,quoteType,defaultKeyStatistics,assetProfile,summaryDetail"
        f"&crumb={crumb}"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        logger.debug(f"Fetching Yahoo Finance data for {symbol}")
        response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"Successfully fetched data for {symbol}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON for {symbol}: {e}")
                return {"error": "JSON parse error", "status_code": response.status_code}
        else:
            # Enhanced logging for 401/Invalid Crumb
            logger.warning(f"HTTP {response.status_code} for {symbol}: {response.text[:200]}")
            if response.status_code == 401 or ("Invalid Crumb" in response.text):
                logger.error(f"Full 401/Invalid Crumb response for {symbol}:\n"
                             f"URL: {url}\n"
                             f"Request Headers: {headers}\n"
                             f"Request Cookies: {cookies}\n"
                             f"Response Headers: {dict(response.headers)}\n"
                             f"Response Body: {response.text}")
            return {"error": f"HTTP {response.status_code}", "status_code": response.status_code, "response_text": response.text}
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching data for {symbol}")
        return {"error": "Timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {symbol}: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error fetching {symbol}: {e}")
        return {"error": str(e)}


def get_or_create_asset_type_sync(session: Session, code: str, name: str) -> AssetType:
    """Get or create an asset type (synchronous version)."""
    # Check if exists
    result = session.execute(
        select(AssetType).where(AssetType.code == code)
    )
    asset_type = result.scalar_one_or_none()
    
    if not asset_type:
        asset_type = AssetType(code=code, name=name)
        session.add(asset_type)
        session.flush()
        logger.info(f"Created asset type: {code} - {name}")
    
    return asset_type


def get_or_create_exchange_sync(session: Session, code: str, name: str, country: str = "USA") -> Exchange:
    """Get or create an exchange (synchronous version)."""
    # Check if exists
    result = session.execute(
        select(Exchange).where(Exchange.code == code)
    )
    exchange = result.scalar_one_or_none()
    
    if not exchange:
        exchange = Exchange(
            code=code, 
            name=name, 
            country=country,
            timezone="America/New_York"
        )
        session.add(exchange)
        session.flush()
        logger.info(f"Created exchange: {code} - {name}")
    
    return exchange


def get_or_create_sector_sync(session: Session, name: str, gics_code: str = None) -> Sector:
    """Get or create a sector (synchronous version)."""
    # Check if exists
    result = session.execute(
        select(Sector).where(Sector.name == name)
    )
    sector = result.scalar_one_or_none()
    
    if not sector:
        sector = Sector(name=name, gics_code=gics_code)
        session.add(sector)
        session.flush()
        logger.info(f"Created sector: {name}")
    
    return sector


def get_or_create_security_sync(session: Session, ticker: str, name: str, 
                               asset_type_code: str, exchange_code: str, 
                               sector_gics_code: str = None, yahoo_data: Dict = None) -> Optional[Security]:
    """
    Get or create a security with Yahoo Finance data (synchronous version).
    
    Args:
        session: Database session
        ticker: Stock ticker symbol
        name: Company name
        asset_type_code: Asset type code
        exchange_code: Exchange code
        sector_gics_code: Sector GICS code
        yahoo_data: Yahoo Finance data dictionary
        
    Returns:
        Security object or None if failed
    """
    try:
        # Check if exists
        result = session.execute(
            select(Security).where(Security.ticker == ticker.upper())
        )
        security = result.scalar_one_or_none()
        
        if not security:
            # Extract data from Yahoo Finance response
            market_cap = None
            shares_outstanding = None
            beta = None
            pe_ratio = None
            dividend_yield = None
            currency = "USD"
            
            if yahoo_data and "quoteSummary" in yahoo_data:
                try:
                    # Extract financial data
                    financial_data = yahoo_data["quoteSummary"]["result"][0].get("financialData", {})
                    if financial_data:
                        market_cap = financial_data.get("marketCap")
                        shares_outstanding = financial_data.get("sharesOutstanding")
                        beta = financial_data.get("beta")
                        pe_ratio = financial_data.get("trailingPE")
                        dividend_yield = financial_data.get("dividendYield")
                    
                    # Extract summary detail
                    summary_detail = yahoo_data["quoteSummary"]["result"][0].get("summaryDetail", {})
                    if summary_detail:
                        currency = summary_detail.get("currency", "USD")
                        
                except (KeyError, IndexError) as e:
                    logger.debug(f"Could not extract Yahoo data for {ticker}: {e}")
            
            # Convert market cap to cents if available
            market_cap_cents = None
            if market_cap:
                market_cap_cents = int(market_cap * 100)
            
            # Create new security
            security = Security(
                ticker=ticker.upper(),
                name=name,
                asset_type_code=asset_type_code,
                sector_gics_code=sector_gics_code,
                exchange_code=exchange_code,
                currency=currency,
                market_cap=market_cap_cents,
                shares_outstanding=shares_outstanding,
                beta=beta,
                pe_ratio=pe_ratio,
                dividend_yield=dividend_yield,
                is_active=True
            )
            
            session.add(security)
            session.flush()
            logger.info(f"✅ Created security: {ticker} - {name}")
            return security
            
        else:
            logger.debug(f"⏭️ Security already exists: {ticker}")
            return security
            
    except IntegrityError as e:
        logger.warning(f"Duplicate security {ticker} detected: {e}")
        # Try to get the existing security
        result = session.execute(
            select(Security).where(Security.ticker == ticker.upper())
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to create security {ticker}: {e}")
        return None


def get_all_tickers() -> List[Dict[str, str]]:
    """Get all tickers from various sources."""
    all_tickers = []
    
    try:
        logger.info("Fetching S&P 500 tickers...")
        sp500_tickers = fetch_sp500_tickers()
        all_tickers.extend(sp500_tickers)
        logger.info(f"Fetched {len(sp500_tickers)} S&P 500 tickers")
    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 tickers: {e}")
    
    try:
        logger.info("Fetching NASDAQ-100 tickers...")
        nasdaq_tickers = fetch_nasdaq100_tickers()
        all_tickers.extend(nasdaq_tickers)
        logger.info(f"Fetched {len(nasdaq_tickers)} NASDAQ-100 tickers")
    except Exception as e:
        logger.error(f"Failed to fetch NASDAQ-100 tickers: {e}")
    
    try:
        logger.info("Fetching Dow Jones tickers...")
        dow_tickers = fetch_dow_jones_tickers()
        all_tickers.extend(dow_tickers)
        logger.info(f"Fetched {len(dow_tickers)} Dow Jones tickers")
    except Exception as e:
        logger.error(f"Failed to fetch Dow Jones tickers: {e}")
    
    try:
        logger.info("Fetching TSX tickers...")
        tsx_tickers = fetch_tsx_tickers()
        all_tickers.extend(tsx_tickers)
        logger.info(f"Fetched {len(tsx_tickers)} TSX tickers")
    except Exception as e:
        logger.error(f"Failed to fetch TSX tickers: {e}")
    
    try:
        logger.info("Fetching bond securities...")
        bond_tickers = fetch_bond_securities()
        all_tickers.extend(bond_tickers)
        logger.info(f"Fetched {len(bond_tickers)} bond securities")
    except Exception as e:
        logger.error(f"Failed to fetch bond securities: {e}")
    
    try:
        logger.info("Fetching ETF securities...")
        etf_tickers = fetch_etf_securities()
        all_tickers.extend(etf_tickers)
        logger.info(f"Fetched {len(etf_tickers)} ETF securities")
    except Exception as e:
        logger.error(f"Failed to fetch ETF securities: {e}")
    
    return all_tickers


def seed_securities_with_crumb(max_tickers: int = None, save_results: bool = False) -> Dict[str, Any]:
    """
    Seed securities database using crumb/cookie authentication.
    
    Args:
        max_tickers: Maximum number of tickers to process (None for all)
        save_results: Whether to save Yahoo Finance data to files
        
    Returns:
        Dict with seeding statistics
    """
    logger.info("🌱 Starting securities database seeding with crumb/cookie authentication...")
    
    try:
        # Initialize database
        asyncio.run(init_database())
        
        # Get database session
        with db_manager.sync_session_scope() as session:
            try:
                # Create reference data
                logger.info("📊 Creating reference data (asset types, exchanges, sectors)...")
                stock_asset_type = get_or_create_asset_type_sync(session, "STK", "Common Stock")
                bond_asset_type = get_or_create_asset_type_sync(session, "BND", "Bond")
                etf_asset_type = get_or_create_asset_type_sync(session, "ETF", "Exchange Traded Fund")
                
                nyse_exchange = get_or_create_exchange_sync(session, "NYSE", "New York Stock Exchange", "USA")
                nasdaq_exchange = get_or_create_exchange_sync(session, "NASDAQ", "NASDAQ Stock Market", "USA")
                tsx_exchange = get_or_create_exchange_sync(session, "TSX", "Toronto Stock Exchange", "CAN")
                
                # Create sectors
                tech_sector = get_or_create_sector_sync(session, "Technology", "45")
                financial_sector = get_or_create_sector_sync(session, "Financials", "40")
                healthcare_sector = get_or_create_sector_sync(session, "Health Care", "35")
                consumer_discretionary_sector = get_or_create_sector_sync(session, "Consumer Discretionary", "25")
                consumer_staples_sector = get_or_create_sector_sync(session, "Consumer Staples", "30")
                industrials_sector = get_or_create_sector_sync(session, "Industrials", "20")
                energy_sector = get_or_create_sector_sync(session, "Energy", "10")
                materials_sector = get_or_create_sector_sync(session, "Materials", "15")
                utilities_sector = get_or_create_sector_sync(session, "Utilities", "55")
                real_estate_sector = get_or_create_sector_sync(session, "Real Estate", "60")
                communication_sector = get_or_create_sector_sync(session, "Communication Services", "50")
                
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
                
                # Get all tickers
                all_tickers = get_all_tickers()
                
                if max_tickers:
                    all_tickers = all_tickers[:max_tickers]
                    logger.info(f"Limited to {max_tickers} tickers")
                
                logger.info(f"📊 Processing {len(all_tickers)} total tickers...")
                
                # Process tickers
                created_count = 0
                failed_count = 0
                skipped_count = 0
                yahoo_data_results = {}
                
                for i, info in enumerate(all_tickers):
                    if shutdown_requested:
                        logger.warning("Shutdown requested during processing. Stopping gracefully.")
                        break
                    
                    try:
                        ticker = info['ticker']
                        name = info['name']
                        
                        logger.info(f"[{i+1}/{len(all_tickers)}] Processing {ticker} - {name}")
                        
                        # Fetch Yahoo Finance data using crumb/cookie
                        yahoo_data = fetch_yahoo_finance_with_crumb(ticker)
                        
                        if save_results:
                            yahoo_data_results[ticker] = yahoo_data
                        
                        # Determine exchange
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
                        
                        # Create or update security
                        security = get_or_create_security_sync(
                            session, ticker, name, asset_type_code, 
                            exchange_code, sector_gics_code, yahoo_data
                        )
                        
                        if security:
                            created_count += 1
                            if created_count % 10 == 0:
                                logger.info(f"Progress: {created_count} securities created...")
                        else:
                            failed_count += 1
                        
                        # Add delay to be respectful to Yahoo Finance
                        if i > 0 and i % 5 == 0:
                            logger.info(f"Rate limiting: pausing for 2 seconds after {i} tickers...")
                            time.sleep(2.0)
                        else:
                            time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Failed to process {info.get('ticker', 'unknown')}: {e}")
                        failed_count += 1
                
                # Commit all changes
                session.commit()
                logger.info("✅ Securities data committed successfully")
                
                # Save results if requested
                if save_results and yahoo_data_results:
                    timestamp = int(time.time())
                    filename = f"yahoo_finance_data_{timestamp}.json"
                    with open(filename, 'w') as f:
                        json.dump(yahoo_data_results, f, indent=2)
                    logger.info(f"💾 Saved Yahoo Finance data to {filename}")
                
                return {
                    "total_tickers": len(all_tickers),
                    "created": created_count,
                    "failed": failed_count,
                    "skipped": skipped_count,
                    "success": True
                }
                
            except IntegrityError as e:
                logger.error(f"❌ Database integrity error: {e}")
                session.rollback()
                return {
                    "error": "IntegrityError",
                    "success": False,
                    "error": str(e)
                }
            except Exception as e:
                logger.error(f"❌ Unexpected error during seeding: {e}")
                session.rollback()
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
    print("🌱 SECURITIES DATABASE SEEDING SUMMARY (CRUMB/COOKIE)")
    print("="*60)
    
    if results.get("success"):
        print("✅ Seeding completed successfully!")
        
        print(f"\n📊 Securities Processed:")
        print(f"   • Total Tickers: {results.get('total_tickers', 0):,}")
        print(f"   • Created: {results.get('created', 0):,}")
        print(f"   • Failed: {results.get('failed', 0):,}")
        print(f"   • Skipped: {results.get('skipped', 0):,}")
        
        if results.get('created', 0) > 0:
            success_rate = (results.get('created', 0) / results.get('total_tickers', 1)) * 100
            print(f"   • Success Rate: {success_rate:.1f}%")
            
    else:
        print("❌ Seeding failed!")
        error = results.get("error", "Unknown error")
        print(f"Error: {error}")
    
    print("="*60)


def main():
    """Main function with robust error handling."""
    global shutdown_requested
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Seed securities database with crumb/cookie authentication")
        parser.add_argument("--max-tickers", type=int, default=None,
                          help="Maximum number of tickers to process (default: all)")
        parser.add_argument("--save-results", action="store_true",
                          help="Save Yahoo Finance data to JSON files")
        
        args = parser.parse_args()
        
        # Check for shutdown request
        if shutdown_requested:
            logger.warning("Shutdown requested before starting. Exiting.")
            return
        
        # Run the seeding
        results = seed_securities_with_crumb(
            max_tickers=args.max_tickers,
            save_results=args.save_results
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
        main()
    except KeyboardInterrupt:
        logger.warning("🛑 Script interrupted. Exiting.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unhandled exception: {e}")
        sys.exit(1)
