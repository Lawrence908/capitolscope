#!/usr/bin/env python3
"""
Comprehensive testing script for congressional import pipeline.

This script validates the implementation before production deployment.
"""

import sys
import os
import csv
import json
import tempfile
from datetime import datetime, date
from pathlib import Path

# Add app source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'src'))

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from domains.congressional.data_quality import DataQualityEnhancer, TickerExtractionResult
        from domains.congressional.ingestion import CongressionalDataIngestion
        print("✅ Core modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("💡 Try: pip install -r requirements_congressional.txt")
        return False

def test_data_quality_components():
    """Test individual data quality components."""
    print("\n🧪 Testing data quality components...")
    
    try:
        from domains.congressional.data_quality import DataQualityEnhancer
        enhancer = DataQualityEnhancer()
        
        # Test ticker extraction
        test_cases = [
            ("Apple Inc Common Stock", "AAPL"),
            ("Microsoft Corporation", "MSFT"), 
            ("SPDR S&P 500 ETF", "SPY"),
            ("Alphabet Inc Class A", "GOOGL"),
            ("(TSLA) Tesla Inc", "TSLA"),
        ]
        
        ticker_successes = 0
        for description, expected in test_cases:
            result = enhancer.extract_ticker(description)
            if result.ticker == expected:
                print(f"✅ Ticker: '{description}' → {result.ticker}")
                ticker_successes += 1
            else:
                print(f"❌ Ticker: '{description}' → {result.ticker} (expected {expected})")
        
        print(f"📊 Ticker extraction: {ticker_successes}/{len(test_cases)} successful")
        
        # Test amount normalization
        amount_test_cases = [
            ("$1,001 - $15,000", (100100, 1500000)),
            ("$1,001 - $15,000 gfedc", (100100, 1500000)),
            ("$50,000,000+", (5000000000, None)),
            ("Between $100,001 and $250,000", (10000100, 25000000)),
        ]
        
        amount_successes = 0
        for amount_str, expected in amount_test_cases:
            result = enhancer.normalize_amount(amount_str)
            if (result.amount_min, result.amount_max) == expected:
                print(f"✅ Amount: '{amount_str}' → min={result.amount_min}, max={result.amount_max}")
                amount_successes += 1
            else:
                print(f"❌ Amount: '{amount_str}' → min={result.amount_min}, max={result.amount_max} (expected {expected})")
        
        print(f"📊 Amount normalization: {amount_successes}/{len(amount_test_cases)} successful")
        
        # Test owner normalization
        owner_test_cases = [
            ("SPOUSE", "SP"),
            ("C", "C"),
            ("JOINT ACCOUNT", "JT"),
            ("DEPENDENT CHILD", "DC"),
            ("Apple Inc", "C"),  # Misalignment case
        ]
        
        owner_successes = 0
        for owner_str, expected in owner_test_cases:
            result = enhancer.normalize_owner(owner_str)
            if result.normalized_owner and result.normalized_owner.value == expected:
                print(f"✅ Owner: '{owner_str}' → {result.normalized_owner.value}")
                owner_successes += 1
            else:
                print(f"❌ Owner: '{owner_str}' → {result.normalized_owner} (expected {expected})")
        
        print(f"📊 Owner normalization: {owner_successes}/{len(owner_test_cases)} successful")
        
        return ticker_successes, amount_successes, owner_successes
        
    except Exception as e:
        print(f"❌ Data quality testing failed: {e}")
        return 0, 0, 0

def create_test_csv():
    """Create a test CSV file with sample congressional trades."""
    print("\n🧪 Creating test CSV...")
    
    test_data = [
        {
            'doc_id': 'TEST001',
            'member_name': 'Test Member 1',
            'raw_asset_description': 'Apple Inc Common Stock',
            'transaction_type': 'P',
            'transaction_date': '2024-01-15',
            'owner': 'C',
            'amount': '$1,001 - $15,000'
        },
        {
            'doc_id': 'TEST002', 
            'member_name': 'Test Member 2',
            'raw_asset_description': 'Microsoft Corporation',
            'transaction_type': 'S',
            'transaction_date': '2024-01-16',
            'owner': 'SPOUSE',
            'amount': '$15,001 - $50,000 gfedc'
        },
        {
            'doc_id': 'TEST003',
            'member_name': 'Test Member 3', 
            'raw_asset_description': 'SPDR S&P 500 ETF',
            'transaction_type': 'P',
            'transaction_date': '2024-01-17',
            'owner': 'JT',
            'amount': '$50,001 - $100,000'
        },
        {
            'doc_id': 'TEST004',
            'member_name': 'Test Member 4',
            'raw_asset_description': 'Unknown Company XYZ',
            'transaction_type': 'P', 
            'transaction_date': '2024-01-18',
            'owner': 'Apple Inc',  # Misalignment case
            'amount': '$100,001 - $250,000 abcdef'
        },
        {
            'doc_id': 'TEST005',
            'member_name': 'Test Member 5',
            'raw_asset_description': 'Tesla Motors Inc',
            'transaction_type': 'E',
            'transaction_date': '2024-01-19', 
            'owner': 'DC',
            'amount': 'Over $50,000,000'
        }
    ]
    
    # Create temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    
    fieldnames = test_data[0].keys()
    writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(test_data)
    temp_file.close()
    
    print(f"✅ Test CSV created: {temp_file.name}")
    return temp_file.name

def test_database_connection():
    """Test database connection without making changes."""
    print("\n🧪 Testing database connection...")
    
    try:
        from core.database import db_manager
        
        with db_manager.session_scope() as session:
            # Simple query to test connection
            result = session.execute("SELECT 1").scalar()
            if result == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("💡 Check database configuration and ensure PostgreSQL is running")
        return False

def test_existing_data_analysis():
    """Analyze existing congressional trade data."""
    print("\n🧪 Analyzing existing congressional trade data...")
    
    try:
        from core.database import db_manager
        from domains.congressional.models import CongressionalTrade
        from sqlalchemy import func
        
        with db_manager.session_scope() as session:
            # Get basic counts
            total_trades = session.query(CongressionalTrade).count()
            null_tickers = session.query(CongressionalTrade).filter(
                CongressionalTrade.ticker.is_(None)
            ).count()
            
            print(f"📊 Total congressional trades: {total_trades}")
            print(f"📊 Trades with NULL tickers: {null_tickers}")
            
            if total_trades > 0:
                null_percentage = (null_tickers / total_trades) * 100
                print(f"📊 NULL ticker percentage: {null_percentage:.1f}%")
                
                # Sample some records for analysis
                sample_trades = session.query(CongressionalTrade).limit(5).all()
                print(f"📊 Sample trade records found: {len(sample_trades)}")
                
                return {
                    'total_trades': total_trades,
                    'null_tickers': null_tickers,
                    'null_percentage': null_percentage,
                    'has_data': total_trades > 0
                }
            else:
                print("📊 No existing congressional trade data found")
                return {
                    'total_trades': 0,
                    'null_tickers': 0, 
                    'null_percentage': 0,
                    'has_data': False
                }
                
    except Exception as e:
        print(f"❌ Database analysis error: {e}")
        return None

def run_comprehensive_test():
    """Run comprehensive testing suite."""
    print("🚀 Starting Congressional Import Pipeline Testing")
    print("=" * 60)
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Testing stopped - import failures")
        return False
    
    # Test 2: Data quality components  
    ticker_score, amount_score, owner_score = test_data_quality_components()
    
    # Test 3: Database connection
    db_connected = test_database_connection()
    
    # Test 4: Existing data analysis
    existing_data = test_existing_data_analysis()
    
    # Test 5: Create test CSV
    test_csv_path = create_test_csv()
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📋 TESTING SUMMARY REPORT")
    print("=" * 60)
    
    print(f"✅ Import Success: {'Yes' if True else 'No'}")
    print(f"✅ Database Connection: {'Yes' if db_connected else 'No'}")
    print(f"📊 Ticker Extraction: {ticker_score}/5 test cases passed")
    print(f"📊 Amount Normalization: {amount_score}/4 test cases passed") 
    print(f"📊 Owner Normalization: {owner_score}/5 test cases passed")
    
    if existing_data:
        print(f"📊 Existing Trades: {existing_data['total_trades']}")
        print(f"📊 NULL Tickers: {existing_data['null_tickers']} ({existing_data['null_percentage']:.1f}%)")
    
    print(f"📁 Test CSV Created: {test_csv_path}")
    
    # Overall assessment
    total_score = ticker_score + amount_score + owner_score
    max_score = 5 + 4 + 5  # Total possible points
    
    print(f"\n🎯 Overall Quality Score: {total_score}/{max_score} ({(total_score/max_score)*100:.1f}%)")
    
    if total_score >= max_score * 0.8 and db_connected:
        print("✅ READY FOR PRODUCTION TESTING")
        print("💡 Next step: Test with real data sample")
    elif total_score >= max_score * 0.6:
        print("⚠️ NEEDS REFINEMENT")
        print("💡 Fix failing test cases before production")
    else:
        print("❌ SIGNIFICANT ISSUES FOUND") 
        print("💡 Major fixes required before testing")
    
    # Cleanup
    try:
        os.unlink(test_csv_path)
        print(f"🧹 Cleaned up test file: {test_csv_path}")
    except:
        pass
    
    return total_score >= max_score * 0.8 and db_connected

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)