import pandas as pd
import os

def consolidate():
    # 1. Load NSE list
    nse_file = 'EQUITY_L.csv'
    if not os.path.exists(nse_file):
        import requests
        print("Downloading EQUITY_L.csv...")
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        r = requests.get(url)
        with open(nse_file, 'wb') as f:
            f.write(r.content)

    nse_df = pd.read_csv(nse_file)
    nse_df.columns = nse_df.columns.str.strip()
    nse_df = nse_df.rename(columns={
        'SYMBOL': 'NSE_Symbol',
        'NAME OF COMPANY': 'Company_Name',
        'ISIN NUMBER': 'ISIN'
    })

    # 2. Load BSE list
    bse_file = 'SCRIP/BSE_EQ_SCRIP_15062023.csv'
    if os.path.exists(bse_file):
        bse_df = pd.read_csv(bse_file, low_memory=False)
        bse_df.columns = bse_df.columns.str.strip()
        bse_df = bse_df.rename(columns={
            'FinInstrmId': 'BSE_Script_Code',
            'TckrSymb': 'BSE_Symbol',
            'ISIN': 'ISIN',
            'FinInstrmNm': 'BSE_Company_Name'
        })
        bse_df = bse_df[['BSE_Script_Code', 'BSE_Symbol', 'ISIN', 'BSE_Company_Name']]
    else:
        print("Warning: BSE scrip file not found. Falling back to NSE-only mapping.")
        bse_df = pd.DataFrame(columns=['BSE_Script_Code', 'BSE_Symbol', 'ISIN', 'BSE_Company_Name'])

    # 3. Merge
    merged = pd.merge(nse_df[['NSE_Symbol', 'Company_Name', 'ISIN']], bse_df, on='ISIN', how='outer')

    # Fill missing company names
    merged['Company_Name'] = merged['Company_Name'].fillna(merged['BSE_Company_Name']).fillna(merged['BSE_Symbol']).fillna(merged['NSE_Symbol'])

    def generate_yq_ticker(row):
        if pd.notnull(row['NSE_Symbol']):
            return f"{str(row['NSE_Symbol']).strip()}.NS"
        if pd.notnull(row['BSE_Script_Code']):
            return f"{str(int(row['BSE_Script_Code'])).strip()}.BO"
        return None

    merged['YQ_Symbol'] = merged.apply(generate_yq_ticker, axis=1)
    merged = merged.dropna(subset=['YQ_Symbol']).sort_values('Company_Name')

    merged.to_csv('companies_list.csv', index=False)
    print(f"Consolidation complete. Total tickers: {len(merged)}")

if __name__ == "__main__":
    consolidate()
