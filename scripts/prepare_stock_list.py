import pandas as pd
import requests
import os
import io
from pathlib import Path



def fetch_nse_list():
    print("Fetching NSE list...")
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = df.columns.str.strip().str.lower()

    # Save interim NSE file
    # Resolves to one level above the script file
    parent_dir = Path(__file__).resolve().parents[1]
    os.makedirs(parent_dir / 'data', exist_ok=True)

    df.to_csv(parent_dir / 'data' / 'stocks_nse.csv', index=False)

    return df[['symbol', 'name of company', 'isin number']].rename(columns={
        'symbol': 'Symbol',
        'name of company': 'Company_Name',
        'isin number': 'ISIN'
    })

def fetch_bse_list():
    print("Fetching BSE list...")
    url = "https://www.bseindia.com/downloads/Help/scrip.zip"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        import zipfile
        z = zipfile.ZipFile(io.BytesIO(r.content))
        for name in z.namelist():
            if 'BSE_EQ_SCRIP' in name:
                with z.open(name) as f:
                    df = pd.read_csv(f, low_memory=False)
                    df.columns = df.columns.str.strip().str.lower()

                    # Save interim BSE file
                    parent_dir = Path(__file__).resolve().parents[1]
                    df.to_csv(parent_dir / 'data' / 'stocks_bse.csv', index=False)

                    return df.loc[df['sctytpflg'] == 'EQ', ['fininstrmid', 'tckrsymb', 'isin', 'fininstrmnm']].rename(columns={
                        'fininstrmid': 'BSE_Code',
                        'tckrsymb': 'Symbol',
                        'isin': 'ISIN',
                        'fininstrmnm': 'Company_Name'
                    })
    except Exception as e:
        print(f"Error fetching BSE list: {e}")
        return pd.DataFrame(columns=['BSE_Code', 'Symbol', 'ISIN', 'Company_Name'])

def main():
    nse_df = fetch_nse_list()
    bse_df = fetch_bse_list()

    print("Consolidating lists using Symbol...")
    # The user specifically requested merging using the symbol.
    # Note: NSE symbols are strings, BSE 'TckrSymb' are also strings.
    combined = pd.merge(nse_df, bse_df, on='ISIN', how='outer', suffixes=('_NSE', '_BSE'))

    # Consolidate Company Name and ISIN
    combined['Company_Name'] = combined['Company_Name_NSE'].fillna(combined['Company_Name_BSE'])

    # Final cleanup
    combined = combined[['Company_Name', 'Symbol_BSE', 'Symbol_NSE', 'BSE_Code', 'ISIN']]

    parent_dir = Path(__file__).resolve().parents[1]
    combined.to_csv(parent_dir / 'data' / 'nse_bse_stocks_combined.csv', index=False)
    print(f"Saved {len(combined)} stocks to data/nse_bse_stocks_combined.csv")

if __name__ == "__main__":
    main()
