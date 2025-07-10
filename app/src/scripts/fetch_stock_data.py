#!/usr/bin/env python3
"""
Enhanced stock data fetching script for CapitolScope.

This script fetches historical stock data from multiple sources with support for
major market indices, individual tickers, and comprehensive data collection.

Usage:
    python scripts/fetch_stock_data.py --ticker AAPL  # Single ticker
    python scripts/fetch_stock_data.py --all-major    # All major indices
    python scripts/fetch_stock_data.py --tickers AAPL,GOOGL,MSFT  # Multiple tickers
    python scripts/fetch_stock_data.py --file tickers.txt  # From file
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List

from core.logging import get_logger
from domains.securities.data_fetcher import (
    EnhancedStockDataService, 
    StockDataRequest,
    TickerListFetcher
)

logger = get_logger(__name__)


def parse_ticker_file(file_path: str) -> List[str]:
    """Parse ticker symbols from a text file."""
    try:
        with open(file_path, 'r') as f:
            tickers = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip comments
                    # Support comma-separated or one per line
                    if ',' in line:
                        tickers.extend([t.strip().upper() for t in line.split(',')])
                    else:
                        tickers.append(line.upper())
            return list(set(tickers))  # Remove duplicates
    except Exception as e:
        logger.error(f"Failed to parse ticker file {file_path}: {e}")
        return []


async def fetch_single_ticker(service: EnhancedStockDataService, 
                            ticker: str, 
                            interval: str = "1d",
                            start_date: str = "2014-01-01",
                            end_date: str = None,
                            source: str = "yfinance") -> Dict[str, Any]:
    """Fetch data for a single ticker."""
    logger.info(f"📊 Fetching data for {ticker}...")
    
    request = StockDataRequest(
        symbol=ticker,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        source=source
    )
    
    response = service.fetch_single_stock(request)
    
    if response.success:
        logger.info(f"✅ Successfully fetched {len(response.data)} records for {ticker}")
        return {
            "ticker": ticker,
            "records": len(response.data),
            "start_date": response.data.index.min().strftime("%Y-%m-%d") if not response.data.empty else None,
            "end_date": response.data.index.max().strftime("%Y-%m-%d") if not response.data.empty else None,
            "status": "success"
        }
    else:
        logger.error(f"❌ Failed to fetch data for {ticker}: {response.error}")
        return {
            "ticker": ticker,
            "records": 0,
            "status": "failed",
            "error": response.error
        }


async def fetch_multiple_tickers(service: EnhancedStockDataService,
                               tickers: List[str],
                               interval: str = "1d",
                               start_date: str = "2014-01-01", 
                               end_date: str = None,
                               source: str = "yfinance",
                               use_async: bool = True,
                               batch_size: int = 10) -> Dict[str, Any]:
    """Fetch data for multiple tickers."""
    logger.info(f"📈 Fetching data for {len(tickers)} tickers...")
    
    # Create requests
    requests = []
    for ticker in tickers:
        request = StockDataRequest(
            symbol=ticker,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            source=source
        )
        requests.append(request)
    
    # Fetch data
    if use_async:
        logger.info(f"Using async fetching with batch size {batch_size}")
        responses = await service.fetch_multiple_stocks_async(requests, batch_size)
    else:
        logger.info("Using synchronous fetching")
        responses = service.fetch_multiple_stocks(requests)
    
    # Analyze results
    successful = [r for r in responses if r.success]
    failed = [r for r in responses if not r.success]
    
    total_records = sum(len(r.data) for r in successful)
    
    results = {
        "total_tickers": len(tickers),
        "successful_tickers": len(successful),
        "failed_tickers": len(failed),
        "total_records": total_records,
        "success_rate": len(successful) / len(tickers) * 100 if tickers else 0,
        "successful_symbols": [r.symbol for r in successful],
        "failed_symbols": [(r.symbol, r.error) for r in failed]
    }
    
    logger.info(f"✅ Completed: {len(successful)}/{len(tickers)} successful ({results['success_rate']:.1f}%)")
    logger.info(f"📊 Total records: {total_records:,}")
    
    return results


async def fetch_all_major_indices(service: EnhancedStockDataService,
                                interval: str = "1d",
                                start_date: str = "2014-01-01",
                                end_date: str = None,
                                source: str = "yfinance",
                                use_async: bool = True,
                                batch_size: int = 10) -> Dict[str, Any]:
    """Fetch data for all major market indices."""
    logger.info("🚀 Fetching data for all major market indices...")
    
    request_template = StockDataRequest(
        symbol="",  # Will be replaced for each ticker
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        source=source
    )
    
    if use_async:
        responses = await service.fetch_all_major_stocks_async(request_template, batch_size)
    else:
        responses = service.fetch_all_major_stocks(request_template)
    
    # Analyze results
    successful = [r for r in responses if r.success]
    failed = [r for r in responses if not r.success]
    
    total_records = sum(len(r.data) for r in successful)
    
    results = {
        "total_tickers": len(responses),
        "successful_tickers": len(successful),
        "failed_tickers": len(failed),
        "total_records": total_records,
        "success_rate": len(successful) / len(responses) * 100 if responses else 0,
        "failed_symbols": [(r.symbol, r.error) for r in failed]
    }
    
    logger.info(f"✅ Completed major indices: {len(successful)}/{len(responses)} successful ({results['success_rate']:.1f}%)")
    logger.info(f"📊 Total records: {total_records:,}")
    
    return results


def print_results_summary(results: Dict[str, Any], mode: str):
    """Print a formatted summary of the fetch results."""
    print("\n" + "="*60)
    print(f"📊 STOCK DATA FETCH SUMMARY ({mode.upper()})")
    print("="*60)
    
    print(f"📈 Total Tickers:         {results.get('total_tickers', 0):,}")
    print(f"✅ Successful:            {results.get('successful_tickers', 0):,}")
    print(f"❌ Failed:                {results.get('failed_tickers', 0):,}")
    print(f"📊 Total Records:         {results.get('total_records', 0):,}")
    print(f"🎯 Success Rate:          {results.get('success_rate', 0):.1f}%")
    
    # Show failed symbols if any
    failed_symbols = results.get('failed_symbols', [])
    if failed_symbols and len(failed_symbols) <= 10:
        print(f"\n❌ Failed Symbols:")
        for symbol, error in failed_symbols:
            print(f"   • {symbol}: {error}")
    elif len(failed_symbols) > 10:
        print(f"\n❌ Failed Symbols: {len(failed_symbols)} total (showing first 5)")
        for symbol, error in failed_symbols[:5]:
            print(f"   • {symbol}: {error}")
    
    print("="*60)


async def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Fetch stock data using enhanced CapitolScope data service'
    )
    
    # Ticker selection options
    ticker_group = parser.add_mutually_exclusive_group(required=True)
    ticker_group.add_argument(
        '--ticker',
        type=str,
        help='Single ticker symbol to fetch (e.g., AAPL)'
    )
    ticker_group.add_argument(
        '--tickers',
        type=str,
        help='Comma-separated list of ticker symbols (e.g., AAPL,GOOGL,MSFT)'
    )
    ticker_group.add_argument(
        '--file',
        type=str,
        help='File containing ticker symbols (one per line or comma-separated)'
    )
    ticker_group.add_argument(
        '--all-major',
        action='store_true',
        help='Fetch all major market indices (S&P 500, NASDAQ-100, Dow Jones)'
    )
    
    # Data options
    parser.add_argument(
        '--interval',
        type=str,
        default='1d',
        choices=['1d', '1wk', '1mo'],
        help='Data interval (default: 1d)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default='2014-01-01',
        help='Start date in YYYY-MM-DD format (default: 2014-01-01)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date in YYYY-MM-DD format (default: today)'
    )
    parser.add_argument(
        '--source',
        type=str,
        default='yfinance',
        choices=['yfinance', 'alpha_vantage'],
        help='Data source (default: yfinance)'
    )
    
    # Performance options
    parser.add_argument(
        '--no-async',
        action='store_true',
        help='Use synchronous fetching instead of async'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for async operations (default: 10)'
    )
    parser.add_argument(
        '--alpha-vantage-key',
        type=str,
        help='Alpha Vantage API key (if using alpha_vantage source)'
    )
    
    # Output options
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
        # Initialize service
        service = EnhancedStockDataService(
            alpha_vantage_api_key=args.alpha_vantage_key
        )
        
        # Show what we're about to do
        print("📈 CapitolScope Enhanced Stock Data Fetcher")
        print("-" * 50)
        
        if args.ticker:
            print(f"🎯 Target: Single ticker ({args.ticker})")
            mode = "Single Ticker"
        elif args.tickers:
            tickers = [t.strip().upper() for t in args.tickers.split(',')]
            print(f"🎯 Target: {len(tickers)} tickers")
            mode = "Multiple Tickers"
        elif args.file:
            tickers = parse_ticker_file(args.file)
            print(f"🎯 Target: {len(tickers)} tickers from file")
            mode = "File Input"
        elif args.all_major:
            print(f"🎯 Target: All major market indices")
            mode = "Major Indices"
        
        print(f"📊 Interval: {args.interval}")
        print(f"📅 Date Range: {args.start_date} to {args.end_date or 'today'}")
        print(f"🔌 Source: {args.source}")
        print(f"⚡ Mode: {'Async' if not args.no_async else 'Sync'}")
        if not args.no_async:
            print(f"📦 Batch Size: {args.batch_size}")
        print()
        
        # Execute based on mode
        if args.ticker:
            result = await fetch_single_ticker(
                service=service,
                ticker=args.ticker.upper(),
                interval=args.interval,
                start_date=args.start_date,
                end_date=args.end_date,
                source=args.source
            )
            # Convert single result to summary format
            results = {
                "total_tickers": 1,
                "successful_tickers": 1 if result["status"] == "success" else 0,
                "failed_tickers": 1 if result["status"] == "failed" else 0,
                "total_records": result.get("records", 0),
                "success_rate": 100.0 if result["status"] == "success" else 0.0,
                "failed_symbols": [(result["ticker"], result.get("error", ""))] if result["status"] == "failed" else []
            }
            
        elif args.tickers or args.file:
            if args.tickers:
                tickers = [t.strip().upper() for t in args.tickers.split(',')]
            else:
                tickers = parse_ticker_file(args.file)
            
            results = await fetch_multiple_tickers(
                service=service,
                tickers=tickers,
                interval=args.interval,
                start_date=args.start_date,
                end_date=args.end_date,
                source=args.source,
                use_async=not args.no_async,
                batch_size=args.batch_size
            )
            
        elif args.all_major:
            results = await fetch_all_major_indices(
                service=service,
                interval=args.interval,
                start_date=args.start_date,
                end_date=args.end_date,
                source=args.source,
                use_async=not args.no_async,
                batch_size=args.batch_size
            )
        
        # Print summary
        print_results_summary(results, mode)
        
        # Next steps
        print("\n🎯 NEXT STEPS:")
        print("1. Store data in securities database:")
        print("   python scripts/seed_securities_database.py --prices")
        print("2. Import congressional trading data:")
        print("   python scripts/import_congressional_data.py")
        print("3. Start analysis notebooks or API server")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Fetch interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Fetch failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 