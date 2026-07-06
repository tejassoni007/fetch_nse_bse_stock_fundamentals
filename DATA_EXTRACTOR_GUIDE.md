# Indian Stock Market Financial Data Extractor

This repository provides tools to extract historical financial data for Indian companies listed on the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE) using Yahoo Finance.

## Features
- Fetches up to 15 years of annual financial statements (Income Statement, Balance Sheet, Cash Flow).
- Captures all available metrics from Yahoo Finance.
- Flattens hierarchical data into a wide-format Excel file with metrics labeled by year.
- Includes specific handling for Nifty 50 constituents.

## Installation
```bash
pip install pandas yahooquery openpyxl requests
```

## Quick Start: Nifty 50
To fetch financials for all Nifty 50 companies:
1.  Ensure `nifty50_list.csv` is present.
2.  Run the extractor:
    ```bash
    python fetch_nifty50_financials.py
    ```
    This generates `Nifty50_Financials.xlsx`.

## Large Scale Extraction
For full NSE/BSE extraction, use `consolidate_lists.py` followed by `fetch_all_financials.py`. Note that this process can take several hours for the full 17,000+ companies list and is best run in batches.

## Files
- `fetch_nifty50_financials.py`: Optimized script for Nifty 50 data extraction.
- `nifty50_list.csv`: List of Nifty 50 constituents.
- `Nifty50_Financials.xlsx`: Consolidated financial dataset for Nifty 50.
- `consolidate_lists.py`: Helper to merge NSE and BSE company lists.
