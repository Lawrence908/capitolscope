"""

# Project Context:
# I am building a Python-based algorithmic trading platform called "CapitolScope."
# The project involves working with time-series stock data and Congress trading data for machine learning models.
# This prompt is specifically focused on fetching time-series stock data using the AlphaVantage API.

# Task Context:
# 1. I need to create a Python script that fetches historical stock data from the AlphaVantage API.
# 2. The API should support different intervals (daily, weekly, monthly) and allow fetching compact (100 rows) or full data.
# 3. The fetched data should be stored as a pandas DataFrame with columns: ['date', 'open', 'high', 'low', 'close', 'volume'].
# 4. The script should handle API errors, unexpected response structures, and missing data gracefully.
# 5. Later, this data will be saved into a PostgreSQL database or as CSV files.

# Folder Structure:
# - src/
#   - ingestion/
#     - fetch_stock_data.py (this script)
#   - .env (stores API key and base URL)
# - data/
#   - raw/ (to store fetched data temporarily)
# - notebooks/
#   - For testing and debugging fetched data.

# Requirements for fetch_stock_data.py:
# 1. Create a function `fetch_time_series()` that:
#    - Accepts stock symbol (e.g., "AAPL"), interval ("daily", "weekly", "monthly"), and output size ("compact", "full").
#    - Makes a GET request to the AlphaVantage API using the requests library.
#    - Parses the response JSON into a pandas DataFrame.
#    - Sorts the data by date (oldest to newest).
#    - Handles potential errors (e.g., invalid symbol, API rate limits, missing data).
# 2. Include detailed docstrings for the function.
# 3. Add type hints for function arguments and return values.
# 4. Provide an example call to the function for testing.

# Example Output:
# A pandas DataFrame structured like this:
# |    date     |   open |   high |   low |   close |   volume |
# |-------------|--------|--------|-------|---------|----------|
# | 2023-12-01  |  150.0 |  152.0 | 148.5 |   151.0 |   500000 |
# | 2023-12-02  |  151.0 |  153.0 | 149.0 |   152.5 |   450000 |

# Configuration Reference:
# - The API key is stored in src/utils/config.py as ALPHA_VANTAGE_API_KEY.
# - The base URL for AlphaVantage API calls is https://www.alphavantage.co/query.

# Function Signature:
# def fetch_time_series(symbol: str, interval: str = "daily", output_size: str = "compact") -> pd.DataFrame:



"""


import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
BASE_URL = os.getenv("ALPHA_VANTAGE_BASE_URL")

def get_tickers(SP500: bool = True, NASDAQ: bool = True, DowJones: bool = True) -> list:
    
    # Get S&P 500 tickers
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    tickers500 = []
    for row in table.find_all('tr')[1:]:
        ticker = row.find('td').text.strip()
        tickers500.append(ticker)
    
    # Get NASDAQ tickers
    url = 'https://en.wikipedia.org/wiki/NASDAQ-100'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    tickers100 = []
    for row in table.find_all('tr')[1:]:
        ticker = row.find_all('td')[1].text.strip()
        tickers100.append(ticker) 
        
    # Get Dow Jones tickers
    url = 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'wikitable'})
    tickers30 = []
    for row in table.find_all('tr')[1:]:
        ticker = row.find_all('td')[2].text.strip()
        tickers30.append(ticker)
        
    if SP500 and NASDAQ and DowJones:
        tickers = list(set(tickers500 + tickers100 + tickers30))
    elif SP500 and NASDAQ:
        tickers = list(set(tickers500 + tickers100))
    elif SP500 and DowJones:
        tickers = list(set(tickers500 + tickers30))
    elif NASDAQ and DowJones:
        tickers = list(set(tickers100 + tickers30))
    elif SP500:
        tickers = tickers500
    elif NASDAQ:
        tickers = tickers100
    elif DowJones:
        tickers = tickers30
    else:
        tickers = tickers500
    
    return tickers

def fetch_time_series(symbol: str, interval: str = "daily", output_size: str = "compact") -> pd.DataFrame:
    """
    Fetch time-series data for a given stock symbol from AlphaVantage.

    Args:
        symbol (str): Stock ticker symbol (e.g., "AAPL").
        interval (str): Time interval ("daily", "weekly", "monthly").
        output_size (str): "compact" (latest 100 data points) or "full" (all available data).

    Returns:
        pd.DataFrame: Time-series data with columns ['date', 'open', 'high', 'low', 'close', 'volume'].
    """
    function_map = {
        "daily": "TIME_SERIES_DAILY",
        "weekly": "TIME_SERIES_WEEKLY",
        "monthly": "TIME_SERIES_MONTHLY"
    }
    if interval not in function_map:
        raise ValueError(f"Invalid interval: {interval}. Choose from 'daily', 'weekly', or 'monthly'.")

    url = BASE_URL
    params = {
        "function": function_map[interval],
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "outputsize": output_size
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    if "Error Message" in data:
        raise ValueError(f"Error fetching data for symbol {symbol}: {data['Error Message']}")
    if f"Time Series ({interval.capitalize()})" not in data:
        raise ValueError(f"Unexpected response structure: {data}")

    time_series_key = f"Time Series ({interval.capitalize()})"
    time_series_data = data[time_series_key]

    records = []
    for date, values in time_series_data.items():
        record = {
            "date": date,
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": float(values["5. volume"])
        }
        records.append(record)

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values('date', inplace=True)

    return df




def main():
    pass


if __name__ == "__main__":
    main()