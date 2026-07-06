import pandas as pd
import nsepython

def consolidate():
    # 1. Get current NSE symbols
    # nse_symbols = nsepython.nse_eq_symbols() # Slow and sometimes fails

    # Use EQUITY_L.csv which we downloaded
    nse_list = pd.read_csv('EQUITY_L.csv')
    # Clean column names (strip spaces)
    nse_list.columns = nse_list.columns.str.strip()
    print(f"NSE Columns: {nse_list.columns.tolist()}")

    nse_list = nse_list.rename(columns={'SYMBOL': 'NSE_Symbol', 'ISIN NUMBER': 'ISIN', 'NAME OF COMPANY': 'Company_Name'})

    # 2. Load BSE list from scrip file
    bse_file = 'SCRIP/BSE_EQ_SCRIP_15062023.csv'
    bse_scrip = pd.read_csv(bse_file, low_memory=False)
    # Clean column names
    bse_scrip.columns = bse_scrip.columns.str.strip()
    print(f"BSE Columns: {bse_scrip.columns.tolist()[:10]}")

    bse_scrip = bse_scrip.rename(columns={'FinInstrmId': 'BSE_Script_Code', 'TckrSymb': 'BSE_Symbol', 'ISIN': 'ISIN', 'FinInstrmNm': 'BSE_Company_Name'})

    # Merge NSE and BSE on ISIN
    merged = pd.merge(nse_list[['NSE_Symbol', 'Company_Name', 'ISIN']],
                      bse_scrip[['BSE_Script_Code', 'BSE_Symbol', 'ISIN']],
                      on='ISIN', how='outer')

    # If Company_Name is missing (from BSE only), use BSE_Symbol as a placeholder or search later
    merged['Company_Name'] = merged['Company_Name'].fillna(merged['BSE_Symbol'])

    # Create a column for the YahooQuery symbol
    def get_yq_symbol(row):
        if pd.notnull(row['NSE_Symbol']):
            return str(row['NSE_Symbol']).strip() + '.NS'
        elif pd.notnull(row['BSE_Script_Code']):
            return str(int(row['BSE_Script_Code'])).strip() + '.BO'
        return None

    merged['YQ_Symbol'] = merged.apply(get_yq_symbol, axis=1)

    # Filter out entries with no YQ_Symbol
    merged = merged.dropna(subset=['YQ_Symbol'])

    merged.to_csv('companies_list.csv', index=False)
    print(f"Consolidated list saved to companies_list.csv with {len(merged)} entries.")

if __name__ == "__main__":
    consolidate()
