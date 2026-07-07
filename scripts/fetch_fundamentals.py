"""
Indian Stock Market Financial Data Extractor
-------------------------------------------
Fetches historical annual financials and recent metrics from Yahoo Finance.
Reads from 'data/nse_bse_stocks_combined.csv'.
"""

import pandas as pd
import yahooquery as yq
import logging
import os
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

INPUT_FILE = 'data/nse_bse_stocks_combined.csv'
OUTPUT_EXCEL = 'data/NSE_BSE_Comprehensive_Financials.xlsx'

def get_ticker_data(ticker):
    """
    Helper function to fetch all available financial data for a single ticker.
    Returns a dictionary with dataframes and summary metrics.
    """
    if not ticker:
        return None

    try:
        stock = yq.Ticker(ticker)

        # Fetching annual financial statements (Income, Balance, Cash Flow)
        income = stock.income_statement(frequency='a')
        balance = stock.balance_sheet(frequency='a')
        cashflow = stock.cash_flow(frequency='a')

        # Summary information (Key Stats and Summary Detail)
        ks = stock.key_stats.get(ticker, {})
        sd = stock.summary_detail.get(ticker, {})

        # Flattening financials into a single structure
        dfs = []
        for df in [income, balance, cashflow]:
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Ensure we only work with full-year (12M) data
                if 'periodType' in df.columns:
                    df = df[df['periodType'] == '12M']
                if not df.empty:
                    # Reset index to make asOfDate accessible as a column
                    if 'asOfDate' not in df.columns:
                        df = df.reset_index()
                    dfs.append(df)

        merged_df = pd.DataFrame()
        if dfs:
            merged_df = dfs[0]
            for next_df in dfs[1:]:
                # Merge on date to align different statement entries
                cols_to_use = next_df.columns.difference(merged_df.columns).tolist() + ['asOfDate']
                merged_df = pd.merge(merged_df, next_df[cols_to_use], on='asOfDate', how='outer')

        return {
            'financials': merged_df,
            'recent': {**(ks if isinstance(ks, dict) else {}), **(sd if isinstance(sd, dict) else {})}
        }
    except Exception as e:
        logging.debug(f"Error fetching {ticker}: {e}")
        return None

def fetch_data(sample_limit=None):
    if not os.path.exists(INPUT_FILE):
        logging.error(f"{INPUT_FILE} not found. Ensure prepare_stock_list.py has been run.")
        return

    # Load consolidated stock registry
    df_stocks = pd.read_csv(INPUT_FILE)

    # Handle sampling for testing (e.g., 10 random stocks)
    if sample_limit:
        logging.info(f"Randomly selecting {sample_limit} companies for test...")
        df_stocks = df_stocks.sample(n=min(sample_limit, len(df_stocks)))

    all_data = []

    for _, stock in df_stocks.iterrows():
        # Identify listed exchanges and build tickers
        symbol_nse = stock.get('Symbol_NSE')
        symbol_bse = stock.get('Symbol_BSE')
        bse_code = stock.get('BSE_Code')

        ticker_nse = f"{str(symbol_nse).strip()}.NS" if pd.notnull(symbol_nse) else None
        # Use BSE Script Code for more reliable Yahoo Finance matching on BSE
        ticker_bse = f"{str(int(bse_code)).strip()}.BO" if pd.notnull(bse_code) else (f"{str(symbol_bse).strip()}.BO" if pd.notnull(symbol_bse) else None)

        logging.info(f"Processing {stock['Company_Name']} (NSE: {ticker_nse}, BSE: {ticker_bse})...")

        # Fetch data from both sources if available
        data_nse = get_ticker_data(ticker_nse)
        data_bse = get_ticker_data(ticker_bse)

        # Intelligence: Compare and pick the source with more data
        # We prioritize the number of records in the financial statements
        nse_count = len(data_nse['financials']) if data_nse and not data_nse['financials'].empty else 0
        bse_count = len(data_bse['financials']) if data_bse and not data_bse['financials'].empty else 0

        if nse_count >= bse_count and data_nse:
            selected_data = data_nse
            selected_ticker = ticker_nse
        elif data_bse:
            selected_data = data_bse
            selected_ticker = ticker_bse
        else:
            logging.warning(f"No meaningful data found for {stock['Company_Name']}")
            continue

        # Build the flat record
        row = {
            'Company Name': stock['Company_Name'],
            'Symbol_NSE': stock.get('Symbol_NSE'),
            'Symbol_BSE': stock.get('Symbol_BSE'),
            'BSE Code': stock.get('BSE_Code'),
            'ISIN': stock.get('ISIN'),
            'Selected Ticker': selected_ticker
        }

        # Add Recent Metrics
        for k, v in selected_data['recent'].items():
            if not isinstance(v, (dict, list)) and pd.notnull(v):
                row[f"Recent_{k}"] = v

        # Add Annual Financials (Flattened by year)
        if not selected_data['financials'].empty:
            for _, r in selected_data['financials'].iterrows():
                as_of = r.get('asOfDate')
                if pd.isnull(as_of): continue
                year = pd.to_datetime(as_of).year
                for k, v in r.to_dict().items():
                    # Exclude non-metric metadata
                    if k not in ['asOfDate', 'periodType', 'currencyCode', 'symbol'] and not isinstance(v, (dict, list)) and pd.notnull(v):
                        row[f"{k} ({year})"] = v

        all_data.append(row)

    if all_data:
        # Convert all collected records into a tabular DataFrame
        final_df = pd.DataFrame(all_data)

        # Column Organization: Identifiers first, then sorted metrics
        info_cols = ['Company Name', 'Symbol_NSE', 'Symbol_BSE', 'BSE Code', 'ISIN', 'Selected Ticker']
        other_cols = sorted([c for c in final_df.columns if c not in info_cols])

        final_df = final_df[info_cols + other_cols]

        # Export to high-precision Excel file
        final_df.to_excel(OUTPUT_EXCEL, index=False)
        logging.info(f"Successfully saved {len(final_df)} records to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    import sys
    # Optional command line argument to limit number of stocks for testing
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    fetch_data(sample_limit=limit)
