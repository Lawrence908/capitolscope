#!/usr/bin/env python3
"""
Congressional data import recovery and testing script.

This script provides utilities for:
- Database state checking and cleanup
- Import testing and validation
- Performance analysis and optimization
- Data quality assessment and improvement
- Recovery from failed imports
"""

import sys
import os
import json
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal

# Add the app source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, func, desc, and_, or_
from sqlalchemy.orm import Session

from core.database import db_manager
from core.logging import get_logger
from domains.congressional.models import CongressMember, CongressionalTrade
from domains.congressional.ingestion import CongressionalDataIngestion
from domains.congressional.data_quality import DataQualityEnhancer, QualityReport
from domains.securities.models import Security

logger = get_logger(__name__)


@dataclass
class DatabaseState:
    """Database state information."""
    total_members: int
    total_trades: int
    trades_with_ticker: int
    trades_with_amount: int
    trades_with_valid_owner: int
    null_ticker_count: int
    null_amount_count: int
    invalid_owner_count: int
    duplicate_count: int
    recent_imports: List[Dict[str, Any]]
    
    @property
    def ticker_extraction_rate(self) -> float:
        """Calculate ticker extraction rate."""
        if self.total_trades == 0:
            return 0.0
        return (self.trades_with_ticker / self.total_trades) * 100
    
    @property
    def amount_parsing_rate(self) -> float:
        """Calculate amount parsing rate."""
        if self.total_trades == 0:
            return 0.0
        return (self.trades_with_amount / self.total_trades) * 100
    
    @property
    def owner_normalization_rate(self) -> float:
        """Calculate owner normalization rate."""
        if self.total_trades == 0:
            return 0.0
        return (self.trades_with_valid_owner / self.total_trades) * 100


class CongressionalImportRecovery:
    """Recovery and testing utilities for congressional data import."""
    
    def __init__(self):
        self.data_quality = DataQualityEnhancer()
        self.ingestion = CongressionalDataIngestion()
        
    def check_database_state(self) -> DatabaseState:
        """Check current database state and return summary."""
        logger.info("Checking database state...")
        
        with db_manager.session_scope() as session:
            # Basic counts
            total_members = session.query(CongressMember).count()
            total_trades = session.query(CongressionalTrade).count()
            
            # Quality metrics
            trades_with_ticker = session.query(CongressionalTrade).filter(
                CongressionalTrade.ticker.isnot(None)
            ).count()
            
            trades_with_amount = session.query(CongressionalTrade).filter(
                or_(
                    CongressionalTrade.amount_min.isnot(None),
                    CongressionalTrade.amount_max.isnot(None),
                    CongressionalTrade.amount_exact.isnot(None)
                )
            ).count()
            
            trades_with_valid_owner = session.query(CongressionalTrade).filter(
                CongressionalTrade.owner.in_(['C', 'SP', 'JT', 'DC'])
            ).count()
            
            # Problem counts
            null_ticker_count = session.query(CongressionalTrade).filter(
                CongressionalTrade.ticker.is_(None)
            ).count()
            
            null_amount_count = session.query(CongressionalTrade).filter(
                and_(
                    CongressionalTrade.amount_min.is_(None),
                    CongressionalTrade.amount_max.is_(None),
                    CongressionalTrade.amount_exact.is_(None)
                )
            ).count()
            
            invalid_owner_count = session.query(CongressionalTrade).filter(
                CongressionalTrade.owner.notin_(['C', 'SP', 'JT', 'DC'])
            ).count()
            
            # Duplicate count
            duplicate_query = text("""
                SELECT COUNT(*) - COUNT(DISTINCT doc_id, member_id, transaction_date, raw_asset_description)
                FROM congressional_trades
            """)
            duplicate_count = session.execute(duplicate_query).scalar() or 0
            
            # Recent imports (last 7 days)
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_trades = session.query(CongressionalTrade).filter(
                CongressionalTrade.created_at >= recent_cutoff
            ).order_by(desc(CongressionalTrade.created_at)).limit(10).all()
            
            recent_imports = [
                {
                    'id': trade.id,
                    'doc_id': trade.doc_id,
                    'member_id': trade.member_id,
                    'ticker': trade.ticker,
                    'transaction_date': trade.transaction_date.isoformat(),
                    'created_at': trade.created_at.isoformat()
                }
                for trade in recent_trades
            ]
            
        return DatabaseState(
            total_members=total_members,
            total_trades=total_trades,
            trades_with_ticker=trades_with_ticker,
            trades_with_amount=trades_with_amount,
            trades_with_valid_owner=trades_with_valid_owner,
            null_ticker_count=null_ticker_count,
            null_amount_count=null_amount_count,
            invalid_owner_count=invalid_owner_count,
            duplicate_count=duplicate_count,
            recent_imports=recent_imports
        )
    
    def analyze_problematic_records(self, limit: int = 100) -> Dict[str, Any]:
        """Analyze problematic records and suggest fixes."""
        logger.info(f"Analyzing {limit} problematic records...")
        
        analysis = {
            'null_ticker_analysis': self._analyze_null_tickers(limit),
            'amount_parsing_analysis': self._analyze_amount_issues(limit),
            'owner_normalization_analysis': self._analyze_owner_issues(limit),
            'recommendations': []
        }
        
        # Generate recommendations
        ticker_issues = analysis['null_ticker_analysis']['sample_count']
        amount_issues = analysis['amount_parsing_analysis']['sample_count']
        owner_issues = analysis['owner_normalization_analysis']['sample_count']
        
        if ticker_issues > 0:
            analysis['recommendations'].append(
                f"Found {ticker_issues} records with ticker extraction issues. "
                f"Consider expanding company name mappings."
            )
        
        if amount_issues > 0:
            analysis['recommendations'].append(
                f"Found {amount_issues} records with amount parsing issues. "
                f"Review amount field data quality."
            )
        
        if owner_issues > 0:
            analysis['recommendations'].append(
                f"Found {owner_issues} records with owner normalization issues. "
                f"Check for data misalignment problems."
            )
        
        return analysis
    
    def _analyze_null_tickers(self, limit: int) -> Dict[str, Any]:
        """Analyze records with null tickers."""
        with db_manager.session_scope() as session:
            null_ticker_trades = session.query(CongressionalTrade).filter(
                CongressionalTrade.ticker.is_(None)
            ).limit(limit).all()
            
            analysis = {
                'sample_count': len(null_ticker_trades),
                'asset_description_patterns': {},
                'potential_fixes': [],
                'examples': []
            }
            
            for trade in null_ticker_trades:
                # Test ticker extraction
                if trade.raw_asset_description:
                    result = self.data_quality.extract_ticker(trade.raw_asset_description)
                    
                    if result.ticker:
                        analysis['potential_fixes'].append({
                            'trade_id': trade.id,
                            'original_description': trade.raw_asset_description,
                            'extracted_ticker': result.ticker,
                            'confidence': float(result.confidence),
                            'method': result.extraction_method
                        })
                    
                    # Track patterns
                    desc_words = trade.raw_asset_description.upper().split()[:3]
                    pattern = ' '.join(desc_words)
                    analysis['asset_description_patterns'][pattern] = analysis['asset_description_patterns'].get(pattern, 0) + 1
                
                # Add examples
                if len(analysis['examples']) < 5:
                    analysis['examples'].append({
                        'trade_id': trade.id,
                        'raw_asset_description': trade.raw_asset_description,
                        'transaction_date': trade.transaction_date.isoformat(),
                        'member_id': trade.member_id
                    })
            
            return analysis
    
    def _analyze_amount_issues(self, limit: int) -> Dict[str, Any]:
        """Analyze records with amount parsing issues."""
        with db_manager.session_scope() as session:
            amount_issue_trades = session.query(CongressionalTrade).filter(
                and_(
                    CongressionalTrade.amount_min.is_(None),
                    CongressionalTrade.amount_max.is_(None),
                    CongressionalTrade.amount_exact.is_(None)
                )
            ).limit(limit).all()
            
            analysis = {
                'sample_count': len(amount_issue_trades),
                'amount_patterns': {},
                'potential_fixes': [],
                'examples': []
            }
            
            # This would require access to original amount data
            # For now, analyze what we have
            for trade in amount_issue_trades:
                if len(analysis['examples']) < 5:
                    analysis['examples'].append({
                        'trade_id': trade.id,
                        'raw_asset_description': trade.raw_asset_description,
                        'transaction_date': trade.transaction_date.isoformat(),
                        'member_id': trade.member_id
                    })
            
            return analysis
    
    def _analyze_owner_issues(self, limit: int) -> Dict[str, Any]:
        """Analyze records with owner normalization issues."""
        with db_manager.session_scope() as session:
            owner_issue_trades = session.query(CongressionalTrade).filter(
                CongressionalTrade.owner.notin_(['C', 'SP', 'JT', 'DC'])
            ).limit(limit).all()
            
            analysis = {
                'sample_count': len(owner_issue_trades),
                'owner_patterns': {},
                'potential_fixes': [],
                'examples': []
            }
            
            for trade in owner_issue_trades:
                # Test owner normalization
                if trade.owner:
                    result = self.data_quality.normalize_owner(trade.owner)
                    
                    if result.normalized_owner:
                        analysis['potential_fixes'].append({
                            'trade_id': trade.id,
                            'original_owner': trade.owner,
                            'normalized_owner': result.normalized_owner.value,
                            'confidence': float(result.confidence),
                            'notes': result.notes
                        })
                    
                    # Track patterns
                    analysis['owner_patterns'][trade.owner] = analysis['owner_patterns'].get(trade.owner, 0) + 1
                
                # Add examples
                if len(analysis['examples']) < 5:
                    analysis['examples'].append({
                        'trade_id': trade.id,
                        'owner': trade.owner,
                        'raw_asset_description': trade.raw_asset_description,
                        'transaction_date': trade.transaction_date.isoformat(),
                        'member_id': trade.member_id
                    })
            
            return analysis
    
    def fix_ticker_extraction(self, limit: int = 1000, dry_run: bool = True) -> Dict[str, Any]:
        """Fix ticker extraction issues."""
        logger.info(f"Fixing ticker extraction issues (limit: {limit}, dry_run: {dry_run})...")
        
        results = {
            'processed': 0,
            'fixed': 0,
            'skipped': 0,
            'errors': 0,
            'fixes': []
        }
        
        with db_manager.session_scope() as session:
            # Get trades with null tickers
            null_ticker_trades = session.query(CongressionalTrade).filter(
                CongressionalTrade.ticker.is_(None)
            ).limit(limit).all()
            
            for trade in null_ticker_trades:
                results['processed'] += 1
                
                try:
                    if not trade.raw_asset_description:
                        results['skipped'] += 1
                        continue
                    
                    # Try to extract ticker
                    result = self.data_quality.extract_ticker(trade.raw_asset_description)
                    
                    if result.ticker and result.confidence > Decimal('0.7'):
                        fix_info = {
                            'trade_id': trade.id,
                            'original_description': trade.raw_asset_description,
                            'extracted_ticker': result.ticker,
                            'confidence': float(result.confidence),
                            'method': result.extraction_method
                        }
                        
                        if not dry_run:
                            # Apply fix
                            trade.ticker = result.ticker
                            trade.asset_name = result.asset_name
                            trade.asset_type = result.asset_type
                            trade.ticker_confidence = result.confidence
                            
                            # Try to resolve security ID
                            security = session.query(Security).filter(
                                Security.ticker == result.ticker.upper()
                            ).first()
                            
                            if security:
                                trade.security_id = security.id
                        
                        results['fixed'] += 1
                        results['fixes'].append(fix_info)
                    else:
                        results['skipped'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing trade {trade.id}: {e}")
                    results['errors'] += 1
            
            if not dry_run:
                session.commit()
                logger.info(f"Committed {results['fixed']} ticker fixes")
        
        return results
    
    def fix_amount_parsing(self, limit: int = 1000, dry_run: bool = True) -> Dict[str, Any]:
        """Fix amount parsing issues."""
        logger.info(f"Fixing amount parsing issues (limit: {limit}, dry_run: {dry_run})...")
        
        results = {
            'processed': 0,
            'fixed': 0,
            'skipped': 0,
            'errors': 0,
            'fixes': []
        }
        
        # Note: This would require access to original amount data
        # For now, we'll focus on fixing existing amount fields
        
        with db_manager.session_scope() as session:
            # Get trades with missing amounts
            missing_amount_trades = session.query(CongressionalTrade).filter(
                and_(
                    CongressionalTrade.amount_min.is_(None),
                    CongressionalTrade.amount_max.is_(None),
                    CongressionalTrade.amount_exact.is_(None)
                )
            ).limit(limit).all()
            
            for trade in missing_amount_trades:
                results['processed'] += 1
                results['skipped'] += 1  # Skip for now without original data
        
        return results
    
    def fix_owner_normalization(self, limit: int = 1000, dry_run: bool = True) -> Dict[str, Any]:
        """Fix owner normalization issues."""
        logger.info(f"Fixing owner normalization issues (limit: {limit}, dry_run: {dry_run})...")
        
        results = {
            'processed': 0,
            'fixed': 0,
            'skipped': 0,
            'errors': 0,
            'fixes': []
        }
        
        with db_manager.session_scope() as session:
            # Get trades with invalid owners
            invalid_owner_trades = session.query(CongressionalTrade).filter(
                CongressionalTrade.owner.notin_(['C', 'SP', 'JT', 'DC'])
            ).limit(limit).all()
            
            for trade in invalid_owner_trades:
                results['processed'] += 1
                
                try:
                    if not trade.owner:
                        results['skipped'] += 1
                        continue
                    
                    # Try to normalize owner
                    result = self.data_quality.normalize_owner(trade.owner)
                    
                    if result.normalized_owner and result.confidence > Decimal('0.6'):
                        fix_info = {
                            'trade_id': trade.id,
                            'original_owner': trade.owner,
                            'normalized_owner': result.normalized_owner.value,
                            'confidence': float(result.confidence),
                            'notes': result.notes
                        }
                        
                        if not dry_run:
                            # Apply fix
                            trade.owner = result.normalized_owner.value
                        
                        results['fixed'] += 1
                        results['fixes'].append(fix_info)
                    else:
                        results['skipped'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing trade {trade.id}: {e}")
                    results['errors'] += 1
            
            if not dry_run:
                session.commit()
                logger.info(f"Committed {results['fixed']} owner fixes")
        
        return results
    
    def remove_duplicates(self, dry_run: bool = True) -> Dict[str, Any]:
        """Remove duplicate trades."""
        logger.info(f"Removing duplicate trades (dry_run: {dry_run})...")
        
        results = {
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'errors': 0,
            'duplicate_groups': []
        }
        
        with db_manager.session_scope() as session:
            # Find duplicates based on key fields
            duplicate_query = text("""
                SELECT doc_id, member_id, transaction_date, raw_asset_description, 
                       COUNT(*) as count, MIN(id) as keep_id, 
                       ARRAY_AGG(id ORDER BY id) as all_ids
                FROM congressional_trades
                GROUP BY doc_id, member_id, transaction_date, raw_asset_description
                HAVING COUNT(*) > 1
            """)
            
            duplicate_groups = session.execute(duplicate_query).fetchall()
            
            for group in duplicate_groups:
                results['duplicates_found'] += group.count - 1
                
                duplicate_info = {
                    'doc_id': group.doc_id,
                    'member_id': group.member_id,
                    'transaction_date': group.transaction_date.isoformat(),
                    'count': group.count,
                    'keep_id': group.keep_id,
                    'remove_ids': group.all_ids[1:]  # Remove all but the first
                }
                
                results['duplicate_groups'].append(duplicate_info)
                
                if not dry_run:
                    try:
                        # Remove duplicates (keep the first one)
                        session.query(CongressionalTrade).filter(
                            CongressionalTrade.id.in_(group.all_ids[1:])
                        ).delete(synchronize_session=False)
                        
                        results['duplicates_removed'] += group.count - 1
                        
                    except Exception as e:
                        logger.error(f"Error removing duplicates for group {group.doc_id}: {e}")
                        results['errors'] += 1
            
            if not dry_run and results['duplicates_removed'] > 0:
                session.commit()
                logger.info(f"Removed {results['duplicates_removed']} duplicate trades")
        
        return results
    
    def test_import_pipeline(self, test_file: str, sample_size: int = 100) -> Dict[str, Any]:
        """Test the import pipeline with a sample file."""
        logger.info(f"Testing import pipeline with {test_file} (sample_size: {sample_size})...")
        
        if not os.path.exists(test_file):
            return {'error': f'Test file not found: {test_file}'}
        
        # Create temporary test ingestion
        test_ingestion = CongressionalDataIngestion(batch_size=10)
        
        try:
            # Process a small sample for testing
            with open(test_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                sample_rows = []
                
                for i, row in enumerate(reader):
                    if i >= sample_size:
                        break
                    sample_rows.append(row)
            
            # Create temporary CSV for testing
            temp_file = f"/tmp/congressional_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(temp_file, 'w', newline='', encoding='utf-8') as outfile:
                if sample_rows:
                    writer = csv.DictWriter(outfile, fieldnames=sample_rows[0].keys())
                    writer.writeheader()
                    writer.writerows(sample_rows)
            
            # Test the pipeline
            report = test_ingestion.process_csv_file(temp_file)
            
            # Clean up
            os.remove(temp_file)
            
            return {
                'success': True,
                'sample_size': len(sample_rows),
                'report': asdict(report) if hasattr(report, '__dict__') else report,
                'test_file': test_file
            }
            
        except Exception as e:
            logger.error(f"Error testing import pipeline: {e}")
            return {'error': str(e)}
    
    def export_data_quality_report(self, output_file: str):
        """Export comprehensive data quality report."""
        logger.info(f"Exporting data quality report to {output_file}...")
        
        # Check database state
        db_state = self.check_database_state()
        
        # Analyze problematic records
        analysis = self.analyze_problematic_records(limit=500)
        
        # Generate report
        report = {
            'generated_at': datetime.now().isoformat(),
            'database_state': asdict(db_state),
            'problematic_records_analysis': analysis,
            'summary': {
                'total_records': db_state.total_trades,
                'quality_metrics': {
                    'ticker_extraction_rate': db_state.ticker_extraction_rate,
                    'amount_parsing_rate': db_state.amount_parsing_rate,
                    'owner_normalization_rate': db_state.owner_normalization_rate,
                },
                'problem_counts': {
                    'null_tickers': db_state.null_ticker_count,
                    'null_amounts': db_state.null_amount_count,
                    'invalid_owners': db_state.invalid_owner_count,
                    'duplicates': db_state.duplicate_count,
                }
            }
        }
        
        # Export to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Data quality report exported to {output_file}")
        return report
    
    def cleanup_database(self, dry_run: bool = True) -> Dict[str, Any]:
        """Comprehensive database cleanup."""
        logger.info(f"Starting database cleanup (dry_run: {dry_run})...")
        
        results = {
            'ticker_fixes': self.fix_ticker_extraction(limit=2000, dry_run=dry_run),
            'owner_fixes': self.fix_owner_normalization(limit=2000, dry_run=dry_run),
            'duplicate_removal': self.remove_duplicates(dry_run=dry_run)
        }
        
        # Summary
        results['summary'] = {
            'total_ticker_fixes': results['ticker_fixes']['fixed'],
            'total_owner_fixes': results['owner_fixes']['fixed'],
            'total_duplicates_removed': results['duplicate_removal']['duplicates_removed'],
            'total_errors': (
                results['ticker_fixes']['errors'] +
                results['owner_fixes']['errors'] +
                results['duplicate_removal']['errors']
            )
        }
        
        return results


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description='Congressional import recovery and testing')
    parser.add_argument('command', choices=[
        'check', 'analyze', 'fix-tickers', 'fix-owners', 'remove-duplicates',
        'test-import', 'export-report', 'cleanup'
    ], help='Command to execute')
    
    # Optional arguments
    parser.add_argument('--limit', type=int, default=1000, help='Limit for processing')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no changes)')
    parser.add_argument('--file', help='Input file for testing')
    parser.add_argument('--output', help='Output file for reports')
    parser.add_argument('--sample-size', type=int, default=100, help='Sample size for testing')
    
    args = parser.parse_args()
    
    # Initialize recovery tool
    recovery = CongressionalImportRecovery()
    
    try:
        if args.command == 'check':
            print("=== Database State Check ===")
            state = recovery.check_database_state()
            print(f"Total members: {state.total_members}")
            print(f"Total trades: {state.total_trades}")
            print(f"Ticker extraction rate: {state.ticker_extraction_rate:.1f}%")
            print(f"Amount parsing rate: {state.amount_parsing_rate:.1f}%")
            print(f"Owner normalization rate: {state.owner_normalization_rate:.1f}%")
            print(f"NULL tickers: {state.null_ticker_count}")
            print(f"NULL amounts: {state.null_amount_count}")
            print(f"Invalid owners: {state.invalid_owner_count}")
            print(f"Duplicates: {state.duplicate_count}")
            
        elif args.command == 'analyze':
            print("=== Problematic Records Analysis ===")
            analysis = recovery.analyze_problematic_records(limit=args.limit)
            print(f"Null ticker samples: {analysis['null_ticker_analysis']['sample_count']}")
            print(f"Amount parsing samples: {analysis['amount_parsing_analysis']['sample_count']}")
            print(f"Owner normalization samples: {analysis['owner_normalization_analysis']['sample_count']}")
            
            if analysis['recommendations']:
                print("\n=== Recommendations ===")
                for rec in analysis['recommendations']:
                    print(f"- {rec}")
                    
        elif args.command == 'fix-tickers':
            print("=== Fixing Ticker Extraction ===")
            results = recovery.fix_ticker_extraction(limit=args.limit, dry_run=args.dry_run)
            print(f"Processed: {results['processed']}")
            print(f"Fixed: {results['fixed']}")
            print(f"Skipped: {results['skipped']}")
            print(f"Errors: {results['errors']}")
            
        elif args.command == 'fix-owners':
            print("=== Fixing Owner Normalization ===")
            results = recovery.fix_owner_normalization(limit=args.limit, dry_run=args.dry_run)
            print(f"Processed: {results['processed']}")
            print(f"Fixed: {results['fixed']}")
            print(f"Skipped: {results['skipped']}")
            print(f"Errors: {results['errors']}")
            
        elif args.command == 'remove-duplicates':
            print("=== Removing Duplicates ===")
            results = recovery.remove_duplicates(dry_run=args.dry_run)
            print(f"Duplicates found: {results['duplicates_found']}")
            print(f"Duplicates removed: {results['duplicates_removed']}")
            print(f"Errors: {results['errors']}")
            
        elif args.command == 'test-import':
            if not args.file:
                print("Error: --file argument required for test-import")
                return 1
            
            print("=== Testing Import Pipeline ===")
            results = recovery.test_import_pipeline(args.file, args.sample_size)
            
            if 'error' in results:
                print(f"Error: {results['error']}")
                return 1
            
            print(f"Sample size: {results['sample_size']}")
            print(f"Test successful: {results['success']}")
            
        elif args.command == 'export-report':
            output_file = args.output or f'congressional_quality_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            print(f"=== Exporting Data Quality Report to {output_file} ===")
            recovery.export_data_quality_report(output_file)
            print(f"Report exported successfully")
            
        elif args.command == 'cleanup':
            print("=== Database Cleanup ===")
            results = recovery.cleanup_database(dry_run=args.dry_run)
            print(f"Ticker fixes: {results['summary']['total_ticker_fixes']}")
            print(f"Owner fixes: {results['summary']['total_owner_fixes']}")
            print(f"Duplicates removed: {results['summary']['total_duplicates_removed']}")
            print(f"Total errors: {results['summary']['total_errors']}")
            
            if args.dry_run:
                print("\n(DRY RUN - No changes made)")
                
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())