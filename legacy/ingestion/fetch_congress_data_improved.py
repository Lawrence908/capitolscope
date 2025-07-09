#!/usr/bin/env python3
"""
Improved version of fetch_congress_data.py with rate limiting and better error handling
"""

import requests
import zipfile
import pandas as pd
import re
import os
import io
import sys
import time
import datetime
import asyncio
import aiohttp
import nest_asyncio
from bs4 import BeautifulSoup
from pathlib import Path
import pdfplumber
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine
import logging
from typing import Optional, List
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ingestion.log'),
        logging.StreamHandler()
    ]
)

# Ensure the database directory exists
root_path = Path(__file__).resolve().parents[2]
data_path = root_path / 'data' / 'congress' / 'csv'
db_path = root_path / 'data' / 'congress'
logs_path = root_path / 'logs'
logs_path.mkdir(exist_ok=True)

# Create a SQLite database engine
disk_engine = create_engine(f'sqlite:///{db_path}/congress_trades.db', echo=False)

# Import the get_tickers function
from fetch_stock_data import get_tickers, get_tickers_company_dict
from pdf_parsing_improvements import ImprovedPDFParser

class RateLimitedSession:
    """Session with rate limiting to avoid being blocked"""
    
    def __init__(self, delay_range=(1, 3)):
        self.delay_range = delay_range
        self.last_request = 0
        
    async def get(self, url: str, **kwargs):
        """Make a rate-limited GET request"""
        # Add random delay
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)
        
        # Add headers to avoid bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        kwargs['headers'] = {**headers, **kwargs.get('headers', {})}
        
        async with aiohttp.ClientSession() as session:
            return await session.get(url, **kwargs)

class CongressTradesImproved:
    def __init__(self, year: int = None):
        # Check if the year is valid
        if year == None:
            self.year = datetime.datetime.now().year
        else:
            if year < 2014:
                raise ValueError("The year must be 2014 or later.")
            if year > datetime.datetime.now().year:
                raise ValueError("The year must be the current year or earlier.")
            if len(str(year)) != 4:
                raise ValueError("The year must be in the format YYYY.")
            self.year = year
        
        # Set the root path dynamically
        self.root_path = Path(__file__).resolve().parents[2]
        self.data_path = self.root_path / 'data' / 'congress' / 'csv'
        self.pdf_path = self.root_path / 'data' / 'congress' / 'pdf'
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.pdf_path.mkdir(parents=True, exist_ok=True)
        self.data_path = str(self.data_path) + '/'
        self.pdf_path = str(self.pdf_path) + '/'
    
        self.tickers = get_tickers()
        self.tickers_company = get_tickers_company_dict()
        self.asset_dict = self.get_asset_type_dict()
        self.members = self.get_congress_members()
        self.junk_members = []

        # Initialize the improved PDF parser
        self.improved_parser = ImprovedPDFParser(
            tickers=set(self.tickers),
            asset_dict=self.asset_dict,
            tickers_company=self.tickers_company
        )

        # Apply nest_asyncio to allow nested use of asyncio.run()
        nest_asyncio.apply()
        self.trades = asyncio.run(self.get_trades_by_member())

    def get_asset_type_dict(self) -> dict:
        """Get asset type dictionary (same as original)"""
        asset_type_dict = {
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
        return asset_type_dict

    def get_congress_trading_data(self) -> pd.DataFrame:
        """Get congress trading data with improved error handling"""
        current_fd = str(self.year) + "FD"
        url = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/" + current_fd + ".zip"
        
        logging.info(f"Downloading initial data from: {url}")
        
        # Add retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                
                response = requests.get(url, headers=headers, timeout=30)
                logging.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    logging.info(f"Successfully downloaded {len(response.content)} bytes")
                    break
                elif response.status_code == 403:
                    logging.error(f"Access denied (403) - may be rate limited or data not available")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logging.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise Exception("Max retries exceeded for 403 error")
                else:
                    logging.error(f"HTTP {response.status_code}: {response.text[:200]}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        raise Exception(f"Failed to download after {max_retries} attempts")
                        
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        
        # Process the downloaded data
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        
        # Initialize lists to store data
        txt_data = []
        xml_data = []

        # Extract the TXT file
        txt_file_name = current_fd + ".txt"
        with zip_file.open(txt_file_name) as txt_file:
            for line in txt_file:
                txt_data.append(line.decode("utf-8").strip().split("\t"))

        # Extract the XML file
        xml_file_name = current_fd + ".xml"
        with zip_file.open(xml_file_name) as xml_file:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for trade in root.findall('.//Member'):
                trade_data = {child.tag: child.text for child in trade}
                xml_data.append(trade_data)

        # Create DataFrames
        txt_df = pd.DataFrame(txt_data[1:], columns=txt_data[0])
        txt_df.reset_index(drop=True, inplace=True)

        # Create a DataFrame from the XML data
        xml_df = pd.DataFrame(xml_data)
        xml_df.to_csv(self.data_path + current_fd + '_docIDlist.csv', index=False)
        
        logging.info(f"Saved: {current_fd}_docIDlist.csv")
        return xml_df

    def get_congress_members(self) -> list:
        """Get the members of Congress"""
        congress_data = self.get_congress_trading_data()
        congress_members = congress_data['Last'].unique().tolist()
        congress_members = congress_members[1:]
        return congress_members

    async def get_trades_by_member(self, member_list = None) -> pd.DataFrame:
        """Get trades by member with improved error handling"""
        current_fd = str(self.year) + "FD"
        congress_data = self.get_congress_trading_data()
        trades_by_member_df = pd.DataFrame()
        
        tasks = []
        async with aiohttp.ClientSession() as session:
            try:
                for _, row in congress_data.iterrows():
                    member = f"{row['Last']}".strip()
                    logging.info(f"Processing: {member}")
                    
                    if member:
                        doc_id = row['DocID']
                        if doc_id == None:
                            logging.warning(f"DocID is missing for {member}")
                            self.junk_members.append(member)
                            continue
                        
                        self.members.append(member)
                        
                        # Try all documents, not just those starting with "2"
                        logging.info(f"Processing DocID: {doc_id} for member: {member}")
                        tasks.append(self.download_and_parse_pdf(session, doc_id, member))
                        
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logging.error(f"Task {i} failed: {result}")
                    elif result is not None:
                        trades_by_member_df = pd.concat([result, trades_by_member_df], ignore_index=True)
              
            except Exception as e:
                logging.error(f"get_trades_by_member error: {e}")
        
        # Sort and save results
        if not trades_by_member_df.empty:
            trades_by_member_df = trades_by_member_df.sort_values(by=['Member', 'Transaction Date'], ascending=[True, False])
            trades_by_member_df.reset_index(drop=True, inplace=True)
            
            trades_by_member_df.to_csv(self.data_path + current_fd + '.csv', index=False)
            trades_by_member_df.to_excel(self.data_path + current_fd + '.xlsx', index=False)
            trades_by_member_df.to_sql(name=current_fd, con=disk_engine, if_exists='replace', index=False)
            
            logging.info(f"Saved: {current_fd}.csv")
            logging.info(f"Saved: {current_fd}.xlsx")
            logging.info(f"Saved: {current_fd}.db")
        else:
            logging.warning("No trades found")
        
        return trades_by_member_df

    async def download_and_parse_pdf(self, session, doc_id, member) -> pd.DataFrame:
        """Download and parse PDF with rate limiting"""
        trade_dict = {
            "Member": [], "DocID": [], "Owner": [], "Asset": [], "Ticker": [],
            "Transaction Type": [], "Transaction Date": [], "Notification Date": [],
            "Amount": [], "Filing Status": [], "Description": []
        }
            
        pdf_file_name = doc_id + ".pdf"
        url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{self.year}/{pdf_file_name}"
        
        try:
            # Add rate limiting
            await asyncio.sleep(random.uniform(1, 3))
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            async with session.get(url, headers=headers) as response:
                logging.info(f"Downloading: {doc_id} from URL: {url}")

                if response.status != 200:
                    logging.warning(f"Failed to download {doc_id}: HTTP {response.status}")
                    return None

                content = await response.read()
                with open(self.pdf_path + pdf_file_name, 'wb') as pdf_file:
                    pdf_file.write(content)
                
                logging.info(f"Downloaded: {doc_id} ({len(content)} bytes)")

                # Use the improved parser
                try:
                    logging.info(f"Parsing {doc_id} with improved parser...")
                    improved_records = self.improved_parser.parse_pdf_improved(
                        pdf_path=self.pdf_path + pdf_file_name,
                        doc_id=doc_id,
                        member=member
                    )
                    
                    if improved_records:
                        logging.info(f"Improved parser found {len(improved_records)} records for {doc_id}")
                        
                        for record in improved_records:
                            trade_dict["Member"].append(record.member)
                            trade_dict["DocID"].append(record.doc_id)
                            trade_dict["Owner"].append(record.owner)
                            trade_dict["Asset"].append(record.asset)
                            trade_dict["Ticker"].append(record.ticker)
                            trade_dict["Transaction Type"].append(record.transaction_type)
                            trade_dict["Transaction Date"].append(record.transaction_date)
                            trade_dict["Notification Date"].append(record.notification_date)
                            trade_dict["Amount"].append(record.amount)
                            trade_dict["Filing Status"].append(record.filing_status)
                            trade_dict["Description"].append(record.description)
                        
                        pdf_df = pd.DataFrame(trade_dict)
                        return pdf_df
                    else:
                        logging.info(f"No records found for {doc_id}")
                        return pd.DataFrame()
                        
                except Exception as e:
                    logging.error(f"Improved parser failed for {doc_id}: {e}")
                    return pd.DataFrame()
            
        except Exception as e:
            logging.error(f"download_and_parse_pdf error for {doc_id}: {e}")
            return None

def main():
    import sys
    
    # Check for year parameter from command line
    year = None
    if len(sys.argv) > 1:
        try:
            year = int(sys.argv[1])
            logging.info(f"Using year parameter: {year}")
        except ValueError:
            logging.error(f"Invalid year parameter: {sys.argv[1]}. Using current year.")
            year = None
    
    try:
        # Create an instance of the CongressTrades class
        congress_trades = CongressTradesImproved(year=year)
        
        # Get the trades by member
        trades_by_member = congress_trades.trades
        
        # Get the junk members
        junk_members = congress_trades.junk_members
        
        logging.info(f"Junk Members: {junk_members}")
        logging.info("Done")
        
    except Exception as e:
        logging.error(f"Main execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 