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
        

        
    async def get_trades_by_member(self, member_list = None) -> pd.DataFrame:
        current_fd = str(self.year) + "FD"
        congress_data = self.get_congress_trading_data()
        trades_by_member_df = pd.DataFrame()
        
        tasks = []
        async with aiohttp.ClientSession() as session:
            try:
                for _, row in congress_data.iterrows():
                    member = f"{row['Last']}".strip()
                    print ("Processing: ", member)  ##### DEBUGGING #####
                    if member:
                        doc_id = row['DocID']
                        if doc_id == None:
                            print("DocID is missing, some members of Congress do not have a DocID for downloadable PDFs.")   ##### DEBUGGING #####
                            self.junk_members.append(member)
                            continue
                        self.members.append(member)
                        
                        if doc_id.startswith("2"):
                            print("DocID download: ", doc_id)   ##### DEBUGGING #####
                            tasks.append(self.download_and_parse_pdf(session, doc_id, member))
                            # pdf_df = self.download_and_parse_pdf(doc_id)
                        else:
                            print("DocID does not start with 2: ", doc_id)   ##### DEBUGGING #####
                            self.junk_members.append(member)
                            continue
                        
                results = await asyncio.gather(*tasks)
                for pdf_df in results:
                    if pdf_df is not None:
                        trades_by_member_df = pd.concat([pdf_df, trades_by_member_df], ignore_index=True)
              
            except Exception as e:
                print("get_trades_by_member:", e)
        
        
        # Sort the DataFrame by Member and Transaction Date
        trades_by_member_df = trades_by_member_df.sort_values(by=['Member', 'Transaction Date'], ascending=[True, False])
        # Reset the index
        trades_by_member_df.reset_index(drop=True, inplace=True)
        # Save the DataFrame to a CSV file
        trades_by_member_df.to_csv(self.data_path + current_fd + '.csv', index=False)
        trades_by_member_df.to_excel(self.data_path + current_fd + '.xlsx', index=False)
        trades_by_member_df.to_sql(name=current_fd, con=disk_engine, if_exists='replace', index=False)
        
        print("Saved: ", current_fd + '.csv')   ##### DEBUGGING #####
        print("Saved: ", current_fd + '.xlsx')   ##### DEBUGGING #####
        print("Saved: ", current_fd + '.db')   ##### DEBUGGING #####
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
        print(f"Downloading initial data from: {url}")

        # Send a GET request to download the zip file
        try:
            response = requests.get(url, timeout=30)
            print(f"Response status: {response.status_code}")

            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to download the file: HTTP {response.status_code}")
                print(f"Response content: {response.text[:200]}...")
                sys.exit()

            print(f"Successfully downloaded {len(response.content)} bytes")
        except Exception as e:
            print(f"Error downloading initial data: {e}")
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
        
        print ("Saved: ", current_fd + '_docIDlist.csv')   ##### DEBUGGING #####
        # print ("Saved: ", current_fd + '_docIDlist.xlsx')   ##### DEBUGGING #####
        # print ("Saved: ", current_fd + '_docIDlist.db')  ##### DEBUGGING #####

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
            async with session.get(url) as response:
                print(f"Downloading: {doc_id} from URL: {url}")

                # Check if the request was successful
                if response.status != 200:
                    print(f"Failed to download {doc_id}: HTTP {response.status}")
                    return None

                # Use the pdfplumber library to extract text from the PDF
                content = await response.read()
                with open(self.pdf_path + pdf_file_name, 'wb') as pdf_file:
                    pdf_file.write(content)
                
                print(f"Downloaded: {doc_id} ({len(content)} bytes)")   ##### DEBUGGING #####

                # Use the improved parser to parse the PDF
                try:
                    print(f"Parsing {doc_id} with improved parser...")
                    improved_records = self.improved_parser.parse_pdf_improved(
                        pdf_path=self.pdf_path + pdf_file_name,
                        doc_id=doc_id,
                        member=member
                    )
                    
                    # Convert TradeRecord list to DataFrame
                    if improved_records:
                        print(f"Improved parser found {len(improved_records)} records for {doc_id}")
                        
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
                            print("PDF DataFrame is empty: ", doc_id)
                            pdf_df = pd.DataFrame()
                        return pdf_df
                    else:
                        print(f"No records found for {doc_id} with improved parser")
                        return pd.DataFrame()
                        
                except Exception as e:
                    print(f"Improved parser failed for {doc_id}: {e}")
                    return pd.DataFrame()
            
        except Exception as e:
            print("download_and_parse_pdf, try: ", e)   ##### DEBUGGING #####
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
                
                print(f"\n=== Record Count Comparison ===")
                print(f"Old records: {comparison['old_records']}")
                print(f"New records: {comparison['new_records']}")
                print(f"Difference: {comparison['difference']:+}")
                print(f"Improvement: {comparison['improvement_percentage']:.1f}%")
                print(f"Unique members: {comparison['new_unique_members']}")
                print(f"Unique doc IDs: {comparison['new_unique_doc_ids']}")
                
            except Exception as e:
                print(f"Error reading old CSV for comparison: {e}")
        else:
            print(f"\n=== New Record Count ===")
            print(f"Total records: {comparison['new_records']}")
            print(f"Unique members: {new_df['Member'].nunique()}")
            print(f"Unique doc IDs: {new_df['DocID'].nunique()}")
        
        return comparison
    
    
def main():
    import sys
    
    # Check for year parameter from command line
    year = None
    if len(sys.argv) > 1:
        try:
            year = int(sys.argv[1])
            print(f"Using year parameter: {year}")
        except ValueError:
            print(f"Invalid year parameter: {sys.argv[1]}. Using current year.")
            year = None
            
    # Change previous csv to _old.csv and compare to it after running
    if year == None:
        year = datetime.datetime.now().year
        print(f"Using current year: {year}")
        
    # Set the root path dynamically
    root_path = Path(__file__).resolve().parents[2]
    data_path = root_path / 'data' / 'congress' / 'csv'
    data_path = str(data_path) + '/'
        
    old_csv_path = data_path + str(year) + "FD.csv"
    try:
        if Path(old_csv_path).exists():
            print(f"\nComparing with previous results from {old_csv_path}")
            os.rename(old_csv_path, old_csv_path.replace(".csv", "_old.csv"))
    except Exception as e:
        print(f"Error renaming file: {e}")
        print(f"No previous results found for comparison")
    
    # Create an instance of the CongressTrades class for the specified year
    congress_trades = CongressTrades(year=year)
    
    
    # Get the trades by member
    trades_by_member = congress_trades.trades
    
    # Get the junk members
    junk_members = congress_trades.junk_members
    
    print("Junk Members: ", junk_members)   ##### DEBUGGING #####
    
    # Compare with previous results if available
    old_csv_path = congress_trades.data_path + str(year) + "FD_old.csv"
    if Path(old_csv_path).exists():
        print(f"\nComparing with previous results from {old_csv_path}")
        comparison = congress_trades.compare_record_counts(trades_by_member, old_csv_path)
    else:
        print(f"\nNo previous results found for comparison")
        comparison = congress_trades.compare_record_counts(trades_by_member)
    
    print("Done")   ##### DEBUGGING #####
    
if __name__ == "__main__":
    main()
