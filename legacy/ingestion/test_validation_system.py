#!/usr/bin/env python3
"""
Test script for the improved congressional data parsing and validation system.

This script tests the entire pipeline:
1. PDF parsing improvements
2. Data validation
3. Database ingestion
4. Quality reporting

Usage:
    python scripts/test_validation_system.py --sample-size 100
    python scripts/test_validation_system.py --year 2025 --full-test
"""

import asyncio
import sys
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import random
import logging

# Add src directory to path
src_path = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(src_path))

from import_congressional_data import CongressionalDataValidator

logger = logging.getLogger(__name__)


def test_sample_records(csv_file: str, sample_size: int = 100) -> Dict[str, Any]:
    """Test validation on a sample of records from a CSV file"""
    logger.info(f"Testing validation on {sample_size} sample records from {csv_file}")
    
    try:
        # Load CSV file
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded {len(df)} total records from {csv_file}")
        
        # Sample records
        if len(df) > sample_size:
            sample_df = df.sample(n=sample_size, random_state=42)
        else:
            sample_df = df
            
        logger.info(f"Testing with {len(sample_df)} records")
        
        # Initialize validator
        validator = CongressionalDataValidator()
        
        # Validate each record
        results = {
            'valid_records': [],
            'invalid_records': [],
            'cleaned_records': [],
            'validation_details': []
        }
        
        for idx, row in sample_df.iterrows():
            record = row.to_dict()
            validation_result = validator.validate_record(record)
            
            result_detail = {
                'original_record': record,
                'validation_result': validation_result,
                'row_index': idx
            }
            
            results['validation_details'].append(result_detail)
            
            if validation_result.is_valid:
                results['valid_records'].append(record)
                if validation_result.cleaned_data != record:
                    results['cleaned_records'].append({
                        'original': record,
                        'cleaned': validation_result.cleaned_data
                    })
            else:
                results['invalid_records'].append({
                    'record': record,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings
                })
        
        # Generate summary
        summary = {
            'total_tested': len(sample_df),
            'valid_count': len(results['valid_records']),
            'invalid_count': len(results['invalid_records']),
            'cleaned_count': len(results['cleaned_records']),
            'success_rate': (len(results['valid_records']) / len(sample_df)) * 100,
            'validation_report': validator.get_validation_report(),
            'validation_stats': validator.validation_stats
        }
        
        return {
            'summary': summary,
            'results': results,
            'validator': validator
        }
        
    except Exception as e:
        logger.error(f"Error testing sample records: {e}")
        raise


def analyze_problematic_records(test_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the most common validation issues"""
    logger.info("Analyzing problematic records...")
    
    invalid_records = test_results['results']['invalid_records']
    
    # Count error types
    error_counts = {}
    warning_counts = {}
    
    for invalid_record in invalid_records:
        for error in invalid_record['errors']:
            error_type = error.split(':')[0]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        for warning in invalid_record['warnings']:
            warning_type = warning.split(':')[0]
            warning_counts[warning_type] = warning_counts.get(warning_type, 0) + 1
    
    # Find most problematic fields
    problematic_patterns = {}
    
    for invalid_record in invalid_records:
        record = invalid_record['record']
        
        # Check each field for common issues
        for field, value in record.items():
            if pd.isna(value) or str(value).strip() == '':
                pattern = f"{field}_missing"
                problematic_patterns[pattern] = problematic_patterns.get(pattern, 0) + 1
            elif field == 'Transaction Type' and str(value) not in ['P', 'S', 'E', 'S (partial)']:
                pattern = f"invalid_transaction_type_{value}"
                problematic_patterns[pattern] = problematic_patterns.get(pattern, 0) + 1
            elif field in ['Transaction Date', 'Notification Date']:
                if not pd.isna(value) and not str(value).strip() == '':
                    # Check for common date issues
                    value_str = str(value).strip()
                    if len(value_str.split('/')) != 3:
                        pattern = f"invalid_date_format_{field}"
                        problematic_patterns[pattern] = problematic_patterns.get(pattern, 0) + 1
    
    return {
        'error_counts': error_counts,
        'warning_counts': warning_counts,
        'problematic_patterns': problematic_patterns,
        'most_common_errors': sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        'most_common_patterns': sorted(problematic_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
    }


def compare_old_vs_new_data(old_csv: str, new_csv: str) -> Dict[str, Any]:
    """Compare data quality between old and new parsing results"""
    logger.info(f"Comparing data quality: {old_csv} vs {new_csv}")
    
    try:
        old_df = pd.read_csv(old_csv)
        new_df = pd.read_csv(new_csv)
        
        # Test both with validator
        validator_old = CongressionalDataValidator()
        validator_new = CongressionalDataValidator()
        
        # Validate old data
        for _, row in old_df.iterrows():
            validator_old.validate_record(row.to_dict())
        
        # Validate new data
        for _, row in new_df.iterrows():
            validator_new.validate_record(row.to_dict())
        
        # Compare statistics
        old_stats = validator_old.validation_stats
        new_stats = validator_new.validation_stats
        
        comparison = {
            'record_count_change': len(new_df) - len(old_df),
            'record_count_improvement': ((len(new_df) - len(old_df)) / len(old_df)) * 100 if len(old_df) > 0 else 0,
            'old_validation_rate': (old_stats['valid_records'] / old_stats['total_records']) * 100 if old_stats['total_records'] > 0 else 0,
            'new_validation_rate': (new_stats['valid_records'] / new_stats['total_records']) * 100 if new_stats['total_records'] > 0 else 0,
            'old_confidence_avg': sum(old_stats['confidence_distribution']) / len(old_stats['confidence_distribution']) if old_stats['confidence_distribution'] else 0,
            'new_confidence_avg': sum(new_stats['confidence_distribution']) / len(new_stats['confidence_distribution']) if new_stats['confidence_distribution'] else 0,
            'old_stats': old_stats,
            'new_stats': new_stats
        }
        
        comparison['validation_improvement'] = comparison['new_validation_rate'] - comparison['old_validation_rate']
        comparison['confidence_improvement'] = comparison['new_confidence_avg'] - comparison['old_confidence_avg']
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error comparing old vs new data: {e}")
        raise


def generate_validation_report(test_results: Dict[str, Any], analysis: Dict[str, Any], 
                             comparison: Dict[str, Any] = None) -> str:
    """Generate a comprehensive validation report"""
    
    summary = test_results['summary']
    
    # Calculate average confidence score safely
    confidence_dist = summary['validation_stats']['confidence_distribution']
    avg_confidence = sum(confidence_dist) / len(confidence_dist) if confidence_dist else 0
    high_confidence_count = len([s for s in confidence_dist if s > 0.8]) if confidence_dist else 0
    low_confidence_count = len([s for s in confidence_dist if s < 0.5]) if confidence_dist else 0
    
    report = f"""
Congressional Data Validation Test Report
========================================

Test Summary:
- Total Records Tested: {summary['total_tested']:,}
- Valid Records: {summary['valid_count']:,} ({summary['success_rate']:.1f}%)
- Invalid Records: {summary['invalid_count']:,}
- Records Requiring Cleaning: {summary['cleaned_count']:,}

Validation Quality:
- Average Confidence Score: {avg_confidence:.3f}
- High Confidence Records (>0.8): {high_confidence_count:,}
- Low Confidence Records (<0.5): {low_confidence_count:,}

Most Common Validation Issues:
"""
    
    for error_type, count in analysis['most_common_errors']:
        percentage = (count / summary['total_tested']) * 100
        report += f"- {error_type}: {count} occurrences ({percentage:.1f}%)\n"
    
    report += "\nMost Common Data Patterns Requiring Attention:\n"
    for pattern, count in analysis['most_common_patterns']:
        percentage = (count / summary['total_tested']) * 100
        report += f"- {pattern}: {count} occurrences ({percentage:.1f}%)\n"
    
    if comparison:
        report += f"""

Old vs New Data Comparison:
- Record Count Improvement: +{comparison['record_count_change']:,} records ({comparison['record_count_improvement']:.1f}% increase)
- Validation Rate Improvement: {comparison['validation_improvement']:.1f} percentage points
- Confidence Score Improvement: {comparison['confidence_improvement']:.3f} points
- Old Validation Rate: {comparison['old_validation_rate']:.1f}%
- New Validation Rate: {comparison['new_validation_rate']:.1f}%
"""
    
    report += f"""

Recommendations:
1. Focus on fixing the top 3 error types to improve data quality
2. {"Implement additional cleaning for date formats" if any("date" in pattern.lower() for pattern, _ in analysis['most_common_patterns'][:3]) else "Continue monitoring data quality"}
3. {"Review asset name parsing for field contamination" if any("asset" in pattern.lower() for pattern, _ in analysis['most_common_patterns'][:3]) else "Asset parsing is performing well"}
4. Set up automated monitoring for validation rates below 95%

Overall Assessment: {"EXCELLENT - Parsing improvements are working well" if summary['success_rate'] >= 95 else "GOOD - Some issues remain but significant improvement" if summary['success_rate'] >= 85 else "NEEDS ATTENTION - Consider additional parsing improvements"}
"""
    
    return report


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Test congressional data validation system'
    )
    
    parser.add_argument(
        '--csv-file',
        type=str,
        help='Specific CSV file to test'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Test specific year (will look for YEARFD.csv)'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=100,
        help='Number of records to sample for testing (default: 100)'
    )
    parser.add_argument(
        '--full-test',
        action='store_true',
        help='Test all records instead of sampling'
    )
    parser.add_argument(
        '--compare-old',
        action='store_true',
        help='Compare with old parsing results (looks for *_old.csv files)'
    )
    parser.add_argument(
        '--output-report',
        type=str,
        help='Save detailed report to file'
    )
    
    args = parser.parse_args()
    
    try:
        # Determine which file to test
        if args.csv_file:
            csv_file = args.csv_file
        elif args.year:
            csv_file = f"data/congress/csv/{args.year}FD.csv"
        else:
            # Default to most recent file
            csv_dir = Path("data/congress/csv")
            csv_files = list(csv_dir.glob("*FD.csv"))
            if not csv_files:
                logger.error("No CSV files found in data/congress/csv/")
                return 1
            csv_file = max(csv_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Using most recent file: {csv_file}")
        
        # Ensure file exists
        if not Path(csv_file).exists():
            logger.error(f"CSV file not found: {csv_file}")
            return 1
        
        # Determine sample size
        sample_size = None if args.full_test else args.sample_size
        
        # Run validation test
        print("🔍 Testing Congressional Data Validation System")
        print("=" * 50)
        
        test_results = test_sample_records(csv_file, sample_size)
        analysis = analyze_problematic_records(test_results)
        
        # Compare with old data if requested
        comparison = None
        if args.compare_old:
            old_csv_file = csv_file.replace('.csv', '_old.csv')
            if Path(old_csv_file).exists():
                comparison = compare_old_vs_new_data(old_csv_file, csv_file)
                logger.info("Comparison with old data completed")
            else:
                logger.warning(f"Old CSV file not found: {old_csv_file}")
        
        # Generate and display report
        report = generate_validation_report(test_results, analysis, comparison)
        print(report)
        
        # Save report if requested
        if args.output_report:
            with open(args.output_report, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {args.output_report}")
        
        # Print summary statistics
        summary = test_results['summary']
        
        print("\n" + "="*50)
        print("🎯 VALIDATION TEST RESULTS")
        print("="*50)
        print(f"✅ Success Rate: {summary['success_rate']:.1f}%")
        print(f"📊 Records Tested: {summary['total_tested']:,}")
        print(f"🔧 Records Cleaned: {summary['cleaned_count']:,}")
        print(f"❌ Records Rejected: {summary['invalid_count']:,}")
        
        if comparison:
            print(f"\n📈 IMPROVEMENT METRICS:")
            print(f"Records Added: +{comparison['record_count_change']:,}")
            print(f"Validation Rate: +{comparison['validation_improvement']:.1f}%")
            print(f"Confidence Score: +{comparison['confidence_improvement']:.3f}")
        
        # Return appropriate exit code
        return 0 if summary['success_rate'] >= 85 else 1
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 