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
from domains.base.schemas import validate_ticker_symbol

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
    """Fetch TSX (Toronto Stock Exchange) ticker list from Wikipedia."""
    try:
        logger.info("Fetching TSX tickers from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_TSX_companies"
        
        tables = pd.read_html(url)
        tsx_table = tables[0]  # First table contains the TSX list
        
        tickers = []
        for _, row in tsx_table.iterrows():
            ticker = str(row['Symbol']).replace('.', '-')  # Yahoo Finance format
            name = str(row['Company'])
            sector = str(row.get('Sector', 'Unknown'))
            
            tickers.append({
                'ticker': ticker,
                'name': name,
                'sector': sector,
                'index': 'TSX'
            })
        
        logger.info(f"Fetched {len(tickers)} TSX tickers")
        return tickers
        
    except Exception as e:
        logger.error(f"Error fetching TSX tickers: {e}")
        # Fallback to major Canadian stocks
        logger.info("Using fallback list of major TSX stocks")
        return [
            {'ticker': 'RY.TO', 'name': 'Royal Bank of Canada', 'sector': 'Financials', 'index': 'TSX'},
            {'ticker': 'TD.TO', 'name': 'Toronto-Dominion Bank', 'sector': 'Financials', 'index': 'TSX'},
            {'ticker': 'SHOP.TO', 'name': 'Shopify Inc.', 'sector': 'Technology', 'index': 'TSX'},
            {'ticker': 'CNR.TO', 'name': 'Canadian National Railway', 'sector': 'Industrials', 'index': 'TSX'},
            {'ticker': 'CP.TO', 'name': 'Canadian Pacific Railway', 'sector': 'Industrials', 'index': 'TSX'},
            {'ticker': 'BCE.TO', 'name': 'BCE Inc.', 'sector': 'Communication Services', 'index': 'TSX'},
            {'ticker': 'TRI.TO', 'name': 'Thomson Reuters Corporation', 'sector': 'Technology', 'index': 'TSX'},
            {'ticker': 'ENB.TO', 'name': 'Enbridge Inc.', 'sector': 'Energy', 'index': 'TSX'},
            {'ticker': 'SU.TO', 'name': 'Suncor Energy Inc.', 'sector': 'Energy', 'index': 'TSX'},
            {'ticker': 'ABX.TO', 'name': 'Barrick Gold Corporation', 'sector': 'Materials', 'index': 'TSX'},
            {'ticker': 'GOLD.TO', 'name': 'Barrick Gold Corporation', 'sector': 'Materials', 'index': 'TSX'},
            {'ticker': 'WCN.TO', 'name': 'Waste Connections Inc.', 'sector': 'Industrials', 'index': 'TSX'},
            {'ticker': 'ATD.TO', 'name': 'Alimentation Couche-Tard Inc.', 'sector': 'Consumer Staples', 'index': 'TSX'},
            {'ticker': 'L.TO', 'name': 'Loblaw Companies Limited', 'sector': 'Consumer Staples', 'index': 'TSX'},
            {'ticker': 'MRU.TO', 'name': 'Metro Inc.', 'sector': 'Consumer Staples', 'index': 'TSX'},
        ]


# ============================================================================
# MAIN INGESTION FUNCTIONS
# ============================================================================

async def populate_securities_from_major_indices(session: AsyncSession) -> Dict[str, int]:
    """Populate securities database with major market indices and enhanced YFinance data."""
    logger.info("Starting enhanced securities database population with YFinance data...")
    
    # Create reference data
    stock_asset_type = await get_or_create_asset_type(session, "STK", "Common Stock")
    bond_asset_type = await get_or_create_asset_type(session, "BND", "Bond")
    etf_asset_type = await get_or_create_asset_type(session, "ETF", "Exchange Traded Fund")
    preferred_asset_type = await get_or_create_asset_type(session, "PFD", "Preferred Stock")
    mutual_fund_asset_type = await get_or_create_asset_type(session, "MF", "Mutual Fund")
    
    nyse_exchange = await get_or_create_exchange(session, "NYSE", "New York Stock Exchange")
    nasdaq_exchange = await get_or_create_exchange(session, "NASDAQ", "NASDAQ Stock Market")
    tsx_exchange = await get_or_create_exchange(session, "TSX", "Toronto Stock Exchange", "Canada")
    
    # Common sectors
    tech_sector = await get_or_create_sector(session, "Technology", "45")
    finance_sector = await get_or_create_sector(session, "Financials", "40")
    healthcare_sector = await get_or_create_sector(session, "Health Care", "35")
    
    # Detailed sector mapping for major index sectors
    consumer_discretionary_sector = await get_or_create_sector(session, "Consumer Discretionary", "25")
    consumer_staples_sector = await get_or_create_sector(session, "Consumer Staples", "30")
    communication_services_sector = await get_or_create_sector(session, "Communication Services", "50")
    industrials_sector = await get_or_create_sector(session, "Industrials", "20")
    energy_sector = await get_or_create_sector(session, "Energy", "10")
    utilities_sector = await get_or_create_sector(session, "Utilities", "55")
    real_estate_sector = await get_or_create_sector(session, "Real Estate", "60")
    materials_sector = await get_or_create_sector(session, "Materials", "15")

    sector_map = {
        'Technology': tech_sector.id,
        'Information Technology': tech_sector.id,
        'Financials': finance_sector.id,
        'Financial Services': finance_sector.id,
        'Health Care': healthcare_sector.id,
        'Healthcare': healthcare_sector.id,
        'Consumer Discretionary': consumer_discretionary_sector.id,
        'Consumer Staples': consumer_staples_sector.id,
        'Communication Services': communication_services_sector.id,
        'Industrials': industrials_sector.id,
        'Energy': energy_sector.id,
        'Utilities': utilities_sector.id,
        'Real Estate': real_estate_sector.id,
        'Materials': materials_sector.id,
        # Add more mappings as needed for completeness
    }
    
    # Fetch all ticker lists
    all_tickers = []
    sp500 = fetch_sp500_tickers()
    nasdaq = fetch_nasdaq100_tickers()
    dow = fetch_dow_jones_tickers()
    tsx = fetch_tsx_tickers()
    
    # If all are empty, forcibly use the fallback from fetch_sp500_tickers
    if not sp500 and not nasdaq and not dow and not tsx:
        logger.info("All ticker fetches failed, using fallback S&P 500 list only.")
        all_tickers = fetch_sp500_tickers()
    else:
        all_tickers.extend(sp500)
        all_tickers.extend(nasdaq)
        all_tickers.extend(dow)
        all_tickers.extend(tsx)
    
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
            # Determine exchange (enhanced logic)
            if any(x in info['index'] for x in ['NASDAQ', 'Tech']):
                exchange_id = nasdaq_exchange.id
            elif any(x in info['index'] for x in ['TSX']):
                exchange_id = tsx_exchange.id
            else:
                exchange_id = nyse_exchange.id
            
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