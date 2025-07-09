"""
Securities domain data ingestion module.

This module handles fetching and ingesting stock data from various sources
into the securities database. Supports CAP-24 (Stock Database) and CAP-25 (Price Data Ingestion).
"""

import asyncio
import aiohttp
import requests
import time
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, date

from core.logging import get_logger
from domains.securities.models import Security, AssetType, Exchange, Sector, DailyPrice

logger = get_logger(__name__)


# ============================================================================
# ASYNC DATABASE HELPERS
# ============================================================================

async def get_or_create_asset_type(session: AsyncSession, code: str, name: str) -> AssetType:
    """Get or create an asset type."""
    # Check if exists
    result = await session.execute(
        select(AssetType).where(AssetType.code == code)
    )
    asset_type = result.scalar_one_or_none()
    
    if not asset_type:
        asset_type = AssetType(code=code, name=name)
        session.add(asset_type)
        await session.flush()
        logger.info(f"Created asset type: {code} - {name}")
    
    return asset_type


async def get_or_create_exchange(session: AsyncSession, code: str, name: str, country: str = "USA") -> Exchange:
    """Get or create an exchange."""
    # Check if exists
    result = await session.execute(
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
        await session.flush()
        logger.info(f"Created exchange: {code} - {name}")
    
    return exchange


async def get_or_create_sector(session: AsyncSession, name: str, gics_code: str = None) -> Sector:
    """Get or create a sector."""
    # Check if exists
    result = await session.execute(
        select(Sector).where(Sector.name == name)
    )
    sector = result.scalar_one_or_none()
    
    if not sector:
        sector = Sector(name=name, gics_code=gics_code)
        session.add(sector)
        await session.flush()
        logger.info(f"Created sector: {name}")
    
    return sector


def fetch_yfinance_data(ticker: str, retry_count: int = 3, delay: float = 1.0) -> Dict:
    """Fetch comprehensive company data from YFinance with rate limiting and retries."""
    for attempt in range(retry_count):
        try:
            # Add delay to avoid rate limiting
            if attempt > 0:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
            
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info
            
            # Extract relevant data with fallbacks
            data = {
                'market_cap': info.get('marketCap'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'beta': info.get('beta'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'volume_avg_30d': info.get('averageDailyVolume10Day'),
                'volatility_30d': info.get('beta'),  # Approximate with beta for now
                'business_summary': info.get('longBusinessSummary', ''),
                'industry': info.get('industry', ''),
                'sector_detailed': info.get('sector', ''),
                'website': info.get('website', ''),
                'employees': info.get('fullTimeEmployees'),
                'currency': info.get('currency', 'USD'),
                'exchange_name': info.get('exchange', ''),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'price_to_book': info.get('priceToBook'),
                'return_on_equity': info.get('returnOnEquity'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'revenue': info.get('totalRevenue'),
                'gross_profit': info.get('grossProfits'),
                'ebitda': info.get('ebitda'),
                'recommendation': info.get('recommendationKey', ''),
                'analyst_price_target': info.get('targetMeanPrice'),
            }
            
            logger.debug(f"Fetched YFinance data for {ticker}: market_cap={data.get('market_cap')}")
            
            # Add small delay even on success to be respectful to API
            time.sleep(0.1)
            return data
            
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                logger.warning(f"Rate limited for {ticker}, attempt {attempt + 1}/{retry_count}")
                if attempt < retry_count - 1:
                    continue
            else:
                logger.warning(f"Failed to fetch YFinance data for {ticker} (attempt {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    continue
    
    # All retries failed
    logger.warning(f"Failed to fetch YFinance data for {ticker} after {retry_count} attempts")
    return {}


async def get_or_create_security_enhanced(session: AsyncSession, ticker: str, name: str, 
                                         asset_type_id: int, exchange_id: int, sector_id: int = None) -> Security:
    """Get or create a security with enhanced YFinance data."""
    # Check if exists
    result = await session.execute(
        select(Security).where(Security.ticker == ticker.upper())
    )
    security = result.scalar_one_or_none()
    
    if not security:
        # Fetch YFinance data
        yf_data = fetch_yfinance_data(ticker)
        
        # Convert market cap to cents (our DB stores in cents)
        market_cap_cents = None
        if yf_data.get('market_cap'):
            try:
                market_cap_cents = int(yf_data['market_cap'] * 100)
            except:
                pass
        
        # Convert dividend yield to decimal (YFinance gives as decimal already)
        dividend_yield = yf_data.get('dividend_yield')
        if dividend_yield and dividend_yield > 1:
            dividend_yield = dividend_yield / 100  # Convert percentage to decimal
        
        # Create enhanced metadata
        metadata = {
            'business_summary': yf_data.get('business_summary', '')[:500],  # Truncate
            'industry': yf_data.get('industry', ''),
            'website': yf_data.get('website', ''),
            'employees': yf_data.get('employees'),
            'fifty_two_week_high': yf_data.get('fifty_two_week_high'),
            'fifty_two_week_low': yf_data.get('fifty_two_week_low'),
            'price_to_book': yf_data.get('price_to_book'),
            'return_on_equity': yf_data.get('return_on_equity'),
            'debt_to_equity': yf_data.get('debt_to_equity'),
            'current_ratio': yf_data.get('current_ratio'),
            'revenue': yf_data.get('revenue'),
            'gross_profit': yf_data.get('gross_profit'),
            'ebitda': yf_data.get('ebitda'),
            'recommendation': yf_data.get('recommendation', ''),
            'analyst_price_target': yf_data.get('analyst_price_target'),
            'data_source': 'yfinance',
            'last_updated': datetime.utcnow().isoformat()
        }
        
        security = Security(
            ticker=ticker.upper(),
            name=name,
            asset_type_id=asset_type_id,
            exchange_id=exchange_id,
            sector_id=sector_id,
            currency=yf_data.get('currency', 'USD'),
            market_cap=market_cap_cents,
            shares_outstanding=yf_data.get('shares_outstanding'),
            beta=yf_data.get('beta'),
            pe_ratio=yf_data.get('pe_ratio'),
            dividend_yield=dividend_yield,
            volume_avg_30d=yf_data.get('volume_avg_30d'),
            volatility_30d=yf_data.get('volatility_30d'),
            is_active=True,
            metadata=metadata
        )
        
        session.add(security)
        await session.flush()
        
        logger.info(f"Created enhanced security: {ticker} - {name} (Market Cap: ${market_cap_cents/100 if market_cap_cents else 'N/A'})")
    
    return security


# ============================================================================
# TICKER FETCHING
# ============================================================================

def fetch_sp500_tickers() -> List[Dict[str, str]]:
    """Fetch S&P 500 ticker list from Wikipedia."""
    try:
        logger.info("Fetching S&P 500 tickers from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
        tables = pd.read_html(url)
        sp500_table = tables[0]  # First table contains the S&P 500 list
        
        tickers = []
        for _, row in sp500_table.iterrows():
            ticker = str(row['Symbol']).replace('.', '-')  # Yahoo Finance format
            name = str(row['Security'])
            sector = str(row['GICS Sector'])
            
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


def fetch_nasdaq100_tickers() -> List[Dict[str, str]]:
    """Fetch NASDAQ-100 ticker list."""
    try:
        logger.info("Fetching NASDAQ-100 tickers...")
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        
        tables = pd.read_html(url)
        nasdaq_table = tables[4]  # Table with the companies
        
        tickers = []
        for _, row in nasdaq_table.iterrows():
            ticker = str(row['Ticker'])
            name = str(row['Company'])
            
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


def fetch_dow_jones_tickers() -> List[Dict[str, str]]:
    """Fetch Dow Jones Industrial Average ticker list."""
    try:
        logger.info("Fetching Dow Jones tickers...")
        url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
        
        tables = pd.read_html(url)
        dow_table = tables[2]  # Third table contains the companies (table index 2)
        
        tickers = []
        for _, row in dow_table.iterrows():
            ticker = str(row['Symbol'])
            name = str(row['Company'])
            
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


# ============================================================================
# MAIN INGESTION FUNCTIONS
# ============================================================================

async def populate_securities_from_major_indices(session: AsyncSession) -> Dict[str, int]:
    """Populate securities database with major market indices and enhanced YFinance data."""
    logger.info("Starting enhanced securities database population with YFinance data...")
    
    # Create reference data
    stock_asset_type = await get_or_create_asset_type(session, "STK", "Common Stock")
    nyse_exchange = await get_or_create_exchange(session, "NYSE", "New York Stock Exchange")
    nasdaq_exchange = await get_or_create_exchange(session, "NASDAQ", "NASDAQ Stock Market")
    
    # Common sectors
    tech_sector = await get_or_create_sector(session, "Technology", "45")
    finance_sector = await get_or_create_sector(session, "Financials", "40")
    healthcare_sector = await get_or_create_sector(session, "Health Care", "35")
    
    sector_map = {
        'Technology': tech_sector.id,
        'Financials': finance_sector.id,
        'Health Care': healthcare_sector.id,
        'Consumer Discretionary': tech_sector.id,  # Simplified mapping
        'Communication Services': tech_sector.id,
        'Industrials': tech_sector.id,
        'Consumer Staples': finance_sector.id,
        'Energy': finance_sector.id,
        'Utilities': finance_sector.id,
        'Real Estate': finance_sector.id,
        'Materials': finance_sector.id,
    }
    
    # Fetch all ticker lists
    all_tickers = []
    all_tickers.extend(fetch_sp500_tickers())
    all_tickers.extend(fetch_nasdaq100_tickers())
    all_tickers.extend(fetch_dow_jones_tickers())
    
    # Remove duplicates
    unique_tickers = {}
    for ticker_info in all_tickers:
        ticker = ticker_info['ticker']
        if ticker not in unique_tickers:
            unique_tickers[ticker] = ticker_info
    
    logger.info(f"Processing {len(unique_tickers)} unique tickers with YFinance enhancement...")
    
    created_count = 0
    failed_count = 0
    
    for ticker, info in unique_tickers.items():
        try:
            # Determine exchange (simplified logic)
            exchange_id = nasdaq_exchange.id if any(x in info['index'] for x in ['NASDAQ', 'Tech']) else nyse_exchange.id
            
            # Get sector ID
            sector_id = sector_map.get(info.get('sector'), tech_sector.id)
            
            # Create enhanced security with YFinance data
            security = await get_or_create_security_enhanced(
                session=session,
                ticker=ticker,
                name=info['name'],
                asset_type_id=stock_asset_type.id,
                exchange_id=exchange_id,
                sector_id=sector_id
            )
            
            created_count += 1
            
            # Commit every 10 securities (slower due to YFinance calls and rate limiting)
            if created_count % 10 == 0:
                await session.commit()
                logger.info(f"Progress: {created_count}/{len(unique_tickers)} enhanced securities processed")
                
        except Exception as e:
            logger.error(f"Failed to create enhanced security {ticker}: {e}")
            failed_count += 1
    
    # Final commit
    await session.commit()
    
    results = {
        'created': created_count,
        'failed': failed_count,
        'total_tickers': len(unique_tickers)
    }
    
    logger.info(f"Enhanced securities population completed: {results}")
    return results


async def ingest_price_data_for_all_securities(session: AsyncSession, batch_size: int = 50) -> Dict[str, int]:
    """Fetch historical price data for all securities."""
    logger.info("Starting price data ingestion for all securities...")
    
    # Get all securities
    result = await session.execute(select(Security).where(Security.is_active == True))
    securities = result.scalars().all()
    
    logger.info(f"Found {len(securities)} securities to process")
    
    total_securities = len(securities)
    processed_securities = 0
    total_price_records = 0
    failed_securities = 0
    
    for i in range(0, total_securities, batch_size):
        batch = securities[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}: securities {i+1}-{min(i+batch_size, total_securities)}")
        
        for security in batch:
            try:
                # Fetch price data using yfinance
                ticker_obj = yf.Ticker(security.ticker)
                hist = ticker_obj.history(period="1y")  # 1 year of data
                
                if hist.empty:
                    logger.warning(f"No price data found for {security.ticker}")
                    failed_securities += 1
                    continue
                
                # Insert price data
                price_records = 0
                for date_index, row in hist.iterrows():
                    try:
                        # Check if price already exists
                        existing = await session.execute(
                            select(DailyPrice).where(
                                DailyPrice.security_id == security.id,
                                DailyPrice.price_date == date_index.date()
                            )
                        )
                        
                        if existing.scalar_one_or_none():
                            continue  # Skip if already exists
                        
                        price = DailyPrice(
                            security_id=security.id,
                            price_date=date_index.date(),
                            open_price=int(row['Open'] * 100),  # Store in cents
                            high_price=int(row['High'] * 100),
                            low_price=int(row['Low'] * 100),
                            close_price=int(row['Close'] * 100),
                            volume=int(row['Volume'])
                        )
                        session.add(price)
                        price_records += 1
                        
                    except Exception as e:
                        logger.error(f"Error creating price record for {security.ticker}: {e}")
                
                total_price_records += price_records
                processed_securities += 1
                
                logger.debug(f"Added {price_records} price records for {security.ticker}")
                
            except Exception as e:
                logger.error(f"Error fetching price data for {security.ticker}: {e}")
                failed_securities += 1
        
        # Commit batch
        await session.commit()
        logger.info(f"Batch committed: {processed_securities} securities processed")
    
    results = {
        'total_securities': total_securities,
        'processed_securities': processed_securities,
        'total_price_records': total_price_records,
        'failed_securities': failed_securities
    }
    
    logger.info(f"Price data ingestion completed: {results}")
    return results


# Export main functions
__all__ = [
    "populate_securities_from_major_indices",
    "ingest_price_data_for_all_securities"
] 