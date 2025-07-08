# # Process each year with conservative settings
# for year in 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025; do
#     echo "Processing year $year..."
#     python src/ingestion/fetch_congress_data.py $year --delay 3.0 --concurrent 2 --retries 5
#     echo "Completed $year, waiting before next year..."
#     sleep 60
# done



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
import logging
from bs4 import BeautifulSoup
from pathlib import Path
import pdfplumber
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine

# Configure logging
def setup_logging(level=logging.INFO, log_file=None):
    """
    Set up logging configuration for congressional data processing.
    
    Parameters:
    -----------
    level : int
        Logging level (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
    log_file : str, optional
        Path to log file. If None, logs only to console.
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create logger
    logger = logging.getLogger('congress_data')
    logger.setLevel(level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets all debug info
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Initialize logger (will be configured in main())
logger = logging.getLogger('congress_data')

# Ensure the database directory exists
root_path = Path(__file__).resolve().parents[2]
data_path = root_path / 'data' / 'congress' / 'csv'
db_path = root_path / 'data' / 'congress'

# Create a SQLite database engine
disk_engine = create_engine(f'sqlite:///{db_path}/congress_trades.db', echo=False)

# Import the get_tickers function
# from src.ingestion.fetch_stock_data import get_tickers, get_tickers_company_dict
from fetch_stock_data import get_tickers, get_tickers_company_dict
from pdf_parsing_improvements import ImprovedPDFParser

# Rate limiting configuration
REQUEST_DELAY = 2.0  # 2 seconds between requests
MAX_CONCURRENT_DOWNLOADS = 3  # Limit concurrent downloads
MAX_RETRIES = 3  # Retry failed downloads
RETRY_DELAY = 5.0  # 5 seconds between retries

def configure_rate_limiting(request_delay=2.0, max_concurrent=3, max_retries=3, retry_delay=5.0):
    """
    Configure rate limiting parameters for congressional data downloads.
    
    Parameters:
    -----------
    request_delay : float
        Minimum seconds between requests (default: 2.0)
    max_concurrent : int
        Maximum concurrent downloads (default: 3)
    max_retries : int
        Maximum retry attempts for failed downloads (default: 3)
    retry_delay : float
        Seconds to wait between retry attempts (default: 5.0)
    """
    global REQUEST_DELAY, MAX_CONCURRENT_DOWNLOADS, MAX_RETRIES, RETRY_DELAY
    REQUEST_DELAY = request_delay
    MAX_CONCURRENT_DOWNLOADS = max_concurrent
    MAX_RETRIES = max_retries
    RETRY_DELAY = retry_delay
    
    logger.info("Rate limiting configured:")
    logger.info(f"  Request delay: {REQUEST_DELAY}s")
    logger.info(f"  Max concurrent: {MAX_CONCURRENT_DOWNLOADS}")
    logger.info(f"  Max retries: {MAX_RETRIES}")
    logger.info(f"  Retry delay: {RETRY_DELAY}s")

# Define the CongressTrades class
class CongressTrades:
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
        
        logger.info(f"Initializing CongressTrades for year {self.year}")
        
        # Set the root path dynamically
        self.root_path = Path(__file__).resolve().parents[2]
        self.data_path = self.root_path / 'data' / 'congress' / 'csv'
        self.pdf_path = self.root_path / 'data' / 'congress' / 'pdf'
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.pdf_path.mkdir(parents=True, exist_ok=True)
        self.data_path = str(self.data_path) + '/'
        self.pdf_path = str(self.pdf_path) + '/'
        
        logger.debug(f"Data path: {self.data_path}")
        logger.debug(f"PDF path: {self.pdf_path}")
    
        # Rate limiting semaphore
        self.download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        self.last_request_time = 0
        
        logger.info("Loading stock tickers and asset data...")
        self.tickers = get_tickers()
        self.tickers_company = get_tickers_company_dict()
        self.asset_dict = self.get_asset_type_dict()
        self.members = self.get_congress_members()
        self.junk_members = []
        
        logger.info(f"Loaded {len(self.tickers)} stock tickers and {len(self.asset_dict)} asset types")

        # Initialize the improved PDF parser
        logger.info("Initializing improved PDF parser...")
        self.improved_parser = ImprovedPDFParser(
            tickers=set(self.tickers),
            asset_dict=self.asset_dict,
            tickers_company=self.tickers_company
        )

        # Apply nest_asyncio to allow nested use of asyncio.run()
        nest_asyncio.apply()
        logger.info("Starting trade data processing...")
        self.trades = asyncio.run(self.get_trades_by_member())
        
    async def rate_limit_delay(self):
        """Ensure minimum delay between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - time_since_last)
        self.last_request_time = time.time()

        
    async def get_trades_by_member(self, member_list = None) -> pd.DataFrame:
        current_fd = str(self.year) + "FD"
        congress_data = self.get_congress_trading_data()
        trades_by_member_df = pd.DataFrame()
        
        # Prepare list of valid document IDs to download
        doc_ids_to_download = []
        total_members = len(congress_data)
        valid_members = 0
        
        for _, row in congress_data.iterrows():
            member = f"{row['Last']}".strip()
            logger.debug(f"Processing: {member}")
            if member:
                doc_id = row['DocID']
                if doc_id == None:
                    logger.debug(f"DocID is missing for {member}")
                    self.junk_members.append(member)
                    continue
                self.members.append(member)
                
                if doc_id.startswith("2"):
                    # Check if PDF already exists to enable resume functionality
                    pdf_file_path = self.pdf_path + doc_id + ".pdf"
                    if Path(pdf_file_path).exists():
                        logger.debug(f"PDF already exists for {doc_id}, skipping download")
                        # Still try to parse the existing PDF
                        try:
                            existing_records = self.improved_parser.parse_pdf_improved(
                                pdf_path=pdf_file_path,
                                doc_id=doc_id,
                                member=member
                            )
                            if existing_records:
                                logger.debug(f"Parsed existing PDF {doc_id} with {len(existing_records)} records")
                                # Convert to DataFrame and add to results
                                trade_dict = {
                                    "Member": [], "DocID": [], "Owner": [], "Asset": [], "Ticker": [],
                                    "Transaction Type": [], "Transaction Date": [], "Notification Date": [],
                                    "Amount": [], "Filing Status": [], "Description": []
                                }
                                for record in existing_records:
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
                                existing_df = pd.DataFrame(trade_dict)
                                trades_by_member_df = pd.concat([existing_df, trades_by_member_df], ignore_index=True)
                        except Exception as e:
                            logger.error(f"Error parsing existing PDF {doc_id}: {e}")
                    else:
                        logger.debug(f"DocID download: {doc_id}")
                        doc_ids_to_download.append((doc_id, member))
                    valid_members += 1
                else:
                    logger.debug(f"DocID does not start with 2: {doc_id}")
                    self.junk_members.append(member)
                    continue
        
        logger.info(f"Processed {total_members} members: {valid_members} valid, {len(self.junk_members)} invalid DocIDs")
        
        # Process downloads in batches to reduce server load
        BATCH_SIZE = 10  # Process 10 documents at a time
        total_docs = len(doc_ids_to_download)
        skipped_docs = valid_members - total_docs
        
        if skipped_docs > 0:
            logger.info(f"Found {skipped_docs} existing PDFs, skipping downloads")
        
        if total_docs > 0:
            logger.info(f"Starting download of {total_docs} new PDFs")
        else:
            logger.info("No new PDFs to download")
        
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_DOWNLOADS, limit_per_host=MAX_CONCURRENT_DOWNLOADS)
        timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                successful_downloads = 0
                failed_downloads = 0
                
                # Process in batches
                for i in range(0, total_docs, BATCH_SIZE):
                    batch = doc_ids_to_download[i:i + BATCH_SIZE]
                    batch_num = (i // BATCH_SIZE) + 1
                    total_batches = (total_docs + BATCH_SIZE - 1) // BATCH_SIZE
                    
                    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
                    
                    # Create tasks for this batch
                    batch_tasks = []
                    for doc_id, member in batch:
                        batch_tasks.append(self.download_and_parse_pdf_with_retry(session, doc_id, member))
                    
                    # Execute batch with rate limiting
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process batch results
                    batch_successful = 0
                    for j, result in enumerate(batch_results):
                        doc_id, member = batch[j]
                        if isinstance(result, Exception):
                            logger.error(f"Download task failed for {doc_id}: {result}")
                            failed_downloads += 1
                        elif result is not None and not result.empty:
                            trades_by_member_df = pd.concat([result, trades_by_member_df], ignore_index=True)
                            successful_downloads += 1
                            batch_successful += 1
                        else:
                            failed_downloads += 1
                    
                    logger.info(f"Batch {batch_num} completed: {batch_successful}/{len(batch)} successful")
                    
                    # Add a longer delay between batches to be respectful
                    if i + BATCH_SIZE < total_docs:
                        logger.debug(f"Waiting {RETRY_DELAY} seconds before next batch...")
                        await asyncio.sleep(RETRY_DELAY)
                
                if total_docs > 0:
                    success_rate = (successful_downloads / total_docs) * 100
                    logger.info(f"Download summary: {successful_downloads}/{total_docs} successful ({success_rate:.1f}%)")
                    if failed_downloads > 0:
                        logger.warning(f"Failed downloads: {failed_downloads}")
              
            except Exception as e:
                logger.error("get_trades_by_member:", e)
        
        
        # Sort the DataFrame by Member and Transaction Date
        trades_by_member_df = trades_by_member_df.sort_values(by=['Member', 'Transaction Date'], ascending=[True, False])
        # Reset the index
        trades_by_member_df.reset_index(drop=True, inplace=True)
        # Save the DataFrame to a CSV file
        trades_by_member_df.to_csv(self.data_path + current_fd + '.csv', index=False)
        trades_by_member_df.to_excel(self.data_path + current_fd + '.xlsx', index=False)
        trades_by_member_df.to_sql(name=current_fd, con=disk_engine, if_exists='replace', index=False)
        
        logger.info(f"Saved: {current_fd}.csv")
        logger.info(f"Saved: {current_fd}.xlsx")
        logger.info(f"Saved: {current_fd}.db")
        return trades_by_member_df

    
    def get_asset_type_dict(self) -> dict:
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
    
    # NOTE Commented out because too many requests to the website caused an error, using a dictionary above instead
    # def get_asset_type_dict(self) -> dict:
    #     """
    #     Get the asset type codes from house.gov website.
    #     Returns
    #     -------
    #     dict
    #         A dictionary containing the asset codes and their names.
    #     """
    #     url = "https://fd.house.gov/reference/asset-type-codes.aspx"
    #     response = requests.get(url)
    #     soup = BeautifulSoup(response.text, 'html.parser')
    #     table = soup.find_all('table')[0]
    #     html_string = str(table)
    #     html_io = io.StringIO(html_string)
    #     df = pd.read_html(html_io)[0]

    #     asset_type_dict = df.set_index('Asset Code')['Asset Name'].to_dict()

    #     return asset_type_dict

    def get_congress_trading_data(self) -> pd.DataFrame:
        current_fd = str(self.year) + "FD"

        # Define the URL of the zip file
        url = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/" + current_fd + ".zip"
        logger.info(f"Downloading initial data from: {url}")

        # Send a GET request to download the zip file
        try:
            response = requests.get(url, timeout=30)
            logger.info(f"Response status: {response.status_code}")

            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"Failed to download the file: HTTP {response.status_code}")
                logger.error(f"Response content: {response.text[:200]}...")
                sys.exit()

            logger.info(f"Successfully downloaded {len(response.content)} bytes")
        except Exception as e:
            logger.error(f"Error downloading initial data: {e}")
            sys.exit()

        # Load the zip file into memory
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
        # Save the DataFrame to a CSV file
        xml_df.to_csv(self.data_path + current_fd + '_docIDlist.csv', index=False)
        # xml_df.to_excel(self.data_path + current_fd + '_docIDlist.xlsx', index=False)
        # xml_df.to_sql(name=current_fd + '_docIDlist', con=disk_engine, if_exists='replace', index=False)
        
        logger.info(f"Saved: {current_fd}_docIDlist.csv")
        # logger.info(f"Saved: {current_fd}_docIDlist.xlsx")
        # logger.info(f"Saved: {current_fd}_docIDlist.db")

        return xml_df
    
    def get_congress_members(self) -> list:
        """
        Get the members of Congress from the House of Representatives website.
        Returns
        -------
        dict
            A dictionary containing the members of Congress.
        """
        congress_data = self.get_congress_trading_data()

        congress_members = congress_data['Last'].unique().tolist()
        congress_members = congress_members[1:]

        return congress_members
    
    def get_junk_members(self):
        """
        Get the members of Congress that do not have a DocID for downloadable PDFs.
        Returns
        -------
        list
            A list containing the members of Congress that do not have a DocID for downloadable PDFs.
        """
        junk_members = []
        
        with open('data/congress/txt/junk_members.txt', 'r') as f:
            for line in f:
                junk_members.append(line.strip())
        
        return junk_members

    async def download_and_parse_pdf_with_retry(self, session, doc_id, member) -> pd.DataFrame:
        """
        Download and parse PDF with retry logic for rate limiting
        """
        async with self.download_semaphore:  # Limit concurrent downloads
            for attempt in range(MAX_RETRIES):
                try:
                    # Rate limiting delay
                    await self.rate_limit_delay()
                    
                    result = await self.download_and_parse_pdf(session, doc_id, member)
                    if result is not None:
                        return result
                    else:
                        logger.warning(f"No data returned for {doc_id}, attempt {attempt + 1}")
                        
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed for {doc_id}: {e}")
                    if attempt < MAX_RETRIES - 1:
                        logger.info(f"Retrying {doc_id} in {RETRY_DELAY} seconds...")
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        logger.error(f"All retry attempts failed for {doc_id}")
                        
            return pd.DataFrame()  # Return empty DataFrame if all attempts fail

    async def download_and_parse_pdf(self, session, doc_id, member) -> pd.DataFrame:
        """
        Download and parse a financial disclosure PDF to extract structured trade data.
        Handles multi-line trade entries robustly.
        """
        
        trade_dict = {
            "Member": [],
            "DocID": [],
            "Owner": [],
            "Asset": [],
            "Ticker": [],
            "Transaction Type": [],
            "Transaction Date": [],
            "Notification Date": [],
            "Amount": [],
            "Filing Status": [],
            "Description": []
        }
            
        pdf_file_name = doc_id + ".pdf"

        # Define the URL of the zip file
        url = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/" + str(self.year) + '/' + pdf_file_name
        
        # Send a GET request to download the zip file
        try:
            logger.info(f"Downloading: {doc_id} from URL: {url}")
            async with session.get(url) as response:
                # Check if the request was successful
                if response.status == 403:
                    logger.warning(f"Rate limited (HTTP 403) for {doc_id}")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=403,
                        message="Rate limited"
                    )
                elif response.status != 200:
                    logger.error(f"Failed to download {doc_id}: HTTP {response.status}")
                    return None

                # Use the pdfplumber library to extract text from the PDF
                content = await response.read()
                with open(self.pdf_path + pdf_file_name, 'wb') as pdf_file:
                    pdf_file.write(content)
                
                logger.info(f"Downloaded: {doc_id} ({len(content)} bytes)")

                # Use the improved parser to parse the PDF
                try:
                    logger.info(f"Parsing {doc_id} with improved parser...")
                    improved_records = self.improved_parser.parse_pdf_improved(
                        pdf_path=self.pdf_path + pdf_file_name,
                        doc_id=doc_id,
                        member=member
                    )
                    
                    # Convert TradeRecord list to DataFrame
                    if improved_records:
                        logger.info(f"Improved parser found {len(improved_records)} records for {doc_id}")
                        
                        # Convert records to DataFrame format
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
                        
                        if pdf_df is not None:
                            pdf_df = pdf_df.sort_values(by=['Member', 'Transaction Date'], ascending=[True, False])
                            pdf_df.reset_index(drop=True, inplace=True)
                        else:
                            logger.warning(f"PDF DataFrame is empty: {doc_id}")
                            pdf_df = pd.DataFrame()
                        return pdf_df
                    else:
                        logger.warning(f"No records found for {doc_id} with improved parser")
                        return pd.DataFrame()
                        
                except Exception as e:
                    logger.error(f"Improved parser failed for {doc_id}: {e}")
                    return pd.DataFrame()
            
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                # Re-raise 403 errors for retry logic
                raise e
            else:
                logger.error(f"HTTP error for {doc_id}: {e}")
                return None
        except Exception as e:
            logger.error("download_and_parse_pdf, try: ", e)
            return None
    
    def get_doc_ids(self, trade_list) -> str:
        """
        Get the document IDs from the trade list.
        Parameters
        ----------
        trade_list : list
            The list of trades.
        Returns
        -------
        str
            The document IDs.
        """
        doc_ids = []
        for trade in trade_list:
            if trade['DocID'] == None:
                raise ValueError("DocID is missing, some members of Congress do not have a DocID for downloadable PDFs.")
            else:
                doc_id = trade['DocID']
            doc_ids.append(doc_id)
        return doc_ids
    
    def compare_record_counts(self, new_df: pd.DataFrame, old_csv_path: str = None) -> dict:
        """
        Compare record counts between new parsing results and old CSV file.
        
        Parameters
        ----------
        new_df : pd.DataFrame
            The new DataFrame with improved parser results
        old_csv_path : str, optional
            Path to the old CSV file for comparison
            
        Returns
        -------
        dict
            Comparison statistics
        """
        comparison = {
            'new_records': len(new_df),
            'old_records': 0,
            'difference': 0,
            'improvement_percentage': 0,
            'new_unique_members': 0,
            'new_unique_doc_ids': 0
        }
        
        if old_csv_path and Path(old_csv_path).exists():
            try:
                old_df = pd.read_csv(old_csv_path)
                comparison['old_records'] = len(old_df)
                comparison['difference'] = comparison['new_records'] - comparison['old_records']
                
                if comparison['old_records'] > 0:
                    comparison['improvement_percentage'] = (
                        (comparison['new_records'] - comparison['old_records']) / comparison['old_records']
                    ) * 100
                
                # Count unique members and doc IDs
                comparison['new_unique_members'] = new_df['Member'].nunique()
                comparison['new_unique_doc_ids'] = new_df['DocID'].nunique()
                
                logger.info(f"\n=== Record Count Comparison ===")
                logger.info(f"Old records: {comparison['old_records']}")
                logger.info(f"New records: {comparison['new_records']}")
                logger.info(f"Difference: {comparison['difference']:+}")
                logger.info(f"Improvement: {comparison['improvement_percentage']:.1f}%")
                logger.info(f"Unique members: {comparison['new_unique_members']}")
                logger.info(f"Unique doc IDs: {comparison['new_unique_doc_ids']}")
                
            except Exception as e:
                logger.error(f"Error reading old CSV for comparison: {e}")
        else:
            logger.info(f"\n=== New Record Count ===")
            logger.info(f"Total records: {comparison['new_records']}")
            logger.info(f"Unique members: {new_df['Member'].nunique()}")
            logger.info(f"Unique doc IDs: {new_df['DocID'].nunique()}")
        
        return comparison
    
    
def main():
    import sys
    import argparse
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Download and parse congressional trading data')
    parser.add_argument('year', type=int, nargs='?', default=None, 
                       help='Year to process (default: current year)')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between requests in seconds (default: 2.0)')
    parser.add_argument('--concurrent', type=int, default=3,
                       help='Maximum concurrent downloads (default: 3)')
    parser.add_argument('--retries', type=int, default=3,
                       help='Maximum retry attempts (default: 3)')
    parser.add_argument('--retry-delay', type=float, default=5.0,
                       help='Delay between retries in seconds (default: 5.0)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set logging level (default: INFO)')
    parser.add_argument('--log-file', type=str, default=None,
                       help='Log file path (default: console only)')
    parser.add_argument('--quiet', action='store_true',
                       help='Quiet mode - only show warnings and errors')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.quiet:
        log_level = logging.WARNING
    else:
        log_level = getattr(logging, args.log_level.upper())
    
    global logger
    logger = setup_logging(level=log_level, log_file=args.log_file)
    
    logger.info("=== Congressional Trading Data Processing ===")
    
    # Configure rate limiting with provided parameters
    configure_rate_limiting(
        request_delay=args.delay,
        max_concurrent=args.concurrent,
        max_retries=args.retries,
        retry_delay=args.retry_delay
    )
    
    year = args.year
    if year is None:
        year = datetime.datetime.now().year
        logger.info(f"Using current year: {year}")
    else:
        logger.info(f"Using year parameter: {year}")
        
    # Set the root path dynamically
    root_path = Path(__file__).resolve().parents[2]
    data_path = root_path / 'data' / 'congress' / 'csv'
    data_path = str(data_path) + '/'
        
    old_csv_path = data_path + str(year) + "FD.csv"
    try:
        if Path(old_csv_path).exists():
            logger.info(f"Comparing with previous results from {old_csv_path}")
            os.rename(old_csv_path, old_csv_path.replace(".csv", "_old.csv"))
    except Exception as e:
        logger.error(f"Error renaming file: {e}")
        logger.info(f"No previous results found for comparison")
    
    # Create an instance of the CongressTrades class for the specified year
    logger.info(f"Initializing CongressTrades for year {year}")
    congress_trades = CongressTrades(year=year)
    
    # Get the trades by member
    trades_by_member = congress_trades.trades
    
    # Get the junk members
    junk_members = congress_trades.junk_members
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Junk Members: {junk_members}")
    else:
        logger.info(f"Total junk members (no valid DocID): {len(junk_members)}")
    
    # Compare with previous results if available
    old_csv_path = congress_trades.data_path + str(year) + "FD_old.csv"
    if Path(old_csv_path).exists():
        logger.info(f"Comparing with previous results from {old_csv_path}")
        comparison = congress_trades.compare_record_counts(trades_by_member, old_csv_path)
    else:
        logger.info(f"No previous results found for comparison")
        comparison = congress_trades.compare_record_counts(trades_by_member)
    
    logger.info("Processing completed successfully")
    
    return {
        'year': year,
        'total_records': len(trades_by_member),
        'unique_members': trades_by_member['Member'].nunique() if not trades_by_member.empty else 0,
        'unique_doc_ids': trades_by_member['DocID'].nunique() if not trades_by_member.empty else 0,
        'junk_members_count': len(junk_members),
        'comparison': comparison
    }
    
if __name__ == "__main__":
    result = main()
    # Exit with appropriate code based on results
    if result and result.get('total_records', 0) > 0:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # No records processed
