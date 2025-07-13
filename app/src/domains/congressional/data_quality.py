"""
Congressional data quality enhancement module.

This module provides advanced data quality processing for congressional trade data:
- Enhanced ticker extraction with fuzzy matching and pattern recognition
- Amount range standardization with garbage character removal
- Owner field normalization and validation
- Comprehensive quality metrics and reporting
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any, NamedTuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from fuzzywuzzy import fuzz, process
import regex

from core.logging import get_logger
from domains.congressional.schemas import TradeOwner

logger = get_logger(__name__)


class TickerExtractionResult(NamedTuple):
    """Result of ticker extraction process."""
    ticker: Optional[str]
    asset_name: Optional[str]
    asset_type: Optional[str]
    confidence: Decimal
    extraction_method: str
    notes: List[str]


class AmountNormalizationResult(NamedTuple):
    """Result of amount normalization process."""
    amount_min: Optional[int]
    amount_max: Optional[int]
    amount_exact: Optional[int]
    original_amount: str
    normalized_amount: str
    confidence: Decimal
    notes: List[str]


class OwnerNormalizationResult(NamedTuple):
    """Result of owner normalization process."""
    normalized_owner: Optional[TradeOwner]
    original_owner: str
    confidence: Decimal
    notes: List[str]


@dataclass
class QualityReport:
    """Comprehensive quality report for import process."""
    total_records: int
    successful_records: int
    failed_records: int
    processing_errors: int
    ticker_extraction_rate: float
    amount_parsing_rate: float
    owner_normalization_rate: float
    duplicate_count: int
    processing_time: float
    recommendations: List[str]
    
    # Detailed breakdowns
    ticker_extraction_methods: Dict[str, int] = field(default_factory=dict)
    amount_parsing_issues: Dict[str, int] = field(default_factory=dict)
    owner_normalization_issues: Dict[str, int] = field(default_factory=dict)


@dataclass
class ImportStatistics:
    """Statistics tracking for import process."""
    records_processed: int = 0
    records_successful: int = 0
    records_failed: int = 0
    processing_errors: int = 0
    
    # Timing
    import_start_time: Optional[datetime] = None
    import_end_time: Optional[datetime] = None
    
    # Quality metrics
    ticker_extractions: Dict[str, int] = field(default_factory=dict)
    amount_normalizations: Dict[str, int] = field(default_factory=dict)
    owner_normalizations: Dict[str, int] = field(default_factory=dict)
    
    def reset(self):
        """Reset all statistics."""
        self.records_processed = 0
        self.records_successful = 0
        self.records_failed = 0
        self.processing_errors = 0
        self.import_start_time = None
        self.import_end_time = None
        self.ticker_extractions.clear()
        self.amount_normalizations.clear()
        self.owner_normalizations.clear()
    
    @property
    def processing_time_seconds(self) -> float:
        """Calculate processing time in seconds."""
        if self.import_start_time and self.import_end_time:
            return (self.import_end_time - self.import_start_time).total_seconds()
        return 0.0


class DataQualityEnhancer:
    """Enhanced data quality processor for congressional trades."""
    
    def __init__(self):
        self._init_ticker_patterns()
        self._init_amount_patterns()
        self._init_owner_patterns()
        self._init_asset_type_patterns()
        
    def _init_ticker_patterns(self):
        """Initialize ticker extraction patterns."""
        # Enhanced regex patterns for ticker extraction
        self.ticker_patterns = [
            # Standard ticker patterns
            r'\b([A-Z]{1,5})\b',  # 1-5 uppercase letters
            r'\(([A-Z]{1,5})\)',  # Ticker in parentheses
            r'Symbol:\s*([A-Z]{1,5})',  # "Symbol: AAPL"
            r'Ticker:\s*([A-Z]{1,5})',  # "Ticker: AAPL"
            r'NYSE:\s*([A-Z]{1,5})',  # "NYSE: AAPL"
            r'NASDAQ:\s*([A-Z]{1,5})',  # "NASDAQ: AAPL"
            r'AMEX:\s*([A-Z]{1,5})',  # "AMEX: AAPL"
            
            # Complex ticker patterns
            r'\b([A-Z]{1,4}\.[A-Z])\b',  # Berkshire Hathaway style (BRK.A)
            r'\b([A-Z]{1,4}-[A-Z])\b',  # Hyphenated tickers
            r'\b([A-Z]{2,4}\d{1,2})\b',  # Bonds/Options with numbers
            
            # ETF patterns
            r'\b(SPY|VTI|QQQ|IVV|VOO|VEA|VWO|EFA|EEM)\b',  # Common ETFs
            r'\b(XL[A-Z]{1,2})\b',  # Sector ETFs (XLF, XLK, etc.)
            r'\b(I[A-Z]{2,3})\b',  # iShares ETFs
            r'\b(V[A-Z]{2,3})\b',  # Vanguard ETFs
        ]
        
        # Compile patterns for performance
        self.compiled_ticker_patterns = [re.compile(pattern) for pattern in self.ticker_patterns]
        
        # Common false positives to exclude
        self.ticker_blacklist = {
            'INC', 'CORP', 'LLC', 'LTD', 'CO', 'THE', 'AND', 'OR', 'OF', 'IN', 'ON', 'AT',
            'FOR', 'TO', 'BY', 'WITH', 'FROM', 'UP', 'OUT', 'IF', 'SO', 'NO', 'AS', 'DO',
            'BE', 'HE', 'SHE', 'IT', 'WE', 'YOU', 'THEY', 'AM', 'IS', 'ARE', 'WAS', 'WERE',
            'BEEN', 'BEING', 'HAVE', 'HAS', 'HAD', 'WILL', 'WOULD', 'COULD', 'SHOULD',
            'MAY', 'MIGHT', 'MUST', 'CAN', 'CANT', 'WONT', 'DONT', 'DIDNT', 'HAVENT',
            'HASNT', 'HADNT', 'WOULDNT', 'COULDNT', 'SHOULDNT', 'MUSTNT', 'MAYN',
            'JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST',
            'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER', 'JAN', 'FEB', 'MAR', 'APR',
            'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'MONDAY', 'TUESDAY',
            'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY', 'MON', 'TUE',
            'WED', 'THU', 'FRI', 'SAT', 'SUN', 'STOCK', 'SHARE', 'SHARES', 'OPTION',
            'OPTIONS', 'CALL', 'PUT', 'BOND', 'BONDS', 'FUND', 'FUNDS', 'ETF', 'ETFS',
            'MUTUAL', 'INDEX', 'COMMODITY', 'COMMODITIES', 'FUTURE', 'FUTURES',
            'WARRANT', 'WARRANTS', 'RIGHT', 'RIGHTS', 'UNIT', 'UNITS', 'SECURITY',
            'SECURITIES', 'INVESTMENT', 'INVESTMENTS', 'PORTFOLIO', 'PORTFOLIOS',
            'ACCOUNT', 'ACCOUNTS', 'TRUST', 'TRUSTS', 'FUND', 'FUNDS', 'PARTNERSHIP',
            'PARTNERSHIPS', 'VEHICLE', 'VEHICLES', 'HOLDING', 'HOLDINGS', 'ASSET',
            'ASSETS', 'PROPERTY', 'PROPERTIES', 'REAL', 'ESTATE', 'REIT', 'REITS'
        }
        
        # Enhanced company name to ticker mapping
        self.company_ticker_mapping = {
            # Technology companies
            'APPLE': 'AAPL',
            'APPLE INC': 'AAPL',
            'APPLE COMPUTER': 'AAPL',
            'MICROSOFT': 'MSFT',
            'MICROSOFT CORP': 'MSFT',
            'MICROSOFT CORPORATION': 'MSFT',
            'AMAZON': 'AMZN',
            'AMAZON.COM': 'AMZN',
            'AMAZON.COM INC': 'AMZN',
            'AMAZON COM INC': 'AMZN',
            'ALPHABET': 'GOOGL',
            'ALPHABET INC': 'GOOGL',
            'GOOGLE': 'GOOGL',
            'GOOGLE INC': 'GOOGL',
            'TESLA': 'TSLA',
            'TESLA INC': 'TSLA',
            'TESLA MOTORS': 'TSLA',
            'META': 'META',
            'META PLATFORMS': 'META',
            'META PLATFORMS INC': 'META',
            'FACEBOOK': 'META',
            'FACEBOOK INC': 'META',
            'NVIDIA': 'NVDA',
            'NVIDIA CORP': 'NVDA',
            'NVIDIA CORPORATION': 'NVDA',
            'ORACLE': 'ORCL',
            'ORACLE CORP': 'ORCL',
            'ORACLE CORPORATION': 'ORCL',
            'SALESFORCE': 'CRM',
            'SALESFORCE.COM': 'CRM',
            'SALESFORCE INC': 'CRM',
            'NETFLIX': 'NFLX',
            'NETFLIX INC': 'NFLX',
            'ADOBE': 'ADBE',
            'ADOBE INC': 'ADBE',
            'ADOBE SYSTEMS': 'ADBE',
            'PAYPAL': 'PYPL',
            'PAYPAL HOLDINGS': 'PYPL',
            'PAYPAL HOLDINGS INC': 'PYPL',
            'INTEL': 'INTC',
            'INTEL CORP': 'INTC',
            'INTEL CORPORATION': 'INTC',
            'CISCO': 'CSCO',
            'CISCO SYSTEMS': 'CSCO',
            'CISCO SYSTEMS INC': 'CSCO',
            'IBM': 'IBM',
            'IBM CORP': 'IBM',
            'INTERNATIONAL BUSINESS MACHINES': 'IBM',
            
            # Financial services
            'JPMORGAN': 'JPM',
            'JP MORGAN': 'JPM',
            'JPMORGAN CHASE': 'JPM',
            'JPMORGAN CHASE & CO': 'JPM',
            'BANK OF AMERICA': 'BAC',
            'BANK OF AMERICA CORP': 'BAC',
            'BERKSHIRE HATHAWAY': 'BRK.B',
            'BERKSHIRE HATHAWAY INC': 'BRK.B',
            'GOLDMAN SACHS': 'GS',
            'GOLDMAN SACHS GROUP': 'GS',
            'GOLDMAN SACHS GROUP INC': 'GS',
            'MORGAN STANLEY': 'MS',
            'WELLS FARGO': 'WFC',
            'WELLS FARGO & CO': 'WFC',
            'AMERICAN EXPRESS': 'AXP',
            'AMERICAN EXPRESS CO': 'AXP',
            'VISA': 'V',
            'VISA INC': 'V',
            'MASTERCARD': 'MA',
            'MASTERCARD INC': 'MA',
            'MASTERCARD INCORPORATED': 'MA',
            
            # Healthcare
            'JOHNSON & JOHNSON': 'JNJ',
            'JOHNSON AND JOHNSON': 'JNJ',
            'PFIZER': 'PFE',
            'PFIZER INC': 'PFE',
            'ABBVIE': 'ABBV',
            'ABBVIE INC': 'ABBV',
            'MERCK': 'MRK',
            'MERCK & CO': 'MRK',
            'MERCK AND CO': 'MRK',
            'BRISTOL MYERS': 'BMY',
            'BRISTOL MYERS SQUIBB': 'BMY',
            'BRISTOL-MYERS SQUIBB': 'BMY',
            'UNITED HEALTH': 'UNH',
            'UNITED HEALTH GROUP': 'UNH',
            'UNITEDHEALTH GROUP': 'UNH',
            'THERMO FISHER': 'TMO',
            'THERMO FISHER SCIENTIFIC': 'TMO',
            'MEDTRONIC': 'MDT',
            'MEDTRONIC PLC': 'MDT',
            
            # Consumer goods
            'COCA COLA': 'KO',
            'COCA-COLA': 'KO',
            'COCA COLA CO': 'KO',
            'THE COCA-COLA COMPANY': 'KO',
            'PEPSI': 'PEP',
            'PEPSICO': 'PEP',
            'PEPSICO INC': 'PEP',
            'PROCTER & GAMBLE': 'PG',
            'PROCTER AND GAMBLE': 'PG',
            'PROCTER & GAMBLE CO': 'PG',
            'WALMART': 'WMT',
            'WALMART INC': 'WMT',
            'WAL-MART': 'WMT',
            'HOME DEPOT': 'HD',
            'HOME DEPOT INC': 'HD',
            'THE HOME DEPOT': 'HD',
            'MCDONALDS': 'MCD',
            'MCDONALD\'S': 'MCD',
            'MCDONALDS CORP': 'MCD',
            'NIKE': 'NKE',
            'NIKE INC': 'NKE',
            'STARBUCKS': 'SBUX',
            'STARBUCKS CORP': 'SBUX',
            'STARBUCKS CORPORATION': 'SBUX',
            'COSTCO': 'COST',
            'COSTCO WHOLESALE': 'COST',
            'COSTCO WHOLESALE CORP': 'COST',
            
            # Energy
            'EXXON': 'XOM',
            'EXXON MOBIL': 'XOM',
            'EXXON MOBIL CORP': 'XOM',
            'EXXONMOBIL': 'XOM',
            'CHEVRON': 'CVX',
            'CHEVRON CORP': 'CVX',
            'CHEVRON CORPORATION': 'CVX',
            
            # Industrial
            'BOEING': 'BA',
            'BOEING CO': 'BA',
            'THE BOEING COMPANY': 'BA',
            'GENERAL ELECTRIC': 'GE',
            'GENERAL ELECTRIC CO': 'GE',
            'CATERPILLAR': 'CAT',
            'CATERPILLAR INC': 'CAT',
            'LOCKHEED MARTIN': 'LMT',
            'LOCKHEED MARTIN CORP': 'LMT',
            'UNION PACIFIC': 'UNP',
            'UNION PACIFIC CORP': 'UNP',
            'DANAHER': 'DHR',
            'DANAHER CORP': 'DHR',
            'DANAHER CORPORATION': 'DHR',
            
            # Automotive
            'FORD': 'F',
            'FORD MOTOR': 'F',
            'FORD MOTOR CO': 'F',
            'GENERAL MOTORS': 'GM',
            'GENERAL MOTORS CO': 'GM',
            
            # Telecommunications
            'VERIZON': 'VZ',
            'VERIZON COMMUNICATIONS': 'VZ',
            'VERIZON COMMUNICATIONS INC': 'VZ',
            'AT&T': 'T',
            'ATT': 'T',
            'AT&T INC': 'T',
            'COMCAST': 'CMCSA',
            'COMCAST CORP': 'CMCSA',
            'COMCAST CORPORATION': 'CMCSA',
            
            # Entertainment
            'DISNEY': 'DIS',
            'WALT DISNEY': 'DIS',
            'WALT DISNEY CO': 'DIS',
            'THE WALT DISNEY COMPANY': 'DIS',
            'DISNEY WALT CO': 'DIS',
        }
        
        # ETF mappings
        self.etf_mappings = {
            'SPDR S&P 500': 'SPY',
            'SPDR S&P 500 ETF': 'SPY',
            'SPDR S&P 500 ETF TRUST': 'SPY',
            'ISHARES RUSSELL 2000': 'IWM',
            'ISHARES RUSSELL 2000 ETF': 'IWM',
            'VANGUARD TOTAL STOCK MARKET': 'VTI',
            'VANGUARD TOTAL STOCK MARKET ETF': 'VTI',
            'INVESCO QQQ': 'QQQ',
            'INVESCO QQQ TRUST': 'QQQ',
            'POWERSHARES QQQ': 'QQQ',
            'ISHARES CORE S&P 500': 'IVV',
            'ISHARES CORE S&P 500 ETF': 'IVV',
            'VANGUARD S&P 500': 'VOO',
            'VANGUARD S&P 500 ETF': 'VOO',
            'FINANCIAL SELECT SECTOR SPDR': 'XLF',
            'TECHNOLOGY SELECT SECTOR SPDR': 'XLK',
            'HEALTH CARE SELECT SECTOR SPDR': 'XLV',
            'ENERGY SELECT SECTOR SPDR': 'XLE',
            'CONSUMER DISCRETIONARY SELECT SECTOR SPDR': 'XLY',
            'CONSUMER STAPLES SELECT SECTOR SPDR': 'XLP',
            'INDUSTRIAL SELECT SECTOR SPDR': 'XLI',
            'MATERIALS SELECT SECTOR SPDR': 'XLB',
            'UTILITIES SELECT SECTOR SPDR': 'XLU',
            'REAL ESTATE SELECT SECTOR SPDR': 'XLRE',
        }
        
        # Combine all mappings
        self.company_ticker_mapping.update(self.etf_mappings)
        
    def _init_amount_patterns(self):
        """Initialize amount parsing patterns."""
        # Standard congressional disclosure ranges
        self.standard_ranges = {
            '$1,001 - $15,000': (100100, 1500000),
            '$15,001 - $50,000': (1500100, 5000000),
            '$50,001 - $100,000': (5000100, 10000000),
            '$100,001 - $250,000': (10000100, 25000000),
            '$250,001 - $500,000': (25000100, 50000000),
            '$500,001 - $1,000,000': (50000100, 100000000),
            '$1,000,001 - $5,000,000': (100000100, 500000000),
            '$5,000,001 - $25,000,000': (500000100, 2500000000),
            '$25,000,001 - $50,000,000': (2500000100, 5000000000),
            '$50,000,000+': (5000000000, None),
            '$50,000,001+': (5000000100, None),
            'Over $50,000,000': (5000000000, None),
            'Greater than $50,000,000': (5000000000, None),
        }
        
        # Garbage characters commonly found in amount fields
        self.garbage_chars = re.compile(r'[abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ]+$')
        
        # Amount extraction patterns
        self.amount_patterns = [
            # Standard ranges
            r'\$[\d,]+\s*-\s*\$[\d,]+',
            r'\$[\d,]+\s*to\s*\$[\d,]+',
            r'\$[\d,]+\s*through\s*\$[\d,]+',
            r'Between\s*\$[\d,]+\s*and\s*\$[\d,]+',
            r'From\s*\$[\d,]+\s*to\s*\$[\d,]+',
            
            # Single amounts
            r'\$[\d,]+\+?',
            r'Over\s*\$[\d,]+',
            r'Greater than\s*\$[\d,]+',
            r'More than\s*\$[\d,]+',
            r'Above\s*\$[\d,]+',
            r'At least\s*\$[\d,]+',
            r'Minimum\s*\$[\d,]+',
            r'Maximum\s*\$[\d,]+',
            
            # Numeric only
            r'[\d,]+',
        ]
        
        # Common variations and typos
        self.amount_variations = {
            '1,001 - 15,000': '$1,001 - $15,000',
            '15,001 - 50,000': '$15,001 - $50,000',
            '50,001 - 100,000': '$50,001 - $100,000',
            '100,001 - 250,000': '$100,001 - $250,000',
            '250,001 - 500,000': '$250,001 - $500,000',
            '500,001 - 1,000,000': '$500,001 - $1,000,000',
            '1,000,001 - 5,000,000': '$1,000,001 - $5,000,000',
            '5,000,001 - 25,000,000': '$5,000,001 - $25,000,000',
            '25,000,001 - 50,000,000': '$25,000,001 - $50,000,000',
            '50,000,000+': '$50,000,000+',
            '50,000,001+': '$50,000,001+',
            # Common typos
            '$1,001-$15,000': '$1,001 - $15,000',
            '$15,001-$50,000': '$15,001 - $50,000',
            '$50,001-$100,000': '$50,001 - $100,000',
            '$100,001-$250,000': '$100,001 - $250,000',
            '$250,001-$500,000': '$250,001 - $500,000',
            '$500,001-$1,000,000': '$500,001 - $1,000,000',
            '$1,000,001-$5,000,000': '$1,000,001 - $5,000,000',
            '$5,000,001-$25,000,000': '$5,000,001 - $25,000,000',
            '$25,000,001-$50,000,000': '$25,000,001 - $50,000,000',
        }
        
    def _init_owner_patterns(self):
        """Initialize owner field patterns."""
        self.owner_mappings = {
            # Standard values
            'C': TradeOwner.SELF,
            'SP': TradeOwner.SPOUSE,
            'JT': TradeOwner.JOINT,
            'DC': TradeOwner.DEPENDENT_CHILD,
            
            # Full text mappings
            'SELF': TradeOwner.SELF,
            'CONGRESSMAN': TradeOwner.SELF,
            'CONGRESSWOMAN': TradeOwner.SELF,
            'REPRESENTATIVE': TradeOwner.SELF,
            'SENATOR': TradeOwner.SELF,
            'MEMBER': TradeOwner.SELF,
            'MYSELF': TradeOwner.SELF,
            'PERSONAL': TradeOwner.SELF,
            'INDIVIDUAL': TradeOwner.SELF,
            'OWN': TradeOwner.SELF,
            'OWNED': TradeOwner.SELF,
            'DIRECT': TradeOwner.SELF,
            'DIRECTLY': TradeOwner.SELF,
            
            'SPOUSE': TradeOwner.SPOUSE,
            'WIFE': TradeOwner.SPOUSE,
            'HUSBAND': TradeOwner.SPOUSE,
            'PARTNER': TradeOwner.SPOUSE,
            'MARRIED': TradeOwner.SPOUSE,
            'SPOUSES': TradeOwner.SPOUSE,
            
            'JOINT': TradeOwner.JOINT,
            'JOINTLY': TradeOwner.JOINT,
            'JOINT ACCOUNT': TradeOwner.JOINT,
            'JOINT OWNERSHIP': TradeOwner.JOINT,
            'TOGETHER': TradeOwner.JOINT,
            'BOTH': TradeOwner.JOINT,
            'SHARED': TradeOwner.JOINT,
            'COMBINED': TradeOwner.JOINT,
            'MUTUAL': TradeOwner.JOINT,
            
            'DEPENDENT': TradeOwner.DEPENDENT_CHILD,
            'DEPENDENT CHILD': TradeOwner.DEPENDENT_CHILD,
            'CHILD': TradeOwner.DEPENDENT_CHILD,
            'CHILDREN': TradeOwner.DEPENDENT_CHILD,
            'MINOR': TradeOwner.DEPENDENT_CHILD,
            'MINOR CHILD': TradeOwner.DEPENDENT_CHILD,
            'SON': TradeOwner.DEPENDENT_CHILD,
            'DAUGHTER': TradeOwner.DEPENDENT_CHILD,
            'KID': TradeOwner.DEPENDENT_CHILD,
            'KIDS': TradeOwner.DEPENDENT_CHILD,
            'JUVENILE': TradeOwner.DEPENDENT_CHILD,
            'UNDERAGE': TradeOwner.DEPENDENT_CHILD,
        }
        
    def _init_asset_type_patterns(self):
        """Initialize asset type detection patterns."""
        self.asset_type_patterns = {
            'STOCK': [
                r'\bstock\b', r'\bshares?\b', r'\bequity\b', r'\bequities\b',
                r'\bcommon\b', r'\bordinary\b', r'\bvoting\b', r'\bnon-voting\b'
            ],
            'BOND': [
                r'\bbond\b', r'\bbonds\b', r'\bdebt\b', r'\bdebenture\b',
                r'\bnote\b', r'\bnotes\b', r'\bfixed.income\b', r'\btreasury\b',
                r'\bcorporate.bond\b', r'\bgovernment.bond\b', r'\bmunicipal\b'
            ],
            'ETF': [
                r'\betf\b', r'\betfs\b', r'\bfund\b', r'\bfunds\b',
                r'\bexchange.traded\b', r'\bindex.fund\b', r'\bspdr\b',
                r'\bishares\b', r'\bvanguard\b', r'\binvesco\b'
            ],
            'OPTION': [
                r'\boption\b', r'\boptions\b', r'\bcall\b', r'\bcalls\b',
                r'\bput\b', r'\bputs\b', r'\bstrike\b', r'\bexpiration\b',
                r'\bderivative\b', r'\bderivatives\b'
            ],
            'MUTUAL_FUND': [
                r'\bmutual.fund\b', r'\bmutual.funds\b', r'\bopen.end\b',
                r'\bclosed.end\b', r'\bload\b', r'\bno.load\b', r'\bfund\b'
            ],
            'REIT': [
                r'\breit\b', r'\breits\b', r'\breal.estate\b', r'\bproperty\b',
                r'\breal.estate.investment\b', r'\breal.estate.trust\b'
            ],
            'CRYPTOCURRENCY': [
                r'\bcrypto\b', r'\bcryptocurrency\b', r'\bbitcoin\b', r'\bethereum\b',
                r'\bdigital.currency\b', r'\bvirtual.currency\b', r'\btoken\b'
            ],
        }
        
        # Compile patterns
        self.compiled_asset_patterns = {}
        for asset_type, patterns in self.asset_type_patterns.items():
            self.compiled_asset_patterns[asset_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def extract_ticker(self, asset_description: str) -> TickerExtractionResult:
        """Extract ticker symbol from asset description with enhanced accuracy."""
        if not asset_description:
            return TickerExtractionResult(
                ticker=None,
                asset_name=None,
                asset_type=None,
                confidence=Decimal('0.0'),
                extraction_method='no_input',
                notes=['No asset description provided']
            )
        
        original_description = asset_description
        normalized_description = asset_description.upper().strip()
        notes = []
        
        # Method 1: Direct ticker pattern matching
        ticker_candidates = []
        for pattern in self.compiled_ticker_patterns:
            matches = pattern.findall(normalized_description)
            for match in matches:
                if match not in self.ticker_blacklist and len(match) <= 5:
                    ticker_candidates.append((match, 'regex_pattern'))
        
        # Method 2: Company name mapping
        company_matches = []
        for company_name, ticker in self.company_ticker_mapping.items():
            if ticker and company_name in normalized_description:
                company_matches.append((ticker, 'company_mapping'))
        
        # Method 3: Fuzzy matching against company names
        fuzzy_matches = []
        if not ticker_candidates and not company_matches:
            # Extract potential company names (sequences of words)
            words = re.findall(r'\b[A-Z][A-Z\s&\.]+\b', normalized_description)
            for word_group in words:
                if len(word_group) > 3:  # Skip very short matches
                    best_match = process.extractOne(
                        word_group,
                        self.company_ticker_mapping.keys(),
                        scorer=fuzz.ratio,
                        score_cutoff=85
                    )
                    if best_match:
                        ticker = self.company_ticker_mapping[best_match[0]]
                        if ticker:
                            fuzzy_matches.append((ticker, 'fuzzy_company'))
                            notes.append(f"Fuzzy matched: {word_group} -> {best_match[0]}")
        
        # Method 4: ETF pattern matching
        etf_matches = []
        for etf_name, ticker in self.etf_mappings.items():
            if etf_name in normalized_description:
                etf_matches.append((ticker, 'etf_mapping'))
        
        # Combine all matches and score them
        all_matches = ticker_candidates + company_matches + fuzzy_matches + etf_matches
        
        if not all_matches:
            # Method 5: Fallback pattern matching
            fallback_patterns = [
                r'\b([A-Z]{2,5})\s+(?:STOCK|SHARES|EQUITY|COMMON|ORDINARY)\b',
                r'(?:STOCK|SHARES|EQUITY|COMMON|ORDINARY)\s+([A-Z]{2,5})\b',
                r'\b([A-Z]{2,5})\s+(?:INC|CORP|CO|LTD|LLC)\b',
                r'(?:INC|CORP|CO|LTD|LLC)\s+([A-Z]{2,5})\b',
            ]
            
            for pattern in fallback_patterns:
                matches = re.findall(pattern, normalized_description)
                for match in matches:
                    if match not in self.ticker_blacklist:
                        all_matches.append((match, 'fallback_pattern'))
        
        # Select best match
        if all_matches:
            # Priority order: company_mapping > etf_mapping > regex_pattern > fuzzy_company > fallback_pattern
            method_priority = {
                'company_mapping': 5,
                'etf_mapping': 4,
                'regex_pattern': 3,
                'fuzzy_company': 2,
                'fallback_pattern': 1
            }
            
            # Sort by priority and take the best
            sorted_matches = sorted(all_matches, key=lambda x: method_priority.get(x[1], 0), reverse=True)
            best_ticker, best_method = sorted_matches[0]
            
            # Calculate confidence based on method and context
            confidence = self._calculate_ticker_confidence(best_ticker, best_method, normalized_description)
            
            # Extract asset name and type
            asset_name = self._extract_asset_name(original_description, best_ticker)
            asset_type = self._detect_asset_type(normalized_description)
            
            notes.append(f"Extracted using {best_method}")
            if len(all_matches) > 1:
                notes.append(f"Multiple candidates found: {[m[0] for m in all_matches[:3]]}")
            
            return TickerExtractionResult(
                ticker=best_ticker,
                asset_name=asset_name,
                asset_type=asset_type,
                confidence=confidence,
                extraction_method=best_method,
                notes=notes
            )
        
        # No ticker found
        notes.append("No ticker patterns matched")
        return TickerExtractionResult(
            ticker=None,
            asset_name=self._extract_asset_name(original_description, None),
            asset_type=self._detect_asset_type(normalized_description),
            confidence=Decimal('0.0'),
            extraction_method='no_match',
            notes=notes
        )
    
    def _calculate_ticker_confidence(self, ticker: str, method: str, description: str) -> Decimal:
        """Calculate confidence score for ticker extraction."""
        base_confidence = {
            'company_mapping': Decimal('0.95'),
            'etf_mapping': Decimal('0.95'),
            'regex_pattern': Decimal('0.80'),
            'fuzzy_company': Decimal('0.70'),
            'fallback_pattern': Decimal('0.60'),
        }
        
        confidence = base_confidence.get(method, Decimal('0.50'))
        
        # Adjust based on context
        if len(ticker) <= 2:
            confidence *= Decimal('0.8')  # Very short tickers are less reliable
        elif len(ticker) == 3:
            confidence *= Decimal('0.9')  # 3-letter tickers are common
        elif len(ticker) >= 5:
            confidence *= Decimal('0.85')  # Long tickers are less common
        
        # Boost confidence if ticker appears multiple times
        ticker_count = description.count(ticker)
        if ticker_count > 1:
            confidence *= Decimal('1.1')
        
        # Reduce confidence if description is very short
        if len(description) < 20:
            confidence *= Decimal('0.9')
        
        return min(confidence, Decimal('1.0'))
    
    def _extract_asset_name(self, description: str, ticker: Optional[str]) -> Optional[str]:
        """Extract clean asset name from description."""
        if not description:
            return None
        
        # Clean the description
        clean_desc = description.strip()
        
        # Remove ticker if present
        if ticker:
            clean_desc = re.sub(rf'\b{re.escape(ticker)}\b', '', clean_desc, flags=re.IGNORECASE)
        
        # Remove common noise words
        noise_patterns = [
            r'\b(?:STOCK|SHARES|EQUITY|COMMON|ORDINARY|SECURITIES?)\b',
            r'\b(?:INC|CORP|CO|LTD|LLC|CORPORATION|INCORPORATED|COMPANY)\b',
            r'\b(?:THE|AND|OR|OF|IN|ON|AT|FOR|TO|BY|WITH|FROM)\b',
            r'\([^)]*\)',  # Remove parentheses
            r'\[[^\]]*\]',  # Remove brackets
            r'\s+',  # Multiple spaces
        ]
        
        for pattern in noise_patterns:
            clean_desc = re.sub(pattern, ' ', clean_desc, flags=re.IGNORECASE)
        
        # Clean up spacing and return
        clean_desc = ' '.join(clean_desc.split())
        return clean_desc[:300] if clean_desc else None
    
    def _detect_asset_type(self, description: str) -> Optional[str]:
        """Detect asset type from description."""
        if not description:
            return None
        
        # Check each asset type pattern
        for asset_type, patterns in self.compiled_asset_patterns.items():
            for pattern in patterns:
                if pattern.search(description):
                    return asset_type
        
        # Default to STOCK if no specific type detected
        return 'STOCK'
    
    def normalize_amount(self, amount_str: str) -> AmountNormalizationResult:
        """Normalize amount string to standard congressional ranges."""
        if not amount_str:
            return AmountNormalizationResult(
                amount_min=None,
                amount_max=None,
                amount_exact=None,
                original_amount=amount_str,
                normalized_amount='',
                confidence=Decimal('0.0'),
                notes=['No amount provided']
            )
        
        original_amount = amount_str
        notes = []
        
        # Clean garbage characters
        cleaned_amount = amount_str.strip()
        
        # Remove trailing garbage characters (common issue)
        garbage_match = self.garbage_chars.search(cleaned_amount)
        if garbage_match:
            garbage_text = garbage_match.group()
            cleaned_amount = cleaned_amount.replace(garbage_text, '').strip()
            notes.append(f"Removed garbage characters: {garbage_text}")
        
        # Handle common variations
        if cleaned_amount in self.amount_variations:
            cleaned_amount = self.amount_variations[cleaned_amount]
            notes.append("Applied variation mapping")
        
        # Try exact match with standard ranges
        if cleaned_amount in self.standard_ranges:
            amount_min, amount_max = self.standard_ranges[cleaned_amount]
            return AmountNormalizationResult(
                amount_min=amount_min,
                amount_max=amount_max,
                amount_exact=None,
                original_amount=original_amount,
                normalized_amount=cleaned_amount,
                confidence=Decimal('0.95'),
                notes=notes + ['Exact range match']
            )
        
        # Try pattern matching
        confidence = Decimal('0.0')
        amount_min = None
        amount_max = None
        amount_exact = None
        
        # Extract dollar amounts
        dollar_amounts = re.findall(r'\$?([\d,]+)', cleaned_amount)
        if dollar_amounts:
            try:
                # Convert to integers (in cents)
                amounts = [int(amt.replace(',', '')) * 100 for amt in dollar_amounts]
                
                if len(amounts) == 1:
                    # Single amount
                    amount_exact = amounts[0]
                    confidence = Decimal('0.85')
                    notes.append("Single amount extracted")
                    
                elif len(amounts) == 2:
                    # Range
                    amount_min = min(amounts)
                    amount_max = max(amounts)
                    confidence = Decimal('0.90')
                    notes.append("Range extracted")
                    
                else:
                    # Multiple amounts, use first two
                    amount_min = amounts[0]
                    amount_max = amounts[1]
                    confidence = Decimal('0.70')
                    notes.append(f"Multiple amounts found, using first two: {amounts}")
                    
            except (ValueError, IndexError) as e:
                notes.append(f"Error parsing amounts: {e}")
        
        # Check for "over" or "+" indicators
        if any(word in cleaned_amount.lower() for word in ['over', 'greater', 'more', 'above', 'minimum', '+']):
            if amount_exact:
                amount_min = amount_exact
                amount_max = None
                amount_exact = None
                confidence *= Decimal('0.9')
                notes.append("Interpreted as minimum amount")
        
        # Validate amounts are reasonable
        if amount_min and amount_min < 0:
            amount_min = None
            confidence *= Decimal('0.5')
            notes.append("Negative minimum amount adjusted")
        
        if amount_max and amount_max < 0:
            amount_max = None
            confidence *= Decimal('0.5')
            notes.append("Negative maximum amount adjusted")
        
        if amount_min and amount_max and amount_min > amount_max:
            amount_min, amount_max = amount_max, amount_min
            confidence *= Decimal('0.8')
            notes.append("Swapped min/max amounts")
        
        # Final validation
        if not any([amount_min, amount_max, amount_exact]):
            confidence = Decimal('0.0')
            notes.append("No valid amounts extracted")
        
        return AmountNormalizationResult(
            amount_min=amount_min,
            amount_max=amount_max,
            amount_exact=amount_exact,
            original_amount=original_amount,
            normalized_amount=cleaned_amount,
            confidence=confidence,
            notes=notes
        )
    
    def normalize_owner(self, owner_str: str) -> OwnerNormalizationResult:
        """Normalize owner field to standard enum values."""
        if not owner_str:
            return OwnerNormalizationResult(
                normalized_owner=None,
                original_owner=owner_str,
                confidence=Decimal('0.0'),
                notes=['No owner provided']
            )
        
        original_owner = owner_str
        normalized_owner_str = owner_str.upper().strip()
        notes = []
        
        # Direct mapping
        if normalized_owner_str in self.owner_mappings:
            return OwnerNormalizationResult(
                normalized_owner=self.owner_mappings[normalized_owner_str],
                original_owner=original_owner,
                confidence=Decimal('0.95'),
                notes=['Direct mapping']
            )
        
        # Fuzzy matching
        best_match = process.extractOne(
            normalized_owner_str,
            self.owner_mappings.keys(),
            scorer=fuzz.ratio,
            score_cutoff=70
        )
        
        if best_match:
            matched_key = best_match[0]
            score = best_match[1]
            confidence = Decimal(str(score / 100.0))
            
            notes.append(f"Fuzzy matched: {normalized_owner_str} -> {matched_key} (score: {score})")
            
            return OwnerNormalizationResult(
                normalized_owner=self.owner_mappings[matched_key],
                original_owner=original_owner,
                confidence=confidence,
                notes=notes
            )
        
        # Check if it's a company name (likely misaligned data)
        if any(word in normalized_owner_str for word in ['INC', 'CORP', 'LLC', 'CO', 'COMPANY', 'CORPORATION']):
            notes.append("Detected company name in owner field - likely data misalignment")
            
            # Try to map to common corporate structures
            if any(word in normalized_owner_str for word in ['FAMILY', 'TRUST', 'FOUNDATION']):
                return OwnerNormalizationResult(
                    normalized_owner=TradeOwner.JOINT,
                    original_owner=original_owner,
                    confidence=Decimal('0.60'),
                    notes=notes + ['Assumed JOINT for family/trust structure']
                )
        
        # Check for member names (another misalignment indicator)
        if len(normalized_owner_str.split()) >= 2 and all(word.isalpha() for word in normalized_owner_str.split()):
            notes.append("Detected person name in owner field - likely data misalignment")
            
            return OwnerNormalizationResult(
                normalized_owner=TradeOwner.SELF,
                original_owner=original_owner,
                confidence=Decimal('0.50'),
                notes=notes + ['Assumed SELF for person name']
            )
        
        # No match found
        notes.append("No owner mapping found")
        return OwnerNormalizationResult(
            normalized_owner=None,
            original_owner=original_owner,
            confidence=Decimal('0.0'),
            notes=notes
        )
    
    def analyze_data_quality(self, sample_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze data quality of a sample of records."""
        if not sample_records:
            return {'error': 'No sample records provided'}
        
        analysis = {
            'total_records': len(sample_records),
            'ticker_analysis': self._analyze_ticker_quality(sample_records),
            'amount_analysis': self._analyze_amount_quality(sample_records),
            'owner_analysis': self._analyze_owner_quality(sample_records),
            'overall_recommendations': []
        }
        
        # Generate overall recommendations
        ticker_success_rate = analysis['ticker_analysis']['success_rate']
        amount_success_rate = analysis['amount_analysis']['success_rate']
        owner_success_rate = analysis['owner_analysis']['success_rate']
        
        if ticker_success_rate < 80:
            analysis['overall_recommendations'].append(
                f"Ticker extraction success rate is {ticker_success_rate:.1f}%. Consider expanding company name mappings."
            )
        
        if amount_success_rate < 95:
            analysis['overall_recommendations'].append(
                f"Amount parsing success rate is {amount_success_rate:.1f}%. Review amount field data quality."
            )
        
        if owner_success_rate < 99:
            analysis['overall_recommendations'].append(
                f"Owner normalization success rate is {owner_success_rate:.1f}%. Check for data misalignment issues."
            )
        
        return analysis
    
    def _analyze_ticker_quality(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ticker extraction quality."""
        successful_extractions = 0
        extraction_methods = {}
        confidence_scores = []
        
        for record in records:
            asset_desc = record.get('raw_asset_description', '')
            result = self.extract_ticker(asset_desc)
            
            if result.ticker:
                successful_extractions += 1
                extraction_methods[result.extraction_method] = extraction_methods.get(result.extraction_method, 0) + 1
                confidence_scores.append(float(result.confidence))
        
        return {
            'success_rate': (successful_extractions / len(records)) * 100,
            'extraction_methods': extraction_methods,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'successful_extractions': successful_extractions,
            'failed_extractions': len(records) - successful_extractions
        }
    
    def _analyze_amount_quality(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze amount normalization quality."""
        successful_normalizations = 0
        garbage_char_count = 0
        confidence_scores = []
        
        for record in records:
            amount_str = record.get('amount', '')
            result = self.normalize_amount(amount_str)
            
            if any([result.amount_min, result.amount_max, result.amount_exact]):
                successful_normalizations += 1
                confidence_scores.append(float(result.confidence))
            
            if any('garbage' in note.lower() for note in result.notes):
                garbage_char_count += 1
        
        return {
            'success_rate': (successful_normalizations / len(records)) * 100,
            'garbage_character_rate': (garbage_char_count / len(records)) * 100,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'successful_normalizations': successful_normalizations,
            'failed_normalizations': len(records) - successful_normalizations
        }
    
    def _analyze_owner_quality(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze owner normalization quality."""
        successful_normalizations = 0
        misalignment_count = 0
        confidence_scores = []
        owner_distribution = {}
        
        for record in records:
            owner_str = record.get('owner', '')
            result = self.normalize_owner(owner_str)
            
            if result.normalized_owner:
                successful_normalizations += 1
                confidence_scores.append(float(result.confidence))
                owner_type = result.normalized_owner.value
                owner_distribution[owner_type] = owner_distribution.get(owner_type, 0) + 1
            
            if any('misalignment' in note.lower() for note in result.notes):
                misalignment_count += 1
        
        return {
            'success_rate': (successful_normalizations / len(records)) * 100,
            'misalignment_rate': (misalignment_count / len(records)) * 100,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'owner_distribution': owner_distribution,
            'successful_normalizations': successful_normalizations,
            'failed_normalizations': len(records) - successful_normalizations
        }