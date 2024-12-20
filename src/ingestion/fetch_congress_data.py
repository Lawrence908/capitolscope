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
from src.ingestion.fetch_stock_data import get_tickers, get_tickers_company_dict

# Define the CongressTrades class
class CongressTrades:
    def __init__(self, year: int = None):
        # Check if the year is valid
        if year == None:
            self.year = datetime.datetime.now().year
        else:
            if year < 2006:
                raise ValueError("The year must be 2006 or later.")
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
                    print ("Processing: ", row['Last'])   ##### DEBUGGING #####
                    member = f"{row['Last']}".strip()
                    # Check if the member is in the junk list
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
        trades_by_member_df.to_sql(name=current_fd, con=disk_engine, if_exists='replace')
        
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

        # Send a GET request to download the zip file
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code != 200:
            print("Failed to download the file")
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
        xml_df.to_excel(self.data_path + current_fd + '_docIDlist.xlsx', index=False)
        xml_df.to_sql(name=current_fd + '_docIDlist', con=disk_engine, if_exists='replace')
        print ("Saved: ", current_fd + '_docIDlist.csv')   ##### DEBUGGING #####
        print ("Saved: ", current_fd + '_docIDlist.xlsx')   ##### DEBUGGING #####
        print ("Saved: ", current_fd + '_docIDlist.db')  ##### DEBUGGING #####

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
                print("Downloading: ", doc_id)
                # response = requests.get(url)

                # Check if the request was successful
                if response.status != 200:
                    print(f"Failed to download the file: {doc_id}")
                    return None

                # Use the pdfplumber library to extract text from the PDF
                content = await response.read()
                with open(self.pdf_path + pdf_file_name, 'wb') as pdf_file:
                    pdf_file.write(content)
                
                print("Downloaded: ", doc_id)   ##### DEBUGGING #####      

                # Open the PDF file
                with pdfplumber.open(self.pdf_path + pdf_file_name) as pdf:
                    pdf_text = "".join(page.extract_text() for page in pdf.pages)

                if not pdf_text.strip():
                    print("PDF is empty: ", doc_id)   ##### DEBUGGING #####
                    return pd.DataFrame()

                lines = pdf_text.splitlines()
                
                owner_types = ["SP", "DC", "JT"]
                current_trade = {key: "" for key in trade_dict}  # Initialize a trade record
                
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    # Check if this is a new trade line starting with known owner types
                    if any(line.startswith(owner_type) for owner_type in owner_types):
                        if current_trade["Owner"]:  # If current_trade is not empty, save it
                            for key in trade_dict:
                                trade_dict[key].append(current_trade[key])
                            current_trade = {key: "" for key in trade_dict}  # Reset current trade

                        columns = line.split()
                        
                        if doc_id == "20019790":
                            # print a line for debugging with column values
                            print("Columns: ", columns)   ##### DEBUGGING #####
                        
                        
                        current_trade["Member"] = member
                        current_trade["DocID"] = doc_id
                        current_trade["Owner"] = columns[0]
                        current_trade["Asset"] = " ".join(columns[1:-6]).split("-", 1)[0].strip()
                        # current_trade["Ticker"] = columns[-6].strip("()")
                        
                        # Find t he column containing "()" and split the asset and ticker
                        if current_trade["Asset"].__contains__("("):
                            current_trade["Asset"], current_trade["Ticker"] = current_trade["Asset"].rsplit("(", 1)
                            current_trade["Ticker"] = current_trade["Ticker"].split(")")[0]
                            
                        current_trade["Transaction Type"] = columns[-5]
                        current_trade["Transaction Date"] = columns[-4]
                        current_trade["Notification Date"] = columns[-3]
                        current_trade["Amount"] = columns[-2]
                        
                        
                        if current_trade["Notification Date"].startswith("$") and current_trade["Notification Date"].endswith("1"):
                            current_trade["Amount"] = columns[-3]
                            current_trade["Notification Date"] = columns[-4]
                            current_trade["Transaction Date"] = columns[-5]
                            current_trade["Transaction Type"] = columns[-6]
                        elif current_trade["Notification Date"].startswith("$") and current_trade["Notification Date"].endswith("0"):
                            current_trade["Amount"] = columns[-5]
                            current_trade["Notification Date"] = columns[-6]
                            current_trade["Transaction Date"] = columns[-7]
                            current_trade["Transaction Type"] = columns[-8]


                        if current_trade["Transaction Date"].startswith("$") and current_trade["Transaction Date"].endswith("1"):
                            current_trade["Amount"] = columns[-4]
                            current_trade["Notification Date"] = columns[-5]
                            current_trade["Transaction Date"] = columns[-6]
                            current_trade["Transaction Type"] = columns[-7]
                        elif current_trade["Transaction Date"].startswith("$") and current_trade["Transaction Date"].endswith("0"):
                            current_trade["Amount"] = columns[-7]
                            current_trade["Notification Date"] = columns[-6]
                            current_trade["Transaction Date"] = columns[-5]
                            current_trade["Transaction Type"] = columns[-4]
                        

                        if current_trade["Transaction Type"].startswith("(partial)"):
                            current_trade["Transaction Type"] = columns[-6] + " " + columns[-5]
                            if current_trade["Transaction Type"].startswith("(partial)"):
                                current_trade["Transaction Type"] = columns[-7] + " " + columns[-6]    
                        
                        # check if transaction type is a date
                        if current_trade["Transaction Type"].startswith("0") or current_trade["Transaction Type"].startswith("1") or current_trade["Transaction Type"].startswith("2") or current_trade["Transaction Type"].startswith("3") or current_trade["Transaction Type"].startswith("4") or current_trade["Transaction Type"].startswith("5") or current_trade["Transaction Type"].startswith("6") or current_trade["Transaction Type"].startswith("7") or current_trade["Transaction Type"].startswith("8") or current_trade["Transaction Type"].startswith("9"):
                            if current_trade["Notification Date"].startswith("$"):
                                current_trade["Amount"] = current_trade["Notification Date"]
                            current_trade["Notification Date"] = current_trade["Transaction Type"].split(" ")[1]
                            if current_trade["Notification Date"].startswith("$"):
                                current_trade["Amount"] = current_trade["Notification Date"]
                            current_trade["Transaction Date"] = current_trade["Transaction Type"].split(" ")[0]
                            current_trade["Transaction Type"] = columns[-8]
                            current_trade["Amount"] = columns[-3]
                            
                        if current_trade["Amount"] == "-":
                            current_trade["Amount"] = columns[-3]
                        
                        # Set amount based on current case
                        if current_trade["Amount"] == "$0":
                            current_trade["Amount"] = "None"
                        elif current_trade["Amount"] == "$1":
                            current_trade["Amount"] = "$1 - $15,000"
                        elif current_trade["Amount"] == "$1,001":
                            current_trade["Amount"] = "$1,001 - $15,000"
                        elif current_trade["Amount"] == "$15,000":
                            current_trade["Amount"] = "$1,001 - $15,000"
                        elif current_trade["Amount"] == "$15,001":
                            current_trade["Amount"] = "$15,001 - $50,000"
                        elif current_trade["Amount"] == "$50,001":
                            current_trade["Amount"] = "$50,001 - $100,000"
                        elif current_trade["Amount"] == "$100,001":
                            current_trade["Amount"] = "$100,001 - $250,000"
                        elif current_trade["Amount"] == "$250,001":
                            current_trade["Amount"] = "$250,001 - $500,000"
                        elif current_trade["Amount"] == "$500,001":
                            current_trade["Amount"] = "$500,001 - $1,000,000"
                        elif current_trade["Amount"] == "$1,000,001":
                            current_trade["Amount"] = "$1,000,001 - $5,000,000"
                        elif current_trade["Amount"] == "$5,000,001":
                            current_trade["Amount"] = "$5,000,001 - $25,000,000"
                        if current_trade["Transaction Type"].startswith("(partial)"):
                            current_trade["Transaction Type"] = columns[-6] + " " + columns[-5]
                            if current_trade["Transaction Type"].startswith("(partial)"):
                                current_trade["Transaction Type"] = columns[-7] + " " + columns[-6] 

                        # Look ahead for additional information (multi-line)
                        j = i + 1
                        while j < len(lines) and not any(lines[j].startswith(owner) for owner in owner_types):
                            next_line = lines[j].strip()
                            if next_line.startswith("* For the"):
                                break
                            elif next_line.startswith("("):  # Ticker continuation
                                current_trade["Ticker"] = re.search(r'\((.*?)\)', next_line).group(1)
                            elif next_line.startswith("Stock"):
                                current_trade["Asset"] += " " + next_line.split("Stock", 1)[0].strip()
                                current_trade["Ticker"] = re.search(r'\((.*?)\)', next_line).group(1)
                            elif next_line.startswith("F"):  # Filing Status
                                current_trade["Filing Status"] = next_line.split(":", 1)[1].strip()
                                if current_trade["Filing Status"].startswith("New"):
                                    current_trade["Filing Status"] = "New"
                            elif next_line.startswith("S"):
                                current_trade["Description"] = "Subholding of: " + next_line.split(":", 1)[1].strip()
                            elif next_line.startswith("D"):  # Description
                                current_trade["Description"] = next_line.split(":", 1)[1].strip()
                                if current_trade["Description"].startswith("Hon."):
                                    current_trade["Description"] = ""

                                

                            j += 1  
                                                        
                        # Check if columns[1] matches the first word in the values of self.tickers_company
                        for key, value in self.tickers_company.items():
                            if value.split()[0] == columns[1]:
                                current_trade["Ticker"] = key
                                current_trade["Asset"] = value
                                break 
                        
                        # if columns[1] in self.tickers_company.values():
                        #     # Get the key from the value that matches the first word in the Asset
                        #     # The first word in the asset just needs to match the first word in the tickers_company_dict values
                        #     current_trade["Ticker"] = list(self.tickers_company.keys())[list(self.tickers_company.values()).index(columns[1])]
                        #     current_trade["Asset"] = self.tickers_company[current_trade["Ticker"]]
                            
                        
                        # Check if the ticker is is a variation of BRK.B
                        if current_trade["Ticker"].startswith("BRK"):
                            current_trade["Ticker"] = "BRK.B"
                        
                        if current_trade["Ticker"] not in self.tickers:

                            # Check if the ticker is in the S&P 500
                            print("Not in S&P 500: ", current_trade["Ticker"])   ##### DEBUGGING #####
                            if current_trade["Ticker"].__contains__(")"):
                                current_trade["Ticker"] = current_trade["Ticker"].split(")")[0]
                            if current_trade["Ticker"].strip("[]") in self.asset_dict:
                                current_trade["Ticker"] = self.asset_dict[current_trade["Ticker"].strip("[]")]
                            else:
                                try:
                                    # Check self.asset_dict for the asset type
                                    print("Try get_asset_type: ", current_trade["Ticker"])   ##### DEBUGGING #####
                                    current_trade["Ticker"] = self.asset_dict[current_trade["Ticker"].strip("[]")]
                                except Exception as e:
                                    print("download_and_parse_pdf, try get_asset_type: ", e)   ##### DEBUGGING #####
                                    current_trade["Ticker"] = "NaN"
                                    
                        if current_trade["DocID"] == "20025151" and current_trade["Ticker"] == "DIS":
                            current_trade["Transaction Type"] = "P"
                            current_trade["Transaction Date"] = "06/30/2021"
                            current_trade["Notification Date"] = "05/30/2024"
                            current_trade["Amount"] = "$1,001 - $15,000"
                            current_trade["Filing Status"] = "New"
                            current_trade["Description"] = ""  
                             
                        # Append to trade dictionary
                        for key in trade_dict:
                            trade_dict[key].append(current_trade[key])

                        # Reset current trade and update index
                        current_trade = {key: "" for key in trade_dict}
                        i = j - 1  # Move index to the next owner line

                    i += 1
                
                # Add the Member and DocID to the 
                
                # Convert to DataFrame
                pdf_df = pd.DataFrame(trade_dict)
                # pdf_df.insert(0, "Member", member)
                # pdf_df.insert(1, "DocID", doc_id)
                

                
                
                if pdf_df is not None:
                    pdf_df = pdf_df.sort_values(by=['Member', 'Transaction Date'], ascending=[True, False])
                    pdf_df.reset_index(drop=True, inplace=True)
                else:
                    print("PDF DataFrame is empty: ", doc_id)
                    pdf_df = pd.DataFrame()
                return pdf_df
            
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