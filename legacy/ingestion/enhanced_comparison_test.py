#!/usr/bin/env python3
"""
Enhanced comparison test including the new enhanced parser that combines
original logic with validation framework.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import time
from typing import Dict, List, Tuple

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent))

from original_pdf_parser import OriginalPDFParser
from pdf_parsing_improvements import ImprovedPDFParser, TradeRecord
from enhanced_pdf_parser import EnhancedPDFParser, EnhancedTradeRecord
from fetch_stock_data import get_tickers, get_tickers_company_dict

TEST_PDF_SIZE = 100

def setup_all_parsers():
    """Set up all three parsers with the same configuration"""
    
    print("Setting up all parsers...")
    
    # Get tickers and company data
    tickers = get_tickers()
    tickers_company = get_tickers_company_dict()
    
    # Asset type dictionary (from your original code)
    asset_dict = {
        "4K": "401K and Other Non-Federal Retirement Accounts",
        "5C": "529 College Savings Plan",
        "5F": "529 Portfolio",
        "5P": "529 Prepaid Tuition Plan",
        "AB": "Asset-Backed Securities",
        "BA": "Bank Accounts, Money Market Accounts and CDs",
        "BK": "Brokerage Accounts",
        "CO": "Collectibles",
        "CS": "Corporate Securities (Bonds and Notes)",
        "CT": "Cryptocurrency",
        "DB": "Defined Benefit Pension",
        "DO": "Debts Owed to the Filer",
        "DS": "Delaware Statutory Trust",
        "EF": "Exchange Traded Funds (ETF)",
        "EQ": "Excepted/Qualified Blind Trust",
        "ET": "Exchange Traded Notes",
        "FA": "Farms",
        "FE": "Foreign Exchange Position (Currency)",
        "FN": "Fixed Annuity",
        "FU": "Futures",
        "GS": "Government Securities and Agency Debt",
        "HE": "Hedge Funds & Private Equity Funds (EIF)",
        "HN": "Hedge Funds & Private Equity Funds (non-EIF)",
        "IC": "Investment Club",
        "IH": "IRA (Held in Cash)",
        "IP": "Intellectual Property & Royalties",
        "IR": "IRA",
        "MA": "Managed Accounts (e.g., SMA and UMA)",
        "MF": "Mutual Funds",
        "MO": "Mineral/Oil/Solar Energy Rights",
        "OI": "Ownership Interest (Holding Investments)",
        "OL": "Ownership Interest (Engaged in a Trade or Business)",
        "OP": "Options",
        "OT": "Other",
        "PE": "Pensions",
        "PM": "Precious Metals",
        "PS": "Stock (Not Publicly Traded)",
        "RE": "Real Estate Invest. Trust (REIT)",
        "RP": "Real Property",
        "RS": "Restricted Stock Units (RSUs)",
        "SA": "Stock Appreciation Right",
        "ST": "Stocks (including ADRs)",
        "TR": "Trust",
        "VA": "Variable Annuity",
        "VI": "Variable Insurance",
        "WU": "Whole/Universal Insurance"
    }
    
    # Initialize all parsers
    original_parser = OriginalPDFParser(
        tickers=set(tickers),
        asset_dict=asset_dict,
        tickers_company=tickers_company
    )
    
    improved_parser = ImprovedPDFParser(
        tickers=set(tickers),
        asset_dict=asset_dict,
        tickers_company=tickers_company
    )
    
    enhanced_parser = EnhancedPDFParser(
        tickers=set(tickers),
        asset_dict=asset_dict,
        tickers_company=tickers_company
    )
    
    return original_parser, improved_parser, enhanced_parser

def find_test_pdfs():
    """Find PDF files for testing"""
    
    root_path = Path(__file__).resolve().parents[2]
    pdf_path = root_path / 'data' / 'congress' / 'pdf'
    pdf_list_file = pdf_path / 'pdf_list.txt'
    
    # Read the first 30 PDF filenames from the list
    sample_pdfs = []
    with open(pdf_list_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= TEST_PDF_SIZE:
                break
            sample_pdfs.append(line.strip())
    
    found_pdfs = []
    for pdf_name in sample_pdfs:
        pdf_file = pdf_path / pdf_name
        if pdf_file.exists():
            found_pdfs.append(str(pdf_file))
        else:
            print(f"Warning: {pdf_name} not found at {pdf_file}")
    
    return found_pdfs

def test_single_pdf_enhanced_comparison(original_parser, improved_parser, enhanced_parser, pdf_path: str) -> Dict:
    """Test all three parsers on a single PDF and compare results"""
    
    doc_id = Path(pdf_path).stem
    member = "TestMember"
    
    print(f"\n=== Testing {doc_id} ===")
    
    results = {
        'doc_id': doc_id,
        'original_records': 0,
        'improved_records': 0,
        'enhanced_records': 0,
        'original_time': 0,
        'improved_time': 0,
        'enhanced_time': 0,
        'original_df': None,
        'improved_records_list': [],
        'enhanced_records_list': [],
        'common_original_enhanced': 0,
        'unique_to_original': 0,
        'unique_to_enhanced': 0,
        'enhanced_edge_cases': []
    }
    
    # Test original parser
    try:
        start_time = time.time()
        original_df = original_parser.parse_pdf_original(pdf_path, doc_id, member)
        original_time = time.time() - start_time
        
        results['original_records'] = len(original_df) if not original_df.empty else 0
        results['original_time'] = original_time
        results['original_df'] = original_df
        
        print(f"  Original parser: {results['original_records']} records in {original_time:.3f}s")
        
    except Exception as e:
        print(f"  Original parser failed: {e}")
    
    # Test improved parser
    try:
        start_time = time.time()
        improved_records = improved_parser.parse_pdf_improved(pdf_path, doc_id, member)
        improved_time = time.time() - start_time
        
        results['improved_records'] = len(improved_records)
        results['improved_time'] = improved_time
        results['improved_records_list'] = improved_records
        
        print(f"  Improved parser: {results['improved_records']} records in {improved_time:.3f}s")
        
        # Calculate confidence scores
        if improved_records:
            confidence_scores = [r.confidence_score for r in improved_records]
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            print(f"  Improved average confidence: {avg_confidence:.2f}")
            
            # Count validation issues
            issues = sum(1 for r in improved_records if r.parsing_notes)
            print(f"  Improved records with issues: {issues}/{len(improved_records)}")
        
    except Exception as e:
        print(f"  Improved parser failed: {e}")
    
    # Test enhanced parser
    try:
        start_time = time.time()
        enhanced_records = enhanced_parser.parse_pdf_enhanced(pdf_path, doc_id, member)
        enhanced_time = time.time() - start_time
        
        results['enhanced_records'] = len(enhanced_records)
        results['enhanced_time'] = enhanced_time
        results['enhanced_records_list'] = enhanced_records
        
        print(f"  Enhanced parser: {results['enhanced_records']} records in {enhanced_time:.3f}s")
        
        # Calculate confidence scores
        if enhanced_records:
            confidence_scores = [r.confidence_score for r in enhanced_records]
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            print(f"  Enhanced average confidence: {avg_confidence:.2f}")
            
            # Count validation issues
            issues = sum(1 for r in enhanced_records if r.parsing_notes)
            print(f"  Enhanced records with issues: {issues}/{len(enhanced_records)}")
            
            # Collect edge cases
            all_edge_cases = []
            for record in enhanced_records:
                all_edge_cases.extend(record.edge_cases_applied)
            results['enhanced_edge_cases'] = list(set(all_edge_cases))
            print(f"  Enhanced edge cases applied: {results['enhanced_edge_cases']}")
        
    except Exception as e:
        print(f"  Enhanced parser failed: {e}")
    
    # Compare results if both original and enhanced worked
    if results['original_records'] > 0 and results['enhanced_records'] > 0:
        comparison = compare_parsing_results_enhanced(original_df, enhanced_records)
        results.update(comparison)
        
        print(f"  Comparison: {results['common_original_enhanced']} common, "
              f"{results['unique_to_original']} unique to original, "
              f"{results['unique_to_enhanced']} unique to enhanced")
    
    return results

def compare_parsing_results_enhanced(original_df: pd.DataFrame, enhanced_records: List[EnhancedTradeRecord]) -> Dict:
    """Compare results from original and enhanced parsers"""
    
    # Convert enhanced records to DataFrame for comparison
    enhanced_data = []
    for record in enhanced_records:
        enhanced_data.append({
            'Member': record.member,
            'DocID': record.doc_id,
            'Owner': record.owner,
            'Asset': record.asset,
            'Ticker': record.ticker,
            'Transaction Type': record.transaction_type,
            'Transaction Date': record.transaction_date,
            'Notification Date': record.notification_date,
            'Amount': record.amount,
            'Filing Status': record.filing_status,
            'Description': record.description
        })
    
    enhanced_df = pd.DataFrame(enhanced_data)
    
    # Simple comparison based on key fields
    common_count = 0
    unique_to_original = 0
    unique_to_enhanced = 0
    
    # For each original record, check if there's a matching enhanced record
    for _, orig_row in original_df.iterrows():
        matching = enhanced_df[
            (enhanced_df['Owner'] == orig_row['Owner']) &
            (enhanced_df['Asset'] == orig_row['Asset']) &
            (enhanced_df['Transaction Type'] == orig_row['Transaction Type']) &
            (enhanced_df['Transaction Date'] == orig_row['Transaction Date'])
        ]
        
        if len(matching) > 0:
            common_count += 1
        else:
            unique_to_original += 1
    
    # For each enhanced record, check if there's a matching original record
    for _, enh_row in enhanced_df.iterrows():
        matching = original_df[
            (original_df['Owner'] == enh_row['Owner']) &
            (original_df['Asset'] == enh_row['Asset']) &
            (original_df['Transaction Type'] == enh_row['Transaction Type']) &
            (original_df['Transaction Date'] == enh_row['Transaction Date'])
        ]
        
        if len(matching) == 0:
            unique_to_enhanced += 1
    
    return {
        'common_original_enhanced': common_count,
        'unique_to_original': unique_to_original,
        'unique_to_enhanced': unique_to_enhanced
    }

def run_enhanced_comparison():
    """Run comprehensive comparison between all three parsers"""
    
    print("=== Enhanced PDF Parsing Comparison Test ===\n")
    
    # Setup parsers
    original_parser, improved_parser, enhanced_parser = setup_all_parsers()
    
    # Find test PDFs
    pdf_files = find_test_pdfs()
    
    if not pdf_files:
        print("No test PDF files found.")
        return
    
    print(f"Found {len(pdf_files)} test PDF files")
    
    # Test each PDF
    all_results = []
    total_original_records = 0
    total_improved_records = 0
    total_enhanced_records = 0
    total_original_time = 0
    total_improved_time = 0
    total_enhanced_time = 0
    
    for pdf_file in pdf_files:
        results = test_single_pdf_enhanced_comparison(original_parser, improved_parser, enhanced_parser, pdf_file)
        all_results.append(results)
        
        total_original_records += results['original_records']
        total_improved_records += results['improved_records']
        total_enhanced_records += results['enhanced_records']
        total_original_time += results['original_time']
        total_improved_time += results['improved_time']
        total_enhanced_time += results['enhanced_time']
    
    # Generate summary report
    print(f"\n=== Summary Report ===")
    print(f"Total PDFs tested: {len(pdf_files)}")
    print(f"Original parser: {total_original_records} total records in {total_original_time:.3f}s")
    print(f"Improved parser: {total_improved_records} total records in {total_improved_time:.3f}s")
    print(f"Enhanced parser: {total_enhanced_records} total records in {total_enhanced_time:.3f}s")
    
    if total_original_records > 0:
        print(f"Original parser average: {total_original_records/len(pdf_files):.1f} records per PDF")
    if total_improved_records > 0:
        print(f"Improved parser average: {total_improved_records/len(pdf_files):.1f} records per PDF")
    if total_enhanced_records > 0:
        print(f"Enhanced parser average: {total_enhanced_records/len(pdf_files):.1f} records per PDF")
    
    # Save detailed results
    save_enhanced_comparison_results(all_results)
    
    return all_results

def save_enhanced_comparison_results(results: List[Dict]):
    """Save detailed enhanced comparison results"""
    
    root_path = Path(__file__).resolve().parents[2]
    output_path = root_path / 'data' / 'congress' / 'csv'
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save summary results
    summary_data = []
    for result in results:
        summary_data.append({
            'DocID': result['doc_id'],
            'Original_Records': result['original_records'],
            'Improved_Records': result['improved_records'],
            'Enhanced_Records': result['enhanced_records'],
            'Original_Time_s': result['original_time'],
            'Improved_Time_s': result['improved_time'],
            'Enhanced_Time_s': result['enhanced_time'],
            'Common_Original_Enhanced': result.get('common_original_enhanced', 0),
            'Unique_to_Original': result.get('unique_to_original', 0),
            'Unique_to_Enhanced': result.get('unique_to_enhanced', 0),
            'Enhanced_Edge_Cases': '; '.join(result.get('enhanced_edge_cases', []))
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_path = output_path / 'enhanced_parsing_comparison_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"\nEnhanced comparison summary saved to: {summary_path}")
    
    # Save detailed results for each parser
    all_original_records = []
    all_improved_records = []
    all_enhanced_records = []
    
    for result in results:
        if result['original_df'] is not None and not result['original_df'].empty:
            all_original_records.append(result['original_df'])
        
        if result['improved_records_list']:
            improved_data = []
            for record in result['improved_records_list']:
                improved_data.append({
                    'Member': record.member,
                    'DocID': record.doc_id,
                    'Owner': record.owner,
                    'Asset': record.asset,
                    'Ticker': record.ticker,
                    'Transaction Type': record.transaction_type,
                    'Transaction Date': record.transaction_date,
                    'Notification Date': record.notification_date,
                    'Amount': record.amount,
                    'Filing Status': record.filing_status,
                    'Description': record.description,
                    'Confidence Score': record.confidence_score,
                    'Parsing Notes': '; '.join(record.parsing_notes) if record.parsing_notes else ''
                })
            all_improved_records.append(pd.DataFrame(improved_data))
        
        if result['enhanced_records_list']:
            enhanced_data = []
            for record in result['enhanced_records_list']:
                enhanced_data.append({
                    'Member': record.member,
                    'DocID': record.doc_id,
                    'Owner': record.owner,
                    'Asset': record.asset,
                    'Ticker': record.ticker,
                    'Transaction Type': record.transaction_type,
                    'Transaction Date': record.transaction_date,
                    'Notification Date': record.notification_date,
                    'Amount': record.amount,
                    'Filing Status': record.filing_status,
                    'Description': record.description,
                    'Confidence Score': record.confidence_score,
                    'Parsing Notes': '; '.join(record.parsing_notes) if record.parsing_notes else '',
                    'Parsing Strategy': record.parsing_strategy,
                    'Edge Cases Applied': '; '.join(record.edge_cases_applied) if record.edge_cases_applied else ''
                })
            all_enhanced_records.append(pd.DataFrame(enhanced_data))
    
    if all_original_records:
        original_combined = pd.concat(all_original_records, ignore_index=True)
        original_path = output_path / 'original_parser_results.csv'
        original_combined.to_csv(original_path, index=False)
        print(f"Original parser results saved to: {original_path}")
    
    if all_improved_records:
        improved_combined = pd.concat(all_improved_records, ignore_index=True)
        improved_path = output_path / 'improved_parser_results.csv'
        improved_combined.to_csv(improved_path, index=False)
        print(f"Improved parser results saved to: {improved_path}")
    
    if all_enhanced_records:
        enhanced_combined = pd.concat(all_enhanced_records, ignore_index=True)
        enhanced_path = output_path / 'enhanced_parser_results.csv'
        enhanced_combined.to_csv(enhanced_path, index=False)
        print(f"Enhanced parser results saved to: {enhanced_path}")

def main():
    """Main enhanced comparison execution"""
    
    try:
        results = run_enhanced_comparison()
        
        print(f"\n=== Enhanced Comparison Complete ===")
        print(f"Check the generated files in data/congress/csv/ for detailed results")
        
        # Provide recommendations
        print(f"\n=== Recommendations ===")
        total_original = sum(r['original_records'] for r in results)
        total_improved = sum(r['improved_records'] for r in results)
        total_enhanced = sum(r['enhanced_records'] for r in results)
        
        print(f"Records extracted:")
        print(f"  Original parser: {total_original}")
        print(f"  Improved parser: {total_improved}")
        print(f"  Enhanced parser: {total_enhanced}")
        
        if total_enhanced >= total_original and total_enhanced >= total_improved:
            print(f"\n✅ Enhanced parser is the best performer!")
            print("Consider using the enhanced parser as it combines:")
            print("  - Original parser's edge case handling")
            print("  - Validation framework's quality assessment")
            print("  - Confidence scoring and parsing notes")
        elif total_original > total_enhanced:
            print(f"\n⚠️  Original parser still extracts more records")
            print("Consider further enhancing the enhanced parser with additional edge cases")
        else:
            print(f"\n📊 Mixed results - each parser has different strengths")
            print("Consider using the enhanced parser for its validation features")
        
    except Exception as e:
        print(f"Error during enhanced comparison: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 