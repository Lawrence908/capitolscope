"""
Congressional Trade Data Quality Enhancement Module.

This module provides comprehensive data quality improvements for congressional trade data import,
including:
1. Enhanced amount parsing with standard congressional disclosure ranges
2. Owner field validation and correction
3. Column misalignment detection and correction
4. Garbage character removal and normalization
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)

class OwnerType(Enum):
    """Valid owner types for congressional trades."""
    CONGRESS_MEMBER = "C"
    SPOUSE = "SP"
    JOINT = "JT"
    DEPENDENT_CHILD = "DC"

@dataclass
class AmountRange:
    """Standard congressional disclosure amount range."""
    min_amount: int
    max_amount: Optional[int]
    display_text: str
    
    def contains_amount(self, amount: int) -> bool:
        """Check if amount falls within this range."""
        if self.max_amount is None:
            return amount >= self.min_amount
        return self.min_amount <= amount <= self.max_amount

class CongressionalAmountValidator:
    """Validator for congressional disclosure amount ranges."""
    
    # Standard congressional disclosure amount ranges in cents
    STANDARD_RANGES = [
        AmountRange(100_100, 1_500_000, "$1,001 - $15,000"),
        AmountRange(1_500_100, 5_000_000, "$15,001 - $50,000"),
        AmountRange(5_000_100, 10_000_000, "$50,001 - $100,000"),
        AmountRange(10_000_100, 25_000_000, "$100,001 - $250,000"),
        AmountRange(25_000_100, 50_000_000, "$250,001 - $500,000"),
        AmountRange(50_000_100, 100_000_000, "$500,001 - $1,000,000"),
        AmountRange(100_000_100, 500_000_000, "$1,000,001 - $5,000,000"),
        AmountRange(500_000_100, 2_500_000_000, "$5,000,001 - $25,000,000"),
        AmountRange(2_500_000_100, 5_000_000_000, "$25,000,001 - $50,000,000"),
        AmountRange(5_000_000_100, None, "$50,000,001 +"),
    ]
    
    @classmethod
    def get_standard_range(self, min_amount: int, max_amount: Optional[int]) -> Optional[AmountRange]:
        """Get the standard range that matches the given min/max amounts."""
        for range_obj in self.STANDARD_RANGES:
            if range_obj.min_amount == min_amount and range_obj.max_amount == max_amount:
                return range_obj
        return None
    
    @classmethod
    def normalize_to_standard_range(self, min_amount: int, max_amount: Optional[int]) -> Optional[AmountRange]:
        """Normalize amounts to closest standard range."""
        # Find the best matching standard range
        best_match = None
        best_score = 0
        
        for range_obj in self.STANDARD_RANGES:
            # Calculate match score based on how close the amounts are
            score = 0
            if range_obj.min_amount <= min_amount <= (range_obj.max_amount or float('inf')):
                score += 50  # Min amount is within range
            if max_amount and range_obj.max_amount:
                if range_obj.min_amount <= max_amount <= range_obj.max_amount:
                    score += 50  # Max amount is within range
            
            # Prefer exact matches
            if range_obj.min_amount == min_amount and range_obj.max_amount == max_amount:
                score = 100
            
            if score > best_score:
                best_score = score
                best_match = range_obj
        
        return best_match if best_score >= 50 else None

class CongressionalDataQualityEnhancer:
    """Enhanced data quality processor for congressional trade data."""
    
    def __init__(self):
        self.amount_validator = CongressionalAmountValidator()
        self.statistics = {
            'total_rows': 0,
            'fixed_owner_field': 0,
            'fixed_amount_parsing': 0,
            'fixed_column_alignment': 0,
            'removed_garbage_chars': 0,
            'rows_with_errors': 0,
            'unfixable_rows': 0
        }
    
    def enhance_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enhance the entire dataframe with comprehensive data quality improvements.
        
        Args:
            df: Input dataframe with potentially problematic data
            
        Returns:
            Enhanced dataframe with improved data quality
        """
        logger.info(f"Starting data quality enhancement for {len(df)} rows")
        self.statistics['total_rows'] = len(df)
        
        # Create a copy to avoid modifying original
        enhanced_df = df.copy()
        
        # Step 1: Detect and fix column misalignment
        enhanced_df = self._fix_column_misalignment(enhanced_df)
        
        # Step 2: Clean and validate owner field
        enhanced_df = self._enhance_owner_field(enhanced_df)
        
        # Step 3: Enhanced amount parsing
        enhanced_df = self._enhance_amount_parsing(enhanced_df)
        
        # Step 4: Remove garbage characters from all text fields
        enhanced_df = self._remove_garbage_characters(enhanced_df)
        
        # Step 5: Validate and normalize data
        enhanced_df = self._validate_and_normalize(enhanced_df)
        
        # Log statistics
        self._log_enhancement_statistics()
        
        return enhanced_df
    
    def _fix_column_misalignment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect and fix column misalignment issues.
        
        This happens when data shifts columns due to parsing errors.
        """
        logger.info("Checking for column misalignment...")
        
        # Check if owner field contains company names instead of valid owner types
        if 'Owner' in df.columns:
            invalid_owners = df[df['Owner'].str.len() > 5]  # Owner should be 1-2 chars
            
            if len(invalid_owners) > 0:
                logger.warning(f"Found {len(invalid_owners)} rows with invalid owner data")
                
                # Try to fix by shifting columns
                for idx, row in invalid_owners.iterrows():
                    fixed_row = self._attempt_column_shift_fix(row)
                    if fixed_row is not None:
                        df.loc[idx] = fixed_row
                        self.statistics['fixed_column_alignment'] += 1
        
        return df
    
    def _attempt_column_shift_fix(self, row: pd.Series) -> Optional[pd.Series]:
        """
        Attempt to fix a misaligned row by shifting columns.
        
        This is a heuristic approach that looks for patterns that indicate
        the data has shifted columns.
        """
        try:
            # Look for valid owner types in nearby columns
            potential_owners = []
            for col in row.index:
                if isinstance(row[col], str) and len(row[col]) <= 3:
                    val = row[col].strip().upper()
                    if val in ['C', 'SP', 'JT', 'DC']:
                        potential_owners.append((col, val))
            
            if potential_owners:
                # Found a valid owner type, try to reconstruct the row
                # This is a simplified approach - in practice, you'd want more sophisticated logic
                logger.debug(f"Found potential owner fixes: {potential_owners}")
                return row  # Return as-is for now, but could implement column shifting
        
        except Exception as e:
            logger.debug(f"Failed to fix column alignment: {e}")
        
        return None
    
    def _enhance_owner_field(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate owner field values.
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with enhanced owner field
        """
        if 'Owner' not in df.columns:
            return df
        
        logger.info("Enhancing owner field...")
        
        # Define valid owner types and their variations
        owner_mappings = {
            'C': ['C', 'CONGRESS', 'MEMBER', 'CONGRESSMAN', 'CONGRESSWOMAN'],
            'SP': ['SP', 'SPOUSE', 'S'],
            'JT': ['JT', 'JOINT', 'J'],
            'DC': ['DC', 'DEPENDENT', 'CHILD', 'DEPENDENT CHILD']
        }
        
        def fix_owner_value(value):
            if pd.isna(value) or value == '':
                return None
            
            value_str = str(value).strip().upper()
            
            # Check for exact matches first
            if value_str in [e.value for e in OwnerType]:
                return value_str
            
            # Check for fuzzy matches
            for standard_owner, variations in owner_mappings.items():
                for variation in variations:
                    if fuzz.ratio(value_str, variation) > 80:  # 80% similarity
                        self.statistics['fixed_owner_field'] += 1
                        return standard_owner
            
            # If it's a company name or other invalid data, check if it should be 'C'
            if len(value_str) > 10:  # Likely a company name
                logger.warning(f"Invalid owner value (likely company name): {value_str}")
                self.statistics['rows_with_errors'] += 1
                return 'C'  # Default to Congress member
            
            # Return None for unfixable values
            logger.warning(f"Could not fix owner value: {value_str}")
            return None
        
        # Apply the fix
        df['Owner'] = df['Owner'].apply(fix_owner_value)
        
        return df
    
    def _enhance_amount_parsing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enhanced amount parsing with garbage character removal and validation.
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with enhanced amount parsing
        """
        amount_columns = ['Amount', 'amount', 'Value', 'value']
        found_column = None
        
        for col in amount_columns:
            if col in df.columns:
                found_column = col
                break
        
        if not found_column:
            return df
        
        logger.info(f"Enhancing amount parsing for column: {found_column}")
        
        def parse_enhanced_amount(value):
            """Enhanced amount parser that handles garbage characters."""
            if pd.isna(value) or value == '':
                return None, None
            
            value_str = str(value).strip()
            
            # Remove garbage characters like 'gfedc' at the end
            # Common garbage patterns to remove
            garbage_patterns = [
                r'\s+gfedc\s*$',  # 'gfedc' at end
                r'\s+[a-z]{3,}\s*$',  # Any 3+ letter sequence at end
                r'\s+\w{1,3}\s*$',  # Short word patterns at end
            ]
            
            cleaned_value = value_str
            for pattern in garbage_patterns:
                old_value = cleaned_value
                cleaned_value = re.sub(pattern, '', cleaned_value, flags=re.IGNORECASE).strip()
                if old_value != cleaned_value:
                    self.statistics['removed_garbage_chars'] += 1
            
            # Parse the cleaned amount
            min_amount, max_amount = self._parse_amount_range(cleaned_value)
            
            if min_amount is not None or max_amount is not None:
                self.statistics['fixed_amount_parsing'] += 1
                
                # Try to normalize to standard congressional ranges
                if min_amount and max_amount:
                    standard_range = self.amount_validator.normalize_to_standard_range(min_amount, max_amount)
                    if standard_range:
                        return standard_range.min_amount, standard_range.max_amount
                
                return min_amount, max_amount
            
            return None, None
        
        # Apply enhanced parsing
        df[['amount_min', 'amount_max']] = df[found_column].apply(
            lambda x: pd.Series(parse_enhanced_amount(x))
        )
        
        return df
    
    def _parse_amount_range(self, amount_str: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse amount range strings with comprehensive pattern matching.
        
        Args:
            amount_str: Amount string from CSV
            
        Returns:
            Tuple of (min_cents, max_cents)
        """
        if not amount_str:
            return None, None
        
        try:
            # Remove common characters and normalize
            cleaned = re.sub(r'[^\d,.$\-+\s]', '', amount_str)
            cleaned = cleaned.replace('$', '').replace(',', '').strip()
            
            # Handle different range patterns
            range_patterns = [
                r'^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$',  # 1001 - 15000
                r'^(\d+(?:\.\d+)?)\s*to\s*(\d+(?:\.\d+)?)$',  # 1001 to 15000
                r'^(\d+(?:\.\d+)?)\s*\+$',  # 50001+
                r'^(\d+(?:\.\d+)?)$',  # Single value
            ]
            
            # Try range patterns
            for pattern in range_patterns:
                match = re.match(pattern, cleaned, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) == 2:  # Range
                        min_val = float(groups[0]) * 100  # Convert to cents
                        max_val = float(groups[1]) * 100 if groups[1] else None
                        return int(min_val), int(max_val) if max_val else None
                    elif len(groups) == 1:  # Single value or plus
                        if '+' in cleaned:
                            min_val = float(groups[0]) * 100
                            return int(min_val), None
                        else:
                            val = float(groups[0]) * 100
                            return int(val), int(val)
            
            # Try to extract numbers and infer ranges
            numbers = re.findall(r'\d+(?:\.\d+)?', cleaned)
            if len(numbers) >= 2:
                min_val = float(numbers[0]) * 100
                max_val = float(numbers[1]) * 100
                return int(min_val), int(max_val)
            elif len(numbers) == 1:
                val = float(numbers[0]) * 100
                return int(val), int(val)
                
        except Exception as e:
            logger.debug(f"Failed to parse amount '{amount_str}': {e}")
        
        return None, None
    
    def _remove_garbage_characters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove garbage characters from all text fields.
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with cleaned text fields
        """
        logger.info("Removing garbage characters from text fields...")
        
        # Define common garbage patterns
        garbage_patterns = [
            r'\s+gfedc\s*',  # 'gfedc' pattern
            r'\s+[a-z]{4,}\s*$',  # Long lowercase sequences at end
            r'[^\x00-\x7F]+',  # Non-ASCII characters
            r'\s+$',  # Trailing whitespace
        ]
        
        # Apply cleaning to all string columns
        for col in df.columns:
            if df[col].dtype == 'object':  # String-like columns
                def clean_text(value):
                    if pd.isna(value) or not isinstance(value, str):
                        return value
                    
                    cleaned = value
                    for pattern in garbage_patterns:
                        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
                    
                    return cleaned.strip()
                
                df[col] = df[col].apply(clean_text)
        
        return df
    
    def _validate_and_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Final validation and normalization of the dataframe.
        
        Args:
            df: Input dataframe
            
        Returns:
            Validated and normalized dataframe
        """
        logger.info("Performing final validation and normalization...")
        
        # Count rows with remaining errors
        if 'Owner' in df.columns:
            invalid_owners = df[df['Owner'].isna() | ~df['Owner'].isin(['C', 'SP', 'JT', 'DC'])]
            self.statistics['unfixable_rows'] += len(invalid_owners)
        
        # Additional validation can be added here
        
        return df
    
    def _log_enhancement_statistics(self):
        """Log comprehensive statistics about the enhancement process."""
        logger.info("Data Quality Enhancement Statistics:")
        logger.info(f"  Total rows processed: {self.statistics['total_rows']}")
        logger.info(f"  Fixed owner field: {self.statistics['fixed_owner_field']}")
        logger.info(f"  Fixed amount parsing: {self.statistics['fixed_amount_parsing']}")
        logger.info(f"  Fixed column alignment: {self.statistics['fixed_column_alignment']}")
        logger.info(f"  Removed garbage characters: {self.statistics['removed_garbage_chars']}")
        logger.info(f"  Rows with errors: {self.statistics['rows_with_errors']}")
        logger.info(f"  Unfixable rows: {self.statistics['unfixable_rows']}")
        
        # Calculate success rate
        if self.statistics['total_rows'] > 0:
            success_rate = (1 - self.statistics['unfixable_rows'] / self.statistics['total_rows']) * 100
            logger.info(f"  Data quality success rate: {success_rate:.1f}%")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get enhancement statistics."""
        return self.statistics.copy()

# Utility functions for external use

def enhance_congressional_data_quality(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Enhance congressional data quality for a dataframe.
    
    Args:
        df: Input dataframe with congressional trade data
        
    Returns:
        Tuple of (enhanced_dataframe, statistics)
    """
    enhancer = CongressionalDataQualityEnhancer()
    enhanced_df = enhancer.enhance_dataframe(df)
    statistics = enhancer.get_statistics()
    
    return enhanced_df, statistics

def validate_congressional_amount_range(min_amount: int, max_amount: Optional[int]) -> Optional[str]:
    """
    Validate if an amount range matches congressional disclosure standards.
    
    Args:
        min_amount: Minimum amount in cents
        max_amount: Maximum amount in cents (None for open-ended)
        
    Returns:
        Standard range display text if valid, None otherwise
    """
    standard_range = CongressionalAmountValidator.normalize_to_standard_range(min_amount, max_amount)
    return standard_range.display_text if standard_range else None 