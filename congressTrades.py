import requests
import zipfile
import pandas as pd
import re
import os
import io
import sys
import time
import datetime
from bs4 import BeautifulSoup
import pdfplumber
import xml.etree.ElementTree as ET
from IPython.display import display

from tickers500 import Tickers500

# Set display options to show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

class CongressTrades:
    
    def __init__(self):
        # Create an instance of the Tickers500 class
        self.tickers = Tickers500().tickers
        self.members = self.get_congress_members()
        self.trades = self.get_trades_by_member()
        
    def get_trades_by_member(self):
        congress_data = self.get_congress_trading_data()
        trades_by_member = {}
        
        try:
            for _, row in congress_data.iterrows():
                member = f"{row['Last']}".strip()
                doc_id = row['DocID']
                if member == "Pelosi":
                    print("DocID for download: ", doc_id)
                    pdf_df, trade_data = self.download_and_parse_pdf(doc_id)
                    
                    if member not in trades_by_member:
                        trades_by_member[member] = []
                    trades_by_member[member].extend(trade_data)
                else:
                    print("Member: ", member)    
                         
        except Exception as e:
            print(e)
        
        return trades_by_member

    def get_asset_type(self, asset_code = None) -> str:
        """
        Get the asset type codes from house.gov website.
        Parameters
        ----------
        asset_code : str
            The asset code to get the asset type name for.
        Returns
        -------
        str
            The asset name.
        """
        url = "https://fd.house.gov/reference/asset-type-codes.aspx"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find_all('table')[0]
        html_string = str(table)
        html_io = io.StringIO(html_string)
        df = pd.read_html(html_io)[0]

        df = df[df['Asset Code'] == asset_code]
        asset_name = df['Asset Name'].values[0]
        return asset_name

    def get_asset_type_df() -> pd.DataFrame:
        """
        Get the asset type codes from house.gov website.
        Returns
        -------
        pd.DataFrame
            A DataFrame containing the asset codes and their names.
        """
        url = "https://fd.house.gov/reference/asset-type-codes.aspx"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find_all('table')[0]
        html_string = str(table)
        html_io = io.StringIO(html_string)
        df = pd.read_html(html_io)[0]

        return df

    def get_congress_trading_data(self) -> pd.DataFrame:
        """
        Downloads the latest financial disclosure data from the House of Representatives
        and returns a DataFrame with the data.
        """

        file_path = 'data/congress/'
        current_year = datetime.datetime.now().year
        current_fd = str(current_year) + "FD"

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

        # Save the DataFrames to CSV files
        # txt_df.to_csv(file_path + current_fd + ".csv", index=False)
        xml_df.to_csv(file_path + 'csv/' + current_fd + ".csv", index=False)

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

    def download_and_parse_pdf(self, doc_id) -> pd.DataFrame:
        """
        Download and parse a financial disclosure PDF to extract structured trade data.
        Handles multi-line trade entries robustly.
        """
        
        trade_dict = {
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
        
        file_path = 'data/congress/'
        current_year = datetime.datetime.now().year
        pdf_file_name = doc_id + ".pdf"

        # Define the URL of the zip file
        url = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/" + str(current_year) + '/' + pdf_file_name

        # Send a GET request to download the zip file
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code != 200:
            print("Failed to download the file")
            sys.exit()

        # Use the pdfplumber library to extract text from the PDF

        # Create the pdf file
        with open(file_path + 'pdf/' + pdf_file_name, 'wb') as pdf_file:
            pdf_file.write(response.content)

        # Open the PDF file
        with pdfplumber.open(file_path + 'pdf/' + pdf_file_name) as pdf:
            pdf_text = "".join(page.extract_text() for page in pdf.pages)

        lines = pdf_text.splitlines()
        
        owner_types = ["SP", "DC", "JT"]
        current_trade = {key: "" for key in trade_dict}  # Initialize a trade record
        
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a new trade line starting with known owner types
            if any(line.startswith(owner_type) for owner_type in owner_types):
                columns = line.split()
                current_trade["Owner"] = columns[0]
                current_trade["Asset"] = " ".join(columns[1:-6]).split("-", 1)[0].strip()
                current_trade["Ticker"] = columns[-6].strip("()")
                if current_trade["Asset"].__contains__("("):
                    current_trade["Asset"], current_trade["Ticker"] = current_trade["Asset"].rsplit("(", 1)
                    current_trade["Ticker"] = current_trade["Ticker"].split(")")[0]
                current_trade["Transaction Type"] = columns[-5]
                current_trade["Transaction Date"] = columns[-4]
                current_trade["Notification Date"] = columns[-3]
                current_trade["Amount"] = columns[-2]
                # Set amount based on current case
                if current_trade["Amount"] == "$0":
                    current_trade["Amount"] = "None"
                elif current_trade["Amount"] == "$1":
                    current_trade["Amount"] = "$1 - $15,000"
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
                if current_trade["Transaction Type"] == "(partial)":
                    current_trade["Transaction Type"] = columns[-6] + " " + columns[-5]
                    # current_trade["Ticker"] = re.search(r'\((.*?)\)', current_trade["Asset"]).group(1)

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
                    # elif next_line.startswith("$"):  # Additional amount info
                    #     current_trade["Amount"] += " " + next_line
                    elif next_line.__contains__("F"):  # Filing Status
                        current_trade["Filing Status"] = next_line.split(":", 1)[1].strip()
                    elif next_line.__contains__("D"):  # Description
                        current_trade["Description"] = next_line.split(":", 1)[1].strip()
                    # else:
                        

                    j += 1

                # Append to trade dictionary
                for key in trade_dict:
                    trade_dict[key].append(current_trade[key])

                # Reset current trade and update index
                current_trade = {key: "" for key in trade_dict}
                i = j - 1  # Move index to the next owner line

            i += 1
        
        # Convert to DataFrame
        pdf_df = pd.DataFrame(trade_dict)


        return pdf_df
    
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