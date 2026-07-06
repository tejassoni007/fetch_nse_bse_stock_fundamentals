# Indian Stock Market Financial Data Extractor

This repository contains tools for extracting historical annual financial statements and recent key metrics for companies listed on the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE) of India.

## Features
- **Consolidated Registry**: Merges NSE and BSE listed company lists using ISIN and Symbol mapping.
- **Comprehensive Extraction**: Fetches Income Statements, Balance Sheets, and Cash Flow statements (up to 15 years) from Yahoo Finance.
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
Extract financial data for the stocks in the list:
```bash
python scripts/fetch_fundamentals.py [sample_size]
```
- To run a test on 10 random stocks: `python scripts/fetch_fundamentals.py 10`
- To run for all stocks (Time intensive): `python scripts/fetch_fundamentals.py`
- Final output is saved to `data/NSE_BSE_Comprehensive_Financials.xlsx`.

## Directory Structure
- `data/`: Contains the consolidated stock list and the final financial dataset.
- `scripts/`: Contains the logic for list preparation and data extraction.
- `requirements.txt`: Python package dependencies.
