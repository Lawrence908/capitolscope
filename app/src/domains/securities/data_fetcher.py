"""
Enhanced stock data fetching service for the securities domain.

This module provides comprehensive stock data fetching capabilities with support for
multiple data sources, async operations, and robust error handling.
"""

import asyncio
import aiohttp
import requests
import time
import datetime
from typing import List, Dict, Optional, Tuple, Any
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

import logging
logger = logging.getLogger(__name__)
from core.config import get_settings

settings = get_settings()


@dataclass
class StockDataRequest:
    """Request configuration for stock data fetching."""
    symbol: str
    interval: str = "1d"  # 1d, 1wk, 1mo
    start_date: str = "2014-01-01"
    end_date: str = None
    source: str = "yfinance"  # yfinance, alpha_vantage
    
    def __post_init__(self):
        if self.end_date is None:
            self.end_date = str(datetime.date.today())


@dataclass
class StockDataResponse:
    """Response containing stock data."""
    symbol: str
    data: pd.DataFrame
    source: str
    fetch_time: datetime.datetime
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.error is None and not self.data.empty


class TickerListFetcher:
    """Service for fetching ticker lists from major indices."""
    
    @staticmethod
    def fetch_sp500_tickers() -> List[Dict[str, str]]:
        """Fetch S&P 500 ticker list from Wikipedia."""
        try:
            logger.info("Fetching S&P 500 tickers from Wikipedia...")
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'id': 'constituents'})
            
            tickers = []
            for row in table.find_all('tr')[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 3:
                    ticker = cells[0].text.strip().replace('.', '-')  # Yahoo Finance format
                    name = cells[1].text.strip()
                    sector = cells[3].text.strip() if len(cells) > 3 else "Unknown"
                    
                    tickers.append({
                        'ticker': ticker,
                        'name': name,
                        'sector': sector,
                        'index': 'S&P 500'
                    })
            
            logger.info(f"Fetched {len(tickers)} S&P 500 tickers")
            return tickers
            
        except Exception as e:
            logger.error(f"Error fetching S&P 500 tickers: {e}")
            return []
    
    @staticmethod
    def fetch_nasdaq100_tickers() -> List[Dict[str, str]]:
        """Fetch NASDAQ-100 ticker list from Wikipedia."""
        try:
            logger.info("Fetching NASDAQ-100 tickers...")
            url = "https://en.wikipedia.org/wiki/NASDAQ-100"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'id': 'constituents'})
            
            tickers = []
            for row in table.find_all('tr')[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 2:
                    ticker = cells[1].text.strip()
                    name = cells[0].text.strip()
                    
                    tickers.append({
                        'ticker': ticker,
                        'name': name,
                        'sector': 'Technology',  # Most NASDAQ-100 are tech
                        'index': 'NASDAQ-100'
                    })
            
            logger.info(f"Fetched {len(tickers)} NASDAQ-100 tickers")
            return tickers
            
        except Exception as e:
            logger.error(f"Error fetching NASDAQ-100 tickers: {e}")
            return []
    
    @staticmethod
    def fetch_dow_jones_tickers() -> List[Dict[str, str]]:
        """Fetch Dow Jones Industrial Average ticker list."""
        try:
            logger.info("Fetching Dow Jones tickers...")
            url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'wikitable'})
            
            tickers = []
            for row in table.find_all('tr')[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 3:
                    ticker = cells[2].text.strip()
                    name = cells[0].text.strip()
                    
                    tickers.append({
                        'ticker': ticker,
                        'name': name,
                        'sector': 'Industrial',
                        'index': 'Dow Jones'
                    })
            
            logger.info(f"Fetched {len(tickers)} Dow Jones tickers")
            return tickers
            
        except Exception as e:
            logger.error(f"Error fetching Dow Jones tickers: {e}")
            return []
    
    @classmethod
    def get_all_major_tickers(self, 
                             include_sp500: bool = True,
                             include_nasdaq: bool = True, 
                             include_dow: bool = True) -> List[Dict[str, str]]:
        """Get ticker lists from all major indices."""
        all_tickers = []
        
        if include_sp500:
            all_tickers.extend(self.fetch_sp500_tickers())
        if include_nasdaq:
            all_tickers.extend(self.fetch_nasdaq100_tickers())
        if include_dow:
            all_tickers.extend(self.fetch_dow_jones_tickers())
        
        # Remove duplicates while preserving order
        unique_tickers = {}
        for ticker_info in all_tickers:
            ticker = ticker_info['ticker']
            if ticker not in unique_tickers:
                unique_tickers[ticker] = ticker_info
        
        return list(unique_tickers.values())


class AlphaVantageDataFetcher:
    """Alpha Vantage API data fetcher."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        
    def fetch_time_series(self, symbol: str, interval: str = "daily", 
                         output_size: str = "compact") -> StockDataResponse:
        """Fetch time-series data from Alpha Vantage API."""
        function_map = {
            "daily": "TIME_SERIES_DAILY",
            "weekly": "TIME_SERIES_WEEKLY",
            "monthly": "TIME_SERIES_MONTHLY"
        }
        
        if interval not in function_map:
            return StockDataResponse(
                symbol=symbol,
                data=pd.DataFrame(),
                source="alpha_vantage",
                fetch_time=datetime.datetime.now(),
                error=f"Invalid interval: {interval}"
            )
        
        params = {
            "function": function_map[interval],
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": output_size
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "Error Message" in data:
                return StockDataResponse(
                    symbol=symbol,
                    data=pd.DataFrame(),
                    source="alpha_vantage",
                    fetch_time=datetime.datetime.now(),
                    error=data["Error Message"]
                )
            
            time_series_key = f"Time Series ({interval.capitalize()})"
            if time_series_key not in data:
                return StockDataResponse(
                    symbol=symbol,
                    data=pd.DataFrame(),
                    source="alpha_vantage",
                    fetch_time=datetime.datetime.now(),
                    error="Unexpected response structure"
                )
            
            time_series_data = data[time_series_key]
            
            records = []
            for date_str, values in time_series_data.items():
                record = {
                    "date": pd.to_datetime(date_str),
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": float(values["5. volume"]),
                    "symbol": symbol
                }
                records.append(record)
            
            df = pd.DataFrame(records)
            df.sort_values('date', inplace=True)
            df.set_index('date', inplace=True)
            
            return StockDataResponse(
                symbol=symbol,
                data=df,
                source="alpha_vantage",
                fetch_time=datetime.datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage API error for {symbol}: {e}")
            return StockDataResponse(
                symbol=symbol,
                data=pd.DataFrame(),
                source="alpha_vantage",
                fetch_time=datetime.datetime.now(),
                error=str(e)
            )


class YFinanceDataFetcher:
    """Yahoo Finance data fetcher with rate limiting."""
    
    def __init__(self, rate_limit_delay: float = 0.1):
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0.0
        
    def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def fetch_stock_data(self, request: StockDataRequest) -> StockDataResponse:
        """Fetch stock data using Yahoo Finance."""
        try:
            self._apply_rate_limit()
            
            ticker_obj = yf.Ticker(request.symbol)
            hist = ticker_obj.history(
                interval=request.interval,
                start=request.start_date,
                end=request.end_date,
                progress=False
            )
            
            if hist.empty:
                return StockDataResponse(
                    symbol=request.symbol,
                    data=pd.DataFrame(),
                    source="yfinance",
                    fetch_time=datetime.datetime.now(),
                    error="No data available"
                )
            
            # Add symbol column
            hist['symbol'] = request.symbol
            
            # Standardize column names
            hist.columns = hist.columns.str.lower()
            
            return StockDataResponse(
                symbol=request.symbol,
                data=hist,
                source="yfinance",
                fetch_time=datetime.datetime.now()
            )
            
        except Exception as e:
            logger.error(f"YFinance error for {request.symbol}: {e}")
            return StockDataResponse(
                symbol=request.symbol,
                data=pd.DataFrame(),
                source="yfinance",
                fetch_time=datetime.datetime.now(),
                error=str(e)
            )
    
    async def fetch_stock_data_async(self, session: aiohttp.ClientSession, 
                                   request: StockDataRequest) -> StockDataResponse:
        """Fetch stock data asynchronously."""
        try:
            start_timestamp = int(datetime.datetime.strptime(request.start_date, "%Y-%m-%d").timestamp())
            end_timestamp = int(datetime.datetime.strptime(request.end_date, "%Y-%m-%d").timestamp())
            
            url = (f"https://query1.finance.yahoo.com/v7/finance/download/{request.symbol}"
                  f"?period1={start_timestamp}&period2={end_timestamp}"
                  f"&interval={request.interval}&events=history")
            
            async with session.get(url) as response:
                if response.status != 200:
                    return StockDataResponse(
                        symbol=request.symbol,
                        data=pd.DataFrame(),
                        source="yfinance_async",
                        fetch_time=datetime.datetime.now(),
                        error=f"HTTP {response.status}"
                    )
                
                data = await response.text()
                
                import io
                df = pd.read_csv(io.StringIO(data))
                
                if df.empty:
                    return StockDataResponse(
                        symbol=request.symbol,
                        data=pd.DataFrame(),
                        source="yfinance_async",
                        fetch_time=datetime.datetime.now(),
                        error="No data in response"
                    )
                
                # Set date as index and add symbol
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                df['symbol'] = request.symbol
                df.columns = df.columns.str.lower()
                
                return StockDataResponse(
                    symbol=request.symbol,
                    data=df,
                    source="yfinance_async",
                    fetch_time=datetime.datetime.now()
                )
                
        except Exception as e:
            logger.error(f"YFinance async error for {request.symbol}: {e}")
            return StockDataResponse(
                symbol=request.symbol,
                data=pd.DataFrame(),
                source="yfinance_async",
                fetch_time=datetime.datetime.now(),
                error=str(e)
            )


class EnhancedStockDataService:
    """Comprehensive stock data fetching service."""
    
    def __init__(self, alpha_vantage_api_key: Optional[str] = None):
        self.yfinance_fetcher = YFinanceDataFetcher()
        self.alpha_vantage_fetcher = None
        if alpha_vantage_api_key:
            self.alpha_vantage_fetcher = AlphaVantageDataFetcher(alpha_vantage_api_key)
        self.ticker_fetcher = TickerListFetcher()
        
    def fetch_single_stock(self, request: StockDataRequest) -> StockDataResponse:
        """Fetch data for a single stock."""
        if request.source == "alpha_vantage" and self.alpha_vantage_fetcher:
            # Map interval for Alpha Vantage
            av_interval = "daily"
            if "1w" in request.interval:
                av_interval = "weekly"
            elif "1mo" in request.interval:
                av_interval = "monthly"
            
            return self.alpha_vantage_fetcher.fetch_time_series(
                request.symbol, av_interval
            )
        else:
            # Default to YFinance
            return self.yfinance_fetcher.fetch_stock_data(request)
    
    def fetch_multiple_stocks(self, requests: List[StockDataRequest]) -> List[StockDataResponse]:
        """Fetch data for multiple stocks synchronously."""
        results = []
        total = len(requests)
        
        for i, request in enumerate(requests):
            logger.info(f"Fetching {request.symbol} ({i+1}/{total})...")
            result = self.fetch_single_stock(request)
            results.append(result)
            
            # Log progress
            if (i + 1) % 10 == 0:
                success_count = sum(1 for r in results if r.success)
                logger.info(f"Progress: {i+1}/{total} completed, {success_count} successful")
        
        return results
    
    async def fetch_multiple_stocks_async(self, requests: List[StockDataRequest], 
                                        batch_size: int = 10) -> List[StockDataResponse]:
        """Fetch data for multiple stocks asynchronously."""
        results = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} stocks")
            
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self.yfinance_fetcher.fetch_stock_data_async(session, req)
                    for req in batch
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle exceptions
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        results.append(StockDataResponse(
                            symbol=batch[j].symbol,
                            data=pd.DataFrame(),
                            source="yfinance_async",
                            fetch_time=datetime.datetime.now(),
                            error=str(result)
                        ))
                    else:
                        results.append(result)
            
            # Add delay between batches
            if i + batch_size < len(requests):
                await asyncio.sleep(1.0)
        
        return results
    
    def fetch_all_major_stocks(self, request_template: StockDataRequest) -> List[StockDataResponse]:
        """Fetch data for all major market stocks."""
        # Get all major tickers
        tickers = self.ticker_fetcher.get_all_major_tickers()
        
        # Create requests for each ticker
        requests = []
        for ticker_info in tickers:
            request = StockDataRequest(
                symbol=ticker_info['ticker'],
                interval=request_template.interval,
                start_date=request_template.start_date,
                end_date=request_template.end_date,
                source=request_template.source
            )
            requests.append(request)
        
        logger.info(f"Fetching data for {len(requests)} major market stocks...")
        return self.fetch_multiple_stocks(requests)
    
    async def fetch_all_major_stocks_async(self, request_template: StockDataRequest, 
                                         batch_size: int = 10) -> List[StockDataResponse]:
        """Fetch data for all major market stocks asynchronously."""
        # Get all major tickers
        tickers = self.ticker_fetcher.get_all_major_tickers()
        
        # Create requests for each ticker
        requests = []
        for ticker_info in tickers:
            request = StockDataRequest(
                symbol=ticker_info['ticker'],
                interval=request_template.interval,
                start_date=request_template.start_date,
                end_date=request_template.end_date,
                source=request_template.source
            )
            requests.append(request)
        
        logger.info(f"Fetching data for {len(requests)} major market stocks asynchronously...")
        return await self.fetch_multiple_stocks_async(requests, batch_size)
    
    def get_ticker_company_mapping(self) -> Dict[str, str]:
        """Get mapping of ticker symbols to company names."""
        tickers = self.ticker_fetcher.get_all_major_tickers()
        return {ticker_info['ticker']: ticker_info['name'] for ticker_info in tickers}
    
    def get_available_tickers(self) -> List[str]:
        """Get list of all available ticker symbols."""
        tickers = self.ticker_fetcher.get_all_major_tickers()
        return [ticker_info['ticker'] for ticker_info in tickers]


# Convenience functions for backward compatibility
def fetch_time_series_yf(symbol: str, interval: str = "1d", 
                        start: str = "2014-01-01", 
                        end: str = None) -> pd.DataFrame:
    """Backward compatibility function for YFinance data fetching."""
    service = EnhancedStockDataService()
    request = StockDataRequest(
        symbol=symbol,
        interval=interval,
        start_date=start,
        end_date=end or str(datetime.date.today())
    )
    response = service.fetch_single_stock(request)
    return response.data


def fetch_all_stock_data_yf(interval: str = "1d", 
                           start: str = "2014-01-01", 
                           end: str = None) -> pd.DataFrame:
    """Backward compatibility function for fetching all major market data."""
    service = EnhancedStockDataService()
    request_template = StockDataRequest(
        symbol="",  # Will be replaced for each ticker
        interval=interval,
        start_date=start,
        end_date=end or str(datetime.date.today())
    )
    
    responses = service.fetch_all_major_stocks(request_template)
    successful_responses = [r for r in responses if r.success]
    
    if not successful_responses:
        return pd.DataFrame()
    
    # Combine all dataframes
    all_data = []
    for response in successful_responses:
        all_data.append(response.data)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


async def fetch_all_stock_data_yf_async(interval: str = "1d", 
                                       start: str = "2014-01-01", 
                                       end: str = None,
                                       batch_size: int = 10) -> pd.DataFrame:
    """Backward compatibility function for async fetching all major market data."""
    service = EnhancedStockDataService()
    request_template = StockDataRequest(
        symbol="",  # Will be replaced for each ticker
        interval=interval,
        start_date=start,
        end_date=end or str(datetime.date.today())
    )
    
    responses = await service.fetch_all_major_stocks_async(request_template, batch_size)
    successful_responses = [r for r in responses if r.success]
    
    if not successful_responses:
        return pd.DataFrame()
    
    # Combine all dataframes
    all_data = []
    for response in successful_responses:
        all_data.append(response.data)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame() 