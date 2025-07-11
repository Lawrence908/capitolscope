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
import os
import random
from sqlalchemy.exc import IntegrityError

from core.logging import get_logger
from domains.securities.models import Security, AssetType, Exchange, Sector, DailyPrice
from domains.base.schemas import validate_ticker_symbol
from dotenv import load_dotenv

load_dotenv()

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


# Global rate limiting state
yfinance_rate_limited = False
rate_limit_detected_time = 0

def fetch_yfinance_data(ticker: str, retry_count: int = 1, delay: float = 0.0) -> Dict:
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
                'exchange_code': info.get('exchange', ''),
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


def fetch_alpha_vantage_overview(ticker: str) -> dict:
    """Fetch company overview from Alpha Vantage API."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.warning("Alpha Vantage API key not set.")
        return {}
    
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data and 'Symbol' in data:
                # Convert Alpha Vantage format to our expected format
                return {
                    'market_cap': int(data.get('MarketCapitalization', 0)) if data.get('MarketCapitalization') else None,
                    'shares_outstanding': int(data.get('SharesOutstanding', 0)) if data.get('SharesOutstanding') else None,
                    'pe_ratio': float(data.get('PERatio', 0)) if data.get('PERatio') else None,
                    'dividend_yield': float(data.get('DividendYield', 0)) if data.get('DividendYield') else None,
                    'business_summary': data.get('Description', ''),
                    'industry': data.get('Industry', ''),
                    'website': data.get('Website', ''),
                    'employees': int(data.get('FullTimeEmployees', 0)) if data.get('FullTimeEmployees') else None,
                    'currency': data.get('Currency', 'USD'),
                    'beta': float(data.get('Beta', 0)) if data.get('Beta') else None,
                    'data_source': 'alpha_vantage'
                }
            else:
                logger.warning(f"Alpha Vantage returned no data for {ticker}")
    except Exception as e:
        logger.warning(f"Alpha Vantage error for {ticker}: {e}")
    return {}

def fetch_openfigi_identifiers(ticker: str, exchange_code: str) -> dict:
    api_key = os.getenv("OPEN_FIGI_API_KEY")
    if not api_key:
        logger.warning("OpenFIGI API key not set.")
        return {}
    url = "https://api.openfigi.com/v3/mapping"
    headers = {"Content-Type": "application/json", "X-OPENFIGI-APIKEY": api_key}
    data = [{
        "idType": "TICKER",
        "idValue": ticker,
        "exchCode": exchange_code
    }]
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=15)
        if resp.status_code == 200:
            out = resp.json()
            if out and out[0].get("data"):
                return out[0]["data"][0]
    except Exception as e:
        logger.warning(f"OpenFIGI error for {ticker}: {e}")
    return {}

# Patch get_or_create_security_enhanced to use Alpha Vantage and OpenFIGI
async def get_or_create_security_enhanced(session: AsyncSession, ticker: str, name: str, 
                                         asset_type_code: str, exchange_code: str, sector_gics_code: str = None) -> Security:
    """Get or create a security with enhanced YFinance data."""
    try:
        # Check if exists
        result = await session.execute(
            select(Security).where(Security.ticker == ticker.upper())
        )
        security = result.scalar_one_or_none()
        
        # Initialize variables for new data
        isin = None
        cusip = None
        figi = None
        yf_data = {}
        used_source = 'yfinance'
        
        # Always try to get OpenFIGI identifiers
        try:
            figi_data = fetch_openfigi_identifiers(ticker, exchange_code)
            isin = figi_data.get('isin')
            cusip = figi_data.get('cusip')
            figi = figi_data.get('figi')
        except Exception as e:
            logger.debug(f"OpenFIGI fetch failed for {ticker}: {e}")
        
        if not security:
            # Determine data source strategy based on ticker
            is_tsx = ticker.upper().endswith('.TO')
            
            if is_tsx:
                # For TSX tickers, skip YFinance entirely and go straight to Alpha Vantage
                logger.info(f"TSX ticker {ticker} - using Alpha Vantage directly")
                try:
                    yf_data = fetch_alpha_vantage_overview(ticker)
                    used_source = 'alpha_vantage'
                    # Add delay for TSX to avoid rate limiting
                    time.sleep(random.uniform(1, 3))
                except Exception as av_e:
                    logger.warning(f"Alpha Vantage failed for TSX {ticker}: {av_e}")
                    yf_data = {}
            else:
                # For non-TSX tickers, try YFinance first, then Alpha Vantage as fallback if YF returns no data
                try:
                    yf_data = fetch_yfinance_data(ticker)
                    used_source = 'yfinance'
                except Exception as e:
                    logger.warning(f"YFinance failed for {ticker}: {e}")
                    yf_data = {}
                # Fallback to Alpha Vantage if YFinance returns no data
                if not yf_data:
                    try:
                        yf_data = fetch_alpha_vantage_overview(ticker)
                        if yf_data:
                            used_source = 'alpha_vantage'
                    except Exception as av_e:
                        logger.warning(f"Alpha Vantage also failed for {ticker}: {av_e}")
                        yf_data = {}
            
            # --- CAD override for TSX tickers ---
            currency = yf_data.get('currency', 'USD')
            if ticker.upper().endswith('.TO') and (not currency or currency == 'USD'):
                currency = 'CAD'
            # --- end CAD override ---
            
            # Convert market cap to cents (our DB stores in cents)
            market_cap_cents = None
            if yf_data.get('market_cap'):
                market_cap_cents = int(yf_data['market_cap'] * 100)
            
            # Create new security
            security = Security(
                ticker=ticker.upper(),
                name=name,
                asset_type_code=asset_type_code,
                sector_gics_code=sector_gics_code,
                exchange_code=exchange_code,
                currency=currency,
                market_cap=market_cap_cents,
                shares_outstanding=yf_data.get('shares_outstanding'),
                isin=isin,
                cusip=cusip,
                figi=figi,
                beta=yf_data.get('beta'),
                pe_ratio=yf_data.get('pe_ratio'),
                dividend_yield=yf_data.get('dividend_yield'),
                volatility_30d=yf_data.get('volatility_30d'),
                volume_avg_30d=yf_data.get('volume_avg_30d'),
                esg_score=yf_data.get('esg_score'),
                controversy_score=yf_data.get('controversy_score'),
                extra_data={
                    'business_summary': yf_data.get('business_summary', ''),
                    'industry': yf_data.get('industry', ''),
                    'website': yf_data.get('website', ''),
                    'employees': yf_data.get('employees'),
                    'data_source': used_source
                }
            )
            
            try:
                session.add(security)
                await session.flush()
                logger.info(f"Created enhanced security {ticker} using {used_source}")
            except IntegrityError as e:
                logger.warning(f"Duplicate security {ticker} detected during creation: {e}")
                # Don't call rollback here - let the session handle it
                # Try to get the existing security
                result = await session.execute(
                    select(Security).where(Security.ticker == ticker.upper())
                )
                security = result.scalar_one_or_none()
                if not security:
                    logger.error(f"Failed to retrieve existing security {ticker} after duplicate error")
                    return None
        else:
            # Security exists - update with new data if available
            updated = False
            
            # Update identifiers if we have new ones and they're not already set
            if isin and not security.isin:
                security.isin = isin
                updated = True
            if cusip and not security.cusip:
                security.cusip = cusip
                updated = True
            if figi and not security.figi:
                security.figi = figi
                updated = True
            
            if updated:
                try:
                    await session.flush()
                    logger.info(f"Updated identifiers for existing security {ticker}")
                except IntegrityError as e:
                    logger.warning(f"Error updating {ticker}: {e}")
                    # Don't call rollback here
        
        return security
        
    except IntegrityError as e:
        logger.error(f"Database integrity error for {ticker}: {e}")
        # Don't call rollback here - let the session handle it
        return None
    except Exception as e:
        logger.error(f"Failed to create enhanced security {ticker}: {e}")
        # Don't call rollback here - let the session handle it
        return None


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
        # Fallback to common major stocks
        logger.info("Using fallback list of major stocks")
        return [
            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'BRK-B', 'name': 'Berkshire Hathaway Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'V', 'name': 'Visa Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'PG', 'name': 'Procter & Gamble Co.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'HD', 'name': 'Home Depot Inc.', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'MA', 'name': 'Mastercard Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'UNH', 'name': 'UnitedHealth Group Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'DIS', 'name': 'Walt Disney Co.', 'sector': 'Communication Services', 'index': 'S&P 500'},
            {'ticker': 'PYPL', 'name': 'PayPal Holdings Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'BAC', 'name': 'Bank of America Corp.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'ADBE', 'name': 'Adobe Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'CRM', 'name': 'Salesforce Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Communication Services', 'index': 'S&P 500'},
            {'ticker': 'INTC', 'name': 'Intel Corporation', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'PFE', 'name': 'Pfizer Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'ABT', 'name': 'Abbott Laboratories', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'KO', 'name': 'Coca-Cola Co.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'PEP', 'name': 'PepsiCo Inc.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'TMO', 'name': 'Thermo Fisher Scientific Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'AVGO', 'name': 'Broadcom Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'COST', 'name': 'Costco Wholesale Corporation', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'ABBV', 'name': 'AbbVie Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'MRK', 'name': 'Merck & Co. Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'LLY', 'name': 'Eli Lilly and Co.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'QCOM', 'name': 'Qualcomm Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'DHR', 'name': 'Danaher Corporation', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'ACN', 'name': 'Accenture plc', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'VZ', 'name': 'Verizon Communications Inc.', 'sector': 'Communication Services', 'index': 'S&P 500'},
            {'ticker': 'TXN', 'name': 'Texas Instruments Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'CMCSA', 'name': 'Comcast Corporation', 'sector': 'Communication Services', 'index': 'S&P 500'},
            {'ticker': 'HON', 'name': 'Honeywell International Inc.', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'NEE', 'name': 'NextEra Energy Inc.', 'sector': 'Utilities', 'index': 'S&P 500'},
            {'ticker': 'PM', 'name': 'Philip Morris International Inc.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'RTX', 'name': 'Raytheon Technologies Corporation', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'LOW', 'name': 'Lowe\'s Companies Inc.', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'UPS', 'name': 'United Parcel Service Inc.', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'IBM', 'name': 'International Business Machines Corporation', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'AMD', 'name': 'Advanced Micro Devices Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'CAT', 'name': 'Caterpillar Inc.', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'GS', 'name': 'Goldman Sachs Group Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'MS', 'name': 'Morgan Stanley', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'SPGI', 'name': 'S&P Global Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'ISRG', 'name': 'Intuitive Surgical Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'GILD', 'name': 'Gilead Sciences Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'AMGN', 'name': 'Amgen Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'ADP', 'name': 'Automatic Data Processing Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'BKNG', 'name': 'Booking Holdings Inc.', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'MDLZ', 'name': 'Mondelez International Inc.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'ADI', 'name': 'Analog Devices Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'REGN', 'name': 'Regeneron Pharmaceuticals Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'BDX', 'name': 'Becton Dickinson and Co.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'KLAC', 'name': 'KLA Corporation', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'SBUX', 'name': 'Starbucks Corporation', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'TMUS', 'name': 'T-Mobile US Inc.', 'sector': 'Communication Services', 'index': 'S&P 500'},
            {'ticker': 'CHTR', 'name': 'Charter Communications Inc.', 'sector': 'Communication Services', 'index': 'S&P 500'},
            {'ticker': 'MU', 'name': 'Micron Technology Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'PANW', 'name': 'Palo Alto Networks Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'ORCL', 'name': 'Oracle Corporation', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'INTU', 'name': 'Intuit Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'CSCO', 'name': 'Cisco Systems Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'CME', 'name': 'CME Group Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'BLK', 'name': 'BlackRock Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'SYK', 'name': 'Stryker Corporation', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'AMAT', 'name': 'Applied Materials Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'VRTX', 'name': 'Vertex Pharmaceuticals Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'TGT', 'name': 'Target Corporation', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'SCHW', 'name': 'Charles Schwab Corporation', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'MO', 'name': 'Altria Group Inc.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'PLD', 'name': 'Prologis Inc.', 'sector': 'Real Estate', 'index': 'S&P 500'},
            {'ticker': 'DUK', 'name': 'Duke Energy Corporation', 'sector': 'Utilities', 'index': 'S&P 500'},
            {'ticker': 'SO', 'name': 'Southern Company', 'sector': 'Utilities', 'index': 'S&P 500'},
            {'ticker': 'AON', 'name': 'Aon plc', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'ITW', 'name': 'Illinois Tool Works Inc.', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'MMC', 'name': 'Marsh & McLennan Companies Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'ETN', 'name': 'Eaton Corporation plc', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'TJX', 'name': 'TJX Companies Inc.', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'CI', 'name': 'Cigna Corporation', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'USB', 'name': 'U.S. Bancorp', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'PGR', 'name': 'Progressive Corporation', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'TRV', 'name': 'Travelers Companies Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'ZTS', 'name': 'Zoetis Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'AIG', 'name': 'American International Group Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'FISV', 'name': 'Fiserv Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'ICE', 'name': 'Intercontinental Exchange Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'EQIX', 'name': 'Equinix Inc.', 'sector': 'Real Estate', 'index': 'S&P 500'},
            {'ticker': 'COF', 'name': 'Capital One Financial Corporation', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'APD', 'name': 'Air Products and Chemicals Inc.', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'NOC', 'name': 'Northrop Grumman Corporation', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'CTAS', 'name': 'Cintas Corporation', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'HUM', 'name': 'Humana Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'MCD', 'name': 'McDonald\'s Corporation', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'NSC', 'name': 'Norfolk Southern Corporation', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'WM', 'name': 'Waste Management Inc.', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'ANTM', 'name': 'Anthem Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'FDX', 'name': 'FedEx Corporation', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'LMT', 'name': 'Lockheed Martin Corporation', 'sector': 'Industrials', 'index': 'S&P 500'},
            {'ticker': 'COP', 'name': 'ConocoPhillips', 'sector': 'Energy', 'index': 'S&P 500'},
            {'ticker': 'EOG', 'name': 'EOG Resources Inc.', 'sector': 'Energy', 'index': 'S&P 500'},
            {'ticker': 'SLB', 'name': 'Schlumberger Limited', 'sector': 'Energy', 'index': 'S&P 500'},
            {'ticker': 'CVX', 'name': 'Chevron Corporation', 'sector': 'Energy', 'index': 'S&P 500'},
            {'ticker': 'XOM', 'name': 'Exxon Mobil Corporation', 'sector': 'Energy', 'index': 'S&P 500'},
            {'ticker': 'DOW', 'name': 'Dow Inc.', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'DD', 'name': 'DuPont de Nemours Inc.', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'LIN', 'name': 'Linde plc', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'NEM', 'name': 'Newmont Corporation', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'FCX', 'name': 'Freeport-McMoRan Inc.', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'BLL', 'name': 'Ball Corporation', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'ECL', 'name': 'Ecolab Inc.', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'APTV', 'name': 'Aptiv plc', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'ALB', 'name': 'Albemarle Corporation', 'sector': 'Materials', 'index': 'S&P 500'},
            {'ticker': 'BEN', 'name': 'Franklin Resources Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'CHD', 'name': 'Church & Dwight Co. Inc.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
            {'ticker': 'DG', 'name': 'Dollar General Corporation', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'INTC', 'name': 'Intel Corporation', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'VZ', 'name': 'Verizon Communications Inc.', 'sector': 'Communication Services', 'index': 'S&P 500'},
            {'ticker': 'ABBV', 'name': 'AbbVie Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'CSCO', 'name': 'Cisco Systems Inc.', 'sector': 'Technology', 'index': 'S&P 500'},
            {'ticker': 'YUM', 'name': 'Yum! Brands Inc.', 'sector': 'Consumer Discretionary', 'index': 'S&P 500'},
            {'ticker': 'MUR', 'name': 'Murphy Oil Corporation', 'sector': 'Energy', 'index': 'S&P 500'},
            {'ticker': 'DBA', 'name': 'Invesco DB Agriculture Fund', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'ARCP', 'name': 'American Realty Capital Properties Inc.', 'sector': 'Real Estate', 'index': 'S&P 500'},
            {'ticker': 'CG', 'name': 'Carlyle Group Inc.', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'PBYI', 'name': 'Puma Biotechnology Inc.', 'sector': 'Health Care', 'index': 'S&P 500'},
            {'ticker': 'SLV', 'name': 'iShares Silver Trust', 'sector': 'Financials', 'index': 'S&P 500'},
            {'ticker': 'HLF', 'name': 'Herbalife Nutrition Ltd.', 'sector': 'Consumer Staples', 'index': 'S&P 500'},
        ]


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
        # Return empty list since S&P 500 fallback will cover most major stocks
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
        # Return empty list since S&P 500 fallback will cover most major stocks
        return []


def fetch_tsx_tickers() -> List[Dict[str, str]]:
    logger.info("Fetching TSX tickers from Wikipedia (A-Z, 0-9)...")
    tickers = []
    suffixes = ["0-9"] + [chr(i) for i in range(ord('A'), ord('Z')+1)]
    base_url = "https://en.wikipedia.org/wiki/Companies_listed_on_the_Toronto_Stock_Exchange_({})"
    for suffix in suffixes:
        url = base_url.format(suffix)
        try:
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find_all("table")[1]
            for row in table.find_all("tr")[1:]:  # skip header
                tds = row.find_all("td")
                if len(tds) < 2:
                    continue
                if tds[0].find("a") is None or tds[1].find("a") is None:
                    continue
                # Get company name (from link title or text)
                name_link = tds[0].find("a")
                name = name_link["title"] if name_link and name_link.has_attr("title") else tds[0].get_text(strip=True)
                # Get symbol (from link text)
                symbol_link = tds[1].find("a")
                symbol = symbol_link.get_text(strip=True) if symbol_link else tds[1].get_text(strip=True)
                # Get TMX link (optional)
                tmx_link = symbol_link["href"] if symbol_link and symbol_link.has_attr("href") else None
                tickers.append({
                    "ticker": symbol.replace('.', '-'),  # Yahoo format
                    "name": name,
                    "index": "TSX",
                    "tmx_url": tmx_link
                })
            logger.info(f"Fetched {len(tickers)} tickers from {url}")
        except Exception as e:
            logger.warning(f"Failed to fetch TSX tickers from {url}: {e}")
    logger.info(f"Total TSX tickers fetched: {len(tickers)}")
    return tickers


def fetch_bond_securities() -> List[Dict[str, str]]:
    """Fetch major bond ETFs and government bonds that congress members commonly trade."""
    logger.info("Adding major bond securities...")
    
    # Major bond ETFs and government bonds
    bond_securities = [
        # Government Bonds
        {'ticker': 'TLT', 'name': 'iShares 20+ Year Treasury Bond ETF', 'sector': 'Government', 'index': 'Bonds'},
        {'ticker': 'IEF', 'name': 'iShares 7-10 Year Treasury Bond ETF', 'sector': 'Government', 'index': 'Bonds'},
        {'ticker': 'SHY', 'name': 'iShares 1-3 Year Treasury Bond ETF', 'sector': 'Government', 'index': 'Bonds'},
        {'ticker': 'VGIT', 'name': 'Vanguard Intermediate-Term Treasury ETF', 'sector': 'Government', 'index': 'Bonds'},
        {'ticker': 'VGSH', 'name': 'Vanguard Short-Term Treasury ETF', 'sector': 'Government', 'index': 'Bonds'},
        {'ticker': 'VGLT', 'name': 'Vanguard Long-Term Treasury ETF', 'sector': 'Government', 'index': 'Bonds'},
        
        # Corporate Bonds
        {'ticker': 'LQD', 'name': 'iShares iBoxx $ Investment Grade Corporate Bond ETF', 'sector': 'Corporate', 'index': 'Bonds'},
        {'ticker': 'VCIT', 'name': 'Vanguard Intermediate-Term Corporate Bond ETF', 'sector': 'Corporate', 'index': 'Bonds'},
        {'ticker': 'VCSH', 'name': 'Vanguard Short-Term Corporate Bond ETF', 'sector': 'Corporate', 'index': 'Bonds'},
        {'ticker': 'VCLT', 'name': 'Vanguard Long-Term Corporate Bond ETF', 'sector': 'Corporate', 'index': 'Bonds'},
        {'ticker': 'HYG', 'name': 'iShares iBoxx $ High Yield Corporate Bond ETF', 'sector': 'High Yield', 'index': 'Bonds'},
        {'ticker': 'JNK', 'name': 'SPDR Bloomberg High Yield Bond ETF', 'sector': 'High Yield', 'index': 'Bonds'},
        
        # Municipal Bonds
        {'ticker': 'MUB', 'name': 'iShares National Muni Bond ETF', 'sector': 'Municipal', 'index': 'Bonds'},
        {'ticker': 'VTEB', 'name': 'Vanguard Tax-Exempt Bond ETF', 'sector': 'Municipal', 'index': 'Bonds'},
        {'ticker': 'TFI', 'name': 'SPDR Nuveen Bloomberg Municipal Bond ETF', 'sector': 'Municipal', 'index': 'Bonds'},
        
        # International Bonds
        {'ticker': 'BWX', 'name': 'SPDR Bloomberg International Treasury Bond ETF', 'sector': 'International', 'index': 'Bonds'},
        {'ticker': 'EMB', 'name': 'iShares J.P. Morgan USD Emerging Markets Bond ETF', 'sector': 'Emerging Markets', 'index': 'Bonds'},
        {'ticker': 'PCY', 'name': 'Invesco Emerging Markets Sovereign Debt ETF', 'sector': 'Emerging Markets', 'index': 'Bonds'},
        
        # TIPS (Treasury Inflation-Protected Securities)
        {'ticker': 'TIP', 'name': 'iShares TIPS Bond ETF', 'sector': 'Government', 'index': 'Bonds'},
        {'ticker': 'VTIP', 'name': 'Vanguard Short-Term Inflation-Protected Securities ETF', 'sector': 'Government', 'index': 'Bonds'},
        {'ticker': 'SCHP', 'name': 'Schwab U.S. TIPS ETF', 'sector': 'Government', 'index': 'Bonds'},
        
        # Floating Rate Bonds
        {'ticker': 'FLOT', 'name': 'iShares Floating Rate Bond ETF', 'sector': 'Corporate', 'index': 'Bonds'},
        {'ticker': 'FLRN', 'name': 'SPDR Bloomberg Investment Grade Floating Rate ETF', 'sector': 'Corporate', 'index': 'Bonds'},
        
        # Preferred Stock ETFs (often traded like bonds)
        {'ticker': 'PFF', 'name': 'iShares Preferred and Income Securities ETF', 'sector': 'Preferred', 'index': 'Bonds'},
        {'ticker': 'PGX', 'name': 'Invesco Preferred ETF', 'sector': 'Preferred', 'index': 'Bonds'},
        {'ticker': 'PSK', 'name': 'SPDR ICE Preferred Securities ETF', 'sector': 'Preferred', 'index': 'Bonds'},
    ]
    
    logger.info(f"Added {len(bond_securities)} bond securities")
    return bond_securities


def fetch_etf_securities() -> List[Dict[str, str]]:
    """Fetch major ETFs that congress members commonly trade."""
    logger.info("Adding major ETF securities...")
    
    # Major ETFs across different categories
    etf_securities = [
        # Broad Market ETFs
        {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'sector': 'Broad Market', 'index': 'ETFs'},
        {'ticker': 'VOO', 'name': 'Vanguard S&P 500 ETF', 'sector': 'Broad Market', 'index': 'ETFs'},
        {'ticker': 'IVV', 'name': 'iShares Core S&P 500 ETF', 'sector': 'Broad Market', 'index': 'ETFs'},
        {'ticker': 'QQQ', 'name': 'Invesco QQQ Trust', 'sector': 'Technology', 'index': 'ETFs'},
        {'ticker': 'IWM', 'name': 'iShares Russell 2000 ETF', 'sector': 'Small Cap', 'index': 'ETFs'},
        {'ticker': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'sector': 'Broad Market', 'index': 'ETFs'},
        {'ticker': 'ITOT', 'name': 'iShares Core S&P Total U.S. Stock Market ETF', 'sector': 'Broad Market', 'index': 'ETFs'},
        
        # International ETFs
        {'ticker': 'EFA', 'name': 'iShares MSCI EAFE ETF', 'sector': 'International', 'index': 'ETFs'},
        {'ticker': 'VEA', 'name': 'Vanguard FTSE Developed Markets ETF', 'sector': 'International', 'index': 'ETFs'},
        {'ticker': 'EEM', 'name': 'iShares MSCI Emerging Markets ETF', 'sector': 'Emerging Markets', 'index': 'ETFs'},
        {'ticker': 'VWO', 'name': 'Vanguard FTSE Emerging Markets ETF', 'sector': 'Emerging Markets', 'index': 'ETFs'},
        {'ticker': 'IEMG', 'name': 'iShares Core MSCI Emerging Markets ETF', 'sector': 'Emerging Markets', 'index': 'ETFs'},
        
        # Sector ETFs
        {'ticker': 'XLK', 'name': 'Technology Select Sector SPDR Fund', 'sector': 'Technology', 'index': 'ETFs'},
        {'ticker': 'XLF', 'name': 'Financial Select Sector SPDR Fund', 'sector': 'Financials', 'index': 'ETFs'},
        {'ticker': 'XLV', 'name': 'Health Care Select Sector SPDR Fund', 'sector': 'Health Care', 'index': 'ETFs'},
        {'ticker': 'XLE', 'name': 'Energy Select Sector SPDR Fund', 'sector': 'Energy', 'index': 'ETFs'},
        {'ticker': 'XLI', 'name': 'Industrial Select Sector SPDR Fund', 'sector': 'Industrials', 'index': 'ETFs'},
        {'ticker': 'XLP', 'name': 'Consumer Staples Select Sector SPDR Fund', 'sector': 'Consumer Staples', 'index': 'ETFs'},
        {'ticker': 'XLY', 'name': 'Consumer Discretionary Select Sector SPDR Fund', 'sector': 'Consumer Discretionary', 'index': 'ETFs'},
        {'ticker': 'XLU', 'name': 'Utilities Select Sector SPDR Fund', 'sector': 'Utilities', 'index': 'ETFs'},
        {'ticker': 'XLB', 'name': 'Materials Select Sector SPDR Fund', 'sector': 'Materials', 'index': 'ETFs'},
        {'ticker': 'XLRE', 'name': 'Real Estate Select Sector SPDR Fund', 'sector': 'Real Estate', 'index': 'ETFs'},
        
        # Commodity ETFs
        {'ticker': 'GLD', 'name': 'SPDR Gold Shares', 'sector': 'Commodities', 'index': 'ETFs'},
        {'ticker': 'SLV', 'name': 'iShares Silver Trust', 'sector': 'Commodities', 'index': 'ETFs'},
        {'ticker': 'USO', 'name': 'United States Oil Fund LP', 'sector': 'Commodities', 'index': 'ETFs'},
        {'ticker': 'UNG', 'name': 'United States Natural Gas Fund LP', 'sector': 'Commodities', 'index': 'ETFs'},
        
        # Dividend ETFs
        {'ticker': 'DVY', 'name': 'iShares Select Dividend ETF', 'sector': 'Dividend', 'index': 'ETFs'},
        {'ticker': 'VYM', 'name': 'Vanguard High Dividend Yield ETF', 'sector': 'Dividend', 'index': 'ETFs'},
        {'ticker': 'SCHD', 'name': 'Schwab U.S. Dividend Equity ETF', 'sector': 'Dividend', 'index': 'ETFs'},
        
        # Growth/Value ETFs
        {'ticker': 'VUG', 'name': 'Vanguard Growth ETF', 'sector': 'Growth', 'index': 'ETFs'},
        {'ticker': 'VTV', 'name': 'Vanguard Value ETF', 'sector': 'Value', 'index': 'ETFs'},
        {'ticker': 'IWF', 'name': 'iShares Russell 1000 Growth ETF', 'sector': 'Growth', 'index': 'ETFs'},
        {'ticker': 'IWD', 'name': 'iShares Russell 1000 Value ETF', 'sector': 'Value', 'index': 'ETFs'},
        
        # Volatility ETFs
        {'ticker': 'VXX', 'name': 'iPath Series B S&P 500 VIX Short-Term Futures ETN', 'sector': 'Volatility', 'index': 'ETFs'},
        {'ticker': 'UVXY', 'name': 'ProShares Ultra VIX Short-Term Futures ETF', 'sector': 'Volatility', 'index': 'ETFs'},
    ]
    
    logger.info(f"Added {len(etf_securities)} ETF securities")
    return etf_securities


def fetch_security_data_alpha_vantage_only(ticker: str) -> Dict:
    """
    Fetch security data using only Alpha Vantage API to avoid Yahoo Finance rate limiting.
    
    This function completely bypasses Yahoo Finance and uses Alpha Vantage as the primary
    data source to avoid the widespread 429 rate limiting issues.
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.warning("Alpha Vantage API key not set. Cannot fetch data.")
        return {}
    
    try:
        # Add delay to be respectful to Alpha Vantage API
        time.sleep(1.0)
        
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
        resp = requests.get(url, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            if data and 'Symbol' in data:
                # Convert Alpha Vantage format to our expected format
                result = {
                    'market_cap': int(data.get('MarketCapitalization', 0)) if data.get('MarketCapitalization') else None,
                    'shares_outstanding': int(data.get('SharesOutstanding', 0)) if data.get('SharesOutstanding') else None,
                    'pe_ratio': float(data.get('PERatio', 0)) if data.get('PERatio') else None,
                    'dividend_yield': float(data.get('DividendYield', 0)) if data.get('DividendYield') else None,
                    'business_summary': data.get('Description', ''),
                    'industry': data.get('Industry', ''),
                    'website': data.get('Website', ''),
                    'employees': int(data.get('FullTimeEmployees', 0)) if data.get('FullTimeEmployees') else None,
                    'currency': data.get('Currency', 'USD'),
                    'beta': float(data.get('Beta', 0)) if data.get('Beta') else None,
                    'data_source': 'alpha_vantage'
                }
                
                logger.debug(f"Fetched Alpha Vantage data for {ticker}: market_cap={result.get('market_cap')}")
                return result
            else:
                logger.warning(f"Alpha Vantage returned no data for {ticker}")
                return {}
        else:
            logger.warning(f"Alpha Vantage API error for {ticker}: HTTP {resp.status_code}")
            return {}
            
    except Exception as e:
        logger.error(f"Alpha Vantage error for {ticker}: {e}")
        return {}


# ============================================================================
# MAIN INGESTION FUNCTIONS
# ============================================================================

# Global shutdown flag for graceful interruption
shutdown_requested = False

def set_shutdown_flag():
    """Set the shutdown flag for graceful interruption."""
    global shutdown_requested
    shutdown_requested = True

async def populate_securities_from_major_indices(session: AsyncSession) -> Dict[str, int]:
    """Populate securities database with major market indices and enhanced YFinance data."""
    global shutdown_requested
    
    logger.info("Starting enhanced securities database population with YFinance data...")
    
    # Create reference data
    stock_asset_type = await get_or_create_asset_type(session, "STK", "Common Stock")
    bond_asset_type = await get_or_create_asset_type(session, "BND", "Bond")
    etf_asset_type = await get_or_create_asset_type(session, "ETF", "Exchange Traded Fund")
    preferred_asset_type = await get_or_create_asset_type(session, "PFD", "Preferred Stock")
    mutual_fund_asset_type = await get_or_create_asset_type(session, "MF", "Mutual Fund")
    
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
    
    # Fetch all ticker lists
    all_tickers = []
    
    try:
        logger.info("Fetching S&P 500 tickers...")
        sp500_tickers = fetch_sp500_tickers()
        all_tickers.extend(sp500_tickers)
        logger.info(f"Fetched {len(sp500_tickers)} S&P 500 tickers")
    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 tickers: {e}")
        sp500_tickers = []
    
    try:
        logger.info("Fetching NASDAQ-100 tickers...")
        nasdaq_tickers = fetch_nasdaq100_tickers()
        all_tickers.extend(nasdaq_tickers)
        logger.info(f"Fetched {len(nasdaq_tickers)} NASDAQ-100 tickers")
    except Exception as e:
        logger.error(f"Failed to fetch NASDAQ-100 tickers: {e}")
        nasdaq_tickers = []
    
    try:
        logger.info("Fetching Dow Jones tickers...")
        dow_tickers = fetch_dow_jones_tickers()
        all_tickers.extend(dow_tickers)
        logger.info(f"Fetched {len(dow_tickers)} Dow Jones tickers")
    except Exception as e:
        logger.error(f"Failed to fetch Dow Jones tickers: {e}")
        dow_tickers = []
    
    try:
        logger.info("Fetching TSX tickers...")
        tsx_tickers = fetch_tsx_tickers()
        all_tickers.extend(tsx_tickers)
        logger.info(f"Fetched {len(tsx_tickers)} TSX tickers")
    except Exception as e:
        logger.error(f"Failed to fetch TSX tickers: {e}")
        tsx_tickers = []
    
    try:
        logger.info("Fetching bond securities...")
        bond_tickers = fetch_bond_securities()
        all_tickers.extend(bond_tickers)
        logger.info(f"Fetched {len(bond_tickers)} bond securities")
    except Exception as e:
        logger.error(f"Failed to fetch bond securities: {e}")
        bond_tickers = []
    
    try:
        logger.info("Fetching ETF securities...")
        etf_tickers = fetch_etf_securities()
        all_tickers.extend(etf_tickers)
        logger.info(f"Fetched {len(etf_tickers)} ETF securities")
    except Exception as e:
        logger.error(f"Failed to fetch ETF securities: {e}")
        etf_tickers = []
    
    # Process all tickers
    created_count = 0
    failed_count = 0
    skipped_count = 0
    
    logger.info(f"Processing {len(all_tickers)} total tickers...")
    
    for i, info in enumerate(all_tickers):
        # Check for shutdown request
        if shutdown_requested:
            logger.warning("Shutdown requested during processing. Stopping gracefully.")
            break
            
        try:
            ticker = info['ticker']
            name = info['name']
            
            # # Add delay between processing tickers to avoid rate limiting
            # if i > 0 and i % 10 == 0:  # Every 10 tickers, add a longer delay
            #     logger.info(f"Rate limiting: pausing for 5 seconds after processing {i} tickers...")
            #     time.sleep(5.0)
            # elif i > 0:  # Add small delay between each ticker
            #     time.sleep(0.5)
            
            # Determine exchange (enhanced logic)
            if any(x in info['index'] for x in ['NASDAQ', 'Tech']):
                exchange_code = nasdaq_exchange.code
            elif any(x in info['index'] for x in ['TSX']):
                exchange_code = tsx_exchange.code
            else:
                exchange_code = nyse_exchange.code
            
            # Get sector GICS code
            sector_gics_code = sector_map.get(info.get('sector'), tech_sector.gics_code)
            
            # Determine asset type based on index and ticker
            if info['index'] == 'Bonds':
                asset_type_code = bond_asset_type.code
            elif info['index'] == 'ETFs':
                asset_type_code = etf_asset_type.code
            else:
                asset_type_code = stock_asset_type.code
            
            # Create enhanced security with YFinance data
            security = await get_or_create_security_enhanced(
                session, ticker, name, asset_type_code, exchange_code, sector_gics_code
            )
            
            if security:
                created_count += 1
                if created_count % 50 == 0:
                    logger.info(f"Processed {created_count} securities...")
            else:
                failed_count += 1
                
        except IntegrityError as e:
            logger.warning(f"Integrity error for {info.get('ticker', 'unknown')}: {e}")
            # Don't call rollback here - let the session handle it
            failed_count += 1
        except Exception as e:
            logger.error(f"Failed to process {info.get('ticker', 'unknown')}: {e}")
            # Don't call rollback here - let the session handle it
            failed_count += 1
    
    # Commit all changes
    try:
        await session.commit()
        logger.info(f"✅ Securities population completed successfully!")
        logger.info(f"📊 Created: {created_count}, Failed: {failed_count}, Skipped: {skipped_count}")
    except Exception as e:
        logger.error(f"❌ Failed to commit securities data: {e}")
        # Don't call rollback here - let the session handle it
        raise
    
    return {
        "S&P 500": len(sp500_tickers),
        "NASDAQ-100": len(nasdaq_tickers),
        "Dow Jones": len(dow_tickers),
        "TSX": len(tsx_tickers),
        "Bonds": len(bond_tickers),
        "ETFs": len(etf_tickers),
        "created": created_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "total": len(all_tickers)
    }


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