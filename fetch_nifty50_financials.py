import pandas as pd
import yahooquery as yq
import logging
import os
from datetime import datetime
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
INPUT_LIST = 'nifty50_list.csv'
OUTPUT_EXCEL = 'Nifty50_Financials.xlsx'
def fetch_nifty50_data():
    if not os.path.exists(INPUT_LIST): return
    df_nifty = pd.read_csv(INPUT_LIST)
    symbols = (df_nifty['Symbol'] + '.NS').tolist()
    info_map = {row['Symbol'] + '.NS': row.to_dict() for _, row in df_nifty.iterrows()}
    logging.info(f"Fetching data for {len(symbols)} Nifty 50 companies...")
    stocks = yq.Ticker(symbols, asynchronous=True)
    income_statements = stocks.income_statement(frequency='a')
    balance_sheets = stocks.balance_sheet(frequency='a')
    cash_flows = stocks.cash_flow(frequency='a')
    key_stats = stocks.key_stats
    summary_details = stocks.summary_detail
    all_data = []
    for ticker in symbols:
        try:
            logging.info(f"Processing {ticker}...")
            info = info_map.get(ticker, {})
            row_base = {'Company Name': info.get('Company Name'), 'NSE Symbol': info.get('Symbol'), 'ISIN': info.get('ISIN Code'), 'YQ Ticker': ticker}
            ticker_dfs = []
            for st_df in [income_statements, balance_sheets, cash_flows]:
                if isinstance(st_df, pd.DataFrame) and not st_df.empty:
                    if ticker in st_df.index.get_level_values(0):
                        df = st_df.loc[ticker]
                        if 'periodType' in df.columns: df = df[df['periodType'] == '12M']
                        if not df.empty:
                            if 'asOfDate' not in df.columns: df = df.reset_index()
                            ticker_dfs.append(df)
            annual_rows = {}
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
                        if k not in ['asOfDate','periodType','currencyCode','symbol'] and not isinstance(v,(dict,list)) and pd.notnull(v):
                            annual_rows[f"{k} ({year})"] = v
            recent_metrics = {}
            ks = key_stats.get(ticker, {})
            sd = summary_details.get(ticker, {})
            combined_recent = {**(ks if isinstance(ks, dict) else {}), **(sd if isinstance(sd, dict) else {})}
            for k, v in combined_recent.items():
                if not isinstance(v, (dict, list)) and pd.notnull(v): recent_metrics[f"Recent_{k}"] = v
            all_data.append({**row_base, **recent_metrics, **annual_rows})
        except Exception as e: logging.error(f"Error for {ticker}: {e}")
    if all_data:
        final_df = pd.DataFrame(all_data)
        info_cols = ['Company Name', 'NSE Symbol', 'ISIN', 'YQ Ticker']
        other_cols = sorted([c for c in final_df.columns if c not in info_cols])
        final_df[info_cols + other_cols].to_excel(OUTPUT_EXCEL, index=False)
        logging.info(f"Successfully saved {len(final_df)} rows.")
if __name__ == "__main__":
    fetch_nifty50_data()
