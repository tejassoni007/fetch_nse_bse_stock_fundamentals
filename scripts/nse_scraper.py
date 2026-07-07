import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import logging
import re
import os
import random
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class NSEScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.base_url = "https://www.nseindia.com"
        self.filings_url = "https://www.nseindia.com/api/corporates-financial-results"

    def fetch_filings(self, symbol):
        params = {"symbol": symbol, "industry": "-", "period": "Annual", "index": "equities"}
        headers = {"Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"}
        try:
            response = self.session.get(self.filings_url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                self.session.get(self.base_url, timeout=20)
                response = self.session.get(self.filings_url, params=params, headers=headers, timeout=20)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logging.error(f"Error fetching filings for {symbol}: {e}")
        return []

    def parse_html_table(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        data = {}
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    key = re.sub(r'\s+', ' ', cols[0].get_text(" ", strip=True)).strip()
                    val = cols[1].get_text(strip=True)
                    data[key] = val
        return data

    def clean_val(self, v):
        if v is None or v == '' or v == '-' or v == '0.00': return None
        if isinstance(v, (int, float)): return float(v)
        try:
            return float(re.sub(r'[^\d.E+-]', '', str(v).replace(',', '')))
        except:
            return None

    def extract_metrics_from_html(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                html_data = self.parse_html_table(response.text)
                revenue_keys = ['Total income from operations (net) ( a + b)', 'Total income from operations (net)', 'Total income from operations', 'Total Income', 'Net Sales/Income from Operation', 'Net Sales/Income from Operations', 'Net sales/income from operations (Inclusive of excise duty)']
                op_income_keys = ['Profit / (Loss) from operations before other income, finance costs and exceptional items', 'Profit from Operations before Other Income, Interest & Exceptional Items', 'Profit from Operations before Other Income, Interest & Exceptional Items', 'Operating Profit', 'PBDIT']

                revenue = next((html_data[k] for k in revenue_keys if k in html_data), None)
                op_income = next((html_data[k] for k in op_income_keys if k in html_data), None)
                equity_cap = html_data.get('Paid-up Equity Share Capital') or html_data.get('Equity Share Capital')
                face_val = html_data.get('Face Value (in Rs.)') or html_data.get('Face Value')

                return {
                    "Revenue": self.clean_val(revenue),
                    "Operating Income": self.clean_val(op_income),
                    "Equity Capital": self.clean_val(equity_cap),
                    "Face Value": self.clean_val(face_val)
                }
        except Exception as e:
            logging.error(f"Error extracting from HTML {url}: {e}")
        return None

    def extract_xbrl_metrics(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                content = response.text

                def find_tag_val(tag):
                    # Modified to check for FourD then D12M then others
                    match = re.search(f'<{tag}[^>]*contextRef="(FourD|D12M)"[^>]*>([^<]+)</{tag}>', content)
                    if not match:
                        match = re.search(f'<{tag}[^>]*contextRef="(OneI|OneD)"[^>]*>([^<]+)</{tag}>', content)
                    if not match:
                        match = re.search(f'<{tag}[^>]*>([^<]+)</{tag}>', content)
                    return self.clean_val(match.group(2)) if match else None

                # Calculate Operating Income from XBRL
                pbt = find_tag_val("in-bse-fin:ProfitBeforeTax")
                finance_costs = find_tag_val("in-bse-fin:FinanceCosts") or find_tag_val("in-bse-fin:Interest")
                # Operating Income Heuristic: PBT + Finance Costs (excluding other income)
                # But typically Operating Income in result tables is EBIT.
                ebit = find_tag_val("in-bse-fin:ProfitBeforeFinanceCostsAndExceptionalItemsBeforeTax")
                if ebit is None and pbt is not None and finance_costs is not None:
                    ebit = pbt + finance_costs

                metrics = {
                    "Receivables": find_tag_val("in-bse-fin:TradeReceivablesCurrent") or find_tag_val("in-bse-fin:TradeReceivables"),
                    "Inventory": find_tag_val("in-bse-fin:Inventories"),
                    "PP&E": find_tag_val("in-bse-fin:PropertyPlantAndEquipment"),
                    "Payables": find_tag_val("in-bse-fin:TradePayablesCurrent") or find_tag_val("in-bse-fin:TradePayables"),
                    "Revenue": find_tag_val("in-bse-fin:RevenueFromOperations") or find_tag_val("in-bse-fin:IncomeFromOperations") or find_tag_val("in-bse-fin:TotalIncome"),
                    "Operating Income": ebit,
                    "Equity Capital": find_tag_val("in-bse-fin:EquityShareCapital"),
                    "Face Value": find_tag_val("in-bse-fin:FaceValuePerEquityShare"),
                    "EPS": find_tag_val("in-bse-fin:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations") or find_tag_val("in-bse-fin:BasicEarningsLossPerShareFromContinuingOperations"),
                    "NetProfit": find_tag_val("in-bse-fin:ProfitLossForPeriod") or find_tag_val("in-bse-fin:ProfitLossForPeriodFromContinuingOperations")
                }
                return metrics
        except Exception as e:
            logging.error(f"Error extracting from XBRL {url}: {e}")
        return None

    def get_company_data(self, symbol):
        logging.info(f"Scraping data for {symbol}...")
        filings = self.fetch_filings(symbol)
        if not filings: return None

        all_years_data = {}
        year_groups = {}
        for f in filings:
            to_date = f.get('toDate')
            if not to_date: continue
            try:
                dt = pd.to_datetime(to_date)
                year = dt.year
                if year not in year_groups: year_groups[year] = []
                year_groups[year].append(f)
            except: continue

        latest_special = {}
        years = sorted(year_groups.keys(), reverse=True)
        if not years: return None
        latest_year = years[0]

        for year in years:
            if year < 2011: continue
            group = year_groups[year]
            selected_filing = next((f for f in group if f.get('consolidated') == 'Consolidated'), group[0])

            html_link = selected_filing.get('resultDetailedDataLink')
            xbrl_link = selected_filing.get('xbrl')
            if xbrl_link == '-': xbrl_link = None

            metrics = None

            if xbrl_link:
                metrics = self.extract_xbrl_metrics(xbrl_link)

            if (not metrics or not metrics.get('Revenue')) and html_link:
                html_metrics = self.extract_metrics_from_html(html_link)
                if html_metrics:
                    if not metrics: metrics = {}
                    metrics.update({k: v for k, v in html_metrics.items() if v is not None})

            if metrics and metrics.get('Revenue'):
                shares = None
                rev = metrics['Revenue']
                if metrics.get('Equity Capital') and metrics.get('Face Value'):
                    cap = metrics['Equity Capital']
                    if rev > 1e9 or cap > 1e9: # Absolute INR
                        shares = cap / metrics['Face Value']
                    else: # Lakhs
                        shares = (cap * 100000) / metrics['Face Value']

                if not shares and metrics.get('NetProfit') and metrics.get('EPS'):
                    shares = metrics['NetProfit'] / metrics['EPS']

                all_years_data[year] = {
                    "Revenue": rev,
                    "Operating Income": metrics.get('Operating Income'),
                    "Shares": shares
                }

            if year == latest_year and metrics:
                latest_special = metrics

        return {"annual": all_years_data, "latest_special": latest_special}

def process_stocks(stocks_file, output_file, limit=None):
    df_stocks = pd.read_csv(stocks_file)
    if limit:
        df_stocks = df_stocks.sample(n=min(limit, len(df_stocks)), random_state=random.randint(1, 1000))

    scraper = NSEScraper()
    all_rows = []

    for _, stock in df_stocks.iterrows():
        symbol = stock['Symbol_NSE']
        if pd.isnull(symbol): continue

        data = scraper.get_company_data(symbol)
        if not data: continue

        row = {
            "Company Name": stock['Company_Name'],
            "NSE Symbol": symbol,
            "BSE Script Code": stock.get('BSE_Code')
        }

        for y in range(2011, 2027):
            y_data = data['annual'].get(y, {})
            row[f"Total Revenue ({y})"] = y_data.get('Revenue', "N/A")
            row[f"Total Operating Income ({y})"] = y_data.get('Operating Income', "N/A")
            row[f"Basic Weighted Average Shares Outstanding ({y})"] = y_data.get('Shares', "N/A")

        ls = data['latest_special']
        row["Total Receivables (2025-2026)"] = ls.get('Receivables', "N/A")
        row["Inventory (2025-2026)"] = ls.get('Inventory', "N/A")
        row["Net Property Plant and Equipment (PP&E) (2025-2026)"] = ls.get('PP&E', "N/A")
        row["Total Accounts Payable (2025-2026)"] = ls.get('Payables', "N/A")
        row["Last Total Enterprise Value (TEV) (2025-2026)"] = "N/A"

        all_rows.append(row)
        time.sleep(2)

    if all_rows:
        df_final = pd.DataFrame(all_rows)
        cols = ["Company Name", "NSE Symbol", "BSE Script Code"]
        for y in range(2011, 2027):
            cols.extend([f"Total Revenue ({y})", f"Total Operating Income ({y})", f"Basic Weighted Average Shares Outstanding ({y})"])
        cols.extend(["Total Receivables (2025-2026)", "Inventory (2025-2026)", "Net Property Plant and Equipment (PP&E) (2025-2026)", "Total Accounts Payable (2025-2026)", "Last Total Enterprise Value (TEV) (2025-2026)"])
        cols = [c for c in cols if c in df_final.columns]
        df_final = df_final[cols]
        df_final.to_excel(output_file, index=False)
        logging.info(f"Saved {len(all_rows)} results to {output_file}")

if __name__ == "__main__":
    import sys
    limit = 20
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    process_stocks('data/nse_bse_stocks_combined.csv', 'data/NSE_BSE_Comprehensive_Financials.xlsx', limit=limit)
