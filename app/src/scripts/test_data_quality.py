#!/usr/bin/env python3
"""
Test script for congressional data quality enhancements.

This script tests the data quality improvements on sample problematic data
that matches the error patterns described in the user's request.
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from domains.congressional.data_quality import enhance_congressional_data_quality

def test_data_quality_enhancements():
    """Test the data quality enhancements with problematic sample data."""
    
    print("Testing Congressional Data Quality Enhancements")
    print("=" * 50)
    
    # Create sample problematic data that matches the error patterns
    problematic_data = [
        {
            'Member': 'John Smith',
            'DocID': 'DOC123',
            'Owner': 'arconic',  # Company name instead of valid owner type
            'Asset': 'Apple Inc Stock',
            'Ticker': 'AAPL',
            'Transaction Type': 'P',
            'Transaction Date': '01/15/2021',
            'Notification Date': '02/15/2021',
            'Amount': '$1,001 - $15,000 gfedc',  # Garbage characters
            'Description': 'Stock purchase'
        },
        {
            'Member': 'Jane Doe',
            'DocID': 'DOC124',
            'Owner': 'Oracle',  # Company name instead of valid owner type
            'Asset': 'Microsoft Corporation',
            'Ticker': 'MSFT',
            'Transaction Type': 'S',
            'Transaction Date': '02/20/2021',
            'Notification Date': '03/20/2021',
            'Amount': '$15,001 - gfedc',  # Incomplete range with garbage
            'Description': 'Stock sale'
        },
        {
            'Member': 'Bob Johnson',
            'DocID': 'DOC125',
            'Owner': 'goldman',  # Company name instead of valid owner type
            'Asset': 'Tesla Inc',
            'Ticker': 'TSLA',
            'Transaction Type': 'P',
            'Transaction Date': '03/10/2021',
            'Notification Date': '04/10/2021',
            'Amount': '$250,001 - $100000 xyzabc',  # Range error + garbage
            'Description': 'Electric vehicle stock'
        },
        {
            'Member': 'Sarah Wilson',
            'DocID': 'DOC126',
            'Owner': 'C',  # Valid owner type
            'Asset': 'Amazon.com Inc',
            'Ticker': 'AMZN',
            'Transaction Type': 'P',
            'Transaction Date': '04/05/2021',
            'Notification Date': '05/05/2021',
            'Amount': '$50,001 - $100,000',  # Clean amount
            'Description': 'E-commerce stock'
        }
    ]
    
    # Create DataFrame
    df = pd.DataFrame(problematic_data)
    
    print("Original problematic data:")
    print(df[['Owner', 'Amount']].to_string(index=False))
    print()
    
    # Apply data quality enhancements
    try:
        enhanced_df, stats = enhance_congressional_data_quality(df)
        
        print("Enhanced data:")
        print(enhanced_df[['Owner', 'Amount']].to_string(index=False))
        print()
        
        print("Enhancement Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print()
        
        # Test specific improvements
        print("Specific Test Results:")
        print("-" * 30)
        
        # Test 1: Owner field fixes
        print("1. Owner Field Fixes:")
        for i, (orig, enhanced) in enumerate(zip(df['Owner'], enhanced_df['Owner'])):
            if orig != enhanced:
                print(f"   Row {i}: '{orig}' → '{enhanced}'")
            else:
                print(f"   Row {i}: '{orig}' (unchanged)")
        print()
        
        # Test 2: Amount parsing fixes
        print("2. Amount Parsing Fixes:")
        for i, (orig, enhanced) in enumerate(zip(df['Amount'], enhanced_df['Amount'])):
            if orig != enhanced:
                print(f"   Row {i}: '{orig}' → '{enhanced}'")
            else:
                print(f"   Row {i}: '{orig}' (unchanged)")
        print()
        
        # Test 3: Check if amount_min and amount_max were created
        if 'amount_min' in enhanced_df.columns and 'amount_max' in enhanced_df.columns:
            print("3. Amount Range Parsing:")
            for i, row in enhanced_df.iterrows():
                min_amt = row.get('amount_min')
                max_amt = row.get('amount_max')
                if min_amt is not None or max_amt is not None:
                    min_str = f"${min_amt/100:,.0f}" if min_amt else "None"
                    max_str = f"${max_amt/100:,.0f}" if max_amt else "None"
                    print(f"   Row {i}: {min_str} - {max_str}")
                else:
                    print(f"   Row {i}: No amount parsed")
        print()
        
        # Calculate success metrics
        total_rows = len(df)
        owner_fixes = stats.get('fixed_owner_field', 0)
        amount_fixes = stats.get('fixed_amount_parsing', 0)
        garbage_removed = stats.get('removed_garbage_chars', 0)
        unfixable = stats.get('unfixable_rows', 0)
        
        success_rate = ((total_rows - unfixable) / total_rows * 100) if total_rows > 0 else 0
        
        print("Summary:")
        print(f"  Total rows processed: {total_rows}")
        print(f"  Owner field fixes: {owner_fixes}")
        print(f"  Amount parsing fixes: {amount_fixes}")
        print(f"  Garbage characters removed: {garbage_removed}")
        print(f"  Unfixable rows: {unfixable}")
        print(f"  Success rate: {success_rate:.1f}%")
        
        if success_rate >= 75:
            print("✅ Data quality enhancement test PASSED!")
        else:
            print("❌ Data quality enhancement test FAILED!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_amount_parsing_specific():
    """Test specific amount parsing patterns."""
    
    print("\nTesting Specific Amount Parsing Patterns")
    print("=" * 40)
    
    from domains.congressional.data_quality import CongressionalDataQualityEnhancer
    
    enhancer = CongressionalDataQualityEnhancer()
    
    test_amounts = [
        "$1,001 - $15,000 gfedc",
        "$15,001 - gfedc",
        "$250,001 - $100000 xyzabc",
        "$50,001 - $100,000",
        "$1,000,000 +",
        "$5,000",
        "1001 - 15000",
        "$1,001-$15,000",
        "15001 + abcd",
    ]
    
    print("Amount String → Parsed Result (min, max)")
    print("-" * 45)
    
    for amount_str in test_amounts:
        try:
            min_amt, max_amt = enhancer._parse_amount_range(amount_str)
            
            min_display = f"${min_amt/100:,.0f}" if min_amt else "None"
            max_display = f"${max_amt/100:,.0f}" if max_amt else "None"
            
            print(f"'{amount_str}' → ({min_display}, {max_display})")
            
        except Exception as e:
            print(f"'{amount_str}' → ERROR: {e}")

if __name__ == "__main__":
    test_data_quality_enhancements()
    test_amount_parsing_specific() 