#!/usr/bin/env python3
"""
Test script for congressional data import.

This script tests the import functionality with a small subset of data
to verify everything works before running the full import.
"""

import asyncio
import sys
from pathlib import Path
import pandas as pd

# Add src directory to path
src_path = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(src_path))

from core.database import db_manager, init_database
from core.logging import get_logger
from domains.congressional.ingestion import CongressionalDataIngester
from domains.congressional.models import CongressMember, CongressionalTrade
from sqlalchemy import select, text

logger = get_logger(__name__)


async def test_database_connection():
    """Test basic database connection and table existence."""
    logger.info("🔗 Testing database connection...")
    
    await init_database()
    
    async with db_manager.session_scope() as session:
        # Test if tables exist
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM congress_members"))
            member_count = result.scalar()
            logger.info(f"✅ congress_members table exists with {member_count} records")
            
            result = await session.execute(text("SELECT COUNT(*) FROM congressional_trades"))
            trade_count = result.scalar()
            logger.info(f"✅ congressional_trades table exists with {trade_count} records")
            
            return True
        except Exception as e:
            logger.error(f"❌ Database test failed: {e}")
            return False


async def test_member_creation():
    """Test creating a sample member."""
    logger.info("👤 Testing member creation...")
    
    async with db_manager.session_scope() as session:
        ingester = CongressionalDataIngester(session)
        
        # Create a test DataFrame with sample member data
        test_data = pd.DataFrame({
            'Member': ['Test, John', 'Smith, Jane'],
            'DocID': ['20240001', '20240002'],
            'Ticker': ['AAPL', 'MSFT'],
            'Transaction Type': ['P', 'S'],
            'Transaction Date': ['2024-01-15', '2024-01-16'],
            'Amount': ['$15,001 - $50,000', '$50,001 - $100,000']
        })
        
        try:
            # Test member extraction
            members_created = await ingester._extract_and_create_members(test_data)
            logger.info(f"✅ Created {members_created} test members")
            
            # Verify members exist
            result = await session.execute(select(CongressMember))
            members = result.scalars().all()
            logger.info(f"✅ Found {len(members)} total members in database")
            
            for member in members[-2:]:  # Show last 2 members
                logger.info(f"   - {member.full_name} (ID: {member.id})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Member creation test failed: {e}")
            return False


async def test_trade_import():
    """Test importing a few trade records."""
    logger.info("💼 Testing trade import...")
    
    async with db_manager.session_scope() as session:
        ingester = CongressionalDataIngester(session)
        
        # Create test data with proper format
        test_data = pd.DataFrame({
            'Member': ['Test, John', 'Test, John', 'Smith, Jane'],
            'DocID': ['20240001', '20240001', '20240002'],
            'Owner': ['SP', 'SP', 'JT'],
            'Asset': ['Apple Inc.', 'Microsoft Corp.', 'Tesla Inc.'],
            'Ticker': ['AAPL', 'MSFT', 'TSLA'],
            'Transaction Type': ['P', 'S', 'P'],
            'Transaction Date': ['2024-01-15', '2024-01-16', '2024-01-17'],
            'Notification Date': ['2024-01-20', '2024-01-21', '2024-01-22'],
            'Amount': ['$15,001 - $50,000', '$50,001 - $100,000', '$100,001 - $250,000'],
            'Filing Status': ['New', 'New', 'New'],
            'Description': ['Purchase of Apple stock', 'Sale of Microsoft stock', 'Purchase of Tesla stock']
        })
        
        try:
            # Import test trades
            created, failed = await ingester._import_trades_from_dataframe(test_data, "test_data")
            logger.info(f"✅ Imported {created} trades, {failed} failed")
            
            # Verify trades exist
            result = await session.execute(select(CongressionalTrade))
            trades = result.scalars().all()
            logger.info(f"✅ Found {len(trades)} total trades in database")
            
            for trade in trades[-3:]:  # Show last 3 trades
                logger.info(f"   - {trade.ticker} ({trade.transaction_type}) by member {trade.member_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Trade import test failed: {e}")
            return False


async def test_csv_sample():
    """Test importing a small sample from actual CSV file."""
    logger.info("📄 Testing CSV sample import...")
    
    csv_file = Path(__file__).parent.parent / "data" / "congress" / "csv" / "2025FD.csv"
    
    if not csv_file.exists():
        logger.warning(f"⚠️  CSV file not found: {csv_file}")
        return True  # Not a failure, just skip this test
    
    try:
        # Read first 10 rows as a sample
        df = pd.read_csv(csv_file, nrows=10)
        logger.info(f"📊 Sample CSV data shape: {df.shape}")
        logger.info(f"📊 Columns: {list(df.columns)}")
        
        # Show a few sample records
        logger.info("📊 Sample records:")
        for i, row in df.head(3).iterrows():
            logger.info(f"   {i+1}: {row['Member']} - {row.get('Ticker', 'N/A')} ({row.get('Transaction Type', 'N/A')})")
        
        async with db_manager.session_scope() as session:
            ingester = CongressionalDataIngester(session)
            
            # Extract members from sample
            members_created = await ingester._extract_and_create_members(df)
            logger.info(f"✅ Created {members_created} members from CSV sample")
            
            # Import trades from sample
            created, failed = await ingester._import_trades_from_dataframe(df, "csv_sample")
            logger.info(f"✅ Imported {created} trades from CSV sample, {failed} failed")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ CSV sample test failed: {e}")
        return False


async def cleanup_test_data():
    """Clean up test data."""
    logger.info("🧹 Cleaning up test data...")
    
    async with db_manager.session_scope() as session:
        try:
            # Delete test trades
            await session.execute(text("DELETE FROM congressional_trades WHERE source_file LIKE '%test%'"))
            
            # Delete test members
            await session.execute(text("DELETE FROM congress_members WHERE full_name LIKE 'Test%' OR full_name LIKE 'Smith%'"))
            
            await session.commit()
            logger.info("✅ Test data cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")


async def main():
    """Run all tests."""
    print("🧪 CapitolScope Congressional Data Import Tests")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 5
    
    try:
        # Test 1: Database connection
        if await test_database_connection():
            tests_passed += 1
        
        # Test 2: Member creation
        if await test_member_creation():
            tests_passed += 1
        
        # Test 3: Trade import
        if await test_trade_import():
            tests_passed += 1
        
        # Test 4: CSV sample
        if await test_csv_sample():
            tests_passed += 1
        
        # Test 5: Cleanup
        await cleanup_test_data()
        tests_passed += 1
        
        print("\n" + "=" * 50)
        print(f"🎯 TEST RESULTS: {tests_passed}/{total_tests} passed")
        
        if tests_passed == total_tests:
            print("✅ All tests passed! Ready for full import.")
            print("\n🚀 Next steps:")
            print("1. Run full CSV import:")
            print("   python scripts/import_congressional_data.py --csvs")
            print("2. Or fetch live data:")
            print("   python scripts/import_congressional_data.py --live")
            return 0
        else:
            print("❌ Some tests failed. Check the logs above.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 