# Indian Stock Market Financial Data Extractor

This repository provides a robust toolset for extracting historical financial data for all companies listed on the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE) of India.

## Overview
The extractor leverages the `yahooquery` library to fetch comprehensive financial data from Yahoo Finance. It is designed to handle the scale of the Indian market (17,000+ tickers) by implementing multi-threading, batching, and a persistent checkpointing system to ensure data integrity and resume capabilities.

## Key Features
- **Historical Depth**: Fetches up to 15 years of annual financial statements (Income Statement, Balance Sheet, Cash Flow).
- **Comprehensive Metrics**: Captures all available fields including Revenue, Operating Income, Shares Outstanding, Receivables, Inventory, PP&E, Accounts Payable, and Enterprise Value (TEV).
- **Automated Mapping**: Merges NSE and BSE company registries using ISIN to ensure accurate cross-exchange data.
- **Optimized for Scale**: Uses asynchronous fetching and multi-threading for high-performance extraction.
- **Data Precision**: Maintains raw INR values as provided by the official sources without rounding.
- **Wide-Format Output**: Flattens complex financial data into a single Excel row per company, with columns labeled by fiscal year for easy analysis.

## Installation
Ensure you have Python 3.10+ installed. Install the required dependencies:

```bash
pip install pandas yahooquery openpyxl requests
```

## Usage

### 1. Quick Start: Nifty 50
To verify the extraction logic and generate a dataset for the Nifty 50 constituents:
```bash
python fetch_nifty50_financials.py
```
This will produce `Nifty50_Financials.xlsx` containing the full history for the top 50 companies.

### 2. Large Scale Market Extraction
To extract data for all listed companies:
1. **Consolidate Lists**: Merge the NSE and BSE metadata.
   ```bash
   python consolidate_lists.py
   ```
2. **Run Full Extraction**:
   ```bash
   python fetch_all_financials.py
   ```
   *Note: Extracting all 17,000+ companies is data-intensive and may take several hours. The script saves progress to `extraction_checkpoint.json` automatically.*

## Repository Structure
- `fetch_nifty50_financials.py`: Optimized script for Nifty 50 data extraction.
- `fetch_all_financials.py`: Robust, multi-threaded engine for full-market extraction.
- `consolidate_lists.py`: Utility to download and merge NSE/BSE registries.
- `Nifty50_Financials.xlsx`: Sample dataset containing multi-year financials for Nifty 50.
- `nifty50_list.csv`: Source list of Nifty 50 symbols.

## Data Source & Reliability
Data is fetched directly from Yahoo Finance via the `yahooquery` interface. This source provides a reliable and historical alternative to direct exchange scraping, which is often subject to aggressive anti-bot measures. The metrics are derived from consolidated annual reports (12M period type).
