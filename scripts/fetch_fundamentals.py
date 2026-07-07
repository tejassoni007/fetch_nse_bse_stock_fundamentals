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
        # symbol = 'RGIL'
        # bse_code = 539922
        symbol_nse = stock.get('Symbol_NSE')
        symbol_bse = stock.get('Symbol_BSE')
        if pd.notnull(symbol_nse):
            ticker_nse = f"{str(symbol_nse).strip()}.NS"
        else:
            ticker_nse = None
        if pd.notnull(symbol_bse):
            ticker_bse = f"{str(symbol_bse).strip()}.BO"
        else:
            ticker_bse = None

        try:
            logging.info(f"Fetching data for BSE {ticker_bse} and NSE {ticker_nse}...")
            yq_stock_bse = yq.Ticker(ticker_bse)
            yq_stock_nse = yq.Ticker(ticker_nse)

            # Annual Financials (12M only)
            income_bse = yq_stock_bse.income_statement(frequency='a')
            balance_bse = yq_stock_bse.balance_sheet(frequency='a')
            cashflow_bse = yq_stock_bse.cash_flow(frequency='a')
            income_nse = yq_stock_nse.income_statement(frequency='a')
            balance_nse = yq_stock_nse.balance_sheet(frequency='a')
            cashflow_nse = yq_stock_nse.cash_flow(frequency='a')

            # Summary Metrics
            ks_bse = yq_stock_bse.key_stats.get(ticker_bse, {})
            sd_bse = yq_stock_bse.summary_detail.get(ticker_bse, {})
            ks_nse = yq_stock_nse.key_stats.get(ticker_nse, {})
            sd_nse = yq_stock_nse.summary_detail.get(ticker_nse, {})

            # Base info
            row_base = {
                'Company Name': stock['Company_Name'],
                'Symbol_NSE': stock['Symbol_NSE'],
                'Symbol_BSE': stock['Symbol_BSE'],
                'BSE Code': stock['BSE_Code'],
                'ISIN': stock['ISIN'],
                'YQ Ticker NSE': ticker_nse,
                'YQ Ticker BSE': ticker_bse
            }

            # Recent Metrics
            recent_bse = {**(ks_bse if isinstance(ks_bse, dict) else {}), **(sd_bse if isinstance(sd_bse, dict) else {})}
            recent_nse = {**(ks_nse if isinstance(ks_nse, dict) else {}), **(sd_nse if isinstance(sd_nse, dict) else {})}
            for k, v in recent_nse.items():
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
