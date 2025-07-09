#!/usr/bin/env python3
"""
Original PDF parsing logic extracted from fetch_congress_data.py
This module contains the original parsing logic for comparison with the validation framework.
"""

import pdfplumber
import re
import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path


class OriginalPDFParser:
    """Original PDF parsing logic from fetch_congress_data.py"""
    
    def __init__(self, tickers: set, asset_dict: dict, tickers_company: dict):
        self.tickers = tickers
        self.asset_dict = asset_dict
        self.tickers_company = tickers_company
    
    def parse_pdf_original(self, pdf_path: str, doc_id: str, member: str) -> pd.DataFrame:
        """
        Original PDF parsing logic from fetch_congress_data.py
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
        
        try:
            # Open the PDF file
            with pdfplumber.open(pdf_path) as pdf:
                pdf_text = "".join(page.extract_text() for page in pdf.pages)

            if not pdf_text.strip():
                print("PDF is empty: ", doc_id)
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
                    
                    if doc_id == "20019685":
                        # print a line for debugging with column values
                        print("Columns: ", columns)
                    
                    current_trade["Member"] = member
                    current_trade["DocID"] = doc_id
                    current_trade["Owner"] = columns[0]
                    current_trade["Asset"] = " ".join(columns[1:-6]).split("-", 1)[0].strip()
                    
                    # Find the column containing "()" and split the asset and ticker
                    if current_trade["Asset"].__contains__("("):
                        current_trade["Asset"], current_trade["Ticker"] = current_trade["Asset"].rsplit("(", 1)
                        current_trade["Ticker"] = current_trade["Ticker"].split(")")[0]
                        
                    current_trade["Transaction Type"] = columns[-5]
                    if "transaction" in current_trade["Transaction Type"]:
                        i+=2
                        break
                    if "Transaction" in current_trade["Transaction Type"]:
                        i+=2
                        break
                    current_trade["Transaction Date"] = columns[-4]
                    current_trade["Notification Date"] = columns[-3]
                    current_trade["Amount"] = columns[-2]
                    if current_trade["Amount"] == "-":
                        current_trade["Amount"] = columns[-3]
                    
                    # Original complex logic for handling various edge cases
                    if current_trade["Notification Date"].startswith("$") and current_trade["Notification Date"].endswith("1"):
                        current_trade["Amount"] = columns[-3]
                        if current_trade["Amount"] == "-":
                            current_trade["Amount"] = columns[-4]
                        current_trade["Notification Date"] = columns[-4]
                        current_trade["Transaction Date"] = columns[-5]
                        current_trade["Transaction Type"] = columns[-6]
                    elif current_trade["Notification Date"].startswith("$") and current_trade["Notification Date"].endswith("0"):
                        current_trade["Amount"] = columns[-5]
                        if current_trade["Amount"] == "-":
                            current_trade["Amount"] = columns[-6]
                        current_trade["Notification Date"] = columns[-6]
                        current_trade["Transaction Date"] = columns[-7]
                        current_trade["Transaction Type"] = columns[-8]

                    if current_trade["Transaction Date"].startswith("$") and current_trade["Transaction Date"].endswith("1"):
                        current_trade["Amount"] = columns[-4]
                        if current_trade["Amount"] == "-":
                            current_trade["Amount"] = columns[-5]
                        current_trade["Notification Date"] = columns[-5]
                        current_trade["Transaction Date"] = columns[-6]
                        current_trade["Transaction Type"] = columns[-7]
                    elif current_trade["Transaction Date"].startswith("$") and current_trade["Transaction Date"].endswith("0"):
                        current_trade["Amount"] = columns[-7]
                        if current_trade["Amount"] == "-":
                            current_trade["Amount"] = columns[-8]
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
                        
                    # Set amount based on current case
                    if current_trade["Amount"] == "-":
                        current_trade["Amount"] = columns[-4] + " " + columns[-3] + " " + columns[-2]
                        
                    if current_trade["Amount"].startswith("Spouse/DC"):
                        current_trade["Amount"] = "$1,000,001 - $5,000,000"                           
                    
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
                        if next_line.startswith("Initial"):
                            break
                        if next_line.startswith("Asset"):
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
                            if current_trade["Description"].endswith("ID Owner Asset Transaction Date Notification Amount"):
                                current_trade["Description"].split("ID Owner Asset Transaction Date Notification Amount")[0]

                        j += 1  
                                                    
                    # Check if columns[1] matches the first word in the values of self.tickers_company
                    for key, value in self.tickers_company.items():
                        if value.split()[0] == columns[1]:
                            current_trade["Ticker"] = key
                            current_trade["Asset"] = value
                            break 
                        
                    
                    # Check if the ticker is is a variation of BRK.B
                    if current_trade["Ticker"].startswith("BRK"):
                        current_trade["Ticker"] = "BRK.B"
                    if current_trade["Ticker"].startswith("bRK"):
                        current_trade["Ticker"] = "BRK.B"
                    
                    if current_trade["Ticker"] not in self.tickers:
                        # Check if the ticker is in the S&P 500
                        print("Not in S&P 500: ", current_trade["Ticker"])
                        if current_trade["Ticker"].__contains__(")"):
                            current_trade["Ticker"] = current_trade["Ticker"].split(")")[0]
                        if current_trade["Ticker"].strip("[]") in self.asset_dict:
                            current_trade["Ticker"] = self.asset_dict[current_trade["Ticker"].strip("[]")]
                        else:
                            try:
                                # Check self.asset_dict for the asset type
                                print("Try get_asset_type: ", current_trade["Ticker"])
                                current_trade["Ticker"] = self.asset_dict[current_trade["Ticker"].strip("[]")]
                            except Exception as e:
                                print("download_and_parse_pdf, try get_asset_type: ", e)
                                current_trade["Ticker"] = "NaN"
                                
                    if current_trade["DocID"] == "20025151" and current_trade["Ticker"] == "DIS":
                        current_trade["Transaction Type"] = "P"
                        current_trade["Transaction Date"] = "06/30/2021"
                        current_trade["Notification Date"] = "05/30/2024"
                        current_trade["Amount"] = "$1,001 - $15,000"
                        current_trade["Filing Status"] = "New"
                        current_trade["Description"] = ""  
                    
                    transaction_types = ["P", "S", "S (partial)"]
                    if current_trade["Transaction Type"] not in transaction_types:
                        # Skip this current trade and move to the next line
                        i += 1
                        continue
                    
                         
                    # Append to trade dictionary
                    for key in trade_dict:
                        trade_dict[key].append(current_trade[key])

                    # Reset current trade and update index
                    current_trade = {key: "" for key in trade_dict}
                    i = j - 1  # Move index to the next owner line

                i += 1
            
            # Convert to DataFrame
            pdf_df = pd.DataFrame(trade_dict)        
            
            if pdf_df is not None:
                pdf_df = pdf_df.sort_values(by=['Member', 'Transaction Date'], ascending=[True, False])
                pdf_df.reset_index(drop=True, inplace=True)
            else:
                print("PDF DataFrame is empty: ", doc_id)
                pdf_df = pd.DataFrame()
            return pdf_df
        
        except Exception as e:
            print("parse_pdf_original, try: ", e)
            return pd.DataFrame() 