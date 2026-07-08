import pandas as pd
import time
import logging
import random
import os
import sys
from Fundamentals.TickerTape import Tickertape

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class BharatScraper:
    def __init__(self):
        self.tt = Tickertape()
        self.unit_multiplier = 10000000  # TickerTape uses Crores (10^7) for absolute figures

    def fetch_company_data(self, symbol, isin=None, company_name=None):
        """Fetches data from TickerTape with retries and SID resolution."""
        logging.info(f"Fetching data for {symbol} (ISIN: {isin})...")

        data_found = None
        sid_used = None

        # Priority 1: Use symbol as SID directly
        # Priority 2: Search by ISIN
        # Priority 3: Search by Symbol
        # Priority 4: Search by Name
        search_candidates = []
        if symbol and not pd.isnull(symbol): search_candidates.append(('direct', str(symbol)))
        if isin and not pd.isnull(isin): search_candidates.append(('search', str(isin)))
        if symbol and not pd.isnull(symbol): search_candidates.append(('search', str(symbol)))
        if company_name and not pd.isnull(company_name): search_candidates.append(('search', str(company_name)))

        for method, query in search_candidates:
            if not query or query == 'nan' or query == '0': continue
            try:
                if method == 'direct':
                    # Try a small call to check if SID exists
                    df_check = self.tt.get_income_data(query, time_horizon='annual', num_time_periods=1)
                    if not df_check.empty:
                        sid_used = query
                else:
                    # Use search API
                    time.sleep(random.uniform(2, 4))
                    sid_used, _ = self.tt.get_ticker(query)

                if sid_used:
                    # Fetch full historical income data
                    df_inc = self.tt.get_income_data(sid_used, time_horizon='annual', num_time_periods=20)
                    if not df_inc.empty:
                        data_found = {'income': df_inc}
                        break
                    else:
                        sid_used = None # Reset if income was empty
            except Exception as e:
                if "403" in str(e):
                    logging.warning(f"  403 Forbidden for {query}. Cooling down...")
                    time.sleep(30)
                    self.tt = Tickertape() # Reset session
                else:
                    logging.debug(f"  Method {method} failed for {query}: {e}")

        if not data_found:
            return None

        # Fetch sub-data (Balance Sheet and Ratios)
        try:
            time.sleep(random.uniform(1, 3))
            df_bs = self.tt.get_balance_sheet_data(sid_used, num_time_periods=20)
            time.sleep(random.uniform(1, 3))
            slug = self.tt._get_url_of_the_ticker(sid_used)
            ratios = self.tt.get_key_ratios(slug) if slug != '/' else pd.DataFrame()

            data_found.update({
                'balance': df_bs,
                'ratios': ratios,
                'sid': sid_used
            })
            return data_found
        except Exception as e:
            logging.debug(f"  Partial data fetched for {sid_used}: {e}")
            return data_found

    def extract_metrics(self, data):
        if not data: return None

        df_inc = data.get('income', pd.DataFrame())
        df_bs = data.get('balance', pd.DataFrame())
        ratios = data.get('ratios', pd.DataFrame())

        annual_data = {}
        def parse_year(dp):
            if not dp or 'FY' not in dp: return None
            try: return int(dp.split(' ')[1])
            except: return None

        # Process Income Statement
        if not df_inc.empty:
            for _, row in df_inc.iterrows():
                year = parse_year(row.get('displayPeriod'))
                if not year: continue
                annual_data[year] = {
                    'Revenue': row.get('incTrev') * self.unit_multiplier if pd.notnull(row.get('incTrev')) else None,
                    'Operating Income': row.get('incEbi') * self.unit_multiplier if pd.notnull(row.get('incEbi')) else None,
                }

        # Process Balance Sheet
        if not df_bs.empty:
            for _, row in df_bs.iterrows():
                year = parse_year(row.get('displayPeriod'))
                if not year: continue
                if year not in annual_data: annual_data[year] = {}

                annual_data[year].update({
                    'Shares': row.get('balTcso') * self.unit_multiplier if pd.notnull(row.get('balTcso')) else None,
                    'Receivables': row.get('balTrec') * self.unit_multiplier if pd.notnull(row.get('balTrec')) else None,
                    'Inventory': row.get('balTinv') * self.unit_multiplier if pd.notnull(row.get('balTinv')) else None,
                    'PP&E': row.get('balNppe') * self.unit_multiplier if pd.notnull(row.get('balNppe')) else None,
                    'Payables': row.get('balAccp') * self.unit_multiplier if pd.notnull(row.get('balAccp')) else None,
                    'Debt': row.get('balTdeb') * self.unit_multiplier if pd.notnull(row.get('balTdeb')) else None,
                    'Cash': row.get('balCsti') * self.unit_multiplier if pd.notnull(row.get('balCsti')) else None,
                })

        # Find latest available fiscal year (up to 2026)
        years = sorted([y for y in annual_data.keys() if y <= 2026], reverse=True)
        latest_year = years[0] if years else None

        latest_special = {}
        if latest_year:
            ls = annual_data[latest_year]
            latest_special = {
                'Receivables': ls.get('Receivables'),
                'Inventory': ls.get('Inventory'),
                'PP&E': ls.get('PP&E'),
                'Payables': ls.get('Payables'),
            }

            # Enterprise Value (TEV) Calculation: Mcap + Total Debt - Cash
            mcap = None
            if not ratios.empty:
                try:
                    if 'marketCap' in ratios.index:
                        val = ratios.loc['marketCap'].iloc[0] if hasattr(ratios.loc['marketCap'], 'iloc') else ratios.loc['marketCap']
                        mcap = float(val) * self.unit_multiplier
                except: pass

            debt = ls.get('Debt')
            cash = ls.get('Cash')
            if mcap and debt is not None and cash is not None:
                latest_special['TEV'] = mcap + debt - cash
            else:
                latest_special['TEV'] = None

        return {"annual": annual_data, "latest_special": latest_special}

def run_bharat_scraper(stocks_file, output_file, limit=50):
    if not os.path.exists(stocks_file):
        logging.error(f"Input file {stocks_file} not found.")
        return

    df_stocks = pd.read_csv(stocks_file)
    if limit:
        # Reproducible sample
        df_stocks = df_stocks.sample(n=min(limit, len(df_stocks)), random_state=42)

    scraper = BharatScraper()
    all_rows = []

    for i, stock in df_stocks.iterrows():
        symbol = stock.get('Symbol_NSE')
        if not symbol or pd.isnull(symbol):
            symbol = stock.get('Symbol_BSE')

        isin = stock.get('ISIN')
        name = stock.get('Company_Name')

        if not symbol or pd.isnull(symbol):
            continue

        try:
            data = scraper.fetch_company_data(symbol, isin=isin, company_name=name)
            metrics = scraper.extract_metrics(data)
        except Exception as e:
            logging.error(f"Critical failure for {name} ({symbol}): {e}")
            metrics = None

        if not metrics or not metrics.get('annual'):
            logging.warning(f"No meaningful data found for {name} ({symbol})")
            continue

        row = {
            "Company Name": name,
            "NSE Symbol": stock.get('Symbol_NSE'),
            "BSE Script Code": stock.get('BSE_Code')
        }

        # Map 15 years chronologically (2011 to 2026)
        for y in range(2011, 2027):
            y_data = metrics['annual'].get(y, {})
            row[f"Total Revenue ({y})"] = y_data.get('Revenue', "N/A")
            row[f"Total Operating Income ({y})"] = y_data.get('Operating Income', "N/A")
            row[f"Basic Weighted Average Shares Outstanding ({y})"] = y_data.get('Shares', "N/A")

        ls = metrics['latest_special']
        row["Total Receivables (2025-2026)"] = ls.get('Receivables', "N/A")
        row["Inventory (2025-2026)"] = ls.get('Inventory', "N/A")
        row["Net Property Plant and Equipment (PP&E) (2025-2026)"] = ls.get('PP&E', "N/A")
        row["Total Accounts Payable (2025-2026)"] = ls.get('Payables', "N/A")
        row["Last Total Enterprise Value (TEV) (2025-2026)"] = ls.get('TEV', "N/A")

        all_rows.append(row)
        # Moderate delay to balance speed and safety
        time.sleep(random.uniform(3, 6))

    if all_rows:
        df_final = pd.DataFrame(all_rows)
        # Column Ordering
        base_cols = ["Company Name", "NSE Symbol", "BSE Script Code"]
        annual_cols = []
        for y in range(2011, 2027):
            annual_cols.extend([f"Total Revenue ({y})", f"Total Operating Income ({y})", f"Basic Weighted Average Shares Outstanding ({y})"])
        recent_cols = ["Total Receivables (2025-2026)", "Inventory (2025-2026)", "Net Property Plant and Equipment (PP&E) (2025-2026)", "Total Accounts Payable (2025-2026)", "Last Total Enterprise Value (TEV) (2025-2026)"]

        final_cols = base_cols + [c for c in annual_cols if c in df_final.columns] + [c for c in recent_cols if c in df_final.columns]
        df_final = df_final[final_cols]

        df_final.to_excel(output_file, index=False)
        logging.info(f"Process complete. Saved {len(all_rows)} results to {output_file}")
    else:
        logging.warning("No data collected in this run.")

if __name__ == "__main__":
    # Test on 50 stocks by default
    limit = 50
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    run_bharat_scraper('data/nse_bse_stocks_combined.csv', 'data/NSE_BSE_Comprehensive_Financials.xlsx', limit=limit)
