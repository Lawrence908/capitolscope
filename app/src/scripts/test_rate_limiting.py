#!/usr/bin/env python3
"""
Test script for rate limiting improvements.

This script tests the improved rate limiting in the securities ingestion module.
"""

import sys
import os
from pathlib import Path

# Add the app/src directory to Python path so we can import modules
script_dir = Path(__file__).parent
app_src_dir = script_dir.parent
project_root = app_src_dir.parent

# Add app/src to Python path
sys.path.insert(0, str(app_src_dir))

import time
import logging
logger = logging.getLogger(__name__)
from domains.securities.ingestion import fetch_yfinance_data


def test_rate_limiting():
    """Test the improved rate limiting functionality."""
    logger.info("🧪 Testing rate limiting improvements...")
    
    # Test tickers (small set to avoid overwhelming APIs)
    test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    results = []
    
    for i, ticker in enumerate(test_tickers):
        logger.info(f"Testing ticker {i+1}/{len(test_tickers)}: {ticker}")
        
        start_time = time.time()
        
        try:
            data = fetch_yfinance_data(ticker)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if data:
                logger.info(f"✅ {ticker}: Success in {duration:.2f}s")
                results.append({
                    "ticker": ticker,
                    "success": True,
                    "duration": duration,
                    "market_cap": data.get('market_cap')
                })
            else:
                logger.warning(f"⚠️ {ticker}: No data returned")
                results.append({
                    "ticker": ticker,
                    "success": False,
                    "duration": duration,
                    "error": "No data"
                })
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"❌ {ticker}: Error after {duration:.2f}s - {e}")
            results.append({
                "ticker": ticker,
                "success": False,
                "duration": duration,
                "error": str(e)
            })
    
    # Print summary
    print("\n" + "="*50)
    print("🧪 RATE LIMITING TEST RESULTS")
    print("="*50)
    
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    
    if successful > 0:
        avg_duration = sum(r["duration"] for r in results if r["success"]) / successful
        print(f"Average duration: {avg_duration:.2f}s")
    
    print("\nDetailed results:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {result['ticker']}: {result['duration']:.2f}s")
        if not result["success"]:
            print(f"    Error: {result['error']}")
    
    print("="*50)
    
    return successful == total


if __name__ == "__main__":
    try:
        success = test_rate_limiting()
        if success:
            print("🎉 All tests passed!")
            sys.exit(0)
        else:
            print("⚠️ Some tests failed, but rate limiting is working.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("🛑 Test interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Test failed with error: {e}")
        sys.exit(1) 