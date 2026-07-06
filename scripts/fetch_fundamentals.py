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

def fetch_data(sample_limit=None):
    if not os.path.exists(INPUT_FILE):
        logging.error(f"{INPUT_FILE} not found. Run scripts/prepare_stock_list.py first.")
        return

    df_stocks = pd.read_csv(INPUT_FILE)

    # Handle sampling if requested
    if sample_limit:
        logging.info(f"Randomly selecting {sample_limit} companies for test...")
        df_stocks = df_stocks.sample(n=min(sample_limit, len(df_stocks)))

    all_data = []

    for _, stock in df_stocks.iterrows():
        # Prefer NSE symbol if available
        # Based on new prepare_stock_list, we have 'Symbol' and 'BSE_Code'
        symbol = stock.get('Symbol')
        bse_code = stock.get('BSE_Code')

        # If it's likely an NSE symbol (alphabetic), append .NS
        # If it's purely numeric (BSE Code), append .BO
        # Actually, symbols in our combined list are mixed.

        if pd.notnull(symbol) and any(c.isalpha() for c in str(symbol)):
            ticker = f"{str(symbol).strip()}.NS"
        elif pd.notnull(bse_code):
            ticker = f"{str(int(bse_code)).strip()}.BO"
        elif pd.notnull(symbol): # Fallback
            ticker = f"{str(symbol).strip()}.BO"
        else:
            continue

        try:
            logging.info(f"Fetching data for {ticker}...")
            yq_stock = yq.Ticker(ticker)

            # Annual Financials (12M only)
            income = yq_stock.income_statement(frequency='a')
            balance = yq_stock.balance_sheet(frequency='a')
            cashflow = yq_stock.cash_flow(frequency='a')

            # Summary Metrics
            ks = yq_stock.key_stats.get(ticker, {})
            sd = yq_stock.summary_detail.get(ticker, {})

            # Base info
            row_base = {
                'Company Name': stock['Company_Name'],
                'Symbol': stock['Symbol'],
                'BSE Code': stock['BSE_Code'],
                'ISIN': stock['ISIN'],
                'YQ Ticker': ticker
            }

            # Recent Metrics
            recent = {**(ks if isinstance(ks, dict) else {}), **(sd if isinstance(sd, dict) else {})}
            for k, v in recent.items():
                if not isinstance(v, (dict, list)) and pd.notnull(v):
                    row_base[f"Recent_{k}"] = v

            # Annual metrics flattening
            annual_rows = {}
            ticker_dfs = []
            for df in [income, balance, cashflow]:
                if isinstance(df, pd.DataFrame) and not df.empty:
                    if ticker in df.index.get_level_values(0):
                        tdf = df.loc[ticker]
                        if 'periodType' in tdf.columns:
                            tdf = tdf[tdf['periodType'] == '12M']
                        if not tdf.empty:
                            if 'asOfDate' not in tdf.columns: tdf = tdf.reset_index()
                            ticker_dfs.append(tdf)

            if ticker_dfs:
                merged = ticker_dfs[0]
                for next_df in ticker_dfs[1:]:
                    cols = next_df.columns.difference(merged.columns).tolist() + ['asOfDate']
                    merged = pd.merge(merged, next_df[cols], on='asOfDate', how='outer')

                for _, r in merged.iterrows():
                    as_of = r.get('asOfDate')
                    if pd.isnull(as_of): continue
                    year = pd.to_datetime(as_of).year
                    for k, v in r.to_dict().items():
                        if k not in ['asOfDate', 'periodType', 'currencyCode', 'symbol'] and not isinstance(v,(dict,list)) and pd.notnull(v):
                            annual_rows[f"{k} ({year})"] = v

            all_data.append({**row_base, **annual_rows})

        except Exception as e:
            logging.error(f"Error for {ticker}: {e}")

    if all_data:
        final_df = pd.DataFrame(all_data)
        info_cols = ['Company Name', 'Symbol', 'BSE Code', 'ISIN', 'YQ Ticker']
        other_cols = sorted([c for c in final_df.columns if c not in info_cols])
        final_df[info_cols + other_cols].to_excel(OUTPUT_EXCEL, index=False)
        logging.info(f"Successfully saved results to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    fetch_data(sample_limit=limit)
