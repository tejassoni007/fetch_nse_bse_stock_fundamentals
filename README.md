# Indian Stock Market Financial Data Extractor

This repository contains tools for extracting historical annual financial statements and recent key metrics for companies listed on the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE) of India.

## Features
- **Consolidated Registry**: Merges NSE and BSE listed company lists using ISIN and Symbol mapping.
- **Enhanced Historical Extraction**: Utilizes the `Bharat-SM-Data` library to fetch up to 15 years of historical financials (Revenue, Operating Income, Shares) from TickerTape and other reliable sources.
- **BSE & NSE Coverage**: Supports symbols from both major Indian exchanges.
- **Recent Balance Sheet Metrics**: Extracts Receivables, Inventory, PP&E, and Payables for the latest fiscal year.
- **Enterprise Value Calculation**: Computes Total Enterprise Value (TEV) using current Market Cap and balance sheet data.
- **Wide-Format Output**: Generates an Excel file with metrics labeled by year for easy longitudinal analysis.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Execution Steps

### 1. Prepare Stock List
Generate the consolidated list of NSE and BSE stocks:
```bash
python scripts/prepare_stock_list.py
```
This produces `data/nse_bse_stocks_combined.csv`.

### 2. Fetch Fundamentals
Extract financial data for the stocks in the list using the refined Bharat Scraper:
```bash
python scripts/bharat_scraper.py [sample_size]
```
- To run a test on 50 random stocks: `python scripts/bharat_scraper.py 50`
- To run for all stocks: `python scripts/bharat_scraper.py`
- Final output is saved to `data/NSE_BSE_Comprehensive_Financials.xlsx`.

## Directory Structure
- `data/`: Contains the consolidated stock list and the final financial dataset.
- `scripts/`: Contains the logic for list preparation and data extraction.
- `requirements.txt`: Python package dependencies.
