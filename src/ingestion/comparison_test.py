#!/usr/bin/env python3
"""
Comprehensive comparison test between original PDF parser and validation framework.
This script tests both approaches on the same PDFs and provides detailed comparison metrics.
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
from fetch_stock_data import get_tickers, get_tickers_company_dict

def setup_parsers():
    """Set up both parsers with the same configuration"""
    
    print("Setting up parsers...")
    
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
    
    # Initialize both parsers
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
    
    return original_parser, improved_parser

def find_test_pdfs():
    """Find PDF files for testing"""
    
    root_path = Path(__file__).resolve().parents[2]
    pdf_path = root_path / 'data' / 'congress' / 'pdf'
    
    # Use the same sample PDFs as before
    sample_pdfs = [
        "20000022.pdf",
        "20000034.pdf", 
        "20000036.pdf",
        "20000037.pdf",
        "20000070.pdf",
        "20000083.pdf",
        "20000085.pdf",
        "20000087.pdf",
        "20000134.pdf",
        "20000168.pdf"
    ]
    
    found_pdfs = []
    for pdf_name in sample_pdfs:
        pdf_file = pdf_path / pdf_name
        if pdf_file.exists():
            found_pdfs.append(str(pdf_file))
        else:
            print(f"Warning: {pdf_name} not found at {pdf_file}")
    
    return found_pdfs

def test_single_pdf_comparison(original_parser, improved_parser, pdf_path: str) -> Dict:
    """Test both parsers on a single PDF and compare results"""
    
    doc_id = Path(pdf_path).stem
    member = "TestMember"
    
    print(f"\n=== Testing {doc_id} ===")
    
    results = {
        'doc_id': doc_id,
        'original_records': 0,
        'improved_records': 0,
        'original_time': 0,
        'improved_time': 0,
        'original_df': None,
        'improved_records_list': [],
        'common_records': 0,
        'unique_to_original': 0,
        'unique_to_improved': 0
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
            print(f"  Average confidence: {avg_confidence:.2f}")
            
            # Count validation issues
            issues = sum(1 for r in improved_records if r.parsing_notes)
            print(f"  Records with issues: {issues}/{len(improved_records)}")
        
    except Exception as e:
        print(f"  Improved parser failed: {e}")
    
    # Compare results if both worked
    if results['original_records'] > 0 and results['improved_records'] > 0:
        comparison = compare_parsing_results(original_df, improved_records)
        results.update(comparison)
        
        print(f"  Comparison: {results['common_records']} common, "
              f"{results['unique_to_original']} unique to original, "
              f"{results['unique_to_improved']} unique to improved")
    
    return results

def compare_parsing_results(original_df: pd.DataFrame, improved_records: List[TradeRecord]) -> Dict:
    """Compare results from both parsers"""
    
    # Convert improved records to DataFrame for comparison
    improved_data = []
    for record in improved_records:
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
            'Description': record.description
        })
    
    improved_df = pd.DataFrame(improved_data)
    
    # Simple comparison based on key fields
    common_count = 0
    unique_to_original = 0
    unique_to_improved = 0
    
    # For each original record, check if there's a matching improved record
    for _, orig_row in original_df.iterrows():
        matching = improved_df[
            (improved_df['Owner'] == orig_row['Owner']) &
            (improved_df['Asset'] == orig_row['Asset']) &
            (improved_df['Transaction Type'] == orig_row['Transaction Type']) &
            (improved_df['Transaction Date'] == orig_row['Transaction Date'])
        ]
        
        if len(matching) > 0:
            common_count += 1
        else:
            unique_to_original += 1
    
    # For each improved record, check if there's a matching original record
    for _, imp_row in improved_df.iterrows():
        matching = original_df[
            (original_df['Owner'] == imp_row['Owner']) &
            (original_df['Asset'] == imp_row['Asset']) &
            (original_df['Transaction Type'] == imp_row['Transaction Type']) &
            (original_df['Transaction Date'] == imp_row['Transaction Date'])
        ]
        
        if len(matching) == 0:
            unique_to_improved += 1
    
    return {
        'common_records': common_count,
        'unique_to_original': unique_to_original,
        'unique_to_improved': unique_to_improved
    }

def run_comprehensive_comparison():
    """Run comprehensive comparison between both parsers"""
    
    print("=== PDF Parsing Comparison Test ===\n")
    
    # Setup parsers
    original_parser, improved_parser = setup_parsers()
    
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
    total_original_time = 0
    total_improved_time = 0
    
    for pdf_file in pdf_files:
        results = test_single_pdf_comparison(original_parser, improved_parser, pdf_file)
        all_results.append(results)
        
        total_original_records += results['original_records']
        total_improved_records += results['improved_records']
        total_original_time += results['original_time']
        total_improved_time += results['improved_time']
    
    # Generate summary report
    print(f"\n=== Summary Report ===")
    print(f"Total PDFs tested: {len(pdf_files)}")
    print(f"Original parser: {total_original_records} total records in {total_original_time:.3f}s")
    print(f"Improved parser: {total_improved_records} total records in {total_improved_time:.3f}s")
    
    if total_original_records > 0:
        print(f"Original parser average: {total_original_records/len(pdf_files):.1f} records per PDF")
    if total_improved_records > 0:
        print(f"Improved parser average: {total_improved_records/len(pdf_files):.1f} records per PDF")
    
    # Save detailed results
    save_comparison_results(all_results)
    
    return all_results

def save_comparison_results(results: List[Dict]):
    """Save detailed comparison results"""
    
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
            'Original_Time_s': result['original_time'],
            'Improved_Time_s': result['improved_time'],
            'Common_Records': result.get('common_records', 0),
            'Unique_to_Original': result.get('unique_to_original', 0),
            'Unique_to_Improved': result.get('unique_to_improved', 0)
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_path = output_path / 'parsing_comparison_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"\nComparison summary saved to: {summary_path}")
    
    # Save detailed results for each parser
    all_original_records = []
    all_improved_records = []
    
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

def main():
    """Main comparison execution"""
    
    try:
        results = run_comprehensive_comparison()
        
        print(f"\n=== Comparison Complete ===")
        print(f"Check the generated files in data/congress/csv/ for detailed results")
        
        # Provide recommendations
        print(f"\n=== Recommendations ===")
        total_original = sum(r['original_records'] for r in results)
        total_improved = sum(r['improved_records'] for r in results)
        
        if total_original > total_improved:
            print(f"Original parser extracted more records ({total_original} vs {total_improved})")
            print("Consider incorporating original parser's edge case handling into validation framework")
        elif total_improved > total_original:
            print(f"Improved parser extracted more records ({total_improved} vs {total_original})")
            print("Validation framework shows promise for better parsing")
        else:
            print("Both parsers extracted similar numbers of records")
            print("Focus on quality and validation features of the improved parser")
        
    except Exception as e:
        print(f"Error during comparison: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 