"""
NSE & BSE Comprehensive Financial Data Extractor
-----------------------------------------------
This script fetches extensive historical financial data for all companies listed on the
NSE and BSE using Yahoo Finance.

Features:
- Robust multi-threaded execution.
- Checkpointing to resume progress.
- Flattens complex financial statements into a tabular Excel format.
"""

import pandas as pd
import yahooquery as yq
import time
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

CHECKPOINT_FILE = 'extraction_checkpoint.json'
COMPANIES_LIST = 'companies_list.csv'
OUTPUT_EXCEL = 'NSE_BSE_Comprehensive_Financials.xlsx'

def fetch_company_data(ticker, info):
    try:
        stock = yq.Ticker(ticker)

        # 1. Financial Statements (Annual)
        income_stmt = stock.income_statement(frequency='a')
        balance_sheet = stock.balance_sheet(frequency='a')
        cash_flow = stock.cash_flow(frequency='a')

        # 2. Recent Information
        try:
            ks = stock.key_stats.get(ticker, {})
        except: ks = {}
        try:
            sd = stock.summary_detail.get(ticker, {})
        except: sd = {}

        company_data = {
            'Company_Info': {
                'Ticker': ticker,
                'Company_Name': info.get('Company_Name'),
                'NSE_Symbol': info.get('NSE_Symbol'),
                'BSE_Code': info.get('BSE_Script_Code'),
                'ISIN': info.get('ISIN')
            },
            'Annual_Financials': [],
            'Recent_Metrics': {**(ks if isinstance(ks, dict) else {}),
                               **(sd if isinstance(sd, dict) else {})}
        }

        # Process annual statements
        all_dfs = []
        for df in [income_stmt, balance_sheet, cash_flow]:
            if isinstance(df, pd.DataFrame) and not df.empty:
                if 'periodType' in df.columns:
                    df = df[df['periodType'] == '12M']
                if not df.empty:
                    if 'asOfDate' not in df.columns:
                        df = df.reset_index()
                    all_dfs.append(df)

        if all_dfs:
            merged = all_dfs[0]
            for next_df in all_dfs[1:]:
                cols_to_use = next_df.columns.difference(merged.columns).tolist() + ['asOfDate']
                merged = pd.merge(merged, next_df[cols_to_use], on='asOfDate', how='outer')

            for _, r in merged.iterrows():
                try:
                    as_of = r.get('asOfDate')
                    if pd.isnull(as_of): continue
                    row_dict = r.to_dict()
                    clean = {k: v for k, v in row_dict.items() if k not in ['asOfDate','periodType','currencyCode','symbol'] and not isinstance(v,(dict,list)) and pd.notnull(v)}
                    clean['asOfDate'] = str(as_of)
                    company_data['Annual_Financials'].append(clean)
                except: continue

        return company_data
    except Exception as e:
        return None

def main(limit=None):
    if not os.path.exists(COMPANIES_LIST):
        logging.error(f"{COMPANIES_LIST} not found. Run consolidate_lists.py first.")
        return

    df_all = pd.read_csv(COMPANIES_LIST)

    all_results = {}
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                all_results = json.load(f)
            logging.info(f"Loaded {len(all_results)} companies from checkpoint.")
        except: pass

    # Identify tickers to skip
    processed_tickers = set(all_results.keys())
    remaining_df = df_all[~df_all['YQ_Symbol'].astype(str).isin(processed_tickers)]

    if limit:
        remaining_df = remaining_df.head(limit)

    tickers = remaining_df['YQ_Symbol'].tolist()
    info_map = {row['YQ_Symbol']: row for _, row in df_all.iterrows()}

    logging.info(f"Total: {len(df_all)}, Remaining: {len(tickers)}")

    batch_size = 20
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        logging.info(f"Batch {i//batch_size + 1}... ({i}/{len(tickers)})")

        batch_results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ticker = {executor.submit(fetch_company_data, t, info_map[t]): t for t in batch}
            for future in as_completed(future_to_ticker):
                res = future.result()
                if res:
                    batch_results[future_to_ticker[future]] = res

        all_results.update(batch_results)
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(all_results, f)
        time.sleep(1)

    # Save to Excel
    flatten_and_save(all_results)

def flatten_and_save(results):
    flattened = []
    for ticker, data in results.items():
        info = data.get('Company_Info', {})
        row = {
            'Company Name': info.get('Company_Name'),
            'NSE Symbol': info.get('NSE_Symbol'),
            'BSE Script Code': info.get('BSE_Code'),
            'ISIN': info.get('ISIN'),
            'YQ Ticker': ticker
        }
        for k, v in data.get('Recent_Metrics', {}).items():
            if not isinstance(v,(dict,list)) and pd.notnull(v):
                row[f"Recent_{k}"] = v
        for entry in data.get('Annual_Financials', []):
            try:
                yr = pd.to_datetime(entry['asOfDate']).year
                for k, v in entry.items():
                    if k != 'asOfDate':
                        row[f"{k} ({yr})"] = v
            except: continue
        flattened.append(row)

    if flattened:
        df = pd.DataFrame(flattened)
        info_cols = [c for c in ['Company Name', 'NSE Symbol', 'BSE Script Code', 'ISIN', 'YQ Ticker'] if c in df.columns]
        other_cols = sorted([c for c in df.columns if c not in info_cols])
        df[info_cols + other_cols].to_excel(OUTPUT_EXCEL, index=False)
        logging.info(f"Saved {len(df)} rows to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    import sys
    limit_val = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit=limit_val)
