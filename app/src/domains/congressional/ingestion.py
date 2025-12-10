"""
Congressional data ingestion pipeline with enhanced data quality processing.

This module handles the import and processing of congressional trade data with focus on:
- Enhanced ticker extraction from asset descriptions
- Amount range standardization and garbage character removal
- Owner field normalization and validation
- Comprehensive data quality reporting and batch processing
"""

import re
import csv as pycsv  # Avoid conflict with csv module
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from pathlib import Path
from decimal import Decimal

from fuzzywuzzy import fuzz, process
from sqlalchemy import text, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.database import db_manager
from domains.congressional.models import CongressMember, CongressionalTrade
from domains.congressional.schemas import TradeOwner, FilingStatus, TransactionType
from domains.congressional.data_quality import DataQualityEnhancer, QualityReport, ImportStatistics
from domains.securities.models import Security

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """Raw trade record from import source."""
    doc_id: str
    member_name: str
    raw_asset_description: str
    transaction_type: str
    transaction_date: date
    notification_date: date
    owner: str
    amount: str
    filing_status: Optional[str] = None
    comment: Optional[str] = None
    cap_gains_over_200: bool = False
    
    # Processing metadata
    source_line: str = ""
    line_number: int = 0
    batch_id: Optional[str] = None

@dataclass
class ProcessedTrade:
    """Processed trade record with enhanced data quality."""
    # Original fields
    doc_id: str
    member_id: int
    raw_asset_description: str
    transaction_type: str
    transaction_date: date
    notification_date: date
    owner: TradeOwner
    amount_min: Optional[int]
    amount_max: Optional[int]
    amount_exact: Optional[int]
    filing_status: Optional[FilingStatus]
    comment: Optional[str]
    cap_gains_over_200: bool
    
    # Enhanced fields
    ticker: Optional[str]
    asset_name: Optional[str]
    asset_type: Optional[str]
    security_id: Optional[int]
    
    # Quality metrics
    ticker_confidence: Decimal
    amount_confidence: Decimal
    parsed_successfully: bool
    parsing_notes: List[str] = field(default_factory=list)
    
    # Validation flags
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


class CongressionalDataIngestion:
    """Enhanced congressional data ingestion with quality processing."""
    
    def __init__(self, batch_size: int = 50, session: Optional[Session] = None):  # Reduced from 100 to 50
        self.batch_size = batch_size
        self.data_quality = DataQualityEnhancer()
        self.statistics = ImportStatistics()
        self.external_session = session  # For sync operations
        # Error collector
        self.error_counts = {}
        self.error_samples = {}
        self.error_records = []
        
        # Load reference data
        self._load_ticker_database()
        self._load_member_mapping()
        self._load_company_ticker_mapping()
        
        # Processing state
        self.current_batch = []
        self.processed_records = 0
        self.failed_records = 0
        self.session: Optional[Session] = None
        
    def record_error(self, category, doc_id, member_name, message, row=None):
        self.error_counts[category] = self.error_counts.get(category, 0) + 1
        if category not in self.error_samples:
            self.error_samples[category] = []
        if len(self.error_samples[category]) < 5:
            self.error_samples[category].append({'doc_id': doc_id, 'member_name': member_name, 'message': message})
        # For CSV export
        self.error_records.append({'category': category, 'doc_id': doc_id, 'member_name': member_name, 'message': message, 'row': str(row) if row else ''})

    def _load_ticker_database(self):
        """Load known ticker symbols from securities table."""
        with db_manager.sync_session_scope() as session:  # Use sync session scope
            securities = session.query(Security).filter(Security.is_active == True).all()
            
            self.known_tickers = {s.ticker.upper() for s in securities}
            self.ticker_to_security = {s.ticker.upper(): s for s in securities}
            
            # Also store by name for fuzzy matching
            self.company_names = {s.name.upper(): s.ticker.upper() for s in securities}
            
        logger.info(f"Loaded {len(self.known_tickers)} known tickers")
    
    def _load_member_mapping(self):
        """Load congress member name to ID mapping."""
        with db_manager.sync_session_scope() as session:  # Use sync session scope
            members = session.query(CongressMember).all()
            
            self.member_mapping = {}
            for member in members:
                # Create variations of member names
                variations = [
                    member.full_name.upper(),
                    f"{member.first_name} {member.last_name}".upper(),
                    f"{member.last_name}, {member.first_name}".upper(),
                ]
                
                for variation in variations:
                    self.member_mapping[variation] = member.id
                    
        logger.info(f"Loaded {len(self.member_mapping)} member name mappings")
    
    def _load_company_ticker_mapping(self):
        """Load enhanced company name to ticker mapping."""
        # Common company name patterns that map to tickers
        self.company_ticker_mapping = {
            'APPLE INC': 'AAPL',
            'MICROSOFT CORP': 'MSFT',
            'AMAZON.COM INC': 'AMZN',
            'ALPHABET INC': 'GOOGL',
            'TESLA INC': 'TSLA',
            'META PLATFORMS INC': 'META',
            'NVIDIA CORP': 'NVDA',
            'BERKSHIRE HATHAWAY': 'BRK.B',
            'JOHNSON & JOHNSON': 'JNJ',
            'EXXON MOBIL CORP': 'XOM',
            'JPMORGAN CHASE & CO': 'JPM',
            'BANK OF AMERICA CORP': 'BAC',
            'COCA COLA CO': 'KO',
            'WALMART INC': 'WMT',
            'PROCTER & GAMBLE': 'PG',
            'VISA INC': 'V',
            'MASTERCARD INC': 'MA',
            'UNITED HEALTH GROUP': 'UNH',
            'HOME DEPOT INC': 'HD',
            'DISNEY WALT CO': 'DIS',
            'VERIZON COMMUNICATIONS': 'VZ',
            'AT&T INC': 'T',
            'CHEVRON CORP': 'CVX',
            'PFIZER INC': 'PFE',
            'ABBVIE INC': 'ABBV',
            'MERCK & CO': 'MRK',
            'BRISTOL MYERS SQUIBB': 'BMY',
            'INTEL CORP': 'INTC',
            'CISCO SYSTEMS': 'CSCO',
            'ORACLE CORP': 'ORCL',
            'SALESFORCE INC': 'CRM',
            'NETFLIX INC': 'NFLX',
            'ADOBE INC': 'ADBE',
            'PAYPAL HOLDINGS': 'PYPL',
            'COMCAST CORP': 'CMCSA',
            'PEPSICO INC': 'PEP',
            'THERMO FISHER SCIENTIFIC': 'TMO',
            'COSTCO WHOLESALE': 'COST',
            'DANAHER CORP': 'DHR',
            'TEXAS INSTRUMENTS': 'TXN',
            'MEDTRONIC PLC': 'MDT',
            'UNION PACIFIC CORP': 'UNP',
            'MCDONALD\'S CORP': 'MCD',
            'LOCKHEED MARTIN': 'LMT',
            'GOLDMAN SACHS GROUP': 'GS',
            'MORGAN STANLEY': 'MS',
            'AMERICAN EXPRESS': 'AXP',
            'NIKE INC': 'NKE',
            'CATERPILLAR INC': 'CAT',
            'BOEING CO': 'BA',
            'IBM CORP': 'IBM',
            'GENERAL ELECTRIC': 'GE',
            'FORD MOTOR CO': 'F',
            'GENERAL MOTORS': 'GM',
            'STARBUCKS CORP': 'SBUX',
            'TIKTOK': None,  # Not publicly traded
            'CRYPTOCURRENCY': None,  # Not a single ticker
            'BITCOIN': None,  # Not a traditional ticker
            'ETHEREUM': None,  # Not a traditional ticker
        }
        
        # ETF and Index mappings
        self.etf_mappings = {
            'SPDR S&P 500 ETF': 'SPY',
            'ISHARES RUSSELL 2000 ETF': 'IWM',
            'VANGUARD TOTAL STOCK MARKET': 'VTI',
            'INVESCO QQQ': 'QQQ',
            'ISHARES CORE S&P 500': 'IVV',
            'VANGUARD S&P 500': 'VOO',
            'VANGUARD FTSE DEVELOPED': 'VEA',
            'VANGUARD FTSE EMERGING': 'VWO',
            'ISHARES MSCI EAFE': 'EFA',
            'ISHARES MSCI EMERGING': 'EEM',
            'FINANCIAL SELECT SECTOR': 'XLF',
            'TECHNOLOGY SELECT SECTOR': 'XLK',
            'HEALTH CARE SELECT SECTOR': 'XLV',
            'ENERGY SELECT SECTOR': 'XLE',
            'CONSUMER DISCRETIONARY': 'XLY',
            'CONSUMER STAPLES': 'XLP',
            'INDUSTRIAL SELECT SECTOR': 'XLI',
            'MATERIALS SELECT SECTOR': 'XLB',
            'UTILITIES SELECT SECTOR': 'XLU',
            'REAL ESTATE SELECT SECTOR': 'XLRE',
        }
        
        # Combine all mappings
        self.company_ticker_mapping.update(self.etf_mappings)
        
    def process_csv_file(self, csv_path: str, member_name: str = None) -> QualityReport:
        """Process a CSV file of congressional trades."""
        logger.info(f"Processing CSV file: {csv_path}")
        
        self.statistics.reset()
        self.statistics.import_start_time = datetime.now()
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                # Detect CSV format
                dialect = pycsv.Sniffer().sniff(file.read(1024))
                file.seek(0)
                
                reader = pycsv.DictReader(file, dialect=dialect)
                
                # Process in batches
                with db_manager.sync_session_scope() as session:  # Use sync session scope
                    self.session = session
                    batch = []
                    total_rows = 0
                    last_progress_time = datetime.now()
                    
                    for row_num, row in enumerate(reader, 1):
                        # Add progress indicator every 1000 rows
                        if row_num % 1000 == 0:
                            current_time = datetime.now()
                            elapsed = (current_time - last_progress_time).total_seconds()
                            logger.info(f"Processed {row_num} rows from CSV file (elapsed: {elapsed:.1f}s)")
                            last_progress_time = current_time
                        
                        try:
                            # Convert row to TradeRecord
                            trade_record = self._parse_csv_row(row, row_num)
                            if trade_record:
                                batch.append(trade_record)
                                total_rows += 1
                                
                                # Process batch when full
                                # logger.info(f"Processing batch of {len(batch)} records")
                                # logger.info(f"Batch: {batch[0]}")
                                # logger.info(f"Batch size: {self.batch_size}")
                                if len(batch) >= self.batch_size:
                                    self._process_batch(batch)
                                    batch = []
                                    
                        except Exception as e:
                            self.record_error('parse_error', row.get('DocID', ''), row.get('Member', ''), str(e), row)
                            logger.error(f"Error processing row {row_num}: {e}")
                            self.statistics.processing_errors += 1
                    
                    # Process final batch
                    if batch:
                        self._process_batch(batch)
                        
                    logger.info(f"Completed processing CSV file. Total rows processed: {total_rows}")
                    
        except Exception as e:
            self.record_error('parse_error', '', '', str(e), None)
            logger.error(f"Error processing CSV file: {e}")
            self.statistics.processing_errors += 1
            
        finally:
            self.statistics.import_end_time = datetime.now()
            self.session = None
            
        return self._generate_quality_report()
    
    def _parse_csv_row(self, row: Dict[str, str], row_num: int) -> Optional[TradeRecord]:
        """Parse a CSV row into a TradeRecord."""
        try:
            # Map CSV columns to our fields (matching actual congressional data format)
            doc_id = row.get('DocID', row.get('doc_id', row.get('Document ID', row.get('document_id', f"unknown_{row_num}"))))
            
            # Handle member name - combine prefix, first name, and last name
            prefix = row.get('Prefix', '').strip()
            first_name = row.get('FirstName', row.get('first_name', '')).strip()
            last_name = row.get('LastName', row.get('last_name', '')).strip()
            member_name = f"{prefix} {first_name} {last_name}".strip()
            
            raw_asset = row.get('Asset', row.get('raw_asset_description', row.get('asset', '')))
            transaction_type = row.get('Transaction Type', row.get('transaction_type', row.get('Type', row.get('type', ''))))
            owner = row.get('Owner', row.get('owner', ''))
            amount = row.get('Amount', row.get('amount', ''))
            
            # Parse dates with fallback and notes
            transaction_date_str = row.get('Transaction Date', row.get('transaction_date', ''))
            notification_date_str = row.get('Notification Date', row.get('notification_date', ''))
            transaction_date = self._parse_date(transaction_date_str)
            notification_date = self._parse_date(notification_date_str)
            date_notes = []
            if not transaction_date:
                # Try notification date as fallback
                if notification_date:
                    transaction_date = notification_date
                    date_notes.append('transaction_date_inferred_from_notification_date')
                else:
                    # Try extracting a date from description text as last resort
                    description_text = row.get('Description', '') or row.get('comment', '') or ''
                    inferred_date = self._parse_date(description_text)
                    if inferred_date:
                        transaction_date = inferred_date
                        date_notes.append('transaction_date_inferred_from_description')
                # If still no valid transaction date, record error
                if not transaction_date:
                    self.record_error('invalid_date', doc_id, member_name, f"Invalid or missing transaction date: {transaction_date_str}", row)
                    return None
            if not all([doc_id, member_name, raw_asset, transaction_type, transaction_date]):
                msg = f"Missing required fields: doc_id={doc_id}, member_name={member_name}, raw_asset={raw_asset}, transaction_type={transaction_type}, transaction_date={transaction_date}"
                self.record_error('missing_field', doc_id, member_name, msg, row)
                return None
            return TradeRecord(
                doc_id=doc_id,
                member_name=member_name,
                raw_asset_description=raw_asset.strip(),
                transaction_type=transaction_type.strip(),
                transaction_date=transaction_date,
                notification_date=notification_date or transaction_date,
                owner=owner.strip(),
                amount=amount.strip(),
                filing_status=row.get('Filing Status', row.get('filing_status', '')),
                comment=row.get('Description', row.get('comment', '')),
                cap_gains_over_200=row.get('cap_gains_over_200', '').lower() == 'true',
                source_line=str(row),
                line_number=row_num
            )
        except Exception as e:
            self.record_error('parse_error', row.get('DocID', ''), row.get('Member', ''), str(e), row)
            logger.error(f"Error parsing row {row_num}: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string with multiple format support and sanitization.

        Handles placeholders like 'S', '[ST]', words leaking into the field,
        and scans arbitrary text to extract a date token if needed.
        """
        if not date_str:
            return None
        
        # Normalize input to string
        raw = str(date_str).strip()
        if not raw:
            return None
        
        # Fast reject common non-dates/placeholders
        placeholders = {"S", "[ST]", "ST", "N/A", "NA", "NONE", "-"}
        if raw.upper() in placeholders:
            return None
        
        # If the string is clearly just a year with 2 or 4 digits, try to coerce
        if raw.isdigit():
            if len(raw) == 4:
                # Year-only -> choose Jan 1 of that year
                try:
                    return date(int(raw), 1, 1)
                except ValueError:
                    pass
            elif len(raw) == 2:
                # Two-digit year, assume 20xx for 00-30 else 19xx
                try:
                    yy = int(raw)
                    century = 2000 if yy <= 30 else 1900
                    return date(century + yy, 1, 1)
                except ValueError:
                    pass
        
        # Try structured formats first
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%m/%d/%Y %H:%M:%S',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        
        # Handle two-digit year in slash format (e.g., 2/18/22)
        try:
            mdy = datetime.strptime(raw, '%m/%d/%y').date()
            # Normalize 2-digit year into 19xx/20xx similar to above assumption
            yy = int(raw.split('/')[-1])
            century = 2000 if yy <= 30 else 1900
            return date(century + mdy.year % 100, mdy.month, mdy.day)
        except ValueError:
            pass
        
        # As a last resort, scan the string for a date token using regex
        # - ISO: YYYY-MM-DD
        # - M/D/YY(YY)
        iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", raw)
        if iso_match:
            try:
                y, m, d = map(int, iso_match.groups())
                return date(y, m, d)
            except ValueError:
                pass
        mdy_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", raw)
        if mdy_match:
            try:
                m, d, y = mdy_match.groups()
                m = int(m)
                d = int(d)
                if len(y) == 2:
                    yy = int(y)
                    y = 2000 + yy if yy <= 30 else 1900 + yy
                else:
                    y = int(y)
                return date(y, m, d)
            except ValueError:
                pass
        
        logger.warning(f"Could not parse date: {raw}")
        return None
    
    def _process_batch(self, batch: List[TradeRecord]):
        """Process a batch of trade records with transaction management."""
        # logger.info(f"Processing batch of {len(batch)} records")
        
        try:
            processed_trades = []
            start_time = datetime.now()
            
            for i, trade_record in enumerate(batch):
                # Add progress indicator every 1000 records
                if i % 1000 == 0 and i > 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Processed {i}/{len(batch)} records in current batch (elapsed: {elapsed:.1f}s)")
                
                # Add timeout check - if processing takes too long, skip remaining records
                if i > 0 and (datetime.now() - start_time).total_seconds() > 300:  # 5 minute timeout
                    logger.warning(f"Batch processing timeout after {i} records, skipping remaining {len(batch) - i} records")
                    break
                
                processed_trade = self._process_single_trade(trade_record)
                if processed_trade:
                    processed_trades.append(processed_trade)
                    
            # Insert valid trades
            valid_trades = [t for t in processed_trades if t.is_valid]
            self._insert_trades(valid_trades)
            
            # Update statistics
            self.statistics.records_processed += len(batch)
            self.statistics.records_successful += len(valid_trades)
            self.statistics.records_failed += len(batch) - len(valid_trades)
            
            # Log batch summary
            elapsed = (datetime.now() - start_time).total_seconds()
            # logger.info(f"Batch processed: {len(valid_trades)}/{len(batch)} successful (elapsed: {elapsed:.1f}s)")
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            self.statistics.processing_errors += 1
            # Rollback handled by session_scope context manager
            
    def _process_single_trade(self, trade_record: TradeRecord) -> Optional[ProcessedTrade]:
        """Process a single trade record with quality enhancement."""
        try:
            # Increment processed records counter
            self.processed_records += 1
            
            # Get member ID, pass trade_record for auto-creation
            member_id = self._resolve_member_id(trade_record.member_name, trade_record)
            if not member_id:
                # Only log warnings occasionally to reduce spam
                if self.processed_records % 100 == 0:
                    logger.warning(f"Could not resolve member: {trade_record.member_name}")
                self.record_error('member_not_found', trade_record.doc_id, trade_record.member_name, 'Could not resolve member', trade_record.source_line)
                return None
                
            # Enhance ticker extraction
            ticker_result = self.data_quality.extract_ticker(trade_record.raw_asset_description)
            
            # Normalize amount
            amount_result = self.data_quality.normalize_amount(trade_record.amount)
            
            # Normalize owner
            owner_result = self.data_quality.normalize_owner(trade_record.owner)
            
            # Resolve security ID
            security_id = None
            if ticker_result.ticker:
                security_id = self._resolve_security_id(ticker_result.ticker)
                
            # Create processed trade
            processed_trade = ProcessedTrade(
                doc_id=trade_record.doc_id,
                member_id=member_id,
                raw_asset_description=trade_record.raw_asset_description,
                transaction_type=trade_record.transaction_type,
                transaction_date=trade_record.transaction_date,
                notification_date=trade_record.notification_date,
                owner=owner_result.normalized_owner,
                amount_min=amount_result.amount_min,
                amount_max=amount_result.amount_max,
                amount_exact=amount_result.amount_exact,
                filing_status=self._parse_filing_status(trade_record.filing_status),
                comment=trade_record.comment,
                cap_gains_over_200=trade_record.cap_gains_over_200,
                ticker=ticker_result.ticker,
                asset_name=ticker_result.asset_name,
                asset_type=ticker_result.asset_type,
                security_id=security_id,
                ticker_confidence=ticker_result.confidence,
                amount_confidence=amount_result.confidence,
                parsed_successfully=True,
                parsing_notes=ticker_result.notes + amount_result.notes + owner_result.notes
            )
            
            # Validate trade
            self._validate_trade(processed_trade)
            
            return processed_trade
            
        except Exception as e:
            self.record_error('unknown', getattr(trade_record, 'doc_id', ''), getattr(trade_record, 'member_name', ''), str(e), getattr(trade_record, 'source_line', ''))
            logger.error(f"Error processing trade: {e}")
            return None
    
    def _resolve_member_id(self, member_name: str, trade_record: 'TradeRecord' = None) -> Optional[int]:
        """Resolve member name to ID with fuzzy matching and auto-creation if not found."""
        if not member_name:
            return None
            
        # Normalize and split name
        normalized_name = member_name.upper().strip()
        name_parts = normalized_name.split()
        first_name = name_parts[1] if len(name_parts) > 1 else ''
        last_name = name_parts[-1] if len(name_parts) > 0 else ''

        # Try exact match first
        if normalized_name in self.member_mapping:
            return self.member_mapping[normalized_name]
            
        # Try first + last name only (ignore prefix)
        fl_name = f"{first_name} {last_name}".strip().upper()
        if fl_name in self.member_mapping:
            return self.member_mapping[fl_name]

        # Try last, first
        lf_name = f"{last_name}, {first_name}".strip().upper()
        if lf_name in self.member_mapping:
            return self.member_mapping[lf_name]

        # Try partial match on first name (case-insensitive)
        for key in self.member_mapping.keys():
            if last_name in key and (first_name[:2] in key):
                logger.debug(f"Partial match for member: {member_name} -> {key}")
                return self.member_mapping[key]

        # Fuzzy match with lower threshold
        best_match = process.extractOne(
            fl_name,
            self.member_mapping.keys(),
            scorer=fuzz.ratio,
            score_cutoff=70
        )
        if best_match:
            logger.debug(f"Fuzzy matched member: {member_name} -> {best_match[0]}")
            return self.member_mapping[best_match[0]]
            
        # If still not found, auto-create member if trade_record is provided
        if trade_record:
            new_member_id = self.create_member_from_trade(trade_record)
            if new_member_id:
                logger.info(f"Auto-created new member: {trade_record.member_name}")
                return new_member_id

        return None
    
    def create_member_from_trade(self, trade_record: 'TradeRecord') -> Optional[int]:
        """Create a new CongressMember from trade record and add to DB. Log and export."""
        # Only use first and last name, ignore prefix
        name_parts = trade_record.member_name.strip().split()
        first_name = name_parts[1] if len(name_parts) > 1 else ''
        last_name = name_parts[-1] if len(name_parts) > 0 else ''
        full_name = f"{first_name} {last_name}".strip()
        # Check for duplicate (same first and last name)
        with db_manager.sync_session_scope() as session:
            existing = session.query(CongressMember).filter(
                CongressMember.first_name.ilike(first_name),
                CongressMember.last_name.ilike(last_name)
            ).first()
            if existing:
                logger.debug(f"Duplicate member found, not auto-creating: {full_name}")
                return existing.id
            # Create new member
            new_member = CongressMember(
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                prefix=name_parts[0] if len(name_parts) > 2 else None,
                party=None,
                chamber=None,
                state=None,
                district=None
            )
            session.add(new_member)
            session.commit()
            # Add to mapping for future lookups
            variations = [
                full_name.upper(),
                f"{first_name} {last_name}".upper(),
                f"{last_name}, {first_name}".upper(),
            ]
            for variation in variations:
                self.member_mapping[variation] = new_member.id
            # Log and export
            self.auto_created_members = getattr(self, 'auto_created_members', [])
            self.auto_created_members.append({
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'prefix': name_parts[0] if len(name_parts) > 2 else '',
                'source_doc_id': trade_record.doc_id,
                'source_line': trade_record.source_line
            })
            logger.debug(f"Auto-created member: {full_name}")
            return new_member.id

    def export_auto_created_members(self, path='logs/auto_created_members.csv'):
        if not hasattr(self, 'auto_created_members') or not self.auto_created_members:
            return
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['first_name', 'last_name', 'full_name', 'prefix', 'source_doc_id', 'source_line']
            writer = pycsv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for rec in self.auto_created_members:
                writer.writerow(rec)

    def _resolve_security_id(self, ticker: str) -> Optional[int]:
        """Resolve ticker to security ID."""
        if not ticker:
            return None
            
        ticker_upper = ticker.upper()
        security = self.ticker_to_security.get(ticker_upper)
        return security.id if security else None
    
    def _parse_filing_status(self, status: str) -> Optional[FilingStatus]:
        """Parse filing status string."""
        if not status:
            return None
            
        status_map = {
            'N': FilingStatus.NEW,
            'P': FilingStatus.PARTIAL,
            'A': FilingStatus.AMENDMENT,
            'NEW': FilingStatus.NEW,
            'PARTIAL': FilingStatus.PARTIAL,
            'AMENDMENT': FilingStatus.AMENDMENT,
        }
        
        return status_map.get(status.upper())
    
    def _validate_trade(self, trade: ProcessedTrade):
        """Validate a processed trade record."""
        errors = []
        
        # Required fields
        if not trade.doc_id:
            errors.append("Missing document ID")
        if not trade.member_id:
            errors.append("Missing member ID")
        if not trade.transaction_date:
            errors.append("Missing transaction date")
        if not trade.transaction_type:
            errors.append("Missing transaction type")
            
        # Transaction type validation
        if trade.transaction_type not in ['P', 'S', 'E']:
            errors.append(f"Invalid transaction type: {trade.transaction_type}")
            
        # Amount validation
        if not any([trade.amount_min, trade.amount_max, trade.amount_exact]):
            errors.append("Missing amount information")
            
        # Owner validation
        if not trade.owner:
            errors.append("Missing owner information")
            
        # Date validation
        if trade.notification_date and trade.transaction_date:
            if trade.notification_date < trade.transaction_date:
                errors.append("Notification date cannot be before transaction date")
                
        trade.validation_errors = errors
        trade.is_valid = len(errors) == 0
    
    def _insert_trades(self, trades: List[ProcessedTrade]):
        """Insert processed trades into database with diagnostics."""
        if not trades:
            logger.debug("No trades to insert.")
            return
        logger.debug(f"Attempting to insert {len(trades)} trades.")
        inserted = 0
        for trade in trades:
            try:
                existing = self.session.query(CongressionalTrade).filter(
                    CongressionalTrade.doc_id == trade.doc_id,
                    CongressionalTrade.member_id == trade.member_id,
                    CongressionalTrade.transaction_date == trade.transaction_date,
                    CongressionalTrade.raw_asset_description == trade.raw_asset_description
                ).first()
                if existing:
                    logger.debug(f"Duplicate trade found, skipping: {trade.doc_id}")
                    continue
                db_trade = CongressionalTrade(
                    doc_id=trade.doc_id,
                    member_id=trade.member_id,
                    security_id=trade.security_id,
                    raw_asset_description=trade.raw_asset_description,
                    ticker=trade.ticker,
                    asset_name=trade.asset_name,
                    asset_type=trade.asset_type,
                    transaction_type=trade.transaction_type,
                    transaction_date=trade.transaction_date,
                    notification_date=trade.notification_date,
                    owner=trade.owner.value if trade.owner else None,
                    amount_min=trade.amount_min,
                    amount_max=trade.amount_max,
                    amount_exact=trade.amount_exact,
                    filing_status=trade.filing_status.value if trade.filing_status else None,
                    comment=trade.comment,
                    cap_gains_over_200=trade.cap_gains_over_200,
                    ticker_confidence=trade.ticker_confidence,
                    amount_confidence=trade.amount_confidence,
                    parsed_successfully=trade.parsed_successfully,
                    parsing_notes='; '.join(trade.parsing_notes) if trade.parsing_notes else None
                )
                self.session.add(db_trade)
                inserted += 1
            except Exception as e:
                logger.error(f"Error inserting trade: {e}")
                self.record_error('db_insert_error', getattr(trade, 'doc_id', ''), getattr(trade, 'member_id', ''), str(e), str(trade))
                continue
        try:
            self.session.commit()
            logger.debug(f"Committed {inserted} trades to the database.")
            
            # NEW: Trigger notifications for new trades
            if inserted > 0:
                self._trigger_trade_notifications(trades[:inserted])
                
        except Exception as e:
            logger.error(f"DB commit failed: {e}")
            self.record_error('db_commit_error', '', '', str(e), '')
            self.session.rollback()
        logger.info(f"Inserted {inserted} trades")
    
    def _trigger_trade_notifications(self, trades: List[ProcessedTrade]):
        """Trigger notification processing for newly inserted trades."""
        try:
            # Import here to avoid circular imports
            from background.tasks import process_new_trade_notifications
            
            for trade in trades:
                try:
                    # Schedule background task for each new trade
                    # We pass the doc_id and member_id to find the trade later
                    process_new_trade_notifications.delay(
                        doc_id=trade.doc_id,
                        member_id=str(trade.member_id),
                        transaction_date=trade.transaction_date.isoformat()
                    )
                    logger.debug(f"Scheduled notification task for trade {trade.doc_id}")
                except Exception as e:
                    logger.error(f"Failed to schedule notification for trade {trade.doc_id}: {e}")
            
            logger.info(f"Triggered notification processing for {len(trades)} new trades")
            
        except Exception as e:
            logger.error(f"Error triggering trade notifications: {e}")
            # Don't raise - notifications failing shouldn't break ingestion
    
    def _generate_quality_report(self) -> QualityReport:
        """Generate comprehensive quality report."""
        return QualityReport(
            total_records=self.statistics.records_processed,
            successful_records=self.statistics.records_successful,
            failed_records=self.statistics.records_failed,
            processing_errors=self.statistics.processing_errors,
            ticker_extraction_rate=self._calculate_ticker_extraction_rate(),
            amount_parsing_rate=self._calculate_amount_parsing_rate(),
            owner_normalization_rate=self._calculate_owner_normalization_rate(),
            duplicate_count=self._count_duplicates(),
            processing_time=self.statistics.processing_time_seconds,
            recommendations=self._generate_recommendations()
        )
    
    def _calculate_ticker_extraction_rate(self) -> float:
        """Calculate ticker extraction success rate."""
        if not self.session:
            return 0.0
            
        total_trades = self.session.query(CongressionalTrade).count()
        trades_with_ticker = self.session.query(CongressionalTrade).filter(
            CongressionalTrade.ticker.isnot(None)
        ).count()
        
        return (trades_with_ticker / total_trades) * 100 if total_trades > 0 else 0.0
    
    def _calculate_amount_parsing_rate(self) -> float:
        """Calculate amount parsing success rate."""
        if not self.session:
            return 0.0
            
        total_trades = self.session.query(CongressionalTrade).count()
        trades_with_amount = self.session.query(CongressionalTrade).filter(
            or_(
                CongressionalTrade.amount_min.isnot(None),
                CongressionalTrade.amount_max.isnot(None),
                CongressionalTrade.amount_exact.isnot(None)
            )
        ).count()
        
        return (trades_with_amount / total_trades) * 100 if total_trades > 0 else 0.0
    
    def _calculate_owner_normalization_rate(self) -> float:
        """Calculate owner normalization success rate."""
        if not self.session:
            return 0.0
            
        total_trades = self.session.query(CongressionalTrade).count()
        trades_with_valid_owner = self.session.query(CongressionalTrade).filter(
            CongressionalTrade.owner.in_(['C', 'SP', 'JT', 'DC'])
        ).count()
        
        return (trades_with_valid_owner / total_trades) * 100 if total_trades > 0 else 0.0
    
    def _count_duplicates(self) -> int:
        """Count duplicate trades in database."""
        if not self.session:
            return 0
            
        # Count trades with identical key fields
        query = text("""
            SELECT COUNT(*) - COUNT(DISTINCT doc_id, member_id, transaction_date, raw_asset_description)
            FROM congressional_trades
        """)
        
        result = self.session.execute(query).scalar()
        return result or 0
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on quality metrics."""
        recommendations = []
        
        ticker_rate = self._calculate_ticker_extraction_rate()
        amount_rate = self._calculate_amount_parsing_rate()
        owner_rate = self._calculate_owner_normalization_rate()
        
        if ticker_rate < 80:
            recommendations.append("Consider expanding ticker extraction patterns")
        if amount_rate < 95:
            recommendations.append("Review amount parsing logic for edge cases")
        if owner_rate < 99:
            recommendations.append("Investigate owner field data quality issues")
        if self.statistics.processing_errors > 0:
            recommendations.append("Review processing errors and improve error handling")
            
        return recommendations
    
    def export_problematic_records(self, output_path: str):
        """Export problematic records to CSV for manual review."""
        logger.info(f"Exporting problematic records to: {output_path}")
        
        with db_manager.session_scope() as session:
            # Query problematic records
            problematic_trades = session.query(CongressionalTrade).filter(
                or_(
                    CongressionalTrade.ticker.is_(None),
                    CongressionalTrade.amount_min.is_(None),
                    CongressionalTrade.amount_max.is_(None),
                    CongressionalTrade.owner.notin_(['C', 'SP', 'JT', 'DC']),
                    CongressionalTrade.parsed_successfully == False
                )
            ).all()
            
            # Export to CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'id', 'doc_id', 'member_id', 'raw_asset_description',
                    'ticker', 'asset_name', 'transaction_type', 'transaction_date',
                    'owner', 'amount_min', 'amount_max', 'amount_exact',
                    'ticker_confidence', 'amount_confidence', 'parsing_notes'
                ]
                
                writer = pycsv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for trade in problematic_trades:
                    writer.writerow({
                        'id': trade.id,
                        'doc_id': trade.doc_id,
                        'member_id': trade.member_id,
                        'raw_asset_description': trade.raw_asset_description,
                        'ticker': trade.ticker,
                        'asset_name': trade.asset_name,
                        'transaction_type': trade.transaction_type,
                        'transaction_date': trade.transaction_date,
                        'owner': trade.owner,
                        'amount_min': trade.amount_min,
                        'amount_max': trade.amount_max,
                        'amount_exact': trade.amount_exact,
                        'ticker_confidence': trade.ticker_confidence,
                        'amount_confidence': trade.amount_confidence,
                        'parsing_notes': trade.parsing_notes
                    })
                    
        logger.info(f"Exported {len(problematic_trades)} problematic records")

    def export_failed_records(self, path='logs/failed_imports.csv'):
        if not self.error_records:
            return
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['category', 'doc_id', 'member_name', 'message', 'row']
            writer = pycsv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for rec in self.error_records:
                writer.writerow(rec)

    def print_error_summary(self):
        summary_lines = ["\n===== IMPORT ERROR SUMMARY ====="]
        for cat, count in self.error_counts.items():
            summary_lines.append(f"  {cat}: {count}")
        summary_lines.append("\nSample errors:")
        for cat, samples in self.error_samples.items():
            summary_lines.append(f"  {cat}:")
            for s in samples:
                summary_lines.append(f"    - DocID: {s['doc_id']}, Member: {s['member_name']}, Msg: {s['message']}")
        if hasattr(self, 'auto_created_members') and self.auto_created_members:
            summary_lines.append(f"\nAuto-created members: {len(self.auto_created_members)} (see logs/auto_created_members.csv)")
        summary = "\n".join(summary_lines)
        print(summary)
        logger.info(summary)

    def import_congressional_data_from_csvs_sync(self, csv_directory: str) -> Dict[str, Any]:
        """
        Import congressional data from CSV files in a directory (synchronous version).
        
        Args:
            csv_directory: Path to directory containing CSV files
            
        Returns:
            Dictionary with import results and statistics
        """
        import os
        from pathlib import Path
        
        logger.info(f"Starting CSV import from directory: {csv_directory}")
        
        csv_dir = Path(csv_directory)
        if not csv_dir.exists():
            raise FileNotFoundError(f"CSV directory not found: {csv_directory}")
        
        # Find all main CSV files (e.g., 2014FD.csv, 2015FD.csv, etc.)
        csv_files = [f for f in csv_dir.glob("[0-9][0-9][0-9][0-9]FD.csv") if f.is_file()]
        if not csv_files:
            logger.warning(f"No main CSV files found in directory: {csv_directory}")
            return {"status": "no_files", "files_processed": 0}
        
        # Process each CSV file
        results = {
            "status": "success",
            "files_processed": 0,
            "total_records": 0,
            "successful_records": 0,
            "failed_records": 0,
            "processing_errors": 0,
            "files": []
        }
        
        # Use external session if provided, otherwise create sync session scope
        if self.external_session:
            session_context = self.external_session
            should_close = False
        else:
            session_context = db_manager.sync_session_scope()  # Use sync session scope
            should_close = True
        
        try:
            if should_close:
                session_context = session_context.__enter__()
            
            self.session = session_context
            
            for csv_file in csv_files:
                try:
                    logger.info(f"Processing CSV file: {csv_file.name}")
                    print(f"📁 Processing: {csv_file.name}")
                    
                    # Process the file
                    report = self.process_csv_file(str(csv_file))
                    
                    # Update results
                    results["files_processed"] += 1
                    results["total_records"] += report.total_records
                    results["successful_records"] += report.successful_records
                    results["failed_records"] += report.failed_records
                    results["processing_errors"] += report.processing_errors
                    
                    # Add file-specific results
                    results["files"].append({
                        "filename": csv_file.name,
                        "total_records": report.total_records,
                        "successful_records": report.successful_records,
                        "failed_records": report.failed_records,
                        "ticker_extraction_rate": report.ticker_extraction_rate,
                        "amount_parsing_rate": report.amount_parsing_rate,
                        "owner_normalization_rate": report.owner_normalization_rate
                    })
                    
                    logger.info(f"Completed processing {csv_file.name}: {report.successful_records}/{report.total_records} successful")
                    
                except Exception as e:
                    logger.error(f"Error processing CSV file {csv_file.name}: {e}")
                    results["processing_errors"] += 1
                    results["files"].append({
                        "filename": csv_file.name,
                        "error": str(e)
                    })
            
            if should_close:
                session_context.__exit__(None, None, None)
                
        except Exception as e:
            if should_close:
                session_context.__exit__(type(e), e, e.__traceback__)
            raise
        finally:
            self.session = None
        
        logger.info(f"CSV import completed: {results['successful_records']}/{results['total_records']} records successful")
        return results

    def enrich_member_data_sync(self) -> Dict[str, Any]:
        """
        Enrich existing member data with additional information (synchronous version).
        
        Returns:
            Dictionary with enrichment results
        """
        logger.info("Starting member data enrichment")
        
        # Use external session if provided, otherwise create sync session scope
        if self.external_session:
            session_context = self.external_session
            should_close = False
        else:
            session_context = db_manager.sync_session_scope()  # Use sync session scope
            should_close = True
        
        results = {
            "status": "success",
            "members_processed": 0,
            "members_enriched": 0,
            "errors": 0,
            "enrichment_details": []
        }
        
        try:
            if should_close:
                session_context = session_context.__enter__()
            
            self.session = session_context
            
            # Get all members
            members = self.session.query(CongressMember).all()
            logger.info(f"Found {len(members)} members to enrich")
            
            for member in members:
                try:
                    results["members_processed"] += 1
                    
                    # Basic enrichment - this could be expanded with more data sources
                    enriched = False
                    
                    # Example: Normalize member names
                    if member.full_name:
                        original_name = member.full_name
                        normalized_name = self._normalize_member_name(member.full_name)
                        if normalized_name != original_name:
                            member.full_name = normalized_name
                            enriched = True
                    
                    # Example: Populate missing fields from existing data
                    if not member.display_name and member.full_name:
                        member.display_name = member.full_name
                        enriched = True
                    
                    # Example: Update party affiliation formatting
                    if member.party:
                        normalized_party = member.party.upper().strip()
                        if normalized_party != member.party:
                            member.party = normalized_party
                            enriched = True
                    
                    if enriched:
                        results["members_enriched"] += 1
                        results["enrichment_details"].append({
                            "member_id": member.id,
                            "name": member.full_name,
                            "changes": "Normalized name and party data"
                        })
                        logger.debug(f"Enriched member: {member.full_name}")
                    
                except Exception as e:
                    logger.error(f"Error enriching member {member.id}: {e}")
                    results["errors"] += 1
            
            # Commit changes
            self.session.commit()
            
            if should_close:
                session_context.__exit__(None, None, None)
                
        except Exception as e:
            if should_close:
                session_context.__exit__(type(e), e, e.__traceback__)
            raise
        finally:
            self.session = None
        
        logger.info(f"Member enrichment completed: {results['members_enriched']}/{results['members_processed']} members enriched")
        return results

    def _normalize_member_name(self, name: str) -> str:
        """Normalize member name format."""
        if not name:
            return name
        
        # Basic normalization
        normalized = name.strip()
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Standardize title case
        normalized = normalized.title()
        
        # Handle common name patterns
        normalized = normalized.replace("Mc ", "Mc")
        normalized = normalized.replace("O'", "O'")
        
        return normalized


def main():
    """Main ingestion function for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Congressional data ingestion')
    parser.add_argument('csv_file', help='Path to CSV file to import')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--export-problems', help='Export problematic records to CSV')
    
    args = parser.parse_args()
    
    # Initialize ingestion
    ingestion = CongressionalDataIngestion(batch_size=args.batch_size)
    
    # Process file
    report = ingestion.process_csv_file(args.csv_file)
    
    # Print summary
    print(f"\n=== Import Summary ===")
    print(f"Total records: {report.total_records}")
    print(f"Successful: {report.successful_records}")
    print(f"Failed: {report.failed_records}")
    print(f"Processing time: {report.processing_time:.2f} seconds")
    print(f"Ticker extraction rate: {report.ticker_extraction_rate:.1f}%")
    print(f"Amount parsing rate: {report.amount_parsing_rate:.1f}%")
    print(f"Owner normalization rate: {report.owner_normalization_rate:.1f}%")
    
    if report.recommendations:
        print(f"\n=== Recommendations ===")
        for rec in report.recommendations:
            print(f"- {rec}")
    
    # Export problematic records if requested
    if args.export_problems:
        ingestion.export_problematic_records(args.export_problems)


if __name__ == "__main__":
    main()