"""
Congressional data ingestion system for CapitolScope.

This module provides comprehensive data ingestion capabilities for congressional trade data
with enhanced ticker extraction, security enrichment, trade backfill, and quality reporting.
"""

import asyncio
import csv
import re
import json
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_

from core.logging import get_logger
from core.config import settings
from domains.congressional.models import CongressMember, CongressionalTrade
from domains.congressional.schemas import CongressMemberCreate, CongressionalTradeCreate
from domains.congressional.crud import CongressMemberRepository, CongressionalTradeRepository
from domains.securities.models import Security, AssetType, Sector, Exchange
from domains.securities.schemas import SecurityCreate
from domains.securities.crud import SecurityCRUD

logger = get_logger(__name__)


# ============================================================================
# DATA QUALITY TRACKING
# ============================================================================

@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics tracking."""
    
    # Import counts
    total_rows_processed: int = 0
    csv_files_processed: int = 0
    years_processed: int = 0
    
    # Member counts
    total_members: int = 0
    members_created: int = 0
    members_updated: int = 0
    members_with_trades: int = 0
    
    # Trade counts
    total_trades: int = 0
    trades_created: int = 0
    trades_updated: int = 0
    trades_with_security: int = 0
    trades_without_security: int = 0
    
    # Ticker extraction
    tickers_extracted: int = 0
    tickers_from_ticker_field: int = 0
    tickers_from_asset_description: int = 0
    tickers_from_fuzzy_matching: int = 0
    tickers_failed_extraction: int = 0
    
    # Security enrichment
    securities_enriched: int = 0
    securities_with_missing_exchange: int = 0
    securities_with_missing_sector: int = 0
    securities_with_missing_asset_type: int = 0
    
    # Trade backfill
    trades_backfilled: int = 0
    trades_still_unlinked: int = 0
    
    # Error tracking
    failed_trades: int = 0
    parsing_errors: int = 0
    validation_errors: int = 0
    
    # Collections for detailed analysis
    unmatched_tickers: Counter = field(default_factory=Counter)
    unmatched_assets: Counter = field(default_factory=Counter)
    common_parsing_errors: Counter = field(default_factory=Counter)
    ticker_extraction_patterns: Counter = field(default_factory=Counter)
    
    # Performance tracking
    processing_time: float = 0.0
    avg_time_per_row: float = 0.0


@dataclass
class ManualReviewItem:
    """Item that needs manual review."""
    
    category: str  # 'ticker', 'asset', 'trade', 'security'
    description: str
    raw_data: Dict[str, Any]
    suggested_fix: Optional[str] = None
    confidence: float = 0.0
    frequency: int = 1


# ============================================================================
# TICKER EXTRACTION AND NORMALIZATION
# ============================================================================

class TickerExtractor:
    """Enhanced ticker extraction with multiple fallback strategies."""
    
    def __init__(self):
        self.ticker_patterns = [
            # Standard ticker in parentheses
            r'\(([A-Z]{1,5})\)',
            # Ticker after dash
            r'-\s*([A-Z]{1,5})(?:\s|$)',
            # Ticker at end of string
            r'([A-Z]{1,5})$',
            # Ticker with Class designation
            r'([A-Z]{1,5})\s+Class\s+[A-Z]',
            # Ticker in quotes
            r'"([A-Z]{1,5})"',
            # Ticker after "Symbol:"
            r'Symbol:\s*([A-Z]{1,5})',
        ]
        
        # Common replacements for normalization
        self.ticker_replacements = {
            'GOOGL': 'GOOGL',  # Keep as is
            'GOOG': 'GOOGL',   # Normalize to GOOGL
            'BRK.A': 'BRK-A',  # Dot to dash
            'BRK.B': 'BRK-B',  # Dot to dash
        }
        
        # Load company name to ticker mapping
        self.company_ticker_mapping = self._load_company_ticker_mapping()
    
    def _load_company_ticker_mapping(self) -> Dict[str, str]:
        """Load company name to ticker mapping."""
        # This could be loaded from a CSV file or database
        # For now, using a basic mapping
        return {
            'APPLE INC': 'AAPL',
            'MICROSOFT CORPORATION': 'MSFT',
            'AMAZON.COM INC': 'AMZN',
            'ALPHABET INC': 'GOOGL',
            'TESLA INC': 'TSLA',
            'FACEBOOK INC': 'META',
            'BERKSHIRE HATHAWAY INC': 'BRK-B',
            'JOHNSON & JOHNSON': 'JNJ',
            'JPMORGAN CHASE & CO': 'JPM',
            'VISA INC': 'V',
            'PROCTER & GAMBLE': 'PG',
            'NVIDIA CORPORATION': 'NVDA',
            'MASTERCARD INCORPORATED': 'MA',
            'WALT DISNEY COMPANY': 'DIS',
            'NETFLIX INC': 'NFLX',
            'PAYPAL HOLDINGS INC': 'PYPL',
            'ADOBE INC': 'ADBE',
            'SALESFORCE.COM INC': 'CRM',
            'INTEL CORPORATION': 'INTC',
            'CISCO SYSTEMS INC': 'CSCO',
            'COCA-COLA COMPANY': 'KO',
            'PFIZER INC': 'PFE',
            'STARBUCKS CORPORATION': 'SBUX',
            'EXXON MOBIL CORPORATION': 'XOM',
            'CHEVRON CORPORATION': 'CVX',
            'GOLDMAN SACHS GROUP INC': 'GS',
            'MORGAN STANLEY': 'MS',
            'BANK OF AMERICA CORP': 'BAC',
            'WELLS FARGO & COMPANY': 'WFC',
            'CITIGROUP INC': 'C',
            'AMERICAN EXPRESS COMPANY': 'AXP',
            'UNITED HEALTHCARE CORP': 'UNH',
            'HOME DEPOT INC': 'HD',
            'MCDONALD\'S CORPORATION': 'MCD',
            'BOEING COMPANY': 'BA',
            'CATERPILLAR INC': 'CAT',
            'GENERAL ELECTRIC COMPANY': 'GE',
            'FORD MOTOR COMPANY': 'F',
            'GENERAL MOTORS COMPANY': 'GM',
            'WALMART INC': 'WMT',
            'TARGET CORPORATION': 'TGT',
            'COSTCO WHOLESALE CORPORATION': 'COST',
            'VERIZON COMMUNICATIONS': 'VZ',
            'AT&T INC': 'T',
            'COMCAST CORPORATION': 'CMCSA',
            'ABBVIE INC': 'ABBV',
            'MERCK & CO INC': 'MRK',
            'BRISTOL-MYERS SQUIBB': 'BMY',
            'ELI LILLY AND COMPANY': 'LLY',
            'ROCHE HOLDINGS AG': 'RHHBY',
            'NESTLE SA': 'NSRGY',
            'UNILEVER PLC': 'UL',
            'ASML HOLDING NV': 'ASML',
            'TAIWAN SEMICONDUCTOR': 'TSM',
            'ALIBABA GROUP HOLDING': 'BABA',
            'TENCENT HOLDINGS': 'TCEHY',
            'SAMSUNG ELECTRONICS': 'SSNLF',
            'SPDR S&P 500 ETF': 'SPY',
            'ISHARES CORE S&P 500': 'IVV',
            'VANGUARD S&P 500 ETF': 'VOO',
            'INVESCO QQQ TRUST': 'QQQ',
            'ISHARES MSCI EMERGING': 'EEM',
            'VANGUARD TOTAL STOCK': 'VTI',
            'ISHARES RUSSELL 2000': 'IWM',
            'SPDR GOLD TRUST': 'GLD',
            'ISHARES GOLD TRUST': 'IAU',
            'UNITED STATES OIL FUND': 'USO',
            'BITCOIN TRUST': 'GBTC',
            'BLACKROCK FEDERAL FUND': 'CS',  # Common cash sweep
            'BLACKROCK LIQ FDS': 'CS',
            'BLF FEDFUND': 'CS',
            'TREASURY BILL': 'CASH',
            'US TREASURY': 'CASH',
            'MONEY MARKET': 'CASH',
            'CASH SWEEP': 'CS',
        }
    
    def extract_ticker(self, ticker_field: str, asset_description: str) -> Tuple[Optional[str], str, float]:
        """
        Extract ticker with multiple fallback strategies.
        
        Returns:
            Tuple of (ticker, source, confidence)
        """
        # Strategy 1: Use ticker field if valid
        if ticker_field and self._is_valid_ticker(ticker_field):
            normalized = self._normalize_ticker(ticker_field)
            return normalized, "ticker_field", 0.9
        
        # Strategy 2: Extract from asset description using patterns
        if asset_description:
            for pattern in self.ticker_patterns:
                match = re.search(pattern, asset_description.upper())
                if match:
                    ticker = match.group(1)
                    if self._is_valid_ticker(ticker):
                        normalized = self._normalize_ticker(ticker)
                        return normalized, f"pattern_{pattern}", 0.8
        
        # Strategy 3: Fuzzy match company name
        if asset_description:
            fuzzy_ticker = self._fuzzy_match_company_name(asset_description)
            if fuzzy_ticker:
                return fuzzy_ticker, "fuzzy_match", 0.7
        
        # Strategy 4: Extract potential ticker from mixed content
        if asset_description:
            potential_ticker = self._extract_from_mixed_content(asset_description)
            if potential_ticker:
                return potential_ticker, "mixed_content", 0.6
        
        return None, "failed", 0.0
    
    def _is_valid_ticker(self, ticker: str) -> bool:
        """Check if a ticker is valid."""
        if not ticker:
            return False
        
        # Clean up ticker
        ticker = ticker.strip().upper()
        
        # Basic validation
        if len(ticker) < 1 or len(ticker) > 5:
            return False
        
        # Should contain only letters and allowed characters
        if not re.match(r'^[A-Z][A-Z0-9\-\.]*$', ticker):
            return False
        
        # Exclude common non-tickers
        excluded = {
            'P', 'S', 'E',  # Transaction types
            'SP', 'JT', 'DC', 'C',  # Owner types
            'NEW', 'OLD', 'N/A', 'TBD',  # Status indicators
            'USD', 'EUR', 'GBP',  # Currencies
            'CASH', 'BOND', 'STOCK',  # Generic terms
            'DATE', 'TIME', 'AMOUNT',  # Field names
            'YES', 'NO', 'TRUE', 'FALSE',  # Boolean values
        }
        
        return ticker not in excluded
    
    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker symbol."""
        ticker = ticker.strip().upper()
        
        # Replace dots with dashes
        ticker = ticker.replace('.', '-')
        
        # Apply custom replacements
        if ticker in self.ticker_replacements:
            ticker = self.ticker_replacements[ticker]
        
        return ticker
    
    def _fuzzy_match_company_name(self, asset_description: str) -> Optional[str]:
        """Fuzzy match company name to ticker."""
        asset_upper = asset_description.upper()
        
        # Direct mapping lookup
        for company_name, ticker in self.company_ticker_mapping.items():
            if company_name in asset_upper:
                return ticker
        
        # Partial matching for key words
        for company_name, ticker in self.company_ticker_mapping.items():
            # Split company name and check for key words
            key_words = [word for word in company_name.split() 
                        if len(word) > 3 and word not in {'INC', 'CORP', 'COMPANY', 'GROUP', 'HOLDINGS'}]
            
            if key_words and all(word in asset_upper for word in key_words):
                return ticker
        
        return None
    
    def _extract_from_mixed_content(self, content: str) -> Optional[str]:
        """Extract ticker from mixed content with transaction info."""
        # Look for patterns like "AAPL P" or "MSFT S"
        match = re.search(r'([A-Z]{1,5})\s+[PS](?:\s|$)', content.upper())
        if match:
            ticker = match.group(1)
            if self._is_valid_ticker(ticker):
                return self._normalize_ticker(ticker)
        
        # Look for tickers separated by spaces
        words = content.upper().split()
        for word in words:
            if self._is_valid_ticker(word):
                return self._normalize_ticker(word)
        
        return None


# ============================================================================
# SECURITY ENRICHMENT
# ============================================================================

class SecurityEnricher:
    """Enrich securities with exchange, sector, and asset type information."""
    
    def __init__(self, db: Session):
        self.db = db
        self.security_crud = SecurityCRUD(db)
        
        # Load default exchanges, sectors, and asset types
        self._ensure_default_data()
    
    def _ensure_default_data(self):
        """Ensure default exchanges, sectors, and asset types exist."""
        # Create default exchanges
        default_exchanges = [
            {'code': 'NYSE', 'name': 'New York Stock Exchange', 'country': 'USA', 'timezone': 'America/New_York'},
            {'code': 'NASDAQ', 'name': 'NASDAQ Global Select Market', 'country': 'USA', 'timezone': 'America/New_York'},
            {'code': 'AMEX', 'name': 'American Stock Exchange', 'country': 'USA', 'timezone': 'America/New_York'},
            {'code': 'OTC', 'name': 'Over-the-Counter', 'country': 'USA', 'timezone': 'America/New_York'},
            {'code': 'TSE', 'name': 'Tokyo Stock Exchange', 'country': 'JPN', 'timezone': 'Asia/Tokyo'},
            {'code': 'LSE', 'name': 'London Stock Exchange', 'country': 'GBR', 'timezone': 'Europe/London'},
            {'code': 'CASH', 'name': 'Cash/Money Market', 'country': 'USA', 'timezone': 'America/New_York'},
        ]
        
        for exchange_data in default_exchanges:
            existing = self.db.query(Exchange).filter_by(code=exchange_data['code']).first()
            if not existing:
                exchange = Exchange(**exchange_data)
                self.db.add(exchange)
        
        # Create default asset types
        default_asset_types = [
            {'code': 'STK', 'name': 'Common Stock', 'category': 'equity', 'risk_level': 3},
            {'code': 'ETF', 'name': 'Exchange Traded Fund', 'category': 'equity', 'risk_level': 2},
            {'code': 'BOND', 'name': 'Bond', 'category': 'fixed_income', 'risk_level': 1},
            {'code': 'OPT', 'name': 'Option', 'category': 'derivative', 'risk_level': 5},
            {'code': 'CASH', 'name': 'Cash/Money Market', 'category': 'cash', 'risk_level': 1},
            {'code': 'REIT', 'name': 'Real Estate Investment Trust', 'category': 'equity', 'risk_level': 3},
            {'code': 'ADR', 'name': 'American Depositary Receipt', 'category': 'equity', 'risk_level': 4},
        ]
        
        for asset_type_data in default_asset_types:
            existing = self.db.query(AssetType).filter_by(code=asset_type_data['code']).first()
            if not existing:
                asset_type = AssetType(**asset_type_data)
                self.db.add(asset_type)
        
        # Create default sectors
        default_sectors = [
            {'name': 'Technology', 'gics_code': '45'},
            {'name': 'Healthcare', 'gics_code': '35'},
            {'name': 'Financial Services', 'gics_code': '40'},
            {'name': 'Consumer Discretionary', 'gics_code': '25'},
            {'name': 'Communication Services', 'gics_code': '50'},
            {'name': 'Industrials', 'gics_code': '20'},
            {'name': 'Consumer Staples', 'gics_code': '30'},
            {'name': 'Energy', 'gics_code': '10'},
            {'name': 'Utilities', 'gics_code': '55'},
            {'name': 'Materials', 'gics_code': '15'},
            {'name': 'Real Estate', 'gics_code': '60'},
            {'name': 'Government/Municipal', 'gics_code': '90'},
            {'name': 'Cash/Money Market', 'gics_code': '95'},
        ]
        
        for sector_data in default_sectors:
            existing = self.db.query(Sector).filter_by(name=sector_data['name']).first()
            if not existing:
                sector = Sector(**sector_data)
                self.db.add(sector)
        
        self.db.commit()
    
    def enrich_security(self, security: Security) -> bool:
        """
        Enrich a security with exchange, sector, and asset type.
        
        Returns:
            True if enrichment was successful
        """
        enriched = False
        
        # Enrich exchange
        if not security.exchange_id:
            exchange = self._determine_exchange(security.ticker)
            if exchange:
                security.exchange_id = exchange.id
                enriched = True
        
        # Enrich asset type
        if not security.asset_type_id:
            asset_type = self._determine_asset_type(security.ticker, security.name)
            if asset_type:
                security.asset_type_id = asset_type.id
                enriched = True
        
        # Enrich sector
        if not security.sector_id:
            sector = self._determine_sector(security.ticker, security.name)
            if sector:
                security.sector_id = sector.id
                enriched = True
        
        return enriched
    
    def _determine_exchange(self, ticker: str) -> Optional[Exchange]:
        """Determine exchange based on ticker patterns."""
        # Common patterns
        if ticker in ['CS', 'CASH']:
            return self.db.query(Exchange).filter_by(code='CASH').first()
        
        # Foreign tickers
        if ticker.endswith('F'):  # Foreign ordinary shares
            return self.db.query(Exchange).filter_by(code='OTC').first()
        
        # ETF patterns
        if ticker.startswith(('SPY', 'QQQ', 'IVV', 'VOO', 'VTI', 'IWM', 'GLD', 'IAU')):
            return self.db.query(Exchange).filter_by(code='NYSE').first()
        
        # Default to NYSE for most US stocks
        return self.db.query(Exchange).filter_by(code='NYSE').first()
    
    def _determine_asset_type(self, ticker: str, name: str) -> Optional[AssetType]:
        """Determine asset type based on ticker and name."""
        name_upper = name.upper() if name else ''
        
        # Cash/Money Market
        if ticker in ['CS', 'CASH'] or 'CASH' in name_upper or 'MONEY MARKET' in name_upper:
            return self.db.query(AssetType).filter_by(code='CASH').first()
        
        # Bonds
        if 'BOND' in name_upper or 'TREASURY' in name_upper or 'MUNICIPAL' in name_upper:
            return self.db.query(AssetType).filter_by(code='BOND').first()
        
        # ETFs
        if 'ETF' in name_upper or 'FUND' in name_upper or 'TRUST' in name_upper:
            if ticker.startswith(('SPY', 'QQQ', 'IVV', 'VOO', 'VTI', 'IWM', 'GLD', 'IAU')):
                return self.db.query(AssetType).filter_by(code='ETF').first()
        
        # REITs
        if 'REIT' in name_upper or 'REAL ESTATE' in name_upper:
            return self.db.query(AssetType).filter_by(code='REIT').first()
        
        # ADRs
        if 'ADR' in name_upper or 'DEPOSITARY' in name_upper:
            return self.db.query(AssetType).filter_by(code='ADR').first()
        
        # Default to stock
        return self.db.query(AssetType).filter_by(code='STK').first()
    
    def _determine_sector(self, ticker: str, name: str) -> Optional[Sector]:
        """Determine sector based on ticker and name."""
        name_upper = name.upper() if name else ''
        
        # Technology
        tech_keywords = ['MICROSOFT', 'APPLE', 'GOOGLE', 'ALPHABET', 'AMAZON', 'FACEBOOK', 'META', 
                        'NETFLIX', 'TESLA', 'NVIDIA', 'INTEL', 'CISCO', 'ORACLE', 'ADOBE', 'SALESFORCE']
        if any(keyword in name_upper for keyword in tech_keywords):
            return self.db.query(Sector).filter_by(name='Technology').first()
        
        # Healthcare
        healthcare_keywords = ['PFIZER', 'JOHNSON', 'MERCK', 'ABBVIE', 'BRISTOL', 'LILLY', 'GILEAD', 'AMGEN']
        if any(keyword in name_upper for keyword in healthcare_keywords):
            return self.db.query(Sector).filter_by(name='Healthcare').first()
        
        # Financial Services
        financial_keywords = ['JPMORGAN', 'BANK', 'GOLDMAN', 'MORGAN', 'WELLS FARGO', 'CITIGROUP', 
                             'AMERICAN EXPRESS', 'VISA', 'MASTERCARD', 'PAYPAL']
        if any(keyword in name_upper for keyword in financial_keywords):
            return self.db.query(Sector).filter_by(name='Financial Services').first()
        
        # Consumer Discretionary
        consumer_disc_keywords = ['DISNEY', 'NIKE', 'STARBUCKS', 'MCDONALD', 'HOME DEPOT', 'WALMART', 'TARGET']
        if any(keyword in name_upper for keyword in consumer_disc_keywords):
            return self.db.query(Sector).filter_by(name='Consumer Discretionary').first()
        
        # Energy
        energy_keywords = ['EXXON', 'CHEVRON', 'CONOCOPHILLIPS', 'SCHLUMBERGER', 'KINDER MORGAN']
        if any(keyword in name_upper for keyword in energy_keywords):
            return self.db.query(Sector).filter_by(name='Energy').first()
        
        # Cash/Government
        if ticker in ['CS', 'CASH'] or 'TREASURY' in name_upper or 'MUNICIPAL' in name_upper:
            return self.db.query(Sector).filter_by(name='Cash/Money Market').first()
        
        # Default based on asset type
        return self.db.query(Sector).filter_by(name='Financial Services').first()


# ============================================================================
# TRADE BACKFILL
# ============================================================================

class TradeBackfiller:
    """Backfill trades with security IDs after enrichment."""
    
    def __init__(self, db: Session):
        self.db = db
        self.security_crud = SecurityCRUD(db)
    
    def backfill_trades(self) -> Dict[str, int]:
        """
        Backfill trades that don't have security_id set.
        
        Returns:
            Dictionary with backfill statistics
        """
        stats = {
            'trades_processed': 0,
            'trades_linked': 0,
            'trades_still_unlinked': 0,
        }
        
        # Get trades without security_id
        unlinked_trades = self.db.query(CongressionalTrade).filter(
            CongressionalTrade.security_id.is_(None)
        ).all()
        
        stats['trades_processed'] = len(unlinked_trades)
        
        for trade in unlinked_trades:
            security = self._find_security_for_trade(trade)
            if security:
                trade.security_id = security.id
                stats['trades_linked'] += 1
            else:
                stats['trades_still_unlinked'] += 1
        
        self.db.commit()
        return stats
    
    def _find_security_for_trade(self, trade: CongressionalTrade) -> Optional[Security]:
        """Find security for a trade based on ticker or asset name."""
        # Try ticker first
        if trade.ticker:
            security = self.security_crud.get_by_ticker(trade.ticker)
            if security:
                return security
        
        # Try asset name matching
        if trade.asset_name:
            security = self._find_by_asset_name(trade.asset_name)
            if security:
                return security
        
        # Try raw asset description
        if trade.raw_asset_description:
            security = self._find_by_asset_description(trade.raw_asset_description)
            if security:
                return security
        
        return None
    
    def _find_by_asset_name(self, asset_name: str) -> Optional[Security]:
        """Find security by asset name."""
        # Exact match
        security = self.db.query(Security).filter(
            Security.name.ilike(f'%{asset_name}%')
        ).first()
        
        return security
    
    def _find_by_asset_description(self, description: str) -> Optional[Security]:
        """Find security by asset description."""
        # Extract potential ticker from description
        ticker_extractor = TickerExtractor()
        ticker, _, confidence = ticker_extractor.extract_ticker('', description)
        
        if ticker and confidence > 0.5:
            return self.security_crud.get_by_ticker(ticker)
        
        return None


# ============================================================================
# MAIN INGESTION CLASS
# ============================================================================

class CongressionalDataIngester:
    """Main congressional data ingestion class."""
    
    def __init__(self, db: Session):
        self.db = db
        self.member_repo = CongressMemberRepository(db)
        self.trade_repo = CongressionalTradeRepository(db)
        self.security_crud = SecurityCRUD(db)
        
        # Initialize components
        self.ticker_extractor = TickerExtractor()
        self.security_enricher = SecurityEnricher(db)
        self.trade_backfiller = TradeBackfiller(db)
        
        # Metrics tracking
        self.metrics = DataQualityMetrics()
        self.manual_review_items: List[ManualReviewItem] = []
        
        # Member cache
        self.member_cache: Dict[str, CongressMember] = {}
        
        # Processing options
        self.auto_create_securities = True
        self.auto_enrich_securities = True
        self.skip_invalid_trades = True
        self.batch_size = 1000
    
    def import_congressional_data_from_csvs_sync(self, csv_directory: str) -> Dict[str, Any]:
        """
        Import congressional data from CSV files synchronously.
        
        Args:
            csv_directory: Directory containing CSV files
            
        Returns:
            Dictionary with import statistics
        """
        start_time = datetime.now()
        
        try:
            csv_dir = Path(csv_directory)
            if not csv_dir.exists():
                raise ValueError(f"CSV directory does not exist: {csv_directory}")
            
            # Get all CSV files
            csv_files = list(csv_dir.glob("*.csv"))
            if not csv_files:
                raise ValueError(f"No CSV files found in {csv_directory}")
            
            logger.info(f"Found {len(csv_files)} CSV files to process")
            
            # Process each CSV file
            for csv_file in csv_files:
                logger.info(f"Processing {csv_file.name}...")
                self._process_csv_file(csv_file)
                self.metrics.csv_files_processed += 1
            
            # Enrich securities if enabled
            if self.auto_enrich_securities:
                logger.info("Enriching securities...")
                self._enrich_securities()
            
            # Backfill trades
            logger.info("Backfilling trades...")
            backfill_stats = self.trade_backfiller.backfill_trades()
            self.metrics.trades_backfilled = backfill_stats['trades_linked']
            self.metrics.trades_still_unlinked = backfill_stats['trades_still_unlinked']
            
            # Calculate final metrics
            self.metrics.processing_time = (datetime.now() - start_time).total_seconds()
            if self.metrics.total_rows_processed > 0:
                self.metrics.avg_time_per_row = self.metrics.processing_time / self.metrics.total_rows_processed
            
            # Generate manual review items
            self._generate_manual_review_items()
            
            # Save manual review CSV
            self._save_manual_review_csv()
            
            logger.info("Congressional data import completed successfully")
            return self._get_import_results()
            
        except Exception as e:
            logger.error(f"Error importing congressional data: {e}")
            raise
    
    def _process_csv_file(self, csv_file: Path):
        """Process a single CSV file."""
        try:
            if not HAS_PANDAS:
                # Use CSV module fallback
                self._process_csv_file_basic(csv_file)
                return
            
            # Read CSV file with pandas
            df = pd.read_csv(csv_file)
            logger.info(f"Loaded {len(df)} rows from {csv_file.name}")
            
            # Extract year from filename
            year_match = re.search(r'(\d{4})', csv_file.name)
            if year_match:
                year = int(year_match.group(1))
                self.metrics.years_processed = max(self.metrics.years_processed, year)
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    self._process_trade_row(row)
                    self.metrics.total_rows_processed += 1
                    
                    # Commit in batches
                    if self.metrics.total_rows_processed % self.batch_size == 0:
                        self.db.commit()
                        logger.info(f"Processed {self.metrics.total_rows_processed} rows...")
                        
                except Exception as e:
                    self.metrics.parsing_errors += 1
                    self.metrics.common_parsing_errors[str(e)] += 1
                    logger.warning(f"Error processing row {index}: {e}")
                    
                    if not self.skip_invalid_trades:
                        raise
            
            # Final commit for this file
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error processing CSV file {csv_file}: {e}")
            raise
    
    def _process_csv_file_basic(self, csv_file: Path):
        """Process a single CSV file using basic CSV reader."""
        try:
            import csv
            
            # Extract year from filename
            year_match = re.search(r'(\d{4})', csv_file.name)
            if year_match:
                year = int(year_match.group(1))
                self.metrics.years_processed = max(self.metrics.years_processed, year)
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                logger.info(f"Loaded {len(rows)} rows from {csv_file.name}")
                
                                 # Process each row
                for index, row in enumerate(rows):
                    try:
                        self._process_trade_row(row)
                        self.metrics.total_rows_processed += 1
                        
                        # Commit in batches
                        if self.metrics.total_rows_processed % self.batch_size == 0:
                            self.db.commit()
                            logger.info(f"Processed {self.metrics.total_rows_processed} rows...")
                            
                    except Exception as e:
                        self.metrics.parsing_errors += 1
                        self.metrics.common_parsing_errors[str(e)] += 1
                        logger.warning(f"Error processing row {index}: {e}")
                        
                        if not self.skip_invalid_trades:
                            raise
                
                # Final commit for this file
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error processing CSV file {csv_file}: {e}")
            raise
    
    def _process_trade_row(self, row):
        """Process a single trade row."""
        try:
            # Extract basic information
            member_name = str(row.get('Member', '')).strip()
            ticker_field = str(row.get('Ticker', '')).strip()
            asset_description = str(row.get('Asset', '')).strip()
            
            if not member_name or not asset_description:
                raise ValueError("Missing required fields: Member or Asset")
            
            # Get or create member
            member = self._get_or_create_member(member_name)
            
            # Extract ticker
            ticker, ticker_source, ticker_confidence = self.ticker_extractor.extract_ticker(
                ticker_field, asset_description
            )
            
            # Update ticker extraction stats
            if ticker:
                self.metrics.tickers_extracted += 1
                if ticker_source == 'ticker_field':
                    self.metrics.tickers_from_ticker_field += 1
                elif ticker_source.startswith('pattern'):
                    self.metrics.tickers_from_asset_description += 1
                elif ticker_source == 'fuzzy_match':
                    self.metrics.tickers_from_fuzzy_matching += 1
                
                self.metrics.ticker_extraction_patterns[ticker_source] += 1
            else:
                self.metrics.tickers_failed_extraction += 1
                self.metrics.unmatched_tickers[ticker_field] += 1
                self.metrics.unmatched_assets[asset_description] += 1
            
            # Get or create security
            security = None
            if ticker:
                security = self._get_or_create_security(ticker, asset_description)
            
            # Parse trade data
            trade_data = self._parse_trade_data(row, member, security, ticker, ticker_confidence)
            
            # Create trade
            trade = CongressionalTrade(**trade_data)
            self.db.add(trade)
            self.metrics.trades_created += 1
            
            if security:
                self.metrics.trades_with_security += 1
            else:
                self.metrics.trades_without_security += 1
            
        except Exception as e:
            self.metrics.failed_trades += 1
            raise
    
    def _get_or_create_member(self, member_name: str) -> CongressMember:
        """Get or create a congress member."""
        if member_name in self.member_cache:
            return self.member_cache[member_name]
        
        # Try to find existing member
        member = self.db.query(CongressMember).filter(
            CongressMember.last_name.ilike(f'%{member_name}%')
        ).first()
        
        if not member:
            # Create new member
            member = CongressMember(
                first_name='',
                last_name=member_name,
                full_name=member_name,
                party='Unknown',
                state='Unknown',
                chamber='Unknown',
                is_active=True
            )
            self.db.add(member)
            self.db.flush()  # Get ID
            self.metrics.members_created += 1
        
        self.member_cache[member_name] = member
        return member
    
    def _get_or_create_security(self, ticker: str, asset_description: str) -> Optional[Security]:
        """Get or create a security."""
        # Try to find existing security
        security = self.security_crud.get_by_ticker(ticker)
        
        if not security and self.auto_create_securities:
            # Create new security
            security = Security(
                ticker=ticker,
                name=asset_description[:200],  # Truncate to fit
                is_active=True
            )
            self.db.add(security)
            self.db.flush()  # Get ID
            
            # Enrich if enabled
            if self.auto_enrich_securities:
                self.security_enricher.enrich_security(security)
        
        return security
    
    def _parse_trade_data(self, row: pd.Series, member: CongressMember, 
                         security: Optional[Security], ticker: Optional[str], 
                         ticker_confidence: float) -> Dict[str, Any]:
        """Parse trade data from CSV row."""
        # Parse dates
        transaction_date = self._parse_date(row.get('Transaction Date'))
        notification_date = self._parse_date(row.get('Notification Date'))
        
        # Parse amount
        amount_str = str(row.get('Amount', '')).strip()
        amount_min, amount_max = self._parse_amount_range(amount_str)
        
        # Parse transaction type
        transaction_type = str(row.get('Transaction Type', '')).strip()
        if transaction_type not in ['P', 'S', 'E']:
            transaction_type = 'P'  # Default to Purchase
        
        # Parse owner
        owner = str(row.get('Owner', '')).strip()
        if owner not in ['SP', 'JT', 'DC', 'C']:
            owner = 'C'  # Default to Self
        
        return {
            'member_id': member.id,
            'security_id': security.id if security else None,
            'doc_id': str(row.get('DocID', '')).strip(),
            'owner': owner,
            'raw_asset_description': str(row.get('Asset', '')).strip(),
            'ticker': ticker,
            'asset_name': str(row.get('Asset', '')).strip()[:300],
            'transaction_type': transaction_type,
            'transaction_date': transaction_date,
            'notification_date': notification_date,
            'amount_min': amount_min,
            'amount_max': amount_max,
            'filing_status': str(row.get('Filing Status', 'N')).strip(),
            'comment': str(row.get('Description', '')).strip(),
            'ticker_confidence': Decimal(str(ticker_confidence)),
            'parsed_successfully': True,
        }
    
    def _parse_date(self, date_str: Any) -> Optional[date]:
        """Parse date from various formats."""
        if HAS_PANDAS and pd is not None and pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        if not date_str or date_str == '-':
            return None
        
        # Try different date formats
        formats = [
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _parse_amount_range(self, amount_str: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse amount range from string."""
        if not amount_str or amount_str == '-':
            return None, None
        
        # Remove currency symbols and commas
        amount_str = re.sub(r'[,$]', '', amount_str)
        
        # Handle range format like "$1,001 - $15,000"
        if '-' in amount_str:
            parts = amount_str.split('-')
            if len(parts) == 2:
                try:
                    min_amount = int(float(parts[0].strip()) * 100)  # Convert to cents
                    max_amount = int(float(parts[1].strip()) * 100)
                    return min_amount, max_amount
                except ValueError:
                    pass
        
        # Handle single amount
        try:
            amount = int(float(amount_str) * 100)  # Convert to cents
            return amount, amount
        except ValueError:
            pass
        
        return None, None
    
    def _enrich_securities(self):
        """Enrich all securities with missing information."""
        securities = self.db.query(Security).filter(
            or_(
                Security.exchange_id.is_(None),
                Security.sector_id.is_(None),
                Security.asset_type_id.is_(None)
            )
        ).all()
        
        for security in securities:
            if self.security_enricher.enrich_security(security):
                self.metrics.securities_enriched += 1
        
        self.db.commit()
    
    def _generate_manual_review_items(self):
        """Generate items for manual review."""
        # Top unmatched tickers
        for ticker, count in self.metrics.unmatched_tickers.most_common(20):
            self.manual_review_items.append(ManualReviewItem(
                category='ticker',
                description=f'Unmatched ticker: {ticker}',
                raw_data={'ticker': ticker, 'count': count},
                suggested_fix=f'Review and add mapping for {ticker}'
            ))
        
        # Top unmatched assets
        for asset, count in self.metrics.unmatched_assets.most_common(20):
            self.manual_review_items.append(ManualReviewItem(
                category='asset',
                description=f'Unmatched asset: {asset}',
                raw_data={'asset': asset, 'count': count},
                suggested_fix=f'Review and add mapping for {asset}'
            ))
        
        # Securities with missing information
        securities_missing_exchange = self.db.query(Security).filter(
            Security.exchange_id.is_(None)
        ).count()
        
        if securities_missing_exchange > 0:
            self.manual_review_items.append(ManualReviewItem(
                category='security',
                description=f'{securities_missing_exchange} securities missing exchange information',
                raw_data={'count': securities_missing_exchange},
                suggested_fix='Add exchange information for securities'
            ))
    
    def _save_manual_review_csv(self):
        """Save manual review items to CSV."""
        if not self.manual_review_items:
            return
        
        csv_file = Path('manual_review_items.csv')
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Description', 'Raw Data', 'Suggested Fix', 'Confidence'])
            
            for item in self.manual_review_items:
                writer.writerow([
                    item.category,
                    item.description,
                    json.dumps(item.raw_data),
                    item.suggested_fix,
                    item.confidence
                ])
        
        logger.info(f"Saved {len(self.manual_review_items)} manual review items to {csv_file}")
    
    def _get_import_results(self) -> Dict[str, Any]:
        """Get comprehensive import results."""
        return {
            'csv_files_processed': self.metrics.csv_files_processed,
            'years_processed': self.metrics.years_processed,
            'total_rows_processed': self.metrics.total_rows_processed,
            'processing_time': self.metrics.processing_time,
            'avg_time_per_row': self.metrics.avg_time_per_row,
            
            # Members
            'total_members': self.metrics.total_members,
            'members_created': self.metrics.members_created,
            'members_updated': self.metrics.members_updated,
            
            # Trades
            'total_trades': self.metrics.trades_created,
            'trades_with_security': self.metrics.trades_with_security,
            'trades_without_security': self.metrics.trades_without_security,
            'trades_backfilled': self.metrics.trades_backfilled,
            'trades_still_unlinked': self.metrics.trades_still_unlinked,
            
            # Ticker extraction
            'tickers_extracted': self.metrics.tickers_extracted,
            'tickers_from_ticker_field': self.metrics.tickers_from_ticker_field,
            'tickers_from_asset_description': self.metrics.tickers_from_asset_description,
            'tickers_from_fuzzy_matching': self.metrics.tickers_from_fuzzy_matching,
            'tickers_failed_extraction': self.metrics.tickers_failed_extraction,
            
            # Security enrichment
            'securities_enriched': self.metrics.securities_enriched,
            'securities_with_missing_exchange': self.metrics.securities_with_missing_exchange,
            'securities_with_missing_sector': self.metrics.securities_with_missing_sector,
            'securities_with_missing_asset_type': self.metrics.securities_with_missing_asset_type,
            
            # Errors
            'failed_trades': self.metrics.failed_trades,
            'parsing_errors': self.metrics.parsing_errors,
            'validation_errors': self.metrics.validation_errors,
            
            # Manual review
            'manual_review_items_count': len(self.manual_review_items),
            'top_unmatched_tickers': dict(self.metrics.unmatched_tickers.most_common(10)),
            'top_unmatched_assets': dict(self.metrics.unmatched_assets.most_common(10)),
            'ticker_extraction_patterns': dict(self.metrics.ticker_extraction_patterns),
            'common_parsing_errors': dict(self.metrics.common_parsing_errors.most_common(10)),
        }
    
    def enrich_member_data_sync(self) -> Dict[str, Any]:
        """Enrich member data synchronously."""
        # This would typically call external APIs or services
        # For now, just return basic stats
        return {
            'members_enriched': 0,
            'enrichment_errors': 0,
        }