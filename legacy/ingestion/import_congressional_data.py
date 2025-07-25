#!/usr/bin/env python3
"""
Congressional data import script for CapitolScope.

This script imports congressional trading data from existing CSV files or fetches
live data, creates member profiles, and stores everything in the database.

Usage:
    python scripts/import_congressional_data.py --csvs  # Import from existing CSVs
    python scripts/import_congressional_data.py --live  # Fetch live data (10-15 min)
    python scripts/import_congressional_data.py --hybrid # CSVs + latest live data
"""

import asyncio
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add src directory to path
src_path = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(src_path))

from core.database import db_manager, init_database, get_sync_db_session
import logging
logger = logging.getLogger(__name__)
from domains.congressional.ingestion import (
    import_congressional_data_from_csvs,
    import_congressional_data_from_sqlite,
    enrich_member_profiles
)


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_data: Optional[Dict[str, Any]] = None
    confidence_score: float = 1.0


class CongressionalDataValidator:
    """Comprehensive validation system for congressional trade data"""
    
    def __init__(self):
        # Valid transaction types
        self.valid_transaction_types = {'P', 'S', 'E', 'S (partial)', 'Purchase', 'Sale', 'Exchange'}
        
        # Valid owner types
        self.valid_owner_types = {'SP', 'DC', 'JT', 'Joint', 'Spouse', 'Dependent'}
        
        # Valid amount patterns
        self.amount_patterns = [
            r'^\$[\d,]+$',                           # $1,000
            r'^\$[\d,]+\s*-\s*\$[\d,]+$',           # $1,000 - $15,000
            r'^None$',                               # None
            r'^\d+(\.\d+)?%$',                      # 4.375%
            r'^[\d,]+$',                            # 1000 (numbers only)
        ]
        
        # Date patterns
        self.date_patterns = [
            r'^\d{1,2}/\d{1,2}/\d{4}$',            # MM/DD/YYYY
            r'^\d{4}-\d{2}-\d{2}$',                # YYYY-MM-DD
        ]
        
        # Statistics tracking
        self.validation_stats = {
            'total_records': 0,
            'valid_records': 0,
            'cleaned_records': 0,
            'rejected_records': 0,
            'duplicate_records': 0,
            'validation_errors': {},
            'confidence_distribution': []
        }
        
    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """Validate a single congressional trade record"""
        errors = []
        warnings = []
        cleaned_data = record.copy()
        confidence_score = 1.0
        
        self.validation_stats['total_records'] += 1
        
        # 1. Validate required fields
        required_fields = ['Member', 'DocID', 'Asset']
        for field in required_fields:
            if not record.get(field) or str(record[field]).strip() == '':
                errors.append(f"Missing required field: {field}")
                confidence_score -= 0.3
        
        # 2. Validate and clean transaction type
        transaction_type_result = self._validate_transaction_type(record.get('Transaction Type', ''))
        if transaction_type_result['errors']:
            errors.extend(transaction_type_result['errors'])
            confidence_score -= 0.2
        if transaction_type_result['warnings']:
            warnings.extend(transaction_type_result['warnings'])
            confidence_score -= 0.1
        if transaction_type_result['cleaned_value']:
            cleaned_data['Transaction Type'] = transaction_type_result['cleaned_value']
        
        # 3. Validate and clean owner type
        owner_result = self._validate_owner_type(record.get('Owner', ''))
        if owner_result['errors']:
            errors.extend(owner_result['errors'])
            confidence_score -= 0.1
        if owner_result['cleaned_value']:
            cleaned_data['Owner'] = owner_result['cleaned_value']
        
        # 4. Validate and clean dates
        transaction_date_result = self._validate_date(record.get('Transaction Date', ''), 'Transaction Date')
        notification_date_result = self._validate_date(record.get('Notification Date', ''), 'Notification Date')
        
        if transaction_date_result['errors']:
            errors.extend(transaction_date_result['errors'])
            confidence_score -= 0.2
        if notification_date_result['errors']:
            errors.extend(notification_date_result['errors'])
            confidence_score -= 0.1
            
        if transaction_date_result['cleaned_value']:
            cleaned_data['Transaction Date'] = transaction_date_result['cleaned_value']
        if notification_date_result['cleaned_value']:
            cleaned_data['Notification Date'] = notification_date_result['cleaned_value']
        
        # 5. Validate and clean amount
        amount_result = self._validate_amount(record.get('Amount', ''))
        if amount_result['errors']:
            errors.extend(amount_result['errors'])
            confidence_score -= 0.1
        if amount_result['warnings']:
            warnings.extend(amount_result['warnings'])
        if amount_result['cleaned_value']:
            cleaned_data['Amount'] = amount_result['cleaned_value']
        
        # 6. Validate names
        first_name_result = self._validate_name(record.get('FirstName', ''), 'FirstName')
        last_name_result = self._validate_name(record.get('LastName', ''), 'LastName')
        
        if first_name_result['cleaned_value']:
            cleaned_data['FirstName'] = first_name_result['cleaned_value']
        if last_name_result['cleaned_value']:
            cleaned_data['LastName'] = last_name_result['cleaned_value']
        
        # 7. Clean asset name
        asset_result = self._clean_asset_name(record.get('Asset', ''))
        if asset_result['cleaned_value']:
            cleaned_data['Asset'] = asset_result['cleaned_value']
        if asset_result['warnings']:
            warnings.extend(asset_result['warnings'])
        
        # 8. Cross-field validation
        cross_validation_result = self._cross_validate_fields(cleaned_data)
        if cross_validation_result['errors']:
            errors.extend(cross_validation_result['errors'])
            confidence_score -= 0.1
        if cross_validation_result['warnings']:
            warnings.extend(cross_validation_result['warnings'])
        
        # Determine if record is valid
        is_valid = len(errors) == 0 and confidence_score >= 0.3
        
        # Update statistics
        if is_valid:
            self.validation_stats['valid_records'] += 1
            if cleaned_data != record:
                self.validation_stats['cleaned_records'] += 1
        else:
            self.validation_stats['rejected_records'] += 1
            
        self.validation_stats['confidence_distribution'].append(confidence_score)
        
        # Track error types
        for error in errors:
            error_type = error.split(':')[0]
            self.validation_stats['validation_errors'][error_type] = \
                self.validation_stats['validation_errors'].get(error_type, 0) + 1
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data if is_valid else None,
            confidence_score=confidence_score
        )
    
    def _validate_transaction_type(self, value: str) -> Dict[str, Any]:
        """Validate and normalize transaction type"""
        if not value or str(value).strip() == '':
            return {
                'errors': ['Missing transaction type'],
                'warnings': [],
                'cleaned_value': None
            }
        
        value = str(value).strip().upper()
        
        # Normalize common variations
        normalizations = {
            'PURCHASE': 'P',
            'BUY': 'P',
            'BOUGHT': 'P',
            'SALE': 'S',
            'SELL': 'S',
            'SOLD': 'S',
            'EXCHANGE': 'E',
            'EXCHANGED': 'E',
            'S (PARTIAL)': 'S (partial)',
            'PARTIAL SALE': 'S (partial)',
            'PARTIAL': 'S (partial)'
        }
        
        normalized = normalizations.get(value, value)
        
        if normalized in ['P', 'S', 'E', 'S (partial)']:
            return {
                'errors': [],
                'warnings': [],
                'cleaned_value': normalized
            }
        else:
            return {
                'errors': [f'Invalid transaction type: {value}'],
                'warnings': [],
                'cleaned_value': None
            }
    
    def _validate_owner_type(self, value: str) -> Dict[str, Any]:
        """Validate and normalize owner type"""
        if not value or str(value).strip() == '':
            return {
                'errors': [],
                'warnings': ['Missing owner type, defaulting to JT'],
                'cleaned_value': 'JT'
            }
        
        value = str(value).strip().upper()
        
        # Normalize common variations
        normalizations = {
            'SPOUSE': 'SP',
            'DEPENDENT': 'DC',
            'JOINT': 'JT',
            'CHILD': 'DC'
        }
        
        normalized = normalizations.get(value, value)
        
        if normalized in ['SP', 'DC', 'JT']:
            return {
                'errors': [],
                'warnings': [],
                'cleaned_value': normalized
            }
        else:
            return {
                'errors': [f'Invalid owner type: {value}, defaulting to JT'],
                'warnings': [],
                'cleaned_value': 'JT'
            }
    
    def _validate_date(self, value: str, field_name: str) -> Dict[str, Any]:
        """Validate and normalize date"""
        if not value or str(value).strip() == '':
            return {
                'errors': [f'Missing {field_name}'],
                'warnings': [],
                'cleaned_value': None
            }
        
        value = str(value).strip()
        
        # Check if it matches expected patterns
        for pattern in self.date_patterns:
            if re.match(pattern, value):
                # Try to parse and validate the date
                try:
                    if '/' in value:
                        # MM/DD/YYYY format
                        month, day, year = map(int, value.split('/'))
                        date_obj = datetime(year, month, day)
                        return {
                            'errors': [],
                            'warnings': [],
                            'cleaned_value': date_obj.strftime('%m/%d/%Y')
                        }
                    elif '-' in value:
                        # YYYY-MM-DD format
                        date_obj = datetime.strptime(value, '%Y-%m-%d')
                        return {
                            'errors': [],
                            'warnings': [],
                            'cleaned_value': date_obj.strftime('%m/%d/%Y')
                        }
                except ValueError:
                    pass
        
        return {
            'errors': [f'Invalid {field_name} format: {value}'],
            'warnings': [],
            'cleaned_value': None
        }
    
    def _validate_amount(self, value: str) -> Dict[str, Any]:
        """Validate and normalize amount"""
        if not value or str(value).strip() == '':
            return {
                'errors': [],
                'warnings': ['Missing amount'],
                'cleaned_value': None
            }
        
        value = str(value).strip()
        
        # Check if it matches expected patterns
        for pattern in self.amount_patterns:
            if re.match(pattern, value):
                return {
                    'errors': [],
                    'warnings': [],
                    'cleaned_value': value
                }
        
        # Try to extract and fix common amount issues
        # Remove extra characters and try again
        cleaned_value = re.sub(r'[^\d,.$%-]', '', value)
        for pattern in self.amount_patterns:
            if re.match(pattern, cleaned_value):
                return {
                    'errors': [],
                    'warnings': [f'Cleaned amount: {value} -> {cleaned_value}'],
                    'cleaned_value': cleaned_value
                }
        
        return {
            'errors': [],
            'warnings': [f'Unusual amount format: {value}'],
            'cleaned_value': value
        }
    
    def _validate_name(self, value: str, field_name: str) -> Dict[str, Any]:
        """Validate and clean name fields"""
        if not value or str(value).strip() == '':
            return {
                'errors': [],
                'warnings': [f'Missing {field_name}'],
                'cleaned_value': ''
            }
        
        value = str(value).strip()
        
        # Clean up common name issues
        cleaned_value = re.sub(r'[^\w\s\.-]', '', value)  # Remove special chars except . and -
        cleaned_value = re.sub(r'\s+', ' ', cleaned_value).strip()  # Normalize whitespace
        
        return {
            'errors': [],
            'warnings': [] if cleaned_value == value else [f'Cleaned {field_name}: {value} -> {cleaned_value}'],
            'cleaned_value': cleaned_value
        }
    
    def _clean_asset_name(self, value: str) -> Dict[str, Any]:
        """Clean asset name of parsing artifacts"""
        if not value or str(value).strip() == '':
            return {
                'errors': ['Missing asset name'],
                'warnings': [],
                'cleaned_value': None
            }
        
        value = str(value).strip()
        original_value = value
        
        # Remove common parsing artifacts
        cleaning_patterns = [
            (r'\b[PSE]\b', ''),                     # Remove standalone transaction types
            (r'\b\d{1,2}/\d{1,2}/\d{4}\b', ''),   # Remove dates
            (r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?', ''), # Remove amounts
            (r'\b(?:Transaction|Date|Notification|Amount|Asset|Owner|ID)\b', ''), # Remove field names
            (r'\s+', ' ')                           # Normalize whitespace
        ]
        
        for pattern, replacement in cleaning_patterns:
            value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        
        value = value.strip('.,;: ')  # Remove trailing punctuation
        
        if not value:
            return {
                'errors': ['Asset name became empty after cleaning'],
                'warnings': [],
                'cleaned_value': original_value  # Keep original if cleaning removes everything
            }
        
        warnings = []
        if value != original_value:
            warnings.append(f'Cleaned asset name: "{original_value}" -> "{value}"')
        
        return {
            'errors': [],
            'warnings': warnings,
            'cleaned_value': value
        }
    
    def _cross_validate_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-validate related fields"""
        errors = []
        warnings = []
        
        # Check if notification date is after transaction date
        try:
            trans_date_str = data.get('Transaction Date', '')
            notif_date_str = data.get('Notification Date', '')
            
            if trans_date_str and notif_date_str:
                trans_date = datetime.strptime(trans_date_str, '%m/%d/%Y')
                notif_date = datetime.strptime(notif_date_str, '%m/%d/%Y')
                
                if notif_date < trans_date:
                    warnings.append('Notification date is before transaction date')
        except ValueError:
            pass  # Date parsing errors already caught in individual validation
        
        # Check for suspicious patterns
        asset = data.get('Asset', '').lower()
        if any(keyword in asset for keyword in ['asset', 'transaction', 'date', 'amount']):
            warnings.append('Asset name contains field keywords - possible parsing artifact')
        
        return {
            'errors': errors,
            'warnings': warnings
        }
    
    def detect_duplicates(self, records: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
        """Detect potential duplicate records with similarity scoring"""
        duplicates = []
        
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                similarity = self._calculate_similarity(records[i], records[j])
                if similarity > 0.8:  # 80% similarity threshold
                    duplicates.append((i, j, similarity))
        
        return duplicates
    
    def _calculate_similarity(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> float:
        """Calculate similarity between two records"""
        # Key fields for comparison
        key_fields = ['Member', 'DocID', 'Asset', 'Transaction Type', 'Transaction Date', 'Amount']
        
        matches = 0
        total_fields = 0
        
        for field in key_fields:
            val1 = str(record1.get(field, '')).strip().lower()
            val2 = str(record2.get(field, '')).strip().lower()
            
            if val1 and val2:  # Only compare if both have values
                total_fields += 1
                if val1 == val2:
                    matches += 1
                elif self._fuzzy_match(val1, val2):
                    matches += 0.5  # Partial credit for fuzzy matches
        
        return matches / total_fields if total_fields > 0 else 0
    
    def _fuzzy_match(self, str1: str, str2: str) -> bool:
        """Check if two strings are similar enough to be considered a match"""
        # Simple fuzzy matching - can be enhanced with more sophisticated algorithms
        if abs(len(str1) - len(str2)) > 5:
            return False
        
        # Check if one is a subset of the other
        if str1 in str2 or str2 in str1:
            return True
        
        # Check Levenshtein-like similarity (simplified)
        min_length = min(len(str1), len(str2))
        if min_length == 0:
            return False
        
        common_chars = sum(1 for c1, c2 in zip(str1, str2) if c1 == c2)
        return (common_chars / min_length) > 0.8
    
    def get_validation_report(self) -> str:
        """Generate a comprehensive validation report"""
        stats = self.validation_stats
        
        if stats['total_records'] == 0:
            return "No records processed"
        
        success_rate = (stats['valid_records'] / stats['total_records']) * 100
        cleaning_rate = (stats['cleaned_records'] / stats['total_records']) * 100
        
        report = f"""
Congressional Data Validation Report
===================================

Overall Statistics:
- Total Records Processed: {stats['total_records']:,}
- Valid Records: {stats['valid_records']:,} ({success_rate:.1f}%)
- Cleaned Records: {stats['cleaned_records']:,} ({cleaning_rate:.1f}%)
- Rejected Records: {stats['rejected_records']:,}
- Duplicate Records: {stats['duplicate_records']:,}

Data Quality:
- Average Confidence Score: {sum(stats['confidence_distribution']) / len(stats['confidence_distribution']):.2f}
- Records with High Confidence (>0.8): {len([s for s in stats['confidence_distribution'] if s > 0.8]):,}
- Records with Low Confidence (<0.5): {len([s for s in stats['confidence_distribution'] if s < 0.5]):,}

Common Validation Issues:
"""
        
        # Sort errors by frequency
        sorted_errors = sorted(stats['validation_errors'].items(), key=lambda x: x[1], reverse=True)
        for error_type, count in sorted_errors[:10]:  # Top 10 error types
            percentage = (count / stats['total_records']) * 100
            report += f"- {error_type}: {count:,} occurrences ({percentage:.1f}%)\n"
        
        return report


def import_from_csvs(csv_directory: str) -> Dict[str, Any]:
    """Import congressional data from existing CSV files with validation."""
    logger.info("🗂️  Importing congressional data from CSV files...")
    
    validator = CongressionalDataValidator()
    
    with get_sync_db_session() as session:
        try:
            # Create synchronous ingester
            from domains.congressional.ingestion import CongressionalDataIngestion
            ingester = CongressionalDataIngestion(session)
            
            # Add validation to the ingester
            ingester.set_validator(validator)
            
            results = ingester.import_congressional_data_from_csvs_sync(csv_directory)
            
            # Add validation statistics to results
            results['validation_report'] = validator.get_validation_report()
            results['validation_stats'] = validator.validation_stats
            
            logger.info(f"✅ CSV import completed: {results}")
            logger.info(f"📊 Validation Report:\n{validator.get_validation_report()}")
            
            return results
        except Exception as e:
            logger.error(f"❌ CSV import failed: {e}")
            raise


async def fetch_live_data(years: list = None) -> Dict[str, Any]:
    """Fetch live congressional data using the existing fetch script."""
    logger.info("🔄 Fetching live congressional data...")
    
    if years is None:
        years = list(range(2014, 2026))  # 2014-2025
    
    results = {
        "years_processed": len(years),
        "total_records": 0,
        "total_members": 0
    }
    
    # Import the existing fetch script
    try:
        legacy_path = Path(__file__).parent.parent / "legacy" / "ingestion"
        sys.path.insert(0, str(legacy_path))
        
        from fetch_congress_data import CongressTrades
        
        for year in years:
            logger.info(f"📅 Processing year {year}...")
            try:
                congress_trades = CongressTrades(year=year)
                trades_df = congress_trades.trades
                
                if not trades_df.empty:
                    results["total_records"] += len(trades_df)
                    results["total_members"] += trades_df['Member'].nunique()
                    logger.info(f"✅ Year {year}: {len(trades_df)} trades from {trades_df['Member'].nunique()} members")
                else:
                    logger.warning(f"⚠️  No data found for year {year}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to fetch data for year {year}: {e}")
                continue
        
        # Now import the generated CSV files using synchronous session with validation
        csv_directory = Path(__file__).parent.parent / "data" / "congress" / "csv"
        validator = CongressionalDataValidator()
        
        with get_sync_db_session() as session:
            from domains.congressional.ingestion import CongressionalDataIngestion
            ingester = CongressionalDataIngestion(session)
            ingester.set_validator(validator)
            import_results = ingester.import_congressional_data_from_csvs_sync(str(csv_directory))
            results.update(import_results)
            results['validation_report'] = validator.get_validation_report()
        
        logger.info(f"✅ Live data fetch completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Live data fetch failed: {e}")
        raise


def enrich_members() -> Dict[str, Any]:
    """Enrich member profiles with additional data."""
    logger.info("👥 Enriching member profiles...")
    
    with get_sync_db_session() as session:
        try:
            from domains.congressional.ingestion import CongressionalDataIngestion
            ingester = CongressionalDataIngestion(session)
            results = ingester.enrich_member_data_sync()
            logger.info(f"✅ Member enrichment completed: {results}")
            return results
        except Exception as e:
            logger.error(f"❌ Member enrichment failed: {e}")
            raise


def print_results_summary(results: Dict[str, Any], mode: str):
    """Print a formatted summary of the import results."""
    print("\n" + "="*60)
    print(f"📊 CONGRESSIONAL DATA IMPORT SUMMARY ({mode.upper()})")
    print("="*60)
    
    if "csv_files_processed" in results:
        print(f"📁 CSV Files Processed:   {results.get('csv_files_processed', 0):,}")
    if "years_processed" in results:
        print(f"📅 Years Processed:       {results.get('years_processed', 0):,}")
    
    print(f"👥 Members Created:       {results.get('total_members', 0):,}")
    print(f"💼 Trades Imported:       {results.get('total_trades', 0):,}")
    print(f"❌ Failed Trades:         {results.get('failed_trades', 0):,}")
    
    # Validation statistics
    validation_stats = results.get('validation_stats', {})
    if validation_stats:
        print(f"✅ Valid Records:         {validation_stats.get('valid_records', 0):,}")
        print(f"🔧 Cleaned Records:       {validation_stats.get('cleaned_records', 0):,}")
        print(f"🚫 Rejected Records:      {validation_stats.get('rejected_records', 0):,}")
        
        if validation_stats.get('confidence_distribution'):
            avg_confidence = sum(validation_stats['confidence_distribution']) / len(validation_stats['confidence_distribution'])
            print(f"📈 Avg Confidence Score:  {avg_confidence:.2f}")
    
    if results.get('failed_trades', 0) > 0:
        success_rate = (results.get('total_trades', 0) / (results.get('total_trades', 0) + results.get('failed_trades', 0))) * 100
        print(f"✅ Success Rate:          {success_rate:.1f}%")
    
    print("="*60)
    
    # Print validation report if available
    if results.get('validation_report'):
        print(f"\n{results['validation_report']}")


async def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Import congressional trading data into CapitolScope database'
    )
    
    # Import mode options
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--csvs', 
        action='store_true',
        help='Import from existing CSV files (fast)'
    )
    mode_group.add_argument(
        '--live', 
        action='store_true',
        help='Fetch live data from congress.gov (10-15 minutes)'
    )
    mode_group.add_argument(
        '--hybrid',
        action='store_true', 
        help='Import CSVs + fetch latest live data'
    )
    
    # Additional options
    parser.add_argument(
        '--csv-directory',
        type=str,
        default='data/congress/csv',
        help='Directory containing CSV files (default: data/congress/csv)'
    )
    parser.add_argument(
        '--years',
        nargs='+',
        type=int,
        help='Specific years to fetch (for --live mode)'
    )
    parser.add_argument(
        '--skip-enrichment',
        action='store_true',
        help='Skip member profile enrichment'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip data validation (not recommended)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    try:
        # Show what we're about to do
        print("🏛️  CapitolScope Congressional Data Import")
        print("-" * 50)
        
        if args.csvs:
            print(f"📁 Mode: Import from CSV files")
            print(f"📂 Directory: {args.csv_directory}")
            print(f"⏱️  Expected time: 2-5 minutes")
        elif args.live:
            years_str = f"({', '.join(map(str, args.years))})" if args.years else "(2014-2025)"
            print(f"🔄 Mode: Fetch live data {years_str}")
            print(f"⏱️  Expected time: 10-15 minutes")
        elif args.hybrid:
            print(f"🔄 Mode: Hybrid (CSVs + latest live data)")
            print(f"⏱️  Expected time: 12-20 minutes")
        
        if not args.skip_enrichment:
            print(f"👥 Will enrich member profiles with additional data")
        if not args.skip_validation:
            print(f"🔍 Will validate data quality during import")
        print()
        
        # Initialize database
        await init_database()
        
        # Execute based on mode
        if args.csvs:
            results = import_from_csvs(args.csv_directory)
            mode = "CSV Import"
            
        elif args.live:
            results = await fetch_live_data(args.years)
            mode = "Live Fetch"
            
        elif args.hybrid:
            # First import existing CSVs
            logger.info("📁 Step 1: Importing existing CSV files...")
            csv_results = import_from_csvs(args.csv_directory)
            
            # Then fetch latest data (just 2025)
            logger.info("🔄 Step 2: Fetching latest live data...")
            live_results = await fetch_live_data([2025])
            
            # Combine results
            results = {
                "csv_files_processed": csv_results.get("csv_files_processed", 0),
                "years_processed": 1,  # Just 2025
                "total_members": csv_results.get("total_members", 0) + live_results.get("total_members", 0),
                "total_trades": csv_results.get("total_trades", 0) + live_results.get("total_trades", 0),
                "failed_trades": csv_results.get("failed_trades", 0) + live_results.get("failed_trades", 0),
                "validation_report": live_results.get("validation_report", ""),
                "validation_stats": live_results.get("validation_stats", {})
            }
            mode = "Hybrid Import"
        
        # Enrich member profiles (unless skipped)
        if not args.skip_enrichment:
            enrich_results = enrich_members()
            results["members_enriched"] = enrich_results.get("members_enriched", 0)
        
        # Print summary
        print_results_summary(results, mode)
        
        # Next steps
        print("\n🎯 NEXT STEPS:")
        print("1. Start the API server:")
        print("   cd app && python -m uvicorn main:app --reload")
        print("2. View transactions in database:")
        print("   psql -d capitolscope -c 'SELECT COUNT(*) FROM congressional_trades;'")
        print("3. Check member profiles:")
        print("   psql -d capitolscope -c 'SELECT COUNT(*) FROM congress_members;'")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Import interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 