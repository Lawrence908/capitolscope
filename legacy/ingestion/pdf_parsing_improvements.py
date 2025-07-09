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
        # Match original parser logic - just check if line starts with owner type
        parts = line.split()
        if len(parts) < 1:
            return False
            
        return parts[0] in ['SP', 'DC', 'JT']
    
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
        owner_types = ["SP", "DC", "JT"]
        
        for i in range(1, len(lines)):  # Look ahead through all remaining lines
            line = lines[i].strip()
            
            # Stop if we hit a new trade line or section break
            if any(line.startswith(owner_type) for owner_type in owner_types):
                break
            if line.startswith("* For the") or line.startswith("Initial") or line.startswith("Asset"):
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
            
        data = {}
        
        # Owner is always first
        data['owner'] = parts[0]
        
        # Try multiple parsing strategies
        strategies = [
            self._parse_strategy_standard,
            self._parse_strategy_shifted_amounts,
            self._parse_strategy_missing_fields
        ]
        
        for strategy in strategies:
            try:
                result = strategy(parts)
                if result:  # Remove strict validation to match original parser's flexibility
                    return {**data, **result}
            except Exception as e:
                continue
                
        return None
    
    def _parse_strategy_standard(self, parts: List[str]) -> Dict[str, str]:
        """Standard parsing strategy assuming normal column layout"""
        if len(parts) < 2:
            return {}
        
        # Extract asset (everything between owner and the last 6 fields, similar to original parser)
        if len(parts) >= 7:  # owner + asset + 5 trailing fields minimum
            asset = " ".join(parts[1:-6]).split("-", 1)[0].strip()
        elif len(parts) >= 3:
            asset = parts[1]  # Just take the second part if not enough fields
        else:
            asset = ""
        
        ticker = self._extract_ticker(asset)
        
        # Clean asset name by removing ticker information
        if ticker:
            asset = re.sub(r'\([^)]*\)', '', asset).strip()
            asset = re.sub(r'\[[^\]]*\]', '', asset).strip()
        
        # Handle cases with different numbers of trailing fields (like original parser)
        result = {
            'owner': parts[0],
            'asset': asset,
            'ticker': ticker,
            'filing_status': "New",
            'description': ""
        }
        
        # Extract trailing fields based on available parts
        if len(parts) >= 6:
            result['transaction_type'] = parts[-5]
            result['transaction_date'] = parts[-4]
            result['notification_date'] = parts[-3]
            result['amount'] = parts[-2]
        elif len(parts) >= 4:
            result['transaction_type'] = parts[-3] if len(parts) > 3 else ""
            result['transaction_date'] = parts[-2] if len(parts) > 2 else ""
            result['notification_date'] = parts[-1] if len(parts) > 1 else ""
            result['amount'] = ""
        else:
            result['transaction_type'] = ""
            result['transaction_date'] = ""
            result['notification_date'] = ""
            result['amount'] = ""
        
        return result
    
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

class PDFParsingTestSuite:
    """Comprehensive testing suite for PDF parsing validation"""
    
    def __init__(self, parser: ImprovedPDFParser):
        self.parser = parser
        self.test_results = []
        
    def run_validation_tests(self, pdf_files: List[str]) -> Dict[str, any]:
        """Run comprehensive validation tests on PDF files"""
        results = {
            'total_files': len(pdf_files),
            'successful_parses': 0,
            'failed_parses': 0,
            'records_extracted': 0,
            'low_confidence_records': 0,
            'validation_errors': 0,
            'common_errors': {},
            'confidence_distribution': [],
            'ticker_accuracy': 0,
            'date_accuracy': 0,
            'amount_accuracy': 0
        }
        
        all_records = []
        
        for pdf_file in pdf_files:
            try:
                doc_id = pdf_file.split('/')[-1].replace('.pdf', '')
                records = self.parser.parse_pdf_improved(pdf_file, doc_id, "Test")
                
                if records:
                    results['successful_parses'] += 1
                    results['records_extracted'] += len(records)
                    all_records.extend(records)
                    
                    # Analyze confidence scores
                    for record in records:
                        if record.confidence_score < 0.7:
                            results['low_confidence_records'] += 1
                        results['confidence_distribution'].append(record.confidence_score)
                        
                        # Count validation errors
                        if record.parsing_notes:
                            results['validation_errors'] += len(record.parsing_notes)
                            for note in record.parsing_notes:
                                error_type = note.split(':')[0]
                                results['common_errors'][error_type] = results['common_errors'].get(error_type, 0) + 1
                                
                else:
                    results['failed_parses'] += 1
                    
            except Exception as e:
                results['failed_parses'] += 1
                logging.error(f"Failed to parse {pdf_file}: {e}")
        
        # Calculate accuracy metrics
        if all_records:
            results['ticker_accuracy'] = self._calculate_ticker_accuracy(all_records)
            results['date_accuracy'] = self._calculate_date_accuracy(all_records)
            results['amount_accuracy'] = self._calculate_amount_accuracy(all_records)
            
        return results
    
    def _calculate_ticker_accuracy(self, records: List[TradeRecord]) -> float:
        """Calculate ticker symbol accuracy"""
        valid_tickers = sum(1 for r in records if r.ticker in self.parser.tickers or r.ticker == "NaN")
        return valid_tickers / len(records) if records else 0
    
    def _calculate_date_accuracy(self, records: List[TradeRecord]) -> float:
        """Calculate date parsing accuracy"""
        valid_dates = 0
        for record in records:
            try:
                datetime.strptime(record.transaction_date, "%m/%d/%Y")
                datetime.strptime(record.notification_date, "%m/%d/%Y")
                valid_dates += 1
            except:
                pass
        return valid_dates / len(records) if records else 0
    
    def _calculate_amount_accuracy(self, records: List[TradeRecord]) -> float:
        """Calculate amount parsing accuracy"""
        valid_amounts = sum(1 for r in records if r.amount and ("$" in r.amount or r.amount == "None"))
        return valid_amounts / len(records) if records else 0
    
    def generate_test_report(self, results: Dict[str, any]) -> str:
        """Generate a comprehensive test report"""
        report = f"""
PDF Parsing Validation Report
=============================

Overall Statistics:
- Total Files Processed: {results['total_files']}
- Successful Parses: {results['successful_parses']} ({results['successful_parses']/results['total_files']*100:.1f}%)
- Failed Parses: {results['failed_parses']} ({results['failed_parses']/results['total_files']*100:.1f}%)
- Total Records Extracted: {results['records_extracted']}
- Low Confidence Records: {results['low_confidence_records']} ({results['low_confidence_records']/max(1,results['records_extracted'])*100:.1f}%)

Accuracy Metrics:
- Ticker Accuracy: {results['ticker_accuracy']:.2%}
- Date Accuracy: {results['date_accuracy']:.2%}
- Amount Accuracy: {results['amount_accuracy']:.2%}

Validation Issues:
- Total Validation Errors: {results['validation_errors']}
- Most Common Errors:
"""
        
        for error_type, count in sorted(results['common_errors'].items(), key=lambda x: x[1], reverse=True)[:5]:
            report += f"  - {error_type}: {count} occurrences\n"
            
        if results['confidence_distribution']:
            import statistics
            report += f"\nConfidence Score Distribution:\n"
            report += f"- Average: {statistics.mean(results['confidence_distribution']):.2f}\n"
            report += f"- Median: {statistics.median(results['confidence_distribution']):.2f}\n"
            report += f"- Min: {min(results['confidence_distribution']):.2f}\n"
            report += f"- Max: {max(results['confidence_distribution']):.2f}\n"
            
        return report 