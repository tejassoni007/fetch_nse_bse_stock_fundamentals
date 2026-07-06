import pandas as pd
import yahooquery as yq
import time
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

CHECKPOINT_FILE = 'extraction_checkpoint.json'
COMPANIES_LIST = 'companies_list.csv'
OUTPUT_EXCEL = 'NSE_BSE_Comprehensive_Financials.xlsx'

def fetch_company_data(ticker, info):
    try:
        stock = yq.Ticker(ticker)
        income_stmt = stock.income_statement(frequency='a')
        balance_sheet = stock.balance_sheet(frequency='a')
        cash_flow = stock.cash_flow(frequency='a')
        ks = stock.key_stats.get(ticker, {})
        sd = stock.summary_detail.get(ticker, {})

        company_data = {
            'Company_Info': {'Ticker': ticker, 'Company_Name': info.get('Company_Name'), 'NSE_Symbol': info.get('NSE_Symbol'), 'BSE_Code': info.get('BSE_Script_Code'), 'ISIN': info.get('ISIN')},
            'Annual_Financials': [],
            'Recent_Metrics': {**(ks if isinstance(ks, dict) else {}), **(sd if isinstance(sd, dict) else {})}
        }

        all_dfs = []
        for df in [income_stmt, balance_sheet, cash_flow]:
            if isinstance(df, pd.DataFrame) and not df.empty:
                if 'periodType' in df.columns: df = df[df['periodType'] == '12M']
                if not df.empty:
                    if 'asOfDate' not in df.columns: df = df.reset_index()
                    all_dfs.append(df)

        if all_dfs:
            merged = all_dfs[0]
            for next_df in all_dfs[1:]:
                cols = next_df.columns.difference(merged.columns).tolist() + ['asOfDate']
                merged = pd.merge(merged, next_df[cols], on='asOfDate', how='outer')
            for _, row in merged.iterrows():
                try:
                    as_of = row.get('asOfDate')
                    if pd.isnull(as_of): continue
                    rd = row.to_dict()
                    clean = {k: v for k, v in rd.items() if k not in ['asOfDate','periodType','currencyCode','symbol'] and not isinstance(v,(dict,list)) and pd.notnull(v)}
                    clean['asOfDate'] = str(as_of)
                    company_data['Annual_Financials'].append(clean)
                except: continue
        return company_data
    except: return None

def main(limit=None):
    if not os.path.exists(COMPANIES_LIST): return
    df_all = pd.read_csv(COMPANIES_LIST)
    all_results = {}
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f: all_results = json.load(f)
        except: pass

    tickers = [t for t in df_all['YQ_Symbol'].tolist() if t not in all_results]
    if limit: tickers = tickers[:limit]
    info_map = {row['YQ_Symbol']: row for _, row in df_all.iterrows()}

    logging.info(f"Total: {len(df_all)}, Remaining: {len(tickers)}")
    batch_size = 20
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        logging.info(f"Batch {i//batch_size + 1}... ({i}/{len(tickers)})")
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ticker = {executor.submit(fetch_company_data, t, info_map[t]): t for t in batch}
            for future in as_completed(future_to_ticker):
                res = future.result()
                if res: all_results[future_to_ticker[future]] = res
        with open(CHECKPOINT_FILE, 'w') as f: json.dump(all_results, f)
        time.sleep(1)

    flattened = []
    for ticker, data in all_results.items():
        row = {'Company Name': data['Company_Info']['Company_Name'], 'NSE Symbol': data['Company_Info']['NSE_Symbol'], 'BSE Script Code': data['Company_Info']['BSE_Code'], 'ISIN': data['Company_Info']['ISIN'], 'YQ Ticker': ticker}
        for k, v in data.get('Recent_Metrics', {}).items():
            if not isinstance(v,(dict,list)) and pd.notnull(v): row[f"Recent_{k}"] = v
        for entry in data.get('Annual_Financials', []):
            try:
                yr = pd.to_datetime(entry['asOfDate']).year
                for k, v in entry.items():
                    if k != 'asOfDate': row[f"{k} ({yr})"] = v
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
