"""
cleaner.py
----------
Cleaning + categorization logic for FinSight.
 
This module takes a raw, possibly-messy transactions DataFrame (straight
from an uploaded CSV) and returns a clean, standardized DataFrame ready
for analysis:
    - Standardizes column names
    - Cleans and parses dates and amounts
    - Categorizes transactions based on description keywords
"""

# Importing standard libraries
from pathlib import Path
import pandas as pd
import json

# Paths are relative to the project root
BASE = Path(__file__).resolve().parent.parent

# Load categories from a JSON file
def load_categories(path = "categories.json"):
    p = Path(path)
    if not p.is_absolute():
        p = BASE / p
    with p.open('r', encoding='utf-8') as f:
        categories = json.load(f)
    return categories

# --------------------------
# Column Cleaning
# --------------------------

# Common alternate names a real bank export might use — mapped to the
# canonical names this project expects internally.
Column_mapping = {
    "transaction date": "date",
    "txn date": "date",
    "narration": "description",
    "particulars": "description",
    "details": "description",
    "value": "amount",
    "debit/credit": "type",
}

# Lowercase and strip column and column mapping
def standardize_columns(df):
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip()
    df = df.rename(columns=Column_mapping)
    return df

# --------------------------
# Row Cleaning
# --------------------------

# Standardize and clean raw transaction DataFrame.
def clean_rows(df):

    # Expects (after standardize_columns) at least: date, description, amount.
    # 'type' is optional — it's derived from amount's sign if missing.
    df = standardize_columns(df)

    required_columns = ["date", "description", "amount"]
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()

    # --date--
    # dayfirst=True because FinSight assumes Indian-convention dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)

    # --amount--
    # Strip currency symbols or commas
    df["amount"] = (
                    df["amount"]
                    .astype(str)
                    .str.replace(r"[\$,]", "", regex=True)
                    .str.strip()
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # --description--
    df["description"] = df["description"].fillna("Unknown")
    df["description"] = df["description"].astype(str).str.strip()
    df.loc[df["description"] == "", "description"] = "Unknown"

    # Drop rows with unparseable dates or amounts
    before = len(df)
    df = df.dropna(subset=["date", "amount"])
    after_dropped = before - len(df)
    if after_dropped > 0:
        print(f"Dropped {after_dropped} rows due to unparseable dates or amounts.")

    # Removing duplicates
    before = len(df)
    df = df.drop_duplicates(subset = ["date", "description", "amount"])
    after_dropped = before - len(df)
    if after_dropped > 0:
        print(f"Dropped {after_dropped} duplicate rows.")

    #---type--
    df["type"] = df["amount"].apply(lambda a: "credit" if a > 0 else "debit")

    # Derived display column for human-readable date (keeps `date` as datetime)
    df["date_str"] = df["date"].dt.strftime("%d-%m-%Y")

    # Helpful derived columns used throughout the app (readable month)
    df["month"] = df["date"].dt.strftime("%b %Y")
 
    df = df.sort_values("date").reset_index(drop=True)

    return df

# --------------------------
# Categorization
# --------------------------

def categorize_description(description, categories):
    description = description.lower()
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword.lower() in description:
                return category
    return "other"

"""Add a 'category' column to df by applying categorize_description
    to every row's 'description'."""
def categorize_transactions(df, categories):
    df = df.copy()
    df["category"] = df["description"].apply(lambda desc: categorize_description(desc, categories))
    return df

# Calling all at once
def clean_transactions(raw_df, categories):
    cleaned_df = clean_rows(raw_df)
    categorized_df = categorize_transactions(cleaned_df, categories)
    return categorized_df

# Main function
def main():
    raw = pd.read_csv(BASE/"data"/"sample_transactions.csv")
    categories = load_categories(BASE/"categories.json")
    clean = clean_transactions(raw, categories)

    print(clean.head(10))
    print("\nRows:", len(clean))
    print("\nCategory counts:")
    print(clean["category"].value_counts())

if __name__ == "__main__":
    main()