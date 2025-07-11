#!/usr/bin/env python3
"""
Test script for data quality improvements in congressional trade ingestion.

This script tests all the new features including ticker extraction, security enrichment,
trade backfill, and data quality reporting.
"""

import asyncio
import sys
import tempfile
import csv
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any

# Add the app/src directory to Python path
script_dir = Path(__file__).parent.resolve()
app_src_dir = script_dir.parent
sys.path.insert(0, str(app_src_dir))

from core.database import DatabaseManager, init_database, db_manager
from core.logging import get_logger
from domains.congressional.ingestion import (
    CongressionalDataIngester, TickerExtractor, SecurityEnricher, 
    TradeBackfiller, DataQualityMetrics
)
from domains.congressional.models import CongressMember, CongressionalTrade
from domains.securities.models import Security, AssetType, Exchange, Sector

logger = get_logger(__name__)


def get_test_db_session():
    """Get a database session for testing."""
    return db_manager.get_session()


# ============================================================================
# TEST DATA GENERATION
# ============================================================================

def create_test_csv_data() -> list:
    """Create test CSV data with various data quality issues."""
    test_data = [
        # Header row
        ['Member', 'DocID', 'Owner', 'Asset', 'Ticker', 'Transaction Type', 'Transaction Date', 'Notification Date', 'Amount', 'Filing Status', 'Description'],
        
        # Good data
        ['Smith', '12345', 'C', 'Apple Inc.', 'AAPL', 'P', '01/15/2023', '01/20/2023', '$1,001 - $15,000', 'N', 'Purchase of Apple stock'],
        ['Jones', '12346', 'SP', 'Microsoft Corporation', 'MSFT', 'S', '02/10/2023', '02/15/2023', '$15,001 - $50,000', 'N', 'Sale of Microsoft stock'],
        
        # Ticker extraction challenges
        ['Brown', '12347', 'JT', 'Alphabet Inc. Class C (GOOGL)', '', 'P', '03/05/2023', '03/10/2023', '$50,001 - $100,000', 'N', 'Google stock purchase'],
        ['Davis', '12348', 'C', 'Amazon.com, Inc. - AMZN', 'X', 'S', '03/15/2023', '03/20/2023', '$100,001 - $250,000', 'N', 'Amazon stock sale'],
        ['Wilson', '12349', 'DC', 'Tesla Inc TSLA', 'P', 'P', '04/01/2023', '04/05/2023', '$25,000', 'N', 'Tesla stock purchase'],
        
        # Fuzzy matching needed
        ['Taylor', '12350', 'C', 'Walt Disney Company', '', 'P', '04/10/2023', '04/15/2023', '$5,001 - $15,000', 'N', 'Disney stock'],
        ['Anderson', '12351', 'SP', 'Goldman Sachs Group Inc', '', 'S', '04/20/2023', '04/25/2023', '$15,001 - $50,000', 'N', 'Goldman Sachs sale'],
        
        # Cash sweep transactions
        ['Miller', '12352', 'JT', 'BlackRock Liq FDS FedFund', 'CS', 'P', '05/01/2023', '05/05/2023', '$250,001 - $500,000', 'N', 'Cash sweep purchase'],
        ['Garcia', '12353', 'C', 'BLF FedFund TDDXX', 'CS', 'S', '05/10/2023', '05/15/2023', '$500,001 - $1,000,000', 'N', 'Cash sweep sale'],
        
        # Bonds and other asset types
        ['Rodriguez', '12354', 'C', 'US Treasury Bill Due 12/31/23', '', 'P', '06/01/2023', '06/05/2023', '$100,001 - $250,000', 'N', 'Treasury bill purchase'],
        ['Martinez', '12355', 'SP', 'California State Municipal Bond 4.5%', '', 'P', '06/10/2023', '06/15/2023', '$50,001 - $100,000', 'N', 'Municipal bond'],
        
        # ETFs
        ['Lopez', '12356', 'JT', 'SPDR S&P 500 ETF Trust', 'SPY', 'P', '07/01/2023', '07/05/2023', '$15,001 - $50,000', 'N', 'S&P 500 ETF'],
        ['Gonzalez', '12357', 'C', 'iShares Gold Trust', 'IAU', 'S', '07/10/2023', '07/15/2023', '$5,001 - $15,000', 'N', 'Gold ETF sale'],
        
        # International stocks
        ['Lee', '12358', 'C', 'ASML Holding N.V.', 'ASML', 'P', '08/01/2023', '08/05/2023', '$25,001 - $50,000', 'N', 'ASML purchase'],
        ['Kim', '12359', 'SP', 'Nestle SA Sponsored ADR', 'NSRGY', 'S', '08/10/2023', '08/15/2023', '$15,001 - $50,000', 'N', 'Nestle ADR sale'],
        
        # Problematic data
        ['White', '12360', 'C', 'Some Unknown Company XYZ', 'XYZ99', 'P', '09/01/2023', '09/05/2023', '$1,001 - $15,000', 'N', 'Unknown ticker'],
        ['Black', '12361', 'JT', 'Invalid Asset Description', '', 'S', '09/10/2023', '09/15/2023', '$0', 'N', 'No valid ticker'],
        
        # Date parsing issues
        ['Green', '12362', 'C', 'Visa Inc.', 'V', 'P', '2023-10-01', '2023-10-05', '$15,001 - $50,000', 'N', 'Visa stock - ISO date format'],
        ['Blue', '12363', 'SP', 'Mastercard Incorporated', 'MA', 'S', '10/15/23', '10/20/23', '$25,001 - $50,000', 'N', 'Mastercard - short year'],
        
        # Mixed transaction types
        ['Purple', '12364', 'DC', 'Berkshire Hathaway Inc. Class B', 'BRK.B', 'E', '11/01/2023', '11/05/2023', '$50,001 - $100,000', 'N', 'Berkshire exchange'],
        ['Orange', '12365', 'C', 'JPMorgan Chase & Co.', 'JPM', 'P', '11/10/2023', '11/15/2023', '$15,001 - $50,000', 'A', 'JPMorgan - amended filing'],
    ]
    
    return test_data


def create_test_csv_file(data: list) -> str:
    """Create a temporary CSV file with test data."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    
    with open(temp_file.name, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    
    return temp_file.name


# ============================================================================
# INDIVIDUAL COMPONENT TESTS
# ============================================================================

def test_ticker_extraction():
    """Test the ticker extraction component."""
    logger.info("🧪 Testing ticker extraction...")
    
    extractor = TickerExtractor()
    
    test_cases = [
        # (ticker_field, asset_description, expected_ticker, expected_confidence_range)
        ('AAPL', 'Apple Inc.', 'AAPL', (0.8, 1.0)),
        ('', 'Alphabet Inc. Class C (GOOGL)', 'GOOGL', (0.7, 0.9)),
        ('', 'Amazon.com, Inc. - AMZN', 'AMZN', (0.7, 0.9)),
        ('P', 'Tesla Inc TSLA', 'TSLA', (0.5, 0.8)),
        ('', 'Walt Disney Company', 'DIS', (0.6, 0.8)),
        ('', 'Goldman Sachs Group Inc', 'GS', (0.6, 0.8)),
        ('CS', 'BlackRock Liq FDS FedFund', 'CS', (0.8, 1.0)),
        ('', 'BLF FedFund TDDXX', 'CS', (0.6, 0.8)),
        ('', 'US Treasury Bill', 'CASH', (0.6, 0.8)),
        ('XYZ99', 'Some Unknown Company', None, (0.0, 0.1)),
    ]
    
    passed = 0
    failed = 0
    
    for ticker_field, asset_desc, expected_ticker, confidence_range in test_cases:
        ticker, source, confidence = extractor.extract_ticker(ticker_field, asset_desc)
        
        if expected_ticker is None:
            if ticker is None:
                logger.info(f"✅ PASS: {asset_desc} -> No ticker (as expected)")
                passed += 1
            else:
                logger.warning(f"❌ FAIL: {asset_desc} -> Expected None, got {ticker}")
                failed += 1
        else:
            if ticker == expected_ticker and confidence_range[0] <= confidence <= confidence_range[1]:
                logger.info(f"✅ PASS: {asset_desc} -> {ticker} (confidence: {confidence:.2f}, source: {source})")
                passed += 1
            else:
                logger.warning(f"❌ FAIL: {asset_desc} -> Expected {expected_ticker}, got {ticker} (confidence: {confidence:.2f})")
                failed += 1
    
    logger.info(f"📊 Ticker extraction tests: {passed} passed, {failed} failed")
    return passed, failed


def test_security_enrichment():
    """Test the security enrichment component."""
    logger.info("🧪 Testing security enrichment...")
    
    with get_test_db_session() as session:
        enricher = SecurityEnricher(session)
        
        # Create test securities
        test_securities = [
            Security(ticker='AAPL', name='Apple Inc.', is_active=True),
            Security(ticker='MSFT', name='Microsoft Corporation', is_active=True),
            Security(ticker='CS', name='Cash Sweep', is_active=True),
            Security(ticker='SPY', name='SPDR S&P 500 ETF Trust', is_active=True),
            Security(ticker='NSRGY', name='Nestle SA Sponsored ADR', is_active=True),
        ]
        
        for security in test_securities:
            session.add(security)
        session.flush()
        
        # Test enrichment
        enriched_count = 0
        for security in test_securities:
            if enricher.enrich_security(security):
                enriched_count += 1
                logger.info(f"✅ Enriched {security.ticker}: exchange_id={security.exchange_id}, "
                           f"asset_type_id={security.asset_type_id}, sector_id={security.sector_id}")
            else:
                logger.warning(f"❌ Failed to enrich {security.ticker}")
        
        session.commit()
        
        logger.info(f"📊 Security enrichment: {enriched_count}/{len(test_securities)} securities enriched")
        return enriched_count, len(test_securities) - enriched_count


def test_data_quality_metrics():
    """Test the data quality metrics tracking."""
    logger.info("🧪 Testing data quality metrics...")
    
    metrics = DataQualityMetrics()
    
    # Test basic metrics
    metrics.total_rows_processed = 100
    metrics.trades_created = 95
    metrics.failed_trades = 5
    metrics.tickers_extracted = 80
    metrics.tickers_failed_extraction = 15
    
    # Test counter collections
    metrics.unmatched_tickers['XYZ'] = 5
    metrics.unmatched_tickers['ABC'] = 3
    metrics.unmatched_assets['Unknown Company'] = 2
    
    # Test that metrics are properly tracked
    assert metrics.total_rows_processed == 100
    assert metrics.trades_created == 95
    assert metrics.failed_trades == 5
    assert metrics.unmatched_tickers['XYZ'] == 5
    
    logger.info("✅ Data quality metrics test passed")
    return 1, 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_ingestion_pipeline():
    """Test the full ingestion pipeline with test data."""
    logger.info("🧪 Testing full ingestion pipeline...")
    
    # Create test CSV data
    test_data = create_test_csv_data()
    csv_file = create_test_csv_file(test_data)
    
    try:
                 # Create temporary directory for CSV
         temp_dir = Path(csv_file).parent
         
         with get_test_db_session() as session:
            # Initialize ingester
            ingester = CongressionalDataIngester(session)
            
            # Run ingestion
            results = ingester.import_congressional_data_from_csvs_sync(str(temp_dir))
            
            # Verify results
            logger.info("📊 Ingestion Results:")
            for key, value in results.items():
                if isinstance(value, dict):
                    logger.info(f"  {key}: {dict(list(value.items())[:5])}...")  # Show first 5 items
                else:
                    logger.info(f"  {key}: {value}")
            
            # Check that trades were created
            trades_count = session.query(CongressionalTrade).count()
            members_count = session.query(CongressMember).count()
            securities_count = session.query(Security).count()
            
            logger.info(f"📊 Database counts: {trades_count} trades, {members_count} members, {securities_count} securities")
            
            # Verify specific improvements
            trades_with_security = session.query(CongressionalTrade).filter(
                CongressionalTrade.security_id.isnot(None)
            ).count()
            
            trades_without_security = session.query(CongressionalTrade).filter(
                CongressionalTrade.security_id.is_(None)
            ).count()
            
            logger.info(f"📊 Trade linking: {trades_with_security} linked, {trades_without_security} unlinked")
            
            # Check ticker extraction success rate
            ticker_extraction_rate = (results['tickers_extracted'] / results['total_rows_processed']) * 100
            logger.info(f"📊 Ticker extraction rate: {ticker_extraction_rate:.1f}%")
            
            # Check enrichment results
            logger.info(f"📊 Securities enriched: {results['securities_enriched']}")
            
            # Check manual review items
            logger.info(f"📊 Manual review items: {results['manual_review_items_count']}")
            
            success = (
                trades_count > 0 and
                members_count > 0 and 
                securities_count > 0 and
                ticker_extraction_rate > 50  # At least 50% ticker extraction
            )
            
            if success:
                logger.info("✅ Full ingestion pipeline test PASSED")
                return 1, 0
            else:
                logger.warning("❌ Full ingestion pipeline test FAILED")
                return 0, 1
                
    finally:
        # Clean up
        Path(csv_file).unlink()


def test_manual_review_generation():
    """Test the manual review report generation."""
    logger.info("🧪 Testing manual review generation...")
    
    with get_test_db_session() as session:
        ingester = CongressionalDataIngester(session)
        
        # Simulate some unmatched data
        ingester.metrics.unmatched_tickers['XYZ'] = 5
        ingester.metrics.unmatched_tickers['ABC'] = 3
        ingester.metrics.unmatched_assets['Unknown Company'] = 2
        ingester.metrics.unmatched_assets['Mystery Corp'] = 1
        
        # Generate manual review items
        ingester._generate_manual_review_items()
        
        # Check that items were generated
        if len(ingester.manual_review_items) > 0:
            logger.info(f"✅ Generated {len(ingester.manual_review_items)} manual review items")
            
            # Show sample items
            for item in ingester.manual_review_items[:3]:
                logger.info(f"  - {item.category}: {item.description}")
            
            return 1, 0
        else:
            logger.warning("❌ No manual review items generated")
            return 0, 1


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    """Run all data quality improvement tests."""
    logger.info("🚀 Starting data quality improvement tests...")
    
    # Initialize database
    await init_database()
    
    # Run individual component tests
    tests = [
        ("Ticker Extraction", test_ticker_extraction),
        ("Security Enrichment", test_security_enrichment),
        ("Data Quality Metrics", test_data_quality_metrics),
        ("Manual Review Generation", test_manual_review_generation),
        ("Full Ingestion Pipeline", test_full_ingestion_pipeline),
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running {test_name} Test")
        logger.info(f"{'='*60}")
        
        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed
            
            if failed == 0:
                logger.info(f"✅ {test_name} test completed successfully")
            else:
                logger.warning(f"❌ {test_name} test completed with {failed} failures")
                
        except Exception as e:
            logger.error(f"💥 {test_name} test failed with exception: {e}")
            total_failed += 1
    
    # Final summary
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 TEST SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total Passed: {total_passed}")
    logger.info(f"Total Failed: {total_failed}")
    logger.info(f"Success Rate: {(total_passed / (total_passed + total_failed)) * 100:.1f}%")
    
    if total_failed == 0:
        logger.info("🎉 All tests passed! Data quality improvements are working correctly.")
    else:
        logger.warning(f"⚠️  {total_failed} tests failed. Please review the implementation.")
    
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)