import re
import pandas as pd
import pdfplumber
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class TradeRecord:
    """Structured representation of a trade record"""
    member: str
    doc_id: str
    owner: str
    asset: str
    ticker: str
    transaction_type: str
    transaction_date: str
    notification_date: str
    amount: str
    filing_status: str
    description: str
    first_name: str = ""
    last_name: str = ""
    confidence_score: float = 0.0
    parsing_notes: List[str] = None
    
    def __post_init__(self):
        if self.parsing_notes is None:
            self.parsing_notes = []
        
        # Extract first and last names from description if not already set
        if not self.first_name and not self.last_name:
            self._extract_names_from_description()
    
    def _extract_names_from_description(self):
        """Extract first and last names from description field"""
        if not self.description:
            return
            
        # Look for patterns like "Mr. Lou Barletta", "Ms. Suzan K. DelBene", etc.
        name_patterns = [
            r'(Mr\.|Ms\.|Mrs\.|Dr\.|Sen\.|Rep\.)\s+([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+)',
            r'(Mr\.|Ms\.|Mrs\.|Dr\.|Sen\.|Rep\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, self.description)
            if match:
                full_name = match.group(2).strip()
                # Split the full name into first and last
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    # Handle middle initials
                    if len(name_parts) == 3 and len(name_parts[1]) == 1:
                        # Format: "Suzan K. DelBene" -> first: "Suzan", last: "DelBene"
                        self.first_name = name_parts[0]
                        self.last_name = name_parts[2]
                    else:
                        # Format: "Lou Barletta" -> first: "Lou", last: "Barletta"
                        self.first_name = name_parts[0]
                        self.last_name = name_parts[-1]
                break

class PDFParsingValidator:
    """Validation framework for PDF parsing results"""
    
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
        
        # Define expected patterns
        self.date_patterns = [
            r'\d{2}/\d{2}/\d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        
        self.amount_patterns = [
            r'\$[\d,]+ - \$[\d,]+',
            r'\$[\d,]+',
            r'None'
        ]
        
        self.transaction_types = ['P', 'S', 'S (partial)', 'E']
        self.owner_types = ['SP', 'DC', 'JT']
        
    def validate_trade_record(self, record: TradeRecord) -> Dict[str, List[str]]:
        """Validate a single trade record"""
        errors = []
        warnings = []
        
        # Validate owner type
        if record.owner not in self.owner_types:
            errors.append(f"Invalid owner type: {record.owner}")
            
        # Validate transaction type
        if record.transaction_type not in self.transaction_types:
            errors.append(f"Invalid transaction type: {record.transaction_type}")
            
        # Validate dates
        if not self._is_valid_date(record.transaction_date):
            errors.append(f"Invalid transaction date format: {record.transaction_date}")
            
        if not self._is_valid_date(record.notification_date):
            errors.append(f"Invalid notification date format: {record.notification_date}")
            
        # Validate amount
        if not self._is_valid_amount(record.amount):
            warnings.append(f"Unusual amount format: {record.amount}")
            
        # Cross-validation: notification date should be after transaction date
        try:
            trans_date = datetime.strptime(record.transaction_date, "%m/%d/%Y")
            notif_date = datetime.strptime(record.notification_date, "%m/%d/%Y")
            if notif_date < trans_date:
                warnings.append("Notification date is before transaction date")
        except:
            pass  # Date parsing already handled above
            
        return {"errors": errors, "warnings": warnings}
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date string matches expected patterns"""
        for pattern in self.date_patterns:
            if re.match(pattern, date_str):
                return True
        return False
    
    def _is_valid_amount(self, amount_str: str) -> bool:
        """Check if amount string matches expected patterns"""
        for pattern in self.amount_patterns:
            if re.match(pattern, amount_str):
                return True
        return False

class ImprovedPDFParser:
    """Improved PDF parsing with better structure detection"""
    
    def __init__(self, tickers: set, asset_dict: dict, tickers_company: dict):
        self.tickers = tickers
        self.asset_dict = asset_dict
        self.tickers_company = tickers_company
        self.validator = PDFParsingValidator()
        
        # Regex patterns for better field extraction
        self.ticker_pattern = r'\(([A-Z]{1,5})\)'
        self.amount_range_mapping = {
            "$0": "None",
            "$1": "$1 - $15,000",
            "$1,001": "$1,001 - $15,000",
            "$15,000": "$1,001 - $15,000",
            "$15,001": "$15,001 - $50,000",
            "$50,001": "$50,001 - $100,000",
            "$100,001": "$100,001 - $250,000",
            "$250,001": "$250,001 - $500,000",
            "$500,001": "$500,001 - $1,000,000",
            "$1,000,001": "$1,000,001 - $5,000,000",
            "$5,000,001": "$5,000,001 - $25,000,000"
        }
        
    def parse_pdf_improved(self, pdf_path: str, doc_id: str, member: str) -> List[TradeRecord]:
        """Improved PDF parsing with better structure detection"""
        records = []
        
        with pdfplumber.open(pdf_path) as pdf:
            pdf_text = "".join(page.extract_text() for page in pdf.pages)
            
        if not pdf_text.strip():
            return records
            
        lines = pdf_text.splitlines()
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for trade entry starting lines
            if self._is_trade_line_start(line):
                record, lines_consumed = self._parse_trade_entry(lines[i:], doc_id, member)
                if record:
                    records.append(record)
                i += lines_consumed
            else:
                i += 1
                
        return records
    
    def _is_trade_line_start(self, line: str) -> bool:
        """Improved detection of trade line starts"""
        line = line.strip()
        if not line:
            return False
        
        # Skip header lines and other non-trade content
        if any(skip in line.upper() for skip in [
            'FILING', 'INITIAL', 'CERTIFICATION', 'DIGITALLY', 'ASSET CLASS',
            'LOCATION:', 'SUBHOLDING', 'BEST OF MY', 'TRANSACTION', 'OWNER', 'ASSET',
            'TYPE', 'DATE', 'NOTIFICATION', 'AMOUNT'
        ]):
            return False
        
        # Look for transaction patterns: [Asset] [P/S/E] [Date] [Date] [Amount]
        # Use enhanced transaction type detection
        transaction_type, _, _ = self._enhanced_transaction_type_detection(line)
        has_transaction_type = bool(transaction_type)
        has_date_pattern = bool(re.search(r'\d{1,2}/\d{1,2}/\d{4}', line))
        has_amount_pattern = '$' in line
        
        # A valid trade line should have transaction type, date, and amount
        return has_transaction_type and has_date_pattern and has_amount_pattern
    
    def _parse_trade_entry(self, lines: List[str], doc_id: str, member: str) -> Tuple[Optional[TradeRecord], int]:
        """Parse a complete trade entry spanning multiple lines"""
        if not lines:
            return None, 1
            
        main_line = lines[0].strip()
        lines_consumed = 1
        
        # Parse main line using multiple strategies
        parsed_data = self._parse_main_line(main_line)
        if not parsed_data:
            return None, 1
            
        # Look for continuation lines - extend lookahead like original parser
        additional_data = {}
        
        for i in range(1, len(lines)):  # Look ahead through all remaining lines
            line = lines[i].strip()
            
            # Stop if we hit a new trade line
            if self._is_trade_line_start(line):
                break
                
            # Stop if we hit section breaks
            if line.startswith("* For the") or line.startswith("Initial") or line.startswith("Asset"):
                break
            if any(section in line.upper() for section in ["CERTIFICATION", "DIGITALLY SIGNED", "INITIAL PUBLIC"]):
                break
                
            if self._is_continuation_line(line):
                self._parse_continuation_line(line, additional_data)
                lines_consumed = i + 1
                
        # Merge main data with additional data
        merged_data = {**parsed_data, **additional_data}
        
        # Create trade record
        record = TradeRecord(
            member=member,
            doc_id=doc_id,
            owner=merged_data.get('owner', ''),
            asset=merged_data.get('asset', ''),
            ticker=merged_data.get('ticker', ''),
            transaction_type=merged_data.get('transaction_type', ''),
            transaction_date=merged_data.get('transaction_date', ''),
            notification_date=merged_data.get('notification_date', ''),
            amount=self._normalize_amount(merged_data.get('amount', '')),
            filing_status=merged_data.get('filing_status', 'New'),
            description=merged_data.get('description', '')
        )
        
        # Apply field validation and correction
        record = self._validate_and_fix_field_alignment(record)
        
        # Apply enhanced amount parsing fixes
        record = self._fix_amount_parsing_issues(record)
        
        # Calculate confidence score
        record.confidence_score = self._calculate_confidence_score(record)
        
        # Validate record
        validation_results = self.validator.validate_trade_record(record)
        if validation_results['errors']:
            record.parsing_notes.extend(validation_results['errors'])
        if validation_results['warnings']:
            record.parsing_notes.extend(validation_results['warnings'])
            
        return record, lines_consumed
    
    def _parse_main_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse the main trade line using improved logic"""
        parts = line.split()
        if len(parts) < 2:  # Reduced from 6 to 2 - need at least owner and something else
            return None
            
        # Try multiple parsing strategies
        strategies = [
            self._parse_strategy_standard,
            self._parse_strategy_malformed_line,
            self._parse_strategy_shifted_amounts,
            self._parse_strategy_missing_fields
        ]
        
        for strategy in strategies:
            try:
                result = strategy(parts)
                if result:  # Remove strict validation to match original parser's flexibility
                    return result
            except Exception as e:
                continue
                
        return None
    
    def _parse_strategy_standard(self, parts: List[str]) -> Dict[str, str]:
        """Standard parsing strategy using regex-based field extraction"""
        if len(parts) < 2:
            return {}
        
        # Reconstruct the original line from parts
        line = " ".join(parts)
        
        # Use regex to extract fields from the end of the line
        # Pattern: [Asset Name] [Transaction Type] [Date1] [Date2] [Amount]
        # Transaction Type: P, S, E (single letter)
        # Dates: MM/DD/YYYY format
        # Amount: $X,XXX - $X,XXX format
        
        # Regex pattern to match the trailing fields
        pattern = r'^(.+?)\s+([PSE])\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)$'
        
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            asset_with_owner = match.group(1).strip()
            transaction_type = match.group(2).upper()
            transaction_date = match.group(3)
            notification_date = match.group(4)
            amount = match.group(5).strip()
            
            # For PDFs without explicit owner fields, check if first word looks like an owner type
            asset_parts = asset_with_owner.split(None, 1)
            first_word = asset_parts[0] if asset_parts else ""
            
            # If first word is a known owner type (SP, JT, DC), use it as owner
            if first_word.upper() in ['SP', 'JT', 'DC']:
                owner = first_word.upper()
                asset = asset_parts[1] if len(asset_parts) > 1 else ""
            else:
                # No explicit owner, use default "JT" (Joint) and treat entire match as asset
                owner = "JT"
                asset = asset_with_owner
            
            # Extract ticker from asset
            ticker = self._extract_ticker(asset)
            
            # Clean asset name by removing ticker information
            if ticker:
                asset = re.sub(r'\([^)]*\)', '', asset).strip()
                asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
            
            return {
                'owner': owner,
                'asset': asset,
                'ticker': ticker,
                'transaction_type': transaction_type,
                'transaction_date': transaction_date,
                'notification_date': notification_date,
                'amount': amount,
                'filing_status': "New",
                'description': ""
            }
        
        # Fallback: Try a more flexible pattern for malformed data
        # Look for any single letter followed by dates
        flexible_pattern = r'^(.+?)\s+([PSEpse])\s+(\d{1,2}/\d{1,2}/\d{4})(?:\s+(\d{1,2}/\d{1,2}/\d{4}))?(?:\s+(.+))?$'
        
        flexible_match = re.match(flexible_pattern, line, re.IGNORECASE)
        if flexible_match:
            asset_with_owner = flexible_match.group(1).strip()
            transaction_type = flexible_match.group(2).upper()
            transaction_date = flexible_match.group(3)
            notification_date = flexible_match.group(4) or ""
            amount = flexible_match.group(5) or ""
            
            # For PDFs without explicit owner fields, check if first word looks like an owner type
            asset_parts = asset_with_owner.split(None, 1)
            first_word = asset_parts[0] if asset_parts else ""
            
            # If first word is a known owner type (SP, JT, DC), use it as owner
            if first_word.upper() in ['SP', 'JT', 'DC']:
                owner = first_word.upper()
                asset = asset_parts[1] if len(asset_parts) > 1 else ""
            else:
                # No explicit owner, use default "JT" (Joint) and treat entire match as asset
                owner = "JT"
                asset = asset_with_owner
            
            # Extract ticker from asset
            ticker = self._extract_ticker(asset)
            
            # Clean asset name
            if ticker:
                asset = re.sub(r'\([^)]*\)', '', asset).strip()
                asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
            
            return {
                'owner': owner,
                'asset': asset,
                'ticker': ticker,
                'transaction_type': transaction_type,
                'transaction_date': transaction_date,
                'notification_date': notification_date,
                'amount': amount,
                'filing_status': "New",
                'description': ""
            }
        
        # If regex patterns fail, fall back to the old method but with better field detection
        return self._parse_strategy_fallback(parts)
    
    def _parse_strategy_fallback(self, parts: List[str]) -> Dict[str, str]:
        """Fallback parsing strategy when regex patterns fail"""
        if len(parts) < 2:
            return {}
        
        # Use the original approach but with better validation
        owner = parts[0]
        
        # Try to find transaction type using enhanced detection
        line = " ".join(parts)
        transaction_type, position = self._find_transaction_type_in_context(parts, line)
        transaction_type_idx = None
        
        if transaction_type:
            # Find the index of the part containing the transaction type
            for i, part in enumerate(parts[1:], 1):
                if transaction_type in part.upper() or part.upper() in transaction_type:
                    transaction_type_idx = i
                    break
        
        if transaction_type_idx is None:
            # No valid transaction type found, treat as malformed
            return {
                'owner': owner,
                'asset': " ".join(parts[1:]) if len(parts) > 1 else "",
                'ticker': "",
                'transaction_type': transaction_type if transaction_type else "",
                'transaction_date': "",
                'notification_date': "",
                'amount': "",
                'filing_status': "New",
                'description': ""
            }
        
        # Asset is everything between owner and transaction type
        asset = " ".join(parts[1:transaction_type_idx])
        ticker = self._extract_ticker(asset)
        
        # Clean asset name
        if ticker:
            asset = re.sub(r'\([^)]*\)', '', asset).strip()
            asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
        
        # Extract remaining fields after transaction type
        remaining_parts = parts[transaction_type_idx:]
        
        result = {
            'owner': owner,
            'asset': asset,
            'ticker': ticker,
            'transaction_type': transaction_type if transaction_type else (remaining_parts[0].upper() if remaining_parts else ""),
            'transaction_date': remaining_parts[1] if len(remaining_parts) > 1 else "",
            'notification_date': remaining_parts[2] if len(remaining_parts) > 2 else "",
            'amount': remaining_parts[3] if len(remaining_parts) > 3 else "",
            'filing_status': "New",
            'description': ""
        }
        
        return result
    
    def _parse_strategy_malformed_line(self, parts: List[str]) -> Dict[str, str]:
        """Handle lines where transaction data is embedded in asset field"""
        if len(parts) < 2:
            return {}
        
        line = " ".join(parts)
        
        # Enhanced pattern for malformed lines with multiple variations:
        # 1. "Royal Bank Of Canada   P 08/09/2023 08/11/2023 $15,001" - spaces between asset and transaction
        # 2. "Cree, Inc. P 05/12/2014 05/12/2014 $15,001" - minimal spacing
        # 3. "Apple Inc.   P 01/27/2023 02/06/2023 $1,001" - multiple spaces
        
        # Primary pattern: Asset name followed by transaction type, dates, and amount
        malformed_patterns = [
            # Pattern 1: Multiple spaces between asset and transaction data
            r'^(\w+)\s+(.+?)\s{2,}([PSE])\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)$',
            # Pattern 2: Single space between asset and transaction data
            r'^(\w+)\s+(.+?)\s+([PSE])\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)$',
            # Pattern 3: Asset name with commas/periods followed by transaction data
            r'^(\w+)\s+(.+?[,.])\s*([PSE])\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)$',
            # Pattern 4: No owner prefix, just asset with embedded transaction
            r'^(.+?)\s+([PSE])\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)$'
        ]
        
        for i, pattern in enumerate(malformed_patterns):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                if i < 3:  # Patterns 1-3 have owner prefix
                    owner = match.group(1)
                    asset = match.group(2).strip()
                    transaction_type = match.group(3).upper()
                    transaction_date = match.group(4)
                    notification_date = match.group(5)
                    amount = match.group(6)
                else:  # Pattern 4 - no owner prefix
                    owner = "JT"  # Default to Joint
                    asset = match.group(1).strip()
                    transaction_type = match.group(2).upper()
                    transaction_date = match.group(3)
                    notification_date = match.group(4)
                    amount = match.group(5)
                
                # Clean up asset name - remove trailing punctuation that might be artifacts
                asset = re.sub(r'[,\s]+$', '', asset)
                
                # Extract ticker from asset
                ticker = self._extract_ticker(asset)
                
                # Clean asset name by removing ticker information
                if ticker:
                    asset = re.sub(r'\([^)]*\)', '', asset).strip()
                    asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
                
                # Clean up amount - remove trailing characters that might be artifacts
                amount = re.sub(r'[,\s]+$', '', amount)
                
                return {
                    'owner': owner,
                    'asset': asset,
                    'ticker': ticker,
                    'transaction_type': transaction_type,
                    'transaction_date': transaction_date,
                    'notification_date': notification_date,
                    'amount': amount,
                    'filing_status': "New",
                    'description': ""
                }
        
        # Additional strategy for very malformed lines where we can detect transaction patterns
        # Look for transaction type anywhere in the line followed by dates
        transaction_in_line = re.search(r'\b([PSE])\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s*(.*)$', line, re.IGNORECASE)
        if transaction_in_line:
            # Everything before the transaction type is likely the owner and asset
            prefix = line[:transaction_in_line.start()].strip()
            transaction_type = transaction_in_line.group(1).upper()
            transaction_date = transaction_in_line.group(2)
            notification_date = transaction_in_line.group(3)
            amount = transaction_in_line.group(4).strip()
            
            # Try to split prefix into owner and asset
            prefix_parts = prefix.split(None, 1)
            if len(prefix_parts) >= 2:
                owner = prefix_parts[0]
                asset = prefix_parts[1]
            else:
                owner = "JT"
                asset = prefix
            
            # Extract ticker from asset
            ticker = self._extract_ticker(asset)
            
            # Clean asset name
            if ticker:
                asset = re.sub(r'\([^)]*\)', '', asset).strip()
                asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
            
            return {
                'owner': owner,
                'asset': asset,
                'ticker': ticker,
                'transaction_type': transaction_type,
                'transaction_date': transaction_date,
                'notification_date': notification_date,
                'amount': amount,
                'filing_status': "New",
                'description': ""
            }
        
        return {}
    
    def _parse_strategy_shifted_amounts(self, parts: List[str]) -> Dict[str, str]:
        """Parsing strategy for when amounts are shifted due to missing fields"""
        if len(parts) < 5:
            return {}
        
        asset = parts[1] if len(parts) > 1 else ""
        ticker = self._extract_ticker(asset)
        
        # Clean asset name by removing ticker information
        if ticker:
            asset = re.sub(r'\([^)]*\)', '', asset).strip()
            asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
        
        # Try different field positions for shifted data
        if len(parts) >= 6:
            return {
                'owner': parts[0],
                'asset': asset,
                'ticker': ticker,
                'transaction_type': parts[-4],
                'transaction_date': parts[-3],
                'notification_date': parts[-2],
                'amount': parts[-1],
                'filing_status': "New",
                'description': ""
            }
        else:
            return {
                'owner': parts[0],
                'asset': asset,
                'ticker': ticker,
                'transaction_type': parts[-3] if len(parts) > 3 else "",
                'transaction_date': parts[-2] if len(parts) > 2 else "",
                'notification_date': parts[-1] if len(parts) > 1 else "",
                'amount': "",
                'filing_status': "New",
                'description': ""
            }
    
    def _parse_strategy_missing_fields(self, parts: List[str]) -> Dict[str, str]:
        """Parsing strategy for records with missing or incomplete fields"""
        if len(parts) < 3:
            return {}
        
        asset = parts[1] if len(parts) > 1 else ""
        ticker = self._extract_ticker(asset)
        
        # Clean asset name by removing ticker information
        if ticker:
            asset = re.sub(r'\([^)]*\)', '', asset).strip()
            asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
        
        # Try to extract what we can with minimal validation
        result = {
            'owner': parts[0],
            'asset': asset,
            'ticker': ticker,
            'transaction_type': "",
            'transaction_date': "",
            'notification_date': "",
            'amount': "",
            'filing_status': "New",
            'description': ""
        }
        
        # Try to find transaction type in remaining parts
        for i, part in enumerate(parts[2:], 2):
            if part in ['P', 'S', 'E'] or part.startswith('S (partial)'):
                result['transaction_type'] = part
                # Try to extract dates from subsequent parts
                if i + 2 < len(parts):
                    result['transaction_date'] = parts[i + 1]
                    result['notification_date'] = parts[i + 2]
                if i + 3 < len(parts):
                    result['amount'] = parts[i + 3]
                break
        
        return result
    
    def _validate_parsing_result(self, result: Dict[str, str]) -> bool:
        """Validate that parsing result makes sense"""
        # Check if transaction type is valid
        if result.get('transaction_type') not in ['P', 'S', 'S (partial)', 'E']:
            return False
            
        # Check if dates look like dates
        date_pattern = r'\d{1,2}/\d{1,2}/\d{4}'
        if not re.match(date_pattern, result.get('transaction_date', '')):
            return False
            
        return True
    
    def _is_continuation_line(self, line: str) -> bool:
        """Check if line is a continuation of the trade entry"""
        continuation_starts = ['F:', 'S', 'D', '(', 'Stock']
        return any(line.startswith(start) for start in continuation_starts)
    
    def _parse_continuation_line(self, line: str, data: Dict[str, str]) -> None:
        """Parse continuation lines that provide additional information"""
        line = line.strip()
        
        # Handle ticker information in parentheses
        if line.startswith("(") and ")" in line:
            ticker_match = re.search(r'\((.*?)\)', line)
            if ticker_match:
                data['ticker'] = ticker_match.group(1)
        
        # Handle stock continuation lines
        elif line.startswith("Stock") and "(" in line:
            stock_part = line.split("Stock", 1)[0].strip()
            if stock_part:
                data['asset'] = data.get('asset', '') + " " + stock_part
            ticker_match = re.search(r'\((.*?)\)', line)
            if ticker_match:
                data['ticker'] = ticker_match.group(1)
        
        # Handle filing status
        elif line.startswith("F"):
            if ":" in line:
                filing_status = line.split(":", 1)[1].strip()
                if filing_status.startswith("New"):
                    data['filing_status'] = "New"
                else:
                    data['filing_status'] = filing_status
        
        # Handle subholding information (starts with 'S') - exactly like original parser
        elif line.startswith("S"):
            if ":" in line:
                subholding_info = line.split(":", 1)[1].strip()
                if subholding_info and not subholding_info.startswith("Hon."):
                    data['description'] = "Subholding of: " + subholding_info
        
        # Handle description information (starts with 'D') - exactly like original parser
        elif line.startswith("D"):
            if ":" in line:
                description = line.split(":", 1)[1].strip()
                if description and not description.startswith("Hon."):
                    # Clean up description if it contains unwanted text (like original parser)
                    if "ID Owner Asset Transaction Date Notification Amount" in description:
                        description = description.split("ID Owner Asset Transaction Date Notification Amount")[0].strip()
                    data['description'] = description
    
    def _normalize_amount(self, amount: str) -> str:
        """Normalize amount to standard ranges"""
        if amount in self.amount_range_mapping:
            return self.amount_range_mapping[amount]
        return amount
    
    def _calculate_confidence_score(self, record: TradeRecord) -> float:
        """Calculate confidence score for parsing quality"""
        score = 1.0
        
        # Reduce score for missing critical fields
        if not record.ticker and record.asset not in self.asset_dict:
            score -= 0.3
        if not record.transaction_type:
            score -= 0.3
        if not record.transaction_date:
            score -= 0.2
        if not record.amount:
            score -= 0.1
            
        # Increase score for ticker validation
        if record.ticker in self.tickers:
            score += 0.1
            
        return max(0.0, min(1.0, score))

    def _extract_ticker(self, asset: str) -> str:
        """Extract ticker symbol from asset name with case-insensitive matching and company name reverse lookup"""
        if not asset:
            return ""
        
        # Look for ticker in parentheses
        ticker_match = re.search(r'\((.*?)\)', asset)
        if ticker_match:
            ticker = ticker_match.group(1).strip()
            # Normalize to uppercase for comparison
            ticker_upper = ticker.upper()
            
            # Check if normalized ticker exists in our ticker set
            if ticker_upper in self.tickers:
                return ticker_upper
            elif ticker in self.tickers:
                return ticker
            else:
                # Try case-insensitive matching
                for known_ticker in self.tickers:
                    if known_ticker.upper() == ticker_upper:
                        return known_ticker
                return ticker  # Return original if not found
        
        # Look for ticker in brackets
        bracket_match = re.search(r'\[(.*?)\]', asset)
        if bracket_match:
            ticker = bracket_match.group(1).strip()
            ticker_upper = ticker.upper()
            
            if ticker_upper in self.tickers:
                return ticker_upper
            elif ticker in self.tickers:
                return ticker
            else:
                # Try case-insensitive matching
                for known_ticker in self.tickers:
                    if known_ticker.upper() == ticker_upper:
                        return known_ticker
                return ticker
        
        # Reverse lookup using company names in tickers_company mapping
        if not ticker_match and not bracket_match:
            asset_lower = asset.lower().strip()
            
            # Try exact match first
            for ticker, company_name in self.tickers_company.items():
                if company_name.lower() == asset_lower:
                    return ticker
            
            # Try partial matching - check if asset starts with company name or vice versa
            for ticker, company_name in self.tickers_company.items():
                company_lower = company_name.lower()
                
                # Check if asset name starts with company name (e.g., "Apple Inc." matches "Apple Inc")
                if asset_lower.startswith(company_lower) or company_lower.startswith(asset_lower):
                    return ticker
                
                # Check if first word of asset matches first word of company name
                asset_first_word = asset_lower.split()[0] if asset_lower.split() else ""
                company_first_word = company_lower.split()[0] if company_lower.split() else ""
                
                if asset_first_word and company_first_word and asset_first_word == company_first_word:
                    # Additional validation - check if it's a meaningful match (not just "the", "a", etc.)
                    if len(asset_first_word) > 3:  # Avoid matching articles and short words
                        return ticker
            
            # Try matching key words in the asset name
            asset_words = asset_lower.replace(',', '').replace('.', '').split()
            for ticker, company_name in self.tickers_company.items():
                company_words = company_name.lower().replace(',', '').replace('.', '').split()
                
                # Check if we have at least 2 matching significant words
                if len(asset_words) >= 2 and len(company_words) >= 2:
                    # Remove common corporate suffixes for matching
                    filtered_asset_words = [w for w in asset_words if w not in ['inc', 'corp', 'ltd', 'llc', 'co', 'company', 'corporation']]
                    filtered_company_words = [w for w in company_words if w not in ['inc', 'corp', 'ltd', 'llc', 'co', 'company', 'corporation']]
                    
                    # Count matching words
                    matches = sum(1 for word in filtered_asset_words if word in filtered_company_words)
                    
                    # If we have 2+ matching significant words and they represent majority of the shorter list
                    min_words = min(len(filtered_asset_words), len(filtered_company_words))
                    if matches >= 2 and matches >= min_words * 0.7:
                        return ticker
        
        return ""

    def _validate_and_fix_field_alignment(self, record: TradeRecord) -> TradeRecord:
        """Validate and fix field alignment issues in parsed records"""
        # Create a copy to avoid modifying the original
        fixed_record = TradeRecord(
            member=record.member,
            doc_id=record.doc_id,
            owner=record.owner,
            asset=record.asset,
            ticker=record.ticker,
            transaction_type=record.transaction_type,
            transaction_date=record.transaction_date,
            notification_date=record.notification_date,
            amount=record.amount,
            filing_status=record.filing_status,
            description=record.description,
            first_name=record.first_name,
            last_name=record.last_name,
            confidence_score=record.confidence_score,
            parsing_notes=record.parsing_notes.copy() if record.parsing_notes else []
        )
        
        # Check for field misalignment patterns and fix them
        
        # Pattern 1: Date in transaction_type field
        if self._is_date_format(fixed_record.transaction_type):
            fixed_record.parsing_notes.append("Fixed: Date found in transaction_type field")
            # Shift fields: transaction_type -> transaction_date, transaction_date -> notification_date, etc.
            temp_transaction_date = fixed_record.transaction_type
            fixed_record.transaction_type = ""
            
            # Try to find the actual transaction type in other fields
            for field_name, field_value in [
                ("transaction_date", fixed_record.transaction_date),
                ("notification_date", fixed_record.notification_date),
                ("amount", fixed_record.amount)
            ]:
                if field_value in ['P', 'S', 'E', 'S (partial)']:
                    fixed_record.transaction_type = field_value
                    break
            
            # Shift the dates
            if not fixed_record.transaction_type:
                fixed_record.transaction_type = "P"  # Default assumption
                
            fixed_record.transaction_date = temp_transaction_date
            if self._is_date_format(fixed_record.notification_date):
                # Keep notification_date as is
                pass
            else:
                fixed_record.notification_date = fixed_record.transaction_date
        
        # Pattern 2: Amount in date fields
        if self._is_amount_format(fixed_record.transaction_date):
            fixed_record.parsing_notes.append("Fixed: Amount found in transaction_date field")
            # Amount is in wrong place, need to find dates elsewhere
            temp_amount = fixed_record.transaction_date
            fixed_record.amount = temp_amount
            fixed_record.transaction_date = ""
            fixed_record.notification_date = ""
            
            # Look for dates in other fields
            if self._is_date_format(fixed_record.notification_date):
                fixed_record.transaction_date = fixed_record.notification_date
                fixed_record.notification_date = fixed_record.transaction_date  # Duplicate for now
            elif self._is_date_format(fixed_record.amount):
                fixed_record.transaction_date = fixed_record.amount
                fixed_record.amount = temp_amount
                fixed_record.notification_date = fixed_record.transaction_date
        
        # Pattern 3: Transaction type in wrong position
        if not fixed_record.transaction_type or fixed_record.transaction_type not in ['P', 'S', 'E', 'S (partial)']:
            # Look for transaction type in other fields
            for field_name, field_value in [
                ("transaction_date", fixed_record.transaction_date),
                ("notification_date", fixed_record.notification_date),
                ("amount", fixed_record.amount),
                ("asset", fixed_record.asset)
            ]:
                if field_value in ['P', 'S', 'E', 'S (partial)']:
                    fixed_record.parsing_notes.append(f"Fixed: Transaction type found in {field_name} field")
                    fixed_record.transaction_type = field_value
                    # Clear the field where we found it
                    if field_name == "transaction_date":
                        fixed_record.transaction_date = ""
                    elif field_name == "notification_date":
                        fixed_record.notification_date = ""
                    elif field_name == "amount":
                        fixed_record.amount = ""
                    break
        
        # Pattern 4: Missing dates - try to extract from asset or description
        if not fixed_record.transaction_date or not self._is_date_format(fixed_record.transaction_date):
            # Look for dates in asset field (common in malformed lines)
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', fixed_record.asset)
            if date_match:
                fixed_record.parsing_notes.append("Fixed: Date extracted from asset field")
                fixed_record.transaction_date = date_match.group(1)
                # Remove date from asset field
                fixed_record.asset = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '', fixed_record.asset).strip()
                
                # Look for second date
                second_date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', fixed_record.asset)
                if second_date_match:
                    fixed_record.notification_date = second_date_match.group(1)
                    fixed_record.asset = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '', fixed_record.asset).strip()
                else:
                    fixed_record.notification_date = fixed_record.transaction_date
        
        # Pattern 5: Missing or malformed amounts
        if not fixed_record.amount or not self._is_amount_format(fixed_record.amount):
            # Look for amounts in asset field
            amount_match = re.search(r'(\$[\d,]+(?:\s*-\s*\$[\d,]+)?)', fixed_record.asset)
            if amount_match:
                fixed_record.parsing_notes.append("Fixed: Amount extracted from asset field")
                fixed_record.amount = amount_match.group(1)
                # Remove amount from asset field
                fixed_record.asset = re.sub(r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?', '', fixed_record.asset).strip()
        
        # Pattern 6: Clean up asset field from remaining artifacts
        if fixed_record.asset:
            # Remove transaction types that might be left over
            fixed_record.asset = re.sub(r'\b[PSE]\b', '', fixed_record.asset)
            # Remove isolated dates
            fixed_record.asset = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}\b', '', fixed_record.asset)
            # Remove isolated amounts
            fixed_record.asset = re.sub(r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?', '', fixed_record.asset)
            # Clean up multiple spaces
            fixed_record.asset = re.sub(r'\s+', ' ', fixed_record.asset).strip()
        
        # Final validation and cleanup
        fixed_record = self._final_field_cleanup(fixed_record)
        
        return fixed_record
    
    def _final_field_cleanup(self, record: TradeRecord) -> TradeRecord:
        """Final cleanup and validation of all fields"""
        # Ensure transaction_type is valid
        if record.transaction_type not in ['P', 'S', 'E', 'S (partial)']:
            if record.transaction_type.upper() in ['P', 'S', 'E']:
                record.transaction_type = record.transaction_type.upper()
            else:
                record.transaction_type = "P"  # Default assumption
                record.parsing_notes.append("Warning: Invalid transaction type, defaulted to 'P'")
        
        # Ensure dates are properly formatted
        if record.transaction_date and not self._is_date_format(record.transaction_date):
            record.parsing_notes.append("Warning: Invalid transaction date format")
        
        if record.notification_date and not self._is_date_format(record.notification_date):
            record.parsing_notes.append("Warning: Invalid notification date format")
        
        # If notification date is missing, use transaction date
        if not record.notification_date and record.transaction_date:
            record.notification_date = record.transaction_date
            record.parsing_notes.append("Info: Notification date set to transaction date")
        
        # Normalize amount format
        if record.amount:
            record.amount = self._normalize_amount(record.amount)
        
        # Clean up asset name
        if record.asset:
            # Remove extra whitespace
            record.asset = re.sub(r'\s+', ' ', record.asset).strip()
            # Remove leading/trailing punctuation
            record.asset = record.asset.strip('.,;:')
        
        return record
    
    def _is_date_format(self, value: str) -> bool:
        """Check if value matches date format patterns"""
        if not value:
            return False
        
        date_patterns = [
            r'^\d{1,2}/\d{1,2}/\d{4}$',
            r'^\d{2}/\d{2}/\d{4}$',
            r'^\d{4}-\d{2}-\d{2}$'
        ]
        
        return any(re.match(pattern, value.strip()) for pattern in date_patterns)
    
    def _is_amount_format(self, value: str) -> bool:
        """Check if value matches amount format patterns"""
        if not value:
            return False
        
        amount_patterns = [
            r'^\$[\d,]+$',
            r'^\$[\d,]+\s*-\s*\$[\d,]+$',
            r'^[\d,]+$',
            r'^None$'
        ]
        
        return any(re.match(pattern, value.strip()) for pattern in amount_patterns)

    def _enhanced_transaction_type_detection(self, line: str) -> Tuple[str, str, int]:
        """Enhanced detection of transaction types with position tracking"""
        # Define all possible transaction type patterns
        transaction_patterns = [
            # Standard single-letter patterns
            (r'\b([PSE])\b', 1),
            # Case-insensitive patterns
            (r'\b([pse])\b', 1),
            # Partial sale patterns
            (r'\b(S\s*\(partial\))\b', 1),
            (r'\b(s\s*\(partial\))\b', 1),
            # Exchange patterns
            (r'\b(Exchange)\b', 1),
            (r'\b(exchange)\b', 1),
            # Purchase patterns
            (r'\b(Purchase)\b', 1),
            (r'\b(purchase)\b', 1),
            # Sale patterns
            (r'\b(Sale)\b', 1),
            (r'\b(sale)\b', 1),
            # Sell patterns
            (r'\b(Sell)\b', 1),
            (r'\b(sell)\b', 1),
        ]
        
        # Try each pattern and find the best match
        best_match = None
        best_position = -1
        best_normalized = ""
        
        for pattern, group_num in transaction_patterns:
            matches = list(re.finditer(pattern, line, re.IGNORECASE))
            for match in matches:
                transaction_type = match.group(group_num)
                position = match.start()
                
                # Normalize the transaction type
                normalized = self._normalize_transaction_type(transaction_type)
                
                # Prefer matches that are:
                # 1. Closer to the end of the line (more likely to be in the right position)
                # 2. Standard single-letter formats
                # 3. Not part of a larger word (surrounded by spaces or punctuation)
                
                score = 0
                
                # Score based on position (later in line is better)
                score += position / len(line) * 10
                
                # Score based on format (single letters are better)
                if normalized in ['P', 'S', 'E']:
                    score += 20
                elif normalized == 'S (partial)':
                    score += 15
                else:
                    score += 5
                
                # Score based on context (surrounded by whitespace/punctuation is better)
                start_char = line[position - 1] if position > 0 else ' '
                end_char = line[position + len(transaction_type)] if position + len(transaction_type) < len(line) else ' '
                
                if start_char in ' \t\n.,;:' and end_char in ' \t\n.,;:':
                    score += 10
                
                # Check if this is the best match so far
                if best_match is None or score > best_match[0]:
                    best_match = (score, match, normalized)
                    best_position = position
                    best_normalized = normalized
        
        if best_match:
            return best_normalized, line, best_position
        
        return "", line, -1
    
    def _normalize_transaction_type(self, transaction_type: str) -> str:
        """Normalize transaction type to standard format"""
        if not transaction_type:
            return ""
        
        # Convert to uppercase for comparison
        upper_type = transaction_type.upper().strip()
        
        # Handle various formats
        if upper_type == 'P':
            return 'P'
        elif upper_type == 'S':
            return 'S'
        elif upper_type == 'E':
            return 'E'
        elif 'PARTIAL' in upper_type or '(PARTIAL)' in upper_type:
            return 'S (partial)'
        elif upper_type in ['PURCHASE', 'BUY', 'BOUGHT']:
            return 'P'
        elif upper_type in ['SALE', 'SELL', 'SOLD']:
            return 'S'
        elif upper_type in ['EXCHANGE', 'EXCHANGED']:
            return 'E'
        else:
            # Return the original if we can't normalize it
            return transaction_type
    
    def _find_transaction_type_in_context(self, parts: List[str], line: str) -> Tuple[str, int]:
        """Find transaction type considering context and position"""
        # First, try the enhanced detection on the full line
        transaction_type, _, position = self._enhanced_transaction_type_detection(line)
        if transaction_type:
            return transaction_type, position
        
        # If not found in full line, search through parts
        for i, part in enumerate(parts):
            if part.upper() in ['P', 'S', 'E']:
                return part.upper(), i
            elif 'partial' in part.lower():
                return 'S (partial)', i
        
        # Look for transaction types that might be concatenated with other text
        for i, part in enumerate(parts):
            # Check if part contains a transaction type
            for trans_type in ['P', 'S', 'E']:
                if trans_type in part.upper():
                    # Make sure it's not part of a larger word
                    if re.search(r'\b' + trans_type + r'\b', part, re.IGNORECASE):
                        return trans_type, i
        
        # If still not found, make educated guesses based on context
        # Look for words that might indicate transaction type
        for i, part in enumerate(parts):
            part_lower = part.lower()
            if any(word in part_lower for word in ['purchase', 'buy', 'bought']):
                return 'P', i
            elif any(word in part_lower for word in ['sale', 'sell', 'sold']):
                return 'S', i
            elif any(word in part_lower for word in ['exchange', 'exchanged']):
                return 'E', i
        
        return "", -1

    def _extract_and_validate_dates(self, line: str, parts: List[str]) -> Tuple[str, str]:
        """Extract and validate transaction and notification dates from line"""
        # Find all date patterns in the line
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY or M/D/YYYY
            r'\b(\d{2}/\d{2}/\d{4})\b',      # MM/DD/YYYY strict
            r'\b(\d{1,2}/\d{1}/\d{4})\b',    # MM/D/YYYY or M/D/YYYY
            r'\b(\d{1}/\d{1,2}/\d{4})\b',    # M/MM/YYYY or M/M/YYYY
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                date_str = match.group(1)
                position = match.start()
                
                # Validate the date format
                if self._validate_date_format(date_str):
                    found_dates.append((date_str, position))
        
        # Remove duplicates and sort by position
        found_dates = list(set(found_dates))
        found_dates.sort(key=lambda x: x[1])
        
        # Extract transaction and notification dates
        transaction_date = ""
        notification_date = ""
        
        if len(found_dates) >= 2:
            # Use the first two dates found
            transaction_date = found_dates[0][0]
            notification_date = found_dates[1][0]
        elif len(found_dates) == 1:
            # Use the same date for both
            transaction_date = found_dates[0][0]
            notification_date = found_dates[0][0]
        else:
            # Try to find dates in individual parts
            for part in parts:
                if self._validate_date_format(part):
                    if not transaction_date:
                        transaction_date = part
                    elif not notification_date:
                        notification_date = part
                    else:
                        break
            
            # If still missing notification date, use transaction date
            if transaction_date and not notification_date:
                notification_date = transaction_date
        
        # Validate and correct the extracted dates
        transaction_date = self._correct_date_format(transaction_date)
        notification_date = self._correct_date_format(notification_date)
        
        return transaction_date, notification_date 

    def _extract_and_validate_amounts(self, line: str, parts: List[str]) -> str:
        """Extract and validate amount from line with comprehensive pattern matching"""
        # Define amount patterns in order of preference
        amount_patterns = [
            # Range patterns (most specific first)
            r'\$(\d{1,3}(?:,\d{3})*)\s*-\s*\$(\d{1,3}(?:,\d{3})*)',  # $1,000 - $15,000
            r'\$(\d{1,3}(?:,\d{3})*)\s*to\s*\$(\d{1,3}(?:,\d{3})*)',  # $1,000 to $15,000
            r'\$(\d{1,3}(?:,\d{3})*)\s*\-\s*(\d{1,3}(?:,\d{3})*)',   # $1,000 - 15,000
            
            # Single amount patterns
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,000.00 or $1,000
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',  # 1,000 dollars
            
            # Special cases
            r'\$(\d+)',  # Simple $1000 format
            r'(\d+)\s*\$',  # 1000$ format
            
            # Partial amount indicators
            r'over\s*\$(\d{1,3}(?:,\d{3})*)',  # over $1,000
            r'under\s*\$(\d{1,3}(?:,\d{3})*)',  # under $1,000
            r'up\s*to\s*\$(\d{1,3}(?:,\d{3})*)',  # up to $1,000
        ]
        
        # Find all potential amounts in the line
        found_amounts = []
        
        for pattern in amount_patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(0)
                position = match.start()
                
                # Normalize the amount
                normalized = self._normalize_amount_string(amount_str)
                if normalized:
                    found_amounts.append((normalized, position, amount_str))
        
        # If no amounts found in full line, search individual parts
        if not found_amounts:
            for part in parts:
                for pattern in amount_patterns:
                    match = re.search(pattern, part, re.IGNORECASE)
                    if match:
                        amount_str = match.group(0)
                        normalized = self._normalize_amount_string(amount_str)
                        if normalized:
                            found_amounts.append((normalized, 0, amount_str))
                            break
        
        # Select the best amount (prefer ranges, then later positions)
        if found_amounts:
            # Sort by preference: ranges first, then by position
            found_amounts.sort(key=lambda x: (
                0 if '-' in x[0] else 1,  # Ranges first
                -x[1]  # Later positions first
            ))
            return found_amounts[0][0]
        
        # Special handling for common edge cases
        return self._handle_special_amount_cases(line, parts)
    
    def _normalize_amount_string(self, amount_str: str) -> str:
        """Normalize amount string to standard format"""
        if not amount_str:
            return ""
        
        # Remove extra whitespace
        amount_str = amount_str.strip()
        
        # Handle range patterns
        range_match = re.search(r'\$(\d{1,3}(?:,\d{3})*)\s*-\s*\$(\d{1,3}(?:,\d{3})*)', amount_str)
        if range_match:
            low_amount = range_match.group(1)
            high_amount = range_match.group(2)
            return f"${low_amount} - ${high_amount}"
        
        # Handle single amount with dollar sign
        single_match = re.search(r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', amount_str)
        if single_match:
            amount = single_match.group(1)
            # Convert to standard range format based on amount
            return self._convert_to_standard_range(amount)
        
        # Handle amount without dollar sign
        number_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', amount_str)
        if number_match:
            amount = number_match.group(1)
            return self._convert_to_standard_range(amount)
        
        return ""
    
    def _convert_to_standard_range(self, amount_str: str) -> str:
        """Convert single amount to standard range format"""
        if not amount_str:
            return ""
        
        # Remove commas and convert to integer for comparison
        try:
            amount_num = int(amount_str.replace(',', '').replace('.00', ''))
            
            # Define standard ranges
            if amount_num <= 1000:
                return "$1 - $1,000"
            elif amount_num <= 15000:
                return "$1,001 - $15,000"
            elif amount_num <= 50000:
                return "$15,001 - $50,000"
            elif amount_num <= 100000:
                return "$50,001 - $100,000"
            elif amount_num <= 250000:
                return "$100,001 - $250,000"
            elif amount_num <= 500000:
                return "$250,001 - $500,000"
            elif amount_num <= 1000000:
                return "$500,001 - $1,000,000"
            elif amount_num <= 5000000:
                return "$1,000,001 - $5,000,000"
            elif amount_num <= 25000000:
                return "$5,000,001 - $25,000,000"
            else:
                return f"${amount_str}+"
                
        except ValueError:
            # If we can't parse it, return as-is with dollar sign
            return f"${amount_str}"
    
    def _handle_special_amount_cases(self, line: str, parts: List[str]) -> str:
        """Handle special cases for amount extraction"""
        # Look for "None" or "N/A" indicators
        if any(indicator in line.upper() for indicator in ['NONE', 'N/A', 'NOT APPLICABLE', 'ZERO']):
            return "None"
        
        # Look for percentage indicators (bonds, etc.)
        percentage_match = re.search(r'(\d+(?:\.\d+)?)\%', line)
        if percentage_match:
            return f"{percentage_match.group(1)}%"
        
        # Look for share counts that might be mistaken for amounts
        share_match = re.search(r'(\d+)\s*shares?', line, re.IGNORECASE)
        if share_match:
            # This is likely a share count, not an amount
            return "Amount not specified"
        
        # Look for "partial" indicators
        if 'partial' in line.lower():
            return "Partial amount"
        
        # If we find any numbers, try to make sense of them
        numbers = re.findall(r'\d{1,3}(?:,\d{3})*', line)
        if numbers:
            # Take the largest number as it's likely the amount
            largest = max(numbers, key=lambda x: int(x.replace(',', '')))
            return self._convert_to_standard_range(largest)
        
        return ""
    
    def _validate_amount_format(self, amount: str) -> bool:
        """Validate if amount is in proper format"""
        if not amount:
            return False
        
        # Valid formats
        valid_patterns = [
            r'^\$[\d,]+\s*-\s*\$[\d,]+$',  # Range format
            r'^\$[\d,]+$',  # Single amount
            r'^None$',  # None
            r'^\d+(?:\.\d+)?%$',  # Percentage
            r'^[\d,]+$',  # Number only
            r'^Partial amount$',  # Partial
            r'^Amount not specified$',  # Not specified
        ]
        
        return any(re.match(pattern, amount.strip()) for pattern in valid_patterns)
    
    def _fix_amount_parsing_issues(self, record: TradeRecord) -> TradeRecord:
        """Fix common amount parsing issues"""
        if not record.amount or not self._validate_amount_format(record.amount):
            # Try to extract amount from asset field
            if record.asset:
                extracted_amount = self._extract_and_validate_amounts(record.asset, [record.asset])
                if extracted_amount and self._validate_amount_format(extracted_amount):
                    record.amount = extracted_amount
                    record.parsing_notes.append("Fixed: Amount extracted from asset field")
                    # Remove amount from asset field
                    record.asset = re.sub(r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?', '', record.asset).strip()
        
        # Clean up amount format
        if record.amount:
            record.amount = self._normalize_amount(record.amount)
        
        return record 