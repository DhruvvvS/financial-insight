# FinSight 💸

A personal & small-business finance analyzer built with **Python, pandas, and Streamlit**.

Small businesses and freelancers often track expenses in scattered spreadsheets with little visibility into spending patterns. FinSight ingests raw transaction data, automatically cleans and categorizes it, visualizes monthly spending trends, forecasts upcoming expenses, and exports a shareable report — all through an interactive web dashboard.

## Features

- **Upload any transactions CSV** (or explore instantly with bundled sample data)
- **Automatic data cleaning** — parses messy dates/amounts, removes duplicates, standardizes column names from common bank-export formats
- **Keyword-based categorization** — sorts transactions into categories (rent, groceries, shopping, etc.) via an editable `categories.json` rule file
- **Interactive dashboard** — monthly income/expense summary, category breakdown (bar + pie charts), spending trend lines
- **Editable category table** — fix any miscategorized transaction directly in the browser
- **3-month expense forecast** — using both a rolling average and a linear trend projection
- **One-click export** — download your report as CSV, Excel, or PDF

## Tech Stack

Python · pandas · Streamlit · Plotly · openpyxl · fpdf2 · NumPy

## Project Structure

```text
finsight/
├── app.py                      # Streamlit entry point
├── generate_dummy_data.py      # Generates realistic sample transaction data
├── categories.json             # Keyword → category mapping rules
├── requirements.txt
├── data/
│   └── sample_transactions.csv # 6 months of synthetic demo data
└── utils/
    ├── cleaner.py               # Data cleaning + categorization
    ├── analyzer.py              # Monthly summaries, category breakdowns, KPIs
    ├── forecaster.py            # Rolling average & trend-based forecasting
    └── exporter.py               # PDF report generation
```

## Getting Started

### 1. Clone the repo and install dependencies

```bash
git clone <your-repo-url>
cd finsight
pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

**3. Explore**
Check "Use sample data" in the sidebar to try it instantly, or upload your own transactions CSV with `date, description, amount` columns (dates in `DD-MM-YYYY` format).

## Sample Data

`data/sample_transactions.csv` contains 6 months of synthetically generated transactions (income, recurring bills, day-to-day spending, and a few deliberate one-off large expenses) — useful for demoing the dashboard and for testing the cleaning/categorization/forecasting logic. Regenerate it anytime with:

```bash
python generate_dummy_data.py --months 6 --seed 42 --out data/sample_transactions.csv
```

## How It Works

1. **Clean** (`utils/cleaner.py`) — standardizes column names, parses dates (`DD-MM-YYYY`) and amounts, removes duplicates/unparseable rows
2. **Categorize** (`utils/cleaner.py`) — matches each transaction's description against keyword rules in `categories.json`
3. **Analyze** (`utils/analyzer.py`) — computes monthly income/expense summaries, category breakdowns, and headline KPIs
4. **Forecast** (`utils/forecaster.py`) — projects the next 3 months' expenses via rolling average and linear trend
5. **Export** (`utils/exporter.py`) — generates a PDF summary report combining all of the above

## License

This project was built as a personal/portfolio project and is free to use or adapt.
