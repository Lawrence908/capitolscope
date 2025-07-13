#!/usr/bin/env python3
"""
Enhanced ticker extraction and normalization utilities.

This module provides improved ticker extraction from asset descriptions,
normalization, and fuzzy matching capabilities to improve data quality
in congressional trade imports.
"""

import re
import csv
from typing import Optional, List, Dict, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz
        RAPIDFUZZ_AVAILABLE = False
    except ImportError:
        fuzz = None
        RAPIDFUZZ_AVAILABLE = False

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TickerExtractionResult:
    """Result of ticker extraction process."""
    ticker: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"
    notes: List[str] = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []


class TickerExtractor:
    """Enhanced ticker extraction from asset descriptions."""
    
    def __init__(self, company_ticker_mapping: Optional[Dict[str, str]] = None):
        """Initialize with optional company name to ticker mapping."""
        self.company_ticker_mapping = company_ticker_mapping or {}
        self.load_default_mappings()
        
        # Compiled regex patterns for performance
        self.ticker_patterns = [
            re.compile(r'\(([A-Z]{1,5})\)'),                    # (TICKER)
            re.compile(r'\[([A-Z]{1,5})\]'),                    # [TICKER]
            re.compile(r'[-–]\s*([A-Z]{1,5})\s*$'),            # - TICKER at end
            re.compile(r'[-–]\s*([A-Z]{1,5})\s*[-–]'),         # - TICKER -
            re.compile(r'\b([A-Z]{1,5})\s*:'),                  # TICKER:
            re.compile(r'^([A-Z]{1,5})\s*[-–]'),               # TICKER - at start
            re.compile(r'Symbol:\s*([A-Z]{1,5})', re.IGNORECASE), # Symbol: TICKER
            re.compile(r'Ticker:\s*([A-Z]{1,5})', re.IGNORECASE), # Ticker: TICKER
        ]
        
        # Common words to exclude from ticker matching
        self.exclude_words = {
            'INC', 'CORP', 'CO', 'LLC', 'LTD', 'PLC', 'AG', 'SA', 'NV', 'SE',
            'THE', 'AND', 'OR', 'FOR', 'OF', 'IN', 'ON', 'AT', 'TO', 'FROM',
            'CLASS', 'COMMON', 'STOCK', 'SHARE', 'SHARES', 'ORDINARY', 'ADR',
            'REIT', 'TRUST', 'FUND', 'ETF', 'LP', 'LLP', 'SPON', 'SPONSORED'
        }
    
    def load_default_mappings(self):
        """Load default company name to ticker mappings."""
        # Common mappings for frequent assets in congressional data
        default_mappings = {
            'Apple Inc': 'AAPL',
            'Apple Inc.': 'AAPL',
            'Apple': 'AAPL',
            'Microsoft Corporation': 'MSFT',
            'Microsoft Corp': 'MSFT',
            'Microsoft': 'MSFT',
            'Amazon.com Inc': 'AMZN',
            'Amazon.com, Inc': 'AMZN',
            'Amazon': 'AMZN',
            'Alphabet Inc. - Class A': 'GOOGL',
            'Alphabet Inc. - Class C': 'GOOG',
            'Alphabet Inc': 'GOOGL',
            'Google': 'GOOGL',
            'Tesla Inc': 'TSLA',
            'Tesla, Inc': 'TSLA',
            'Tesla': 'TSLA',
            'Meta Platforms Inc': 'META',
            'Meta Platforms': 'META',
            'Facebook': 'META',
            'NVIDIA Corporation': 'NVDA',
            'NVIDIA Corp': 'NVDA',
            'NVIDIA': 'NVDA',
            'Berkshire Hathaway Inc. New': 'BRK.B',
            'Berkshire Hathaway Inc': 'BRK.B',
            'Berkshire Hathaway': 'BRK.B',
            'JPMorgan Chase & Co': 'JPM',
            'JP Morgan Chase & Co': 'JPM',
            'JPMorgan Chase': 'JPM',
            'Johnson & Johnson': 'JNJ',
            'Procter & Gamble': 'PG',
            'Exxon Mobil Corporation': 'XOM',
            'Exxon Mobil': 'XOM',
            'Walmart Inc': 'WMT',
            'Walmart': 'WMT',
            'Walt Disney Company': 'DIS',
            'The Walt Disney Company': 'DIS',
            'Walt Disney': 'DIS',
            'Disney': 'DIS',
            'Visa Inc': 'V',
            'Visa': 'V',
            'Mastercard Inc': 'MA',
            'Mastercard': 'MA',
            'Coca-Cola Company': 'KO',
            'Coca-Cola': 'KO',
            'PepsiCo Inc': 'PEP',
            'Pepsico Inc': 'PEP',
            'PepsiCo': 'PEP',
            'Pepsico': 'PEP',
            'Intel Corporation': 'INTC',
            'Intel Corp': 'INTC',
            'Intel': 'INTC',
            'Cisco Systems Inc': 'CSCO',
            'Cisco Systems': 'CSCO',
            'Cisco': 'CSCO',
            'Pfizer Inc': 'PFE',
            'Pfizer': 'PFE',
            'Merck & Company Inc': 'MRK',
            'Merck & Co': 'MRK',
            'Merck': 'MRK',
            'AT&T Inc': 'T',
            'AT&T': 'T',
            'Verizon Communications Inc': 'VZ',
            'Verizon Communications': 'VZ',
            'Verizon': 'VZ',
            'Home Depot Inc': 'HD',
            'Home Depot': 'HD',
            'Boeing Company': 'BA',
            'Boeing': 'BA',
            'McDonald\'s Corporation': 'MCD',
            'McDonald\'s Corp': 'MCD',
            'McDonald\'s': 'MCD',
            'McDonalds': 'MCD',
            'Nike Inc': 'NKE',
            'Nike': 'NKE',
            'Starbucks Corporation': 'SBUX',
            'Starbucks Corp': 'SBUX',
            'Starbucks': 'SBUX',
            'Netflix Inc': 'NFLX',
            'Netflix': 'NFLX',
            'Adobe Inc': 'ADBE',
            'Adobe': 'ADBE',
            'Salesforce Inc': 'CRM',
            'Salesforce': 'CRM',
            'Twitter Inc': 'TWTR',
            'Twitter': 'TWTR',
            'Zoom Video Communications': 'ZM',
            'Zoom': 'ZM',
            'Spotify Technology SA': 'SPOT',
            'Spotify': 'SPOT',
            'PayPal Holdings Inc': 'PYPL',
            'PayPal': 'PYPL',
            'Square Inc': 'SQ',
            'Square': 'SQ',
            'Block Inc': 'SQ',  # Square renamed to Block
            'Block': 'SQ',
            'Uber Technologies Inc': 'UBER',
            'Uber': 'UBER',
            'Lyft Inc': 'LYFT',
            'Lyft': 'LYFT',
            'Target Corporation': 'TGT',
            'Target Corp': 'TGT',
            'Target': 'TGT',
            'Costco Wholesale Corporation': 'COST',
            'Costco Wholesale': 'COST',
            'Costco': 'COST',
            'Ford Motor Company': 'F',
            'Ford Motor': 'F',
            'Ford': 'F',
            'General Motors Company': 'GM',
            'General Motors': 'GM',
            'GM': 'GM',
            'UnitedHealth Group Incorporated': 'UNH',
            'UnitedHealth Group': 'UNH',
            'UnitedHealth': 'UNH',
            'NextEra Energy Inc': 'NEE',
            'NextEra Energy': 'NEE',
            'Chubb Limited': 'CB',
            'Chubb': 'CB',
            # Add more as needed
        }
        
        # Merge with provided mappings
        self.company_ticker_mapping.update(default_mappings)
    
    def extract_ticker_from_description(self, description: str) -> TickerExtractionResult:
        """Extract ticker from asset description using multiple methods."""
        if not description or not description.strip():
            return TickerExtractionResult(method="empty_description")
        
        description = description.strip()
        result = TickerExtractionResult()
        
        # Method 1: Regex pattern matching
        ticker_result = self._extract_ticker_with_regex(description)
        if ticker_result.ticker:
            return ticker_result
        
        # Method 2: Fuzzy matching with company names
        fuzzy_result = self._extract_ticker_with_fuzzy_matching(description)
        if fuzzy_result.ticker:
            return fuzzy_result
        
        # Method 3: Word-based heuristics
        heuristic_result = self._extract_ticker_with_heuristics(description)
        if heuristic_result.ticker:
            return heuristic_result
        
        # No ticker found
        result.method = "no_match"
        result.notes.append(f"No ticker found in: {description}")
        return result
    
    def _extract_ticker_with_regex(self, description: str) -> TickerExtractionResult:
        """Extract ticker using regex patterns."""
        for i, pattern in enumerate(self.ticker_patterns):
            match = pattern.search(description)
            if match:
                potential_ticker = match.group(1).upper()
                
                # Validate ticker
                if self._is_valid_ticker(potential_ticker):
                    return TickerExtractionResult(
                        ticker=potential_ticker,
                        confidence=0.9,
                        method=f"regex_pattern_{i}",
                        notes=[f"Extracted from pattern: {pattern.pattern}"]
                    )
        
        return TickerExtractionResult(method="regex_no_match")
    
    def _extract_ticker_with_fuzzy_matching(self, description: str) -> TickerExtractionResult:
        """Extract ticker using fuzzy matching with company names."""
        if not fuzz:
            return TickerExtractionResult(method="fuzzy_unavailable")
        
        description_clean = self._clean_description_for_matching(description)
        best_match = None
        best_score = 0
        best_ticker = None
        
        for company_name, ticker in self.company_ticker_mapping.items():
            # Try exact match first
            if company_name.lower() in description_clean.lower():
                return TickerExtractionResult(
                    ticker=ticker,
                    confidence=0.95,
                    method="fuzzy_exact_match",
                    notes=[f"Exact match: {company_name}"]
                )
            
            # Try fuzzy matching
            score = fuzz.partial_ratio(company_name.lower(), description_clean.lower())
            if score > best_score and score >= 80:  # 80% threshold
                best_score = score
                best_match = company_name
                best_ticker = ticker
        
        if best_ticker:
            return TickerExtractionResult(
                ticker=best_ticker,
                confidence=best_score / 100.0,
                method="fuzzy_partial_match",
                notes=[f"Fuzzy match: {best_match} (score: {best_score})"]
            )
        
        return TickerExtractionResult(method="fuzzy_no_match")
    
    def _extract_ticker_with_heuristics(self, description: str) -> TickerExtractionResult:
        """Extract ticker using word-based heuristics."""
        words = re.findall(r'\b[A-Z]{1,5}\b', description.upper())
        
        for word in words:
            if self._is_valid_ticker(word):
                return TickerExtractionResult(
                    ticker=word,
                    confidence=0.5,
                    method="heuristic_word_match",
                    notes=[f"Heuristic match: {word}"]
                )
        
        return TickerExtractionResult(method="heuristic_no_match")
    
    def _clean_description_for_matching(self, description: str) -> str:
        """Clean description for better matching."""
        # Remove common suffixes and prefixes
        clean = description
        clean = re.sub(r'\s*\([^)]*\)\s*', ' ', clean)  # Remove parentheses
        clean = re.sub(r'\s*\[[^\]]*\]\s*', ' ', clean)  # Remove brackets
        clean = re.sub(r'\s+', ' ', clean)  # Normalize whitespace
        return clean.strip()
    
    def _is_valid_ticker(self, ticker: str) -> bool:
        """Check if ticker is valid (not a common word)."""
        if not ticker or len(ticker) < 1 or len(ticker) > 5:
            return False
        
        # Check if it's in exclude list
        if ticker.upper() in self.exclude_words:
            return False
        
        # Must be all uppercase letters
        if not ticker.isupper() or not ticker.isalpha():
            return False
        
        return True
    
    def normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker symbol."""
        if not ticker:
            return ""
        
        # Convert to uppercase
        ticker = ticker.upper().strip()
        
        # Replace dots with dashes (common in Yahoo Finance)
        ticker = ticker.replace('.', '-')
        
        # Remove common suffixes that might be appended
        ticker = re.sub(r'\s*\(.*\)$', '', ticker)
        ticker = re.sub(r'\s*\[.*\]$', '', ticker)
        
        return ticker


class SecurityEnrichmentService:
    """Service for enriching security data with missing fields."""
    
    def __init__(self, session):
        """Initialize with database session."""
        self.session = session
        self.enriched_count = 0
        self.failed_count = 0
        
    def enrich_security_data(self, security_id: str, ticker: str) -> Dict[str, any]:
        """Enrich a single security with missing data."""
        try:
            # Import here to avoid circular imports
            from domains.securities.ingestion import fetch_yfinance_data
            
            # Fetch data from Yahoo Finance
            yf_data = fetch_yfinance_data(ticker)
            
            if not yf_data:
                self.failed_count += 1
                return {"status": "failed", "reason": "No data from Yahoo Finance"}
            
            # Update security record
            from domains.securities.crud import SecurityCRUD
            security_crud = SecurityCRUD(self.session)
            
            # Build update data
            update_data = {}
            
            # Exchange mapping
            exchange_mapping = {
                'NasdaqGS': 'NASDAQ',
                'NYSE': 'NYSE',
                'AMEX': 'AMEX',
                'OTC': 'OTC'
            }
            
            if yf_data.get('exchange') and not update_data.get('exchange_code'):
                yf_exchange = yf_data.get('exchange')
                update_data['exchange_code'] = exchange_mapping.get(yf_exchange, yf_exchange)
            
            # Asset type determination
            if yf_data.get('quote_type') and not update_data.get('asset_type_code'):
                quote_type = yf_data.get('quote_type')
                asset_type_mapping = {
                    'EQUITY': 'ST',
                    'ETF': 'EF',
                    'MUTUALFUND': 'MF',
                    'BOND': 'CS',
                    'OPTION': 'OP',
                    'FUTURE': 'FU',
                    'CURRENCY': 'FE',
                    'CRYPTOCURRENCY': 'CT'
                }
                update_data['asset_type_code'] = asset_type_mapping.get(quote_type, 'ST')
            
            # Sector mapping
            if yf_data.get('sector') and not update_data.get('sector_gics_code'):
                sector = yf_data.get('sector')
                # This would need a proper GICS code mapping
                # For now, use a simple mapping
                sector_mapping = {
                    'Technology': '45',
                    'Healthcare': '35',
                    'Financial Services': '40',
                    'Consumer Cyclical': '25',
                    'Consumer Defensive': '30',
                    'Communication Services': '50',
                    'Industrials': '20',
                    'Energy': '10',
                    'Real Estate': '60',
                    'Materials': '15',
                    'Utilities': '55'
                }
                update_data['sector_gics_code'] = sector_mapping.get(sector, '45')
            
            # Other enrichment fields
            if yf_data.get('market_cap'):
                update_data['market_cap'] = int(yf_data['market_cap'] * 100)  # Convert to cents
            
            if yf_data.get('beta'):
                update_data['beta'] = yf_data['beta']
            
            if yf_data.get('pe_ratio'):
                update_data['pe_ratio'] = yf_data['pe_ratio']
            
            if yf_data.get('dividend_yield'):
                update_data['dividend_yield'] = yf_data['dividend_yield']
            
            # Update the security if we have data
            if update_data:
                from domains.securities.schemas import SecurityUpdate
                update_schema = SecurityUpdate(**update_data)
                security_crud.update(security_id, update_schema)
                self.enriched_count += 1
                
                return {
                    "status": "success",
                    "updated_fields": list(update_data.keys()),
                    "data": update_data
                }
            else:
                return {"status": "no_updates", "reason": "No new data to update"}
                
        except Exception as e:
            logger.error(f"Error enriching security {ticker}: {e}")
            self.failed_count += 1
            return {"status": "error", "reason": str(e)}
    
    def get_enrichment_stats(self) -> Dict[str, int]:
        """Get enrichment statistics."""
        return {
            "enriched_count": self.enriched_count,
            "failed_count": self.failed_count,
            "total_processed": self.enriched_count + self.failed_count
        }


class DataQualityReporter:
    """Reporter for data quality issues and statistics."""
    
    def __init__(self):
        """Initialize reporter."""
        self.issues = []
        self.stats = {
            'total_trades': 0,
            'trades_with_tickers': 0,
            'trades_with_securities': 0,
            'unique_tickers': set(),
            'unmatched_tickers': set(),
            'unmatched_assets': set(),
            'common_issues': {},
            'enrichment_candidates': []
        }
    
    def record_trade(self, ticker: str, asset_name: str, security_id: Optional[str] = None):
        """Record a trade for quality analysis."""
        self.stats['total_trades'] += 1
        
        if ticker:
            self.stats['trades_with_tickers'] += 1
            self.stats['unique_tickers'].add(ticker)
        
        if security_id:
            self.stats['trades_with_securities'] += 1
        else:
            if ticker:
                self.stats['unmatched_tickers'].add(ticker)
            if asset_name:
                self.stats['unmatched_assets'].add(asset_name)
    
    def add_issue(self, issue_type: str, description: str, row_number: int = None):
        """Add a data quality issue."""
        self.issues.append({
            'type': issue_type,
            'description': description,
            'row_number': row_number,
            'timestamp': datetime.now()
        })
        
        # Update common issues count
        if issue_type not in self.stats['common_issues']:
            self.stats['common_issues'][issue_type] = 0
        self.stats['common_issues'][issue_type] += 1
    
    def generate_report(self) -> str:
        """Generate a comprehensive data quality report."""
        report = []
        report.append("=" * 60)
        report.append("DATA QUALITY REPORT")
        report.append("=" * 60)
        
        # Summary statistics
        report.append("\n📊 SUMMARY STATISTICS")
        report.append(f"Total Trades Processed: {self.stats['total_trades']:,}")
        report.append(f"Trades with Tickers: {self.stats['trades_with_tickers']:,}")
        report.append(f"Trades with Securities: {self.stats['trades_with_securities']:,}")
        report.append(f"Unique Tickers Found: {len(self.stats['unique_tickers']):,}")
        report.append(f"Unmatched Tickers: {len(self.stats['unmatched_tickers']):,}")
        report.append(f"Unmatched Assets: {len(self.stats['unmatched_assets']):,}")
        
        # Calculate success rates
        if self.stats['total_trades'] > 0:
            ticker_rate = (self.stats['trades_with_tickers'] / self.stats['total_trades']) * 100
            security_rate = (self.stats['trades_with_securities'] / self.stats['total_trades']) * 100
            report.append(f"Ticker Extraction Rate: {ticker_rate:.1f}%")
            report.append(f"Security Matching Rate: {security_rate:.1f}%")
        
        # Common issues
        if self.stats['common_issues']:
            report.append("\n❌ COMMON ISSUES")
            for issue_type, count in sorted(self.stats['common_issues'].items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {issue_type}: {count:,} occurrences")
        
        # Top unmatched tickers
        if self.stats['unmatched_tickers']:
            report.append("\n🔍 TOP UNMATCHED TICKERS")
            for ticker in sorted(list(self.stats['unmatched_tickers']))[:10]:
                report.append(f"  {ticker}")
        
        # Top unmatched assets
        if self.stats['unmatched_assets']:
            report.append("\n🏢 TOP UNMATCHED ASSETS")
            for asset in sorted(list(self.stats['unmatched_assets']))[:10]:
                report.append(f"  {asset}")
        
        # Recommendations
        report.append("\n💡 RECOMMENDATIONS")
        if len(self.stats['unmatched_tickers']) > 0:
            report.append("  - Add missing tickers to securities database")
        if len(self.stats['unmatched_assets']) > 0:
            report.append("  - Enhance fuzzy matching for asset names")
        if self.stats['trades_with_securities'] < self.stats['trades_with_tickers']:
            report.append("  - Run security enrichment to improve matching")
        
        report.append("=" * 60)
        return "\n".join(report)
    
    def export_issues_to_csv(self, filepath: str):
        """Export issues to CSV for manual review."""
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['type', 'description', 'row_number', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for issue in self.issues:
                writer.writerow(issue)
        
        logger.info(f"Exported {len(self.issues)} issues to {filepath}")
    
    def export_unmatched_assets_to_csv(self, filepath: str):
        """Export unmatched assets for manual review."""
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['asset_name', 'suggested_ticker', 'confidence'])
            
            for asset in sorted(self.stats['unmatched_assets']):
                # Could add fuzzy matching suggestions here
                writer.writerow([asset, '', ''])
        
        logger.info(f"Exported {len(self.stats['unmatched_assets'])} unmatched assets to {filepath}")


# Create global instances
ticker_extractor = TickerExtractor()