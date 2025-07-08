#!/usr/bin/env python3
"""
Enhanced PDF parser that combines validation framework with original parser's edge case handling.
This version incorporates the sophisticated logic from the original parser while maintaining
the validation and confidence scoring features.
"""

import pdfplumber
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from pdf_parsing_improvements import PDFParsingValidator, TradeRecord


@dataclass
class EnhancedTradeRecord(TradeRecord):
    """Enhanced trade record with additional parsing metadata"""
    parsing_strategy: str = "unknown"
    original_line: str = ""
    edge_cases_applied: List[str] = field(default_factory=list)


class EnhancedPDFParser:
    """Enhanced PDF parser combining original logic with validation framework"""
    
    def __init__(self, tickers: set, asset_dict: dict, tickers_company: dict):
        self.tickers = tickers
        self.asset_dict = asset_dict
        self.tickers_company = tickers_company
        self.validator = PDFParsingValidator()
        self.ticker_pattern = re.compile(r'\(([A-Za-z0-9.]+)\)')
        
    def parse_pdf_enhanced(self, pdf_path: str, doc_id: str, member: str) -> List[EnhancedTradeRecord]:
        """
        Enhanced PDF parsing combining original logic with validation
        """
        
        try:
            # Open the PDF file
            with pdfplumber.open(pdf_path) as pdf:
                pdf_text = "".join(page.extract_text() for page in pdf.pages)

            if not pdf_text.strip():
                print("PDF is empty: ", doc_id)
                return []

            lines = pdf_text.splitlines()
            
            # Enhanced owner type detection - handle case variations
            owner_types = ["SP", "DC", "JT", "sP", "dC", "jT", "sp", "dc", "jt"]
            records = []
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Check if this is a new trade line starting with known owner types
                if any(line.startswith(owner_type) for owner_type in owner_types):
                    record, lines_consumed = self._parse_enhanced_trade_entry(
                        lines[i:], doc_id, member, line
                    )
                    
                    if record:
                        records.append(record)
                    
                    i += lines_consumed
                else:
                    i += 1
            
            return records
        
        except Exception as e:
            print(f"parse_pdf_enhanced error: {e}")
            return []
    
    def _parse_enhanced_trade_entry(self, lines: List[str], doc_id: str, member: str, original_line: str) -> Tuple[Optional[EnhancedTradeRecord], int]:
        """Parse a trade entry using enhanced logic from original parser"""
        
        if not lines:
            return None, 1
            
        main_line = lines[0].strip()
        lines_consumed = 1
        
        # Parse using original parser's sophisticated logic
        parsed_data = self._parse_with_original_logic(main_line, doc_id)
        if not parsed_data:
            return None, 1
        
        # Look ahead for continuation lines (original parser logic)
        additional_data = {}
        j = 1
        while j < len(lines) and not any(lines[j].startswith(owner) for owner in ["SP", "DC", "JT", "sP", "dC", "jT", "sp", "dc", "jt"]):
            next_line = lines[j].strip()
            if next_line.startswith("* For the"):
                break
            if next_line.startswith("Initial"):
                break
            if next_line.startswith("Asset"):
                break
            elif next_line.startswith("("):  # Ticker continuation
                ticker_match = re.search(r'\((.*?)\)', next_line)
                if ticker_match:
                    additional_data['ticker'] = ticker_match.group(1)
            elif next_line.startswith("Stock"):
                additional_data['asset'] = next_line.split("Stock", 1)[0].strip()
                ticker_match = re.search(r'\((.*?)\)', next_line)
                if ticker_match:
                    additional_data['ticker'] = ticker_match.group(1)
            elif next_line.startswith("F"):  # Filing Status
                filing_status = next_line.split(":", 1)[1].strip()
                if filing_status.startswith("New"):
                    additional_data['filing_status'] = "New"
                else:
                    additional_data['filing_status'] = filing_status
            elif next_line.startswith("S"):
                additional_data['description'] = "Subholding of: " + next_line.split(":", 1)[1].strip()
            elif next_line.startswith("D"):  # Description
                description = next_line.split(":", 1)[1].strip()
                if description.startswith("Hon."):
                    description = ""
                if description.endswith("ID Owner Asset Transaction Date Notification Amount"):
                    description = description.split("ID Owner Asset Transaction Date Notification Amount")[0]
                additional_data['description'] = description
            j += 1
        
        lines_consumed = j
        
        # Merge data
        merged_data = {**parsed_data, **additional_data}
        
        # Create enhanced trade record
        record = EnhancedTradeRecord(
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
            description=merged_data.get('description', ''),
            parsing_strategy=merged_data.get('strategy', 'enhanced'),
            original_line=original_line,
            edge_cases_applied=merged_data.get('edge_cases', [])
        )
        
        # Calculate confidence score
        record.confidence_score = self._calculate_enhanced_confidence_score(record)
        
        # Validate record
        validation_results = self.validator.validate_trade_record(record)
        if validation_results['errors']:
            record.parsing_notes.extend(validation_results['errors'])
        if validation_results['warnings']:
            record.parsing_notes.extend(validation_results['warnings'])
            
        return record, lines_consumed
    
    def _parse_with_original_logic(self, line: str, doc_id: str) -> Optional[Dict[str, any]]:
        """Parse using the original parser's sophisticated logic"""
        
        columns = line.split()
        if len(columns) < 6:
            return None
        
        data = {
            'owner': columns[0],
            'strategy': 'enhanced',
            'edge_cases': [],
            'doc_id': doc_id
        }
        
        # Asset parsing (original logic)
        data['asset'] = " ".join(columns[1:-6]).split("-", 1)[0].strip()
        
        # Find the column containing "()" and split the asset and ticker
        if data['asset'].__contains__("("):
            data['asset'], data['ticker'] = data['asset'].rsplit("(", 1)
            data['ticker'] = data['ticker'].split(")")[0]
        
        # Initial field assignments
        data['transaction_type'] = columns[-5]
        data['transaction_date'] = columns[-4]
        data['notification_date'] = columns[-3]
        data['amount'] = columns[-2]
        
        if data['amount'] == "-":
            data['amount'] = columns[-3]
        
        # Apply original parser's edge case handling
        data = self._apply_original_edge_cases(data, columns, doc_id)
        
        # Validate transaction type
        transaction_types = ["P", "S", "S (partial)"]
        if data['transaction_type'] not in transaction_types:
            return None
        
        return data
    
    def _apply_original_edge_cases(self, data: Dict, columns: List[str], doc_id: str) -> Dict:
        """Apply the original parser's edge case handling"""
        
        # Original complex logic for handling various edge cases
        if data['notification_date'].startswith("$") and data['notification_date'].endswith("1"):
            data['amount'] = columns[-3]
            if data['amount'] == "-":
                data['amount'] = columns[-4]
            data['notification_date'] = columns[-4]
            data['transaction_date'] = columns[-5]
            data['transaction_type'] = columns[-6]
            data['edge_cases'].append("notification_date_amount_shift")
            
        elif data['notification_date'].startswith("$") and data['notification_date'].endswith("0"):
            data['amount'] = columns[-5]
            if data['amount'] == "-":
                data['amount'] = columns[-6]
            data['notification_date'] = columns[-6]
            data['transaction_date'] = columns[-7]
            data['transaction_type'] = columns[-8]
            data['edge_cases'].append("notification_date_amount_shift_alt")

        if data['transaction_date'].startswith("$") and data['transaction_date'].endswith("1"):
            data['amount'] = columns[-4]
            if data['amount'] == "-":
                data['amount'] = columns[-5]
            data['notification_date'] = columns[-5]
            data['transaction_date'] = columns[-6]
            data['transaction_type'] = columns[-7]
            data['edge_cases'].append("transaction_date_amount_shift")
            
        elif data['transaction_date'].startswith("$") and data['transaction_date'].endswith("0"):
            data['amount'] = columns[-7]
            if data['amount'] == "-":
                data['amount'] = columns[-8]
            data['notification_date'] = columns[-6]
            data['transaction_date'] = columns[-5]
            data['transaction_type'] = columns[-4]
            data['edge_cases'].append("transaction_date_amount_shift_alt")

        if data['transaction_type'].startswith("(partial)"):
            data['transaction_type'] = columns[-6] + " " + columns[-5]
            if data['transaction_type'].startswith("(partial)"):
                data['transaction_type'] = columns[-7] + " " + columns[-6]
            data['edge_cases'].append("partial_transaction_type")
        
        # Check if transaction type is a date
        if data['transaction_type'].startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
            if data['notification_date'].startswith("$"):
                data['amount'] = data['notification_date']
            data['notification_date'] = data['transaction_type'].split(" ")[1]
            if data['notification_date'].startswith("$"):
                data['amount'] = data['notification_date']
            data['transaction_date'] = data['transaction_type'].split(" ")[0]
            data['transaction_type'] = columns[-8]
            data['amount'] = columns[-3]
            data['edge_cases'].append("transaction_type_as_date")
            
        # Set amount based on current case
        if data['amount'] == "-":
            data['amount'] = columns[-4] + " " + columns[-3] + " " + columns[-2]
            
        if data['amount'].startswith("Spouse/DC"):
            data['amount'] = "$1,000,001 - $5,000,000"
            data['edge_cases'].append("spouse_dc_amount")
        
        # Amount normalization (original logic)
        data['amount'] = self._normalize_amount_original(data['amount'])
        
        # Ticker processing (original logic)
        data = self._process_ticker_original(data, columns)
        
        # Special case handling
        if data['doc_id'] == "20025151" and data['ticker'] == "DIS":
            data['transaction_type'] = "P"
            data['transaction_date'] = "06/30/2021"
            data['notification_date'] = "05/30/2024"
            data['amount'] = "$1,001 - $15,000"
            data['filing_status'] = "New"
            data['description'] = ""
            data['edge_cases'].append("special_case_20025151")
        
        return data
    
    def _normalize_amount_original(self, amount: str) -> str:
        """Original amount normalization logic"""
        if amount == "$0":
            return "None"
        elif amount == "$1":
            return "$1 - $15,000"
        elif amount == "$1,001":
            return "$1,001 - $15,000"
        elif amount == "$15,000":
            return "$1,001 - $15,000"
        elif amount == "$15,001":
            return "$15,001 - $50,000"
        elif amount == "$50,001":
            return "$50,001 - $100,000"
        elif amount == "$100,001":
            return "$100,001 - $250,000"
        elif amount == "$250,001":
            return "$250,001 - $500,000"
        elif amount == "$500,001":
            return "$500,001 - $1,000,000"
        elif amount == "$1,000,001":
            return "$1,000,001 - $5,000,000"
        elif amount == "$5,000,001":
            return "$5,000,001 - $25,000,000"
        return amount
    
    def _process_ticker_original(self, data: Dict, columns: List[str]) -> Dict:
        """Original ticker processing logic"""
        
        # Check if columns[1] matches the first word in the values of self.tickers_company
        for key, value in self.tickers_company.items():
            if value.split()[0] == columns[1]:
                data['ticker'] = key
                data['asset'] = value
                data['edge_cases'].append("ticker_company_match")
                break
        
        # Check if the ticker is a variation of BRK.B
        if data['ticker'].startswith("BRK"):
            data['ticker'] = "BRK.B"
            data['edge_cases'].append("brk_variation")
        if data['ticker'].startswith("bRK"):
            data['ticker'] = "BRK.B"
            data['edge_cases'].append("brk_variation")
        
        if data['ticker'] not in self.tickers:
            # Check if the ticker is in the S&P 500
            print("Not in S&P 500: ", data['ticker'])
            if data['ticker'].__contains__(")"):
                data['ticker'] = data['ticker'].split(")")[0]
            if data['ticker'].strip("[]") in self.asset_dict:
                data['ticker'] = self.asset_dict[data['ticker'].strip("[]")]
            else:
                try:
                    # Check self.asset_dict for the asset type
                    print("Try get_asset_type: ", data['ticker'])
                    data['ticker'] = self.asset_dict[data['ticker'].strip("[]")]
                except Exception as e:
                    print("process_ticker_original, try get_asset_type: ", e)
                    data['ticker'] = "NaN"
        
        return data
    
    def _normalize_amount(self, amount: str) -> str:
        """Normalize amount to standard ranges"""
        if not amount or amount == "-":
            return "None"
        
        # Handle standard amount ranges
        amount_ranges = {
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
        
        return amount_ranges.get(amount, amount)
    
    def _calculate_enhanced_confidence_score(self, record: EnhancedTradeRecord) -> float:
        """Calculate confidence score with enhanced features"""
        
        score = 0.0
        max_score = 0.0
        
        # Basic field completeness
        fields = [
            ('owner', 1.0), ('asset', 1.0), ('transaction_type', 1.0),
            ('transaction_date', 1.0), ('notification_date', 1.0), ('amount', 1.0)
        ]
        
        for field, weight in fields:
            value = getattr(record, field, '')
            if value and value.strip():
                score += weight
            max_score += weight
        
        # Bonus for successful parsing
        if record.parsing_strategy == 'enhanced':
            score += 0.2
            max_score += 0.2
        
        # Bonus for edge case handling
        if record.edge_cases_applied:
            score += min(len(record.edge_cases_applied) * 0.1, 0.3)
            max_score += 0.3
        
        # Penalty for validation issues
        if record.parsing_notes:
            score -= min(len(record.parsing_notes) * 0.1, 0.5)
        
        return max(0.0, min(1.0, score / max_score)) if max_score > 0 else 0.0 